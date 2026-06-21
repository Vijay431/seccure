# Contributing to Seccure: Complete Developer Guide

First off, thank you for considering contributing to Seccure! It's people like you that make open-source software such a great community to learn, inspire, and create.

This guide will help you understand the internal architecture of Seccure, how to set up your development environment, and how to write and test code.

---

## 🏗 Architecture Overview

Seccure is not a traditional procedural script. It is an autonomous, goal-oriented system powered by **LangChain via OpenRouter**. 

To manage complexity, avoid context-window bloat, and prevent LLM hallucinations, Seccure uses a **Coordinator-Subagent architecture**.

### 1. The Coordinator Agent
**Role:** The mastermind and orchestrator.
**Model:** `gemini-2.5-pro` (Highly capable at reasoning and complex planning)

The Coordinator acts as the bridge between the target repository and the GitHub API. It orchestrates subagents, analyzes consolidated data, enforces user constraints (like checking `.seccure/constraints.md`), and executes shell commands (`npm audit fix`, manual bumps) in isolated sandboxes to open security PRs.

### 2. The Data-Gathering Subagents
Because raw GitHub API responses are massive, the Coordinator spawns three specialized subagents in parallel to parse and summarize data cleanly. These use faster `gemini-2.0-flash` models and output strictly typed JSON (via Pydantic schemas).

*   **IssueAgent:** Finds open issues tagged with `security` or `dependabot`. Schema: `IssueSummary`.
*   **PRAgent:** Finds open PRs authored by `dependabot[bot]`. Schema: `PRSummary`.
*   **SecurityAgent:** Pulls Dependabot alerts and GitHub Code Scanning alerts, deduplicating them. Schema: `AlertSummary`.

### 3. Shared State Management (`SeccureState`)
Subagents write to a persistent disk-based state file: `seccure_state_{run_id}.json`. The Coordinator reads this clean, structured data before planning its fixes, keeping its context window focused solely on reasoning rather than parsing API bloat.

### 4. Observability & Tracing (LangSmith)
Seccure uses **LangSmith** for granular tracing of tool calls, shell executions, and subagent planning. If a bash command fails, the `FallbackHook` intercepts the error and LangSmith traces the agent's recovery strategy.

---

## 💻 Development Setup

Seccure is built using Python 3.12+ and relies heavily on modern tooling like `uv` and `ruff`.

### 1. Clone the repository
```bash
git clone https://github.com/owner/seccure.git
cd seccure
```

### 2. Create a virtual environment and install dependencies
We use [`uv`](https://github.com/astral-sh/uv) for lightning-fast virtual environment management.
```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

### 3. Environment Variables
To test the agent locally, you will need to export the following environment variables:
```bash
export GEMINI_API_KEY="your-gemini-api-key"
export GITHUB_TOKEN="your-github-personal-access-token"
export TARGET_REPO="owner/test-repo"
export GITHUB_RUN_ID="local_dev_123"

# Optional: Enable LangSmith tracing for deep observability
export LANGCHAIN_TRACING_V2="true"
export LANGCHAIN_API_KEY="your-langsmith-api-key"
export LANGCHAIN_PROJECT="seccure-local-dev"
```

---

## 🛠 Testing & Linting

Before opening a pull request, ensure your code passes our linting and type-checking standards. We use `ruff` for fast linting/formatting and `mypy` for static type checking.

```bash
# Format code and check for linting errors
ruff check . --fix
ruff format .

# Run static type checking
mypy agent/
```

---

## 🚀 Pull Requests

1. **Fork the repo** and create your branch from `main`.
2. Ensure your code follows the standard Python PEP-8 style guidelines and passes `ruff` and `mypy`.
3. **Test your changes locally:** Run the agent locally against a safe `TARGET_REPO` to ensure it successfully patches vulnerabilities without regressions.
4. Issue that pull request! Please include a clear description of the problem you're solving and link any related issues.

---

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](./CODE_OF_CONDUCT.md).
