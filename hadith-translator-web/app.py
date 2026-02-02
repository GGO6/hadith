"""
Hadith Translator Web - Flask app for Railway
لوحة تحكم ترجمة الأحاديث
"""
import os
import json
import threading
from pathlib import Path
from flask import Flask, render_template_string, jsonify, request, Response
from flask_sqlalchemy import SQLAlchemy

# Ensure we can import config and translator
BASE_DIR = Path(__file__).resolve().parent
import config
config.ensure_dirs()

from translator.runner import TranslationRunner

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = config.SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = config.SQLALCHEMY_TRACK_MODIFICATIONS
db = SQLAlchemy(app)


class TranslationProgress(db.Model):
    """تقدم الترجمة لكل لغة (بديل لملف الـ checkpoint)."""
    __tablename__ = "translation_progress"
    id = db.Column(db.Integer, primary_key=True)
    language = db.Column(db.String(50), unique=True, nullable=False)
    total_translated = db.Column(db.Integer, default=0)
    api_calls = db.Column(db.Integer, default=0)
    tokens_used = db.Column(db.Integer, default=0)
    last_book_id = db.Column(db.String(100))

    def __repr__(self):
        return f"<TranslationProgress {self.language}>"


class HadithTranslation(db.Model):
    """ترجمة حديث واحد بلغة معينة."""
    __tablename__ = "hadith_translations"
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.String(100), nullable=False)
    chapter_id = db.Column(db.Integer, nullable=False)
    hadith_id = db.Column(db.Integer, nullable=False)
    language_code = db.Column(db.String(10), nullable=False)
    narrator = db.Column(db.Text)
    text = db.Column(db.Text, nullable=False)
    quality_confidence = db.Column(db.String(50))
    needs_review = db.Column(db.Boolean, default=False)

    __table_args__ = (
        db.UniqueConstraint(
            "book_id", "chapter_id", "hadith_id", "language_code",
            name="uq_hadith_translation"
        ),
    )


# Global state for background translation
_translation_thread = None
_stop_event = threading.Event()
_last_progress = {}
_current_language = None
_status_lock = threading.Lock()
_tables_created = False


def _ensure_tables():
    global _tables_created
    if not _tables_created:
        with app.app_context():
            db.create_all()
        _tables_created = True


def _run_translation(language: str):
    global _last_progress, _current_language
    with _status_lock:
        _current_language = language
        _last_progress = {"language": language, "total_translated": 0, "total_hadiths": 50884, "remaining": 50884}
    def on_progress(data):
        with _status_lock:
            _last_progress.update(data)
    runner = TranslationRunner(stop_event=_stop_event, progress_callback=on_progress, app=app)
    result = runner.run(language)
    with _status_lock:
        _last_progress.update(result)
        _current_language = None


def get_status():
    with _status_lock:
        lang = _current_language
        progress = dict(_last_progress)
    running = _translation_thread is not None and _translation_thread.is_alive()
    # Get checkpoint stats for current or last language
    lang_for_stats = lang or (progress.get("language") if progress else None)
    total_translated = progress.get("total_translated", 0)
    total_hadiths = progress.get("total_hadiths", 50884)
    if isinstance(total_hadiths, (Path, str)) and not isinstance(total_hadiths, int):
        total_hadiths = 50884
    remaining = progress.get("remaining", total_hadiths - total_translated)
    return {
        "running": running,
        "current_language": lang,
        "total_translated": total_translated,
        "total_hadiths": total_hadiths,
        "remaining": remaining,
        "progress_pct": round(100 * total_translated / total_hadiths, 1) if total_hadiths else 0,
        "last_book": progress.get("book_id"),
        "api_calls": progress.get("api_calls", 0),
        "stopped": progress.get("stopped", False),
    }


def get_languages_status():
    """Get per-language stats from DB, with fallback to JSON files."""
    out = {}
    for lang_id, info in config.LANGUAGES.items():
        total = 0
        try:
            prog = TranslationProgress.query.filter_by(language=lang_id).first()
            if prog:
                total = prog.total_translated
            else:
                total = HadithTranslation.query.filter_by(language_code=lang_id).count()
        except Exception:
            cp_file = config.CHECKPOINTS_DIR / f"{lang_id}_api_checkpoint.json"
            out_file = config.OUTPUT_DIR / lang_id / "all_translations.json"
            if cp_file.exists():
                try:
                    with open(cp_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        total = len(data.get("processed_hadiths", []))
                except Exception:
                    pass
            elif out_file.exists():
                try:
                    with open(out_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        total = sum(len(v) for v in data.values() if isinstance(v, dict))
                except Exception:
                    pass
        out[lang_id] = {"name": info["name"], "native_name": info.get("native_name", ""), "translated": total}
    return out


def get_export_data(language: str):
    """تجمع الترجمات للغة من DB أو من ملف JSON بنفس صيغة all_translations.json."""
    if language not in config.LANGUAGES:
        return None
    out = {}
    try:
        rows = HadithTranslation.query.filter_by(language_code=language).order_by(
            HadithTranslation.book_id, HadithTranslation.chapter_id, HadithTranslation.hadith_id
        ).all()
        for r in rows:
            if r.book_id not in out:
                out[r.book_id] = {}
            key = f"{r.chapter_id}:{r.hadith_id}"
            out[r.book_id][key] = {
                "narrator": r.narrator or "",
                "text": r.text,
                "hadith_id": r.hadith_id,
                "chapter_id": r.chapter_id,
                "quality": {"confidence": r.quality_confidence or "HIGH", "needs_review": r.needs_review or False},
            }
        if out:
            return out
    except Exception:
        pass
    out_file = config.OUTPUT_DIR / language / "all_translations.json"
    if out_file.exists():
        try:
            with open(out_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return out if out else None


INDEX_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ترجمة الأحاديث - Hadith Translator</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, sans-serif; margin: 0; padding: 20px; background: #1a1a2e; color: #eee; }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { color: #e94560; }
        .card { background: #16213e; border-radius: 12px; padding: 20px; margin: 16px 0; }
        .status { font-size: 1.1em; margin: 10px 0; }
        .status.running { color: #4ecca3; }
        .status.stopped { color: #ff6b6b; }
        .progress-bar { width: 100%; height: 24px; background: #0f3460; border-radius: 12px; overflow: hidden; margin: 10px 0; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #e94560, #4ecca3); transition: width 0.3s; }
        select, button { padding: 10px 20px; font-size: 1em; border-radius: 8px; margin: 4px; cursor: pointer; }
        select { background: #0f3460; color: #eee; border: 1px solid #e94560; }
        button { background: #e94560; color: #fff; border: none; }
        button:disabled { opacity: 0.5; cursor: not-allowed; }
        button.stop { background: #ff6b6b; }
        .lang-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px; margin-top: 12px; }
        .lang-item { background: #0f3460; padding: 10px; border-radius: 8px; }
        .lang-item .num { color: #4ecca3; font-weight: bold; }
        .lang-item a.dl { display: block; margin-top: 6px; font-size: 0.9em; color: #4ecca3; }
        .lang-item a.dl:hover { text-decoration: underline; }
        .lang-item button.reset { margin-top: 4px; font-size: 0.85em; padding: 4px 8px; background: #5a3; color: #fff; border: none; border-radius: 4px; cursor: pointer; }
        .lang-item button.reset:hover { background: #6b4; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📚 ترجمة الأحاديث - Hadith Translator</h1>
        <p>تشغيل الترجمة على السيرفر (Railway) - لا حاجة لفتح جهازك</p>

        <div class="card">
            <h2>الحالة الحالية</h2>
            <div id="status" class="status">جاري التحميل...</div>
            <div class="progress-bar"><div id="progressFill" class="progress-fill" style="width: 0%;"></div></div>
            <p id="details"></p>
            <div>
                <label>اللغة: </label>
                <select id="langSelect">
                    {% for code, info in languages.items() %}
                    <option value="{{ code }}">{{ info.name }} ({{ info.native_name }})</option>
                    {% endfor %}
                </select>
                <button id="btnStart">▶ بدء الترجمة</button>
                <button id="btnStop" class="stop" disabled>⏹ إيقاف</button>
            </div>
        </div>

        <div class="card">
            <h2>التقدم حسب اللغة</h2>
            <div id="langStatus" class="lang-grid"></div>
        </div>
    </div>

    <script>
        const API = '';
        function fetchStatus() {
            fetch(API + '/api/status').then(r => r.json()).then(data => {
                document.getElementById('status').textContent = data.running
                    ? '🟢 الترجمة تعمل: ' + (data.current_language || '')
                    : '⚪ الترجمة متوقفة';
                document.getElementById('status').className = 'status ' + (data.running ? 'running' : 'stopped');
                document.getElementById('progressFill').style.width = (data.progress_pct || 0) + '%';
                document.getElementById('details').textContent = data.running || data.total_translated
                    ? `تم: ${data.total_translated || 0} | متبقي: ${data.remaining || 0} | استدعاءات API: ${data.api_calls || 0}`
                    : '';
                document.getElementById('btnStart').disabled = data.running;
                document.getElementById('btnStop').disabled = !data.running;
            }).catch(() => {});
        }
        function fetchLangStatus() {
            fetch(API + '/api/languages').then(r => r.json()).then(data => {
                const grid = document.getElementById('langStatus');
                grid.innerHTML = Object.entries(data).map(([code, info]) => {
                    let actions = '';
                    if (info.translated > 0) {
                        actions += `<a class="dl" href="${API}/api/export/${code}" download>⬇ تحميل</a>`;
                        actions += ` <button class="reset" onclick="resetLang('${code}')" title="حذف الترجمة وإعادة البدء من الصفر">إعادة تعيين</button>`;
                    }
                    return `<div class="lang-item">${info.native_name || info.name}<br><span class="num">${info.translated.toLocaleString()}</span> حديث${actions ? '<br>' + actions : ''}</div>`;
                }).join('');
            }).catch(() => {});
        }
        document.getElementById('btnStart').onclick = () => {
            const lang = document.getElementById('langSelect').value;
            fetch(API + '/api/start', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({language: lang}) })
                .then(r => r.json()).then(() => { fetchStatus(); fetchLangStatus(); });
        };
        document.getElementById('btnStop').onclick = () => {
            fetch(API + '/api/stop', { method: 'POST' }).then(() => { fetchStatus(); fetchLangStatus(); });
        };
        function resetLang(lang) {
            if (!confirm('حذف ترجمة هذه اللغة والبدء من الصفر؟')) return;
            fetch(API + '/api/reset/' + lang, { method: 'POST' }).then(r => r.json()).then(() => { fetchStatus(); fetchLangStatus(); }).catch(() => {});
        }
        setInterval(fetchStatus, 3000);
        setInterval(fetchLangStatus, 10000);
        fetchStatus();
        fetchLangStatus();
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    _ensure_tables()
    return render_template_string(INDEX_HTML, languages=config.LANGUAGES)


@app.route('/api/status')
def api_status():
    return jsonify(get_status())


@app.route('/api/languages')
def api_languages():
    return jsonify(get_languages_status())


@app.route('/api/start', methods=['POST'])
def api_start():
    global _translation_thread, _stop_event
    data = request.get_json() or {}
    language = data.get("language", "turkish")
    if language not in config.LANGUAGES:
        return jsonify({"error": "Unknown language"}), 400
    with _status_lock:
        if _translation_thread is not None and _translation_thread.is_alive():
            return jsonify({"error": "Translation already running"}), 409
    _stop_event.clear()
    _translation_thread = threading.Thread(target=_run_translation, args=(language,), daemon=True)
    _translation_thread.start()
    return jsonify({"ok": True, "language": language})


@app.route('/api/stop', methods=['POST'])
def api_stop():
    _stop_event.set()
    return jsonify({"ok": True})


@app.route('/api/reset/<language>', methods=['POST'])
def api_reset(language):
    """حذف تقدم وترجمات لغة واحدة من DB (لإعادة الترجمة من الصفر بعد إصلاح مشكلة النص الإنجليزي)."""
    if language not in config.LANGUAGES:
        return jsonify({"error": "Unknown language"}), 404
    with _status_lock:
        if _translation_thread is not None and _translation_thread.is_alive():
            return jsonify({"error": "Stop translation first"}), 409
    try:
        with app.app_context():
            HadithTranslation.query.filter_by(language_code=language).delete()
            TranslationProgress.query.filter_by(language=language).delete()
            db.session.commit()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"ok": True, "language": language})


@app.route('/api/export/<language>')
def api_export(language):
    """تحميل ترجمات لغة واحدة كملف JSON (نفس صيغة all_translations.json)."""
    if language not in config.LANGUAGES:
        return jsonify({"error": "Unknown language"}), 404
    data = get_export_data(language)
    if data is None or not data:
        return jsonify({"error": "No translations found for this language"}), 404
    code = config.LANGUAGES[language].get("code", language)
    filename = f"hadith_translations_{code}.json"
    body = json.dumps(data, ensure_ascii=False, indent=2)
    return Response(
        body,
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


if __name__ == '__main__':
    _ensure_tables()
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.getenv('FLASK_DEBUG', '0') == '1')
