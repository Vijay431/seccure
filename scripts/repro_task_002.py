import json
import re
import subprocess


def extract_references_from_commits(messages: list[str]) -> list[str]:
    refs = set()
    pattern = re.compile(r"(?:#|GH-|PR-)(\d+)", re.IGNORECASE)
    for msg in messages:
        for match in pattern.finditer(msg):
            refs.add(match.group(1))
    return sorted(list(refs), key=int)

def bulk_validate_references(references: list[str]) -> list[str]:
    if not references:
        return []

    # Get repo owner and name
    try:
        repo_data = subprocess.run(["gh", "repo", "view", "--json", "owner,name"], capture_output=True, text=True, check=True)
        repo_info = json.loads(repo_data.stdout)
        owner = repo_info["owner"]["login"]
        repo = repo_info["name"]
    except Exception:
        return references # Fallback

    query_parts = []
    for ref in references:
        query_parts.append(f'ref_{ref}: issueOrPullRequest(number: {ref}) {{ __typename }}')

    query = "query { repository(owner: \"%s\", name: \"%s\") { %s } }" % (owner, repo, " ".join(query_parts))

    try:
        # Don't use check=True because a missing issue will return exit code 1
        res = subprocess.run(["gh", "api", "graphql", "-f", f"query={query}"], capture_output=True, text=True)
        data = json.loads(res.stdout)

        valid_refs = []
        if "data" in data and "repository" in data["data"]:
            repo_node = data["data"]["repository"]
            for ref in references:
                if repo_node.get(f"ref_{ref}") is not None:
                    valid_refs.append(ref)
        return valid_refs
    except Exception as e:
        print("Fallback:", e)
        return references

print(bulk_validate_references(["1", "9999999"]))
