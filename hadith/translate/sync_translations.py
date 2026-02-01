#!/usr/bin/env python3
"""
Sync translations from output to main translations structure
مزامنة الترجمات من output إلى البنية الرئيسية
"""
import json
import sys
from pathlib import Path
from typing import Dict, List

# Language code mapping
LANG_CODE_MAP = {
    "turkish": "tr",
    "french": "fr",
    "indonesian": "id",
    "urdu": "ur",
    "bengali": "bn",
    "german": "de",
    "spanish": "es",
    "russian": "ru"
}

def load_translations(language: str) -> Dict:
    """Load translations from output directory"""
    script_dir = Path(__file__).parent
    output_file = script_dir / "output" / language / "all_translations.json"
    
    if not output_file.exists():
        print(f"❌ Translation file not found: {output_file}")
        return {}
    
    with open(output_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_book_structure(book_id: str) -> Dict:
    """Load book metadata to understand structure"""
    script_dir = Path(__file__).parent
    books_dir = script_dir / ".." / "books"
    
    # Try to find metadata.json
    metadata_files = list(books_dir.glob(f"**/{book_id}/metadata.json"))
    if not metadata_files:
        return None
    
    with open(metadata_files[0], 'r', encoding='utf-8') as f:
        return json.load(f)

def sync_book_translations(book_id: str, translations: Dict, lang_code: str, language: str):
    """Sync translations for a single book"""
    script_dir = Path(__file__).parent
    books_dir = script_dir.parent / "books"
    translations_dir = script_dir.parent / "translations" / lang_code / "books"
    
    # Find book directory by searching in all categories
    book_dir = None
    for category_dir in books_dir.iterdir():
        if category_dir.is_dir():
            potential_book_dir = category_dir / book_id
            if potential_book_dir.exists():
                book_dir = potential_book_dir
                category = category_dir.name
                break
    
    if not book_dir:
        print(f"⚠️  Book directory not found: {book_id}")
        return False
    
    # Load book metadata
    metadata_file = book_dir / "metadata.json"
    if not metadata_file.exists():
        print(f"⚠️  Metadata not found for: {book_id}")
        return False
    
    with open(metadata_file, 'r', encoding='utf-8') as f:
        book_metadata = json.load(f)
    
    # Determine category
    category = None
    for cat_dir in books_dir.iterdir():
        if cat_dir.is_dir() and (book_dir.parent == cat_dir):
            category = cat_dir.name
            break
    
    if not category:
        print(f"⚠️  Could not determine category for: {book_id}")
        return False
    
    # Create translations directory structure
    trans_book_dir = translations_dir / category / book_id
    trans_book_dir.mkdir(parents=True, exist_ok=True)
    
    book_translations = translations.get(book_id, {})
    if not book_translations:
        # Try to find if book_id exists but is empty
        if book_id in translations:
            print(f"⚠️  Book {book_id} found but empty (0 hadiths)")
        else:
            print(f"⚠️  No translations found for book: {book_id}")
        return False
    
    print(f"📖 Processing {book_id}: {len(book_translations)} hadiths")
    
    # Handle books with chapters (check if chapters list exists and is not empty)
    chapters = book_metadata.get('chapters', [])
    if chapters:
        synced_count = 0
        
        for chapter in chapters:
            chapter_file = chapter.get('file')
            if not chapter_file:
                continue
            
            # Load original chapter
            orig_chapter_path = book_dir / chapter_file
            if not orig_chapter_path.exists():
                continue
            
            with open(orig_chapter_path, 'r', encoding='utf-8') as f:
                orig_chapter = json.load(f)
            
            # Create translated chapter
            trans_chapter_path = trans_book_dir / chapter_file
            trans_chapter_path.parent.mkdir(parents=True, exist_ok=True)
            
            translated_hadiths = []
            for hadith in orig_chapter.get('hadiths', []):
                # Try multiple ID formats
                hadith_id = str(hadith.get('id'))
                hadith_id_in_book = str(hadith.get('idInBook', ''))
                
                trans_data = None
                # Try idInBook first (as translations use this)
                if hadith_id_in_book and hadith_id_in_book in book_translations:
                    trans_data = book_translations[hadith_id_in_book]
                elif hadith_id in book_translations:
                    trans_data = book_translations[hadith_id]
                
                if trans_data:
                    translated_hadiths.append({
                        'id': hadith.get('id'),
                        'narrator': trans_data.get('narrator', ''),
                        'text': trans_data.get('text', '')
                    })
                    synced_count += 1
            
            if translated_hadiths:
                print(f"  ✅ Chapter {chapter_file}: {len(translated_hadiths)} hadiths")
                trans_chapter = {
                    'language': lang_code,
                    'metadata': orig_chapter.get('metadata', {}),
                    'hadiths': translated_hadiths
                }
                
                with open(trans_chapter_path, 'w', encoding='utf-8') as f:
                    json.dump(trans_chapter, f, ensure_ascii=False, indent=2)
        
        print(f"✅ {book_id}: Synced {synced_count} hadiths")
        return synced_count > 0
    
    else:
        # Book without chapters (e.g., forties)
        all_file = book_dir / "all.json"
        if all_file.exists():
            with open(all_file, 'r', encoding='utf-8') as f:
                orig_data = json.load(f)
            
            translated_hadiths = []
            synced_count = 0
            
            for hadith in orig_data.get('hadiths', []):
                # Try multiple ID formats
                hadith_id = str(hadith.get('id'))
                hadith_id_in_book = str(hadith.get('idInBook', ''))
                
                trans_data = None
                # Try idInBook first (as translations use this)
                if hadith_id_in_book and hadith_id_in_book in book_translations:
                    trans_data = book_translations[hadith_id_in_book]
                elif hadith_id in book_translations:
                    trans_data = book_translations[hadith_id]
                
                if trans_data:
                    translated_hadiths.append({
                        'id': hadith.get('id'),
                        'narrator': trans_data.get('narrator', ''),
                        'text': trans_data.get('text', '')
                    })
                    synced_count += 1
            
            if translated_hadiths:
                trans_all_file = trans_book_dir / "all.json"
                trans_data = {
                    'language': lang_code,
                    'metadata': orig_data.get('metadata', {}),
                    'hadiths': translated_hadiths
                }
                
                with open(trans_all_file, 'w', encoding='utf-8') as f:
                    json.dump(trans_data, f, ensure_ascii=False, indent=2)
                
                print(f"✅ {book_id}: Synced {synced_count} hadiths")
                return synced_count > 0
    
    return False

def update_index_json(lang_code: str):
    """Update index.json to mark language as available"""
    script_dir = Path(__file__).parent
    index_file = script_dir / ".." / "index.json"
    
    if not index_file.exists():
        print("⚠️  index.json not found")
        return
    
    with open(index_file, 'r', encoding='utf-8') as f:
        index = json.load(f)
    
    # Update language status
    for lang_info in index.get('availableLanguages', []):
        if lang_info.get('code') == lang_code:
            lang_info['status'] = 'available'
            print(f"✅ Updated index.json: {lang_code} status -> available")
            break
    
    # Save updated index
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

def main():
    if len(sys.argv) < 2:
        print("Usage: python sync_translations.py <language>")
        print("Example: python sync_translations.py turkish")
        sys.exit(1)
    
    language = sys.argv[1].lower()
    lang_code = LANG_CODE_MAP.get(language)
    
    if not lang_code:
        print(f"❌ Unknown language: {language}")
        print(f"Available: {', '.join(LANG_CODE_MAP.keys())}")
        sys.exit(1)
    
    print("="*60)
    print(f"🔄 Syncing translations: {language} ({lang_code})")
    print("="*60)
    
    # Load translations
    translations = load_translations(language)
    if not translations:
        print("❌ No translations found")
        sys.exit(1)
    
    print(f"📚 Found translations for {len(translations)} books")
    
    # Sync each book
    synced_books = 0
    total_hadiths = 0
    
    for book_id in translations.keys():
        if sync_book_translations(book_id, translations, lang_code, language):
            synced_books += 1
            total_hadiths += len(translations[book_id])
    
    print("\n" + "="*60)
    print("📊 Sync Summary:")
    print("="*60)
    print(f"✅ Books synced: {synced_books}")
    print(f"📝 Total hadiths: {total_hadiths:,}")
    
    # Update index.json
    update_index_json(lang_code)
    
    print("\n✅ Sync completed!")

if __name__ == "__main__":
    main()
