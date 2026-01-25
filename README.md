# Hadith Repository

مستودع منظم للأحاديث النبوية الشريفة بصيغة JSON، مصمم للتطبيقات مع دعم التحميل عند الطلب.

## الإحصائيات

| الفئة | عدد الكتب | عدد الأحاديث |
|-------|-----------|--------------|
| الكتب التسعة | 9 | 40,943 |
| الأربعينيات | 3 | 122 |
| كتب أخرى | 5 | 9,819 |
| **الإجمالي** | **17** | **50,884** |

---

## هيكل المشروع

```
hadith/
├── index.json                    # الفهرس الرئيسي
├── books/
│   ├── the_9_books/
│   │   ├── bukhari/
│   │   │   ├── metadata.json
│   │   │   └── chapters/
│   ├── forties/
│   └── other_books/
└── archives/                     # ملفات ZIP
```

---

## بناء الروابط

```javascript
// رابط metadata
const metadataUrl = index.baseUrl + "/" + book.metadataUrl;

// رابط التحميل (ZIP)
const downloadUrl = index.archivesBaseUrl + "/" + book.downloadUrl;

// رابط فصل
const chapterUrl = index.baseUrl + "/" + book.chaptersBaseUrl + "/1.json";
```

---

## إضافة كتاب جديد

1. إنشاء مجلد: `mkdir -p hadith/books/other_books/new_book/chapters`
2. إنشاء `metadata.json` مع قائمة الفصول
3. إضافة ملفات الفصول
4. إنشاء ZIP: `zip -r hadith/archives/new_book.zip new_book/`
5. حساب SHA256: `shasum -a 256 hadith/archives/new_book.zip`
6. **تحديث index.json:**
   - تحديث `version` (مثال: 2.0.1 → 2.0.2)
   - تحديث `lastUpdated`
   - تحديث `totalBooks` و `totalHadiths`

---

## قواعد تحديث version

| نوع التغيير | التحديث |
|-------------|---------|
| إضافة كتاب | 2.0.1 → 2.0.2 |
| تصحيح أخطاء | 2.0.2 → 2.0.3 |
| تغيير البنية | 2.0.3 → 2.1.0 |
| تغيير جذري | 2.1.0 → 3.0.0 |

---

## التحقق من التحديثات

```dart
Future<bool> hasUpdate() async {
  final remote = await fetchIndex();
  final local = await getLocalVersion();
  return remote['version'] != local;
}
```

---

## الترخيص

البيانات متاحة للاستخدام في المشاريع الإسلامية.
