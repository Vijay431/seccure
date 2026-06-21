import os
from unittest.mock import AsyncMock, patch

import pytest

from src.lib.resilient_runner import ResilientOpenRouterAgent
from src.pipelines.coordinator.agent import build_coordinator


def test_build_coordinator():
    agent = build_coordinator("System Prompt")
    assert isinstance(agent, ResilientOpenRouterAgent)
    assert agent.system_prompt == "System Prompt"
    # Should have tools
    assert len(agent.tools) > 0
    # Should have invoke_subagent tool
    tool_names = [t.__name__ for t in agent.tools]
    assert "invoke_subagent" in tool_names


@pytest.mark.asyncio
@patch("subprocess.run")
@patch("src.lib.state.write_state_section")
async def test_coordinator_teardown_on_exception(mock_write_state, mock_subproc):
    with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": "/tmp/dummy_summary.md"}):
        mock_write_state.__name__ = "write_state_section"
        agent = build_coordinator("System Prompt")

        # We need to mock super().chat. Since CoordinatorAgent inherits from ResilientOpenRouterAgent
        # we can mock its chat.
        with patch(
            "src.lib.resilient_runner.ResilientOpenRouterAgent.chat",
            new_callable=AsyncMock,
        ) as mock_super_chat:
            mock_super_chat.side_effect = Exception("Test failure")

            with pytest.raises(Exception, match="Test failure"):
                await agent.chat("test")

            # verify git reset --hard was called
            calls = [c.args[0] for c in mock_subproc.mock_calls if c.args]
            assert ["git", "reset", "--hard"] in calls
            assert ["git", "clean", "-fd"] in calls

            # verify state was written
            write_calls = [c.args for c in mock_write_state.mock_calls]
            assert ("status", "error") in write_calls
            assert ("errors", ["Test failure"]) in write_calls
