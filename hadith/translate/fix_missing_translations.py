#!/usr/bin/env python3
"""
Fix missing translations by retranslating books that were marked as processed
but don't have translations in output file
"""
import json
import sys
from pathlib import Path
from run_api_translation import APIHadithTranslator

def fix_missing_translations(language: str = "turkish"):
    """Retranslate books that are missing from output"""
    
    translator = APIHadithTranslator()
    
    # Load checkpoint
    checkpoint = translator.load_checkpoint(language)
    
    # Load current output
    output_file = translator.output_dir / language / "all_translations.json"
    if output_file.exists():
        with open(output_file, 'r', encoding='utf-8') as f:
            all_translations = json.load(f)
    else:
        all_translations = {}
    
    # Find books that are marked as processed but missing translations
    processed_books = checkpoint.get('processed_books', [])
    missing_books = []
    
    for book_id in processed_books:
        if book_id not in all_translations or not all_translations[book_id]:
            missing_books.append(book_id)
    
    if not missing_books:
        print("✅ All processed books have translations!")
        return
    
    print(f"⚠️  Found {len(missing_books)} books missing translations:")
    for book_id in missing_books:
        print(f"   - {book_id}")
    
    print(f"\n🔄 Retranslating missing books...")
    
    # Load all books
    all_books = translator.load_all_books()
    
    # Retranslate missing books
    for book in all_books:
        book_id = book['id']
        if book_id in missing_books:
            print(f"\n📖 Retranslating: {book_id}")
            
            # Remove from processed list temporarily
            if book_id in checkpoint.get('processed_books', []):
                checkpoint['processed_books'].remove(book_id)
            
            # Translate
            translated = translator.translate_book(book, language, checkpoint)
            
            if translated:
                all_translations[book_id] = translated
                checkpoint['processed_books'].append(book_id)
                translator.save_checkpoint(checkpoint)
                print(f"✅ {book_id}: {len(translated)} hadiths translated")
            else:
                print(f"⚠️  {book_id}: No translations returned")
    
    # Save all translations
    translator.save_translations(language, all_translations)
    print(f"\n✅ All translations saved!")

if __name__ == "__main__":
    language = sys.argv[1] if len(sys.argv) > 1 else "turkish"
    fix_missing_translations(language)
