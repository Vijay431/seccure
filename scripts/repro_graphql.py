import subprocess


def test_graphql():
    # just an example with seccure, let's use gh api to check
    # Wait, we need to know what repo we are in or just use a public one
    query = """
    query {
      repository(owner: "cli", name: "cli") {
        ref_1: issueOrPullRequest(number: 1) { __typename }
        ref_9999999: issueOrPullRequest(number: 9999999) { __typename }
      }
    }
    """
    res = subprocess.run(["gh", "api", "graphql", "-f", f"query={query}"], capture_output=True, text=True)
    print(res.stdout)
    print(res.stderr)

test_graphql()
