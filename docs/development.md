# Development and GitHub workflow

The current milestone initializes the repository and preserves the product plan. There is no application to install or run yet.

## Repository policy

- Name: `ReplayLab`.
- Visibility: private, per the owner's latest instruction.
- Primary branch: `main`.
- Push major completed milestones during requested development work.
- Preserve history; never force-push or overwrite unrelated work.
- Recheck the official hackathon build window before application implementation.

## Daily workflow

These Git commands work in Windows PowerShell and Linux shells:

```sh
git status --short
git diff
# Stage only reviewed files belonging to the completed update.
git add <reviewed-files>
git diff --cached --check
git diff --cached
# Run the checks appropriate to the update before committing.
git commit -m "Describe the completed milestone"
git push origin main
git status --short --branch
```

Replace `<reviewed-files>` with actual paths. If a feature branch is used, push that branch instead and review its changes before merging. Successful milestone completion includes verifying that the intended commit reached GitHub.

Do not store GitHub tokens in remote URLs or tracked configuration. Use the configured credential manager or another approved credential mechanism.

## Secret and artifact handling

`.gitignore` excludes environment files, private keys, dependency folders, build products, Python caches, runtime media directories, and SQLite databases. `.env.example` may be tracked once it contains only documented placeholders.

Before staging, inspect new files. Ignore rules cannot protect a secret that is already tracked. No API key or provider credential is required for this planning milestone.

## Implementation milestone handoff

When the official build window has opened:

1. Recheck event rules and record the implementation start in project documentation.
2. Implement Phase 1 from the roadmap using the requested stack.
3. Add reproducible Windows PowerShell and Linux setup commands for the actual files.
4. Run startup checks and meaningful tests; record the real results.
5. Commit and push the completed milestone, then continue through the roadmap as authorized.

Application CI, containers, dependency lockfiles, screenshots, licenses, and deployment instructions belong with the implementation they validate. Do not add fake success badges, screenshots, deployment links, or test counts.
