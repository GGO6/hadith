#!/bin/bash
# Restart translation process

cd /Users/osamaamer/Desktop/code/hadith/hadith/translate

# Activate virtual environment
source venv/bin/activate

# Check if API key is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ Error: OPENAI_API_KEY not set!"
    echo ""
    echo "Please set your OpenAI API key:"
    echo "  export OPENAI_API_KEY='sk-your-api-key-here'"
    exit 1
fi

# Kill any existing translation processes
pkill -f "python.*run_api_translation" 2>/dev/null
sleep 2

echo "🔄 Restarting translation process..."
echo "📝 Language: Turkish"
echo ""

# Restart translation
python run_api_translation.py \
    --api-key "$OPENAI_API_KEY" \
    --languages turkish \
    > translation_api_full.log 2>&1 &

PID=$!
echo "✅ Translation restarted!"
echo "📋 Process ID: $PID"
echo ""
echo "📊 Monitor progress:"
echo "   tail -f translation_api_full.log"
echo "   python show_progress.py"
