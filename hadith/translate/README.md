# Hadith Translation System

نظام ترجمة الأحاديث النبوية باستخدام NLLB (محلي) + GPT-4o-mini (مراجعة)

## الإعداد

1. تثبيت المتطلبات:
```bash
cd hadith/translate
pip install -r requirements.txt
```

2. إعداد OpenAI API Key (للمراجعة):
```bash
export OPENAI_API_KEY="your-api-key-here"
```

## الاستخدام

### ترجمة تجريبية (100 حديث):
```bash
python run_translation.py --test --languages turkish
```

### ترجمة لغة واحدة:
```bash
python run_translation.py --languages turkish
```

### ترجمة جميع اللغات:
```bash
python run_translation.py
```

### ترجمة بدون مراجعة GPT:
```bash
python run_translation.py --no-gpt
```

## الملفات

- `config.py`: إعدادات اللغات والنماذج
- `glossary.json`: قاموس المصطلحات الدينية
- `translator.py`: محرك الترجمة NLLB
- `quality_check.py`: فحص الجودة (back-translation + semantic similarity)
- `reviewer.py`: مراجعة GPT-4o-mini
- `run_translation.py`: السكريبت الرئيسي

## المخرجات

- `checkpoints/`: نقاط حفظ التقدم
- `output/{language}/all_translations.json`: الترجمات النهائية

## التكلفة المتوقعة

- NLLB: مجاني (محلي)
- GPT-4o-mini مراجعة: ~$5-10 للترجمة الكاملة
