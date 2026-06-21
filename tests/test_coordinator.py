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
