from src.pipelines.subagents.audit_issue_agent import build_audit_issue_agent
from src.pipelines.subagents.audit_pr_agent import build_audit_pr_agent
from src.pipelines.subagents.audit_security_agent import build_audit_security_agent
from src.pipelines.subagents.pr_agent import build_pr_agent


def test_subagent_explicit_allowlist():
    # Verify they instantiate with defaults
    issue_agent = build_audit_issue_agent()
    pr_audit_agent = build_audit_pr_agent()
    security_agent = build_audit_security_agent()
    pr_agent = build_pr_agent()

    # Assert they have tools
    assert len(issue_agent.tools) == 3
    assert len(pr_audit_agent.tools) == 3
    assert len(security_agent.tools) == 4
    assert len(pr_agent.tools) == 6

    # Verify we can pass custom tools
    def dummy_tool():
        pass

    custom_agent = build_audit_issue_agent(tools=[dummy_tool])
    assert len(custom_agent.tools) == 1
    assert custom_agent.tools[0].__name__ == "dummy_tool"
