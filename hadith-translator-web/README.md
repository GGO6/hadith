# Hadith Translator Web

تطبيق ويب لترجمة الأحاديث النبوية باستخدام GPT-4o-mini. يعمل على Railway (أو أي سيرفر) بحيث لا تحتاج لفتح جهازك لتشغيل الترجمة.

## المميزات

- **لوحة تحكم ويب**: بدء/إيقاف الترجمة ومتابعة التقدم
- **يعمل 24/7**: على Railway أو أي VPS
- **حفظ تلقائي**: بعد كل فصل لمنع فقدان التقدم
- **قاعدة بيانات**: دعم PostgreSQL (Railway) أو SQLite محلياً لحفظ التقدم والترجمات
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

**قائمة تحقق مفصّلة:** راجع [RAILWAY_CHECKLIST.md](RAILWAY_CHECKLIST.md) لخطوات واضحة حتى يعمل التطبيق بشكل جيد على Railway.

المستودع يحتوي على مجلدات متعددة (`hadith/`, `hadith-translator-web/`)، لذلك تم إضافة **حل يعمل بدون Root Directory**:

### الحل: Dockerfile في جذر المستودع (مفعّل)

في **جذر المستودع** (نفس مستوى `hadith-translator-web/`) تم إضافة:

- **`Dockerfile`** — يبني التطبيق من مجلد `hadith-translator-web/` ويضمّن كتب الأحاديث من `hadith/books/` و `hadith/index.json` داخل الصورة.
- **`railway.toml`** — يوجّه Railway لاستخدام **DOCKERFILE** بدلاً من Railpack.

بهذا يبني Railway باستخدام الـ Dockerfile ويشغّل التطبيق دون الحاجة لأي إعداد **Root Directory** في الواجهة.

### ربط قاعدة بيانات PostgreSQL (اختياري)

لحفظ التقدم والترجمات في قاعدة بيانات بدلاً من ملفات JSON:

1. في لوحة Railway: **+ New** → **Database** → **Add PostgreSQL**
2. ستُضاف تلقائياً متغيرات البيئة مثل `DATABASE_URL` لخدمة التطبيق
3. أعد نشر التطبيق (Redeploy) بعد إضافة القاعدة

بدون `DATABASE_URL` يستخدم التطبيق **SQLite** محلياً (ملف `hadith_translator.db` في مجلد التطبيق).

**إذا استمرّ البناء بـ Railpack:** من إعدادات الخدمة (Settings) اختر **Builder** أو **Build** وغيِّر البناء إلى **Dockerfile**، أو عيّن مسار ملف الإعداد (Config File) إلى `railway.toml` في الجذر.

### إذا وجدت "Root Directory" لاحقاً (اختياري)

في بعض الواجهات تكون تحت: **Settings** → **Source** (أو **Build**) → **Root Directory**.  
إذا ظهرت، يمكنك تعيينها إلى `hadith-translator-web` والاعتماد على Railpack بدلاً من Dockerfile.

### خطوات النشر

1. **إنشاء مشروع جديد** على [Railway](https://railway.app) وربطه بالمستودع.

2. **تعيين Root Directory** إلى `hadith-translator-web` (كما في الأعلى).

3. **إضافة المتغيرات (Variables)**:
   - `OPENAI_API_KEY`: مفتاح OpenAI API
   - (لحماية اللوحة) `ADMIN_USERNAME` و `ADMIN_PASSWORD`: اسم المستخدم وكلمة المرور لتسجيل الدخول؛ إذا وُجدا يُطلب تسجيل الدخول قبل الوصول للوحة والـ API.
   - (عند تفعيل الدخول) `SECRET_KEY`: مفتاح سري لـ session (مثلاً سلسلة عشوائية طويلة).
   - (اختياري) `OPENAI_DELAY_SEC`: ثوانٍ بين كل طلب (افتراضي: 6) لتجنب 429
   - (اختياري) `OPENAI_BATCH_SIZE`: عدد الأحاديث في كل طلب (افتراضي: 5، أقصى 15)
   - (اختياري) `OPENAI_RATE_LIMIT_WAIT`: ثوانٍ انتظار عند 429 ثم إعادة المحاولة (افتراضي: 60)
   - (اختياري) `OPENAI_RATE_LIMIT_RETRIES`: عدد إعادة المحاولة بعد 429 (افتراضي: 5)
   - (اختياري) `DATA_DIR`: المسار لجذر البيانات إذا استخدمت Volume
   - (اختياري) `BOOKS_PATH`: مسار فرعي للكتب داخل DATA_DIR (افتراضي: `data/books`)

3. **الكتب والبيانات**: الـ Dockerfile ينسخ تلقائياً `hadith/books/` و `hadith/index.json` إلى الصورة، فلا حاجة لإعداد إضافي للكتب عند النشر من جذر المستودع.

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

## السجلات (Logs)

التطبيق يكتب سجلات إلى **stdout** (مثلاً: بداية الترجمة، كل كتاب/فصل، حفظ نقطة التقدم، التوقف، الأخطاء). على Railway تظهر في **Logs** للخدمة:

- من لوحة Railway: خدمة **hadith** → **Logs** (أو **Observability** → **Logs**).
- الصيغة: `YYYY-MM-DD HH:MM:SS [LEVEL] hadith: الرسالة`.

أمثلة على الرسائل:
- `Translation started: language=russian`
- `book start: book_id=abudawud`
- `chapter done: book_id=abudawud chapter=1.json total_translated=1234 remaining=49650`
- `run end: language=russian stop_reason=user_stop total_translated=24065 last_book_id=...`
- `Translation error: OpenAI/API: RateLimitError: ...`

## API

| المسار | الوصف |
|--------|--------|
| `GET /` | لوحة التحكم |
| `GET /api/status` | الحالة الحالية (جاري التشغيل، التقدم، سبب آخر توقف: `stop_reason`, `stop_message`, `last_error`, `last_book_id`, `last_chapter_file`, `stop_time`) |
| `GET /api/languages` | عدد الأحاديث المترجمة لكل لغة |
| `POST /api/start` | بدء الترجمة (body: `{"language": "turkish"}`) |
| `POST /api/stop` | إيقاف الترجمة |
| `GET /api/export/<language>` | تحميل ترجمات لغة واحدة كملف JSON (مثلاً `/api/export/russian` → `hadith_translations_ru.json`) |
| `POST /api/reset/<language>` | حذف تقدم وترجمات لغة من DB للبدء من الصفر (مثلاً بعد إصلاح ترجمات إنجليزية خاطئة) |

## التكلفة على Railway

- الخطة المدفوعة تكفي لتشغيل التطبيق 24/7.
- استهلاك OpenAI يُحسب حسب عدد الأحاديث واللغات المترجمة.

## الترخيص

نفس ترخيص مشروع hadith.
