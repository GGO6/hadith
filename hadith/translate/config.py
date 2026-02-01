"""
Configuration file for translation system
"""

# NLLB language codes mapping
LANGUAGES = {
    "turkish": {
        "nllb": "tur_Latn",
        "name": "Turkish",
        "native_name": "Türkçe",
        "arabic_name": "التركية",
        "code": "tr"
    },
    "french": {
        "nllb": "fra_Latn",
        "name": "French",
        "native_name": "Français",
        "arabic_name": "الفرنسية",
        "code": "fr"
    },
    "indonesian": {
        "nllb": "ind_Latn",
        "name": "Indonesian",
        "native_name": "Bahasa Indonesia",
        "arabic_name": "الإندونيسية",
        "code": "id"
    },
    "urdu": {
        "nllb": "urd_Arab",
        "name": "Urdu",
        "native_name": "اردو",
        "arabic_name": "الأردية",
        "code": "ur"
    },
    "bengali": {
        "nllb": "ben_Beng",
        "name": "Bengali",
        "native_name": "বাংলা",
        "arabic_name": "البنغالية",
        "code": "bn"
    },
    "german": {
        "nllb": "deu_Latn",
        "name": "German",
        "native_name": "Deutsch",
        "arabic_name": "الألمانية",
        "code": "de"
    },
    "spanish": {
        "nllb": "spa_Latn",
        "name": "Spanish",
        "native_name": "Español",
        "arabic_name": "الإسبانية",
        "code": "es"
    },
    "russian": {
        "nllb": "rus_Cyrl",
        "name": "Russian",
        "native_name": "Русский",
        "arabic_name": "الروسية",
        "code": "ru"
    }
}

# NLLB Model configuration
NLLB_MODEL = "facebook/nllb-200-distilled-1.3B"
SOURCE_LANG = "eng_Latn"

# Quality thresholds
SIMILARITY_HIGH = 0.85
SIMILARITY_MEDIUM = 0.70
LENGTH_RATIO_MIN = 0.5
LENGTH_RATIO_MAX = 2.5

# Batch sizes
TRANSLATION_BATCH_SIZE = 8
REVIEW_BATCH_SIZE = 10

# Paths (relative to translate/ directory)
BOOKS_DIR = "../books"
OUTPUT_DIR = "output"
CHECKPOINTS_DIR = "checkpoints"
