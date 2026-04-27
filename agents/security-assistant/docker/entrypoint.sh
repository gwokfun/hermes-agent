#!/bin/bash
# SecHermes Docker entrypoint
# Bootstraps config, skills, and OpenViking integration into the data volume.
set -e

HERMES_HOME="${HERMES_HOME:-/opt/data}"
INSTALL_DIR="/opt/hermes"
SKILLS_DIR="/opt/sechermes-skills"
VENV_DIR="/opt/venv"

# Activate virtualenv
source "${VENV_DIR}/bin/activate"

# ---------------------------------------------------------------------------
# 1. Create essential directories
# ---------------------------------------------------------------------------
mkdir -p "$HERMES_HOME"/{sessions,logs,memories,skills,skins,workspace}

# ---------------------------------------------------------------------------
# 2. .env — merge from environment variables if .env doesn't exist
# ---------------------------------------------------------------------------
if [ ! -f "$HERMES_HOME/.env" ]; then
    echo "# SecHermes environment — auto-generated" > "$HERMES_HOME/.env"
    echo "# Edit this file or pass variables via docker run --env" >> "$HERMES_HOME/.env"
    echo "" >> "$HERMES_HOME/.env"

    # Forward LLM keys if set in container env
    for var in ANTHROPIC_API_KEY OPENROUTER_API_KEY OPENAI_API_KEY GOOGLE_API_KEY; do
        if [ -n "${!var}" ]; then
            echo "${var}=${!var}" >> "$HERMES_HOME/.env"
        fi
    done

    # Forward OpenViking vars
    for var in OPENVIKING_ENDPOINT OPENVIKING_API_KEY OPENVIKING_ACCOUNT OPENVIKING_USER OPENVIKING_AGENT OPENVIKING_EMBEDDING_MODEL OPENVIKING_EMBEDDING_DEVICE OPENVIKING_VLM_MODEL OPENVIKING_VLM_DEVICE; do
        if [ -n "${!var}" ]; then
            echo "${var}=${!var}" >> "$HERMES_HOME/.env"
        fi
    done

    # Forward tool/service keys
    for var in NVD_API_KEY APPROVAL_API_URL APPROVAL_API_TOKEN TELEGRAM_BOT_TOKEN TELEGRAM_ALLOWED_USERS DISCORD_BOT_TOKEN SLACK_BOT_TOKEN SLACK_APP_TOKEN EXA_API_KEY PARALLEL_API_KEY FIRECRAWL_API_KEY; do
        if [ -n "${!var}" ]; then
            echo "${var}=${!var}" >> "$HERMES_HOME/.env"
        fi
    done

    echo "✓ Created $HERMES_HOME/.env"
fi

# ---------------------------------------------------------------------------
# 3. config.yaml — SecHermes config with OpenViking memory
# ---------------------------------------------------------------------------
if [ ! -f "$HERMES_HOME/config.yaml" ]; then
    cat > "$HERMES_HOME/config.yaml" <<'YAML'
# SecHermes Configuration (auto-generated)
# Modify as needed. Re-created only on first run.

model:
  default: "anthropic/claude-sonnet-4-20250514"

agent:
  max_iterations: 30
  auto_skill_creation: false

memory:
  provider: openviking

security:
  docs_base_path: "/opt/sec-docs"
  approval_required: true

display:
  tool_progress: true
  skin: "slate"

tools:
  enabled:
    - terminal
    - file
    - web
    - mcp
  disabled:
    - browser
    - code_execution

mcp:
  servers: []
YAML
    echo "✓ Created $HERMES_HOME/config.yaml"
fi

# ---------------------------------------------------------------------------
# 4. SOUL.md — SecHermes personality
# ---------------------------------------------------------------------------
SOUL_FILE="${SECHERMES_SOUL_FILE:-${INSTALL_DIR}/agents/security-assistant/SOUL.md}"
if [ ! -f "$HERMES_HOME/SOUL.md" ] && [ -f "$SOUL_FILE" ]; then
    cp "$SOUL_FILE" "$HERMES_HOME/SOUL.md"
    echo "✓ Copied SOUL.md"
fi

# ---------------------------------------------------------------------------
# 5. Install bundled security skills (idempotent — won't overwrite user edits)
# ---------------------------------------------------------------------------
if [ -d "$SKILLS_DIR" ]; then
    for skill in "$SKILLS_DIR"/*/; do
        skill_name=$(basename "$skill")
        target="$HERMES_HOME/skills/$skill_name"
        if [ ! -d "$target" ]; then
            cp -r "$skill" "$target"
            echo "✓ Installed skill: $skill_name"
        fi
    done
fi

# ---------------------------------------------------------------------------
# 6. Wait for OpenViking (if configured)
# ---------------------------------------------------------------------------
if [ -n "$OPENVIKING_ENDPOINT" ] && [ "$OPENVIKING_ENDPOINT" != "disabled" ]; then
    echo "⏳ Waiting for OpenViking at $OPENVIKING_ENDPOINT ..."
    retries=0
    max_retries=${OPENVIKING_WAIT_RETRIES:-30}
    until curl -sf "${OPENVIKING_ENDPOINT}/health" > /dev/null 2>&1; do
        retries=$((retries + 1))
        if [ $retries -ge $max_retries ]; then
            echo "⚠  OpenViking not available after ${max_retries}s — starting without memory"
            break
        fi
        sleep 1
    done
    if [ $retries -lt $max_retries ]; then
        echo "✓ OpenViking is ready"
    fi
fi

# ---------------------------------------------------------------------------
# 7. Start hermes
# ---------------------------------------------------------------------------
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  SecHermes — Security Assistant Agent"
echo "  Memory: OpenViking (${OPENVIKING_ENDPOINT:-disabled})"
echo "  Data:   ${HERMES_HOME}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

exec hermes "$@"
