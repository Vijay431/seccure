import pytest
import asyncio
from typing import Any
from unittest.mock import patch

from google.antigravity import ToolContext
from agent.subagents.audit_fanout import run_audit_fanout
from agent.config import ToolResult

class DummyContext:
    def __init__(self):
        self.state = {}

@pytest.mark.asyncio
async def test_run_audit_fanout_handles_permission_error():
    ctx = DummyContext()  # type: ignore
    
    async def mock_issue_tool(ctx: Any) -> str:
        raise PermissionError("Access denied")
        
    async def mock_pr_tool(ctx: Any) -> str:
        return "[]"
        
    async def mock_dep_alert_tool(ctx: Any) -> str:
        return "[]"
        
    async def mock_code_alert_tool(ctx: Any) -> str:
        return "[]"

    result = await run_audit_fanout(
        ctx,  # type: ignore
        issue_tool=mock_issue_tool,
        pr_tool=mock_pr_tool,
        dependabot_alert_tool=mock_dep_alert_tool,
        code_scanning_tool=mock_code_alert_tool,
    )
    
    assert isinstance(result, ToolResult)
    assert result.ok is False
    assert result.fatal is True
    assert result.message == "Access denied"

@pytest.mark.asyncio
@patch('agent.subagents.audit_fanout.write_state_section')
async def test_run_audit_fanout_success(mock_write_state):
    ctx = DummyContext()  # type: ignore
    
    async def mock_issue_tool(ctx: Any) -> str:
        return '[{"issue_number": 1, "title": "Security bug", "url": "http://test"}]'
        
    async def mock_pr_tool(ctx: Any) -> str:
        return '[{"number": 2, "title": "bump foo from 1.0 to 2.0"}]'
        
    async def mock_dep_alert_tool(ctx: Any) -> str:
        return '[{"package": "bar", "severity": "high"}]'
        
    async def mock_code_alert_tool(ctx: Any) -> str:
        return '[{"rule_id": "rule-1", "severity": "critical", "alert_number": 42}]'

    result = await run_audit_fanout(
        ctx,  # type: ignore
        issue_tool=mock_issue_tool,
        pr_tool=mock_pr_tool,
        dependabot_alert_tool=mock_dep_alert_tool,
        code_scanning_tool=mock_code_alert_tool,
    )
    
    assert isinstance(result, ToolResult)
    assert result.ok is True
    assert len(result.data["security_issues"]) == 1
    assert result.data["security_issues"][0]["issue_number"] == 1
    assert len(result.data["dependency_findings"]) == 2 # 1 PR + 1 dep alert
    assert len(result.data["code_scanning_findings"]) == 1
    assert mock_write_state.call_count == 4

