from google.antigravity import ToolContext


async def list_dependabot_alerts(ctx: ToolContext) -> str:
    """Fetch all open Dependabot vulnerability alerts."""
    raise SystemExit(
        "Unsupported error: No direct equivalent tool in github-mcp-server for dependabot alerts"
    )


async def list_code_scanning_alerts(ctx: ToolContext) -> str:
    """Fetch all open code-scanning alerts.

    Raises:
        SystemExit: The github-mcp-server does not support the code scanning API.
    """
    raise SystemExit(
        "Unsupported error: No direct equivalent tool in github-mcp-server for code scanning alerts"
    )
