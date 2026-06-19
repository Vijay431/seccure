import sys
from unittest.mock import patch

sys.path.insert(0, "/home/vijay/Programmer/Repos/Private/seccure")
from src.utils.github_security import list_dependabot_alerts


class MockContext:
    def __init__(self):
        self.state = {}
    def get_state(self, key):
        return self.state.get(key)
    def set_state(self, key, val):
        self.state[key] = val

ctx = MockContext()

with patch("src.utils.github_security.run_gh_command") as mock_gh:
    # We want to test that dependabot fetches 30 items max using per_page=30 and sort.
    # It shouldn't use --paginate.
    mock_gh.return_value = [{"number": i, "security_advisory": {"severity": "critical"}} for i in range(30)]

    list_dependabot_alerts(ctx)
    args = mock_gh.call_args[0][0]

    if "--paginate" in args:
        print("FAILURE: --paginate still used in list_dependabot_alerts")
        sys.exit(1)
    if "per_page=30" not in args:
        print("FAILURE: per_page=30 missing from list_dependabot_alerts")
        sys.exit(1)

    print("SUCCESS: list_dependabot_alerts constraints met.")
