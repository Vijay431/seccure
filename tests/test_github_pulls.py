import json
from unittest.mock import MagicMock, patch

from src.utils.github_pulls import (
    bulk_validate_references,
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

@patch("src.utils.github_pulls.subprocess.run")
def test_bulk_validate_references_success(mock_run):
    # Mock repo info
    repo_mock = MagicMock()
    repo_mock.stdout = json.dumps({"owner": {"login": "testowner"}, "name": "testrepo"})

    # Mock graphql success
    gql_mock = MagicMock()
    gql_mock.stdout = json.dumps({
        "data": {
            "repository": {
                "ref_123": {"__typename": "Issue"},
                "ref_456": {"__typename": "PullRequest"},
                "ref_789": None  # invalid reference
            }
        }
    })

    mock_run.side_effect = [repo_mock, gql_mock]

    valid_refs = bulk_validate_references(["123", "456", "789"])
    assert valid_refs == ["123", "456"]

@patch("src.utils.github_pulls.subprocess.run")
def test_bulk_validate_references_fallback_on_error(mock_run):
    mock_run.side_effect = Exception("GH CLI not found")
    # If the gh cli fails entirely, it should fallback to returning original references
    refs = ["123", "456"]
    assert bulk_validate_references(refs) == refs
