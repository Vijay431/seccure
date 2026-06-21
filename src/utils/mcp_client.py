import asyncio
import logging
import os
from typing import Any

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

logger = logging.getLogger(__name__)


class RobustMCPToolWrapper(BaseTool):
    name: str
    description: str
    args_schema: Any
    tool_name: str
    mcp_manager: Any

    def _run(self, *args, **kwargs):
        raise NotImplementedError("RobustMCPToolWrapper only supports async")

    async def _arun(self, *args, **kwargs):
        return await self.mcp_manager.call_tool_with_retry(self.tool_name, kwargs)


class RobustMCPManager:
    def __init__(self, retry_limit: int = 3):
        self.retry_limit = retry_limit
        self.client = None
        self._tools_cache: dict[str, Any] = {}
        self._lock = asyncio.Lock()

        self.target_repo = os.environ.get("TARGET_REPO")
        if not self.target_repo:
            raise ValueError(
                "TARGET_REPO environment variable is not set. Cannot initialize MCP client."
            )

    async def __aenter__(self):
        await self.start_server()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop_server()

    async def start_server(self):
        server_config = {
            "github": {
                "command": "docker",
                "args": [
                    "run",
                    "-i",
                    "--rm",
                    "-e",
                    "GITHUB_PERSONAL_ACCESS_TOKEN",
                    "-e",
                    "GITHUB_HOST",
                    "ghcr.io/github/github-mcp-server",
                ],
                "transport": "stdio",
                "env": {
                    "GITHUB_PERSONAL_ACCESS_TOKEN": os.environ.get("GITHUB_TOKEN", ""),
                    "GITHUB_HOST": os.environ.get("GITHUB_HOST", "https://github.com"),
                    "PATH": os.environ.get("PATH", ""),
                },
            }
        }
        self.client = MultiServerMCPClient(server_config)

        tools = await self.client.get_tools()
        for t in tools:
            self._tools_cache[t.name] = t

    async def stop_server(self):
        if self.client:
            self.client = None

    async def restart_server(self):
        async with self._lock:
            logger.info("Restarting MCP Server...")
            await self.stop_server()
            await asyncio.sleep(1)
            await self.start_server()

    async def get_tools(self) -> list[BaseTool]:
        async with self._lock:
            if not self.client:
                await self.start_server()

            wrapped_tools: list[BaseTool] = []
            for _name, tool in self._tools_cache.items():
                wrapped_tools.append(
                    RobustMCPToolWrapper(
                        name=tool.name,
                        description=tool.description,
                        args_schema=tool.args_schema,
                        tool_name=tool.name,
                        mcp_manager=self,
                    )
                )
            return wrapped_tools

    async def call_tool_with_retry(self, tool_name: str, kwargs_dict: dict):
        # US2: Intercept requests to other repos
        repo_arg = kwargs_dict.get("repo")
        owner_arg = kwargs_dict.get("owner")

        repo_to_check = None
        if repo_arg and "/" in repo_arg:
            repo_to_check = repo_arg
        elif owner_arg and repo_arg:
            repo_to_check = f"{owner_arg}/{repo_arg}"

        if (
            repo_to_check
            and self.target_repo
            and repo_to_check.lower() != self.target_repo.lower()
        ):
            msg = f"Access to repo {repo_to_check} is forbidden. Only TARGET_REPO {self.target_repo} is allowed."
            logger.error(msg)
            import sys

            sys.exit(1)

        attempts = 0
        while attempts <= self.retry_limit:
            try:
                actual_tool = self._tools_cache.get(tool_name)
                if not actual_tool:
                    raise ValueError(f"Tool {tool_name} not found in MCP server")

                return await actual_tool.ainvoke(kwargs_dict)
            except Exception as e:
                attempts += 1
                logger.warning(
                    f"MCP Tool {tool_name} failed with error: {e}. Attempt {attempts}/{self.retry_limit}"
                )
                if attempts > self.retry_limit:
                    logger.error(
                        f"MCP Server retry limit reached for tool {tool_name}."
                    )
                    raise

                await self.restart_server()


_global_mcp_manager = None


def get_mcp_manager() -> RobustMCPManager:
    global _global_mcp_manager
    if _global_mcp_manager is None:
        _global_mcp_manager = RobustMCPManager()
    return _global_mcp_manager
