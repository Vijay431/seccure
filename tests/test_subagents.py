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
    assert len(issue_agent.tools) == 1
    assert issue_agent.tools[0].__name__ == "list_security_issues"

    assert len(pr_audit_agent.tools) == 1
    assert pr_audit_agent.tools[0].__name__ == "list_dependabot_prs"

    assert len(security_agent.tools) == 2
    assert {t.__name__ for t in security_agent.tools} == {
        "list_dependabot_alerts",
        "list_code_scanning_alerts",
    }

    assert len(pr_agent.tools) == 6
    assert {t.__name__ for t in pr_agent.tools} == {
        "read_state",
        "write_state_section",
        "create_fix_branch",
        "commit_changes",
        "push_branch",
        "upsert_seccure_pr",
    }

    # Verify we can pass custom tools
    def dummy_tool():
        pass

    custom_issue_agent = build_audit_issue_agent(tools=[dummy_tool])
    assert len(custom_issue_agent.tools) == 1
    assert custom_issue_agent.tools[0].__name__ == "dummy_tool"

    custom_pr_audit_agent = build_audit_pr_agent(tools=[dummy_tool])
    assert len(custom_pr_audit_agent.tools) == 1
    assert custom_pr_audit_agent.tools[0].__name__ == "dummy_tool"

    custom_security_agent = build_audit_security_agent(tools=[dummy_tool])
    assert len(custom_security_agent.tools) == 1
    assert custom_security_agent.tools[0].__name__ == "dummy_tool"

    custom_pr_agent = build_pr_agent(tools=[dummy_tool])
    assert len(custom_pr_agent.tools) == 1
    assert custom_pr_agent.tools[0].__name__ == "dummy_tool"
