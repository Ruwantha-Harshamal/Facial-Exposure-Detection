"""
config.py

Configuration settings for OSINT Face Recognition System
"""

import os

# ═══════════════════════════════════════════════════════════
#  DATABASE CONFIGURATION
# ═══════════════════════════════════════════════════════════

# Database type: 'sqlite' or 'postgresql'
DB_TYPE = os.getenv('DB_TYPE', 'sqlite')

# SQLite configuration
SQLITE_DB_PATH = os.getenv('SQLITE_DB_PATH', 'face_recognition.db')

# PostgreSQL configuration
# SECURITY: No default credentials - must be set via environment variables
_postgres_user = os.getenv('POSTGRES_USER')
_postgres_password = os.getenv('POSTGRES_PASSWORD')

if DB_TYPE == 'postgresql':
    if not _postgres_user or not _postgres_password:
        raise ValueError(
            "SECURITY ERROR: PostgreSQL credentials must be set via environment variables!\n"
            "Set POSTGRES_USER and POSTGRES_PASSWORD before running.\n"
            "Never use default credentials in production."
        )

POSTGRES_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', '5432')),
    'database': os.getenv('POSTGRES_DB', 'face_recognition'),
    'user': _postgres_user,
    'password': _postgres_password,
}

# ═══════════════════════════════════════════════════════════
#  FACE DETECTION CONFIGURATION
# ═══════════════════════════════════════════════════════════

# Minimum confidence threshold for face detection (0.0 - 1.0)
MIN_FACE_CONFIDENCE = float(os.getenv('MIN_FACE_CONFIDENCE', '0.90'))

# Thumbnail size (width, height) in pixels
THUMBNAIL_SIZE = (144, 144)  # Optimized for avatar display

# JPEG quality for thumbnails (1-100)
THUMBNAIL_QUALITY = 85

# Face detector: 'mtcnn' (only MTCNN supported currently)
FACE_DETECTOR = 'mtcnn'

# ═══════════════════════════════════════════════════════════
#  EMBEDDING CONFIGURATION
# ═══════════════════════════════════════════════════════════

# Embedding model: 'facenet' (only FaceNet supported currently)
EMBEDDING_MODEL = 'facenet'

# Embedding dimensions
EMBEDDING_DIMENSIONS = 512  # FaceNet produces 512-dimensional embeddings

# ═══════════════════════════════════════════════════════════
#  FAISS CONFIGURATION
# ═══════════════════════════════════════════════════════════

# FAISS index file path
FAISS_INDEX_PATH = os.getenv('FAISS_INDEX_PATH', 'faiss_index.bin')

# FAISS index type: 'flat' (exact) or 'ivf' (approximate)
FAISS_INDEX_TYPE = os.getenv('FAISS_INDEX_TYPE', 'flat')

# For IVF index: number of clusters
FAISS_IVF_CLUSTERS = int(os.getenv('FAISS_IVF_CLUSTERS', '100'))

# Distance metric: 'L2' (Euclidean) or 'IP' (cosine similarity)
FAISS_METRIC = os.getenv('FAISS_METRIC', 'L2')

# ═══════════════════════════════════════════════════════════
#  SCRAPING CONFIGURATION
# ═══════════════════════════════════════════════════════════

# Maximum concurrent download workers
MAX_WORKERS = int(os.getenv('MAX_WORKERS', '5'))

# Minimum seconds between requests to same domain
RATE_LIMIT_SECONDS = float(os.getenv('RATE_LIMIT_SECONDS', '0.2'))

# Seconds to wait for JavaScript to load page
PAGE_LOAD_WAIT_SECONDS = int(os.getenv('PAGE_LOAD_WAIT_SECONDS', '5'))

# Number of progressive scrolls to trigger lazy-loading
# Higher = more images found, but slower scraping
# Recommended: 3-5 for balance, 8-10 for maximum coverage
SCROLL_COUNT = int(os.getenv('SCROLL_COUNT', '5'))

# Delay between scrolls (seconds) - wait for lazy images to load
SCROLL_DELAY = float(os.getenv('SCROLL_DELAY', '1.5'))

# Run browser in headless mode
HEADLESS_BROWSER = os.getenv('HEADLESS_BROWSER', 'true').lower() == 'true'

# User agent string
USER_AGENT = "OSINT-Privacy-Scanner/2.0 (+https://github.com/privacy-scanner)"

# Request timeout in seconds
REQUEST_TIMEOUT = 20

# ═══════════════════════════════════════════════════════════
#  ADVANCED IMAGE DETECTION (Chrome Extension Techniques)
# ═══════════════════════════════════════════════════════════

# Enable CSS background-image detection (scans all elements)
# Adds 2-3s per page but finds 20-30% more images
DETECT_CSS_BACKGROUNDS = os.getenv('DETECT_CSS_BACKGROUNDS', 'true').lower() == 'true'

# Enable link-to-image detection (<a href="image.jpg">)
# Adds ~1s per page, finds 5-10% more (often higher resolution)
DETECT_LINKED_IMAGES = os.getenv('DETECT_LINKED_IMAGES', 'true').lower() == 'true'

# Enable SVG image detection
# Adds ~0.5s per page, finds 2-5% more (mostly logos/icons)
DETECT_SVG_IMAGES = os.getenv('DETECT_SVG_IMAGES', 'true').lower() == 'true'

# Image URL validation regex (based on Chrome Image Downloader extension)
IMAGE_URL_PATTERN = r'(?:([^:\/?#]+):)?(?:\/\/([^\/?#]*))?([^?#]*\.(?:bmp|gif|ico|jfif|jpe?g|png|svg|tiff?|webp|avif))(?:\?([^#]*))?(?:#(.*))?'

# ═══════════════════════════════════════════════════════════
#  LOGGING CONFIGURATION
# ═══════════════════════════════════════════════════════════

# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Log format
LOG_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'

# ═══════════════════════════════════════════════════════════
#  SEARCH CONFIGURATION
# ═══════════════════════════════════════════════════════════

# Default number of search results to return
DEFAULT_SEARCH_RESULTS = 50

# Minimum similarity threshold for matches (0.0 - 1.0)
# Higher = more strict matching
# Default 0.60 = L2 distance of ~0.8 (good balance for same person)
# Lower values (0.40-0.50) include more matches but increase false positives
MIN_SIMILARITY_THRESHOLD = float(os.getenv('MIN_SIMILARITY_THRESHOLD', '0.60'))

# ═══════════════════════════════════════════════════════════
#  CLUSTERING CONFIGURATION
# ═══════════════════════════════════════════════════════════

# Face matching threshold for clustering (0.0 - 1.0)
# Lower = stricter matching (faces must be more similar)
# Default 0.6 is a good balance for grouping same person
FACE_MATCH_THRESHOLD = float(os.getenv('FACE_MATCH_THRESHOLD', '0.6'))

# Minimum number of faces to form a cluster
MIN_CLUSTER_SIZE = int(os.getenv('MIN_CLUSTER_SIZE', '2'))
