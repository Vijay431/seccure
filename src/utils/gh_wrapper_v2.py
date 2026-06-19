import json
import os
import subprocess
import sys
from typing import Any

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


def check_gh_installed() -> None:
    """Check if the gh CLI is installed. Fails fast if not."""
    try:
        subprocess.run(["gh", "--version"], capture_output=True, check=True, shell=False)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("ERROR: GitHub CLI ('gh') is not installed or not in PATH.", file=sys.stderr)
        sys.exit(1)

# Fail fast on startup if gh is missing
check_gh_installed()

def run_gh_command(args: list[str]) -> Any:
    """
    Executes a gh CLI command and returns the parsed JSON output.
    Raises RuntimeError with stderr if the command fails after all retries.
    """
    try:
        return _run_gh_command_with_retry(args)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"GitHub CLI error: {exc.stderr}") from exc

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(subprocess.CalledProcessError),
    reraise=True
)
def _run_gh_command_with_retry(args: list[str]) -> Any:
    cmd = ["gh"] + args

    # Inject GH_PROMPT_DISABLED=1 to prevent hanging on interactive prompts
    env = os.environ.copy()
    env["GH_PROMPT_DISABLED"] = "1"

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True,
        shell=False,
        timeout=300,
        env=env
    )

    if not result.stdout.strip():
        return None

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return result.stdout.strip()
