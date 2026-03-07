# ⚙️ Configuration Guide - Privacy Exposure Checker

## 📋 Quick Configuration Reference

### 1️⃣ **config.py - Main Configuration**

```python
# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================
DB_TYPE = 'sqlite'  # Options: 'sqlite' or 'postgresql'
SQLITE_DB_PATH = 'face_recognition.db'  # SQLite database file path

# PostgreSQL Configuration (if DB_TYPE = 'postgresql')
POSTGRES_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'face_recognition',
    'user': 'postgres',
    'password': 'your_password'
}

# ============================================================================
# FACE DETECTION & RECOGNITION
# ============================================================================

# MTCNN Face Detection
FACE_DETECTION_CONFIDENCE = 0.9  # Minimum confidence (0.0-1.0)
                                 # Higher = stricter (fewer false positives)
                                 # Lower = more faces detected

MIN_FACE_SIZE = 20  # Minimum face size in pixels
                    # Smaller = detect tiny faces (slower)
                    # Larger = skip small faces (faster)

# FaceNet Embeddings
EMBEDDING_DIMENSION = 512  # FaceNet output dimension (DO NOT CHANGE)
SIMILARITY_THRESHOLD = 0.6  # Face matching threshold (0.0-1.0)
                            # Lower = stricter matching
                            # Higher = more lenient

# ============================================================================
# WEB SCRAPING
# ============================================================================

# Scraping Limits
MAX_IMAGES_PER_WEBSITE = 1000  # Maximum images to scrape per site
                               # Prevents infinite scraping

SCRAPING_TIMEOUT = 30  # Timeout in seconds for page load
                       # Increase for slow websites

# Browser Configuration
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
HEADLESS_BROWSER = True  # Run browser in background (no window)

# Image Validation
MIN_IMAGE_SIZE = 50  # Minimum image dimension (width or height)
MAX_IMAGE_SIZE_MB = 10  # Maximum image file size in MB

# ============================================================================
# AUTOMATIC RE-SCRAPING
# ============================================================================

AUTO_RESCRAPE_ENABLED = True  # Enable/disable automatic re-scraping
AUTO_RESCRAPE_INTERVAL_DAYS = 14  # Re-scrape interval (days)
AUTO_RESCRAPE_TIME = '23:00'  # Daily check time (24-hour format)
RESCRAPE_AFTER_DAYS = 30  # Mark websites as "stale" after X days

# Schedule Examples:
# Daily at 2 AM:     AUTO_RESCRAPE_TIME = '02:00'
# Daily at 11 PM:    AUTO_RESCRAPE_TIME = '23:00'
# Daily at midnight: AUTO_RESCRAPE_TIME = '00:00'

# ============================================================================
# FAISS VECTOR INDEX
# ============================================================================

FAISS_INDEX_PATH = 'faiss_index.bin'  # FAISS index file path
FAISS_INDEX_TYPE = 'IndexFlatL2'  # Index type (L2 distance)
TOP_K_RESULTS = 10  # Number of similar faces to return

# ============================================================================
# ADMIN DASHBOARD
# ============================================================================

ADMIN_HOST = '0.0.0.0'  # Listen on all interfaces
ADMIN_PORT = 5001  # Dashboard port

# Rate Limiting
RATE_LIMIT_ENABLED = True
RATE_LIMIT_PER_DAY = 1000  # Requests per day
RATE_LIMIT_PER_HOUR = 100  # Requests per hour

# ============================================================================
# LOGGING
# ============================================================================

LOG_LEVEL = 'INFO'  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE = None  # Log file path (None = console only)

# ============================================================================
# SECURITY
# ============================================================================

# Set in .env file (DO NOT commit to git)
# ADMIN_SECRET_KEY=your-secret-key-here
```

---

## 2️⃣ **.env - Environment Variables**

Create a `.env` file in the project root:

```bash
# ============================================================================
# SECURITY (REQUIRED)
# ============================================================================
ADMIN_SECRET_KEY=your-super-secret-key-change-this-in-production

# Generate a secure key with:
# python -c "import secrets; print(secrets.token_hex(32))"

# ============================================================================
# DATABASE (Optional - for PostgreSQL)
# ============================================================================
DATABASE_URL=postgresql://user:password@localhost:5432/face_recognition

# ============================================================================
# SELENIUM (Optional)
# ============================================================================
CHROME_DRIVER_PATH=/path/to/chromedriver
# Leave empty for auto-download

# ============================================================================
# API KEYS (Optional)
# ============================================================================
# Add any external API keys here
```

---

## 3️⃣ **requirements.txt - Dependencies**

Current dependencies:

```txt
# Core Framework
Flask==3.0.0
Werkzeug==3.0.1

# Rate Limiting & Security
Flask-Limiter==3.5.0
Flask-CORS==4.0.0
Flask-Talisman==1.1.0

# Job Scheduling
APScheduler==3.10.4

# Environment Variables
python-dotenv>=1.0.0

# Image Processing
numpy>=1.24.0
Pillow>=10.0.0

# Web Scraping
requests>=2.31.0
selenium>=4.15.0

# Face Detection & Recognition
mtcnn>=0.1.1
keras-facenet>=0.3.2
tensorflow>=2.14.0

# Vector Search
faiss-cpu>=1.7.4

# Database
psycopg2-binary>=2.9.9  # For PostgreSQL
python-dateutil>=2.8.2
```

---

## 4️⃣ **Configuration Best Practices**

### 🔒 **Security**
```python
✅ DO:
- Set ADMIN_SECRET_KEY in .env file
- Use strong, random secret keys
- Enable rate limiting in production
- Use HTTPS in production (Flask-Talisman)

❌ DON'T:
- Commit .env file to git
- Use default/weak secret keys
- Disable rate limiting in production
- Expose database credentials
```

### ⚡ **Performance**
```python
✅ Optimize for Speed:
- FACE_DETECTION_CONFIDENCE = 0.95  # Higher = faster
- MIN_FACE_SIZE = 30  # Larger = faster
- MAX_IMAGES_PER_WEBSITE = 500  # Lower = faster
- HEADLESS_BROWSER = True  # Faster scraping

✅ Optimize for Quality:
- FACE_DETECTION_CONFIDENCE = 0.85  # Lower = more faces
- MIN_FACE_SIZE = 15  # Smaller = detect tiny faces
- MAX_IMAGES_PER_WEBSITE = 2000  # Higher = more data
- SIMILARITY_THRESHOLD = 0.5  # Lower = stricter matching
```

### 💾 **Storage**
```python
✅ Reduce Storage:
- Use PostgreSQL (better than SQLite for large data)
- Set MAX_IMAGES_PER_WEBSITE = 500
- Regularly clean old/stale data

✅ Maximize Data:
- Use SQLite (simpler setup)
- Set MAX_IMAGES_PER_WEBSITE = 2000
- Enable AUTO_RESCRAPE for updates
```

---

## 5️⃣ **Configuration Examples**

### 🏠 **Home/Personal Use**
```python
# config.py
DB_TYPE = 'sqlite'
FACE_DETECTION_CONFIDENCE = 0.9
MAX_IMAGES_PER_WEBSITE = 1000
AUTO_RESCRAPE_ENABLED = True
AUTO_RESCRAPE_INTERVAL_DAYS = 30
HEADLESS_BROWSER = True
```

### 🏢 **Production/Enterprise**
```python
# config.py
DB_TYPE = 'postgresql'
FACE_DETECTION_CONFIDENCE = 0.95
MAX_IMAGES_PER_WEBSITE = 500
AUTO_RESCRAPE_ENABLED = True
AUTO_RESCRAPE_INTERVAL_DAYS = 7
HEADLESS_BROWSER = True
RATE_LIMIT_ENABLED = True

# .env
ADMIN_SECRET_KEY=<strong-random-key>
DATABASE_URL=postgresql://user:pass@db-server:5432/prod_db
```

### 🧪 **Development/Testing**
```python
# config.py
DB_TYPE = 'sqlite'
FACE_DETECTION_CONFIDENCE = 0.8  # Lower for testing
MAX_IMAGES_PER_WEBSITE = 100  # Small for quick tests
AUTO_RESCRAPE_ENABLED = False  # Disable in dev
HEADLESS_BROWSER = False  # See browser for debugging
LOG_LEVEL = 'DEBUG'
```

---

## 6️⃣ **Configuration Validation**

Run this script to validate your configuration:

```python
# validate_config.py
import config
import os

print("🔍 Validating Configuration...")

# Check required settings
checks = {
    "Database Type": config.DB_TYPE in ['sqlite', 'postgresql'],
    "Face Confidence": 0.0 <= config.FACE_DETECTION_CONFIDENCE <= 1.0,
    "Min Face Size": config.MIN_FACE_SIZE > 0,
    "Max Images": config.MAX_IMAGES_PER_WEBSITE > 0,
    "FAISS Path": isinstance(config.FAISS_INDEX_PATH, str),
}

# Check .env file
if not os.path.exists('.env'):
    print("⚠️  WARNING: .env file not found!")
    print("   Create .env with: ADMIN_SECRET_KEY=<your-key>")

# Print results
for check, passed in checks.items():
    status = "✅" if passed else "❌"
    print(f"{status} {check}")

if all(checks.values()):
    print("\n✅ Configuration is valid!")
else:
    print("\n❌ Configuration has errors!")
```

---

## 7️⃣ **Quick Setup Commands**

```bash
# 1. Create .env file
echo "ADMIN_SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')" > .env

# 2. Install dependencies
pip install -r requirements.txt

# 3. Validate configuration
python validate_config.py

# 4. Run admin dashboard
python run_admin.py
```

---

## 8️⃣ **Troubleshooting Configuration**

### **Issue: "Module not found" errors**
```bash
# Solution: Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### **Issue: "Database locked" errors**
```python
# Solution: Switch to PostgreSQL
DB_TYPE = 'postgresql'  # in config.py
```

### **Issue: Slow scraping**
```python
# Solution: Optimize settings
MAX_IMAGES_PER_WEBSITE = 500  # Reduce limit
SCRAPING_TIMEOUT = 15  # Reduce timeout
HEADLESS_BROWSER = True  # Enable headless
```

### **Issue: Not detecting faces**
```python
# Solution: Lower confidence threshold
FACE_DETECTION_CONFIDENCE = 0.8  # Lower from 0.9
MIN_FACE_SIZE = 15  # Reduce from 20
```

---

## 📝 **Configuration Checklist**

Before running the system:

- [ ] Installed all dependencies (`pip install -r requirements.txt`)
- [ ] Created `.env` file with `ADMIN_SECRET_KEY`
- [ ] Reviewed `config.py` settings
- [ ] Adjusted `FACE_DETECTION_CONFIDENCE` if needed
- [ ] Set appropriate `MAX_IMAGES_PER_WEBSITE`
- [ ] Configured `AUTO_RESCRAPE` settings
- [ ] Checked database type (SQLite vs PostgreSQL)
- [ ] Validated configuration (run `validate_config.py`)
- [ ] Ready to start! (`python run_admin.py`)

---

**Last Updated:** March 7, 2026  
**Version:** 3.0
