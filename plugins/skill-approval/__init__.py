"""Skill Creation Approval Plugin

This plugin adds a user approval step before the agent creates new skills.
When the agent attempts to create a skill via skill_manage(action='create'),
the user is prompted to approve or deny the creation.

Features:
- Interactive approval prompts (CLI and gateway)
- Session-scoped approvals (approve once for the entire session)
- Permanent approvals (always approve skill creation)
- Configurable via plugin settings or environment variables

Configuration:
  Set HERMES_SKILL_APPROVAL_MODE to control behavior:
  - "require" (default): Always prompt for approval
  - "off": Disable approval, allow all skill creation
  - "auto": Auto-approve in non-interactive contexts

Environment Variables:
  HERMES_SKILL_APPROVAL_MODE: Control approval mode (require/off/auto)
  HERMES_SKILL_APPROVAL_YOLO: Set to "1" to bypass all approvals (debug mode)
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Per-session approval state (thread-safe)
_lock = threading.Lock()
_session_approved_skills: Dict[str, bool] = {}  # session_key -> always approve
_permanent_approval: bool = False


def _get_approval_mode() -> str:
    """Get the approval mode from environment or config.

    Returns:
        "require": Always prompt (default)
        "off": Disable approval
        "auto": Auto-approve in non-interactive contexts
    """
    mode = os.environ.get("HERMES_SKILL_APPROVAL_MODE", "require").lower()
    if mode in ("require", "off", "auto"):
        return mode
    return "require"


def _is_yolo_mode() -> bool:
    """Check if YOLO mode is enabled (bypass all approvals)."""
    return os.environ.get("HERMES_SKILL_APPROVAL_YOLO") == "1"


def _get_session_key() -> str:
    """Get the current session key for tracking approvals."""
    # Use the same session key mechanism as the main approval system
    return os.environ.get("HERMES_SESSION_KEY", "default")


def _is_session_approved(session_key: str) -> bool:
    """Check if skills are approved for this session."""
    with _lock:
        return _session_approved_skills.get(session_key, False) or _permanent_approval


def _approve_session(session_key: str) -> None:
    """Approve skill creation for this session."""
    with _lock:
        _session_approved_skills[session_key] = True


def _approve_permanent() -> None:
    """Approve skill creation permanently."""
    global _permanent_approval
    with _lock:
        _permanent_approval = True


def _prompt_skill_approval(skill_name: str, description: str, category: str = None) -> str:
    """Prompt the user to approve skill creation.

    Args:
        skill_name: Name of the skill to create
        description: Description from frontmatter
        category: Optional category

    Returns:
        'once', 'session', 'always', or 'deny'
    """
    is_cli = os.environ.get("HERMES_INTERACTIVE")
    is_gateway = os.environ.get("HERMES_GATEWAY_SESSION")

    # For gateway mode, we need async approval - for now, return 'deny'
    # and log that gateway support needs to be implemented
    if is_gateway:
        logger.warning(
            "Skill approval requested in gateway mode. "
            "Gateway async approval not yet implemented. Denying by default."
        )
        return "deny"

    # CLI interactive prompt
    if not is_cli:
        # Non-interactive context - auto-deny for safety
        logger.warning("Skill approval requested in non-interactive context. Denying by default.")
        return "deny"

    # Pause the spinner if active
    os.environ["HERMES_SPINNER_PAUSE"] = "1"

    try:
        while True:
            print()
            print(f"  📚 SKILL CREATION REQUEST")
            print(f"      Name: {skill_name}")
            if category:
                print(f"      Category: {category}")
            if description:
                # Truncate long descriptions
                desc_preview = description[:200] + "..." if len(description) > 200 else description
                print(f"      Description: {desc_preview}")
            print()
            print("      Allow the agent to create this skill?")
            print("      [o]nce  |  [s]ession  |  [a]lways  |  [d]eny")
            print()
            sys.stdout.flush()

            try:
                choice = input("      Choice [o/s/a/D]: ").strip().lower()
            except (EOFError, OSError):
                choice = ""

            if choice in ('o', 'once'):
                print("      ✓ Skill creation allowed once")
                return "once"
            elif choice in ('s', 'session'):
                print("      ✓ Skill creation allowed for this session")
                return "session"
            elif choice in ('a', 'always'):
                print("      ✓ Skill creation always allowed")
                return "always"
            else:
                print("      ✗ Skill creation denied")
                return "deny"

    except (EOFError, KeyboardInterrupt):
        print("\n      ✗ Cancelled")
        return "deny"
    finally:
        if "HERMES_SPINNER_PAUSE" in os.environ:
            del os.environ["HERMES_SPINNER_PAUSE"]
        print()
        sys.stdout.flush()


def _extract_skill_metadata(tool_args: dict) -> tuple[str, str, str]:
    """Extract skill name, description, and category from tool arguments.

    Args:
        tool_args: Arguments passed to skill_manage tool

    Returns:
        (skill_name, description, category)
    """
    skill_name = tool_args.get("name", "unnamed-skill")
    category = tool_args.get("category", "")

    # Try to extract description from content (SKILL.md frontmatter)
    content = tool_args.get("content", "")
    description = ""

    if content:
        # Simple frontmatter parsing - look for description: field
        lines = content.split('\n')
        in_frontmatter = False
        for line in lines:
            if line.strip() == '---':
                if not in_frontmatter:
                    in_frontmatter = True
                    continue
                else:
                    break
            if in_frontmatter and line.strip().startswith('description:'):
                description = line.split(':', 1)[1].strip().strip('"\'')
                break

    return skill_name, description, category


def pre_tool_call(tool_name: str, tool_args: dict, **kwargs: Any) -> Optional[Dict[str, Any]]:
    """Hook called before any tool execution.

    Intercepts skill_manage(action='create') calls to prompt for approval.

    Args:
        tool_name: Name of the tool being called
        tool_args: Arguments passed to the tool
        **kwargs: Additional context (task_id, session, etc.)

    Returns:
        None to allow the tool to proceed, or a dict with:
        - "block": True to prevent tool execution
        - "result": JSON string to return as the tool result
    """
    # Only intercept skill_manage tool
    if tool_name != "skill_manage":
        return None

    # Only intercept create actions
    action = tool_args.get("action", "")
    if action != "create":
        return None

    # Check approval mode
    mode = _get_approval_mode()
    if mode == "off":
        return None  # Allow all skill creation

    # Check YOLO mode
    if _is_yolo_mode():
        logger.debug("Skill approval bypassed (YOLO mode)")
        return None

    # Check session-level approval
    session_key = _get_session_key()
    if _is_session_approved(session_key):
        logger.debug("Skill creation approved (session-level approval active)")
        return None

    # Auto-approve in non-interactive contexts if mode is "auto"
    is_interactive = os.environ.get("HERMES_INTERACTIVE")
    if mode == "auto" and not is_interactive:
        logger.debug("Skill creation auto-approved (auto mode, non-interactive)")
        return None

    # Extract skill metadata for prompt
    skill_name, description, category = _extract_skill_metadata(tool_args)

    # Prompt for approval
    choice = _prompt_skill_approval(skill_name, description, category)

    # Handle denial
    if choice == "deny":
        error_msg = (
            f"Skill creation denied by user. "
            f"The user has explicitly rejected creating the skill '{skill_name}'. "
            f"Do NOT retry skill creation unless the user explicitly requests it again."
        )
        return {
            "block": True,
            "result": json.dumps({
                "success": False,
                "error": error_msg,
                "skill_name": skill_name,
                "denied": True,
            }, ensure_ascii=False)
        }

    # Handle session approval
    if choice == "session":
        _approve_session(session_key)
        logger.info("Skill creation approved for session %s", session_key)

    # Handle permanent approval
    elif choice == "always":
        _approve_permanent()
        logger.info("Skill creation permanently approved")

    # Allow the tool to proceed (choice was "once", "session", or "always")
    return None


def register(ctx) -> None:
    """Register the skill approval plugin.

    Called by the plugin manager during discovery.

    Args:
        ctx: PluginContext providing access to registration methods
    """
    # Register the pre_tool_call hook
    ctx.register_hook("pre_tool_call", pre_tool_call)

    logger.info(
        "Skill approval plugin loaded (mode: %s)",
        _get_approval_mode()
    )
