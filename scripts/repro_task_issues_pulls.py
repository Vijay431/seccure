import sys
from unittest.mock import patch

sys.path.insert(0, "/home/vijay/Programmer/Repos/Private/seccure")
from src.utils.github_issues import list_security_issues
from src.utils.github_pulls import list_dependabot_prs


class MockContext:
    def __init__(self):
        self.state = {}
    def get_state(self, key):
        return self.state.get(key)
    def set_state(self, key, val):
        self.state[key] = val

ctx = MockContext()

with patch("src.utils.github_issues.run_gh_command") as mock_gh_issues:
    mock_gh_issues.return_value = [{"number": i, "title": "Issue"} for i in range(30)]
    list_security_issues(ctx)
    args = mock_gh_issues.call_args[0][0]
    if "--limit" not in args or "30" not in args:
        print("FAILURE: github_issues limit not set to 30")
        sys.exit(1)

with patch("src.utils.github_pulls.run_gh_command") as mock_gh_pulls:
    mock_gh_pulls.return_value = [{"number": i, "title": "PR"} for i in range(30)]
    list_dependabot_prs(ctx)
    args = mock_gh_pulls.call_args[0][0]
    if "--limit" not in args or "30" not in args:
        print("FAILURE: github_pulls limit not set to 30")
        sys.exit(1)

print("SUCCESS: T006 and T007 limit constraints met.")
