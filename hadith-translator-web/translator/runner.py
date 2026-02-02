"""
Translation runner - runs translation in background with stop support and progress callback.
"""
import os
import json
import glob
from pathlib import Path
from typing import Dict, List, Callable, Optional
import threading

# Project root
_root = Path(__file__).resolve().parent.parent
if str(_root) not in __import__('sys').path:
    __import__('sys').path.insert(0, str(_root))

import config
from .api_translator import APITranslator


class TranslationRunner:
    """Runs hadith translation; supports stop event and progress callback."""

    def __init__(self, api_key: str = None, stop_event: Optional[threading.Event] = None,
                 progress_callback: Optional[Callable[[dict], None]] = None, app=None):
        self.translator = APITranslator(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.checkpoints_dir = config.CHECKPOINTS_DIR
        self.output_dir = config.OUTPUT_DIR
        self.books_dir = config.BOOKS_DIR
        self.stop_event = stop_event or threading.Event()
        self.progress_callback = progress_callback
        self.app = app  # Flask app for DB; if set, use DB instead of JSON
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _emit_progress(self, data: dict):
        if self.progress_callback:
            try:
                self.progress_callback(data)
            except Exception:
                pass

    def load_checkpoint(self, language: str) -> Dict:
        if self.app:
            with self.app.app_context():
                from app import db, TranslationProgress, HadithTranslation
                prog = TranslationProgress.query.filter_by(language=language).first()
                processed = set()
                for row in HadithTranslation.query.filter_by(language_code=language).with_entities(
                    HadithTranslation.book_id, HadithTranslation.chapter_id, HadithTranslation.hadith_id
                ).all():
                    processed.add(f"{row[0]}:{row[1]}:{row[2]}")
                stats = {"total_translated": prog.total_translated, "api_calls": prog.api_calls or 0, "tokens_used": prog.tokens_used or 0} if prog else {"total_translated": 0, "api_calls": 0, "tokens_used": 0}
                return {
                    "language": language,
                    "processed_books": [],
                    "processed_hadiths": list(processed),
                    "stats": stats
                }
        p = self.checkpoints_dir / f"{language}_api_checkpoint.json"
        if p.exists():
            with open(p, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "language": language,
            "processed_books": [],
            "processed_hadiths": [],
            "stats": {"total_translated": 0, "api_calls": 0, "tokens_used": 0}
        }

    def save_checkpoint(self, checkpoint: Dict, new_translations: List[Dict] = None):
        """Save checkpoint; if app/DB, also persist new_translations (list of dicts with book_id, chapter_id, hadith_id, language_code, narrator, text)."""
        if self.app:
            with self.app.app_context():
                from app import db, TranslationProgress, HadithTranslation
                lang = checkpoint["language"]
                if new_translations:
                    for t in new_translations:
                        if HadithTranslation.query.filter_by(
                            book_id=t["book_id"],
                            chapter_id=t["chapter_id"],
                            hadith_id=t["hadith_id"],
                            language_code=lang,
                        ).first():
                            continue
                        rec = HadithTranslation(
                            book_id=t["book_id"],
                            chapter_id=t["chapter_id"],
                            hadith_id=t["hadith_id"],
                            language_code=lang,
                            narrator=t.get("narrator"),
                            text=t.get("text", ""),
                            quality_confidence=t.get("quality_confidence", "HIGH"),
                            needs_review=t.get("needs_review", False),
                        )
                        db.session.add(rec)
                prog = TranslationProgress.query.filter_by(language=lang).first()
                if not prog:
                    prog = TranslationProgress(language=lang)
                    db.session.add(prog)
                prog.total_translated = checkpoint["stats"]["total_translated"]
                prog.api_calls = checkpoint["stats"].get("api_calls", 0)
                prog.tokens_used = checkpoint["stats"].get("tokens_used", 0)
                db.session.commit()
            return
        p = self.checkpoints_dir / f"{checkpoint['language']}_api_checkpoint.json"
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(checkpoint, f, ensure_ascii=False, indent=2)

    def load_all_books(self) -> List[Dict]:
        books = []
        for metadata_file in glob.glob(str(self.books_dir / "**/metadata.json"), recursive=True):
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                metadata['_path'] = Path(metadata_file).parent
                books.append(metadata)
        return sorted(books, key=lambda x: x.get('numericId', 0))

    def load_chapter_file(self, book_path: Path, chapter_file: str) -> Optional[Dict]:
        p = book_path / chapter_file
        if not p.exists():
            return None
        with open(p, 'r', encoding='utf-8') as f:
            return json.load(f)

    def extract_hadith_text(self, hadith: Dict) -> str:
        eng = hadith.get('english', {})
        narrator = eng.get('narrator', '')
        text = eng.get('text', '')
        if narrator and text:
            return f"{narrator} {text}".strip()
        return text or narrator or ""

    def count_total_hadiths(self) -> int:
        try:
            index_file = self.books_dir.parent / "index.json"
            if index_file.exists():
                with open(index_file, 'r', encoding='utf-8') as f:
                    return json.load(f).get('totalHadiths', 50884)
        except Exception:
            pass
        return 50884

    def run(self, language: str) -> dict:
        """Run translation for one language. Returns final status dict."""
        if language not in config.LANGUAGES:
            return {"error": f"Unknown language: {language}"}
        if not self.books_dir.exists():
            return {"error": f"Books directory not found: {self.books_dir}"}

        self.stop_event.clear()
        total_hadiths = self.count_total_hadiths()
        checkpoint = self.load_checkpoint(language)
        processed_set = set(checkpoint.get("processed_hadiths", []))
        all_books = self.load_all_books()
        lang_info = config.LANGUAGES[language]
        output_lang_dir = self.output_dir / language
        output_lang_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_lang_dir / "all_translations.json"
        all_translations = {}
        if not self.app and output_file.exists():
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    all_translations.update(json.load(f))
            except Exception:
                pass

        for book in all_books:
            if self.stop_event.is_set():
                break
            book_id = book['id']
            book_path = book['_path']
            chapters = book.get('chapters', [])
            translated_hadiths = {}

            if not chapters:
                all_file = book_path / "all.json"
                if all_file.exists():
                    data = self.load_chapter_file(book_path, "all.json")
                    if data:
                        hadiths = data.get('hadiths', [])
                        hadiths_to_translate = [
                            h for h in hadiths
                            if f"{book_id}:{h.get('chapterId', 0)}:{h.get('id')}" not in processed_set
                        ]
                        if hadiths_to_translate:
                            texts = [self.extract_hadith_text(h) for h in hadiths_to_translate]
                            meta = [{"id": h.get('id'), "chapterId": h.get('chapterId', 0), "narrator": h.get('english', {}).get('narrator', '')} for h in hadiths_to_translate]
                            try:
                                translated_texts = self.translator.translate_batch(texts, language)
                            except Exception:
                                translated_texts = texts
                            for i, (m, txt) in enumerate(zip(meta, translated_texts)):
                                if i < len(texts) and (txt or "").strip() == (texts[i] or "").strip():
                                    continue
                                key = f"{m['chapterId']}:{m['id']}"
                                composite = f"{book_id}:{m['chapterId']}:{m['id']}"
                                translated_hadiths[key] = {"narrator": m['narrator'], "text": txt, "hadith_id": m['id'], "chapter_id": m['chapterId'], "quality": {"confidence": "HIGH", "needs_review": False}}
                                if composite not in processed_set:
                                    processed_set.add(composite)
                                    checkpoint['stats']['total_translated'] += 1
                                    checkpoint['processed_hadiths'].append(composite)
                            checkpoint['stats']['api_calls'] += (len(texts) + 14) // 15
                if translated_hadiths:
                    new_translations = [
                        {"book_id": book_id, "chapter_id": int(m["chapterId"]), "hadith_id": int(m["id"]),
                         "narrator": m.get("narrator"), "text": translated_hadiths[f"{m['chapterId']}:{m['id']}"]["text"],
                         "quality_confidence": "HIGH", "needs_review": False}
                        for m in meta if f"{m['chapterId']}:{m['id']}" in translated_hadiths
                    ] if self.app else None
                    if not self.app:
                        if book_id not in all_translations:
                            all_translations[book_id] = {}
                        all_translations[book_id].update(translated_hadiths)
                    self.save_checkpoint(checkpoint, new_translations=new_translations)
                    if not self.app:
                        with open(output_file, 'w', encoding='utf-8') as f:
                            json.dump(all_translations, f, ensure_ascii=False, indent=2)
                    self._emit_progress({
                        "language": language,
                        "book_id": book_id,
                        "total_translated": checkpoint['stats']['total_translated'],
                        "total_hadiths": total_hadiths,
                        "remaining": total_hadiths - checkpoint['stats']['total_translated']
                    })
                continue

            for ch in chapters:
                if self.stop_event.is_set():
                    break
                ch_file = ch.get('file')
                if not ch_file:
                    continue
                data = self.load_chapter_file(book_path, ch_file)
                if not data:
                    continue
                hadiths = data.get('hadiths', [])
                hadiths_to_translate = [
                    h for h in hadiths
                    if f"{book_id}:{h.get('chapterId', 0)}:{h.get('id')}" not in processed_set
                ]
                if not hadiths_to_translate:
                    continue
                texts = [self.extract_hadith_text(h) for h in hadiths_to_translate]
                meta = [{"id": h.get('id'), "chapterId": h.get('chapterId', 0), "narrator": h.get('english', {}).get('narrator', '')} for h in hadiths_to_translate]
                try:
                    translated_texts = self.translator.translate_batch(texts, language)
                except Exception:
                    translated_texts = texts
                for i, (m, txt) in enumerate(zip(meta, translated_texts)):
                    if i < len(texts) and (txt or "").strip() == (texts[i] or "").strip():
                        continue
                    key = f"{m['chapterId']}:{m['id']}"
                    composite = f"{book_id}:{m['chapterId']}:{m['id']}"
                    translated_hadiths[key] = {"narrator": m['narrator'], "text": txt, "hadith_id": m['id'], "chapter_id": m['chapterId'], "quality": {"confidence": "HIGH", "needs_review": False}}
                    if composite not in processed_set:
                        processed_set.add(composite)
                        checkpoint['stats']['total_translated'] += 1
                        checkpoint['processed_hadiths'].append(composite)
                checkpoint['stats']['api_calls'] += (len(texts) + 14) // 15
                new_translations = [
                    {"book_id": book_id, "chapter_id": int(m["chapterId"]), "hadith_id": int(m["id"]),
                     "narrator": m.get("narrator"), "text": translated_hadiths[f"{m['chapterId']}:{m['id']}"]["text"],
                     "quality_confidence": "HIGH", "needs_review": False}
                    for m in meta if f"{m['chapterId']}:{m['id']}" in translated_hadiths
                ] if self.app else None
                if not self.app:
                    if book_id not in all_translations:
                        all_translations[book_id] = {}
                    all_translations[book_id].update(translated_hadiths)
                self.save_checkpoint(checkpoint, new_translations=new_translations)
                if not self.app:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(all_translations, f, ensure_ascii=False, indent=2)
                self._emit_progress({
                    "language": language,
                    "book_id": book_id,
                    "total_translated": checkpoint['stats']['total_translated'],
                    "total_hadiths": total_hadiths,
                    "remaining": total_hadiths - checkpoint['stats']['total_translated']
                })

        return {
            "language": language,
            "total_translated": checkpoint['stats']['total_translated'],
            "api_calls": checkpoint['stats']['api_calls'],
            "stopped": self.stop_event.is_set()
        }
