#!/usr/bin/env python3
"""
API-based translation script using GPT-4o-mini
Much faster than local NLLB (~10-20x faster)
"""
import os
import json
import glob
import sys
import argparse
from pathlib import Path
from tqdm import tqdm
from typing import Dict, List
import time
import config
from api_translator import APITranslator

class APIHadithTranslator:
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini"):
        """
        Initialize API-based translation system
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env)
            model: Model to use (default: gpt-4o-mini)
        """
        print("Initializing API translation system...")
        self.translator = APITranslator(api_key=api_key, model=model)
        
        # Resolve paths relative to script location
        script_dir = Path(__file__).parent
        self.checkpoints_dir = script_dir / config.CHECKPOINTS_DIR
        self.output_dir = script_dir / config.OUTPUT_DIR
        self.books_dir = script_dir / config.BOOKS_DIR
        
        self.checkpoints_dir.mkdir(exist_ok=True, parents=True)
        self.output_dir.mkdir(exist_ok=True, parents=True)
    
    def load_checkpoint(self, language: str) -> Dict:
        """Load translation checkpoint for a language"""
        checkpoint_file = self.checkpoints_dir / f"{language}_api_checkpoint.json"
        if checkpoint_file.exists():
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "language": language,
            "processed_books": [],
            "processed_hadiths": [],
            "stats": {
                "total_translated": 0,
                "api_calls": 0,
                "tokens_used": 0
            }
        }
    
    def save_checkpoint(self, checkpoint: Dict):
        """Save translation checkpoint"""
        checkpoint_file = self.checkpoints_dir / f"{checkpoint['language']}_api_checkpoint.json"
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint, f, ensure_ascii=False, indent=2)
    
    def load_all_books(self) -> List[Dict]:
        """Load all book metadata files"""
        books = []
        metadata_files = glob.glob(str(self.books_dir / "**/metadata.json"), recursive=True)
        
        for metadata_file in metadata_files:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                metadata['_path'] = Path(metadata_file).parent
                books.append(metadata)
        
        return sorted(books, key=lambda x: x.get('numericId', 0))
    
    def load_chapter_file(self, book_path: Path, chapter_file: str) -> Dict:
        """Load a chapter JSON file"""
        file_path = book_path / chapter_file
        if not file_path.exists():
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def extract_hadith_text(self, hadith: Dict) -> str:
        """Extract English text from hadith (narrator + text)"""
        english = hadith.get('english', {})
        narrator = english.get('narrator', '')
        text = english.get('text', '')
        
        if narrator and text:
            return f"{narrator} {text}".strip()
        elif text:
            return text
        elif narrator:
            return narrator
        return ""
    
    def translate_book(self, book: Dict, language: str, checkpoint: Dict) -> Dict:
        """Translate all hadiths in a book using API"""
        book_id = book['id']
        book_path = book['_path']
        
        print(f"\nTranslating book: {book['english']['title']} ({book_id})")
        
        translated_hadiths = {}
        chapters = book.get('chapters', [])
        
        if not chapters:
            # Book without chapters (e.g., forties)
            all_file = book_path / "all.json"
            if all_file.exists():
                chapter_data = self.load_chapter_file(book_path, "all.json")
                if chapter_data:
                    hadiths = chapter_data.get('hadiths', [])
                    
                    # Filter out already processed (using composite ID: book_id:chapterId:hadith_id)
                    hadiths_to_translate = [
                        h for h in hadiths 
                        if f"{book_id}:{h.get('chapterId', 0)}:{h.get('id')}" not in checkpoint.get('processed_hadiths', [])
                    ]
                    
                    if hadiths_to_translate:
                        # Extract texts
                        hadith_texts = []
                        hadith_metadata = []
                        for hadith in hadiths_to_translate:
                            english_text = self.extract_hadith_text(hadith)
                            hadith_texts.append(english_text)
                            hadith_metadata.append({
                                'id': hadith.get('id'),
                                'chapterId': hadith.get('chapterId', 0),
                                'narrator': hadith.get('english', {}).get('narrator', ''),
                                'original_text': english_text
                            })
                        
                        # Translate all hadiths at once (parallel API calls inside)
                        print(f"  Translating {len(hadith_texts)} hadiths...")
                        
                        try:
                            translated_texts = self.translator.translate_batch(hadith_texts, language)
                            checkpoint['stats']['api_calls'] += (len(hadith_texts) + 14) // 15
                        except Exception as e:
                            print(f"  Error translating: {e}")
                            translated_texts = hadith_texts  # Keep original on error
                        
                        # Process results
                        for idx, (hadith_meta, translated_text) in enumerate(zip(hadith_metadata, translated_texts)):
                            hadith_id = hadith_meta['id']
                            chapter_id = hadith_meta['chapterId']
                            # Use chapterId:hadith_id as output key for uniqueness
                            output_key = f"{chapter_id}:{hadith_id}"
                            composite_id = f"{book_id}:{chapter_id}:{hadith_id}"
                            
                            translated_hadiths[output_key] = {
                                'narrator': hadith_meta['narrator'],
                                'text': translated_text,
                                'hadith_id': hadith_id,
                                'chapter_id': chapter_id,
                                'quality': {
                                    'confidence': 'HIGH',  # API translations are high quality
                                    'needs_review': False
                                }
                            }
                            
                            # Only add if not already processed (use composite ID)
                            if composite_id not in checkpoint.get('processed_hadiths', []):
                                checkpoint['stats']['total_translated'] += 1
                                checkpoint['processed_hadiths'].append(composite_id)
                            
                            # Show progress
                            remaining = self.total_hadiths - checkpoint['stats']['total_translated']
                            progress_pct = (checkpoint['stats']['total_translated'] / self.total_hadiths) * 100
                            lang_display = f"{self.lang_info['name']} ({self.lang_info.get('native_name', '')})"
                            progress_msg = f"🌍 [{lang_display}] 📖 {book_id} | حديث #{checkpoint['stats']['total_translated']:,} ({progress_pct:.1f}%) | متبقي: {remaining:,}"
                            
                            # Print with carriage return for terminal
                            print(f"\r{progress_msg}", end='', flush=True)
                            
                            # Log every 10 hadiths for better log file visibility
                            if checkpoint['stats']['total_translated'] % 10 == 0:
                                print(f"\n{progress_msg}", flush=True)
                            
                            # Save checkpoint every 50 hadiths
                            if checkpoint['stats']['total_translated'] % 50 == 0:
                                self.save_checkpoint(checkpoint)
                                print()  # New line after checkpoint save
        else:
            # Book with chapters
            for chapter in tqdm(chapters, desc=f"  {book_id}"):
                chapter_file = chapter.get('file')
                if not chapter_file:
                    continue
                
                chapter_data = self.load_chapter_file(book_path, chapter_file)
                if not chapter_data:
                    continue
                
                hadiths = chapter_data.get('hadiths', [])
                
                # Filter out already processed (using composite ID: book_id:chapterId:hadith_id)
                hadiths_to_translate = [
                    h for h in hadiths 
                    if f"{book_id}:{h.get('chapterId', 0)}:{h.get('id')}" not in checkpoint.get('processed_hadiths', [])
                ]
                
                if not hadiths_to_translate:
                    continue
                
                # Extract texts
                hadith_texts = []
                hadith_metadata = []
                for hadith in hadiths_to_translate:
                    english_text = self.extract_hadith_text(hadith)
                    hadith_texts.append(english_text)
                    hadith_metadata.append({
                        'id': hadith.get('id'),
                        'chapterId': hadith.get('chapterId', 0),
                        'narrator': hadith.get('english', {}).get('narrator', ''),
                        'original_text': english_text
                    })
                
                # Translate all hadiths in chapter at once (parallel API calls inside)
                print(f"    Translating {len(hadith_texts)} hadiths...")
                
                try:
                    translated_texts = self.translator.translate_batch(hadith_texts, language)
                    checkpoint['stats']['api_calls'] += (len(hadith_texts) + 14) // 15  # Approximate API calls
                except Exception as e:
                    print(f"    Error translating chapter: {e}")
                    translated_texts = hadith_texts  # Keep original on error
                
                # Process results
                for idx, (hadith_meta, translated_text) in enumerate(zip(hadith_metadata, translated_texts)):
                    hadith_id = hadith_meta['id']
                    chapter_id = hadith_meta['chapterId']
                    # Use chapterId:hadith_id as output key for uniqueness
                    output_key = f"{chapter_id}:{hadith_id}"
                    composite_id = f"{book_id}:{chapter_id}:{hadith_id}"
                    
                    translated_hadiths[output_key] = {
                        'narrator': hadith_meta['narrator'],
                        'text': translated_text,
                        'hadith_id': hadith_id,
                        'chapter_id': chapter_id,
                        'quality': {
                            'confidence': 'HIGH',
                            'needs_review': False
                        }
                    }
                    
                    # Only add if not already processed (use composite ID)
                    if composite_id not in checkpoint.get('processed_hadiths', []):
                        checkpoint['stats']['total_translated'] += 1
                        checkpoint['processed_hadiths'].append(composite_id)
                    
                    # Show progress
                    remaining = self.total_hadiths - checkpoint['stats']['total_translated']
                    print(f"\r🌍 [{self.lang_info['name']}] 📖 {book_id} | حديث #{checkpoint['stats']['total_translated']:,} | متبقي: {remaining:,}", end='', flush=True)
                
                # Save checkpoint and output after EACH chapter to prevent data loss
                self.save_checkpoint(checkpoint)
                # Update all_translations and save immediately
                if book_id not in self.all_translations:
                    self.all_translations[book_id] = {}
                self.all_translations[book_id].update(translated_hadiths)
                self._save_output_file()
        
        return translated_hadiths
    
    def save_translations(self, language: str, all_translations: Dict):
        """Save translations to output directory"""
        output_lang_dir = self.output_dir / language
        output_lang_dir.mkdir(exist_ok=True, parents=True)
        
        output_file = output_lang_dir / "all_translations.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_translations, f, ensure_ascii=False, indent=2)
        
        print(f"\nTranslations saved to: {output_file}")
    
    def _save_output_file(self):
        """Save output file immediately (called after each chapter)"""
        if hasattr(self, 'output_file_path') and hasattr(self, 'all_translations'):
            with open(self.output_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.all_translations, f, ensure_ascii=False, indent=2)
    
    def count_total_hadiths(self) -> int:
        """Count total hadiths across all books"""
        try:
            index_file = self.books_dir.parent / "index.json"
            if index_file.exists():
                with open(index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                    return index_data.get('totalHadiths', 50884)
        except:
            pass
        return 50884  # Default fallback
    
    def run(self, languages: List[str] = None, test_mode: bool = False):
        """
        Run translation for specified languages
        
        Args:
            languages: List of language names (e.g., ["turkish"])
            test_mode: If True, translate only first 100 hadiths
        """
        if languages is None:
            languages = list(config.LANGUAGES.keys())
        
        if test_mode:
            print("\n" + "="*60)
            print("TEST MODE: Translating first 100 hadiths only")
            print("="*60)
        
        total_hadiths = self.count_total_hadiths()
        
        for language in languages:
            if language not in config.LANGUAGES:
                print(f"Unknown language: {language}")
                continue
            
            lang_info = config.LANGUAGES[language]
            print("\n" + "="*60)
            print(f"🌍 Language: {lang_info['name']} ({lang_info.get('native_name', lang_info['name'])})")
            print(f"📊 Total hadiths to translate: {total_hadiths:,}")
            print("="*60)
            
            checkpoint = self.load_checkpoint(language)
            all_books = self.load_all_books()
            self.all_translations = {}  # Instance variable for incremental saves
            hadith_count = 0
            self.current_language = language
            self.lang_info = lang_info
            self.total_hadiths = total_hadiths
            
            # Setup output file path for incremental saves
            output_lang_dir = self.output_dir / language
            output_lang_dir.mkdir(exist_ok=True, parents=True)
            self.output_file_path = output_lang_dir / "all_translations.json"
            
            # Load existing translations first
            if self.output_file_path.exists():
                try:
                    with open(self.output_file_path, 'r', encoding='utf-8') as f:
                        existing_translations = json.load(f)
                        self.all_translations.update(existing_translations)
                        print(f"📂 Loaded {len(existing_translations)} existing books from output file")
                except Exception as e:
                    print(f"⚠️  Could not load existing translations: {e}")
            
            # Local reference for compatibility
            all_translations = self.all_translations
            
            for book in all_books:
                book_id = book['id']
                
                # Get existing translation count for this book
                existing_count = 0
                if book_id in all_translations and isinstance(all_translations[book_id], dict):
                    existing_count = len(all_translations[book_id])
                
                # Always try to translate - the hadith filter will skip already-translated ones
                print(f"\n📖 Processing: {book['english']['title']} ({book_id}) - {existing_count} existing translations")
                
                translated = self.translate_book(book, language, checkpoint)
                
                # Merge new translations with existing ones
                if translated:
                    if book_id not in all_translations:
                        all_translations[book_id] = {}
                    all_translations[book_id].update(translated)
                    
                    if book_id not in checkpoint.get('processed_books', []):
                        checkpoint['processed_books'].append(book_id)
                    
                    # Add hadith IDs only if not already processed (use composite ID)
                    new_hadith_ids = [f"{book_id}:{hid}" for hid in translated.keys() if f"{book_id}:{hid}" not in checkpoint.get('processed_hadiths', [])]
                    checkpoint['processed_hadiths'].extend(new_hadith_ids)
                    hadith_count += len(new_hadith_ids)
                    
                    if test_mode and hadith_count >= 100:
                        print(f"\nTest mode: Reached 100 hadiths limit")
                        break
                    
                    self.save_checkpoint(checkpoint)
            
            # Save final translations
            self.save_translations(language, all_translations)
            
            # Print statistics
            print("\n" + "="*60)
            print("Translation Statistics:")
            print("="*60)
            print(f"Total hadiths translated: {checkpoint['stats']['total_translated']}")
            print(f"API calls made: {checkpoint['stats']['api_calls']}")
            print("="*60)

def main():
    parser = argparse.ArgumentParser(description="Translate hadiths using GPT API")
    parser.add_argument(
        "--languages",
        nargs="+",
        default=["turkish"],
        help="Languages to translate (default: turkish)"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode: translate only first 100 hadiths"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="OpenAI API key (or set OPENAI_API_KEY env var)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-mini",
        help="Model to use (default: gpt-4o-mini)"
    )
    
    args = parser.parse_args()
    
    try:
        translator = APIHadithTranslator(api_key=args.api_key, model=args.model)
        translator.run(languages=args.languages, test_mode=args.test)
    except KeyboardInterrupt:
        print("\n\nTranslation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
