# Hadith Repository

مستودع منظم للأحاديث النبوية الشريفة بصيغة JSON، مصمم للتطبيقات مع دعم التحميل عند الطلب.

## الإحصائيات

| الفئة | عدد الكتب | الحجم التقريبي |
|-------|-----------|----------------|
| الكتب التسعة | 9 | ~59 MB |
| الأربعينيات | 3 | ~180 KB |
| كتب أخرى | 5 | ~11 MB |
| الإجمالي | 17 | ~70 MB |

## هيكل المشروع

    hadith/
    ├── index.json                    # الفهرس الرئيسي
    ├── books/
    │   ├── the_9_books/              # الكتب التسعة
    │   │   ├── bukhari/
    │   │   │   ├── metadata.json     # بيانات الكتاب
    │   │   │   └── chapters/
    │   │   │       ├── 1.json
    │   │   │       └── ...
    │   ├── forties/                  # الأربعينيات
    │   └── other_books/              # كتب أخرى
    └── archives/                     # ملفات مضغوطة

## كيفية الاستخدام

### 1. قراءة الفهرس الرئيسي

    final response = await http.get(Uri.parse(
      'https://raw.githubusercontent.com/GGO6/hadith/main/hadith/index.json'
    ));
    final index = json.decode(response.body);

### 2. تحميل كتاب عند الطلب

    final metadataUrl = index['baseUrl'] + '/' + book['metadataUrl'];
    final metadata = await fetchJson(metadataUrl);

## إضافة كتاب جديد

1. إنشاء مجلد الكتاب: `mkdir -p hadith/books/other_books/new_book/chapters`
2. إنشاء metadata.json
3. إضافة ملفات الفصول
4. تحديث index.json
5. (اختياري) إنشاء ملف مضغوط

## الترخيص

البيانات متاحة للاستخدام العام في المشاريع الإسلامية.
