#!/usr/bin/env python3
"""
Merge translation parts into a single all.json file
دمج أجزاء الترجمة في ملف واحد
"""
import json
import os
from pathlib import Path

# Language mapping
LANG_MAP = {
    "tr": "turkish",
    "id": "indonesian", 
    "fr": "french",
    "ur": "urdu",
    "bn": "bengali",
    "de": "german",
    "es": "spanish",
    "ru": "russian"
}

def merge_nawawi_translations(lang_code: str):
    """Merge all_part*.json files into all.json"""
    base_dir = Path(f"hadith/translations/{lang_code}/books/forties/nawawi40")
    full_name = LANG_MAP.get(lang_code, lang_code)
    
    # Read original file structure
    original = Path("hadith/books/forties/nawawi40/all.json")
    with open(original, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Collect all translated hadiths
    translated_hadiths = {}
    metadata_trans = None
    
    for part_file in sorted(base_dir.glob("all_part*.json")):
        with open(part_file, 'r', encoding='utf-8') as f:
            part_data = json.load(f)
            
            # Get metadata (check both lang_code and full_name)
            if "metadata" in part_data:
                for key in [lang_code, full_name]:
                    if key in part_data["metadata"]:
                        metadata_trans = part_data["metadata"][key]
                        break
            
            # Get hadiths
            for hadith in part_data.get("hadiths", []):
                hadith_id = hadith.get("id")
                if isinstance(hadith_id, int):
                    # Check for translation in both lang_code and full_name
                    trans = hadith.get(full_name, hadith.get(lang_code))
                    if trans and isinstance(trans, dict):
                        translated_hadiths[hadith_id] = trans
    
    # Add metadata translation
    if metadata_trans:
        data["metadata"][lang_code] = metadata_trans
    
    # Add translations to original hadiths
    for hadith in data["hadiths"]:
        hadith_id = hadith.get("id")
        if hadith_id in translated_hadiths:
            hadith[lang_code] = translated_hadiths[hadith_id]
    
    # Write merged file
    output_file = base_dir / "all.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"Merged {len(translated_hadiths)} hadiths for {lang_code}")
    print(f"Output: {output_file}")
    
    # Clean up part files
    for part_file in base_dir.glob("all_part*.json"):
        os.remove(part_file)
        print(f"Removed: {part_file}")

if __name__ == "__main__":
    import sys
    lang = sys.argv[1] if len(sys.argv) > 1 else "tr"
    merge_nawawi_translations(lang)
