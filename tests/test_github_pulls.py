
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
