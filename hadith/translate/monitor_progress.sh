#!/bin/bash
# Script to monitor translation progress with detailed info

cd /Users/osamaamer/Desktop/code/hadith/hadith/translate

echo "📊 Translation Progress Monitor"
echo "================================"
echo ""

# Check if process is running
if pgrep -f "python.*run_api_translation" > /dev/null; then
    echo "✅ Process is running"
else
    echo "❌ Process is not running"
fi

echo ""
echo "📝 Latest log entries:"
echo "----------------------"
tail -20 translation_api_full.log 2>/dev/null || tail -20 translation_run.log 2>/dev/null || echo "No log file found"

echo ""
echo "📈 Checkpoint status:"
echo "---------------------"
if [ -f "checkpoints/turkish_api_checkpoint.json" ]; then
    python3 -c "
import json
try:
    with open('checkpoints/turkish_api_checkpoint.json', 'r') as f:
        cp = json.load(f)
    print(f\"Total translated: {cp['stats']['total_translated']:,}\")
    print(f\"API calls: {cp['stats']['api_calls']:,}\")
    print(f\"Processed books: {len(cp.get('processed_books', []))}\")
except:
    print('Error reading checkpoint')
" 2>/dev/null || echo "Could not read checkpoint"
else
    echo "No checkpoint file found"
fi

echo ""
echo "💡 To follow live progress:"
echo "   tail -f translation_api_full.log"
