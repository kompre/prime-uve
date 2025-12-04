# prime-uve

The scope of this repo is to provide a thin wrapper for uv so that using the command alias `uve` will be equivalent to run:

```sh
uv run --env-file .env.uve -- uv [command] 

# equivalent to
uve [command]
```

Particular care should be taken to provide the `.env.uve` file:

1. look for `.env.uve` in cwd
2. if not found and cwd is not project root (no pyproject.toml in cwd) walk up the tree
3. if no `.env.uve` is found at the project root, then create a default empty one



The reason for this is because I want to be able to set the env variable `UV_PROJECT_ENVIRONMENT` to point to a differente folder not in the project root. Any uv command needs to know about this path to work correctly. Exporting the variable at session start is tedious and error prone. Also claude code need to know about every time it runs a command and it's easy it will forgot about creating the .venv in the project root (default value for uv).

This repo will also provide another command `prime-uve` that will take care of setting up the specific venv workflow and set up `UV_PROJECT_ENVIRONMENT` for `uve`.

## local venv

Reasearch how best to provide a location to save venv local to the machine. The path provided to `UV_PROJECT_ENVIRONMENT` should work cross platform and make use of env variables that could be expanded something like this:

```.env.uve
UV_PROJECT_ENVIRONMENT="$HOME/prime-uve/venvs/<project_name>_<short path hash>"
```

`prime-uve init` should take care of providing the path for the venv and save it to `.env.uve`

## venv management

we should keep track of venv created in the local cached folder (mapping), so that a user can retrieve it:

- `prime-uve list`: list all venvs created (check if list is still valid, by looking if the project folder still exist, and if the path is the same in the `.env.uve` file)
- `prime-uve prune`: remove venvs from the cache:
  - `--all` to clean everything
  - `--orphan` to clean only orphan venvs
  - `path/to/venv` to clean a specific venv
  - `--current` to clean venv mapped to current project from `.env.uve`
- `prime-uve activate`: to activate current project venv from `.env.uve`
- `prime-uve configure vscode` to write to the `.code-workspace` file to make vscode aware of the venv


Other feature may follow.

prime-uve should be installed as stand alone cli tool via `uv tool install prime-uve` to be available system-wide. 
