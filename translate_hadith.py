#!/usr/bin/env python3
"""
Hadith Translation Script
ترجمة الأحاديث النبوية إلى لغات متعددة

Usage:
    python translate_hadith.py --lang tr --book bukhari
    python translate_hadith.py --lang all --book all
    python translate_hadith.py --lang tr --test  # Test mode with 10 hadiths
"""

import json
import os
import sys
import argparse
import asyncio
import aiohttp
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import hashlib
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Project paths
PROJECT_ROOT = Path(__file__).parent
HADITH_DIR = PROJECT_ROOT / "hadith"
BOOKS_DIR = HADITH_DIR / "books"
TRANSLATIONS_DIR = HADITH_DIR / "translations"
GLOSSARY_PATH = TRANSLATIONS_DIR / "glossary.json"

# Supported languages
SUPPORTED_LANGUAGES = {
    "tr": "Turkish",
    "fr": "French", 
    "id": "Indonesian",
    "ur": "Urdu",
    "bn": "Bengali",
    "de": "German",
    "es": "Spanish",
    "ru": "Russian"
}

# Language priorities (order of translation)
LANGUAGE_PRIORITY = ["tr", "id", "ur", "bn", "fr", "es", "de", "ru"]


@dataclass
class TranslationConfig:
    """Configuration for translation API"""
    provider: str  # "google", "deepl", "azure", "openai"
    api_key: str
    endpoint: Optional[str] = None
    model: Optional[str] = None  # For OpenAI


class Glossary:
    """Manages Islamic terminology translations"""
    
    def __init__(self, glossary_path: Path):
        self.glossary_path = glossary_path
        self.data = self._load_glossary()
    
    def _load_glossary(self) -> Dict:
        """Load glossary from JSON file"""
        if self.glossary_path.exists():
            with open(self.glossary_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"terms": {}, "bookTitles": {}, "categories": {}}
    
    def get_term(self, english_term: str, target_lang: str) -> Optional[str]:
        """Get translated term for a specific language"""
        if english_term in self.data.get("terms", {}):
            return self.data["terms"][english_term].get(target_lang)
        return None
    
    def get_book_title(self, english_title: str, target_lang: str) -> Optional[str]:
        """Get translated book title"""
        if english_title in self.data.get("bookTitles", {}):
            return self.data["bookTitles"][english_title].get(target_lang)
        return None
    
    def get_category(self, english_category: str, target_lang: str) -> Optional[str]:
        """Get translated category name"""
        if english_category in self.data.get("categories", {}):
            return self.data["categories"][english_category].get(target_lang)
        return None
    
    def apply_glossary(self, text: str, target_lang: str) -> str:
        """Apply glossary replacements to text before/after translation"""
        result = text
        for english_term, translations in self.data.get("terms", {}).items():
            if target_lang in translations:
                result = result.replace(english_term, translations[target_lang])
        return result


class TranslationProvider:
    """Base class for translation providers"""
    
    async def translate(self, text: str, target_lang: str, source_lang: str = "en") -> str:
        raise NotImplementedError


class GoogleTranslateProvider(TranslationProvider):
    """Google Cloud Translation API provider"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint = "https://translation.googleapis.com/language/translate/v2"
    
    async def translate(self, text: str, target_lang: str, source_lang: str = "en") -> str:
        async with aiohttp.ClientSession() as session:
            params = {
                "key": self.api_key,
                "q": text,
                "source": source_lang,
                "target": target_lang,
                "format": "text"
            }
            async with session.post(self.endpoint, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["data"]["translations"][0]["translatedText"]
                else:
                    error = await response.text()
                    raise Exception(f"Google Translate API error: {error}")


class DeepLProvider(TranslationProvider):
    """DeepL API provider"""
    
    # DeepL language codes mapping
    LANG_MAP = {
        "tr": "TR",
        "fr": "FR",
        "id": "ID",
        "de": "DE",
        "es": "ES",
        "ru": "RU"
        # Note: DeepL doesn't support Urdu (ur) and Bengali (bn)
    }
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint = "https://api-free.deepl.com/v2/translate"  # Use api.deepl.com for Pro
    
    async def translate(self, text: str, target_lang: str, source_lang: str = "en") -> str:
        if target_lang not in self.LANG_MAP:
            raise Exception(f"DeepL doesn't support language: {target_lang}")
        
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"DeepL-Auth-Key {self.api_key}"}
            data = {
                "text": [text],
                "source_lang": "EN",
                "target_lang": self.LANG_MAP[target_lang]
            }
            async with session.post(self.endpoint, headers=headers, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["translations"][0]["text"]
                else:
                    error = await response.text()
                    raise Exception(f"DeepL API error: {error}")


class AzureTranslatorProvider(TranslationProvider):
    """Azure Translator API provider"""
    
    def __init__(self, api_key: str, region: str = "eastus"):
        self.api_key = api_key
        self.region = region
        self.endpoint = "https://api.cognitive.microsofttranslator.com/translate"
    
    async def translate(self, text: str, target_lang: str, source_lang: str = "en") -> str:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Ocp-Apim-Subscription-Key": self.api_key,
                "Ocp-Apim-Subscription-Region": self.region,
                "Content-type": "application/json"
            }
            params = {
                "api-version": "3.0",
                "from": source_lang,
                "to": target_lang
            }
            body = [{"text": text}]
            async with session.post(self.endpoint, headers=headers, params=params, json=body) as response:
                if response.status == 200:
                    result = await response.json()
                    return result[0]["translations"][0]["text"]
                else:
                    error = await response.text()
                    raise Exception(f"Azure Translator API error: {error}")


class OpenAIProvider(TranslationProvider):
    """OpenAI GPT API provider for context-aware translation"""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.api_key = api_key
        self.model = model
        self.endpoint = "https://api.openai.com/v1/chat/completions"
    
    async def translate(self, text: str, target_lang: str, source_lang: str = "en") -> str:
        lang_names = {
            "tr": "Turkish", "fr": "French", "id": "Indonesian",
            "ur": "Urdu", "bn": "Bengali", "de": "German",
            "es": "Spanish", "ru": "Russian"
        }
        
        system_prompt = """You are an expert translator specializing in Islamic religious texts.
Translate the following hadith text accurately while:
1. Preserving religious terminology (keep phrases like (ﷺ) as is)
2. Maintaining the reverent tone appropriate for prophetic narrations
3. Keeping names of companions and places as transliterations
4. Ensuring theological accuracy"""

        user_prompt = f"Translate this hadith from English to {lang_names.get(target_lang, target_lang)}:\n\n{text}"
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            body = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.3
            }
            async with session.post(self.endpoint, headers=headers, json=body) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    error = await response.text()
                    raise Exception(f"OpenAI API error: {error}")


class HadithTranslator:
    """Main hadith translation orchestrator"""
    
    def __init__(self, provider: TranslationProvider, glossary: Glossary):
        self.provider = provider
        self.glossary = glossary
        self.stats = {
            "translated": 0,
            "failed": 0,
            "skipped": 0
        }
    
    async def translate_text(self, text: str, target_lang: str) -> str:
        """Translate a single text with glossary support"""
        # Pre-process with glossary (for terms that shouldn't be translated)
        processed_text = self.glossary.apply_glossary(text, target_lang)
        
        # Translate
        try:
            translated = await self.provider.translate(processed_text, target_lang)
            self.stats["translated"] += 1
            return translated
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            self.stats["failed"] += 1
            return text  # Return original on failure
    
    async def translate_hadith(self, hadith: Dict, target_lang: str) -> Dict:
        """Translate a single hadith"""
        translated_hadith = hadith.copy()
        
        if "english" in hadith and isinstance(hadith["english"], dict):
            english = hadith["english"]
            translated = {}
            
            if "narrator" in english:
                translated["narrator"] = await self.translate_text(english["narrator"], target_lang)
            
            if "text" in english:
                translated["text"] = await self.translate_text(english["text"], target_lang)
            
            translated_hadith[target_lang] = translated
        
        return translated_hadith
    
    async def translate_chapter(self, chapter_path: Path, target_lang: str, output_path: Path) -> Dict:
        """Translate an entire chapter file"""
        logger.info(f"Translating chapter: {chapter_path.name} to {target_lang}")
        
        with open(chapter_path, 'r', encoding='utf-8') as f:
            chapter_data = json.load(f)
        
        # Translate metadata
        if "metadata" in chapter_data:
            meta = chapter_data["metadata"]
            if "english" in meta:
                translated_meta = {}
                for key in ["title", "author", "introduction"]:
                    if key in meta["english"] and meta["english"][key]:
                        translated_meta[key] = await self.translate_text(meta["english"][key], target_lang)
                meta[target_lang] = translated_meta
        
        # Translate chapter info
        if "chapter" in chapter_data and "english" in chapter_data["chapter"]:
            chapter_data["chapter"][target_lang] = await self.translate_text(
                chapter_data["chapter"]["english"], target_lang
            )
        
        # Translate hadiths
        if "hadiths" in chapter_data:
            translated_hadiths = []
            for hadith in chapter_data["hadiths"]:
                translated_hadith = await self.translate_hadith(hadith, target_lang)
                translated_hadiths.append(translated_hadith)
            chapter_data["hadiths"] = translated_hadiths
        
        # Save translated chapter
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(chapter_data, f, ensure_ascii=False, indent=2)
        
        return chapter_data
    
    async def translate_book(self, book_id: str, target_lang: str):
        """Translate an entire book"""
        logger.info(f"Starting translation of book '{book_id}' to '{target_lang}'")
        
        # Find book directory
        book_path = None
        for category in ["the_9_books", "forties", "other_books"]:
            potential_path = BOOKS_DIR / category / book_id
            if potential_path.exists():
                book_path = potential_path
                break
        
        if not book_path:
            raise ValueError(f"Book not found: {book_id}")
        
        # Determine output directory
        category = book_path.parent.name
        output_dir = TRANSLATIONS_DIR / target_lang / "books" / category / book_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Translate metadata.json
        metadata_path = book_path / "metadata.json"
        if metadata_path.exists():
            await self.translate_metadata(metadata_path, target_lang, output_dir / "metadata.json")
        
        # Translate chapters
        chapters_dir = book_path / "chapters"
        if chapters_dir.exists():
            output_chapters_dir = output_dir / "chapters"
            output_chapters_dir.mkdir(parents=True, exist_ok=True)
            
            chapter_files = sorted(chapters_dir.glob("*.json"), key=lambda x: int(x.stem))
            for chapter_file in chapter_files:
                output_file = output_chapters_dir / chapter_file.name
                await self.translate_chapter(chapter_file, target_lang, output_file)
        
        # Translate all.json (for forties books)
        all_path = book_path / "all.json"
        if all_path.exists():
            await self.translate_chapter(all_path, target_lang, output_dir / "all.json")
        
        logger.info(f"Completed translation of book '{book_id}' to '{target_lang}'")
        logger.info(f"Stats: {self.stats}")
    
    async def translate_metadata(self, metadata_path: Path, target_lang: str, output_path: Path):
        """Translate book metadata"""
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Translate book-level metadata
        if "english" in metadata:
            translated = {}
            for key in ["title", "author", "introduction"]:
                if key in metadata["english"] and metadata["english"][key]:
                    # Check glossary first for book titles
                    glossary_translation = self.glossary.get_book_title(
                        metadata["english"].get("title", ""), target_lang
                    )
                    if key == "title" and glossary_translation:
                        translated[key] = glossary_translation
                    else:
                        translated[key] = await self.translate_text(metadata["english"][key], target_lang)
            metadata[target_lang] = translated
        
        # Translate chapter titles
        if "chapters" in metadata:
            for chapter in metadata["chapters"]:
                if "english" in chapter and chapter["english"]:
                    chapter[target_lang] = await self.translate_text(chapter["english"], target_lang)
        
        # Save translated metadata
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)


def get_provider(config: TranslationConfig) -> TranslationProvider:
    """Factory function to get translation provider"""
    if config.provider == "google":
        return GoogleTranslateProvider(config.api_key)
    elif config.provider == "deepl":
        return DeepLProvider(config.api_key)
    elif config.provider == "azure":
        return AzureTranslatorProvider(config.api_key)
    elif config.provider == "openai":
        return OpenAIProvider(config.api_key, config.model or "gpt-4")
    else:
        raise ValueError(f"Unknown provider: {config.provider}")


def get_all_books() -> List[str]:
    """Get list of all book IDs"""
    books = []
    for category in ["the_9_books", "forties", "other_books"]:
        category_dir = BOOKS_DIR / category
        if category_dir.exists():
            for book_dir in category_dir.iterdir():
                if book_dir.is_dir() and not book_dir.name.startswith('.'):
                    books.append(book_dir.name)
    return books


async def main():
    parser = argparse.ArgumentParser(description="Translate Hadith collections")
    parser.add_argument("--lang", required=True, help="Target language code (tr, fr, id, ur, bn, de, es, ru) or 'all'")
    parser.add_argument("--book", required=True, help="Book ID to translate or 'all'")
    parser.add_argument("--provider", default="google", choices=["google", "deepl", "azure", "openai"])
    parser.add_argument("--api-key", help="API key (or set via environment variable)")
    parser.add_argument("--test", action="store_true", help="Test mode - translate only 10 hadiths")
    
    args = parser.parse_args()
    
    # Get API key
    api_key = args.api_key or os.environ.get(f"{args.provider.upper()}_API_KEY")
    if not api_key:
        logger.error(f"API key required. Set --api-key or {args.provider.upper()}_API_KEY environment variable")
        sys.exit(1)
    
    # Initialize
    config = TranslationConfig(provider=args.provider, api_key=api_key)
    provider = get_provider(config)
    glossary = Glossary(GLOSSARY_PATH)
    translator = HadithTranslator(provider, glossary)
    
    # Determine languages and books
    languages = LANGUAGE_PRIORITY if args.lang == "all" else [args.lang]
    books = get_all_books() if args.book == "all" else [args.book]
    
    # Validate languages
    for lang in languages:
        if lang not in SUPPORTED_LANGUAGES:
            logger.error(f"Unsupported language: {lang}")
            sys.exit(1)
    
    # Start translation
    start_time = datetime.now()
    logger.info(f"Starting translation: {len(books)} books to {len(languages)} languages")
    
    for lang in languages:
        logger.info(f"\n{'='*50}")
        logger.info(f"Translating to: {SUPPORTED_LANGUAGES[lang]} ({lang})")
        logger.info(f"{'='*50}")
        
        for book in books:
            try:
                await translator.translate_book(book, lang)
            except Exception as e:
                logger.error(f"Failed to translate book '{book}' to '{lang}': {e}")
    
    # Summary
    elapsed = datetime.now() - start_time
    logger.info(f"\n{'='*50}")
    logger.info("TRANSLATION COMPLETE")
    logger.info(f"Time elapsed: {elapsed}")
    logger.info(f"Stats: {translator.stats}")
    logger.info(f"{'='*50}")


if __name__ == "__main__":
    asyncio.run(main())
