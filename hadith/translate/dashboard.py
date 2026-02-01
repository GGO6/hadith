#!/usr/bin/env python3
"""
Web Dashboard for Translation Progress
لوحة تحكم ويب لمتابعة التقدم
"""
from flask import Flask, jsonify, render_template_string
import json
from pathlib import Path
from datetime import datetime
import os

app = Flask(__name__)

# Paths
SCRIPT_DIR = Path(__file__).parent
CHECKPOINT_FILE = SCRIPT_DIR / "checkpoints" / "turkish_api_checkpoint.json"
OUTPUT_FILE = SCRIPT_DIR / "output" / "turkish" / "all_translations.json"
LOG_FILE = SCRIPT_DIR / "translation_api_full.log"

def get_checkpoint_data():
    """Get checkpoint data"""
    if not CHECKPOINT_FILE.exists():
        return None
    
    with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_output_data():
    """Get output file data"""
    if not OUTPUT_FILE.exists():
        return {}
    
    with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_log_tail(lines=50):
    """Get last N lines from log file"""
    if not LOG_FILE.exists():
        return []
    
    try:
        with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
            return all_lines[-lines:]
    except:
        return []

def check_process_status():
    """Check if translation process is running"""
    import subprocess
    try:
        # Try multiple methods to check process
        result = subprocess.run(
            ['pgrep', '-f', 'python.*run_api_translation'],
            capture_output=True,
            text=True,
            timeout=2
        )
        return result.returncode == 0
    except:
        # Fallback: check if log file was recently updated
        try:
            if LOG_FILE.exists():
                mtime = LOG_FILE.stat().st_mtime
                diff = datetime.now().timestamp() - mtime
                return diff < 300  # Active if updated in last 5 minutes
        except:
            pass
        return False

@app.route('/')
def index():
    """Main dashboard page"""
    html_template = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>لوحة تحكم الترجمة</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .header {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 20px;
            text-align: center;
        }
        
        .header h1 {
            color: #333;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .status-badge {
            display: inline-block;
            padding: 10px 20px;
            border-radius: 25px;
            font-weight: bold;
            font-size: 1.1em;
            margin-top: 10px;
        }
        
        .status-running {
            background: #4CAF50;
            color: white;
        }
        
        .status-stopped {
            background: #f44336;
            color: white;
        }
        
        .status-stopped:hover {
            background: #d32f2f;
        }
        
        .stop-reason {
            margin-top: 10px;
            padding: 15px;
            background: #fff3cd;
            border-right: 4px solid #ff9800;
            border-radius: 8px;
            color: #856404;
        }
        
        .stop-reason h4 {
            margin-bottom: 8px;
            color: #856404;
        }
        
        .stop-reason ul {
            margin-right: 20px;
            margin-top: 8px;
        }
        
        .stop-reason li {
            margin: 5px 0;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .stat-card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            text-align: center;
        }
        
        .stat-card h3 {
            color: #666;
            font-size: 0.9em;
            margin-bottom: 10px;
            text-transform: uppercase;
        }
        
        .stat-card .value {
            font-size: 2.5em;
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }
        
        .stat-card .sub-value {
            color: #999;
            font-size: 0.9em;
        }
        
        .progress-section {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        
        .progress-bar-container {
            width: 100%;
            height: 40px;
            background: #e0e0e0;
            border-radius: 20px;
            overflow: hidden;
            margin-top: 15px;
        }
        
        .progress-bar {
            height: 100%;
            background: linear-gradient(90deg, #4CAF50, #8BC34A);
            transition: width 0.5s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }
        
        .books-section {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        
        .book-item {
            padding: 15px;
            margin: 10px 0;
            background: #f5f5f5;
            border-radius: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .book-item.completed {
            background: #e8f5e9;
            border-right: 4px solid #4CAF50;
        }
        
        .log-section {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .log-line {
            margin: 5px 0;
            padding: 5px;
            border-radius: 3px;
        }
        
        .log-line.error {
            background: rgba(244, 67, 54, 0.2);
            color: #f44336;
        }
        
        .log-line.warning {
            background: rgba(255, 152, 0, 0.2);
            color: #ff9800;
        }
        
        .log-line.success {
            background: rgba(76, 175, 80, 0.2);
            color: #4CAF50;
        }
        
        .refresh-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 25px;
            font-size: 1em;
            cursor: pointer;
            margin-top: 20px;
            transition: background 0.3s;
        }
        
        .refresh-btn:hover {
            background: #764ba2;
        }
        
        .auto-refresh {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-top: 15px;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .pulsing {
            animation: pulse 2s infinite;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌍 لوحة تحكم الترجمة</h1>
            <div id="status-badge" class="status-badge status-stopped">جاري التحميل...</div>
            <div id="stop-reason" class="stop-reason" style="display: none;">
                <h4>⚠️ سبب التوقف:</h4>
                <ul id="stop-reasons-list"></ul>
            </div>
            <div class="auto-refresh">
                <label>
                    <input type="checkbox" id="auto-refresh" checked>
                    تحديث تلقائي كل 5 ثواني
                </label>
            </div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>تم ترجمة</h3>
                <div class="value" id="translated">0</div>
                <div class="sub-value" id="translated-pct">0%</div>
            </div>
            
            <div class="stat-card">
                <h3>متبقي</h3>
                <div class="value" id="remaining">0</div>
                <div class="sub-value">حديث</div>
            </div>
            
            <div class="stat-card">
                <h3>استدعاءات API</h3>
                <div class="value" id="api-calls">0</div>
                <div class="sub-value" id="api-cost">$0.00</div>
            </div>
            
            <div class="stat-card">
                <h3>الكتب المكتملة</h3>
                <div class="value" id="books-completed">0</div>
                <div class="sub-value">من 17</div>
            </div>
        </div>
        
        <div class="progress-section">
            <h2>📊 شريط التقدم</h2>
            <div class="progress-bar-container">
                <div class="progress-bar" id="progress-bar" style="width: 0%">0%</div>
            </div>
            <div style="margin-top: 15px; color: #666;">
                <div>⏱️ الوقت المتوقع المتبقي: <span id="time-remaining">حساب...</span></div>
                <div style="margin-top: 5px;">🕐 آخر تحديث: <span id="last-update">-</span></div>
            </div>
        </div>
        
        <div class="books-section">
            <h2>📚 حالة الكتب</h2>
            <div id="books-list">جاري التحميل...</div>
        </div>
        
        <div class="log-section">
            <h3 style="color: white; margin-bottom: 15px;">📝 آخر السجلات</h3>
            <div id="log-content">جاري التحميل...</div>
        </div>
        
        <button class="refresh-btn" onclick="loadData()">🔄 تحديث الآن</button>
    </div>
    
    <script>
        let autoRefreshInterval;
        
        function formatNumber(num) {
            return num.toString().replace(/\\B(?=(\\d{3})+(?!\\d))/g, ",");
        }
        
        function formatTime(minutes) {
            if (minutes < 60) {
                return Math.round(minutes) + ' دقيقة';
            }
            const hours = Math.floor(minutes / 60);
            const mins = Math.round(minutes % 60);
            return hours + ' ساعة و ' + mins + ' دقيقة';
        }
        
        function calculateCost(apiCalls) {
            // Estimate: ~500 tokens per call, $0.15/1M input, $0.60/1M output
            const tokensPerCall = 500;
            const totalTokens = apiCalls * tokensPerCall;
            const inputCost = (totalTokens * 0.5 / 1000000) * 0.15;
            const outputCost = (totalTokens * 0.5 / 1000000) * 0.60;
            return (inputCost + outputCost).toFixed(2);
        }
        
        async function loadData() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                // Update status
                const statusBadge = document.getElementById('status-badge');
                const stopReasonDiv = document.getElementById('stop-reason');
                const stopReasonsList = document.getElementById('stop-reasons-list');
                
                if (data.is_running) {
                    statusBadge.textContent = '✅ العملية تعمل';
                    statusBadge.className = 'status-badge status-running pulsing';
                    stopReasonDiv.style.display = 'none';
                } else {
                    statusBadge.textContent = '⏸️ العملية متوقفة';
                    statusBadge.className = 'status-badge status-stopped';
                    
                    // Show stop reasons
                    if (data.stop_reasons && data.stop_reasons.length > 0) {
                        stopReasonDiv.style.display = 'block';
                        stopReasonsList.innerHTML = '';
                        data.stop_reasons.forEach(reason => {
                            const li = document.createElement('li');
                            li.textContent = reason;
                            stopReasonsList.appendChild(li);
                        });
                    } else {
                        stopReasonDiv.style.display = 'none';
                    }
                }
                
                // Update stats
                document.getElementById('translated').textContent = formatNumber(data.translated);
                document.getElementById('translated-pct').textContent = data.percentage.toFixed(2) + '%';
                document.getElementById('remaining').textContent = formatNumber(data.remaining);
                document.getElementById('api-calls').textContent = formatNumber(data.api_calls);
                document.getElementById('api-cost').textContent = '$' + calculateCost(data.api_calls);
                document.getElementById('books-completed').textContent = data.books_completed;
                
                // Update progress bar
                const progressBar = document.getElementById('progress-bar');
                progressBar.style.width = data.percentage + '%';
                progressBar.textContent = data.percentage.toFixed(2) + '%';
                
                // Update time remaining
                document.getElementById('time-remaining').textContent = data.time_remaining;
                document.getElementById('last-update').textContent = data.last_update;
                
                // Update books list
                const booksList = document.getElementById('books-list');
                booksList.innerHTML = '';
                data.books.forEach(book => {
                    const bookDiv = document.createElement('div');
                    bookDiv.className = 'book-item' + (book.completed ? ' completed' : '');
                    bookDiv.innerHTML = `
                        <div>
                            <strong>${book.name}</strong>
                            ${book.hadiths > 0 ? `<span style="color: #666; margin-right: 10px;">(${formatNumber(book.hadiths)} حديث)</span>` : ''}
                        </div>
                        <div>
                            ${book.completed ? '✅' : '⏳'}
                        </div>
                    `;
                    booksList.appendChild(bookDiv);
                });
                
                // Update log
                const logContent = document.getElementById('log-content');
                logContent.innerHTML = '';
                data.log_lines.forEach(line => {
                    const logLine = document.createElement('div');
                    logLine.className = 'log-line';
                    if (line.includes('Error') || line.includes('error') || line.includes('Exception')) {
                        logLine.className += ' error';
                    } else if (line.includes('Warning') || line.includes('warning') || line.includes('⚠️')) {
                        logLine.className += ' warning';
                    } else if (line.includes('✅') || line.includes('completed')) {
                        logLine.className += ' success';
                    }
                    logLine.textContent = line;
                    logContent.appendChild(logLine);
                });
                logContent.scrollTop = logContent.scrollHeight;
                
            } catch (error) {
                console.error('Error loading data:', error);
            }
        }
        
        // Auto refresh
        document.getElementById('auto-refresh').addEventListener('change', function(e) {
            if (e.target.checked) {
                autoRefreshInterval = setInterval(loadData, 5000);
            } else {
                clearInterval(autoRefreshInterval);
            }
        });
        
        // Initial load
        loadData();
        if (document.getElementById('auto-refresh').checked) {
            autoRefreshInterval = setInterval(loadData, 5000);
        }
    </script>
</body>
</html>
    """
    return render_template_string(html_template)

@app.route('/api/status')
def api_status():
    """API endpoint for status data"""
    checkpoint = get_checkpoint_data()
    output = get_output_data()
    log_lines = get_log_tail(30)
    
    # Check process status
    is_running = check_process_status()
    
    # Determine stop reasons if not running
    stop_reasons = []
    if not is_running and checkpoint:
        mtime = CHECKPOINT_FILE.stat().st_mtime
        diff_minutes = (datetime.now().timestamp() - mtime) / 60
        
        if diff_minutes > 60:
            stop_reasons.append(f"آخر تحديث منذ {int(diff_minutes/60)} ساعة ({int(diff_minutes)} دقيقة)")
        elif diff_minutes > 30:
            stop_reasons.append(f"آخر تحديث منذ {int(diff_minutes)} دقيقة")
        
        # Check if output file has fewer hadiths than checkpoint
        output_total = sum(len(v) for v in output.values() if isinstance(v, dict))
        checkpoint_total = checkpoint['stats']['total_translated']
        if output_total < checkpoint_total:
            missing = checkpoint_total - output_total
            stop_reasons.append(f"ملف Output يحتوي على {output_total} حديث بينما checkpoint يحتوي على {checkpoint_total} ({missing} حديث مفقود)")
        
        # Check log for errors
        log_lines = get_log_tail(50)
        error_count = sum(1 for line in log_lines if 'error' in line.lower() or 'exception' in line.lower() or 'failed' in line.lower())
        if error_count > 0:
            stop_reasons.append(f"تم العثور على {error_count} خطأ/تحذير في السجل")
    
    # Get checkpoint data
    if checkpoint:
        translated = checkpoint['stats']['total_translated']
        api_calls = checkpoint['stats']['api_calls']
        processed_books = checkpoint.get('processed_books', [])
        
        # Get last update time
        mtime = CHECKPOINT_FILE.stat().st_mtime
        last_update = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        diff_minutes = (datetime.now().timestamp() - mtime) / 60
        
        if diff_minutes < 1:
            last_update_str = "الآن"
        elif diff_minutes < 60:
            last_update_str = f"منذ {int(diff_minutes)} دقيقة"
        else:
            hours = int(diff_minutes / 60)
            last_update_str = f"منذ {hours} ساعة"
    else:
        translated = 0
        api_calls = 0
        processed_books = []
        last_update_str = "لا يوجد"
    
    total_hadiths = 50884
    remaining = total_hadiths - translated
    percentage = (translated / total_hadiths) * 100 if total_hadiths > 0 else 0
    
    # Estimate time remaining
    if translated > 0:
        estimated_total_hours = 18
        estimated_remaining_hours = estimated_total_hours * (remaining / total_hadiths)
        hours = int(estimated_remaining_hours)
        minutes = int((estimated_remaining_hours - hours) * 60)
        time_remaining = f"~{hours} ساعة و {minutes} دقيقة"
    else:
        time_remaining = "حساب..."
    
    # Get books status
    all_books = [
        'bukhari', 'muslim', 'abudawud', 'tirmidhi', 'nasai', 
        'ibnmajah', 'malik', 'ahmed', 'darimi', 'nawawi40', 
        'qudsi40', 'riyad_assalihin', 'bulugh_almaram', 
        'mishkat_almasabih', 'aladab_almufrad', 'shamail_muhammadiyah'
    ]
    
    books_status = []
    for book_id in all_books:
        book_hadiths = len(output.get(book_id, {})) if isinstance(output.get(book_id), dict) else 0
        books_status.append({
            'id': book_id,
            'name': book_id.replace('_', ' ').title(),
            'completed': book_id in processed_books,
            'hadiths': book_hadiths
        })
    
    return jsonify({
        'is_running': is_running,
        'translated': translated,
        'remaining': remaining,
        'percentage': percentage,
        'api_calls': api_calls,
        'books_completed': len(processed_books),
        'time_remaining': time_remaining,
        'last_update': last_update_str,
        'books': books_status,
        'log_lines': [line.rstrip() for line in log_lines[-20:]],
        'stop_reasons': stop_reasons
    })

if __name__ == '__main__':
    print("="*60)
    print("🌐 لوحة التحكم جاهزة!")
    print("="*60)
    print("افتح المتصفح على: http://localhost:5000")
    print("أو: http://127.0.0.1:5000")
    print("اضغط Ctrl+C لإيقاف الخادم")
    print("="*60)
    try:
        app.run(host='127.0.0.1', port=5000, debug=False, threaded=True)
    except OSError as e:
        if "Address already in use" in str(e):
            print("\n❌ الخطأ: المنفذ 5000 مستخدم بالفعل")
            print("💡 جرب:")
            print("   lsof -ti:5000 | xargs kill -9")
            print("   ثم شغّل مرة أخرى")
        else:
            raise
