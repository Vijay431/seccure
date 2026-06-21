from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.pipelines.subagents.audit_fanout import run_audit_fanout


@pytest.mark.asyncio
@patch("src.pipelines.subagents.audit_issue_agent.build_audit_issue_agent")
@patch("src.pipelines.subagents.audit_pr_agent.build_audit_pr_agent")
@patch("src.pipelines.subagents.audit_security_agent.build_audit_security_agent")
async def test_run_audit_fanout_success(mock_sec, mock_pr, mock_iss):
    mock_agent = MagicMock()
    mock_agent.__aenter__ = AsyncMock(return_value=mock_agent)
    mock_agent.__aexit__ = AsyncMock(return_value=False)

    mock_response = MagicMock()
    mock_agent.chat = AsyncMock(return_value=mock_response)

    mock_sec.return_value = mock_agent
    mock_pr.return_value = mock_agent
    mock_iss.return_value = mock_agent

    result = await run_audit_fanout()
    assert result.ok
    assert not result.fatal


@pytest.mark.asyncio
@patch("src.pipelines.subagents.audit_issue_agent.build_audit_issue_agent")
@patch("src.pipelines.subagents.audit_pr_agent.build_audit_pr_agent")
@patch("src.pipelines.subagents.audit_security_agent.build_audit_security_agent")
async def test_run_audit_fanout_handles_permission_error(mock_sec, mock_pr, mock_iss):
    mock_agent = MagicMock()
    mock_agent.__aenter__ = AsyncMock(return_value=mock_agent)
    mock_agent.__aexit__ = AsyncMock(return_value=False)

    mock_agent.chat = AsyncMock(side_effect=PermissionError("Access denied"))

    mock_sec.return_value = mock_agent
    mock_pr.return_value = mock_agent
    mock_iss.return_value = mock_agent

    result = await run_audit_fanout()
    assert not result.ok
    assert result.fatal
    assert "Access denied" in result.message
