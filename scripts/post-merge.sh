#!/bin/bash
set -e

# Nursy post-merge setup script
# Runs automatically after every task merge.
# Must be idempotent and non-interactive.

echo "=== Nursy post-merge setup ==="

# Python dependencies (pip install -q, no interaction)
if [ -f requirements.txt ]; then
  echo "Installing Python dependencies..."
  pip install -q -r requirements.txt
fi

# Node dependencies for mockup-sandbox (if package.json changed)
if [ -f artifacts/mockup-sandbox/package.json ]; then
  echo "Installing Node dependencies for mockup-sandbox..."
  cd artifacts/mockup-sandbox
  npm install --silent 2>&1 | tail -5
  cd ../..
fi

echo "=== Post-merge setup complete ==="
