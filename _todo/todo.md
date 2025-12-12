# Task List

## Active Tasks

<!-- Add tasks here. When creating a proposal, move the task description to the proposal file -->

### prime-uve list improvements

I want to display a more useful table.

- Status should be moved as first column and display only [OK]/[!] so that max width can be contained;
- I want to show the project path, so that user can quickly navigate to the project; (can we display just named link instead of ful path?)
- If prime-list is called in a managed project, then highlight the project in the table as `(current)`
- add option `--no-auto-register` to prevent auto-registration. This need to be implemented also in `prime-uve prune`

### improvement to configure vs-code

vs-code configure is not enough. vscode lament the default path is not correct, and would not spawn a new terminal with the virtual env started. The discoverability needs to be improved.

### register message

when the register method is run, if it is successful, i.e. it register the current project in the cache, it should display a message to let user know it happened. Otherwise a user that want to prune --all the venvs, when they run again prime-uve list the newly registered venv will appear again creating confusion.

### bug: --all in prune

--all option in prune does not eliminate orphaned venvs. add a new option `--valid` to delete only valid venvs, and change `--all` to be the same as `--orphan + --valid`.


## Instructions

- Write clear, specific task objectives with priorities
- Claude will create detailed proposals in `_todo/proposal/[task-name].md`
- After review/approval, proposals move to `_todo/pending/`
- start developing in new branch
- Completed tasks archive to `_todo/completed/YYYY-MM-DD/`
