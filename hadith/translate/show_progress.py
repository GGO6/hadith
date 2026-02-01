#!/usr/bin/env python3
"""
Real-time progress display for translation
"""
import json
import time
import os
from pathlib import Path

def show_progress():
    script_dir = Path(__file__).parent
    checkpoint_file = script_dir / "checkpoints" / "turkish_api_checkpoint.json"
    
    if not checkpoint_file.exists():
        print("❌ No checkpoint file found")
        return
    
    with open(checkpoint_file, 'r', encoding='utf-8') as f:
        cp = json.load(f)
    
    total_hadiths = 50884
    translated = cp['stats']['total_translated']
    remaining = total_hadiths - translated
    pct = (translated / total_hadiths) * 100
    api_calls = cp['stats']['api_calls']
    books = cp.get('processed_books', [])
    
    print("\n" + "="*70)
    print("📊 حالة الترجمة الحالية")
    print("="*70)
    print(f"🌍 اللغة: Turkish (Türkçe)")
    print(f"✅ تم ترجمة: {translated:,} حديث")
    print(f"📈 النسبة المئوية: {pct:.2f}%")
    print(f"⏳ متبقي: {remaining:,} حديث")
    print(f"📞 استدعاءات API: {api_calls:,}")
    print(f"📚 الكتب المكتملة: {len(books)}")
    if books:
        print(f"   - {', '.join(books)}")
    print("="*70)
    
    # Estimate time remaining
    if translated > 0:
        # Rough estimate: ~15-20 hours for full translation
        estimated_total_time = 18 * 3600  # 18 hours in seconds
        estimated_remaining = estimated_total_time * (remaining / total_hadiths)
        hours = int(estimated_remaining // 3600)
        minutes = int((estimated_remaining % 3600) // 60)
        print(f"⏱️  الوقت المتوقع المتبقي: ~{hours} ساعة و {minutes} دقيقة")
        print("="*70)

if __name__ == "__main__":
    show_progress()
