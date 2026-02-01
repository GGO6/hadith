# دليل البدء السريع - الترجمة باستخدام GPT API

## الخطوة 1: الحصول على API Key

1. اذهب إلى: https://platform.openai.com/api-keys
2. سجل دخول أو أنشئ حساب
3. أنشئ API key جديد
4. انسخ المفتاح (يبدأ بـ `sk-`)

## الخطوة 2: تعيين API Key

### الطريقة الأولى: متغير البيئة (موصى به)
```bash
export OPENAI_API_KEY="sk-your-api-key-here"
```

### الطريقة الثانية: في السكريبت
```bash
./start_api_translation.sh sk-your-api-key-here
```

## الخطوة 3: تشغيل الترجمة

### اختبار سريع (100 حديث):
```bash
cd /Users/osamaamer/Desktop/code/hadith/hadith/translate
source venv/bin/activate
export OPENAI_API_KEY="sk-your-api-key-here"
python run_api_translation.py --test --languages turkish
```

### ترجمة كاملة:
```bash
python run_api_translation.py --languages turkish
```

## الخطوة 4: متابعة التقدم

```bash
tail -f translation_api_run.log
```

أو:

```bash
python monitor.py
```

---

## الوقت المتوقع

- **100 حديث:** ~2-3 دقائق
- **كتاب البخاري:** ~2-3 ساعات  
- **جميع الكتب:** ~15-20 ساعة

---

## التكلفة المتوقعة

- **100 حديث:** ~$0.25
- **كتاب البخاري:** ~$20-25
- **جميع الكتب:** ~$125-150

---

## نصائح

1. ✅ ابدأ بالاختبار (`--test`) أولاً
2. ✅ راقب التكلفة في OpenAI dashboard
3. ✅ النظام يحفظ التقدم تلقائياً
4. ✅ يمكنك إيقاف واستئناف في أي وقت

---

## أوامر سريعة

```bash
# تفعيل البيئة
cd /Users/osamaamer/Desktop/code/hadith/hadith/translate
source venv/bin/activate

# تعيين API key
export OPENAI_API_KEY="sk-your-key"

# اختبار
python run_api_translation.py --test --languages turkish

# ترجمة كاملة
python run_api_translation.py --languages turkish
```
