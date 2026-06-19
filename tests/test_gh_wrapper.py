import subprocess
import json
import pytest
from unittest.mock import patch, MagicMock
from agent.tools.gh_wrapper import run_gh_command

@patch('agent.tools.gh_wrapper.subprocess.run')
def test_run_gh_command_success(mock_run):
    # Mock successful JSON response
    mock_result = MagicMock()
    mock_result.stdout = json.dumps([{"id": 1, "title": "Test"}])
    mock_run.return_value = mock_result

    result = run_gh_command(["issue", "list", "--json", "id,title"])
    
    assert len(result) == 1
    assert result[0]["title"] == "Test"
    mock_run.assert_called_once()
    args, kwargs = mock_run.call_args
    assert args[0] == ["gh", "issue", "list", "--json", "id,title"]
    assert kwargs.get("capture_output") is True

@patch('agent.tools.gh_wrapper.subprocess.run')
def test_run_gh_command_empty(mock_run):
    mock_result = MagicMock()
    mock_result.stdout = "   \n"
    mock_run.return_value = mock_result

    result = run_gh_command(["pr", "create"])
    
    assert result is None

@patch('agent.tools.gh_wrapper.subprocess.run')
def test_run_gh_command_retry_then_success(mock_run):
    # Setup mock to fail once then succeed
    mock_fail = subprocess.CalledProcessError(1, ["gh"])
    mock_success = MagicMock()
    mock_success.stdout = json.dumps({"status": "ok"})
    
    mock_run.side_effect = [mock_fail, mock_success]

    result = run_gh_command(["api", "some/endpoint"])
    
    assert result == {"status": "ok"}
    assert mock_run.call_count == 2
