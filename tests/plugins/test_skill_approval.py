"""Tests for skill-approval plugin

Tests the skill creation approval workflow.
"""

import json
import os
from unittest.mock import patch, MagicMock

import pytest


@pytest.fixture
def plugin_module():
    """Import the plugin module"""
    import sys
    from pathlib import Path

    plugin_path = Path(__file__).parent.parent.parent / "plugins" / "skill-approval"
    if str(plugin_path) not in sys.path:
        sys.path.insert(0, str(plugin_path))

    import __init__ as skill_approval_plugin
    return skill_approval_plugin


def test_pre_tool_call_allows_non_skill_manage_tools(plugin_module):
    """Non-skill_manage tools should pass through without approval"""
    result = plugin_module.pre_tool_call("terminal", {"command": "ls"})
    assert result is None


def test_pre_tool_call_allows_non_create_actions(plugin_module):
    """skill_manage with non-create actions should pass through"""
    result = plugin_module.pre_tool_call(
        "skill_manage",
        {"action": "edit", "name": "test"}
    )
    assert result is None


def test_pre_tool_call_respects_off_mode(plugin_module):
    """approval mode=off should allow all skill creation"""
    with patch.dict(os.environ, {"HERMES_SKILL_APPROVAL_MODE": "off"}):
        result = plugin_module.pre_tool_call(
            "skill_manage",
            {"action": "create", "name": "test", "content": "---\ndescription: test\n---\nContent"}
        )
        assert result is None


def test_pre_tool_call_respects_yolo_mode(plugin_module):
    """YOLO mode should bypass all approvals"""
    with patch.dict(os.environ, {"HERMES_SKILL_APPROVAL_YOLO": "1"}):
        result = plugin_module.pre_tool_call(
            "skill_manage",
            {"action": "create", "name": "test", "content": "---\ndescription: test\n---\nContent"}
        )
        assert result is None


def test_pre_tool_call_respects_session_approval(plugin_module):
    """Session approval should allow subsequent skill creations"""
    with patch.dict(os.environ, {"HERMES_SESSION_KEY": "test-session"}):
        # Approve for session
        plugin_module._approve_session("test-session")

        # Should allow skill creation
        result = plugin_module.pre_tool_call(
            "skill_manage",
            {"action": "create", "name": "test", "content": "---\ndescription: test\n---\nContent"}
        )
        assert result is None


def test_pre_tool_call_respects_permanent_approval(plugin_module):
    """Permanent approval should always allow skill creation"""
    plugin_module._approve_permanent()

    result = plugin_module.pre_tool_call(
        "skill_manage",
        {"action": "create", "name": "test", "content": "---\ndescription: test\n---\nContent"}
    )
    assert result is None


def test_pre_tool_call_denies_in_non_interactive_mode(plugin_module):
    """Non-interactive mode should auto-deny (unless mode=auto)"""
    with patch.dict(os.environ, {
        "HERMES_SKILL_APPROVAL_MODE": "require",
        "HERMES_INTERACTIVE": "",  # Not interactive
    }, clear=True):
        with patch.object(plugin_module, "_prompt_skill_approval", return_value="deny"):
            result = plugin_module.pre_tool_call(
                "skill_manage",
                {"action": "create", "name": "test", "content": "---\ndescription: test\n---\nContent"}
            )

            assert result is not None
            assert result["block"] is True
            assert "denied" in result["result"]


def test_pre_tool_call_auto_approves_in_auto_mode(plugin_module):
    """Auto mode should auto-approve in non-interactive contexts"""
    with patch.dict(os.environ, {
        "HERMES_SKILL_APPROVAL_MODE": "auto",
        "HERMES_INTERACTIVE": "",  # Not interactive
    }, clear=True):
        result = plugin_module.pre_tool_call(
            "skill_manage",
            {"action": "create", "name": "test", "content": "---\ndescription: test\n---\nContent"}
        )
        assert result is None


def test_extract_skill_metadata(plugin_module):
    """Should correctly extract skill metadata from tool arguments"""
    tool_args = {
        "name": "my-skill",
        "category": "devops",
        "content": "---\nname: my-skill\ndescription: A test skill\n---\nContent here"
    }

    name, description, category = plugin_module._extract_skill_metadata(tool_args)

    assert name == "my-skill"
    assert description == "A test skill"
    assert category == "devops"


def test_extract_skill_metadata_without_category(plugin_module):
    """Should handle missing category"""
    tool_args = {
        "name": "my-skill",
        "content": "---\ndescription: test\n---\nContent"
    }

    name, description, category = plugin_module._extract_skill_metadata(tool_args)

    assert name == "my-skill"
    assert description == "test"
    assert category == ""


def test_extract_skill_metadata_without_description(plugin_module):
    """Should handle missing description"""
    tool_args = {
        "name": "my-skill",
        "content": "---\nname: my-skill\n---\nContent"
    }

    name, description, category = plugin_module._extract_skill_metadata(tool_args)

    assert name == "my-skill"
    assert description == ""


def test_prompt_skill_approval_once(plugin_module):
    """Test approval choice 'once'"""
    with patch.dict(os.environ, {"HERMES_INTERACTIVE": "1"}):
        with patch("builtins.input", return_value="o"):
            choice = plugin_module._prompt_skill_approval("test", "A test skill")
            assert choice == "once"


def test_prompt_skill_approval_session(plugin_module):
    """Test approval choice 'session'"""
    with patch.dict(os.environ, {"HERMES_INTERACTIVE": "1"}):
        with patch("builtins.input", return_value="s"):
            choice = plugin_module._prompt_skill_approval("test", "A test skill")
            assert choice == "session"


def test_prompt_skill_approval_always(plugin_module):
    """Test approval choice 'always'"""
    with patch.dict(os.environ, {"HERMES_INTERACTIVE": "1"}):
        with patch("builtins.input", return_value="a"):
            choice = plugin_module._prompt_skill_approval("test", "A test skill")
            assert choice == "always"


def test_prompt_skill_approval_deny(plugin_module):
    """Test approval choice 'deny' (default)"""
    with patch.dict(os.environ, {"HERMES_INTERACTIVE": "1"}):
        with patch("builtins.input", return_value=""):
            choice = plugin_module._prompt_skill_approval("test", "A test skill")
            assert choice == "deny"


def test_prompt_skill_approval_deny_on_keyboard_interrupt(plugin_module):
    """Test that KeyboardInterrupt results in denial"""
    with patch.dict(os.environ, {"HERMES_INTERACTIVE": "1"}):
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            choice = plugin_module._prompt_skill_approval("test", "A test skill")
            assert choice == "deny"


def test_plugin_registration():
    """Test that the plugin registers correctly"""
    from unittest.mock import MagicMock

    # Import plugin
    import sys
    from pathlib import Path
    plugin_path = Path(__file__).parent.parent.parent / "plugins" / "skill-approval"
    if str(plugin_path) not in sys.path:
        sys.path.insert(0, str(plugin_path))

    import __init__ as skill_approval_plugin

    # Mock context
    ctx = MagicMock()

    # Register
    skill_approval_plugin.register(ctx)

    # Verify hook was registered
    ctx.register_hook.assert_called_once()
    call_args = ctx.register_hook.call_args
    assert call_args[0][0] == "pre_tool_call"
    assert callable(call_args[0][1])
