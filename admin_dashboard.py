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
from datetime import datetime, timedelta
import subprocess
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

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

# Initialize APScheduler
scheduler = BackgroundScheduler()
scheduler.start()

# Track auto-scraping status
auto_rescrape_status = {
    'enabled': config.AUTO_RESCRAPE_ENABLED,
    'next_run': None,
    'last_run': None,
    'interval_days': config.AUTO_RESCRAPE_INTERVAL_DAYS
}

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
                        <button class="btn" style="background: #28a745;" onclick="rescrape('{{ w.url }}', {{ w.id }})">♻️ Re-scrape</button>
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
            <h2>⏰ Stale Websites (Need Update)</h2>
            <p>Websites last scraped more than {{ rescrape_days }} days ago:</p>
            {% if stale_websites %}
            <button class="btn" style="background: #28a745;" onclick="rescrapeStale()">♻️ Update All Stale Websites</button>
            <table>
                <tr><th>URL</th><th>Last Scraped</th><th>Days Old</th><th>Images</th><th>Faces</th><th>Action</th></tr>
                {% for w in stale_websites %}
                <tr>
                    <td><a href="{{ w.url }}" target="_blank">{{ w.url[:60] }}...</a></td>
                    <td>{{ w.scraped_at }}</td>
                    <td><strong>{{ w.days_old }}</strong> days</td>
                    <td>{{ w.image_count }}</td>
                    <td>{{ w.face_count }}</td>
                    <td>
                        <button class="btn" style="background: #28a745;" onclick="rescrape('{{ w.url }}', {{ w.id }})">♻️ Update</button>
                    </td>
                </tr>
                {% endfor %}
            </table>
            {% else %}
            <p style="color: #28a745;">✓ All websites are up to date!</p>
            {% endif %}
        </div>
        
        <div class="section">
            <h2>🤖 Automatic Re-scraping</h2>
            <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px; margin-bottom: 10px;">
                <p><strong>Status:</strong> 
                    {% if auto_status.enabled %}
                        <span style="color: #28a745;">✓ ENABLED</span>
                    {% else %}
                        <span style="color: #ffc107;">⊗ DISABLED</span>
                    {% endif %}
                </p>
                <p><strong>Schedule:</strong> Every {{ auto_status.interval_days }} days</p>
                {% if auto_status.next_run %}
                <p><strong>Next Run:</strong> {{ auto_status.next_run }}</p>
                {% endif %}
                {% if auto_status.last_run %}
                <p><strong>Last Run:</strong> {{ auto_status.last_run }}</p>
                {% endif %}
            </div>
            <p style="font-size: 0.9em; color: rgba(255,255,255,0.7);">
                ℹ️ Automatic re-scraping runs in the background while the admin dashboard is running.
                To enable/disable or change settings, edit <code>config.py</code> and restart the dashboard.
            </p>
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
        
        async function rescrape(url, websiteId) {
            if (!confirm('Re-scrape ' + url + '?\n\nThis will find and process only NEW images (smart merge).')) return;
            const res = await fetch('/api/rescrape_website', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({url, website_id: websiteId})
            });
            const data = await res.json();
            if (data.success) {
                alert(`✓ Re-scrape complete!\n\nNew images: ${data.new_images}\nNew faces: ${data.new_faces}\nTotal images: ${data.total_images}`);
                location.reload();
            } else {
                alert('✗ Error: ' + data.error);
            }
        }
        
        async function rescrapeStale() {
            if (!confirm('Update all stale websites?\n\nThis will re-scrape all websites older than {{ rescrape_days }} days.')) return;
            const res = await fetch('/api/rescrape_stale', {method: 'POST'});
            const data = await res.json();
            if (data.success) {
                alert(`✓ Batch update complete!\n\nWebsites updated: ${data.updated_count}\nNew images: ${data.new_images}\nNew faces: ${data.new_faces}`);
                location.reload();
            } else {
                alert('✗ Error: ' + data.error);
            }
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
    
    # Get stale websites
    stale_websites = db.get_stale_websites(days=config.RESCRAPE_AFTER_DAYS)
    
    return render_template_string(DASHBOARD_TEMPLATE, 
                                 websites=websites, 
                                 stale_websites=stale_websites,
                                 rescrape_days=config.RESCRAPE_AFTER_DAYS,
                                 auto_status=auto_rescrape_status)


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


def perform_rescrape(website_id: int, url: str) -> dict:
    """
    Internal function to perform re-scraping of a website.
    
    Args:
        website_id: Database ID of the website
        url: Website URL
        
    Returns:
        Dictionary with 'success', 'new_images', 'new_faces', 'total_images'
    """
    try:
        # Import here to avoid circular imports
        from main_pipeline import process_website
        from scraper import WebScraper
        from face_processor import FaceProcessor
        
        # Track before state
        old_image_count = db.get_website_image_count(website_id)
        old_stats = db.get_statistics()
        old_face_count = old_stats.get('active_faces', 0)
        
        # Process website (smart merge will filter existing images)
        scraper = WebScraper(headless=True)
        face_proc = FaceProcessor()
        process_website(url, db, faiss_mgr, face_proc, scraper)
        
        # Track after state
        new_image_count = db.get_website_image_count(website_id)
        new_stats = db.get_statistics()
        new_face_count = new_stats.get('active_faces', 0)
        
        # Calculate deltas
        new_images = new_image_count - old_image_count
        new_faces = new_face_count - old_face_count
        
        return {
            'success': True,
            'new_images': new_images,
            'new_faces': new_faces,
            'total_images': new_image_count
        }
    except Exception as e:
        logger.exception("Error in perform_rescrape")
        return {
            'success': False,
            'error': str(e)
        }


@app.route('/api/rescrape_website', methods=['POST'])
def rescrape_website():
    """
    Re-scrape a specific website with smart merge (only new images).
    """
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        website_id = data.get('website_id')
        
        if not url or not website_id:
            return jsonify({'success': False, 'error': 'url and website_id required'}), 400
        
        scraping_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ♻️ Re-scraping: {url}")
        
        result = perform_rescrape(website_id, url)
        
        if result['success']:
            scraping_logs.append(
                f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Re-scrape complete: "
                f"+{result['new_images']} images, +{result['new_faces']} faces"
            )
        else:
            scraping_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ Re-scrape failed: {result['error']}")
        
        return jsonify(result)
    except Exception as e:
        logger.exception("Error re-scraping website")
        scraping_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ Re-scrape failed: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/rescrape_stale', methods=['POST'])
def rescrape_stale():
    """
    Batch re-scrape all stale websites.
    """
    try:
        # Get stale websites
        stale_websites = db.get_stale_websites(days=config.RESCRAPE_AFTER_DAYS)
        
        if not stale_websites:
            return jsonify({'success': True, 'updated_count': 0, 'new_images': 0, 'new_faces': 0})
        
        scraping_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ♻️ Batch update: {len(stale_websites)} websites")
        
        # Track totals
        total_new_images = 0
        total_new_faces = 0
        updated_count = 0
        
        # Process each stale website
        for website in stale_websites:
            try:
                scraping_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Processing: {website['url']}")
                
                # Use perform_rescrape helper function
                result = perform_rescrape(website['id'], website['url'])
                
                if result['success']:
                    total_new_images += result.get('new_images', 0)
                    total_new_faces += result.get('new_faces', 0)
                    updated_count += 1
                    
                    scraping_logs.append(
                        f"[{datetime.now().strftime('%H:%M:%S')}] ✓ {website['url']}: "
                        f"+{result['new_images']} images, +{result['new_faces']} faces"
                    )
                else:
                    logger.error("Failed to re-scrape %s: %s", website['url'], result.get('error'))
                    scraping_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ Failed: {website['url']}")
                    
            except Exception as e:
                logger.exception("Failed to re-scrape %s", website['url'])
                scraping_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ Failed: {website['url']}")
        
        scraping_logs.append(
            f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Batch complete: "
            f"{updated_count} websites, +{total_new_images} images, +{total_new_faces} faces"
        )
        
        return jsonify({
            'success': True,
            'updated_count': updated_count,
            'new_images': total_new_images,
            'new_faces': total_new_faces
        })
    except Exception as e:
        logger.exception("Error in batch re-scrape")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/status')
def status():
    """Get current scraping status and logs."""
    return jsonify({
        'jobs': scraping_jobs,
        'logs': scraping_logs[-100:]  # Last 100 log entries
    })


def scheduled_rescrape():
    """Automatic re-scraping job that runs on schedule."""
    try:
        logger.info("Starting scheduled automatic re-scrape...")
        auto_rescrape_status['last_run'] = datetime.now().isoformat()
        
        # Get all websites from database
        websites = db.get_all_websites()
        if not websites:
            logger.info("No websites found for scheduled re-scrape")
            return
        
        total_new_images = 0
        total_new_faces = 0
        
        # Import here to avoid circular imports
        from main_pipeline import process_website
        from scraper import WebScraper
        from face_processor import FaceProcessor
        
        scraper = WebScraper(headless=True)
        face_proc = FaceProcessor()
        
        for website in websites:
            website_id = website[0]
            url = website[1]
            
            try:
                scraping_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 🤖 Auto re-scrape: {url}")
                
                # Track before state
                old_image_count = db.get_website_image_count(website_id)
                old_stats = db.get_statistics()
                old_face_count = old_stats.get('active_faces', 0)
                
                # Process website (smart merge will filter existing images)
                process_website(url, db, faiss_mgr, face_proc, scraper)
                
                # Track after state
                new_image_count = db.get_website_image_count(website_id)
                new_stats = db.get_statistics()
                new_face_count = new_stats.get('active_faces', 0)
                
                # Calculate deltas
                new_images = new_image_count - old_image_count
                new_faces = new_face_count - old_face_count
                
                total_new_images += new_images
                total_new_faces += new_faces
                
                scraping_logs.append(
                    f"[{datetime.now().strftime('%H:%M:%S')}] ✓ {url}: "
                    f"+{new_images} images, +{new_faces} faces"
                )
                
            except Exception as e:
                logger.error("Error in scheduled re-scrape of %s: %s", url, str(e))
                scraping_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ Failed: {url}")
        
        logger.info("Scheduled re-scrape completed: %d total new images, %d total new faces", 
                   total_new_images, total_new_faces)
        
        # Update next run time
        update_next_run_time()
        
    except Exception as e:
        logger.exception("Error in scheduled_rescrape: %s", str(e))


def update_next_run_time():
    """Update the next scheduled run time."""
    jobs = scheduler.get_jobs()
    if jobs:
        auto_rescrape_status['next_run'] = jobs[0].next_run_time.isoformat() if jobs[0].next_run_time else None


def setup_scheduler():
    """Setup the APScheduler with configured schedule."""
    if not config.AUTO_RESCRAPE_ENABLED:
        logger.info("Auto re-scraping is disabled in config")
        return
    
    # Parse time from config (format: "23:00" for 11 PM)
    hour, minute = map(int, config.AUTO_RESCRAPE_TIME.split(':'))
    
    # Calculate day of week for bi-weekly schedule
    # Run every 14 days starting from a reference date
    trigger = CronTrigger(
        day_of_week='*',  # Every day (but we'll use interval to make it every 14 days)
        hour=hour,
        minute=minute
    )
    
    # For bi-weekly, we'll use interval trigger instead
    from apscheduler.triggers.interval import IntervalTrigger
    trigger = IntervalTrigger(
        days=config.AUTO_RESCRAPE_INTERVAL_DAYS,
        start_date=datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
    )
    
    scheduler.add_job(
        func=scheduled_rescrape,
        trigger=trigger,
        id='auto_rescrape',
        name='Automatic Website Re-scraping',
        replace_existing=True
    )
    
    update_next_run_time()
    logger.info("Scheduled auto re-scraping: every %d days at %s", 
               config.AUTO_RESCRAPE_INTERVAL_DAYS, config.AUTO_RESCRAPE_TIME)
    logger.info("Next run: %s", auto_rescrape_status['next_run'])


# Existing scraping functions

if __name__ == '__main__':
    print("\n" + "="*70)
    print("ADMIN DASHBOARD - PRIVACY EXPOSURE CHECKER")
    print("="*70)
    print("Starting web interface...")
    print("Access at: http://localhost:5001")
    
    # Setup automatic re-scraping scheduler
    setup_scheduler()
    
    if auto_rescrape_status['enabled']:
        print(f"Auto re-scraping: ENABLED (every {auto_rescrape_status['interval_days']} days)")
        if auto_rescrape_status['next_run']:
            print(f"Next run: {auto_rescrape_status['next_run']}")
    else:
        print("Auto re-scraping: DISABLED")
    
    print("="*70 + "\n")
    
    try:
        app.run(host='0.0.0.0', port=5001, debug=False)
    finally:
        # Shutdown scheduler on exit
        scheduler.shutdown()
