#!/usr/bin/env python3
"""
دمج الترجمات التركية في هيكل المشروع
Integrate Turkish translations into project structure
"""
import json
import os
from pathlib import Path
from collections import defaultdict

# Book categorization
THE_9_BOOKS = ['bukhari', 'muslim', 'abudawud', 'tirmidhi', 'nasai', 'ibnmajah', 'malik', 'ahmed', 'darimi']
FORTIES = ['nawawi40', 'qudsi40']
OTHER_BOOKS = ['riyad_assalihin', 'bulugh_almaram', 'mishkat_almasabih', 'aladab_almufrad', 'shamail_muhammadiyah']

# Book metadata
BOOK_METADATA = {
    'bukhari': {
        'arabic': {'title': 'صحيح البخاري', 'author': 'الإمام محمد بن إسماعيل البخاري'},
        'english': {'title': 'Sahih al-Bukhari', 'author': 'Imam Muhammad ibn Ismail al-Bukhari'}
    },
    'muslim': {
        'arabic': {'title': 'صحيح مسلم', 'author': 'الإمام مسلم بن الحجاج'},
        'english': {'title': 'Sahih Muslim', 'author': 'Imam Muslim ibn al-Hajjaj'}
    },
    'abudawud': {
        'arabic': {'title': 'سنن أبي داود', 'author': 'الإمام أبو داود السجستاني'},
        'english': {'title': 'Sunan Abu Dawud', 'author': 'Imam Abu Dawud al-Sijistani'}
    },
    'tirmidhi': {
        'arabic': {'title': 'سنن الترمذي', 'author': 'الإمام محمد بن عيسى الترمذي'},
        'english': {'title': 'Jami at-Tirmidhi', 'author': 'Imam Muhammad ibn Isa at-Tirmidhi'}
    },
    'nasai': {
        'arabic': {'title': 'سنن النسائي', 'author': 'الإمام أحمد بن شعيب النسائي'},
        'english': {'title': 'Sunan an-Nasai', 'author': 'Imam Ahmad ibn Shuayb an-Nasai'}
    },
    'ibnmajah': {
        'arabic': {'title': 'سنن ابن ماجه', 'author': 'الإمام محمد بن يزيد ابن ماجه'},
        'english': {'title': 'Sunan Ibn Majah', 'author': 'Imam Muhammad ibn Yazid Ibn Majah'}
    },
    'malik': {
        'arabic': {'title': 'موطأ مالك', 'author': 'الإمام مالك بن أنس'},
        'english': {'title': "Muwatta Malik", 'author': 'Imam Malik ibn Anas'}
    },
    'ahmed': {
        'arabic': {'title': 'مسند أحمد', 'author': 'الإمام أحمد بن حنبل'},
        'english': {'title': 'Musnad Ahmad', 'author': 'Imam Ahmad ibn Hanbal'}
    },
    'darimi': {
        'arabic': {'title': 'سنن الدارمي', 'author': 'الإمام عبد الله بن عبد الرحمن الدارمي'},
        'english': {'title': 'Sunan ad-Darimi', 'author': 'Imam Abdullah ibn Abd ar-Rahman ad-Darimi'}
    },
    'nawawi40': {
        'arabic': {'title': 'الأربعون النووية', 'author': 'الإمام النووي'},
        'english': {'title': "An-Nawawi's Forty Hadith", 'author': 'Imam an-Nawawi'}
    },
    'qudsi40': {
        'arabic': {'title': 'الأحاديث القدسية', 'author': 'مجموعة علماء'},
        'english': {'title': 'Forty Hadith Qudsi', 'author': 'Various Scholars'}
    },
    'riyad_assalihin': {
        'arabic': {'title': 'رياض الصالحين', 'author': 'الإمام النووي'},
        'english': {'title': 'Riyad as-Salihin', 'author': 'Imam an-Nawawi'}
    },
    'bulugh_almaram': {
        'arabic': {'title': 'بلوغ المرام', 'author': 'ابن حجر العسقلاني'},
        'english': {'title': 'Bulugh al-Maram', 'author': 'Ibn Hajar al-Asqalani'}
    },
    'mishkat_almasabih': {
        'arabic': {'title': 'مشكاة المصابيح', 'author': 'الخطيب التبريزي'},
        'english': {'title': 'Mishkat al-Masabih', 'author': 'Al-Khatib al-Tabrizi'}
    },
    'aladab_almufrad': {
        'arabic': {'title': 'الأدب المفرد', 'author': 'الإمام البخاري'},
        'english': {'title': 'Al-Adab Al-Mufrad', 'author': 'Imam al-Bukhari'}
    },
    'shamail_muhammadiyah': {
        'arabic': {'title': 'الشمائل المحمدية', 'author': 'الإمام الترمذي'},
        'english': {'title': 'Shamail Muhammadiyah', 'author': 'Imam at-Tirmidhi'}
    }
}

def get_book_category(book_id):
    if book_id in THE_9_BOOKS:
        return 'the_9_books'
    elif book_id in FORTIES:
        return 'forties'
    else:
        return 'other_books'

def load_translations():
    """Load our translated hadiths"""
    with open('output/turkish/all_translations.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def organize_by_chapter(translations):
    """Organize translations by book and chapter"""
    organized = {}
    
    for book_id, hadiths in translations.items():
        if not isinstance(hadiths, dict):
            continue
            
        organized[book_id] = defaultdict(list)
        
        for key, hadith_data in hadiths.items():
            # Key format: "chapterId:hadithId"
            parts = key.split(':')
            if len(parts) == 2:
                try:
                    chapter_id = int(parts[0]) if parts[0] and parts[0] != 'None' else 0
                    hadith_id = int(parts[1]) if parts[1] and parts[1] != 'None' else 0
                except ValueError:
                    chapter_id = 0
                    hadith_id = 0
            else:
                chapter_id = 0
                try:
                    hadith_id = int(key) if key.isdigit() else 0
                except ValueError:
                    hadith_id = 0
            
            organized[book_id][chapter_id].append({
                'id': hadith_id,
                'narrator': hadith_data.get('narrator', ''),
                'text': hadith_data.get('text', '')
            })
        
        # Sort hadiths by ID within each chapter
        for chapter_id in organized[book_id]:
            organized[book_id][chapter_id].sort(key=lambda x: x['id'])
    
    return organized

def create_chapter_file(book_id, chapter_id, hadiths):
    """Create a chapter JSON file"""
    metadata = BOOK_METADATA.get(book_id, {
        'arabic': {'title': book_id, 'author': ''},
        'english': {'title': book_id, 'author': ''}
    })
    
    return {
        'language': 'tr',
        'metadata': {
            'length': len(hadiths),
            'arabic': metadata['arabic'],
            'english': metadata['english']
        },
        'hadiths': hadiths
    }

def integrate_translations():
    """Main function to integrate translations"""
    print("🔄 جاري تحميل الترجمات...")
    translations = load_translations()
    
    print("📊 جاري تنظيم الترجمات بحسب الفصول...")
    organized = organize_by_chapter(translations)
    
    base_path = Path('../translations/tr/books')
    
    total_files = 0
    total_hadiths = 0
    
    for book_id, chapters in organized.items():
        category = get_book_category(book_id)
        book_path = base_path / category / book_id / 'chapters'
        book_path.mkdir(parents=True, exist_ok=True)
        
        print(f"\n📖 {book_id}:")
        
        for chapter_id, hadiths in chapters.items():
            chapter_file = book_path / f"{chapter_id}.json"
            chapter_data = create_chapter_file(book_id, chapter_id, hadiths)
            
            with open(chapter_file, 'w', encoding='utf-8') as f:
                json.dump(chapter_data, f, ensure_ascii=False, indent=2)
            
            total_files += 1
            total_hadiths += len(hadiths)
        
        print(f"   ✅ {len(chapters)} فصل، {sum(len(h) for h in chapters.values())} حديث")
    
    print(f"\n{'='*50}")
    print(f"✅ تم الدمج بنجاح!")
    print(f"📁 عدد الملفات: {total_files}")
    print(f"📿 عدد الأحاديث: {total_hadiths:,}")
    print(f"{'='*50}")

if __name__ == "__main__":
    integrate_translations()
