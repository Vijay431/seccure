import asyncio
import os
import sys

# Ensure python path
sys.path.insert(0, os.path.abspath("."))

from src.utils.mcp_client import get_mcp_manager


async def test_mcp_interceptor():
    os.environ["TARGET_REPO"] = "vijay/seccure"
    os.environ["GITHUB_TOKEN"] = "fake_token_for_test"

    manager = get_mcp_manager()
    try:
        # call_tool_with_retry will start the server and invoke
        await manager.call_tool_with_retry(
            "get_file_contents", {"repo": "torvalds/linux", "path": "README.md"}
        )
        print("FAIL: The call should have been intercepted and blocked!")
        sys.exit(1)
    except ValueError as e:
        if "forbidden" in str(e).lower() and "target_repo" in str(e).lower():
            print("PASS: The cross-repo call was blocked.")
            sys.exit(0)
        else:
            print(f"FAIL: Expected forbidden error, got: {e}")
            sys.exit(1)
    except Exception as e:
        print(f"FAIL: The call failed for another reason (no interceptor): {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_mcp_interceptor())
