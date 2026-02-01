# أوامر سريعة للترجمة

## تفعيل البيئة الافتراضية
```bash
cd /Users/osamaamer/Desktop/code/hadith/hadith/translate
source venv/bin/activate
```

## متابعة التقدم

### الطريقة 1: سكريبت المراقبة (الأسهل)
```bash
cd /Users/osamaamer/Desktop/code/hadith/hadith/translate
source venv/bin/activate
python monitor.py
```

### الطريقة 2: متابعة السجل مباشرة
```bash
cd /Users/osamaamer/Desktop/code/hadith/hadith/translate
tail -f translation_run.log
```

### الطريقة 3: آخر 30 سطر
```bash
cd /Users/osamaamer/Desktop/code/hadith/hadith/translate
tail -30 translation_run.log
```

## إعادة تشغيل الترجمة

### استخدام السكريبت
```bash
cd /Users/osamaamer/Desktop/code/hadith/hadith/translate
./restart_translation.sh
```

### يدوياً
```bash
cd /Users/osamaamer/Desktop/code/hadith/hadith/translate
pkill -f "python.*run_translation"
source venv/bin/activate
python run_translation.py --test --languages turkish --no-gpt > translation_run.log 2>&1 &
tail -f translation_run.log
```

## التحقق من Checkpoints
```bash
cd /Users/osamaamer/Desktop/code/hadith/hadith/translate
cat checkpoints/turkish_checkpoint.json
```

## التحقق من ملفات الإخراج
```bash
cd /Users/osamaamer/Desktop/code/hadith/hadith/translate
ls -lh output/turkish/
```

## ملاحظات مهمة

1. **استخدم `python` بعد تفعيل venv**، أو `python3` مباشرة
2. **اسم الملف:** `translation_run.log` (وليس `translation_run.lo`)
3. **التحذيرات:** تحذيرات semaphore عادية ولا تؤثر على العملية
4. **الوقت:** الترجمة قد تستغرق وقتاً، خاصة في البداية
