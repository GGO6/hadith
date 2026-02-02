#!/usr/bin/env python3
"""
Merge Turkish translations from hadith/translations/tr into hadith/books.
For each hadith file: if tr file exists, add turkish: { narrator, text } to each hadith.
Supports both tr file formats: hadith.tr.{narrator,text} or hadith.{narrator,text} (flat).
Then rebuild all ZIP archives and update index.json sha256.
"""
import hashlib
import json
import zipfile
from pathlib import Path

HADITH_DIR = Path(__file__).resolve().parent / "hadith"
BOOKS_DIR = HADITH_DIR / "books"
TR_DIR = HADITH_DIR / "translations" / "tr" / "books"
ARCHIVES_DIR = HADITH_DIR / "archives"
INDEX_PATH = HADITH_DIR / "index.json"


def get_tr_for_hadith(tr_hadith: dict) -> dict:
    """Extract Turkish narrator and text from tr file hadith (supports nested 'tr' or flat)."""
    tr_obj = tr_hadith.get("tr")
    if tr_obj:
        return {
            "narrator": (tr_obj.get("narrator") or "").strip(),
            "text": (tr_obj.get("text") or "").strip(),
        }
    return {
        "narrator": (tr_hadith.get("narrator") or "").strip(),
        "text": (tr_hadith.get("text") or "").strip(),
    }


def merge_turkish_into_file(books_path: Path, tr_path: Path) -> tuple[int, int]:
    """
    Merge Turkish from tr_path into books_path. Add turkish to each hadith where tr has content.
    Returns (hadiths_updated, hadiths_with_text).
    """
    with open(books_path, "r", encoding="utf-8") as f:
        books_data = json.load(f)
    with open(tr_path, "r", encoding="utf-8") as f:
        tr_data = json.load(f)

    tr_by_id = {}
    for h in tr_data.get("hadiths", []):
        hid = h.get("id")
        if hid is not None:
            tr_by_id[hid] = get_tr_for_hadith(h)

    updated = 0
    with_text = 0
    for hadith in books_data.get("hadiths", []):
        hid = hadith.get("id")
        if hid is None:
            continue
        if hid in tr_by_id:
            hadith["turkish"] = tr_by_id[hid]
            updated += 1
            if hadith["turkish"]["text"]:
                with_text += 1
        else:
            hadith["turkish"] = {"narrator": "", "text": ""}
            updated += 1

    with open(books_path, "w", encoding="utf-8") as f:
        json.dump(books_data, f, ensure_ascii=False, indent=2)
    return updated, with_text


def main():
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        index = json.load(f)

    books_list = index["books"]
    total_files_merged = 0
    total_hadiths_with_tr = 0
    books_modified = set()

    for book in books_list:
        book_id = book["id"]
        category = book["category"]
        has_chapters = book.get("hasChapters", True)
        book_base = BOOKS_DIR / category / book_id
        tr_base = TR_DIR / category / book_id
        tr_base_for_file = {}

        if has_chapters:
            metadata_path = book_base / "metadata.json"
            if not metadata_path.exists():
                print(f"  Skip {book_id}: no metadata.json")
                continue
            with open(metadata_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            chapter_files = [ch.get("file") for ch in meta.get("chapters", []) if ch.get("file")]
        else:
            full_url = book.get("fullBookUrl", "")
            if not full_url:
                print(f"  Skip {book_id}: no fullBookUrl")
                continue
            # fullBookUrl is e.g. forties/nawawi40/all.json -> file is all.json
            chapter_files = [Path(full_url).name]
            # Fallback: if tr has chapters/0.json only (e.g. qudsi40), merge that into all.json
            tr_ch0 = tr_base / "chapters" / "0.json"
            if not (tr_base / chapter_files[0]).exists() and tr_ch0.exists():
                chapter_files = ["all.json"]  # merge from tr_base/chapters/0.json into books .../all.json
                tr_base_for_file = {"all.json": tr_base / "chapters" / "0.json"}

        for ch_file in chapter_files:
            books_path = book_base / ch_file
            tr_path = tr_base_for_file.get(ch_file) or (tr_base / ch_file)
            if not books_path.exists():
                continue
            if not tr_path.exists():
                continue
            try:
                n_updated, n_with_text = merge_turkish_into_file(books_path, tr_path)
                total_files_merged += 1
                total_hadiths_with_tr += n_with_text
                books_modified.add(book_id)
                print(f"  {book_id} {ch_file}: {n_updated} hadiths, {n_with_text} with Turkish text")
            except Exception as e:
                print(f"  Error {book_id} {ch_file}: {e}")

    print(f"\nMerged: {total_files_merged} files, {total_hadiths_with_tr} hadiths with Turkish. Books touched: {len(books_modified)}")

    # Rebuild ALL ZIPs and update index.json (all books, not only modified - sha256 must match)
    print("\nRebuilding ZIP archives and updating index.json...")
    def calculate_sha256(file_path: Path) -> str:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for block in iter(lambda: f.read(4096), b""):
                h.update(block)
        return h.hexdigest()

    for book in books_list:
        book_id = book["id"]
        category = book["category"]
        book_dir = BOOKS_DIR / category / book_id
        zip_path = ARCHIVES_DIR / f"{book_id}.zip"
        if not book_dir.exists():
            continue
        ARCHIVES_DIR.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in book_dir.rglob("*"):
                if f.is_file():
                    zf.write(f, f.relative_to(book_dir))
        sha = calculate_sha256(zip_path)
        book["sha256"] = sha
        print(f"  {book_id}.zip sha256={sha[:16]}...")

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print("\nDone. index.json updated.")


if __name__ == "__main__":
    main()
