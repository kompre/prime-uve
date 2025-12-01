# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`prime-uve` is a thin wrapper around `uv` that automatically loads environment variables from `.env.uve` before executing uv commands. The primary use case is managing `UV_PROJECT_ENVIRONMENT` to point virtual environments to non-project-root locations.

**Two CLI commands:**
- `uve [command]` - Wrapper that loads .env.uve then runs `uv [command]`
- `prime-uve` - Standalone CLI for prime-uve management (e.g., `prime-uve init`)

**Installation:** System-wide via `uv tool install prime-uve`

## Project Management

- **Never modify pyproject.toml directly** - Always use `uv` commands to manipulate dependencies and project configuration
- The project uses Python 3.13+ (see pyproject.toml)
- Environment variables are stored in `.env.uve` at project root (configurable via pyproject.toml or uve.toml)

## Key Architecture Decisions

### Environment Variable Loading
Research is needed to determine the best tool for loading env variables (e.g., dotenvx). The goal is: `uve [command]` ≈ `dotenvx run uv [command]` with .env.uve loaded.

### Virtual Environment Management
The `UV_PROJECT_ENVIRONMENT` variable should point to a cache folder outside the project root. The path is generated based on project path hash. This prevents creating .venv in project root (uv's default).

### CLI Structure
- `uve` accepts no options - only passes through uv commands
- `prime-uve` handles tool-specific operations like `prime-uve init` (creates .env.uve with UV_PROJECT_ENVIRONMENT set to hashed cache path)

## Development Notes

- Project is in early/planning stages - no source code yet
- When running uv commands via Claude Code, remember to use environment variables from .env.uve
- Default .env.uve is currently empty

## Task Planning and Management

### `_todo` Directory Structure
The project uses a structured planning system located in `_todo/`:

```
_todo/
├── todo.md                    # Master task list written by user
├── proposal/                  # Initial task proposals
│   └── [task-name].md        # Claude's detailed plan awaiting user approval
├── pending/                   # Active development files
│   └── [task-name].md        # Approved tasks with progress updates
└── completed/                 # Finished tasks archive
    └── YYYY-MM-DD/           # Date-based folders for completion date
        └── [task-name].md    # Final summary + insights
```

### Planning Workflow
1. **Task Creation**: User writes tasks in `_todo/todo.md` with clear objectives and priorities
2. **Proposal Phase**: Claude creates detailed proposal in `_todo/proposal/[task-name].md`
   - Include original objective from todo.md and remove it from todo.md
   - Break down into specific implementation steps
   - Wait for user review, comments, and approval
3. **Development Phase**: After user approval, move proposal to `_todo/pending/[task-name].md`
   - Update file with implementation progress and activity summaries
   - Use for ongoing development updates
4. **Completion**: After task completion, move file to `_todo/completed/YYYY-MM-DD/`
   - Update with final summary and insights
   - Mark task as "Completed" in todo.md

### Session Startup Protocol
**IMPORTANT**: At the start of each session, always check:
1. `_todo/todo.md` for new or updated tasks from the user
2. `_todo/proposal/` for user-reviewed proposals ready to approve/implement
3. `_todo/pending/` for active tasks requiring progress updates
4. Current git status and recent commits for context
