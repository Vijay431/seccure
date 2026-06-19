# Quickstart: PR Agent Fix

This document explains how to test the new PR Agent feature locally.

## Testing Locally

1. Check out the feature branch:
   ```bash
   git checkout 001-fix-pr-agent
   ```
2. Make sure you have tests running successfully:
   ```bash
   pytest tests/
   ```
3. To test the `get_commit_messages` function, you can run the agent locally against a test repository that has commits mentioning issues (e.g. `Fixes #12`).
   ```bash
   export GITHUB_TOKEN=your_token
   python -m agent.main --repo your_user/test_repo
   ```
4. Verify that the PR opened by the agent preserves any manual description you add, and correctly lists `Fixes #12` in the automated section.
