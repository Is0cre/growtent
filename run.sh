#!/bin/bash
# Quick run script for grow tent automation

set -e

cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run install.sh first."
    exit 1
fi

echo "🌱 Starting Grow Tent Automation..."
echo ""

# Activate virtual environment
source venv/bin/activate

# Load environment variables
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Run the application
cd backend
python main.py
