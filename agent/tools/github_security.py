import json
import subprocess
from google.antigravity import ToolContext
from agent.tools.gh_wrapper import run_gh_command

def list_dependabot_alerts(ctx: ToolContext) -> str:
    """Fetch all open Dependabot vulnerability alerts."""
    cached = ctx.get_state("raw_dependabot_alerts")
    if cached:
        return cached

    try:
        data = run_gh_command([
            "api", "/repos/{owner}/{repo}/dependabot/alerts",
            "-X", "GET",
            "-f", "state=open",
            "--paginate"
        ])
    except subprocess.CalledProcessError as exc:
        if "403" in str(exc) or "404" in str(exc):
            if "403" in str(exc):
                raise PermissionError("GitHub Dependabot alerts API returned 403; security_events permission is required.") from exc
            data = []
        else:
            raise

    results = []
    if data:
        for alert in data:
            sa = alert.get("security_advisory", {})
            sv = alert.get("security_vulnerability", {})
            identifiers = sa.get("identifiers", [])
            cve_id = next(
                (i["value"] for i in identifiers if i["type"] == "CVE"),
                sa.get("ghsa_id", "UNKNOWN"),
            )
            first_patched = sv.get("first_patched_version")
            results.append({
                "alert_number": alert["number"],
                "cve_id": cve_id,
                "package": sv.get("package", {}).get("name", "unknown"),
                "ecosystem": sv.get("package", {}).get("ecosystem", "unknown"),
                "severity": sa.get("severity", "unknown"),
                "patched_version": first_patched.get("identifier") if first_patched else None,
                "advisory_url": sa.get("html_url", ""),
            })

    payload = json.dumps(results)
    ctx.set_state("raw_dependabot_alerts", payload)
    return payload

def list_code_scanning_alerts(ctx: ToolContext) -> str:
    """Fetch all open code-scanning alerts."""
    cached = ctx.get_state("raw_code_scanning_alerts")
    if cached:
        return cached

    try:
        data = run_gh_command([
            "api", "/repos/{owner}/{repo}/code-scanning/alerts",
            "-X", "GET",
            "-f", "state=open",
            "--paginate"
        ])
    except subprocess.CalledProcessError as exc:
        if "403" in str(exc):
            raise PermissionError("GitHub code scanning API returned 403; security_events permission is required.") from exc
        if "404" not in str(exc):
            raise
        print("[Seccure] Warning: code scanning alerts unavailable; treating as empty.")
        data = []

    results = []
    if data:
        for a in data:
            results.append({
                "number": a["number"],
                "rule_id": a.get("rule", {}).get("id", "unknown"),
                "severity": a.get("rule", {}).get("severity", "unknown"),
                "description": a.get("rule", {}).get("description", ""),
                "url": a.get("html_url", ""),
            })

    payload = json.dumps(results)
    ctx.set_state("raw_code_scanning_alerts", payload)
    return payload
