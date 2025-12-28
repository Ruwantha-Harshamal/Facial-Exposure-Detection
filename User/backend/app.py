"""
app.py

Flask backend for Privacy Exposure Checker
Handles user photo uploads and face search
"""

import os
import sys
import logging
from flask import Flask, request, jsonify, send_from_directory, send_file
from werkzeug.utils import secure_filename
import uuid
from io import BytesIO

# Add parent directory to path to import admin backend modules
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.append(PROJECT_ROOT)

# Import config and update paths to be absolute
import config

# Make sure all database and FAISS paths are absolute
if hasattr(config, 'SQLITE_DB_PATH') and not os.path.isabs(config.SQLITE_DB_PATH):
    config.SQLITE_DB_PATH = os.path.join(PROJECT_ROOT, config.SQLITE_DB_PATH)

if hasattr(config, 'FAISS_INDEX_PATH') and not os.path.isabs(config.FAISS_INDEX_PATH):
    config.FAISS_INDEX_PATH = os.path.join(PROJECT_ROOT, config.FAISS_INDEX_PATH)

# Import backend modules
from face_processor import FaceProcessor
from faiss_manager import FAISSManager
from database_manager import DatabaseManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, 
            static_folder='../frontend',
            template_folder='../frontend')

# Configuration
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BACKEND_DIR, 'uploads')
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize components (shared with admin backend)
logger.info("Initializing components...")
db = DatabaseManager(db_path=config.SQLITE_DB_PATH, db_type=config.DB_TYPE)
logger.info("Database path: %s", config.SQLITE_DB_PATH)
faiss_mgr = FAISSManager()
face_proc = FaceProcessor()
logger.info("✓ All components ready")


@app.before_request
def log_request_info():
    """Log every request for debugging"""
    logger.info('REQUEST: %s %s', request.method, request.path)


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Serve the home page"""
    return send_from_directory('../frontend', 'index.html')


@app.route('/about.html')
def about():
    """Serve the about page"""
    return send_from_directory('../frontend', 'about.html')


@app.route('/css/<path:filename>')
def serve_css(filename):
    """Serve CSS files"""
    return send_from_directory('../frontend/css', filename)


@app.route('/js/<path:filename>')
def serve_js(filename):
    """Serve JavaScript files"""
    return send_from_directory('../frontend/js', filename)


@app.route('/api/stats')
def get_stats():
    """Get database statistics"""
    try:
        stats = db.get_statistics()
        return jsonify({
            'success': True,
            'stats': {
                'total_faces': stats.get('active_faces', 0),
                'total_websites': stats.get('active_websites', 0),
                'total_images': stats.get('active_images', 0)
            }
        })
    except (KeyError, AttributeError, TypeError) as e:
        logger.error("Error getting stats: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/upload', methods=['POST'])
def upload():
    """
    Handle user photo upload and face search
    
    Process:
    1. Receive photo from user
    2. Detect face using MTCNN
    3. Generate embedding using FaceNet
    4. Search FAISS for similar faces
    5. Query database for match details
    6. Delete user's photo (privacy!)
    7. Return results
    """
    logger.info("=" * 70)
    logger.info("NEW UPLOAD REQUEST")
    logger.info("=" * 70)
    
    # Check if file was uploaded
    if 'photo' not in request.files:
        return jsonify({'success': False, 'error': 'No photo uploaded'}), 400
    
    file = request.files['photo']
    
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Empty filename'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'Invalid file type. Only JPG, JPEG, PNG allowed'}), 400
    
    # Save to temporary file
    filename = secure_filename(f"{uuid.uuid4()}.jpg")
    temp_path = os.path.join(UPLOAD_FOLDER, filename)
    
    try:
        file.save(temp_path)
        logger.info("Saved temp file: %s", temp_path)
        
        # Load photo into RAM
        with open(temp_path, 'rb') as f:
            photo_bytes = f.read()
        
        # Detect face using MTCNN (same as admin backend)
        logger.info("Detecting face...")
        face_results = face_proc.process_image_bytes(photo_bytes, "user_upload")
        
        logger.info("Face detection returned %d results", len(face_results) if face_results else 0)
        
        if not face_results or len(face_results) == 0:
            os.remove(temp_path)  # Delete temp file
            return jsonify({
                'success': False,
                'error': 'No face detected in photo. Please upload a clear photo with a visible face.'
            }), 400
        
        # Get the best face (highest confidence)
        try:
            # Log the structure of face_results for debugging
            first_len = len(face_results[0]) if hasattr(face_results[0], '__len__') else 'unknown'
            logger.info("First face result structure: %s with %s elements", type(face_results[0]), first_len)
            
            faces = sorted(face_results, key=lambda x: x[1], reverse=True)
            
            if not faces or len(faces) == 0:
                logger.error("Sorting resulted in empty list")
                os.remove(temp_path)
                return jsonify({
                    'success': False,
                    'error': 'No valid faces after sorting'
                }), 400
            
            face_data = faces[0]
            logger.info("Face data has %d elements", len(face_data))
            
            if len(face_data) != 4:
                logger.error("Unexpected face data format: expected 4 elements, got %d", len(face_data))
                os.remove(temp_path)
                return jsonify({
                    'success': False,
                    'error': 'Internal error: Invalid face data format'
                }), 500
            
            _bbox, confidence, _thumbnail_bytes, user_embedding = face_data
            
        except (IndexError, ValueError, TypeError) as e:
            logger.error("Error processing face data: %s", e, exc_info=True)
            os.remove(temp_path)
            return jsonify({
                'success': False,
                'error': f'Internal error processing face data: {str(e)}'
            }), 500
        
        logger.info("Face detected with %.2f%% confidence", confidence * 100)
        
        # Search FAISS for similar faces
        logger.info("Searching database...")
        
        # Check if we have vectors in FAISS
        total_vectors = faiss_mgr.get_total_vectors()
        logger.info("FAISS has %d vectors", total_vectors)
        
        if total_vectors == 0:
            logger.warning("No vectors in FAISS index")
            os.remove(temp_path)
            return jsonify({
                'success': True,
                'status': 'safe',
                'message': 'Good news! Your face was NOT found in our database.',
                'matches': [],
                'total_searched': 0
            })
        
        k = min(50, total_vectors)  # Search top 50 or less if database is small
        logger.info("Searching for top %d similar faces...", k)
        
        # Note: faiss_mgr.search() returns (similarities_list, face_ids_list)
        # NOT nested arrays - they're already filtered and flattened
        similarities, face_ids = faiss_mgr.search(user_embedding, k=k, threshold=0.60)
        
        # Check if search returned results
        if not similarities or not face_ids or len(similarities) == 0 or len(face_ids) == 0:
            logger.info("No matches found above similarity threshold")
            os.remove(temp_path)
            return jsonify({
                'success': True,
                'status': 'safe',
                'message': 'Good news! Your face was NOT found in our database.',
                'matches': [],
                'total_searched': total_vectors
            })
        
        logger.info("Search returned %d matches above threshold", len(similarities))
        
        # Build matches list
        matches = []
        
        for similarity, face_id in zip(similarities, face_ids):
            logger.info("Checking face_id %d with similarity %.2f%%", face_id, similarity * 100)
            
            # Query database for face details
            cursor = db.conn.cursor()
            cursor.execute("""
                SELECT 
                    f.id as face_id,
                    f.confidence as detection_confidence,
                    i.image_url,
                    i.scraped_at,
                    w.url as website_url,
                    w.name as website_name
                FROM faces f
                JOIN images i ON f.image_id = i.id
                JOIN websites w ON i.website_id = w.id
                WHERE f.id = ? AND f.deleted_at IS NULL
            """, (int(face_id),))
            
            row = cursor.fetchone()
            if row:
                matches.append({
                    'face_id': row[0],
                    'similarity': float(similarity),
                    'percentage': f"{similarity * 100:.1f}%",
                    'detection_confidence': row[1],
                    'image_url': row[2],
                    'scraped_at': row[3],
                    'website_url': row[4],
                    'website_name': row[5] or row[4]
                })
        
        # Delete user's photo (PRIVACY!)
        os.remove(temp_path)
        logger.info("✓ Deleted temp file: %s", temp_path)
        
        # Log results
        logger.info("Found %d database matches", len(matches))
        logger.info("=" * 70)
        
        # Return results
        if len(matches) == 0:
            return jsonify({
                'success': True,
                'status': 'safe',
                'message': 'Good news! Your face was NOT found in our database.',
                'matches': [],
                'total_searched': faiss_mgr.get_total_vectors()
            })
        else:
            return jsonify({
                'success': True,
                'status': 'exposed',
                'message': f'Your face was found in {len(matches)} location(s).',
                'matches': matches,
                'total_searched': faiss_mgr.get_total_vectors()
            })
    
    except (IOError, OSError, RuntimeError) as e:
        # Clean up temp file on error
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        logger.error("Error processing upload: %s", e, exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Processing error: {str(e)}'
        }), 500


@app.route('/api/thumbnail/<int:face_id>')
def get_thumbnail(face_id):
    """Serve face thumbnail from database"""
    try:
        cursor = db.conn.cursor()
        cursor.execute("""
            SELECT thumbnail_blob 
            FROM face_thumbnails 
            WHERE face_id = ?
        """, (face_id,))
        
        row = cursor.fetchone()
        if row:
            return send_file(
                BytesIO(row[0]),
                mimetype='image/jpeg',
                as_attachment=False
            )
        else:
            return jsonify({'error': 'Thumbnail not found'}), 404
    
    except (IOError, OSError) as e:
        logger.error("Error serving thumbnail: %s", e)
        return jsonify({'error': str(e)}), 500


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'database': 'connected' if db.conn else 'disconnected',
        'faiss_vectors': faiss_mgr.get_total_vectors()
    })


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("PRIVACY EXPOSURE CHECKER - BACKEND SERVER")
    print("=" * 70)
    print(f"Database: {config.DB_TYPE}")
    print(f"Faces indexed: {faiss_mgr.get_total_vectors()}")
    print("Server starting at: http://localhost:5000")
    print("=" * 70 + "\n")
    
    # Run Flask server
    app.run(
        host='0.0.0.0',  # Accessible from network
        port=5000,
        debug=True  # Set to False in production
    )
