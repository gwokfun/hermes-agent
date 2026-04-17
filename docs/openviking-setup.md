# OpenViking Memory Plugin Integration Guide

OpenViking is a context database by Volcengine (ByteDance) that provides session-managed memory with automatic extraction, tiered retrieval, and filesystem-style knowledge browsing for Hermes Agent.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
  - [Docker Compose (Recommended)](#docker-compose-recommended)
  - [Manual Installation](#manual-installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Tools Reference](#tools-reference)
- [Advanced Topics](#advanced-topics)
- [Troubleshooting](#troubleshooting)

## Overview

OpenViking organizes agent knowledge into a filesystem hierarchy with `viking://` URIs, providing:

- **Automatic memory extraction** - 6 categories: profile, preferences, entities, events, cases, patterns
- **Tiered context loading** - L0 (~100 tokens), L1 (~2k tokens), L2 (full content)
- **Semantic search** - Fast/deep/auto modes with hierarchical retrieval
- **Filesystem-style browsing** - List, tree, stat operations on knowledge base
- **Resource ingestion** - URLs, documents, code files automatically parsed and indexed
- **Session management** - Full conversation lifecycle with commit-based extraction

## Features

### Memory Extraction

OpenViking automatically extracts structured memories from conversations:

- **Profile** - User characteristics, background, context
- **Preferences** - Settings, likes/dislikes, workflow preferences
- **Entities** - People, organizations, projects, tools mentioned
- **Events** - Temporal events, meetings, milestones
- **Cases** - Examples, scenarios, problem-solution pairs
- **Patterns** - Recurring themes, workflows, best practices

### Tiered Retrieval

Three detail levels optimize context usage:

- **Abstract (L0)** - ~100 token summary, for quick scanning
- **Overview (L1)** - ~2k token key points, for most queries
- **Full (L2)** - Complete content, for deep analysis

### Knowledge Hierarchy

Content organized in `viking://` filesystem:

```
viking://
├── user/
│   ├── profile/
│   ├── preferences/
│   └── memories/
├── resources/
│   ├── docs/
│   ├── code/
│   └── web/
├── events/
└── patterns/
```

## Installation

### Docker Compose (Recommended)

The easiest way to deploy Hermes Agent with OpenViking is using Docker Compose:

#### 1. Setup Environment Variables

Copy the example environment file:

```bash
cp .env.openviking.example .env
```

Edit `.env` and configure:

```bash
# Required - OpenViking server endpoint
OPENVIKING_ENDPOINT=http://openviking:1933

# Optional - API key for authenticated servers
OPENVIKING_API_KEY=

# Multi-tenancy settings (use defaults for single-user)
OPENVIKING_ACCOUNT=default
OPENVIKING_USER=default
OPENVIKING_AGENT=hermes

# Model configuration
OPENVIKING_EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
OPENVIKING_EMBEDDING_DEVICE=cpu
OPENVIKING_VLM_MODEL=Qwen/Qwen2-VL-2B-Instruct
OPENVIKING_VLM_DEVICE=cpu
```

#### 2. Start Services

Start both Hermes Agent and OpenViking server:

```bash
docker-compose -f docker-compose.yml -f docker-compose.openviking.yml up -d
```

This will:
- Start OpenViking server on port 1933
- Start Hermes Agent with OpenViking pre-configured
- Create persistent volumes for data
- Set up networking between containers

#### 3. Activate Plugin

Access the Hermes container and activate OpenViking:

```bash
docker exec -it hermes-agent hermes memory setup
# Select "openviking" from the menu
```

#### 4. Verify Installation

Check that everything is working:

```bash
# Check server health
curl http://localhost:1933/health

# Check Hermes memory status
docker exec -it hermes-agent hermes memory status
```

### Manual Installation

For manual installation on your local machine:

#### 1. Install OpenViking

```bash
pip install openviking
```

#### 2. Install Dependencies

OpenViking requires `httpx` which is already included in Hermes Agent's dependencies. If installing separately:

```bash
pip install httpx
```

#### 3. Run Setup Script

Use the interactive setup script:

```bash
./scripts/setup-openviking.sh
```

This script will:
- Verify prerequisites
- Install OpenViking if needed
- Configure environment variables
- Set up embedding and VLM models
- Start the OpenViking server
- Activate the plugin in Hermes

#### 4. Manual Configuration (Alternative)

If you prefer manual setup:

**A. Configure Environment**

Add to `~/.hermes/.env`:

```bash
OPENVIKING_ENDPOINT=http://127.0.0.1:1933
OPENVIKING_ACCOUNT=default
OPENVIKING_USER=default
OPENVIKING_AGENT=hermes
```

**B. Start OpenViking Server**

```bash
openviking-server --host 127.0.0.1 --port 1933
```

Or use the management script:

```bash
./scripts/start-openviking.sh start
```

**C. Activate Plugin**

```bash
hermes memory setup
# Select "openviking" from the menu
```

Or manually edit `~/.hermes/config.yaml`:

```yaml
memory:
  provider: openviking
```

## Configuration

### Environment Variables

All OpenViking configuration is via environment variables in `~/.hermes/.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENVIKING_ENDPOINT` | `http://127.0.0.1:1933` | Server URL (required) |
| `OPENVIKING_API_KEY` | _(empty)_ | API key for authenticated servers |
| `OPENVIKING_ACCOUNT` | `default` | Tenant account ID |
| `OPENVIKING_USER` | `default` | User ID within account |
| `OPENVIKING_AGENT` | `hermes` | Agent ID (useful for multi-agent setups) |
| `OPENVIKING_EMBEDDING_MODEL` | `BAAI/bge-small-zh-v1.5` | Embedding model for search |
| `OPENVIKING_EMBEDDING_DEVICE` | `cpu` | Device: cpu, cuda, mps |
| `OPENVIKING_VLM_MODEL` | `Qwen/Qwen2-VL-2B-Instruct` | Vision language model |
| `OPENVIKING_VLM_DEVICE` | `cpu` | Device for VLM |

### Embedding Models

Choose based on your language and resource requirements:

**Chinese Models:**
- `BAAI/bge-small-zh-v1.5` - 24M params, fast, recommended for most users
- `BAAI/bge-base-zh-v1.5` - 102M params, better quality
- `BAAI/bge-large-zh-v1.5` - 326M params, best quality, slower

**English Models:**
- `sentence-transformers/all-MiniLM-L6-v2` - 22M params, fast, good quality

**Multilingual Models:**
- `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` - 118M params

### Vision Language Models

For processing images and multimodal content:

- `Qwen/Qwen2-VL-2B-Instruct` - 2B params, recommended
- `Qwen/Qwen2-VL-7B-Instruct` - 7B params, better quality, requires more resources

### Device Selection

- `cpu` - Works on all systems, slower
- `cuda` - NVIDIA GPU acceleration (requires CUDA toolkit)
- `mps` - Apple Silicon GPU acceleration (M1/M2/M3 Macs)

### Multi-Tenant Setup

For running multiple users or agents:

```bash
# User 1
OPENVIKING_ACCOUNT=company_a
OPENVIKING_USER=alice
OPENVIKING_AGENT=hermes

# User 2
OPENVIKING_ACCOUNT=company_a
OPENVIKING_USER=bob
OPENVIKING_AGENT=hermes

# Multi-agent setup
OPENVIKING_ACCOUNT=default
OPENVIKING_USER=alice
OPENVIKING_AGENT=research_agent
```

Each combination of account/user/agent gets isolated storage.

## Usage

### Verifying Setup

Check memory provider status:

```bash
hermes memory status
```

Expected output:

```
Memory status
────────────────────────────────────────
  Built-in:  always active
  Provider:  openviking

  openviking config:
    endpoint: http://127.0.0.1:1933

  Plugin:    installed ✓
  Status:    available ✓
```

### Automatic Memory Extraction

OpenViking automatically extracts memories from conversations. No explicit action needed - just chat normally:

```
You: I prefer Python over JavaScript for backend development

Hermes: I'll remember that preference...
[On session end, OpenViking extracts: preference -> "prefers Python for backend"]
```

### Searching Knowledge Base

Use `viking_search` tool to find information:

```
You: Search for my Python projects

Hermes: [calls viking_search(query="Python projects", mode="auto")]

Results:
- [0.92] Project: API refactoring with FastAPI (viking://resources/code/api_project/)
- [0.87] Preference: Python for backend development (viking://user/preferences/lang)
- [0.83] Event: Completed Python training course (viking://events/2024-01/)
```

**Search modes:**
- `auto` - Automatically chooses between fast and deep
- `fast` - Quick lookup, single-hop retrieval
- `deep` - Complex queries, multi-hop reasoning across sources

### Reading Content

Use `viking_read` to access specific URIs:

```
Hermes: [calls viking_read(uri="viking://resources/code/api_project/", level="overview")]

Content:
FastAPI project for customer API, migrated from Express.js...
[~2k tokens of key points]
```

**Detail levels:**
- `abstract` - Brief summary (~100 tokens), for quick context
- `overview` - Key points (~2k tokens), sufficient for most questions
- `full` - Complete content, for deep analysis

### Browsing Knowledge

Explore the knowledge base like a filesystem:

```
Hermes: [calls viking_browse(action="tree", path="viking://resources/")]

viking://resources/
├── docs/
│   ├── api_design.md (API design principles and patterns)
│   └── deployment.md (Kubernetes deployment guide)
├── code/
│   ├── api_project/ (FastAPI customer API)
│   └── ml_pipeline/ (Machine learning training pipeline)
└── web/
    └── github_repo/ (Project dependencies and examples)
```

### Explicit Memory Storage

Use `viking_remember` to store important facts:

```
You: Remember that I have a meeting with the client every Monday at 10am

Hermes: [calls viking_remember(
    content="Client meeting every Monday at 10am",
    category="event"
)]

Stored. Will be indexed on session commit.
```

**Categories:**
- `preference` - User preferences and settings
- `entity` - People, projects, tools, organizations
- `event` - Temporal events, schedules, milestones
- `case` - Examples, scenarios, problem-solution pairs
- `pattern` - Workflows, best practices, recurring themes

### Adding Resources

Ingest URLs and documents:

```
Hermes: [calls viking_add_resource(
    url="https://github.com/user/project",
    reason="Main project repository for reference"
)]

Resource queued. Processing will complete shortly.
Root URI: viking://resources/web/github_com_user_project/
```

Supported resources:
- Web pages (HTML)
- GitHub repositories
- PDFs
- Markdown files
- Code files (Python, JavaScript, Go, etc.)

## Tools Reference

### viking_search

Semantic search over the knowledge base.

**Parameters:**
- `query` (required) - Search query
- `mode` - Search depth: `auto`, `fast`, `deep` (default: `auto`)
- `scope` - Viking URI prefix to limit search (e.g., `viking://resources/docs/`)
- `limit` - Maximum results (default: 10)

**Returns:**
```json
{
  "results": [
    {
      "uri": "viking://user/preferences/lang",
      "type": "preference",
      "score": 0.92,
      "abstract": "Prefers Python over JavaScript for backend",
      "related": ["viking://resources/code/api_project/"]
    }
  ],
  "total": 5
}
```

### viking_read

Read content at a Viking URI with tiered detail levels.

**Parameters:**
- `uri` (required) - Viking URI to read
- `level` - Detail level: `abstract`, `overview`, `full` (default: `overview`)

**Returns:**
```json
{
  "uri": "viking://resources/code/api_project/",
  "level": "overview",
  "content": "FastAPI project implementing customer API..."
}
```

### viking_browse

Browse the knowledge store like a filesystem.

**Parameters:**
- `action` (required) - Browse action: `list`, `tree`, `stat`
- `path` - Viking URI path (default: `viking://`)

**Returns:**
```json
{
  "path": "viking://resources/",
  "entries": [
    {
      "name": "docs/",
      "uri": "viking://resources/docs/",
      "type": "dir",
      "abstract": "Documentation and guides"
    }
  ]
}
```

### viking_remember

Explicitly store a fact for extraction on session commit.

**Parameters:**
- `content` (required) - The information to remember
- `category` - Memory category: `preference`, `entity`, `event`, `case`, `pattern` (auto-detected if omitted)

**Returns:**
```json
{
  "status": "stored",
  "message": "Memory recorded. Will be extracted and indexed on session commit."
}
```

### viking_add_resource

Add a URL or document to the knowledge base.

**Parameters:**
- `url` (required) - URL or path of the resource
- `reason` - Why this resource is relevant (improves search accuracy)

**Returns:**
```json
{
  "status": "added",
  "root_uri": "viking://resources/web/example_com/",
  "message": "Resource queued for processing..."
}
```

## Advanced Topics

### Session Management

OpenViking uses session-based memory extraction:

1. **Session Start** - `initialize()` creates session ID
2. **Turn Sync** - Each conversation turn is recorded via `sync_turn()`
3. **Session End** - `on_session_end()` triggers memory extraction and indexing
4. **Commit** - Automatic categorization into 6 memory types

Sessions persist across Hermes restarts when using the same session ID.

### Prefetching

OpenViking prefetches relevant context in the background:

```python
# Automatic prefetch on user message
queue_prefetch(user_message)  # Non-blocking

# Results ready by the time LLM needs context
prefetch()  # Returns pre-loaded context
```

### Memory Mirroring

Built-in memory writes are automatically mirrored to OpenViking:

```python
# When user writes to MEMORY.md or USER.md
on_memory_write(action="add", target="MEMORY.md", content="...")

# OpenViking receives the write and stores it
```

This ensures compatibility with existing memory workflows.

### Multi-Agent Coordination

Multiple agents can share or isolate knowledge:

**Shared knowledge (same account/user, different agents):**
```bash
# Agent 1
OPENVIKING_ACCOUNT=team
OPENVIKING_USER=alice
OPENVIKING_AGENT=research_agent

# Agent 2 (sees Agent 1's memories)
OPENVIKING_ACCOUNT=team
OPENVIKING_USER=alice
OPENVIKING_AGENT=coding_agent
```

**Isolated knowledge (different users):**
```bash
# User 1
OPENVIKING_ACCOUNT=team
OPENVIKING_USER=alice

# User 2 (separate knowledge base)
OPENVIKING_ACCOUNT=team
OPENVIKING_USER=bob
```

### Performance Tuning

#### Embedding Model Selection

Balance quality vs speed:

```bash
# Fast (24M params) - ~50ms per query
OPENVIKING_EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5

# Quality (326M params) - ~200ms per query
OPENVIKING_EMBEDDING_MODEL=BAAI/bge-large-zh-v1.5
```

#### GPU Acceleration

Enable CUDA for 5-10x speedup:

```bash
OPENVIKING_EMBEDDING_DEVICE=cuda
OPENVIKING_VLM_DEVICE=cuda
```

Requirements:
- NVIDIA GPU with CUDA support
- CUDA toolkit installed
- PyTorch with CUDA support

#### Cache Configuration

OpenViking caches embeddings and frequently accessed content. Configure in `~/.openviking/ov.conf`:

```yaml
cache:
  embedding_cache_size: 10000  # Number of cached embeddings
  content_cache_ttl: 3600      # Cache TTL in seconds
```

### Backup and Export

#### Export Knowledge Base

```bash
# Export all data
openviking-cli export --output backup.json

# Export specific account/user
openviking-cli export --account company_a --user alice --output alice_backup.json
```

#### Import Knowledge Base

```bash
openviking-cli import --input backup.json
```

#### Filesystem Backup

OpenViking stores data in `~/.openviking/data/`:

```bash
# Backup
tar -czf openviking-backup.tar.gz ~/.openviking/

# Restore
tar -xzf openviking-backup.tar.gz -C ~/
```

## Troubleshooting

### Server Connection Issues

**Problem:** Cannot connect to OpenViking server

**Solutions:**

1. Check server is running:
```bash
./scripts/start-openviking.sh status
```

2. Verify endpoint in `.env`:
```bash
grep OPENVIKING_ENDPOINT ~/.hermes/.env
```

3. Test connection manually:
```bash
curl http://127.0.0.1:1933/health
```

4. Check server logs:
```bash
tail -f ~/.openviking/server.log
```

### Memory Not Extracted

**Problem:** Memories are not being extracted from conversations

**Solutions:**

1. Verify session end is being called - memories extract on session end, not per-turn

2. Check server logs for extraction errors:
```bash
grep "extract" ~/.openviking/server.log
```

3. Manually commit session:
```python
# In Hermes debug mode
openviking_client.post(f"/api/v1/sessions/{session_id}/commit")
```

### Search Returns No Results

**Problem:** `viking_search` returns empty results

**Solutions:**

1. Verify knowledge base has content:
```
viking_browse(action="tree", path="viking://")
```

2. Check if embedding model is loaded:
```bash
grep "embedding model" ~/.openviking/server.log
```

3. Try broader search query:
```
viking_search(query="*", limit=20)
```

4. Verify search scope if specified:
```python
# Too narrow scope might exclude results
viking_search(query="...", scope="viking://resources/")
```

### Model Loading Errors

**Problem:** Embedding or VLM model fails to load

**Solutions:**

1. Check model name is correct:
```bash
# Valid embedding models
BAAI/bge-small-zh-v1.5
sentence-transformers/all-MiniLM-L6-v2
```

2. Ensure sufficient memory:
```bash
# Small model: ~500MB RAM
# Base model: ~2GB RAM
# Large model: ~4GB RAM
```

3. Try CPU instead of GPU:
```bash
OPENVIKING_EMBEDDING_DEVICE=cpu
OPENVIKING_VLM_DEVICE=cpu
```

4. Clear model cache and retry:
```bash
rm -rf ~/.cache/huggingface/
```

### Port Already in Use

**Problem:** Port 1933 is already in use

**Solutions:**

1. Find and stop conflicting process:
```bash
lsof -i :1933
kill <PID>
```

2. Use different port:
```bash
OPENVIKING_PORT=1934
OPENVIKING_ENDPOINT=http://127.0.0.1:1934
```

### Docker Networking Issues

**Problem:** Hermes container cannot reach OpenViking container

**Solutions:**

1. Verify containers are on same network:
```bash
docker network inspect hermes-network
```

2. Check OpenViking container health:
```bash
docker ps
docker logs hermes-openviking
```

3. Use container name in endpoint:
```bash
# Not localhost!
OPENVIKING_ENDPOINT=http://openviking:1933
```

4. Test connectivity from Hermes container:
```bash
docker exec hermes-agent curl http://openviking:1933/health
```

### High Memory Usage

**Problem:** OpenViking server using excessive memory

**Solutions:**

1. Use smaller embedding model:
```bash
OPENVIKING_EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5  # 24M params
```

2. Reduce cache size in `~/.openviking/ov.conf`:
```yaml
cache:
  embedding_cache_size: 1000
  content_cache_ttl: 1800
```

3. Restart server periodically:
```bash
./scripts/start-openviking.sh restart
```

### Permission Errors

**Problem:** Permission denied errors in Docker

**Solutions:**

1. Set correct UID/GID:
```bash
export HERMES_UID=$(id -u)
export HERMES_GID=$(id -g)
docker-compose up -d
```

2. Fix volume permissions:
```bash
docker-compose down
sudo chown -R $USER:$USER ~/.hermes
docker-compose up -d
```

## Getting Help

- **Documentation:** `plugins/memory/openviking/README.md`
- **Plugin Issues:** https://github.com/NousResearch/hermes-agent/issues
- **OpenViking Issues:** https://github.com/volcengine/OpenViking/issues
- **Discord:** https://discord.gg/NousResearch
- **Check Status:**
  ```bash
  hermes memory status
  ./scripts/start-openviking.sh status
  ```

## References

- [OpenViking GitHub](https://github.com/volcengine/OpenViking)
- [Hermes Agent Documentation](https://hermes-agent.nousresearch.com/docs/)
- [Memory Provider API](https://hermes-agent.nousresearch.com/docs/developer-guide/architecture)
- [Plugin System](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins)
