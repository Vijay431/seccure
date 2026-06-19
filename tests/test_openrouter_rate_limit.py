
import httpx
import pytest
from openai import RateLimitError

from src.lib.resilient_runner import ResilientOpenRouterAgent


@pytest.mark.asyncio
async def test_resilient_agent_retries_on_rate_limit(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key")
    agent = ResilientOpenRouterAgent(system_instructions="You are a test agent.", base_delay=0.01)

    call_count = 0

    async def mock_create(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise RateLimitError(
                message="Rate limit exceeded",
                response=httpx.Response(status_code=429, request=httpx.Request("POST", "url")),
                body=None,
            )
        class MockMessage:
            role = "assistant"
            content = "Hello there!"
            tool_calls = None
        class MockChoice:
            message = MockMessage()
        class MockResponse:
            choices = [MockChoice()]
            usage = None
        return MockResponse()

    agent.client.chat.completions.create = mock_create

    response = await agent.chat("Hello")
    assert await response.text() == "Hello there!"
    assert call_count == 3

