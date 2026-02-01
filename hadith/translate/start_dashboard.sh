#!/bin/bash
# Start the translation dashboard

cd /Users/osamaamer/Desktop/code/hadith/hadith/translate

# Activate virtual environment
source venv/bin/activate

# Install Flask if not installed
pip install flask -q 2>/dev/null

# Kill any existing dashboard process
lsof -ti:5000 | xargs kill -9 2>/dev/null
sleep 1

echo "🚀 Starting Translation Dashboard..."
echo ""
echo "📊 Dashboard will be available at:"
echo "   http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python dashboard.py
