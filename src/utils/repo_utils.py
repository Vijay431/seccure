def sanitize_repo_name(repo_str: str) -> str:
    """Extract owner/repo from URL or string."""
    if not repo_str:
        return ""
    repo_str = repo_str.strip()
    if repo_str.startswith("https://github.com/"):
        repo_str = repo_str.split("github.com/")[-1]
    elif repo_str.startswith("git@github.com:"):
        repo_str = repo_str.split("github.com:")[-1]

    repo_str = repo_str.removesuffix(".git")
    repo_str = repo_str.strip("/")

    parts = repo_str.split("/")
    if len(parts) >= 2:
        return f"{parts[-2]}/{parts[-1]}"
    return repo_str
