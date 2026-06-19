"""Git and npm shell tools used exclusively by the Coordinator agent.

All shell commands are wrapped in Python subprocess calls.
The LLM never issues raw shell commands — it calls these typed functions.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

_WORKSPACE = Path("/tmp/seccure_workspace")


def _run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    """Run a subprocess command. Returns (returncode, stdout, stderr)."""
    working_dir = cwd or _WORKSPACE

    # Wrap npm/node commands to use nvm and respect .nvmrc
    if cmd[0] in ("npm", "node", "npx"):
        import shlex
        nvm_dir = os.environ.get("NVM_DIR", "/home/seccure/.nvm")
        escaped_cmd = " ".join(shlex.quote(c) for c in cmd)

        bash_script = f"""
        export NVM_DIR="{nvm_dir}"
        [ -s "$NVM_DIR/nvm.sh" ] && \\. "$NVM_DIR/nvm.sh"
        if [ -f .nvmrc ]; then
            # Supress output of nvm install/use unless it fails
            nvm install >/dev/null 2>&1 || true
            nvm use >/dev/null 2>&1 || true
        fi
        {escaped_cmd}
        """
        result = subprocess.run(
            ["bash", "-c", bash_script],
            cwd=str(working_dir),
            capture_output=True,
            text=True,
        )
    else:
        result = subprocess.run(
            cmd,
            cwd=str(working_dir),
            capture_output=True,
            text=True,
        )

    return result.returncode, result.stdout, result.stderr


def clone_repo(repo: str, branch: str) -> str:
    """Clone the target repository's branch into the workspace directory.

    Args:
        repo: Repository in 'owner/repo' format.
        branch: Branch name to clone.

    Returns:
        Confirmation message or error.
    """
    import shutil

    token = os.environ["GITHUB_TOKEN"]
    url = f"https://x-access-token:{token}@github.com/{repo}.git"

    if _WORKSPACE.exists():
        shutil.rmtree(_WORKSPACE)
    _WORKSPACE.mkdir(parents=True)

    code, out, err = _run(
        ["git", "clone", "--branch", branch, "--depth", "1", url, str(_WORKSPACE)],
        cwd=Path("/tmp"),
    )
    if code != 0:
        return f"Error cloning repo: {err}"
    return f"Cloned {repo}@{branch} into {_WORKSPACE}."


def create_fix_branch(branch_name: str) -> str:
    """Create and checkout a new fix branch in the cloned workspace.

    Args:
        branch_name: e.g. 'seccure/auto-fix-20260613'.

    Returns:
        Confirmation or error.
    """
    code, out, err = _run(["git", "checkout", "-b", branch_name])
    if code != 0:
        return f"Error creating branch: {err}"
    return f"Created and checked out branch '{branch_name}'."


def ensure_lockfile() -> str:
    """Ensure package-lock.json exists. Generates it if missing.

    Running 'npm install --package-lock-only' creates the lockfile without
    installing node_modules, avoiding EAUDITNOLOCK errors.

    Returns:
        Status message.
    """
    lockfile = _WORKSPACE / "package-lock.json"
    if lockfile.exists():
        return "package-lock.json already exists."

    pkg_json = _WORKSPACE / "package.json"
    if not pkg_json.exists():
        return "Error: package.json not found in repository root."

    code, out, err = _run(["npm", "install", "--package-lock-only", "--ignore-scripts"])
    if code != 0:
        return f"Error generating package-lock.json: {err}"
    return "Generated package-lock.json via 'npm install --package-lock-only'."


def run_auto_fix(ecosystem: str = "npm") -> str:
    """Run automatic vulnerability patcher if available for the ecosystem.

    Returns:
        JSON string with exit_code, truncated stdout/stderr.
    """
    ecosystem = ecosystem.lower()
    if ecosystem == "npm":
        code, out, err = _run(["npm", "audit", "fix", "--ignore-scripts"])
        return json.dumps(
            {
                "exit_code": code,
                "stdout": out[:3000],
                "stderr": err[:1000],
                "note": "Non-zero exit does not always mean failure — some vulnerabilities may remain.",
            }
        )
    return json.dumps({"error": f"Auto-fix not implemented for ecosystem: {ecosystem}"})


def apply_package_override(package: str, safe_version: str, ecosystem: str = "npm") -> str:
    """Add or update an entry to override nested dependencies.

    Args:
        package: The package name.
        safe_version: The safe version specifier.
        ecosystem: The target ecosystem ("npm" etc).

    Returns:
        Confirmation or error.
    """
    ecosystem = ecosystem.lower()
    if ecosystem == "npm":
        pkg_path = _WORKSPACE / "package.json"
        if not pkg_path.exists():
            return "Error: package.json not found."

        pkg = json.loads(pkg_path.read_text())
        if "overrides" not in pkg:
            pkg["overrides"] = {}
        pkg["overrides"][package] = safe_version
        pkg_path.write_text(json.dumps(pkg, indent=2))

        code, out, err = _run(["npm", "install", "--ignore-scripts"])
        if code != 0:
            return f"Override written but npm install failed: {err[:500]}"
        return f"Added override: {package} -> {safe_version} and ran npm install."

    return f"apply_package_override is not yet supported for ecosystem: {ecosystem}"


def bump_package_version(package: str, target_version: str, ecosystem: str = "npm") -> str:
    """Directly update a dependency's version and reinstall.

    Args:
        package: The package name.
        target_version: The target version string.
        ecosystem: The target ecosystem ("npm", "python", etc).

    Returns:
        Confirmation or error.
    """
    ecosystem = ecosystem.lower()

    if ecosystem == "npm":
        pkg_path = _WORKSPACE / "package.json"
        if not pkg_path.exists():
            return "Error: package.json not found."

        pkg = json.loads(pkg_path.read_text())
        bumped = False
        for dep_key in ("dependencies", "devDependencies", "peerDependencies"):
            if package in pkg.get(dep_key, {}):
                pkg[dep_key][package] = target_version
                bumped = True

        if not bumped:
            return f"'{package}' not found in top-level dependencies — try apply_package_override instead."

        pkg_path.write_text(json.dumps(pkg, indent=2))
        code, out, err = _run(["npm", "install", "--ignore-scripts"])
        if code != 0:
            return f"Version bumped in package.json but npm install failed: {err[:500]}"
        return f"Bumped {package} to {target_version} and ran npm install."

    elif ecosystem in ("python", "pip", "uv"):
        import re
        if not re.match(r"^[<>=^\~]", target_version):
            target_version = f"=={target_version}"

        code, out, err = _run(["uv", "add", f"{package}{target_version}"])
        if code != 0:
            return f"Failed to bump python package {package} using uv: {err}"

        return f"Bumped Python package {package} to {target_version} using uv add."

    return f"Unsupported ecosystem: {ecosystem}"


def check_remaining_vulnerabilities() -> str:
    """Run 'npm audit --json' and return a structured vulnerability summary.

    Returns:
        JSON string with: vulnerability_count, critical, high, moderate, low,
        vulnerabilities (array of {name, severity, via, fix_available}).
    """
    code, out, err = _run(["npm", "audit", "--json"])
    try:
        audit = json.loads(out)
    except json.JSONDecodeError:
        return json.dumps({"error": "Failed to parse npm audit output", "raw": out[:500]})

    meta = audit.get("metadata", {}).get("vulnerabilities", {})
    vulns = audit.get("vulnerabilities", {})

    items = [
        {
            "name": name,
            "severity": info.get("severity", "unknown"),
            "via": [
                v if isinstance(v, str) else v.get("name", "")
                for v in info.get("via", [])
            ],
            "fix_available": info.get("fixAvailable", False),
        }
        for name, info in vulns.items()
    ]

    return json.dumps(
        {
            "vulnerability_count": meta.get("total", len(items)),
            "critical": meta.get("critical", 0),
            "high": meta.get("high", 0),
            "moderate": meta.get("moderate", 0),
            "low": meta.get("low", 0),
            "vulnerabilities": items,
        }
    )


def commit_changes(message: str | None = None) -> str:
    """Commit any changes in package.json, package-lock.json, pyproject.toml, uv.lock, or requirements.txt.

    Args:
        message: Optional commit message. Defaults to standard security fix message.
    """
    commit_msg = message or "fix(deps): automated security patches [seccure]"
    _run(["git", "config", "user.name", "seccure-bot"])
    _run(["git", "config", "user.email", "seccure-bot@users.noreply.github.com"])

    files_to_add = ["package.json", "package-lock.json", "pyproject.toml", "uv.lock", "requirements.txt"]
    existing_files = [f for f in files_to_add if (_WORKSPACE / f).exists()]
    if existing_files:
        _run(["git", "add"] + existing_files)

    code, out, err = _run(["git", "diff", "--staged", "--quiet"])
    if code != 0:
        # Changes are staged, now commit
        code, out, err = _run(["git", "commit", "-m", commit_msg])
        if code != 0:
            return f"Commit failed: {err}"
        return f"Committed: {commit_msg}"

    return "Nothing to commit — no changes were made to tracked files."


def push_branch(branch_name: str, repo: str) -> str:
    """Push the fix branch to the remote repository using GITHUB_TOKEN.

    Args:
        branch_name: The local branch name to push.
        repo: The repository in 'owner/repo' format.

    Returns:
        Confirmation or error.
    """
    token = os.environ["GITHUB_TOKEN"]
    remote_url = f"https://x-access-token:{token}@github.com/{repo}.git"
    _run(["git", "remote", "set-url", "origin", remote_url])
    code, out, err = _run(["git", "push", "origin", branch_name])
    if code != 0:
        return f"Push failed: {err}"
    return f"Pushed branch '{branch_name}' to {repo}."

def get_commit_messages(base_branch: str, head_branch: str) -> list[str]:
    """
    Retrieves commit messages between the base_branch and head_branch locally.
    
    Args:
        base_branch (str): The branch being merged into (e.g., 'main')
        head_branch (str): The feature branch with new commits
        
    Returns:
        list[str]: A list of commit messages.
    """
    code, out, err = _run(["git", "log", f"{base_branch}..{head_branch}", "--format=%B"])
    if code != 0:
        # Fallback if base_branch is not available locally, maybe try origin/base_branch
        code, out, err = _run(["git", "log", f"origin/{base_branch}..{head_branch}", "--format=%B"])
        if code != 0:
            return []

    # Split by empty line separating commits, or just split by some delimiter
    # Actually --format=%B just prints the raw body.
    # To get individual messages reliably, we can use a custom delimiter.
    code, out, err = _run(["git", "log", f"{base_branch}..{head_branch}", "--format=%B%n---END_COMMIT---"])
    if code != 0:
        code, out, err = _run(["git", "log", f"origin/{base_branch}..{head_branch}", "--format=%B%n---END_COMMIT---"])
        if code != 0:
            return []

    messages = out.split("---END_COMMIT---")
    return [m.strip() for m in messages if m.strip()]
