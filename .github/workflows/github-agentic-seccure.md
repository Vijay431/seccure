---
on:
  workflow_dispatch:
    inputs:
      target_repo:
        description: Target repo in owner/repo form. Leave blank to use this repo.
        required: false
        default: ""
      additional_constraints:
        description: One-off extra constraints for this run only.
        required: false
        default: ""
      ecosystem:
        description: Target ecosystem to process.
        required: false
        default: all

permissions:
  contents: read
  pull-requests: read
  issues: read
  security-events: read
  checks: read
  actions: read

engine: codex
strict: false
network: defaults
timeout-minutes: 30

runtimes:
  node:
    version: "20"
  python:
    version: "3.12"
  uv:
    version: latest

jobs:
  seccure_runtime:
    name: Run Seccure runtime
    runs-on: ubuntu-latest
    timeout-minutes: 30
    permissions:
      contents: write
      pull-requests: write
      issues: write
      security-events: read
      checks: read
      actions: read
    steps:
      - name: Checkout Seccure source
        uses: actions/checkout@v4
        with:
          persist-credentials: false

      - name: Set up uv
        uses: astral-sh/setup-uv@v5
        with:
          version: latest

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: "20"

      - name: Install Seccure dependencies
        run: |
          python --version
          python -m pip install --upgrade pip
          python -m pip install -r requirements.txt

      - name: Run Seccure Agent
        env:
          GITHUB_RUN_ID: ${{ github.run_id }}
          GITHUB_TOKEN: ${{ github.token }}
          GITHUB_WORKSPACE: ${{ github.workspace }}
          TARGET_REPO: ${{ github.event.inputs.target_repo || github.repository }}
          ADDITIONAL_CONSTRAINTS: ${{ github.event.inputs.additional_constraints || '' }}
          ECOSYSTEM: ${{ github.event.inputs.ecosystem || 'all' }}
          OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
          PYTHONPATH: ${{ github.workspace }}
        run: python agent/main.py

      - name: Check Seccure artifacts
        if: always()
        run: |
          ls -la "${{ github.workspace }}/seccure_state_${{ github.run_id }}.json"
          ls -la "${{ github.workspace }}/seccure_events_${{ github.run_id }}.jsonl" || true

      - name: Upload Seccure state
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: seccure-state-${{ github.run_id }}
          path: ${{ github.workspace }}/seccure_state_${{ github.run_id }}.json

      - name: Upload Seccure events
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: seccure-events-${{ github.run_id }}
          path: ${{ github.workspace }}/seccure_events_${{ github.run_id }}.jsonl
          if-no-files-found: ignore

safe-outputs:
  noop: {}
  report-failure-as-issue: true
---

# GitHub Agentic Seccure

Run Seccure's current Python agentic runtime against a target repository.

This workflow is a side-by-side validation path for `.github/workflows/seccure.yml`.
Do not disable, remove, or reschedule `.github/workflows/seccure.yml`; it remains
the production Docker workflow until this GitHub Agentic Workflow is validated.

## Objective

Execute the same Seccure job as the current codebase:

1. Gather compact GitHub security inputs with the deterministic audit fan-out.
2. Initialize and update `SeccureState` in `GITHUB_WORKSPACE`.
3. Load `.seccure/constraints.md` via the Python runtime and merge any
   `additional_constraints` dispatch input.
4. Let the Coordinator decide whether there is nothing to fix, an existing
   Seccure PR to update, a failed PR pipeline to repair, or vulnerabilities to
   patch.
5. Let the PRAgent publish changes through deterministic Git and GitHub tools.
6. Upload the state and event artifacts after the run.

The markdown agent must not re-implement Seccure's GitHub API parsing, fix
strategy, PR body rendering, branch pushing, or conflict issue creation. Those
behaviors already live in `agent/main.py` and the Python tools under `agent/`.

## Required Execution

The deterministic `seccure_runtime` job already checks out this repository,
installs Python dependencies, and runs `python agent/main.py` exactly once with
the same environment contract used by the current runtime.

## Artifact Uploads

The deterministic `seccure_runtime` job always uploads
`seccure_state_${{ github.run_id }}.json` and
`seccure_events_${{ github.run_id }}.jsonl` from the workspace.

## Guardrails

- Use only the OpenRouter API key secret expected by the current Python runtime.
- Do not inspect or paste raw Dependabot alert payloads into the agent context.
- Do not author PR markdown in this workflow; `agent.tools.github_write` renders
  the deterministic PR title, body, labels, attempt marker, and closing
  references.
- Keep this workflow manual-only during side-by-side validation. Do not add a
  `schedule:` trigger here.
