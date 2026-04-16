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


def test_prompt_skill_approval_with_clarify_once(plugin_module):
    """Test approval with clarify callback - choice 'once'"""
    mock_callback = MagicMock(return_value="Once (approve this skill only)")
    choice = plugin_module._prompt_skill_approval("test", "A test skill", clarify_callback=mock_callback)
    assert choice == "once"
    mock_callback.assert_called_once()


def test_prompt_skill_approval_with_clarify_session(plugin_module):
    """Test approval with clarify callback - choice 'session'"""
    mock_callback = MagicMock(return_value="Session (approve all skills this session)")
    choice = plugin_module._prompt_skill_approval("test", "A test skill", clarify_callback=mock_callback)
    assert choice == "session"
    mock_callback.assert_called_once()


def test_prompt_skill_approval_with_clarify_always(plugin_module):
    """Test approval with clarify callback - choice 'always'"""
    mock_callback = MagicMock(return_value="Always (always approve skill creation)")
    choice = plugin_module._prompt_skill_approval("test", "A test skill", clarify_callback=mock_callback)
    assert choice == "always"
    mock_callback.assert_called_once()


def test_prompt_skill_approval_with_clarify_deny(plugin_module):
    """Test approval with clarify callback - choice 'deny'"""
    mock_callback = MagicMock(return_value="Deny (reject this skill creation)")
    choice = plugin_module._prompt_skill_approval("test", "A test skill", clarify_callback=mock_callback)
    assert choice == "deny"
    mock_callback.assert_called_once()


def test_prompt_skill_approval_with_clarify_index_response(plugin_module):
    """Test approval with clarify callback using numeric index"""
    # User selects option by index (0 = once, 1 = session, 2 = always, 3 = deny)
    mock_callback = MagicMock(return_value="1")  # Session
    choice = plugin_module._prompt_skill_approval("test", "A test skill", clarify_callback=mock_callback)
    assert choice == "session"


def test_prompt_skill_approval_with_clarify_fallback_on_error(plugin_module):
    """Test that plugin falls back to legacy prompt if clarify callback fails"""
    mock_callback = MagicMock(side_effect=Exception("Callback error"))
    with patch.dict(os.environ, {"HERMES_INTERACTIVE": "1"}):
        with patch("builtins.input", return_value="o"):
            choice = plugin_module._prompt_skill_approval("test", "A test skill", clarify_callback=mock_callback)
            assert choice == "once"


def test_prompt_skill_approval_with_clarify_includes_metadata(plugin_module):
    """Test that clarify callback receives skill metadata in the question"""
    mock_callback = MagicMock(return_value="once")
    plugin_module._prompt_skill_approval(
        "my-skill",
        "A comprehensive test skill",
        category="testing",
        clarify_callback=mock_callback
    )

    # Verify the callback was called with question containing metadata
    call_args = mock_callback.call_args
    question = call_args[0][0]
    assert "my-skill" in question
    assert "testing" in question
    assert "comprehensive test skill" in question or "A comprehensive test skill" in question


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
