#!/bin/bash
# Comprehensive Test Coverage Runner
# This script runs all tests and generates a detailed coverage report

cd "$(dirname "$0")"

echo "🧪 Running Comprehensive Test Coverage Analysis..."
echo "=" | head -c 60
echo

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run tests with coverage on key modules
echo "📊 Running tests with coverage..."
python -m pytest tests/ \
    --cov=src \
    --cov-report=term-missing \
    --cov-report=html:htmlcov \
    --cov-report=json:coverage.json \
    -v \
    --tb=short \
    --maxfail=5 \
    -x

# Check exit code
if [ $? -eq 0 ]; then
    echo
    echo "✅ All tests passed!"
    echo
    echo "📈 Coverage Report:"
    python -m coverage report --skip-empty | tail -20
    echo
    echo "📂 HTML Coverage Report: htmlcov/index.html"
    echo "   Open with: open htmlcov/index.html"
else
    echo
    echo "❌ Some tests failed. Fix failing tests before checking coverage."
    exit 1
fi
