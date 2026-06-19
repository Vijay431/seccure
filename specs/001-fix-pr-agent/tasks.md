# Tasks: Fix PR Agent Creation and Update Fix

**Input**: Design documents from `/specs/001-fix-pr-agent/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

*(No setup required as this is an existing project)*

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T001 [P] Implement `get_commit_messages` in `agent/tools/git_tools.py` using `git log`
- [x] T002 [P] Implement `extract_references_from_commits` in `agent/tools/github_pulls.py` to parse issue/PR IDs
- [x] T003 [P] Implement `bulk_validate_references` in `agent/tools/github_pulls.py` to verify IDs via GitHub API

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Create PR with Commit Mentions (Priority: P1) 🎯 MVP

**Goal**: Automatically create a PR and include the issue/PR mentions extracted from commits.

**Independent Test**: Can be fully tested by pushing a new branch with a commit that mentions an issue (e.g., "Fixes #123") and verifying a PR is created with the mention.

### Implementation for User Story 1

- [x] T004 [US1] Modify `render_pr_title_body` in `agent/tools/github_pulls.py` to accept and format extracted commit references
- [x] T005 [US1] Update `upsert_seccure_pr` in `agent/tools/github_pulls.py` to call `get_commit_messages`, `extract_references_from_commits`, and `bulk_validate_references` before rendering the body

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Update Existing PR with New Commits (Priority: P1)

**Goal**: Update the PR description to include any new issues or PRs mentioned in those commits without overwriting manual descriptions.

**Independent Test**: Can be tested by adding a commit with a new issue mention to an existing PR and checking if the PR description updates appropriately.

### Implementation for User Story 2

- [x] T006 [US2] Update `upsert_seccure_pr` in `agent/tools/github_pulls.py` to fetch existing PR body if `existing_pr_number` is provided
- [x] T007 [US2] Implement merging logic in `agent/tools/github_pulls.py` to preserve text above the `<!-- seccure-attempt-count:X -->` marker

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T008 [P] Create unit tests for regex parsing and bulk validation in `tests/test_github_pulls.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2)
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - Technically builds on US1 changes in `upsert_seccure_pr`

### Parallel Opportunities

- Foundational tasks (T001, T002, T003) can run in parallel.
- Unit tests (T008) can run in parallel after the main logic.

---

## Parallel Example: User Story 1

```bash
# Launch Foundational tasks in parallel:
Task: "Implement get_commit_messages in agent/tools/git_tools.py"
Task: "Implement extract_references_from_commits in agent/tools/github_pulls.py"
Task: "Implement bulk_validate_references in agent/tools/github_pulls.py"
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
2. Complete Phase 3: User Story 1
3. **STOP and VALIDATE**: Test User Story 1 independently

### Incremental Delivery

1. Complete Foundational → Foundation ready
2. Add User Story 1 → Test independently
3. Add User Story 2 → Test independently
4. Polish
