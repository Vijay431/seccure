import os
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_end_to_end_pipeline():
    with patch("src.main._verify_github_access") as mock_verify:
        with patch("src.main.load_constraints_text", return_value=""):
            with patch("src.main.build_coordinator") as mock_build_coord:
                with patch("src.utils.mcp_client.get_mcp_manager") as mock_mcp:
                    from unittest.mock import AsyncMock

                    mock_mcp.return_value.stop_server = AsyncMock()
                    mock_agent = MagicMock()
                    mock_response = AsyncMock()
                    mock_response.text.return_value = "Success"
                    mock_agent.chat = AsyncMock(return_value=mock_response)

                    # Mock context manager
                    mock_agent.__aenter__.return_value = mock_agent
                    mock_agent.__aexit__.return_value = False

                    mock_usage = MagicMock()
                    mock_usage.prompt_token_count = 10
                    mock_usage.candidates_token_count = 20
                    mock_usage.thoughts_token_count = 5
                    mock_usage.total_token_count = 35
                    mock_agent.conversation.total_usage = mock_usage

                    mock_build_coord.return_value = mock_agent

                    with patch.dict(
                        os.environ,
                        {
                            "GITHUB_RUN_ID": "123",
                            "TARGET_REPO": "owner/repo",
                            "GITHUB_TOKEN": "token",
                            "GITHUB_WORKSPACE": "/tmp",
                        },
                    ):
                        from src.main import main

                        await main()

                        mock_verify.assert_called_once_with("owner/repo", "token")
                        mock_agent.chat.assert_called_once()
                        mock_mcp.return_value.stop_server.assert_called_once()
