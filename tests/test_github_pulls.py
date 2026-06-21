from src.utils.github_pulls import (
    extract_references_from_commits,
)


def test_extract_references_from_commits():
    messages = [
        "Fix bug in parser (Fixes #123)",
        "This closes GH-456 and mentions PR-789",
        "Another mention of #123 and also #999",
        "No references here",
    ]
    refs = extract_references_from_commits(messages)
    assert refs == ["123", "456", "789", "999"]


def test_get_owner_repo_edge_cases():
    import os
    from unittest.mock import patch

    from src.utils.github_pulls import _get_owner_repo

    cases = [
        "owner/repo",
        "owner/repo.git",
        "https://github.com/owner/repo",
        "https://github.com/owner/repo.git",
        "git@github.com:owner/repo.git",
    ]

    for case in cases:
        with patch.dict(os.environ, {"TARGET_REPO": case, "GITHUB_REPOSITORY": ""}):
            owner, repo = _get_owner_repo()
            assert owner == "owner"
            assert repo == "repo"
