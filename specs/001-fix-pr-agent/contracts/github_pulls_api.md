# API Contracts: PR Agent Fix

This specifies the new/modified Python function signatures acting as internal APIs for this feature.

## `agent.tools.git_tools.get_commit_messages`

```python
def get_commit_messages(base_branch: str, head_branch: str) -> list[str]:
    """
    Retrieves commit messages between the base_branch and head_branch locally.
    
    Args:
        base_branch (str): The branch being merged into (e.g., 'main')
        head_branch (str): The feature branch with new commits
        
    Returns:
        list[str]: A list of commit messages.
    """
```

## `agent.tools.github_pulls.extract_references_from_commits`

```python
def extract_references_from_commits(messages: list[str]) -> list[str]:
    """
    Parses commit messages to find issue and PR references like #123 or GH-123.
    
    Args:
        messages (list[str]): List of commit messages
        
    Returns:
        list[str]: A deduplicated list of issue/PR references (e.g. ['#123', '#124']).
    """
```

## `agent.tools.github_pulls.bulk_validate_references`

```python
def bulk_validate_references(references: list[str]) -> list[str]:
    """
    Validates a list of references (e.g. ['#123', '#124']) against the GitHub API
    in bulk to ensure they exist.
    
    Args:
        references (list[str]): List of extracted issue/PR references
        
    Returns:
        list[str]: A list containing only the valid references that exist.
    """
```

## `agent.tools.github_pulls.render_pr_title_body`

```python
def render_pr_title_body(state: SeccureState, commit_references: list[str] = None) -> tuple[str, str]:
    """
    Renders the new Seccure automated block, injecting `commit_references`.
    """
```
