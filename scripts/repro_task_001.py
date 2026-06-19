from src.utils.git_tools import get_commit_messages

try:
    msgs = get_commit_messages("main", "feature")
    print("Success:", msgs)
except Exception as e:
    print("Failed:", e)
    import sys; sys.exit(1)
