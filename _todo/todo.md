# Task List

## Active Tasks

<!-- Add tasks here. When creating a proposal, move the task description to the proposal file -->

### set proper venv cache location for each major platform

since we set $home as environment variable when `uve` is called, then we can set a proper cache location for each major platform (windows, linux, mac) with a new variable `$UVE_VENV_CACHE`.

### update cache.json

the cache.json will be populated only when running `prime-uve init`, so there coule be a situation where the .env.uve is already created, but the rproject reference is missing from cache.json, because the user did some operation. If `.env.uve` is already set, user can call `uve sync` that will create the venv in the correct location, but the cache.json will not be updated, and the venv will be marked as orphaned even if it is valid.

We should then add a new command to `prime-uve register`, that will update the cache.json file, when called from within a project that has .env.uve file and `UV_PROJECT_ENVIRONMENT` is set.

`register` should be called before `list` or `prune` to ensure that the cache is up to date.



## Instructions

- Write clear, specific task objectives with priorities
- Claude will create detailed proposals in `_todo/proposal/[task-name].md`
- After review/approval, proposals move to `_todo/pending/`
- start developing in new branch
- Completed tasks archive to `_todo/completed/YYYY-MM-DD/`
