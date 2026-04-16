#!/usr/bin/env python3
"""Manual integration test for skill-approval plugin

This script tests the skill approval plugin by simulating skill creation
attempts and verifying the approval workflow.

Usage:
    python test_integration.py

The test will:
1. Load the plugin
2. Simulate skill creation attempts
3. Test different approval scenarios
4. Print results
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add plugin to path
plugin_path = Path(__file__).parent
if str(plugin_path) not in sys.path:
    sys.path.insert(0, str(plugin_path))

# Import the plugin
try:
    import __init__ as skill_approval
except ImportError as e:
    print(f"Error importing plugin: {e}")
    sys.exit(1)


def test_scenario(name, setup_fn, test_fn):
    """Run a test scenario"""
    print(f"\n{'='*60}")
    print(f"Test: {name}")
    print('='*60)

    try:
        setup_fn()
        result = test_fn()
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
        return result
    except Exception as e:
        print(f"✗ ERROR: {name}")
        print(f"  Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_1_non_skill_tools():
    """Test that non-skill_manage tools pass through"""
    def setup():
        pass

    def test():
        result = skill_approval.pre_tool_call("terminal", {"command": "ls"})
        success = result is None
        print(f"  Non-skill tool passed through: {success}")
        return success

    return test_scenario("Non-skill tools pass through", setup, test)


def test_2_non_create_actions():
    """Test that non-create actions pass through"""
    def setup():
        pass

    def test():
        result = skill_approval.pre_tool_call(
            "skill_manage",
            {"action": "edit", "name": "test"}
        )
        success = result is None
        print(f"  Edit action passed through: {success}")
        return success

    return test_scenario("Non-create actions pass through", setup, test)


def test_3_off_mode():
    """Test that mode=off allows all skill creation"""
    def setup():
        os.environ["HERMES_SKILL_APPROVAL_MODE"] = "off"

    def test():
        result = skill_approval.pre_tool_call(
            "skill_manage",
            {
                "action": "create",
                "name": "test-skill",
                "content": "---\ndescription: test\n---\nContent"
            }
        )
        success = result is None
        print(f"  Mode=off allows creation: {success}")
        return success

    return test_scenario("Mode=off allows creation", setup, test)


def test_4_yolo_mode():
    """Test that YOLO mode bypasses approval"""
    def setup():
        os.environ["HERMES_SKILL_APPROVAL_YOLO"] = "1"
        os.environ.pop("HERMES_SKILL_APPROVAL_MODE", None)

    def test():
        result = skill_approval.pre_tool_call(
            "skill_manage",
            {
                "action": "create",
                "name": "test-skill",
                "content": "---\ndescription: test\n---\nContent"
            }
        )
        success = result is None
        print(f"  YOLO mode bypasses approval: {success}")
        return success

    return test_scenario("YOLO mode bypass", setup, test)


def test_5_session_approval():
    """Test session-scoped approval"""
    def setup():
        os.environ.pop("HERMES_SKILL_APPROVAL_YOLO", None)
        os.environ["HERMES_SKILL_APPROVAL_MODE"] = "require"
        os.environ["HERMES_SESSION_KEY"] = "test-session-123"
        skill_approval._session_approved_skills.clear()

    def test():
        # Approve for session
        skill_approval._approve_session("test-session-123")

        # Test that skill creation is allowed
        result = skill_approval.pre_tool_call(
            "skill_manage",
            {
                "action": "create",
                "name": "test-skill",
                "content": "---\ndescription: test\n---\nContent"
            }
        )
        success = result is None
        print(f"  Session approval allows creation: {success}")
        return success

    return test_scenario("Session-scoped approval", setup, test)


def test_6_permanent_approval():
    """Test permanent approval"""
    def setup():
        os.environ.pop("HERMES_SKILL_APPROVAL_YOLO", None)
        os.environ["HERMES_SKILL_APPROVAL_MODE"] = "require"
        os.environ["HERMES_SESSION_KEY"] = "test-session-456"
        skill_approval._session_approved_skills.clear()
        # Reset permanent approval
        skill_approval._permanent_approval = False

    def test():
        # Set permanent approval
        skill_approval._approve_permanent()

        # Test that skill creation is allowed
        result = skill_approval.pre_tool_call(
            "skill_manage",
            {
                "action": "create",
                "name": "test-skill",
                "content": "---\ndescription: test\n---\nContent"
            }
        )
        success = result is None
        print(f"  Permanent approval allows creation: {success}")
        return success

    return test_scenario("Permanent approval", setup, test)


def test_7_auto_mode():
    """Test auto mode in non-interactive context"""
    def setup():
        os.environ["HERMES_SKILL_APPROVAL_MODE"] = "auto"
        os.environ.pop("HERMES_INTERACTIVE", None)
        os.environ.pop("HERMES_SKILL_APPROVAL_YOLO", None)
        skill_approval._session_approved_skills.clear()
        skill_approval._permanent_approval = False

    def test():
        result = skill_approval.pre_tool_call(
            "skill_manage",
            {
                "action": "create",
                "name": "test-skill",
                "content": "---\ndescription: test\n---\nContent"
            }
        )
        success = result is None
        print(f"  Auto mode allows non-interactive creation: {success}")
        return success

    return test_scenario("Auto mode non-interactive", setup, test)


def test_8_metadata_extraction():
    """Test skill metadata extraction"""
    def setup():
        pass

    def test():
        tool_args = {
            "name": "my-test-skill",
            "category": "testing",
            "content": "---\nname: my-test-skill\ndescription: A comprehensive test skill\n---\nContent here"
        }

        name, description, category = skill_approval._extract_skill_metadata(tool_args)

        success = (
            name == "my-test-skill" and
            description == "A comprehensive test skill" and
            category == "testing"
        )
        print(f"  Extracted name: {name}")
        print(f"  Extracted description: {description}")
        print(f"  Extracted category: {category}")
        print(f"  Metadata extraction correct: {success}")
        return success

    return test_scenario("Metadata extraction", setup, test)


def test_9_plugin_registration():
    """Test plugin registration"""
    def setup():
        pass

    def test():
        # Mock context
        ctx = MagicMock()

        # Register plugin
        skill_approval.register(ctx)

        # Verify hook was registered
        success = ctx.register_hook.called
        if success:
            call_args = ctx.register_hook.call_args[0]
            hook_name = call_args[0]
            hook_fn = call_args[1]
            print(f"  Hook registered: {hook_name}")
            print(f"  Hook callable: {callable(hook_fn)}")
            success = hook_name == "pre_tool_call" and callable(hook_fn)

        return success

    return test_scenario("Plugin registration", setup, test)


def main():
    """Run all integration tests"""
    print("="*60)
    print("Skill Approval Plugin - Integration Tests")
    print("="*60)

    tests = [
        test_1_non_skill_tools,
        test_2_non_create_actions,
        test_3_off_mode,
        test_4_yolo_mode,
        test_5_session_approval,
        test_6_permanent_approval,
        test_7_auto_mode,
        test_8_metadata_extraction,
        test_9_plugin_registration,
    ]

    results = [test() for test in tests]

    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")

    if passed == total:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
