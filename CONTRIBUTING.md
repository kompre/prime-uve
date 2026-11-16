# Contributing

## Workflow

```
issue -> branch -> PR into main (squash merge) -> release PR -> merge = release
```

Everything can be done from the GitHub mobile app (or a Claude Code session
started from the phone); nothing requires a local checkout.

1. **Open an issue** for each bug or task (templates: *Bug report*,
   *Feature / task*). Ideas and backlog live in issues, not in the repo.
2. **Branch from `main`** and open a PR into `main`. Mention the issue in the
   body (`Fixes #12`) so it closes on merge. There is no `dev` branch.
3. **PR title = conventional commit**, because PRs are squash-merged and the
   title becomes the commit on `main`:

   | Title prefix | Effect on next release |
   |---|---|
   | `fix:` / `fix(scope):` | patch (0.2.0 -> 0.2.1) |
   | `feat:` | minor (0.2.0 -> 0.3.0) |
   | `feat!:` / `fix!:` (or `BREAKING CHANGE:` in body) | major (pre-1.0: minor) |
   | `docs:`, `refactor:`, `perf:` | listed in changelog, no bump on their own |
   | `test:`, `ci:`, `chore:`, `build:`, `style:` | hidden, no bump |

   The *PR Title* check fails if the title does not match; edit the title and
   it re-runs.
4. **Merge** once *Run Tests* is green.

## Releasing

`release-please` watches `main`. After every merge it opens or updates a
single PR titled `chore(main): release X.Y.Z` that bumps the version in
`pyproject.toml` / `uv.lock` and writes `CHANGELOG.md`. Leave it open while
changes accumulate; **merging it** tags `vX.Y.Z`, creates the GitHub Release
and publishes to PyPI (Trusted Publishing). Never bump the version by hand.

## CI (kept deliberately small)

| Workflow | Trigger | Cost |
|---|---|---|
| `test.yml` | PR into `main` (open / new push / reopen), manual | one run per PR update; older run cancelled; Markdown-only and release PRs skip the heavy steps |
| `pr-title.yml` | PR into `main` opened / edited / reopened | a few seconds, no checkout |
| `release.yml` | push to `main` (= a merged PR) | release-please; build+publish only when a release is cut |
| `claude.yml` | comment / issue mentioning `@claude` | skipped otherwise |
| `claude-code-review.yml` | `code-review` label added to a PR | skipped otherwise |

No workflow runs on pushes to feature branches. There is no auto-fix bot:
run `uv run ruff format src tests` before committing (CI checks it).

## Local development

```bash
uv sync --group dev
uv run pytest tests
uv run ruff check src tests && uv run ruff format src tests
```

## Repository settings (one-time, done by the maintainer)

- **General -> Pull Requests**: allow *squash merging* only, default commit
  message *Pull request title*; enable *Automatically delete head branches*.
- **Branches -> `main`** ruleset: require a PR, require status checks
  `test` and `conventional-title`.
- **Actions -> General**: *Allow GitHub Actions to create and approve pull
  requests* (needed by release-please).
- **Secrets -> Actions**: `RELEASE_PLEASE_TOKEN`, a fine-grained PAT on this
  repo with *Contents* and *Pull requests* read/write. Without it the release
  PR is created with `GITHUB_TOKEN` and gets no CI checks, so a required check
  would block it.
- **PyPI**: the Trusted Publisher must point at workflow `release.yml`
  (unchanged filename).
