#!/bin/bash
# Script to restart API translation

cd /Users/osamaamer/Desktop/code/hadith/hadith/translate

# Activate virtual environment
source venv/bin/activate

# Kill any existing translation processes
pkill -f "python.*run_api_translation" 2>/dev/null
sleep 2

# Check if API key is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ Error: OPENAI_API_KEY not set!"
    echo ""
    echo "Please set your OpenAI API key:"
    echo "  export OPENAI_API_KEY='sk-your-api-key-here'"
    exit 1
fi

# Restart translation
echo "🚀 Starting API translation with improved progress tracking..."
python run_api_translation.py \
    --api-key "$OPENAI_API_KEY" \
    --test \
    --languages turkish \
    2>&1 | tee translation_api_run.log

echo ""
echo "✅ Translation completed!"
echo "📊 Check results in: output/turkish/all_translations.json"
