# cc-session Implementation Guide

Complete guide for installing the Claude Code Session Orchestrator on new machines.

## Overview

cc-session is a GPT-powered orchestration layer that wraps Claude Code CLI, providing:

- **Persistent RAG Memory**: ChromaDB vector store + SQLite for context across sessions
- **GPT Manager/Reviewer Loop**: Generates optimal prompts, reviews results, iterates until success
- **MCP Integration**: Exposes tools to Claude Code for memory search and repo state
- **Session Hooks**: Auto-saves session summaries to memory

## Prerequisites

| Requirement | Version | Check Command |
|------------|---------|---------------|
| Python | 3.11+ | `python3 --version` |
| Git | Any | `git --version` |
| Claude Code CLI | Latest | `claude --version` |
| OpenAI API Key | - | Must have GPT-4o access |

## Installation Steps

### Step 1: Create Directory Structure

```bash
mkdir -p ~/.local/claude-orchestrator/{data/chroma,runs,prompts,src/cc_session,scripts}
mkdir -p ~/.local/bin
```

### Step 2: Create Source Files

Create the following files in `~/.local/claude-orchestrator/`:

#### pyproject.toml

```toml
[project]
name = "cc-session"
version = "0.1.0"
description = "Local orchestration system for Claude Code CLI with persistent memory and GPT manager/reviewer loop"
readme = "README.md"
requires-python = ">=3.11"
license = {text = "MIT"}
authors = [
    {name = "David Sanker", email = "david@lawkraft.com"}
]
keywords = ["claude", "ai", "orchestration", "rag", "memory"]

dependencies = [
    "typer>=0.12.0",
    "rich>=13.7.0",
    "httpx>=0.27.0",
    "chromadb>=0.5.0",
    "pydantic>=2.6.0",
    "pydantic-settings>=2.2.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "respx>=0.21.0",
]
mcp = [
    "mcp>=1.0.0",
]

[project.scripts]
cc-session = "cc_session.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/cc_session"]
```

#### src/cc_session/__init__.py

```python
"""cc-session: Local orchestration system for Claude Code CLI."""
__version__ = "0.1.0"
```

#### src/cc_session/config.py

```python
"""Configuration management for cc-session."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="CC_SESSION_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # OpenAI API configuration
    openai_api_key: str = ""
    model: str = "gpt-4o"
    review_model: str = "gpt-4o"
    embed_model: str = "text-embedding-3-small"

    # Paths
    base_dir: Path = Path.home() / ".local" / "claude-orchestrator"

    @property
    def data_dir(self) -> Path:
        return self.base_dir / "data"

    @property
    def chroma_dir(self) -> Path:
        return self.data_dir / "chroma"

    @property
    def sqlite_path(self) -> Path:
        return self.data_dir / "sessions.db"

    @property
    def runs_dir(self) -> Path:
        return self.base_dir / "runs"

    @property
    def prompts_dir(self) -> Path:
        return self.base_dir / "prompts"

    # RAG settings
    rag_top_k: int = 5
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # Session settings
    max_loop_iterations: int = 10
    test_timeout: int = 300

    # Claude Code settings
    permission_mode: str = "acceptEdits"
    allowed_tools: str = "Bash(pip:*),Bash(pytest:*),Bash(python:*),Bash(uv:*)"


def get_settings() -> Settings:
    """Get application settings with environment variable overrides."""
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    return Settings(openai_api_key=openai_key)


settings = get_settings()
```

#### src/cc_session/models.py

```python
"""Data models for cc-session."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    AWAITING_REVIEW = "awaiting_review"
    COMPLETED = "completed"
    FAILED = "failed"


class RepoSnapshot(BaseModel):
    repo_path: Path
    repo_name: str
    current_branch: str
    last_commits: list[str] = Field(default_factory=list)
    changed_files: list[str] = Field(default_factory=list)
    staged_files: list[str] = Field(default_factory=list)
    untracked_files: list[str] = Field(default_factory=list)
    has_uncommitted_changes: bool = False
    test_command: Optional[str] = None
    failing_tests: Optional[str] = None


class MemoryDocument(BaseModel):
    id: str
    content: str
    source_path: str
    repo_path: Optional[str] = None
    doc_type: str = "markdown"
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: dict = Field(default_factory=dict)


class SessionRecord(BaseModel):
    id: Optional[int] = None
    session_id: str
    repo_path: str
    repo_name: str
    branch: str
    goal: str
    status: SessionStatus = SessionStatus.STARTED
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    summary: Optional[str] = None
    files_changed: list[str] = Field(default_factory=list)
    run_dir: Optional[str] = None


class StateSummary(BaseModel):
    summary: str
    key_context: list[str] = Field(default_factory=list)
    potential_concerns: list[str] = Field(default_factory=list)
    question: str


class GeneratedPrompt(BaseModel):
    prompt: str
    acceptance_criteria: list[str] = Field(default_factory=list)
    stop_conditions: list[str] = Field(default_factory=list)
    estimated_complexity: str = "medium"


class ReviewResult(BaseModel):
    assessment: str  # pass, partial, fail
    explanation: str
    criteria_met: list[str] = Field(default_factory=list)
    criteria_not_met: list[str] = Field(default_factory=list)
    next_step: Optional[str] = None
    should_finalize: bool = False


class SessionArtifacts(BaseModel):
    git_diff: str = ""
    changed_files: list[str] = Field(default_factory=list)
    test_output: Optional[str] = None
    test_passed: Optional[bool] = None
    claude_output: str = ""
    error: Optional[str] = None
```

The remaining source files (`cli.py`, `session.py`, `store.py`, `mcp_server.py`, `openai_client.py`, `prompts.py`, `repo.py`) should be copied from your existing installation at `~/.local/claude-orchestrator/src/cc_session/`.

### Step 3: Create Install Script

Create `~/.local/claude-orchestrator/scripts/install.sh`:

```bash
#!/bin/bash
# cc-session installer

set -e

INSTALL_DIR="${HOME}/.local/claude-orchestrator"
VENV_DIR="${INSTALL_DIR}/.venv"
BIN_DIR="${HOME}/.local/bin"

echo "========================================"
echo "  cc-session Installer"
echo "========================================"

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]; }; then
    echo "Error: Python 3.11+ is required (found $PYTHON_VERSION)"
    exit 1
fi

echo "✓ Python $PYTHON_VERSION detected"

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv "${VENV_DIR}"

# Activate and install
echo "Installing dependencies..."
source "${VENV_DIR}/bin/activate"
pip install --upgrade pip --quiet
pip install -e "${INSTALL_DIR}" --quiet

# Ensure bin directory exists
mkdir -p "${BIN_DIR}"

# Create wrapper script
SYMLINK="${BIN_DIR}/cc-session"
cat > "${SYMLINK}" << 'EOF'
#!/bin/bash
source "${HOME}/.local/claude-orchestrator/.venv/bin/activate"
exec python -m cc_session.cli "$@"
EOF

chmod +x "${SYMLINK}"

# Create data directories
mkdir -p "${INSTALL_DIR}/data/chroma"
mkdir -p "${INSTALL_DIR}/runs"
mkdir -p "${INSTALL_DIR}/prompts"

echo ""
echo "========================================"
echo "  Installation Complete!"
echo "========================================"
echo ""
echo "Required: export OPENAI_API_KEY='your-key'"
echo ""
echo "Quick start:"
echo "  cd /path/to/your/repo"
echo "  cc-session ingest"
echo "  cc-session start"
```

### Step 4: Create Session End Hook

Create `~/.local/claude-orchestrator/scripts/session_end_hook.sh`:

```bash
#!/bin/bash
# Claude Code hook script for session end

if ! git rev-parse --show-toplevel > /dev/null 2>&1; then
    exit 0
fi

REPO_PATH=$(git rev-parse --show-toplevel)

if ! command -v cc-session &> /dev/null; then
    exit 0
fi

if [ -z "$OPENAI_API_KEY" ]; then
    exit 0
fi

(cc-session summarize-last --repo "$REPO_PATH" > /dev/null 2>&1) &

exit 0
```

Make it executable:
```bash
chmod +x ~/.local/claude-orchestrator/scripts/session_end_hook.sh
```

### Step 5: Run Installation

```bash
chmod +x ~/.local/claude-orchestrator/scripts/install.sh
~/.local/claude-orchestrator/scripts/install.sh
```

### Step 6: Configure Environment

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
# cc-session configuration
export PATH="$HOME/.local/bin:$PATH"
export OPENAI_API_KEY="your-openai-api-key"

# Optional: customize models
export CC_SESSION_MODEL="gpt-4o"
export CC_SESSION_REVIEW_MODEL="gpt-4o"
export CC_SESSION_PERMISSION_MODE="acceptEdits"
```

Reload:
```bash
source ~/.bashrc
```

### Step 7: Configure MCP Server

Create `~/.mcp.json`:

```json
{
  "mcpServers": {
    "cc-session": {
      "command": "/home/YOUR_USERNAME/.local/claude-orchestrator/.venv/bin/python",
      "args": ["-m", "cc_session.mcp_server"],
      "env": {
        "PYTHONPATH": "/home/YOUR_USERNAME/.local/claude-orchestrator/src"
      }
    }
  }
}
```

**Replace `YOUR_USERNAME` with your actual username.**

### Step 8: Configure Claude Code Hooks (Optional)

Add to `~/.claude/settings.local.json`:

```json
{
  "enabledMcpjsonServers": ["cc-session"],
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash\\(git commit",
        "hooks": [
          {
            "type": "command",
            "command": "/home/YOUR_USERNAME/.local/claude-orchestrator/scripts/session_end_hook.sh",
            "timeout": 10
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/home/YOUR_USERNAME/.local/claude-orchestrator/scripts/session_end_hook.sh",
            "timeout": 10,
            "statusMessage": "Saving session to cc-session memory..."
          }
        ]
      }
    ]
  }
}
```

### Step 9: Install Claude Code Plugin (Optional)

If using the official marketplace:

1. Create plugin directory:
```bash
mkdir -p ~/.claude/plugins/cache/claude-plugins-official/cc-session/1.0.0/commands/
```

2. Create `~/.claude/plugins/cache/claude-plugins-official/cc-session/1.0.0/commands/cc-session.md`:
```markdown
---
description: Show cc-session usage guide - GPT-enhanced Claude Code orchestrator
allowed-tools: []
---

# cc-session - Claude Code Session Orchestrator

[... skill content ...]
```

3. Enable in Claude Code settings.

## Verification

```bash
# Check installation
cc-session --version

# Check configuration
cc-session config

# Check stats
cc-session stats

# Test search (after ingesting docs)
cc-session search "test query"
```

## Quick Copy Installation

For a faster installation, copy the entire directory from your existing machine:

```bash
# On source machine
tar -czf cc-session-backup.tar.gz -C ~/.local claude-orchestrator

# Transfer to new machine (via scp, USB, etc.)

# On target machine
tar -xzf cc-session-backup.tar.gz -C ~/.local

# Re-run install to create symlink and venv
~/.local/claude-orchestrator/scripts/install.sh

# Copy MCP config
cp ~/.mcp.json ~/  # adjust path as needed
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         cc-session start                         │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│                     1. Repository Analysis                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐   │
│  │ git status  │  │ git log     │  │ detect test command     │   │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘   │
└───────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│                     2. RAG Memory Query                            │
│  ┌─────────────────────────┐  ┌─────────────────────────────┐    │
│  │ ChromaDB Vector Search  │  │ SQLite Session Index        │    │
│  │ (OpenAI Embeddings)     │  │ (Past sessions, docs)       │    │
│  └─────────────────────────┘  └─────────────────────────────┘    │
└───────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│                     3. GPT Manager                                 │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ Generate State Summary → Ask Goal → Generate Claude Prompt  │ │
│  │ with Acceptance Criteria and Stop Conditions                │ │
│  └─────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│                     4. Claude Code Execution                       │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ claude --print --permission-mode acceptEdits -- "$PROMPT"   │ │
│  └─────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│                     5. Artifact Collection                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐   │
│  │ git diff    │  │ test output │  │ claude output logs      │   │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘   │
└───────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│                     6. GPT Reviewer                                │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ Evaluate: PASS / PARTIAL / FAIL                             │ │
│  │ → Suggest next step OR finalize session                     │ │
│  └─────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
                                │
              ┌─────────────────┴─────────────────┐
              │                                   │
              ▼                                   ▼
      ┌───────────────┐                   ┌───────────────┐
      │   Finalize    │                   │   Iterate     │
      │   Session     │                   │   (loop)      │
      └───────────────┘                   └───────────────┘
              │
              ▼
      ┌───────────────────────────────────────────────────┐
      │ Save Summary to RAG Memory for Future Sessions    │
      └───────────────────────────────────────────────────┘
```

## Data Storage

```
~/.local/claude-orchestrator/
├── data/
│   ├── chroma/              # Vector embeddings (ChromaDB)
│   └── sessions.db          # Session metadata (SQLite)
├── runs/
│   └── YYYYMMDD_HHMMSS/     # Per-session artifacts
│       ├── claude_output_1.log
│       ├── artifacts_1.json
│       └── session_summary.md
├── prompts/                  # Custom prompt overrides (optional)
├── src/cc_session/          # Source code
├── scripts/                  # Install/hook scripts
├── .venv/                    # Python virtual environment
└── pyproject.toml           # Package definition
```

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | (required) | OpenAI API key |
| `CC_SESSION_MODEL` | `gpt-5.2` | Chat model for manager (GPT-5.2 Dec 2025) |
| `CC_SESSION_REVIEW_MODEL` | `gpt-5.2` | Model for reviewer |
| `CC_SESSION_EMBED_MODEL` | `text-embedding-3-small` | Embedding model |
| `CC_SESSION_PERMISSION_MODE` | `acceptEdits` | Claude permission mode |
| `CC_SESSION_ALLOWED_TOOLS` | `Bash(pip:*),Bash(pytest:*),...` | Pre-allowed tools |

### GPT-5.2 Model Variants

| Model ID | Description |
|----------|-------------|
| `gpt-5.2` | Default - best for complex tasks (used by cc-session) |
| `gpt-5.2-instant` | Faster responses, lower latency |
| `gpt-5.2-thinking` | Extended reasoning capability |
| `gpt-5.2-pro` | Maximum compute for hardest problems |
| `gpt-5.2-codex` | Optimized for coding tasks |

## Troubleshooting

### "cc-session: command not found"
```bash
export PATH="$HOME/.local/bin:$PATH"
# Add to ~/.bashrc for persistence
```

### "OPENAI_API_KEY not set"
```bash
export OPENAI_API_KEY="sk-..."
```

### MCP tools not appearing in Claude Code
1. Verify `~/.mcp.json` exists and has correct paths
2. Restart Claude Code CLI
3. Check MCP server can run: `python -m cc_session.mcp_server`

### ChromaDB errors
```bash
# Reset the database
rm -rf ~/.local/claude-orchestrator/data/chroma
mkdir -p ~/.local/claude-orchestrator/data/chroma
cc-session ingest --repo /path/to/repo
```

## License

MIT License - Created by David Sanker (Lawkraft)
