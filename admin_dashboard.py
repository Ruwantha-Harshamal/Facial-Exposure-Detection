"""
admin_dashboard.py

Web-based Admin Dashboard for Privacy Exposure Checker
- View existing websites from database
- Add new websites to database  
- Scrape individual websites
- Scrape all websites at once
- View real-time scraping progress
"""

import os
import sys
import logging
import secrets
from flask import Flask, render_template_string, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import datetime
import subprocess
import threading

# Import project modules
from database_manager import DatabaseManager
from faiss_manager import FAISSManager
import config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('ADMIN_SECRET_KEY', secrets.token_hex(32))

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["1000 per day", "100 per hour"]
)

# Initialize components
db = DatabaseManager(db_path=config.SQLITE_DB_PATH, db_type=config.DB_TYPE)
faiss_mgr = FAISSManager()

# Track running scraping jobs and logs
scraping_jobs = {}
scraping_logs = []

# HTML Template
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Admin Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { background: white; padding: 30px; border-radius: 15px; margin-bottom: 30px; }
        .section { background: white; padding: 30px; border-radius: 15px; margin-bottom: 30px; }
        .btn { background: #667eea; color: white; padding: 12px 30px; border: none; border-radius: 8px; cursor: pointer; }
        .btn:hover { background: #5568d3; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f8f9fa; color: #667eea; }
        .activity-log { background: #1e1e1e; color: #00ff00; padding: 20px; border-radius: 8px; font-family: monospace; max-height: 400px; overflow-y: auto; }
        input, textarea { width: 100%; padding: 12px; border: 2px solid #e0e0e0; border-radius: 8px; margin: 8px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ Admin Dashboard</h1>
            <p>Manage Websites & Scraping - Database-Driven System</p>
        </div>
        
        <div class="section">
            <h2>➕ Add Website</h2>
            <form id="addForm">
                <input type="url" id="url" placeholder="https://example.com" required>
                <input type="text" id="name" placeholder="Website Name (optional)">
                <button type="submit" class="btn">Add Website</button>
            </form>
            <div id="addMsg"></div>
        </div>
        
        <div class="section">
            <h2>🌐 Websites ({{ websites|length }})</h2>
            {% if websites %}
            <button class="btn" onclick="scrapeAll()">🚀 Scrape All</button>
            <table>
                <tr><th>ID</th><th>URL</th><th>Images</th><th>Faces</th><th>Actions</th></tr>
                {% for w in websites %}
                <tr id="row-{{ w.id }}">
                    <td>{{ w.id }}</td>
                    <td><a href="{{ w.url }}" target="_blank">{{ w.url[:60] }}...</a></td>
                    <td>{{ w.image_count }}</td>
                    <td>{{ w.face_count }}</td>
                    <td>
                        <button class="btn" onclick="scrape('{{ w.url }}')">🔄 Scrape</button>
                        <button class="btn" style="background: #dc3545;" onclick="deleteWebsite({{ w.id }}, '{{ w.url }}', {{ w.image_count }}, {{ w.face_count }})">🗑️ Delete</button>
                    </td>
                </tr>
                {% endfor %}
            </table>
            {% else %}
            <p>No websites yet. Add one above!</p>
            {% endif %}
        </div>
        
        <div class="section">
            <h2>📋 Bulk Add</h2>
            <form id="bulkForm">
                <textarea id="bulkUrls" rows="5" placeholder="https://site1.com&#10;https://site2.com" required></textarea>
                <button type="submit" class="btn">Add to Database</button>
            </form>
            <div id="bulkMsg"></div>
        </div>
        
        <div class="section">
            <h2>📊 Activity Log (Live)</h2>
            <div class="activity-log" id="log">Waiting for activity...</div>
            <button class="btn" onclick="refreshLogs()" style="margin-top: 10px;">🔄 Refresh</button>
        </div>
    </div>
    
    <script>
        document.getElementById('addForm').onsubmit = async (e) => {
            e.preventDefault();
            const res = await fetch('/api/add_website', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({url: document.getElementById('url').value, name: document.getElementById('name').value})
            });
            const data = await res.json();
            document.getElementById('addMsg').innerHTML = data.success ? '✓ Added!' : '✗ Error: ' + data.error;
            if (data.success) setTimeout(() => location.reload(), 1000);
        };
        
        document.getElementById('bulkForm').onsubmit = async (e) => {
            e.preventDefault();
            const urls = document.getElementById('bulkUrls').value.split('\\n').filter(u => u.trim());
            const res = await fetch('/api/bulk_scrape', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({urls})
            });
            const data = await res.json();
            document.getElementById('bulkMsg').innerHTML = data.success ? `✓ Added ${data.added_count}!` : '✗ Error';
            if (data.success) setTimeout(() => location.reload(), 1000);
        };
        
        async function scrape(url) {
            if (!confirm('Scrape ' + url + '?')) return;
            const res = await fetch('/api/scrape_website', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({url})
            });
            const data = await res.json();
            alert(data.success ? '✓ Started! Watch log below.' : '✗ Error: ' + data.error);
            startRefresh();
        }
        
        async function scrapeAll() {
            if (!confirm('Scrape ALL websites?')) return;
            const res = await fetch('/api/scrape_all', {method: 'POST'});
            const data = await res.json();
            alert(data.success ? `✓ Started ${data.total_websites} websites!` : '✗ Error');
            startRefresh();
        }
        
        async function deleteWebsite(websiteId, url, imageCount, faceCount) {
            // Detailed confirmation dialog
            const msg = `⚠️ PERMANENT DELETION WARNING ⚠️\n\n` +
                `Website: ${url}\n` +
                `Images: ${imageCount}\n` +
                `Faces: ${faceCount}\n\n` +
                `This will permanently delete:\n` +
                `✗ Website record\n` +
                `✗ All ${imageCount} images\n` +
                `✗ All ${faceCount} faces and embeddings\n` +
                `✗ All face thumbnails\n` +
                `✗ All FAISS vectors for this website\n\n` +
                `THIS CANNOT BE UNDONE!\n\n` +
                `Type "DELETE" to confirm:`;
            
            const confirmation = prompt(msg);
            if (confirmation !== 'DELETE') {
                alert('❌ Deletion cancelled');
                return;
            }
            
            // Show loading state
            const row = document.getElementById('row-' + websiteId);
            if (row) row.style.opacity = '0.5';
            
            const res = await fetch('/api/delete_website', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({website_id: websiteId})
            });
            const data = await res.json();
            
            if (data.success) {
                alert(`✅ Deleted successfully!\n\n` +
                      `Images deleted: ${data.deleted_images}\n` +
                      `Faces deleted: ${data.deleted_faces}\n` +
                      `FAISS vectors removed: ${data.deleted_face_ids_count}`);
                // Remove row from table
                if (row) row.remove();
                // Refresh after showing results
                setTimeout(() => location.reload(), 2000);
            } else {
                alert('❌ Error: ' + data.error);
                if (row) row.style.opacity = '1';
            }
        }
        
        let interval;
        async function refreshLogs() {
            const res = await fetch('/api/scraping_status');
            const data = await res.json();
            if (data.logs.length > 0) {
                document.getElementById('log').innerHTML = data.logs.join('<br>');
                document.getElementById('log').scrollTop = 999999;
            }
        }
        
        function startRefresh() {
            if (interval) clearInterval(interval);
            interval = setInterval(refreshLogs, 2000);
            refreshLogs();
        }
        
        setInterval(refreshLogs, 5000);
        refreshLogs();
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    stats = db.get_statistics()
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT w.id, w.url, w.name, COUNT(DISTINCT i.id) as img, COUNT(DISTINCT f.id) as face
        FROM websites w
        LEFT JOIN images i ON w.id = i.website_id AND i.deleted_at IS NULL
        LEFT JOIN faces f ON i.id = f.image_id AND f.deleted_at IS NULL
        WHERE w.deleted_at IS NULL
        GROUP BY w.id ORDER BY w.created_at DESC
    """)
    websites = [{'id': r[0], 'url': r[1], 'name': r[2], 'image_count': r[3], 'face_count': r[4]} for r in cursor.fetchall()]
    return render_template_string(DASHBOARD_TEMPLATE, websites=websites)


@app.route('/api/add_website', methods=['POST'])
def add_website():
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        if not url:
            return jsonify({'success': False, 'error': 'URL required'}), 400
        website_id = db.add_website(url)  # name parameter not used in current schema
        return jsonify({'success': True, 'website_id': website_id})
    except Exception as e:
        logger.exception("Error adding website")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/scrape_website', methods=['POST'])
def scrape_website():
    try:
        url = request.get_json().get('url', '').strip()
        if not url:
            return jsonify({'success': False, 'error': 'URL required'}), 400
        if url in scraping_jobs and scraping_jobs[url] == 'running':
            return jsonify({'success': False, 'error': 'Already scraping'}), 400
        
        scraping_jobs[url] = 'running'
        
        def run():
            try:
                scraping_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Starting: {url}")
                subprocess.run([sys.executable, 'main_pipeline.py', '--url', url, '--headless'], check=True)
                scraping_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Completed: {url}")
                scraping_jobs[url] = 'completed'
            except Exception as e:
                scraping_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ Failed: {url}")
                scraping_jobs[url] = 'failed'
        
        threading.Thread(target=run, daemon=True).start()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/scrape_all', methods=['POST'])
def scrape_all():
    try:
        cursor = db.conn.cursor()
        cursor.execute("SELECT url FROM websites WHERE deleted_at IS NULL")
        urls = [r[0] for r in cursor.fetchall()]
        if not urls:
            return jsonify({'success': False, 'error': 'No websites'}), 400
        
        for url in urls:
            scraping_jobs[url] = 'running'
        
        def run():
            try:
                scraping_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 Bulk: {len(urls)} websites")
                for i, url in enumerate(urls, 1):
                    try:
                        scraping_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] [{i}/{len(urls)}] {url}")
                        subprocess.run([sys.executable, 'main_pipeline.py', '--url', url, '--headless'], check=True)
                        scraping_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ [{i}/{len(urls)}] Done")
                        scraping_jobs[url] = 'completed'
                    except:
                        scraping_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ [{i}/{len(urls)}] Failed")
                        scraping_jobs[url] = 'failed'
                scraping_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 🎉 All done!")
            except Exception as e:
                scraping_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ Error: {e}")
        
        threading.Thread(target=run, daemon=True).start()
        return jsonify({'success': True, 'total_websites': len(urls)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/bulk_scrape', methods=['POST'])
def bulk_scrape():
    try:
        urls = request.get_json().get('urls', [])
        added = 0
        for url in urls:
            if url.strip():
                try:
                    db.add_website(url.strip())
                    added += 1
                except:
                    pass
        return jsonify({'success': True, 'added_count': added})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/delete_website', methods=['POST'])
def delete_website():
    """
    Delete a website and ALL related data (images, faces, thumbnails, embeddings, FAISS vectors).
    This is a HARD DELETE - permanent removal.
    """
    try:
        website_id = request.get_json().get('website_id')
        if not website_id:
            return jsonify({'success': False, 'error': 'website_id required'}), 400
        
        # Get face IDs before deletion (for FAISS removal)
        face_ids = db.get_face_ids_by_website(website_id)
        
        # Delete from database (website, images, faces, thumbnails, embeddings)
        stats = db.delete_website_complete(website_id)
        
        # Delete from FAISS index (only these face vectors)
        if face_ids:
            faiss_mgr.remove_face_ids(face_ids)
            # Save updated index
            faiss_mgr.save_index()
        
        scraping_logs.append(
            f"[{datetime.now().strftime('%H:%M:%S')}] 🗑️ Deleted website #{website_id}: "
            f"{stats['deleted_images']} images, {stats['deleted_faces']} faces"
        )
        
        return jsonify({
            'success': True,
            'deleted_images': stats['deleted_images'],
            'deleted_faces': stats['deleted_faces'],
            'deleted_face_ids_count': len(face_ids)
        })
    except Exception as e:
        logger.exception("Error deleting website")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/scraping_status')
@limiter.exempt  # No rate limit for status checks
def scraping_status():
    return jsonify({'success': True, 'jobs': scraping_jobs, 'logs': scraping_logs[-50:]})


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("ADMIN DASHBOARD")
    print("=" * 70)
    print(f"Websites: {db.get_statistics().get('active_websites', 0)}")
    print(f"Faces: {faiss_mgr.get_total_vectors()}")
    print("\nhttp://localhost:5001")
    print("=" * 70 + "\n")
    app.run(host='0.0.0.0', port=5001, debug=False)
