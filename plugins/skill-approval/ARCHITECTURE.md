# Skill Approval Plugin - Architecture & Implementation

## Overview

This plugin implements a user approval workflow for skill creation in hermes-agent. It intercepts skill creation attempts via the `pre_tool_call` hook and prompts the user for approval before allowing the skill to be created.

## Problem Statement (需求)

**中文需求：** 当前 hermes-agent 自动创建技能时需要强制进行审批，需要进行人为确定是否同意创建。

**English:** When hermes-agent automatically creates skills, a mandatory approval process is required where a human must confirm whether to allow the creation.

## Solution

This plugin solves the problem by:

1. **Intercepting skill creation** via the `pre_tool_call` hook
2. **Prompting the user** for approval before creation proceeds
3. **Blocking unauthorized creation** if the user denies
4. **Supporting session-scoped approvals** to avoid repeated prompts

## Technical Architecture

### Integration Points

```
┌─────────────────────────────────────────────────────────────┐
│ Hermes-Agent Core (run_agent.py)                           │
│                                                             │
│  ┌────────────────────────────────────────────────────┐   │
│  │ Agent Loop                                         │   │
│  │  1. User message                                   │   │
│  │  2. LLM generates tool calls                       │   │
│  │  3. For each tool call:                            │   │
│  │     ┌─────────────────────────────────────┐       │   │
│  │     │ invoke_hook("pre_tool_call")        │       │   │
│  │     │   ↓                                  │       │   │
│  │     │ Plugin checks if skill creation     │       │   │
│  │     │   ↓                                  │       │   │
│  │     │ Prompt user (if needed)             │       │   │
│  │     │   ↓                                  │       │   │
│  │     │ Return block=True (deny) or None    │       │   │
│  │     └─────────────────────────────────────┘       │   │
│  │  4. Execute tool (if not blocked)                 │   │
│  │  5. Return result to LLM                          │   │
│  └────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Hook Mechanism

The plugin uses the **`pre_tool_call`** hook defined in `hermes_cli/plugins.py`:

```python
# Valid hooks in hermes-agent
VALID_HOOKS = {
    "pre_tool_call",     # ← Used by this plugin
    "post_tool_call",
    "pre_llm_call",
    "post_llm_call",
    "pre_api_request",
    "post_api_request",
    "on_session_start",
    "on_session_end",
    "on_session_finalize",
    "on_session_reset",
}
```

When a tool is about to be executed, the plugin manager calls all registered `pre_tool_call` hooks:

```python
# In model_tools.py or similar
results = invoke_hook("pre_tool_call",
                     tool_name=tool_name,
                     tool_args=args,
                     task_id=task_id)

for result in results:
    if result and result.get("block"):
        # Plugin blocked this tool call
        return result["result"]  # Return error to agent
```

### Plugin Discovery

Plugins are discovered from three locations (in order):

1. **User plugins**: `~/.hermes/plugins/skill-approval/`
2. **Project plugins**: `./.hermes/plugins/skill-approval/` (if enabled)
3. **Bundled plugins**: `plugins/skill-approval/` (this plugin)

The plugin system automatically loads any plugin with:
- A `plugin.yaml` manifest
- An `__init__.py` with a `register(ctx)` function

### Approval State Management

The plugin maintains approval state in memory using thread-safe data structures:

```python
_lock = threading.Lock()
_session_approved_skills: Dict[str, bool] = {}  # session → approved
_permanent_approval: bool = False

def _is_session_approved(session_key: str) -> bool:
    with _lock:
        return _session_approved_skills.get(session_key, False) or _permanent_approval
```

This design:
- **Thread-safe**: Works with concurrent gateway sessions
- **Session-scoped**: Each session tracked independently
- **Permanent bypass**: Global approval flag for trusted environments

## Code Flow

### 1. Plugin Registration

```python
# In __init__.py
def register(ctx):
    ctx.register_hook("pre_tool_call", pre_tool_call)
```

### 2. Hook Invocation

```python
def pre_tool_call(tool_name: str, tool_args: dict, **kwargs) -> Optional[Dict]:
    # Only intercept skill_manage with action='create'
    if tool_name != "skill_manage":
        return None

    if tool_args.get("action") != "create":
        return None

    # Check approval mode and session state
    # ...

    # Prompt user
    choice = _prompt_skill_approval(name, description, category)

    if choice == "deny":
        return {
            "block": True,
            "result": json.dumps({"success": False, "error": "..."})
        }

    # Update approval state
    if choice == "session":
        _approve_session(session_key)
    elif choice == "always":
        _approve_permanent()

    return None  # Allow tool to proceed
```

### 3. User Prompt (CLI)

```python
def _prompt_skill_approval(skill_name: str, description: str, category: str):
    print(f"📚 SKILL CREATION REQUEST")
    print(f"    Name: {skill_name}")
    print(f"    Category: {category}")
    print(f"    Description: {description}")
    print()
    print("    [o]nce  |  [s]ession  |  [a]lways  |  [d]eny")

    choice = input("    Choice [o/s/a/D]: ").strip().lower()

    if choice in ('o', 'once'):
        return "once"
    elif choice in ('s', 'session'):
        return "session"
    elif choice in ('a', 'always'):
        return "always"
    else:
        return "deny"
```

## Comparison with Existing Approval System

The skill approval plugin follows the same patterns as the dangerous command approval system in `tools/approval.py`:

| Feature | Dangerous Commands | Skill Approval |
|---------|-------------------|----------------|
| Hook Used | `pre_tool_call` (terminal) | `pre_tool_call` (skill_manage) |
| Approval Scopes | once/session/always | once/session/always |
| CLI Support | ✓ Interactive prompts | ✓ Interactive prompts |
| Gateway Support | ✓ Async blocking queue | ⚠️ Planned (not implemented) |
| Persistence | Config YAML allowlist | In-memory only |
| YOLO Bypass | `HERMES_YOLO_MODE` | `HERMES_SKILL_APPROVAL_YOLO` |

## Configuration

### Environment Variables

```bash
# Control approval mode
HERMES_SKILL_APPROVAL_MODE=require  # require (default), off, auto

# Bypass all approvals (debug mode)
HERMES_SKILL_APPROVAL_YOLO=1

# Session tracking (inherited from core)
HERMES_SESSION_KEY=my-session-id

# Interactive mode (inherited from core)
HERMES_INTERACTIVE=1
```

### Plugin Disable

```yaml
# ~/.hermes/config.yaml
plugins:
  disabled:
    - skill-approval
```

## Future Enhancements

### 1. Gateway Async Approval

Implement blocking approval for messaging platforms, similar to `tools/approval.py` lines 220-273:

```python
# Register gateway callback
def register_gateway_notify(session_key: str, cb):
    _gateway_notify_cbs[session_key] = cb

# Block until user responds via /approve-skill or /deny-skill
entry = _ApprovalEntry(approval_data)
_gateway_queues.setdefault(session_key, []).append(entry)
notify_cb(approval_data)
entry.event.wait(timeout=300)
```

### 2. Persistent Approvals

Store permanent approvals in config:

```yaml
# ~/.hermes/config.yaml
skill_approval:
  permanent: true
  # or
  allowed_patterns:
    - "devops/*"
    - "automation/*"
```

### 3. Approval Policies

Add pattern-based auto-approval:

```python
APPROVAL_POLICIES = {
    "category:personal": "auto",    # Auto-approve personal category
    "name:test-*": "auto",          # Auto-approve test skills
    "description:*experimental*": "prompt",  # Always prompt for experimental
}
```

### 4. Audit Log

Track all approval decisions:

```python
# ~/.hermes/skill_approval_audit.log
2026-04-16 03:15:23 | APPROVED (session) | postgresql-replication | databases
2026-04-16 03:18:45 | DENIED             | experimental-hack      | testing
2026-04-16 03:22:10 | APPROVED (always)  | docker-compose         | devops
```

## Testing

### Unit Tests

Located in `tests/plugins/test_skill_approval.py`:
- Test approval modes (off, auto, require)
- Test bypass mechanisms (YOLO, session, permanent)
- Test metadata extraction
- Test plugin registration

### Integration Tests

Located in `plugins/skill-approval/test_integration.py`:
- Test end-to-end approval workflow
- Test different approval scenarios
- Test configuration options

Run with:
```bash
cd plugins/skill-approval
python3 test_integration.py
```

### Manual Testing

```bash
# Test CLI approval
hermes chat
> Create a skill for managing Docker containers

# Test session approval
hermes chat
> Create several skills for the deployment process
[Choose 's' for session approval]

# Test denial
hermes chat
> Create a test skill
[Choose 'd' to deny]
```

## Security Considerations

1. **No bypass via tool parameters**: The hook intercepts *before* the tool executes, so malicious tool parameters cannot bypass the approval
2. **Thread-safe state**: Concurrent gateway sessions don't interfere with each other
3. **Default deny**: Non-interactive contexts default to denial unless explicitly configured with `mode=auto`
4. **Audit trail**: All approval decisions are logged (when audit logging is enabled)

## Performance Impact

- **Negligible overhead**: Hook only executes for `skill_manage` calls (rare)
- **No network calls**: All approval logic is local
- **Minimal memory**: Approval state is a small in-memory dict
- **No file I/O**: No persistent storage (yet)

## Compatibility

- **Python**: 3.8+
- **Hermes-Agent**: 0.8.0+
- **Platforms**: CLI (full support), Gateway (planned)

## License

Same as hermes-agent (MIT)
