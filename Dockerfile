# بناء تطبيق hadith-translator-web من المجلد الفرعي
# استخدم هذا الملف عند النشر من جذر المستودع (بدون Root Directory)

FROM python:3.11-slim

WORKDIR /app

# نسخ تطبيق الويب فقط
COPY hadith-translator-web/ .

RUN pip install --no-cache-dir -r requirements.txt

ENV PORT=5000
EXPOSE 5000

CMD gunicorn -w 1 -b 0.0.0.0:${PORT} --timeout 300 app:app
