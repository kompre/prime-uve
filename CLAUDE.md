# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**prime-uve** is a thin wrapper for `uv` that provides two commands:

1. **`uve`** - Alias for `uv run --env-file .env.uve -- uv [command]`
2. **`prime-uve`** - CLI tool for venv management with external venv locations

The core problem being solved: `uv` needs the `UV_PROJECT_ENVIRONMENT` variable to work correctly with external venvs. This wrapper automates loading `.env.uve` for every command and provides tooling to manage venvs in a centralized location outside project roots.

## Development Commands

```bash
# Sync dependencies (run at session start for uv-managed projects)
uv sync

# Use uv commands (prefer uv over direct pyproject.toml edits)
uv add <package>
uv remove <package>
```

## .env.uve File Handling

The `.env.uve` file is critical to this project's operation. The lookup logic is:

1. Look for `.env.uve` in cwd
2. If not found and cwd is not project root (no pyproject.toml), walk up the tree
3. If not found at project root, create a default empty one

The file should contain:
```
UV_PROJECT_ENVIRONMENT="$HOME/prime-uve/venvs/<project_name>_<short path hash>"
```

Path requirements:
- Must work cross-platform
- Should use expandable env variables (e.g., `$HOME`)
- Should be unique per project using name + hash

## prime-uve Commands to Implement

- **`prime-uve init`** - Set up venv path and save to `.env.uve`
- **`prime-uve list`** - List all managed venvs (validate that projects still exist and paths match `.env.uve`)
- **`prime-uve prune`** - Remove venvs from cache
  - `--all` - Clean everything
  - `--orphan` - Clean only orphan venvs
  - `path/to/venv` - Clean specific venv
  - `--current` - Clean venv mapped to current project
- **`prime-uve activate`** - Activate current project venv from `.env.uve`
- **`prime-uve configure vscode`** - Update `.code-workspace` file with venv path

## Installation

`prime-uve` should be installed as a standalone CLI tool:
```bash
uv tool install prime-uve
```

## Task Management Workflow

This project uses a structured task workflow in the `_todo/` directory. **CRITICAL**: Follow this process exactly to keep the todo folder organized.

### Directory Structure
- `_todo/proposal/` - Task proposals awaiting approval
- `_todo/pending/` - Active development tasks with progress updates
- `_todo/completed/YYYY-MM-DD/` - Archived completed tasks

### Workflow with Branching

**IMPORTANT**: Each task gets its own feature branch. This keeps the todo folder in sync across branches.

1. **Proposal Phase**
   - User adds task to `_todo/todo.md`
   - Claude creates detailed proposal in `proposal/[task-name].md`
   - User reviews and approves

2. **Start Work Phase** (CRITICAL PROCESS)
   - Move task from `proposal/` to `pending/[task-name].md`
   - Commit the move: `git add _todo && git commit -m "Move [task-name] to pending"`
   - Push to main/dev branch: `git push`
   - Create feature branch: `git checkout -b feature/[task-name]`
   - Now begin implementation work

3. **Development Phase**
   - Make code changes in the feature branch
   - Update `pending/[task-name].md` with progress notes
   - Commit code changes regularly
   - Push feature branch: `git push -u origin feature/[task-name]`

4. **Completion Phase**
   - Create PR for the feature branch
   - After PR is merged to main/dev
   - Switch back to main/dev: `git checkout main` (or `dev`)
   - Pull latest: `git pull`
   - Move task from `pending/` to `completed/YYYY-MM-DD/[task-name].md`
   - Add completion summary to the task file
   - Commit: `git add _todo && git commit -m "Archive completed task: [task-name]"`
   - Push: `git push`

### Why This Process Matters

- **Todo folder stays clean**: Each task file exists in only one location per branch
- **Git history is clear**: Task progression is tracked through commits
- **No merge conflicts**: Moving tasks before branching prevents conflicts
- **Synchronization**: Main/dev branch always has the source of truth for task status

### Task File Contents

Each task file should include:
- Original objective
- Implementation plan
- Progress updates (in pending phase)
- Final summary (in completed phase)

### Quick Reference

Use the `/todo-init` slash command to start work on an approved task - it automates the branching workflow.

## Architecture Notes

**Current Status**: Project is in early planning phase. No source code exists yet (`src/` directory is empty). Architecture definition is the active task in `_todo/todo.md`.

**Key Design Constraint**: The venv mapping needs to be cached/tracked locally so that `prime-uve list` can verify:
- Which projects still exist on disk
- Whether the path in `.env.uve` matches the cached mapping
- Which venvs are orphaned (project deleted or path changed)
