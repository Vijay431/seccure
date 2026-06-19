# Implementation Plan: Fix PR Agent Creation and Update Fix

**Branch**: `001-fix-pr-agent` | **Date**: 2026-06-19 | **Spec**: [spec.md](../spec.md)
**Input**: Feature specification from `/specs/001-fix-pr-agent/spec.md`

## Summary

The PR Agent (`agent/subagents/pr_agent.py`) needs to be enhanced to automatically handle PR creation and updates based on branch commits. It must parse those commits to extract issue and PR mentions, bulk-validate them against the GitHub API, and include the valid ones in the PR description without overwriting manual descriptions.

## Technical Context

**Language/Version**: Python 3.12 (matches existing seccure stack)
**Primary Dependencies**: `agent.tools.github_pulls`, `agent.tools.git_tools`, PyGithub (or REST API via `requests`), `re` for parsing commits
**Storage**: N/A (Pinecone is used elsewhere, here we just use GitHub API state)
**Testing**: `pytest`
**Target Platform**: Linux server (GitHub Actions via Docker)
**Project Type**: single
**Performance Goals**: PR update within 30 seconds
**Constraints**: Do not overwrite manual descriptions. Parse commits accurately. Validate issue/PR mentions in bulk to save time.
**Scale/Scope**: Impacts `pr_agent.py` and GitHub API tools.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Autonomous Execution**: Is the planned feature utilizing the Coordinator-Subagent architecture to prevent context bloat? (Yes, enhancing PRAgent)
- [x] **Idempotency**: Does the solution reuse state and existing PRs to prevent duplicate work? (Yes, updates existing PRs without overwriting manual descriptions)
- [x] **Compliance Focus**: Does it prioritize resolving existing security events / Dependabot alerts without violating boundaries? (Yes, maintains references to security issues)
- [x] **Non-Destructive**: Is the execution strictly isolated to local testing, branches, and PRs without pushing directly to default? (Yes)

## Project Structure

### Documentation (this feature)

```text
specs/001-fix-pr-agent/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
└── agent/
    ├── subagents/
    │   └── pr_agent.py
    └── tools/
        ├── git_tools.py
        └── github_pulls.py

tests/
└── [Unit tests for regex parsing and PR description updates]
```

**Structure Decision**: The project is a single Python module (`agent/`) handling subagents and tools. We will modify `agent/tools/github_pulls.py` and potentially `agent/tools/git_tools.py` to extract commit messages, validate them, and update PR descriptions.
