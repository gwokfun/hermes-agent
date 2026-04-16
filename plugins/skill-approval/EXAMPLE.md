# Skill Approval Plugin - Usage Examples

This document provides practical examples of how the skill approval plugin works in different scenarios.

## Example 1: Basic Skill Creation with Approval

### Scenario
User asks the agent to create a new skill based on a successful task.

### Conversation Flow

```
User: I just successfully set up a PostgreSQL database with replication.
      Can you create a skill to remember how to do this?

Agent: I'll create a skill to capture the PostgreSQL replication setup process.
       [Calls skill_manage(action='create', name='postgresql-replication', ...)]

📚 SKILL CREATION REQUEST
    Name: postgresql-replication
    Category: databases
    Description: Set up PostgreSQL with streaming replication for high availability

    Allow the agent to create this skill?
    [o]nce  |  [s]ession  |  [a]lways  |  [d]eny

    Choice [o/s/a/D]: o

    ✓ Skill creation allowed once

Agent: Skill 'postgresql-replication' created successfully at ~/.hermes/skills/databases/postgresql-replication/
```

## Example 2: Session Approval for Multiple Skills

### Scenario
User is working on multiple related tasks and wants to create several skills.

### Conversation Flow

```
User: Let's create skills for all the deployment steps we just completed.

Agent: I'll create a skill for the Docker containerization process.
       [Calls skill_manage(action='create', name='docker-multiservice', ...)]

📚 SKILL CREATION REQUEST
    Name: docker-multiservice
    Category: devops
    Description: Containerize multiple services with Docker Compose

    Allow the agent to create this skill?
    [o]nce  |  [s]ession  |  [a]lways  |  [d]eny

    Choice [o/s/a/D]: s

    ✓ Skill creation allowed for this session

Agent: Skill 'docker-multiservice' created.

Agent: Now creating a skill for the CI/CD pipeline setup...
       [Calls skill_manage(action='create', name='github-actions-deploy', ...)]

       [No prompt - session approved]

Agent: Skill 'github-actions-deploy' created.

Agent: Creating a skill for the monitoring setup...
       [Calls skill_manage(action='create', name='prometheus-grafana', ...)]

       [No prompt - session approved]

Agent: Skill 'prometheus-grafana' created.
```

## Example 3: Denying Skill Creation

### Scenario
User doesn't want the agent to create a skill for a one-off task.

### Conversation Flow

```
User: Can you help me debug this Python script?

Agent: [After successful debugging]
       I've fixed the issue. Would you like me to create a skill for debugging
       similar Python issues?

User: Sure, create a skill.

Agent: [Calls skill_manage(action='create', name='python-debug-common', ...)]

📚 SKILL CREATION REQUEST
    Name: python-debug-common
    Description: Common Python debugging techniques for TypeError and AttributeError

    Allow the agent to create this skill?
    [o]nce  |  [s]ession  |  [a]lways  |  [d]eny

    Choice [o/s/a/D]: d

    ✗ Skill creation denied

Agent: Understood. I won't create the debugging skill. The fix has been applied
       to your script, and you can refer to it directly if needed.
```

## Example 4: Permanent Approval

### Scenario
User trusts the agent completely and wants to always allow skill creation.

### Conversation Flow

```
User: I want you to create skills whenever you think it's useful.

Agent: [Later, after completing a complex task]
       I'll create a skill for this Kubernetes deployment pattern.
       [Calls skill_manage(action='create', name='k8s-blue-green', ...)]

📚 SKILL CREATION REQUEST
    Name: k8s-blue-green
    Category: devops
    Description: Blue-green deployment strategy for Kubernetes

    Allow the agent to create this skill?
    [o]nce  |  [s]ession  |  [a]lways  |  [d]eny

    Choice [o/s/a/D]: a

    ✓ Skill creation always allowed

Agent: Skill 'k8s-blue-green' created.

[In a different session, days later]

User: Can you create a skill for that API integration we just built?

Agent: [Calls skill_manage(action='create', name='stripe-webhook', ...)]
       [No prompt - permanent approval active]

Agent: Skill 'stripe-webhook' created successfully.
```

## Example 5: Disabling Approval for Automation

### Scenario
Running hermes in a script/automation context where prompts aren't possible.

### Setup

```bash
#!/bin/bash
# automation-script.sh

export HERMES_SKILL_APPROVAL_MODE=auto

hermes chat << EOF
Create skills for all the steps in the deployment guide at docs/deployment.md
EOF
```

### Behavior
- Skills are auto-approved since we're in non-interactive mode with `mode=auto`
- No prompts are shown
- All skills are created automatically

## Example 6: Debugging with YOLO Mode

### Scenario
Developer is testing skill creation logic and wants to bypass approvals.

### Setup

```bash
export HERMES_SKILL_APPROVAL_YOLO=1
hermes chat
```

### Conversation Flow

```
User: Create 10 test skills.

Agent: [Creates all 10 skills without any approval prompts]

Agent: Created 10 skills:
       - test-skill-1
       - test-skill-2
       ...
       - test-skill-10
```

## Example 7: Category-Based Organization

### Scenario
User wants to organize skills by domain.

### Conversation Flow

```
User: Create a skill for managing AWS EC2 instances in the 'cloud' category.

Agent: [Calls skill_manage(action='create', name='aws-ec2-management',
                          category='cloud', ...)]

📚 SKILL CREATION REQUEST
    Name: aws-ec2-management
    Category: cloud
    Description: Common EC2 instance management tasks (launch, configure, monitor)

    Allow the agent to create this skill?
    [o]nce  |  [s]ession  |  [a]lways  |  [d]eny

    Choice [o/s/a/D]: o

    ✓ Skill creation allowed once

Agent: Skill created at ~/.hermes/skills/cloud/aws-ec2-management/
```

## Configuration Examples

### Disable Approval Globally

Add to `~/.hermes/config.yaml`:

```yaml
plugins:
  disabled:
    - skill-approval
```

### Disable Approval via Environment

```bash
export HERMES_SKILL_APPROVAL_MODE=off
hermes chat
```

### Auto-Approve in CI/CD

```yaml
# .github/workflows/hermes.yml
jobs:
  run-hermes:
    steps:
      - name: Run Hermes Agent
        env:
          HERMES_SKILL_APPROVAL_MODE: auto
        run: |
          hermes chat --task "Analyze codebase and create relevant skills"
```

## Best Practices

1. **Use session approval** when creating multiple related skills in one session
2. **Use once approval** for experimental or one-off skills
3. **Use permanent approval** only if you fully trust the agent's judgment
4. **Review denied skills** - the agent will explain what it tried to create
5. **Use auto mode** in automation/CI contexts where interaction isn't possible
6. **Keep approval enabled** by default for safety and oversight

## Troubleshooting

### Plugin Not Working

Check if the plugin is loaded:
```bash
hermes chat
> /plugins list
```

Should show `skill-approval` in the loaded plugins list.

### No Prompt Appearing

Verify interactive mode:
```bash
# This should show a prompt
HERMES_INTERACTIVE=1 hermes chat

# This won't (auto-denies by default)
hermes chat --non-interactive
```

### Gateway Auto-Denying

Gateway async approval is not yet implemented. Use CLI mode for now, or disable the plugin for gateway usage:

```yaml
# config.yaml
plugins:
  disabled:
    - skill-approval
```

Or set auto mode for gateway:
```bash
export HERMES_SKILL_APPROVAL_MODE=auto
hermes gateway run
```
