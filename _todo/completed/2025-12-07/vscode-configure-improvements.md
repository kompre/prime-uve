# Proposal: VS Code Workspace Configuration Improvements

vscode can access env variables by using the `${env:VAR_NAME}` syntax in settings.json. 

The command `configure vscode` has been fixed to properly escape env variable with this syntax.