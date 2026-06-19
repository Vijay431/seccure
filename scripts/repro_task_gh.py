import sys
from unittest.mock import patch

sys.path.insert(0, "/home/vijay/Programmer/Repos/Private/seccure")
from src.utils.gh_wrapper_v2 import run_gh_command

with patch("subprocess.run") as mock_run:
    # Set a dummy return value to avoid CalledProcessError
    mock_run.return_value.stdout = "{}"

    try:
        run_gh_command(["api", "user"])

        args, kwargs = mock_run.call_args

        print(f"shell=False present? {kwargs.get('shell') is False}")
        print(f"timeout=300 present? {kwargs.get('timeout') == 300}")
        print(f"GH_PROMPT_DISABLED present? {'GH_PROMPT_DISABLED' in kwargs.get('env', {})}")

        if kwargs.get('shell') is False and kwargs.get('timeout') == 300 and 'GH_PROMPT_DISABLED' in kwargs.get('env', {}):
            print("SUCCESS: All hardening constraints met.")
            sys.exit(0)
        else:
            print("FAILURE: Hardening constraints missing.")
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
