#!/bin/bash
# Run pytest for changed Python files
# This script runs tests for files that have been staged for commit

set -euo pipefail

cd apps/api

# Get list of changed Python test files (staged)
CHANGED_TESTS=$(git diff --cached --name-only --diff-filter=ACM | grep -E "apps/api/tests/.*\.py$" | sed 's|apps/api/||' || true)

if [ -z "$CHANGED_TESTS" ]; then
    echo "No test files changed, skipping pytest"
    exit 0
fi

echo "Running pytest for changed test files..."
echo "Files: $CHANGED_TESTS"

# Run tests without coverage to be fast
python -m pytest $CHANGED_TESTS -v --tb=short --no-cov -x

if [ $? -ne 0 ]; then
    echo "Tests failed! Fix before committing."
    exit 1
fi

echo "Tests passed"
exit 0
