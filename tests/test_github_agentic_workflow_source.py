from pathlib import Path


WORKFLOW = Path(".github/workflows/github-agentic-seccure.md")


def test_github_agentic_workflow_source_matches_seccure_contract() -> None:
    text = WORKFLOW.read_text()
    frontmatter = text.split("---", 2)[1]

    assert text.startswith("---\n")
    assert "workflow_dispatch:" in text
    assert "schedule:" not in frontmatter
    assert "engine: codex" in text
    assert "OPENROUTER_API_KEY" in text
    assert "GEMINI_API_KEY" not in text
    assert "python agent/main.py" in text
    assert "GITHUB_RUN_ID" in text
    assert "TARGET_REPO" in text
    assert "ADDITIONAL_CONSTRAINTS" in text
    assert "ECOSYSTEM" in text
    assert "seccure_state_${{ github.run_id }}.json" in text
    assert "seccure_events_${{ github.run_id }}.jsonl" in text
    assert ".github/workflows/seccure.yml" in text
