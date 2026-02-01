#!/usr/bin/env python3
"""
Main translation script for Hadith texts
Uses NLLB for translation + GPT for review
"""
import os
import json
import glob
import sys
from pathlib import Path
from tqdm import tqdm
from typing import Dict, List
import config
from translator import NLLBTranslator
from quality_check import QualityChecker
from reviewer import GPTReviewer

class HadithTranslator:
    def __init__(self, use_gpt_review: bool = True):
        """
        Initialize translation system
        
        Args:
            use_gpt_review: Whether to use GPT for reviewing low-quality translations
        """
        print("Initializing translation system...")
        self.translator = NLLBTranslator()
        self.quality_checker = QualityChecker()
        self.use_gpt_review = use_gpt_review
        
        if use_gpt_review:
            try:
                self.reviewer = GPTReviewer()
                print("GPT reviewer initialized")
            except Exception as e:
                print(f"Warning: GPT reviewer not available: {e}")
                self.use_gpt_review = False
                self.reviewer = None
        else:
            self.reviewer = None
        
        # Resolve paths relative to script location
        script_dir = Path(__file__).parent
        self.checkpoints_dir = script_dir / config.CHECKPOINTS_DIR
        self.output_dir = script_dir / config.OUTPUT_DIR
        self.books_dir = script_dir / config.BOOKS_DIR
        
        self.checkpoints_dir.mkdir(exist_ok=True, parents=True)
        self.output_dir.mkdir(exist_ok=True, parents=True)
    
    def load_checkpoint(self, language: str) -> Dict:
        """Load translation checkpoint for a language"""
        checkpoint_file = self.checkpoints_dir / f"{language}_checkpoint.json"
        if checkpoint_file.exists():
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "language": language,
            "processed_books": [],
            "processed_hadiths": [],
            "stats": {
                "total_translated": 0,
                "high_confidence": 0,
                "medium_confidence": 0,
                "low_confidence": 0
            }
        }
    
    def save_checkpoint(self, checkpoint: Dict):
        """Save translation checkpoint"""
        checkpoint_file = self.checkpoints_dir / f"{checkpoint['language']}_checkpoint.json"
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
    
    def translate_hadith(self, hadith: Dict, target_lang_code: str) -> Dict:
        """Translate a single hadith"""
        english_text = self.extract_hadith_text(hadith)
        
        if not english_text:
            return {
                'translated': '',
                'quality': {
                    'confidence': 'LOW',
                    'needs_review': True
                }
            }
        
        # Translate
        translated_text = self.translator.translate(english_text, target_lang_code)
        
        # Quality check
        quality = self.quality_checker.check(english_text, translated_text, target_lang_code)
        
        return {
            'translated': translated_text,
            'quality': quality
        }
    
    def translate_book(self, book: Dict, language: str, checkpoint: Dict) -> Dict:
        """Translate all hadiths in a book"""
        book_id = book['id']
        book_path = book['_path']
        target_lang_code = config.LANGUAGES[language]['nllb']
        
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
                    
                    # Filter out already processed hadiths
                    hadiths_to_translate = [
                        h for h in hadiths 
                        if h.get('id') not in checkpoint.get('processed_hadiths', [])
                    ]
                    
                    if hadiths_to_translate:
                        # Extract texts for batch translation
                        hadith_texts = []
                        hadith_metadata = []
                        for hadith in hadiths_to_translate:
                            english_text = self.extract_hadith_text(hadith)
                            hadith_texts.append(english_text)
                            hadith_metadata.append({
                                'id': hadith.get('id'),
                                'narrator': hadith.get('english', {}).get('narrator', ''),
                                'original_text': english_text
                            })
                        
                        # Batch translate
                        batch_size = config.TRANSLATION_BATCH_SIZE
                        translated_texts = []
                        
                        for i in tqdm(range(0, len(hadith_texts), batch_size), desc=f"  {book_id}"):
                            batch_texts = hadith_texts[i:i+batch_size]
                            batch_translated = self.translator.translate_batch(batch_texts, target_lang_code)
                            translated_texts.extend(batch_translated)
                        
                        # Process results and quality checks
                        for idx, (hadith_meta, translated_text) in enumerate(zip(hadith_metadata, translated_texts)):
                            hadith_id = hadith_meta['id']
                            
                            # Quality check
                            quality = self.quality_checker.check(
                                hadith_meta['original_text'], 
                                translated_text, 
                                target_lang_code
                            )
                            
                            translated_hadiths[hadith_id] = {
                                'narrator': hadith_meta['narrator'],
                                'text': translated_text,
                                'quality': quality
                            }
                            
                            # Update stats
                            conf = quality['confidence']
                            checkpoint['stats'][f'{conf.lower()}_confidence'] += 1
                            checkpoint['stats']['total_translated'] += 1
                            checkpoint['processed_hadiths'].append(hadith_id)
                            
                            # Save checkpoint every 50 hadiths
                            if checkpoint['stats']['total_translated'] % 50 == 0:
                                self.save_checkpoint(checkpoint)
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
                
                # Filter out already processed hadiths
                hadiths_to_translate = [
                    h for h in hadiths 
                    if h.get('id') not in checkpoint.get('processed_hadiths', [])
                ]
                
                if not hadiths_to_translate:
                    continue
                
                # Extract texts for batch translation
                hadith_texts = []
                hadith_metadata = []
                for hadith in hadiths_to_translate:
                    english_text = self.extract_hadith_text(hadith)
                    hadith_texts.append(english_text)
                    hadith_metadata.append({
                        'id': hadith.get('id'),
                        'narrator': hadith.get('english', {}).get('narrator', ''),
                        'original_text': english_text
                    })
                
                # Batch translate
                batch_size = config.TRANSLATION_BATCH_SIZE
                translated_texts = []
                
                for i in range(0, len(hadith_texts), batch_size):
                    batch_texts = hadith_texts[i:i+batch_size]
                    batch_translated = self.translator.translate_batch(batch_texts, target_lang_code)
                    translated_texts.extend(batch_translated)
                
                # Process results and quality checks
                for idx, (hadith_meta, translated_text) in enumerate(zip(hadith_metadata, translated_texts)):
                    hadith_id = hadith_meta['id']
                    
                    # Quality check
                    quality = self.quality_checker.check(
                        hadith_meta['original_text'], 
                        translated_text, 
                        target_lang_code
                    )
                    
                    translated_hadiths[hadith_id] = {
                        'narrator': hadith_meta['narrator'],
                        'text': translated_text,
                        'quality': quality
                    }
                    
                    # Update stats
                    conf = quality['confidence']
                    checkpoint['stats'][f'{conf.lower()}_confidence'] += 1
                    checkpoint['stats']['total_translated'] += 1
                    checkpoint['processed_hadiths'].append(hadith_id)
                    
                    # Save checkpoint every 50 hadiths
                    if checkpoint['stats']['total_translated'] % 50 == 0:
                        self.save_checkpoint(checkpoint)
        
        return translated_hadiths
    
    def review_with_gpt(self, hadiths_to_review: List[Dict], language: str) -> Dict:
        """Review low-quality translations with GPT"""
        if not self.reviewer:
            return {}
        
        language_name = config.LANGUAGES[language]['name']
        corrections = {}
        
        # Process in batches
        batch_size = config.REVIEW_BATCH_SIZE
        for i in range(0, len(hadiths_to_review), batch_size):
            batch = hadiths_to_review[i:i + batch_size]
            print(f"  Reviewing batch {i//batch_size + 1}...")
            
            review_items = [
                {
                    'hadith_id': h['hadith_id'],
                    'english': h['english'],
                    'translated': h['translated']
                }
                for h in batch
            ]
            
            results = self.reviewer.review_batch(review_items, language_name)
            
            for result in results:
                if result['status'] == 'FIX' and result.get('corrected'):
                    corrections[result['hadith_id']] = result['corrected']
        
        return corrections
    
    def save_translations(self, language: str, all_translations: Dict):
        """Save translations to output directory"""
        lang_output_dir = self.output_dir / language
        lang_output_dir.mkdir(exist_ok=True)
        
        output_file = lang_output_dir / "all_translations.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_translations, f, ensure_ascii=False, indent=2)
        
        print(f"\nTranslations saved to: {output_file}")
    
    def run(self, languages: List[str] = None, test_mode: bool = False):
        """
        Run translation for specified languages
        
        Args:
            languages: List of language keys (defaults to all in config)
            test_mode: If True, only translate first 100 hadiths
        """
        if languages is None:
            languages = list(config.LANGUAGES.keys())
        
        all_books = self.load_all_books()
        
        if test_mode:
            print("TEST MODE: Translating first 100 hadiths only")
        
        for language in languages:
            print(f"\n{'='*60}")
            print(f"Processing language: {language} ({config.LANGUAGES[language]['name']})")
            print(f"{'='*60}")
            
            checkpoint = self.load_checkpoint(language)
            target_lang_code = config.LANGUAGES[language]['nllb']
            all_translations = {}
            hadiths_to_review = []
            
            hadith_count = 0
            for book in all_books:
                book_id = book['id']
                
                if book_id in checkpoint.get('processed_books', []):
                    print(f"Skipping already processed book: {book_id}")
                    continue
                
                translated = self.translate_book(book, language, checkpoint)
                all_translations[book_id] = translated
                
                # Collect hadiths needing review
                for hadith_id, data in translated.items():
                    if data['quality'].get('needs_review'):
                        hadiths_to_review.append({
                            'hadith_id': hadith_id,
                            'english': '',  # Will be filled from original
                            'translated': data['text']
                        })
                
                checkpoint['processed_books'].append(book_id)
                checkpoint['processed_hadiths'].extend(list(translated.keys()))
                
                hadith_count += len(translated)
                
                if test_mode and hadith_count >= 100:
                    print(f"\nTest mode: Reached 100 hadiths limit")
                    break
                
                self.save_checkpoint(checkpoint)
            
            # GPT Review for low-quality translations
            if self.use_gpt_review and hadiths_to_review:
                print(f"\nReviewing {len(hadiths_to_review)} hadiths with GPT...")
                corrections = self.review_with_gpt(hadiths_to_review, language)
                
                # Apply corrections
                for book_id, book_translations in all_translations.items():
                    for hadith_id, correction in corrections.items():
                        if hadith_id in book_translations:
                            book_translations[hadith_id]['text'] = correction
                            book_translations[hadith_id]['quality']['confidence'] = 'REVIEWED'
            
            # Save final translations
            self.save_translations(language, all_translations)
            
            # Print stats
            stats = checkpoint['stats']
            print(f"\nTranslation Statistics for {language}:")
            print(f"  Total translated: {stats['total_translated']}")
            print(f"  High confidence: {stats.get('high_confidence', 0)}")
            print(f"  Medium confidence: {stats.get('medium_confidence', 0)}")
            print(f"  Low confidence: {stats.get('low_confidence', 0)}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Translate Hadith texts")
    parser.add_argument("--languages", nargs="+", help="Languages to translate (default: all)")
    parser.add_argument("--test", action="store_true", help="Test mode (100 hadiths only)")
    parser.add_argument("--no-gpt", action="store_true", help="Skip GPT review")
    
    args = parser.parse_args()
    
    translator = HadithTranslator(use_gpt_review=not args.no_gpt)
    translator.run(languages=args.languages, test_mode=args.test)
