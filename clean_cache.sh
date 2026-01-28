#!/bin/bash

echo "Cleaning Python cache..."

# Remove all __pycache__ directories
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Remove all .pyc files
find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Remove all .pyo files
find . -type f -name "*.pyo" -delete 2>/dev/null || true

# Remove Django cache
rm -rf .pytest_cache 2>/dev/null || true

# Remove venv cache if exists
if [ -d "venv" ]; then
    find venv -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find venv -type f -name "*.pyc" -delete 2>/dev/null || true
fi

echo "Cache cleaned!"

# Restart Passenger
mkdir -p tmp
touch tmp/restart.txt
echo "Passenger restarted!"
