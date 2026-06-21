#!/bin/bash
export GITHUB_RUN_ID="test"
export TARGET_REPO="vijay/nonexistent-repo-123"
export GITHUB_TOKEN="fake_token"
export OPENROUTER_API_KEY="fake"

OUTPUT=$(python3 src/main.py 2>&1)

if echo "$OUTPUT" | grep -q "State initialised at"; then
    echo "FAIL: Expected to exit before initialising state!"
    echo "Output was:"
    echo "$OUTPUT"
    exit 1
else
    if echo "$OUTPUT" | grep -q "Permission error"; then
        echo "PASS: Exited with permission error early."
        exit 0
    else
        echo "FAIL: Did not see permission error."
        echo "Output was:"
        echo "$OUTPUT"
        exit 1
    fi
fi
