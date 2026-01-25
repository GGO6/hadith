#!/usr/bin/env python3
"""
سكريبت لنقل الملفات من الهيكل القديم إلى الجديد
وإنشاء ملفات metadata.json و ZIP
"""

import os
import json
import shutil
import hashlib
import zipfile
from pathlib import Path

BASE_DIR = Path("/Users/osamaamer/Desktop/code/hadith/hadith")
OLD_CHAPTERS_DIR = BASE_DIR / "by_chapter"
OLD_BOOKS_DIR = BASE_DIR / "by_book"
NEW_BOOKS_DIR = BASE_DIR / "books"
ARCHIVES_DIR = BASE_DIR / "archives"

# تعريف الكتب وتصنيفاتها
BOOKS_CONFIG = {
    "the_9_books": {
        "bukhari": {"numericId": 1, "arabic_title": "صحيح البخاري", "arabic_author": "الإمام محمد بن إسماعيل البخاري", "english_title": "Sahih al-Bukhari", "english_author": "Imam Muhammad ibn Ismail al-Bukhari"},
        "muslim": {"numericId": 2, "arabic_title": "صحيح مسلم", "arabic_author": "الإمام مسلم بن الحجاج النيسابوري", "english_title": "Sahih Muslim", "english_author": "Imam Muslim ibn al-Hajjaj al-Naysaburi"},
        "abudawud": {"numericId": 3, "arabic_title": "سنن أبي داود", "arabic_author": "الإمام أبو داود سليمان بن الأشعث السجستاني", "english_title": "Sunan Abu Dawud", "english_author": "Imam Abu Dawud Sulayman ibn al-Ash'ath al-Sijistani"},
        "tirmidhi": {"numericId": 4, "arabic_title": "جامع الترمذي", "arabic_author": "الإمام محمد بن عيسى الترمذي", "english_title": "Jami' at-Tirmidhi", "english_author": "Imam Muhammad ibn Isa al-Tirmidhi"},
        "nasai": {"numericId": 5, "arabic_title": "سنن النسائي", "arabic_author": "الإمام أحمد بن شعيب النسائي", "english_title": "Sunan an-Nasa'i", "english_author": "Imam Ahmad ibn Shu'ayb al-Nasa'i"},
        "ibnmajah": {"numericId": 6, "arabic_title": "سنن ابن ماجه", "arabic_author": "الإمام محمد بن يزيد ابن ماجه القزويني", "english_title": "Sunan Ibn Majah", "english_author": "Imam Muhammad ibn Yazid Ibn Majah al-Qazwini"},
        "malik": {"numericId": 7, "arabic_title": "موطأ الإمام مالك", "arabic_author": "الإمام مالك بن أنس", "english_title": "Muwatta Malik", "english_author": "Imam Malik ibn Anas"},
        "ahmed": {"numericId": 8, "arabic_title": "مسند الإمام أحمد", "arabic_author": "الإمام أحمد بن حنبل", "english_title": "Musnad Ahmad", "english_author": "Imam Ahmad ibn Hanbal"},
        "darimi": {"numericId": 9, "arabic_title": "سنن الدارمي", "arabic_author": "الإمام عبد الله بن عبد الرحمن الدارمي", "english_title": "Sunan al-Darimi", "english_author": "Imam Abdullah ibn Abd al-Rahman al-Darimi"},
    },
    "forties": {
        "nawawi40": {"numericId": 10, "arabic_title": "الأربعون النووية", "arabic_author": "الإمام يحيى بن شرف النووي", "english_title": "The Forty Hadith of Imam Nawawi", "english_author": "Imam Yahya ibn Sharaf al-Nawawi"},
        "qudsi40": {"numericId": 11, "arabic_title": "الأحاديث القدسية الأربعون", "arabic_author": "متنوع", "english_title": "Forty Hadith Qudsi", "english_author": "Various"},
    },
    "other_books": {
        "riyad_assalihin": {"numericId": 13, "arabic_title": "رياض الصالحين", "arabic_author": "الإمام يحيى بن شرف النووي", "english_title": "Riyad as-Salihin", "english_author": "Imam Yahya ibn Sharaf al-Nawawi"},
        "bulugh_almaram": {"numericId": 14, "arabic_title": "بلوغ المرام", "arabic_author": "الحافظ ابن حجر العسقلاني", "english_title": "Bulugh al-Maram", "english_author": "Hafiz Ibn Hajar al-Asqalani"},
        "mishkat_almasabih": {"numericId": 15, "arabic_title": "مشكاة المصابيح", "arabic_author": "الإمام محمد بن عبد الله الخطيب التبريزي", "english_title": "Mishkat al-Masabih", "english_author": "Imam Muhammad ibn Abdullah al-Khatib al-Tabrizi"},
        "aladab_almufrad": {"numericId": 16, "arabic_title": "الأدب المفرد", "arabic_author": "الإمام محمد بن إسماعيل البخاري", "english_title": "Al-Adab Al-Mufrad", "english_author": "Imam Muhammad ibn Ismail al-Bukhari"},
        "shamail_muhammadiyah": {"numericId": 17, "arabic_title": "الشمائل المحمدية", "arabic_author": "الإمام محمد بن عيسى الترمذي", "english_title": "Shama'il Muhammadiyah", "english_author": "Imam Muhammad ibn Isa al-Tirmidhi"},
    }
}


def calculate_sha256(file_path):
    """حساب SHA256 لملف"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def get_dir_size(path):
    """حساب حجم مجلد"""
    total = 0
    for entry in os.scandir(path):
        if entry.is_file():
            total += entry.stat().st_size
        elif entry.is_dir():
            total += get_dir_size(entry.path)
    return total


def format_size(size_bytes):
    """تنسيق الحجم"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def create_book_structure(category, book_id, config):
    """إنشاء هيكل الكتاب الجديد"""
    book_dir = NEW_BOOKS_DIR / category / book_id
    chapters_dir = book_dir / "chapters"
    
    # إنشاء المجلدات
    chapters_dir.mkdir(parents=True, exist_ok=True)
    
    # البحث عن المصدر
    old_book_dir = OLD_CHAPTERS_DIR / category / book_id
    
    if not old_book_dir.exists():
        print(f"  ⚠️  لم يُعثر على: {old_book_dir}")
        return None
    
    # جمع معلومات الفصول
    chapters_info = []
    total_hadiths = 0
    
    # نسخ ملفات الفصول
    for chapter_file in sorted(old_book_dir.glob("*.json")):
        filename = chapter_file.name
        
        # قراءة محتوى الفصل
        with open(chapter_file, 'r', encoding='utf-8') as f:
            chapter_data = json.load(f)
        
        # استخراج معلومات الفصل
        hadiths = chapter_data.get('hadiths', [])
        hadith_count = len(hadiths)
        total_hadiths += hadith_count
        
        # استخراج معلومات العنوان
        metadata = chapter_data.get('metadata', {})
        chapter_info_data = chapter_data.get('chapter', {})
        
        arabic_title = ""
        english_title = ""
        chapter_id = 0
        
        if chapter_info_data:
            arabic_title = chapter_info_data.get('arabic', '')
            english_title = chapter_info_data.get('english', '')
            chapter_id = chapter_info_data.get('id', 0)
        elif metadata:
            arabic_info = metadata.get('arabic', {})
            english_info = metadata.get('english', {})
            arabic_title = arabic_info.get('title', '') or arabic_info.get('introduction', '')
            english_title = english_info.get('title', '') or english_info.get('introduction', '')
        
        # تحديد اسم الملف الجديد
        if filename == "all.json":
            new_filename = "all.json"
            dest_path = book_dir / new_filename
        elif filename == "introduction.json":
            new_filename = "introduction.json"
            dest_path = chapters_dir / new_filename
        else:
            new_filename = filename
            dest_path = chapters_dir / new_filename
        
        # نسخ الملف
        shutil.copy2(chapter_file, dest_path)
        
        # إضافة معلومات الفصل
        try:
            if filename == "all.json":
                chapter_id = 0
            elif filename == "introduction.json":
                chapter_id = 0
            else:
                chapter_id = int(filename.replace('.json', '').replace('introduction', '0'))
        except ValueError:
            chapter_id = 0
        
        chapters_info.append({
            "id": chapter_id,
            "arabic": arabic_title,
            "english": english_title,
            "hadithsCount": hadith_count,
            "file": new_filename if filename == "all.json" else f"chapters/{new_filename}"
        })
    
    # ترتيب الفصول حسب الـ id
    chapters_info.sort(key=lambda x: (x['id'] if isinstance(x['id'], int) else 0))
    
    # إنشاء metadata.json
    metadata = {
        "id": book_id,
        "numericId": config["numericId"],
        "arabic": {
            "title": config["arabic_title"],
            "author": config["arabic_author"],
            "introduction": ""
        },
        "english": {
            "title": config["english_title"],
            "author": config["english_author"],
            "introduction": ""
        },
        "hadithsCount": total_hadiths,
        "chapters": chapters_info
    }
    
    metadata_path = book_dir / "metadata.json"
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    print(f"  ✅ {config['arabic_title']}: {len(chapters_info)} فصل، {total_hadiths} حديث")
    
    return {
        "chapters_count": len(chapters_info),
        "hadiths_count": total_hadiths,
        "size_bytes": get_dir_size(book_dir)
    }


def create_zip_archive(category, book_id):
    """إنشاء ملف ZIP للكتاب"""
    book_dir = NEW_BOOKS_DIR / category / book_id
    zip_path = ARCHIVES_DIR / f"{book_id}.zip"
    
    if not book_dir.exists():
        return None
    
    ARCHIVES_DIR.mkdir(parents=True, exist_ok=True)
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in book_dir.rglob('*'):
            if file_path.is_file():
                arcname = file_path.relative_to(book_dir)
                zipf.write(file_path, arcname)
    
    sha256 = calculate_sha256(zip_path)
    size = zip_path.stat().st_size
    
    print(f"  📦 {book_id}.zip: {format_size(size)}")
    
    return {
        "path": str(zip_path),
        "size": size,
        "sha256": sha256
    }


def update_index_json(books_data):
    """تحديث ملف index.json"""
    index_path = BASE_DIR / "index.json"
    
    with open(index_path, 'r', encoding='utf-8') as f:
        index = json.load(f)
    
    # تحديث معلومات كل كتاب
    for book in index['books']:
        book_id = book['id']
        if book_id in books_data:
            data = books_data[book_id]
            if 'info' in data and data['info']:
                book['chaptersCount'] = data['info']['chapters_count']
                book['hadithsCount'] = data['info']['hadiths_count']
                book['sizeBytes'] = data['info']['size_bytes']
                book['sizeFormatted'] = format_size(data['info']['size_bytes'])
            if 'zip' in data and data['zip']:
                book['sha256'] = data['zip']['sha256']
    
    # حفظ التحديثات
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ تم تحديث index.json")


def main():
    print("=" * 60)
    print("🚀 بدء نقل الملفات وإنشاء الهيكل الجديد")
    print("=" * 60)
    
    books_data = {}
    
    # معالجة كل فئة
    for category, books in BOOKS_CONFIG.items():
        print(f"\n📁 {category}:")
        print("-" * 40)
        
        for book_id, config in books.items():
            info = create_book_structure(category, book_id, config)
            books_data[book_id] = {"info": info, "zip": None}
    
    # إنشاء ملفات ZIP
    print("\n" + "=" * 60)
    print("📦 إنشاء ملفات ZIP")
    print("=" * 60)
    
    for category, books in BOOKS_CONFIG.items():
        print(f"\n📁 {category}:")
        for book_id in books.keys():
            zip_info = create_zip_archive(category, book_id)
            if book_id in books_data:
                books_data[book_id]["zip"] = zip_info
    
    # تحديث index.json
    print("\n" + "=" * 60)
    print("📝 تحديث index.json")
    print("=" * 60)
    
    update_index_json(books_data)
    
    print("\n" + "=" * 60)
    print("🎉 تمت العملية بنجاح!")
    print("=" * 60)


if __name__ == "__main__":
    main()
