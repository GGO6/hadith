# Hadith Translation Project / مشروع ترجمة الأحاديث

## Supported Languages / اللغات المدعومة

| Code | Language | Native Name | Status |
|------|----------|-------------|--------|
| ar | Arabic | العربية | ✅ Complete |
| en | English | English | ✅ Complete |
| tr | Turkish | Türkçe | 🔄 In Progress |
| fr | French | Français | ⏳ Pending |
| id | Indonesian | Bahasa Indonesia | ⏳ Pending |
| ur | Urdu | اردو | ⏳ Pending |
| bn | Bengali | বাংলা | ⏳ Pending |
| de | German | Deutsch | ⏳ Pending |
| es | Spanish | Español | ⏳ Pending |
| ru | Russian | Русский | ⏳ Pending |

## Directory Structure / هيكل المجلدات

```
translations/
├── glossary.json          # Islamic terminology dictionary
├── tr/                    # Turkish translations
│   └── books/
│       ├── the_9_books/
│       ├── forties/
│       └── other_books/
├── fr/                    # French translations
├── id/                    # Indonesian translations
├── ur/                    # Urdu translations
├── bn/                    # Bengali translations
├── de/                    # German translations
├── es/                    # Spanish translations
└── ru/                    # Russian translations
```

## Usage / الاستخدام

### Translate a specific book to a specific language:
```bash
python translate_hadith.py --lang tr --book bukhari --provider google --api-key YOUR_API_KEY
```

### Translate all books to a specific language:
```bash
python translate_hadith.py --lang tr --book all --provider google --api-key YOUR_API_KEY
```

### Translate to all languages:
```bash
python translate_hadith.py --lang all --book all --provider google --api-key YOUR_API_KEY
```

### Test mode (10 hadiths only):
```bash
python translate_hadith.py --lang tr --book bukhari --test
```

## API Providers / مزودي خدمة الترجمة

| Provider | Environment Variable | Notes |
|----------|---------------------|-------|
| Google Cloud Translation | `GOOGLE_API_KEY` | Best overall coverage |
| DeepL | `DEEPL_API_KEY` | Best quality for European languages |
| Azure Translator | `AZURE_API_KEY` | Good balance |
| OpenAI | `OPENAI_API_KEY` | Best for context-aware religious text |

## Translation Statistics / إحصائيات الترجمة

| Category | Books | Hadiths |
|----------|-------|---------|
| The Nine Books | 9 | 40,943 |
| The Forties | 3 | 122 |
| Other Books | 5 | 9,819 |
| **Total** | **17** | **50,884** |
