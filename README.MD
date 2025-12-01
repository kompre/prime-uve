# prime-uve

The scope of this repo is to provide a thin wrapper for uv so that using the command alias `uve` will do 2 things:

1. load env variables contained in default .env.uve (configrable in pyproject.toml or uve.toml, at project root)
2. run uv command with env variables loaded from step 1.

We need to research and define the best tool to load env variable (e.g. dotenvx) such as running `uve [command]` is equivalent to running `dotenvx rn uv [command]` with env variables loaded from .env.uve. 

The reason for this is because I want to be able to set the env variable `UV_PROJECT_ENVIRONMENT` to point to a differente folder not in the project root. Any uv command needs to know about this path to work correctly. Exporting the variable at session start is tedious and error prone. Also claude code need to know about everytime it runs a command and it's easy it will forgot about creating the .venv in the project root (default value for uv).

`uve` will not take any option rather than the uv command itself.

To do other cli command related to prime-uve we will use the `prime-uve` command.

For example we can have a `prime-uve init` command to create the default .env.uve file in the project root, with the `UV_PROJECT_ENVIRONMENT` path set to a cache folder on the system, pointing to a folder name generated based on the project path hash.

Other feature may follow.

prime-uve should be installed as stand alone cli tool via `uv tool install prime-uve` to be available system-wide. 
