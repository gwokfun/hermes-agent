# Skill Approval Plugin

**需求实现说明：** 本插件满足需求 - 当 hermes-agent 自动创建技能时强制进行审批，需要人为确定是否同意创建。插件已集成 Hermes 自带的 `clarify` 审批工具，提供统一的交互界面。

## Overview

This plugin adds a user approval step before the agent creates new skills. When the agent attempts to create a skill using `skill_manage(action='create')`, the user will be prompted to approve or deny the creation using Hermes' built-in `clarify` tool.

## Features

- ✅ **Interactive Approval**: User must explicitly approve skill creation
- ✅ **Clarify Integration**: Uses Hermes' built-in `clarify` tool for consistent UX
- ✅ **Session-scoped Approvals**: Approve once for the entire conversation
- ✅ **Permanent Approvals**: Always approve skill creation (bypass future prompts)
- ✅ **Configurable**: Can be disabled or set to auto-approve mode
- ✅ **CLI Support**: Interactive prompts in terminal via clarify callback
- ✅ **Gateway Support**: Works with messaging platforms that support clarify
- ✅ **Fallback**: Legacy direct prompt support for environments without clarify

## Installation

This plugin is bundled with hermes-agent and located in `plugins/skill-approval/`.

To enable the plugin, it will be automatically discovered from the `plugins/` directory.

To disable the plugin, add it to the disabled list in your `~/.hermes/config.yaml`:

```yaml
plugins:
  disabled:
    - skill-approval
```

## Usage

When enabled, the plugin intercepts all skill creation attempts. The user will see a clarify-powered prompt like:

```
📚 Skill creation request: 'my-new-skill' (category: devops)

Description: A skill for managing Docker containers

Allow the agent to create this skill?

1. Once (approve this skill only)
2. Session (approve all skills this session)
3. Always (always approve skill creation)
4. Deny (reject this skill creation)
5. Other (type your answer)
```

The clarify tool provides an interactive selection interface:
- **CLI**: Arrow keys to navigate, Enter to select, or type a custom response
- **Gateway**: Numbered list for easy selection in messaging apps

If the clarify callback is not available, the plugin falls back to a legacy direct input prompt.

### Approval Options

- **[o]nce**: Allow this skill creation only (prompt again for the next skill)
- **[s]ession**: Allow all skill creations in this session (no more prompts until restart)
- **[a]lways**: Permanently allow skill creation (stored in memory, persists across sessions)
- **[d]eny**: Block this skill creation (agent will receive an error)

## Configuration

### Environment Variables

- `HERMES_SKILL_APPROVAL_MODE`: Control approval behavior
  - `require` (default): Always prompt for approval
  - `off`: Disable approval, allow all skill creation
  - `auto`: Auto-approve in non-interactive contexts

- `HERMES_SKILL_APPROVAL_YOLO`: Set to `"1"` to bypass all approvals (debug mode)

### Examples

Disable skill approval for a single session:
```bash
export HERMES_SKILL_APPROVAL_MODE=off
hermes chat
```

Auto-approve in scripts/automation:
```bash
export HERMES_SKILL_APPROVAL_MODE=auto
hermes chat --non-interactive
```

Debug mode (bypass all prompts):
```bash
export HERMES_SKILL_APPROVAL_YOLO=1
hermes chat
```

## How It Works

1. Plugin registers a `pre_tool_call` hook during initialization
2. Hook intercepts all `skill_manage` tool calls with `action="create"`
3. Extracts skill metadata (name, description, category) from the arguments
4. Prompts the user for approval
5. If approved, allows the tool to proceed
6. If denied, blocks the tool and returns an error to the agent

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│ Agent attempts: skill_manage(action='create', ...)     │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
         ┌────────────────────────────┐
         │ Plugin pre_tool_call Hook │
         └────────────┬───────────────┘
                      │
                      ▼
         ┌────────────────────────────┐
         │ Check Approval Status      │
         │ - Mode (require/off/auto)  │
         │ - YOLO bypass              │
         │ - Session approved         │
         │ - Permanent approved       │
         └────────────┬───────────────┘
                      │
           ┌──────────┴──────────┐
           │                     │
    Already approved      Need approval
           │                     │
           ▼                     ▼
    Allow execution    ┌─────────────────┐
                      │ Prompt User      │
                      │ [o/s/a/d]        │
                      └────────┬─────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
                 Approved               Denied
                    │                     │
                    ▼                     ▼
             Allow execution      Block execution
                                  Return error
```

## Development

### Testing the Plugin

1. Create a test scenario:
```bash
hermes chat
> Please create a new skill for managing Kubernetes pods
```

2. You should see the approval prompt before the skill is created

3. Test different approval modes:
```bash
# Test denial
> Please create a skill
[d]eny  # Agent should receive error

# Test session approval
> Please create another skill
[s]ession  # This skill approved
> And another one
# No prompt (session approved)
```

### Adding Gateway Support

To add async approval for messaging platforms (Telegram, Discord, etc.), implement:

1. Gateway notification callback (similar to `tools/approval.py` dangerous command approval)
2. Blocking queue mechanism for async approval responses
3. Gateway commands (`/approve-skill`, `/deny-skill`)

See `tools/approval.py` lines 220-273 for reference implementation.

## Limitations

- Gateway async approval not yet implemented (denies by default in gateway mode)
- Non-interactive contexts auto-deny unless mode is set to "auto"
- Permanent approval is stored in memory only (not persisted to config)

## Future Enhancements

- [ ] Gateway async approval support
- [ ] Persist permanent approvals to config
- [ ] Approval history/audit log
- [ ] Skill pattern-based auto-approval (e.g., always approve skills in "personal/" category)
- [ ] Integration with skill security scanning results
- [ ] Approval timeout configuration

## Troubleshooting

### Plugin not loading

Check if the plugin is disabled:
```bash
hermes plugins list
```

Enable it in `~/.hermes/config.yaml` by removing from the `disabled` list.

### No approval prompt shown

Check the approval mode:
```bash
echo $HERMES_SKILL_APPROVAL_MODE
```

Should be `require` or empty. If set to `off`, approvals are disabled.

### Auto-denied in gateway

Gateway async approval is not yet implemented. Skills will be auto-denied in messaging platforms. Use CLI mode for now.

## License

Same as hermes-agent (MIT)

## Contributing

To contribute improvements to this plugin:

1. Test thoroughly in both CLI and gateway modes
2. Add tests to `tests/plugins/test_skill_approval.py`
3. Update this README with any new features or configuration options
4. Submit a pull request

## Author

Hermes Team
