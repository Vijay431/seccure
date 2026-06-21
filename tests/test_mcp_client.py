import pytest

from src.utils.mcp_client import get_mcp_manager


@pytest.mark.asyncio
async def test_mcp_client_interceptor(monkeypatch):
    monkeypatch.setenv("TARGET_REPO", "vijay/seccure")
    manager = get_mcp_manager()

    # Reset cache
    manager.target_repo = "vijay/seccure"

    # Should raise SystemExit
    with pytest.raises(SystemExit) as exc:
        await manager.call_tool_with_retry(
            "get_file_contents", {"repo": "torvalds/linux"}
        )

    assert exc.value.code == 1
