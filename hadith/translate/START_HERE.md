# 🚀 ابدأ هنا - الترجمة باستخدام GPT API

## الخطوة 1: تعيين API Key

### ✅ الطريقة الأسهل (موصى به):

افتح Terminal واكتب:

```bash
export OPENAI_API_KEY="sk-your-api-key-here"
```

**استبدل `sk-your-api-key-here` بمفتاحك الحقيقي**

---

## الخطوة 2: تشغيل الترجمة

### اختبار سريع (100 حديث فقط - ~$0.25):

```bash
cd /Users/osamaamer/Desktop/code/hadith/hadith/translate
source venv/bin/activate
python run_api_translation.py --test --languages turkish
```

### ترجمة كاملة:

```bash
python run_api_translation.py --languages turkish
```

---

## 📋 مثال كامل:

```bash
# 1. اذهب للمجلد
cd /Users/osamaamer/Desktop/code/hadith/hadith/translate

# 2. فعّل البيئة الافتراضية
source venv/bin/activate

# 3. ضع API key (استبدل بمفتاحك)
export OPENAI_API_KEY="sk-proj-xxxxxxxxxxxxxxxxxxxxx"

# 4. شغّل الاختبار
python run_api_translation.py --test --languages turkish
```

---

## ⚡ أوامر سريعة:

### إذا كان API key في متغير البيئة:
```bash
python run_api_translation.py --test --languages turkish
```

### إذا أردت تمرير API key مباشرة:
```bash
python run_api_translation.py --api-key "sk-your-key" --test --languages turkish
```

---

## 📊 متابعة التقدم:

```bash
# في Terminal آخر
tail -f translation_api_run.log
```

أو:

```bash
python monitor.py
```

---

## ⏱️ الوقت المتوقع:

- **100 حديث:** ~2-3 دقائق
- **كتاب البخاري:** ~2-3 ساعات
- **جميع الكتب:** ~15-20 ساعة

---

## 💰 التكلفة:

- **100 حديث:** ~$0.25
- **كتاب البخاري:** ~$20-25
- **جميع الكتب:** ~$125-150

---

## ✅ نصائح:

1. ابدأ بالاختبار (`--test`) أولاً
2. راقب التكلفة في: https://platform.openai.com/usage
3. النظام يحفظ التقدم تلقائياً
4. يمكنك إيقاف واستئناف في أي وقت

---

## 🆘 مساعدة:

إذا واجهت مشكلة، تأكد من:
- ✅ API key صحيح ويبدأ بـ `sk-`
- ✅ البيئة الافتراضية مفعلة (`source venv/bin/activate`)
- ✅ لديك رصيد في حساب OpenAI
