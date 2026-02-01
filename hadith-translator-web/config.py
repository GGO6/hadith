"""
Configuration for Hadith Translator Web
Uses environment variables for Railway deployment
"""
import os
from pathlib import Path

# Base path - use DATA_DIR for Railway volume or current dir
BASE_DIR = Path(os.getenv("DATA_DIR", os.path.dirname(os.path.abspath(__file__))))
BOOKS_DIR = BASE_DIR / os.getenv("BOOKS_PATH", "data/books")
OUTPUT_DIR = BASE_DIR / "output"
CHECKPOINTS_DIR = BASE_DIR / "checkpoints"

# Ensure dirs exist when app runs
def ensure_dirs():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "data").mkdir(parents=True, exist_ok=True)

LANGUAGES = {
    "turkish": {"name": "Turkish", "native_name": "Türkçe", "arabic_name": "التركية", "code": "tr"},
    "french": {"name": "French", "native_name": "Français", "arabic_name": "الفرنسية", "code": "fr"},
    "indonesian": {"name": "Indonesian", "native_name": "Bahasa Indonesia", "arabic_name": "الإندونيسية", "code": "id"},
    "urdu": {"name": "Urdu", "native_name": "اردو", "arabic_name": "الأردية", "code": "ur"},
    "bengali": {"name": "Bengali", "native_name": "বাংলা", "arabic_name": "البنغالية", "code": "bn"},
    "german": {"name": "German", "native_name": "Deutsch", "arabic_name": "الألمانية", "code": "de"},
    "spanish": {"name": "Spanish", "native_name": "Español", "arabic_name": "الإسبانية", "code": "es"},
    "russian": {"name": "Russian", "native_name": "Русский", "arabic_name": "الروسية", "code": "ru"},
}
