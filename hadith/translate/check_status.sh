#!/bin/bash
# Check translation status and diagnose issues

cd /Users/osamaamer/Desktop/code/hadith/hadith/translate

echo "📊 Translation Status Check"
echo "=========================="
echo ""

# Check if process is running
if pgrep -f "python.*run_api_translation" > /dev/null 2>&1; then
    echo "✅ Process is RUNNING"
    PID=$(pgrep -f "python.*run_api_translation")
    echo "   PID: $PID"
else
    echo "❌ Process is NOT running"
fi

echo ""

# Check checkpoint
if [ -f "checkpoints/turkish_api_checkpoint.json" ]; then
    python3 << 'PYEOF'
import json
from datetime import datetime
from pathlib import Path

cp_file = Path('checkpoints/turkish_api_checkpoint.json')
with open(cp_file, 'r') as f:
    cp = json.load(f)

mtime = cp_file.stat().st_mtime
last_modified = datetime.fromtimestamp(mtime)
now = datetime.now()
diff = (now - last_modified).total_seconds() / 60

print("📅 Checkpoint Status:")
print(f"   Total translated: {cp['stats']['total_translated']:,}")
print(f"   API calls: {cp['stats']['api_calls']:,}")
print(f"   Processed books: {len(cp.get('processed_books', []))}")
print(f"   Last update: {last_modified.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"   Minutes ago: {diff:.1f}")

if diff > 10:
    print("   ⚠️  Last update was more than 10 minutes ago")
PYEOF
else
    echo "❌ No checkpoint file found"
fi

echo ""

# Check output file
if [ -f "output/turkish/all_translations.json" ]; then
    python3 << 'PYEOF'
import json

with open('output/turkish/all_translations.json', 'r') as f:
    output = json.load(f)

total = sum(len(v) for v in output.values() if isinstance(v, dict))
books_with_translations = sum(1 for v in output.values() if isinstance(v, dict) and len(v) > 0)

print("📁 Output File Status:")
print(f"   Total hadiths: {total:,}")
print(f"   Books with translations: {books_with_translations}")
print(f"   Total books: {len(output)}")
PYEOF
else
    echo "❌ No output file found"
fi

echo ""
echo "💡 To restart: ./restart_translation.sh"
