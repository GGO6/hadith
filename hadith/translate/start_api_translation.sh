#!/bin/bash
# Script to start API-based translation

cd /Users/osamaamer/Desktop/code/hadith/hadith/translate

# Check if API key is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ Error: OPENAI_API_KEY not set!"
    echo ""
    echo "Please set your OpenAI API key:"
    echo "  export OPENAI_API_KEY='sk-your-api-key-here'"
    echo ""
    echo "Or pass it directly:"
    echo "  ./start_api_translation.sh sk-your-api-key-here"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Get API key from argument if provided
API_KEY=${1:-$OPENAI_API_KEY}

echo "🚀 Starting API-based translation..."
echo "📝 Model: GPT-4o-mini"
echo "💰 Estimated cost: ~$125-150 for full translation"
echo ""

# Run translation
python run_api_translation.py \
    --api-key "$API_KEY" \
    --languages turkish \
    --test \
    2>&1 | tee translation_api_run.log

echo ""
echo "✅ Translation completed!"
echo "📊 Check results in: output/turkish/all_translations.json"
