# Phase 0: Research

## Extracting Issue/PR mentions from commits
- **Decision**: We will implement a `get_commit_messages` function in `agent/tools/git_tools.py` that executes `git log <base_branch>..<head_branch> --oneline` inside the local workspace, and a regex parser in `agent/tools/github_pulls.py` to extract `#<id>`, `GH-<id>` or `PR-<id>` references from those messages.
- **Rationale**: The user wants PR creation/updates based on commits. The easiest way to get commit messages locally before pushing (or after pushing) is `git log`. We already have the repository cloned in `/tmp/seccure_workspace` during the fix phase.
- **Alternatives considered**: Querying the GitHub API for branch commits. Rejected because the agent already has the repository cloned locally, making `git log` much faster and decoupled from API rate limits.

## Preserving manual PR descriptions
- **Decision**: In `upsert_seccure_pr`, before calling `update_pull_request`, we will fetch the existing PR body. If it exists, we will inject our auto-generated block (the fixes, commit references, etc.) at the bottom using the `<!-- seccure-attempt-count:X -->` marker as a boundary, retaining the top portion if it was manually modified. 
- **Rationale**: FR-005 dictates that manual descriptions must not be overwritten. Since Seccure currently overwrites the whole body via `render_pr_title_body(state)`, we need to improve how `upsert_seccure_pr` merges content.
- **Alternatives considered**: Appending a new comment instead of editing the body. Rejected because the feature explicitly states "update the PR description".

## Bulk Validation of Extracted Mentions (NEW)
- **Decision**: We will implement a bulk validation step using the `gh issue list` or `gh pr list` commands (via `run_gh_command`) or GraphQL to verify which extracted IDs actually exist. Alternatively, since issues and PRs share the same ID space in GitHub, we can use `gh api graphql` with a batch query or just attempt to resolve them.
- **Rationale**: The user explicitly requested bulk processing to save time when verifying if mentioned numbers are valid.
- **Alternatives considered**: Iterating through each ID and making a separate REST API call. Rejected because it's too slow and prone to rate limits. Blindly linking. Rejected because the user selected validation.
