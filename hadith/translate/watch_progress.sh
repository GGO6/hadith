#!/bin/bash
# Real-time progress watcher

cd /Users/osamaamer/Desktop/code/hadith/hadith/translate

echo "📊 Monitoring translation progress..."
echo "Press Ctrl+C to stop"
echo ""

# Watch the log file and filter progress messages
tail -f translation_api_full.log 2>/dev/null | grep --line-buffered -E "(🌍|حديث|Language|Total|Translating book|Batch|API call)" | while read line; do
    echo "$line"
done
