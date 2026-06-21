import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.config.config import (
    CodeScanningFinding,
    DependencyFinding,
    FixResult,
    IssueItem,
    SeccureState,
    ToolResult,
)
from src.lib.openrouter_runner import OpenRouterAgent
from src.pipelines.coordinator.agent import build_coordinator
from src.pipelines.coordinator.runtime import should_exit_for_tool_result
from src.pipelines.fixers.registry import route_finding
from src.pipelines.subagents.audit_fanout import (
    enrich_dependabot_pr,
    infer_ecosystem_from_files,
    run_audit_fanout,
)
from src.pipelines.subagents.audit_issue_agent import build_audit_issue_agent
from src.pipelines.subagents.audit_pr_agent import build_audit_pr_agent
from src.pipelines.subagents.audit_security_agent import build_audit_security_agent
from src.pipelines.subagents.pr_agent import build_pr_agent
from src.utils.events import redact_text
from src.utils.github_pulls import (
    ATTEMPT_MARKER,
    extract_attempt_count,
    render_pr_title_body,
    with_attempt_marker,
)


def test_dependency_and_code_scanning_findings_are_separate() -> None:
    dependency = DependencyFinding(
        source="dependabot_alert",
        package="django",
        ecosystem="pip",
        severity="high",
        cve_id="CVE-2026-0001",
        patched_version="5.0.1",
        advisory_url="https://github.com/advisories/GHSA-test",
        alert_number=11,
    )
    code_scanning = CodeScanningFinding(
        source="code_scanning",
        rule_id="py/path-injection",
        severity="critical",
        description="Unsafe path usage",
        url="https://github.com/o/r/security/code-scanning/1",
        alert_number=9,
    )

    assert dependency.package == "django"
    assert code_scanning.rule_id == "py/path-injection"

    with pytest.raises(ValidationError):
        DependencyFinding(
            source="code_scanning",
            package="",
            ecosystem="",
            severity="high",
        )


def test_fatal_tool_result_stops_coordinator() -> None:
    fatal = ToolResult(ok=False, fatal=True, message="GitHub security API denied")
    warning = ToolResult(ok=False, fatal=False, message="Code scanning disabled")

    assert should_exit_for_tool_result(fatal) is True
    assert should_exit_for_tool_result(warning) is False


def test_pr_body_attempt_marker_round_trip_and_limit() -> None:
    body = with_attempt_marker("## Body", 2)

    assert ATTEMPT_MARKER in body
    assert extract_attempt_count(body) == 2
    assert extract_attempt_count("no marker") == 0


def test_dependabot_pr_enrichment_from_changed_files() -> None:
    enriched = enrich_dependabot_pr(
        {
            "number": 7,
            "title": "chore(deps): bump requests from 2.31.0 to 2.32.0",
            "html_url": "https://github.com/o/r/pull/7",
        },
        ["requirements.txt", "src/app.py"],
    )

    assert enriched.package == "requests"
    assert enriched.ecosystem == "pip"
    assert enriched.from_version == "2.31.0"
    assert enriched.to_version == "2.32.0"
    assert infer_ecosystem_from_files(["pnpm-lock.yaml"]) == "pnpm"


def test_supported_and_unsupported_ecosystem_routing() -> None:
    node = DependencyFinding(source="dependabot_pr", package="vite", ecosystem="npm")
    python = DependencyFinding(source="issue", package="flask", ecosystem="pip")
    go = DependencyFinding(
        source="dependabot_alert",
        package="x/net",
        ecosystem="gomod",
    )

    assert route_finding(node).supported is True
    assert route_finding(python).supported is True
    unsupported = route_finding(go)
    assert unsupported.supported is False
    assert unsupported.conflict_reason == "unsupported ecosystem fixer: gomod"


def test_deterministic_pr_rendering_includes_closes_and_labels_intent() -> None:
    state = SeccureState(
        run_id="1",
        repo="owner/repo",
        attempt_count=1,
        fix_results=[
            FixResult(
                package="vite",
                fixed=True,
                strategy="npm_audit_fix",
                from_version="5.0.0",
                to_version="5.0.1",
                cve_id="CVE-2026-0002",
                severity="high",
            )
        ],
        dependabot_prs=[
            DependencyFinding(
                source="dependabot_pr",
                package="vite",
                ecosystem="npm",
                pr_number=8,
            )
        ],
        security_issues=[
            IssueItem(
                issue_number=22,
                title="Security: vite",
                labels=["security"],
                url="https://github.com/o/r/issues/22",
            )
        ],
    )

    title, body = render_pr_title_body(state)

    assert title == "fix(deps): automated Seccure security updates"
    assert "- Closes #8" in body
    assert "- Closes #22" in body
    assert "<!-- seccure-attempt-count:1 -->" in body


def test_redaction_removes_tokens_from_jsonl_payload(tmp_path: Path) -> None:
    secret = "ghp_abcdefghijklmnopqrstuvwxyz1234567890"
    payload = json.dumps({"url": f"https://x-access-token:{secret}@github.com/o/r.git"})

    redacted = redact_text(payload)

    assert secret not in redacted
    assert "[REDACTED]" in redacted


def test_openrouter_schema_hides_injected_audit_fanout_parameters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    agent = OpenRouterAgent(system_instructions="test", tools=[run_audit_fanout])

    schema = agent._get_tool_schemas()[0]["function"]["parameters"]

    assert schema["properties"] == {}
    assert schema["required"] == []


def test_openrouter_serializes_pydantic_tool_results_as_json() -> None:
    result = ToolResult(ok=True, fatal=False, message="done", data={"count": 1})

    serialized = OpenRouterAgent._serialize_tool_result(result)

    assert json.loads(serialized) == {
        "ok": True,
        "fatal": False,
        "message": "done",
        "data": {"count": 1},
        "reasoning_summary": None,
    }


def test_agent_builders_always_use_openrouter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("LLM_PROVIDER", "antigravity")

    assert isinstance(build_coordinator("system"), OpenRouterAgent)
    assert isinstance(build_pr_agent(), OpenRouterAgent)
    assert isinstance(build_audit_issue_agent(), OpenRouterAgent)
    assert isinstance(build_audit_pr_agent(), OpenRouterAgent)
    assert isinstance(build_audit_security_agent(), OpenRouterAgent)
