import os
from unittest.mock import MagicMock, patch

from src.main import _verify_github_access
from src.utils.repo_utils import sanitize_repo_name


def test_sanitize_repo_name():
    assert sanitize_repo_name("owner/repo") == "owner/repo"
    assert sanitize_repo_name("owner/repo.git") == "owner/repo"
    assert sanitize_repo_name("https://github.com/owner/repo") == "owner/repo"
    assert sanitize_repo_name("https://github.com/owner/repo.git") == "owner/repo"
    assert sanitize_repo_name("git@github.com:owner/repo.git") == "owner/repo"
    assert sanitize_repo_name("") == ""


def test_verify_github_access_no_token():
    with patch("sys.exit") as mock_exit:
        mock_exit.side_effect = SystemExit(1)
        try:
            _verify_github_access("owner/repo", "")
        except SystemExit:
            pass
        mock_exit.assert_called_once_with(1)


def test_verify_github_access_mismatch():
    with patch.dict(
        os.environ, {"GITHUB_ACTIONS": "true", "GITHUB_REPOSITORY": "owner/repo"}
    ):
        with patch("sys.exit") as mock_exit:
            mock_exit.side_effect = SystemExit(1)
            try:
                _verify_github_access("hacker/repo", "token")
            except SystemExit:
                pass
            mock_exit.assert_called_once_with(1)


@patch("urllib.request.urlopen")
def test_verify_github_access_http_error(mock_urlopen):
    import urllib.error

    mock_urlopen.side_effect = urllib.error.HTTPError("url", 403, "Forbidden", {}, None)

    with patch("sys.exit") as mock_exit:
        mock_exit.side_effect = SystemExit(1)
        try:
            _verify_github_access("owner/repo", "token")
        except SystemExit:
            pass
        mock_exit.assert_called_once_with(1)


@patch("urllib.request.urlopen")
def test_verify_github_access_success(mock_urlopen):
    mock_response = MagicMock()
    mock_response.status = 200
    mock_urlopen.return_value.__enter__.return_value = mock_response

    with patch("sys.exit") as mock_exit:
        _verify_github_access("owner/repo", "token")
        mock_exit.assert_not_called()
