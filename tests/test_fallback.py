import pytest

from src.lib.resilient_runner import ResilientOpenRouterAgent


@pytest.mark.asyncio
async def test_agent_initialization():
    agent = ResilientOpenRouterAgent("system", max_retries=2)
    assert agent.max_retries == 2
    assert agent.base_delay == 2.0
