import re

titles = [
    "chore(deps): update pydantic requirement from >=2.7.0 to >=2.13.4",
    "chore(deps): bump python from 3.12-slim to 3.14-slim",
    "chore(deps): update langsmith requirement from >=0.1.0 to >=0.8.15",
    "chore(deps): bump docker/build-push-action from 5 to 7",
]

def _parse_dependabot_title(title: str):
    match = re.search(
        r"(?:bump|update)\s+(?P<pkg>[\w@/.-]+)(?:\s+requirement)?\s+from\s+(?P<from>[<>=^\~]*[\d.\w-]+)\s+to\s+(?P<to>[<>=^\~]*[\d.\w-]+)",
        title,
        re.IGNORECASE,
    )
    if match:
        return match.group("pkg"), match.group("from"), match.group("to")
    return title, "unknown", "unknown"

for t in titles:
    print(_parse_dependabot_title(t))
