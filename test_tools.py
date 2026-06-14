import os
from dotenv import load_dotenv

load_dotenv()

# Set mock ToolContext
class MockToolContext:
    def __init__(self):
        self.state = {}
    def get_state(self, key):
        return self.state.get(key)
    def set_state(self, key, value):
        self.state[key] = value

ctx = MockToolContext()

# Patch environment if TARGET_REPO isn't set
if not os.environ.get("TARGET_REPO"):
    os.environ["TARGET_REPO"] = "Vijay431/seccure"

from agent.tools.github_read import list_security_issues, list_dependabot_prs, list_dependabot_alerts, list_code_scanning_alerts

print("--- ISSUES ---")
try:
    print(list_security_issues(ctx))
except Exception as e:
    print("Error:", e)

print("\n--- PRs ---")
try:
    print(list_dependabot_prs(ctx))
except Exception as e:
    print("Error:", e)

print("\n--- ALERTS ---")
try:
    print(list_dependabot_alerts(ctx))
except Exception as e:
    print("Error:", e)

print("\n--- CODE SCANNING ---")
try:
    print(list_code_scanning_alerts(ctx))
except Exception as e:
    print("Error:", e)
