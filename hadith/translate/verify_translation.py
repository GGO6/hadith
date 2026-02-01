#!/usr/bin/env python3
"""
أداة للتحقق من جودة الترجمة يدوياً
تعرض أحاديث عشوائية مع النص الأصلي والترجمة
"""
import json
import random
import glob
from pathlib import Path

def load_source_hadith(books_dir, book_id, chapter_id, hadith_id):
    """Load original hadith from source files"""
    book_path = Path(books_dir) / book_id
    
    # Try to find the hadith in chapter files
    for json_file in glob.glob(str(book_path / "*.json")):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                hadiths = data.get('hadiths', [])
                for h in hadiths:
                    if str(h.get('chapterId', 0)) == str(chapter_id) and str(h.get('id')) == str(hadith_id):
                        return h
        except:
            continue
    return None

def main():
    print("\n" + "="*70)
    print("🔍 أداة التحقق من جودة الترجمة")
    print("="*70)
    
    # Load translations
    with open('output/turkish/all_translations.json', 'r', encoding='utf-8') as f:
        translations = json.load(f)
    
    books_dir = '../books'
    
    books = list(translations.keys())
    
    while True:
        print("\n" + "-"*50)
        print("الكتب المتاحة:")
        for i, book in enumerate(books, 1):
            count = len(translations[book]) if isinstance(translations[book], dict) else 0
            print(f"  {i}. {book} ({count:,} حديث)")
        
        print("\n  0. خروج")
        print("  r. حديث عشوائي من أي كتاب")
        print("-"*50)
        
        choice = input("\nاختر رقم الكتاب (أو 'r' لعشوائي): ").strip()
        
        if choice == '0':
            print("\nشكراً لاستخدام الأداة! 👋")
            break
        
        if choice.lower() == 'r':
            book_id = random.choice(books)
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(books):
                    book_id = books[idx]
                else:
                    print("❌ رقم غير صحيح")
                    continue
            except:
                print("❌ إدخال غير صحيح")
                continue
        
        hadiths = translations[book_id]
        if not isinstance(hadiths, dict) or len(hadiths) == 0:
            print("❌ لا توجد أحاديث في هذا الكتاب")
            continue
        
        # Pick random hadith
        random_key = random.choice(list(hadiths.keys()))
        hadith = hadiths[random_key]
        
        # Parse key to get chapter_id and hadith_id
        parts = random_key.split(':')
        if len(parts) == 2:
            chapter_id, hadith_id = parts
        else:
            chapter_id, hadith_id = '0', random_key
        
        print("\n" + "="*70)
        print(f"📖 الكتاب: {book_id.upper()}")
        print(f"📑 الفصل: {chapter_id} | الحديث: {hadith_id}")
        print("="*70)
        
        # Show narrator (English)
        narrator = hadith.get('narrator', '')
        if narrator:
            print(f"\n👤 الراوي (English):")
            print(f"   {narrator}")
        
        # Try to load original hadith
        source = load_source_hadith(books_dir, book_id, chapter_id, hadith_id)
        if source:
            original_text = source.get('english', {}).get('text', '')
            if original_text:
                print(f"\n📝 النص الأصلي (English):")
                print(f"   {original_text[:600]}")
                if len(original_text) > 600:
                    print("   ...")
        
        # Show Turkish translation
        turkish_text = hadith.get('text', '')
        print(f"\n🇹🇷 الترجمة التركية:")
        print(f"   {turkish_text[:600]}")
        if len(turkish_text) > 600:
            print("   ...")
        
        print("\n" + "-"*50)
        input("اضغط Enter للمتابعة...")

if __name__ == "__main__":
    main()
