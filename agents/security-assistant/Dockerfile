# =============================================================================
# SecHermes — Lightweight Security Assistant Docker Image
# =============================================================================
# A minimal image for the security assistant agent, integrating:
#   - hermes-agent core (CLI + gateway)
#   - OpenViking memory plugin (httpx)
#   - MCP client (for vuln-scanner, approval-api, etc.)
#   - Security skills (vuln-scan, sec-docs-qa, sec-auto-fix, sec-intel)
#
# Stripped compared to root Dockerfile:
#   ✗ Playwright / browser automation (~400MB)
#   ✗ WhatsApp bridge / Node.js (~200MB)
#   ✗ Voice / TTS / STT
#   ✗ RL training (atropos/tinker)
#   ✗ Matrix messaging
#   ✗ gosu privilege helper
#   ✗ build-essential / gcc / python3-dev (not needed at runtime)
#
# Build:
#   docker build -t sechermes -f agents/security-assistant/Dockerfile .
#
# Run:
#   docker run --env-file agents/security-assistant/.env.sechermes \
#     -v sechermes-data:/opt/data sechermes
# =============================================================================

# syntax=docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:0.11.6-python3.13-trixie@sha256:b3c543b6c4f23a5f2df22866bd7857e5d304b67a564f4feab6ac22044dde719b AS uv_source

# ---------------------------------------------------------------------------
# Stage 1: Builder — install Python deps in an isolated venv
# ---------------------------------------------------------------------------
FROM python:3.13-slim-trixie AS builder

COPY --chmod=0755 --from=uv_source /usr/local/bin/uv /usr/local/bin/

# Build tools needed for some wheels (e.g. cffi for PyJWT[crypto])
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential gcc libffi-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy hermes-agent source
# Note: agents/security-assistant/Dockerfile.dockerignore ensures .md files
# (SOUL.md, AGENT.md, SKILL.md) are included — unlike the root .dockerignore
COPY . /opt/hermes
WORKDIR /opt/hermes

# Install hermes-agent and dependencies into venv
#   mcp          — MCP client for vuln-scanner, approval-api
#   messaging    — telegram/discord/slack gateway
#   cron         — scheduled security scans
#   pty          — better terminal tool support
# httpx is already a core dep but we ensure it's present for OpenViking
RUN uv venv /opt/venv && \
    VIRTUAL_ENV=/opt/venv uv pip install --no-cache-dir \
        -e ".[mcp,messaging,cron,pty]"

# ---------------------------------------------------------------------------
# Stage 2: Runtime — minimal final image
# ---------------------------------------------------------------------------
FROM python:3.13-slim-trixie

LABEL maintainer="SecHermes" \
      description="Lightweight security assistant — hermes-agent + OpenViking"

# Disable Python stdout buffering
ENV PYTHONUNBUFFERED=1

# Only essential runtime packages (no build-essential, no nodejs, no npm)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ripgrep \
        git \
        curl \
        procps && \
    rm -rf /var/lib/apt/lists/*

# Non-root runtime user
RUN useradd -u 10000 -m -d /opt/data sechermes

# Copy pre-built venv and source from builder
COPY --chown=sechermes:sechermes --from=builder /opt/venv /opt/venv
COPY --chown=sechermes:sechermes --from=builder /opt/hermes /opt/hermes

ENV PATH="/opt/venv/bin:$PATH"
ENV VIRTUAL_ENV=/opt/venv

WORKDIR /opt/hermes

# Entrypoint
COPY --chown=sechermes:sechermes agents/security-assistant/docker/entrypoint.sh /opt/sechermes-entrypoint.sh
RUN chmod +x /opt/sechermes-entrypoint.sh

# Pre-stage security skills for first-run installation
RUN mkdir -p /opt/sechermes-skills && \
    cp -r agents/security-assistant/skills/vuln-scan /opt/sechermes-skills/ && \
    cp -r agents/security-assistant/skills/sec-docs-qa /opt/sechermes-skills/ && \
    cp -r agents/security-assistant/skills/sec-auto-fix /opt/sechermes-skills/ && \
    cp -r agents/security-assistant/skills/sec-intel /opt/sechermes-skills/ && \
    chown -R sechermes:sechermes /opt/sechermes-skills

# ---------------------------------------------------------------------------
# Environment defaults — override via .env or docker run --env
# ---------------------------------------------------------------------------

# Hermes home directory (persistent data volume)
ENV HERMES_HOME=/opt/data

# SecHermes identity
ENV SECHERMES_SOUL_FILE=/opt/hermes/agents/security-assistant/SOUL.md

# OpenViking defaults (Docker Compose networking)
ENV OPENVIKING_ENDPOINT=http://openviking:1933
ENV OPENVIKING_ACCOUNT=default
ENV OPENVIKING_USER=default
ENV OPENVIKING_AGENT=sechermes
ENV OPENVIKING_EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
ENV OPENVIKING_EMBEDDING_DEVICE=cpu

# Security docs mount point
ENV SEC_DOCS_BASE_PATH=/opt/sec-docs

# Terminal timeout
ENV TERMINAL_TIMEOUT=60

# ---------------------------------------------------------------------------
# Volumes & runtime
# ---------------------------------------------------------------------------
VOLUME ["/opt/data"]
VOLUME ["/opt/sec-docs"]

USER sechermes
ENTRYPOINT ["/opt/sechermes-entrypoint.sh"]
