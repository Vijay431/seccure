# Data Model: PR Agent Fix

The PR Agent Fix operates primarily on existing GitHub structures and the `SeccureState` model. No new databases are introduced.

## Updated Entities

### `SeccureState` (Existing, to be expanded)

We will expand `SeccureState` conceptually or simply pass commit references directly when parsing.

If expanding `SeccureState`, we could add:
- `commit_mentions: list[str] = Field(default_factory=list)` 

However, since `upsert_seccure_pr` dynamically runs `get_commit_messages`, it may not even need to be stored in `SeccureState`.

### `PullRequest` (GitHub API)

- **Title**: String
- **Body**: String. The body is composed of:
  1. `User Manual Description` (Top section, preserved)
  2. `Seccure Automated Section` (Bottom section, generated and replaced on updates)
     - Includes `Packages Fixed`
     - Includes `Commit Mentions` (New)
     - Includes `Closes Dependabot PRs`
     - Includes `Closes Issues`
- **Labels**: `seccure`, `auto-fix`, `dependabot`
