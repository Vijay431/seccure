# seccure Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-06-19

## Active Technologies
- Python >= 3.12 + Google Agent Development Kit (ADK), Pydantic, LangSmith, pinecone-client (001-seccure-migration)
- Pinecone Vector Database (isolated by repository name namespaces) (001-seccure-migration)
- Python >= 3.12 + Google Agent Development Kit (ADK), Pydantic, LangSmith, tenacity (001-gh-cli-integration)
- Python 3.12 + Google Agent Development Kit (ADK), Pydantic, tenacity (002-gh-cli-hardening)
- Python 3.12 (matches existing seccure stack) + `src.utils.github_pulls`, `src.utils.git_tools`, PyGithub (or REST API via `requests`), `re` for parsing commits (001-fix-pr-agent)
- N/A (Pinecone is used elsewhere, here we just use GitHub API state) (001-fix-pr-agent)
- Python >= 3.12 + None new added. (001-cleanup-scripts)

- Python >= 3.12 + Google Agent Development Kit (ADK), Pydantic, LangSmith (001-seccure-migration)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python >= 3.12: Follow standard conventions

## Recent Changes
- 001-cleanup-scripts: Added Python >= 3.12 + None new added.
- 001-cleanup-scripts: Added Python >= 3.12 + None new added.
- 001-fix-pr-agent: Added Python 3.12 (matches existing seccure stack) + `src.utils.github_pulls`, `src.utils.git_tools`, PyGithub (or REST API via `requests`), `re` for parsing commits


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
