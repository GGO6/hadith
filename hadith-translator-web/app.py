"""
Hadith Translator Web - Flask app for Railway
لوحة تحكم ترجمة الأحاديث
"""
import os
import json
import logging
import sys
import threading
from pathlib import Path
from flask import Flask, render_template_string, jsonify, request, Response, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from functools import wraps

# Logging: stdout so Railway (and gunicorn) capture logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
    force=True,
)
logger = logging.getLogger("hadith")

# Ensure we can import config and translator
BASE_DIR = Path(__file__).resolve().parent
import config
config.ensure_dirs()

from translator.runner import TranslationRunner

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = config.SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = config.SQLALCHEMY_TRACK_MODIFICATIONS
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
app.config["PERMANENT_SESSION_LIFETIME"] = 86400 * 7
db = SQLAlchemy(app)

# Auth: if ADMIN_USERNAME and ADMIN_PASSWORD are set, require login
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "").strip()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
AUTH_REQUIRED = bool(ADMIN_USERNAME and ADMIN_PASSWORD)


def _is_logged_in():
    return AUTH_REQUIRED and session.get("user") == ADMIN_USERNAME


def _require_auth(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not AUTH_REQUIRED:
            return f(*args, **kwargs)
        if not _is_logged_in():
            if request.path.startswith("/api/"):
                return jsonify({"error": "Unauthorized", "login_required": True}), 401
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return wrapped


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
    logger.info("Translation started: language=%s", language)
    with _status_lock:
        _current_language = language
        _last_progress = {"language": language, "total_translated": 0, "total_hadiths": 50884, "remaining": 50884}
    def on_progress(data):
        with _status_lock:
            _last_progress.update(data)
    runner = TranslationRunner(stop_event=_stop_event, progress_callback=on_progress, app=app)
    try:
        result = runner.run(language)
        with _status_lock:
            _last_progress.update(result)
        if result.get("error"):
            logger.warning("Translation startup error: %s", result.get("error"))
        else:
            logger.info(
                "Translation finished: language=%s reason=%s total_translated=%s last_book=%s",
                language, result.get("stop_reason"), result.get("total_translated"), result.get("last_book_id"),
            )
        if result.get("last_error"):
            logger.error("Translation error: %s", result.get("last_error"))
    except Exception as e:
        logger.exception("Translation crashed: %s", e)
        from datetime import datetime, timezone
        with _status_lock:
            _last_progress.update({
                "stop_reason": "error",
                "stop_message": "توقف بسبب خطأ غير متوقع (استثناء خارج التشغيل).",
                "last_error": f"{type(e).__name__}: {e}",
                "stop_time": datetime.now(timezone.utc).isoformat(),
            })
    finally:
        with _status_lock:
            _current_language = None
        logger.info("Translation thread ended: language=%s", language)


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
        "stop_reason": progress.get("stop_reason"),
        "stop_message": progress.get("stop_message"),
        "last_book_id": progress.get("last_book_id"),
        "last_chapter_file": progress.get("last_chapter_file"),
        "last_error": progress.get("last_error"),
        "stop_time": progress.get("stop_time"),
        "error": progress.get("error"),
        "phase": progress.get("phase"),
        "books_count": progress.get("books_count"),
        "chapter_file": progress.get("chapter_file"),
        "hadiths_count": progress.get("hadiths_count"),
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


LOGIN_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تسجيل الدخول - Hadith Translator</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, sans-serif; margin: 0; padding: 20px; background: #1a1a2e; color: #eee; }
        .container { max-width: 400px; margin: 80px auto; }
        h1 { color: #e94560; text-align: center; }
        .card { background: #16213e; border-radius: 12px; padding: 24px; margin: 16px 0; }
        label { display: block; margin: 12px 0 4px 0; color: #8ab; }
        input { width: 100%; padding: 10px; font-size: 1em; border-radius: 8px; border: 1px solid #0f3460; background: #0f3460; color: #eee; }
        button { width: 100%; padding: 12px; font-size: 1em; border-radius: 8px; margin-top: 16px; background: #e94560; color: #fff; border: none; cursor: pointer; }
        button:hover { background: #ff6b6b; }
        .error { color: #ff6b6b; margin-top: 8px; font-size: 0.95em; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📚 ترجمة الأحاديث</h1>
        <div class="card">
            <h2 style="margin-top:0;">تسجيل الدخول</h2>
            <form method="post" action="">
                <label for="username">اسم المستخدم</label>
                <input type="text" id="username" name="username" required autocomplete="username">
                <label for="password">كلمة المرور</label>
                <input type="password" id="password" name="password" required autocomplete="current-password">
                <button type="submit">دخول</button>
            </form>
            {% if error %}<p class="error">{{ error }}</p>{% endif %}
        </div>
    </div>
</body>
</html>
"""


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
        .stop-info { margin-top: 12px; padding: 12px; background: #0f3460; border-radius: 8px; font-size: 0.95em; }
        .stop-info h3 { margin: 0 0 8px 0; color: #8ab; font-size: 1em; }
        .stop-info pre { margin: 4px 0; white-space: pre-wrap; word-break: break-all; color: #ccc; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📚 ترجمة الأحاديث - Hadith Translator</h1>
        <p>تشغيل الترجمة على السيرفر (Railway) - لا حاجة لفتح جهازك</p>
        {% if auth_required %}<p style="text-align:left;"><a href="{{ url_logout }}" style="color:#8ab;">تسجيل خروج</a></p>{% endif %}
        <p style="font-size:0.95em; color:#8ab;">إذا توقفت الترجمة لأي سبب (إعادة تشغيل، انقطاع، إيقاف) — اضغط «بدء الترجمة» مرة أخرى لنفس اللغة لاستئناف من آخر نقطة محفوظة.</p>

        <div class="card">
            <h2>الحالة الحالية</h2>
            <div id="status" class="status">جاري التحميل...</div>
            <div class="progress-bar"><div id="progressFill" class="progress-fill" style="width: 0%;"></div></div>
            <p id="details"></p>
            <p id="errorMsg" class="error-msg" style="display:none; color:#ff6b6b; margin-top:8px;"></p>
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
            <div id="stopInfo" class="stop-info" style="display:none;"></div>
        </div>

        <div class="card">
            <h2>التقدم حسب اللغة</h2>
            <div id="langStatus" class="lang-grid"></div>
        </div>
    </div>

    <script>
        const API = '';
        function checkAuth(r) {
            if (r.status === 401) { window.location.href = (API || '') + '/login'; return true; }
            return false;
        }
        function fetchStatus() {
            fetch(API + '/api/status').then(r => {
                if (checkAuth(r)) return;
                return r.json();
            }).then(data => {
                if (!data) return;
                document.getElementById('status').textContent = data.running
                    ? '🟢 الترجمة تعمل: ' + (data.current_language || '')
                    : '⚪ الترجمة متوقفة';
                document.getElementById('status').className = 'status ' + (data.running ? 'running' : 'stopped');
                document.getElementById('progressFill').style.width = (data.progress_pct || 0) + '%';
                let details = '';
                if (data.running) {
                    if (data.phase === 'translating' && data.last_book)
                        details = 'جاري الترجمة: كتاب ' + data.last_book + (data.chapter_file ? ' — ' + data.chapter_file : '') + (data.hadiths_count != null ? ' (' + data.hadiths_count + ' حديث)' : '') + ' | تم: ' + (data.total_translated || 0) + ' | متبقي: ' + (data.remaining || 0);
                    else if (data.phase === 'started' && data.books_count != null)
                        details = 'جاري البدء... ' + data.books_count + ' كتب.';
                    else if (data.last_book)
                        details = 'كتاب: ' + data.last_book + ' | تم: ' + (data.total_translated || 0) + ' | متبقي: ' + (data.remaining || 0) + ' | API: ' + (data.api_calls || 0);
                    else
                        details = 'تم: ' + (data.total_translated || 0) + ' | متبقي: ' + (data.remaining || 0) + ' | استدعاءات API: ' + (data.api_calls || 0);
                } else if (data.total_translated > 0) {
                    details = 'تم: ' + data.total_translated + ' | متبقي: ' + (data.remaining || 0) + ' | استدعاءات API: ' + (data.api_calls || 0);
                }
                document.getElementById('details').textContent = details;
                const errorEl = document.getElementById('errorMsg');
                if (data.error) {
                    errorEl.textContent = '⚠ ' + data.error;
                    errorEl.style.display = 'block';
                } else {
                    errorEl.style.display = 'none';
                }
                document.getElementById('btnStart').disabled = data.running;
                document.getElementById('btnStop').disabled = !data.running;
                const stopInfo = document.getElementById('stopInfo');
                if (!data.running && (data.stop_reason || data.stop_message || data.last_error || data.error)) {
                    let html = '<h3>آخر توقف — لتحليل ما حدث</h3>';
                    if (data.error) html += '<p><strong>الخطأ:</strong> ' + data.error + '</p>';
                    if (data.stop_reason) html += '<p><strong>السبب:</strong> ' + (data.stop_reason === 'user_stop' ? 'إيقاف يدوي' : data.stop_reason === 'error' ? 'خطأ' : data.stop_reason === 'completed' ? 'اكتمال' : data.stop_reason) + '</p>';
                    if (data.stop_message) html += '<p><strong>الوصف:</strong> ' + data.stop_message + '</p>';
                    if (data.last_book_id) html += '<p><strong>آخر كتاب:</strong> ' + data.last_book_id + '</p>';
                    if (data.last_chapter_file) html += '<p><strong>آخر فصل (ملف):</strong> ' + data.last_chapter_file + '</p>';
                    if (data.stop_time) html += '<p><strong>وقت التوقف (UTC):</strong> ' + data.stop_time + '</p>';
                    if (data.last_error) html += '<p><strong>تفاصيل الخطأ:</strong></p><pre>' + data.last_error + '</pre>';
                    stopInfo.innerHTML = html;
                    stopInfo.style.display = 'block';
                } else {
                    stopInfo.style.display = 'none';
                }
            }).catch(() => {});
        }
        function fetchLangStatus() {
            fetch(API + '/api/languages').then(r => {
                if (checkAuth(r)) return;
                return r.json();
            }).then(data => {
                if (!data) return;
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
                .then(r => { if (checkAuth(r)) return; return r.json(); }).then(d => { if (d !== undefined) { fetchStatus(); fetchLangStatus(); } });
        };
        document.getElementById('btnStop').onclick = () => {
            fetch(API + '/api/stop', { method: 'POST' }).then(r => { if (checkAuth(r)) return; fetchStatus(); fetchLangStatus(); });
        };
        function resetLang(lang) {
            if (!confirm('حذف ترجمة هذه اللغة والبدء من الصفر؟')) return;
            fetch(API + '/api/reset/' + lang, { method: 'POST' }).then(r => { if (checkAuth(r)) return; return r.json(); }).then(() => { fetchStatus(); fetchLangStatus(); }).catch(() => {});
        }
        setInterval(fetchStatus, 3000);
        setInterval(fetchLangStatus, 10000);
        fetchStatus();
        fetchLangStatus();
    </script>
</body>
</html>
"""


@app.route('/login', methods=['GET', 'POST'])
def login():
    if not AUTH_REQUIRED:
        return redirect(url_for('index'))
    if _is_logged_in():
        return redirect(url_for('index'))
    error = None
    if request.method == 'POST':
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["user"] = username
            session.permanent = True
            session.modified = True
            next_url = request.args.get("next") or url_for("index")
            return redirect(next_url)
        error = "اسم المستخدم أو كلمة المرور غير صحيحة."
    return render_template_string(LOGIN_HTML, error=error)


@app.route('/logout')
def logout():
    session.pop("user", None)
    return redirect(url_for('login') if AUTH_REQUIRED else url_for('index'))


@app.route('/')
@_require_auth
def index():
    _ensure_tables()
    return render_template_string(
        INDEX_HTML,
        languages=config.LANGUAGES,
        auth_required=AUTH_REQUIRED,
        url_logout=url_for('logout'),
    )


@app.route('/api/status')
@_require_auth
def api_status():
    return jsonify(get_status())


@app.route('/api/languages')
@_require_auth
def api_languages():
    return jsonify(get_languages_status())


@app.route('/api/start', methods=['POST'])
@_require_auth
def api_start():
    global _translation_thread, _stop_event
    data = request.get_json() or {}
    language = data.get("language", "turkish")
    if language not in config.LANGUAGES:
        return jsonify({"error": "Unknown language"}), 400
    with _status_lock:
        if _translation_thread is not None and _translation_thread.is_alive():
            logger.warning("api/start rejected: translation already running")
            return jsonify({"error": "Translation already running"}), 409
    _stop_event.clear()
    _translation_thread = threading.Thread(target=_run_translation, args=(language,), daemon=True)
    _translation_thread.start()
    logger.info("api/start: language=%s thread started", language)
    return jsonify({"ok": True, "language": language})


@app.route('/api/stop', methods=['POST'])
@_require_auth
def api_stop():
    _stop_event.set()
    logger.info("api/stop: stop_event set")
    return jsonify({"ok": True})


@app.route('/api/reset/<language>', methods=['POST'])
@_require_auth
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
@_require_auth
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
