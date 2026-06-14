from agent.tools.git_tools import _run
code, out, err = _run(["uv", "add", "pydantic>=2.13.4"])
print(f"CODE: {code}")
print(f"OUT: {out}")
print(f"ERR: {err}")
