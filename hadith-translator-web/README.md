# Hadith Translator Web

تطبيق ويب لترجمة الأحاديث النبوية باستخدام GPT-4o-mini. يعمل على Railway (أو أي سيرفر) بحيث لا تحتاج لفتح جهازك لتشغيل الترجمة.

## المميزات

- **لوحة تحكم ويب**: بدء/إيقاف الترجمة ومتابعة التقدم
- **يعمل 24/7**: على Railway أو أي VPS
- **حفظ تلقائي**: بعد كل فصل لمنع فقدان التقدم
- **لغات متعددة**: تركي، فرنسي، إندونيسي، أردو، بنغالي، ألماني، إسباني، روسي

## المتطلبات

- Python 3.11+
- مفتاح OpenAI API (`OPENAI_API_KEY`)
- بيانات الكتب (مجلد `books` من مشروع hadith)

## الإعداد المحلي

```bash
# استنساخ أو نسخ المشروع
cd hadith-translator-web

# إنشاء بيئة افتراضية
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# تثبيت المتطلبات
pip install -r requirements.txt

# نسخ بيانات الكتب من مشروع hadith الرئيسي
mkdir -p data/books
cp -r ../hadith/books/* data/books/
cp ../hadith/index.json data/

# تعيين مفتاح API
export OPENAI_API_KEY="sk-..."

# تشغيل التطبيق
python app.py
```

افتح المتصفح على: http://localhost:5000

## النشر على Railway

1. **إنشاء مشروع جديد** على [Railway](https://railway.app) وربطه بهذا المستودع.

2. **إضافة المتغيرات (Variables)**:
   - `OPENAI_API_KEY`: مفتاح OpenAI API
   - (اختياري) `DATA_DIR`: المسار لجذر البيانات إذا استخدمت Volume
   - (اختياري) `BOOKS_PATH`: مسار فرعي للكتب داخل DATA_DIR (افتراضي: `data/books`)

3. **الكتب والبيانات**:
   - **الخيار أ**: إضافة مجلد الكتب إلى المستودع (مجلد `data/books` مع نفس هيكل مشروع hadith: `the_9_books`, `forties`, `other_books`)، وملف `data/index.json`.
   - **الخيار ب**: استخدام Railway Volume وربطه بـ `DATA_DIR` ونسخ الكتب هناك بعد النشر.

4. **النشر**: Railway يبني المشروع تلقائياً من `requirements.txt` ويشغّل `Procfile`.

## هيكل المشروع

```
hadith-translator-web/
├── app.py              # تطبيق Flask والواجهة
├── config.py           # الإعدادات (من env)
├── translator/
│   ├── api_translator.py   # ترجمة GPT
│   └── runner.py           # تشغيل الترجمة في الخلفية
├── data/                # يجب نسخ الكتب هنا
│   ├── books/          # نفس هيكل hadith/books
│   └── index.json
├── output/             # مخرجات الترجمة (تُنشأ تلقائياً)
├── checkpoints/        # نقاط الحفظ (تُنشأ تلقائياً)
├── requirements.txt
├── Procfile
├── railway.toml
└── README.md
```

## API

| المسار | الوصف |
|--------|--------|
| `GET /` | لوحة التحكم |
| `GET /api/status` | الحالة الحالية (جاري التشغيل، التقدم، إلخ) |
| `GET /api/languages` | عدد الأحاديث المترجمة لكل لغة |
| `POST /api/start` | بدء الترجمة (body: `{"language": "turkish"}`) |
| `POST /api/stop` | إيقاف الترجمة |

## التكلفة على Railway

- الخطة المدفوعة تكفي لتشغيل التطبيق 24/7.
- استهلاك OpenAI يُحسب حسب عدد الأحاديث واللغات المترجمة.

## الترخيص

نفس ترخيص مشروع hadith.
