# 🔄 Privacy Exposure Checker - Complete Project Flow

## 📋 Table of Contents
1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Setup & Configuration](#setup--configuration)
4. [End-to-End Flow](#end-to-end-flow)
5. [Component Details](#component-details)
6. [Data Flow](#data-flow)
7. [API Endpoints](#api-endpoints)
8. [Troubleshooting](#troubleshooting)

---

## 🎯 System Overview

**Purpose:** Detect and track facial exposure across websites by scraping images, detecting faces, and creating a searchable database.

**Key Features:**
- Web scraping with intelligent image extraction
- Face detection using MTCNN
- Face embedding generation using FaceNet
- Vector similarity search using FAISS
- Database-driven with smart merge (avoid duplicates)
- Web-based admin dashboard
- Automatic re-scraping scheduler
- User search interface

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        ADMIN DASHBOARD                          │
│                    (Flask Web Interface)                        │
│                     http://localhost:5001                       │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ├──► Add Website URLs
                  ├──► Trigger Scraping
                  ├──► View Statistics
                  ├──► Delete Websites
                  └──► Monitor Activity Log
                  │
┌─────────────────▼───────────────────────────────────────────────┐
│                      SCRAPING PIPELINE                          │
│                    (main_pipeline.py)                           │
└─────────────────┬───────────────────────────────────────────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
    ▼             ▼             ▼
┌─────────┐  ┌──────────┐  ┌──────────┐
│ Scraper │  │   Face   │  │ Database │
│ Module  │──►Processor │──►  Manager │
│         │  │ (MTCNN + │  │          │
│Selenium │  │ FaceNet) │  │ SQLite   │
└─────────┘  └──────────┘  └─────┬────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
                    ▼             ▼             ▼
            ┌─────────────┐  ┌────────┐  ┌──────────┐
            │   SQLite    │  │ FAISS  │  │  Faces   │
            │  Database   │  │ Index  │  │Thumbnails│
            │face_recog.db│  │.bin    │  │  (RAM)   │
            └─────────────┘  └────────┘  └──────────┘
```

---

## ⚙️ Setup & Configuration

### 1️⃣ **Prerequisites**
```bash
# Python 3.11 recommended
python --version

# Chrome/Chromium browser installed
# ChromeDriver (auto-managed by Selenium)
```

### 2️⃣ **Installation**
```bash
# Clone repository
git clone https://github.com/Ruwantha-Harshamal/Facial-Exposure-Detection.git
cd Facial-Exposure-Detection

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Windows CMD:
.venv\Scripts\activate.bat
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3️⃣ **Configuration**
Edit `config.py` to customize settings:

```python
# Database Configuration
DB_TYPE = 'sqlite'  # or 'postgresql'
SQLITE_DB_PATH = 'face_recognition.db'

# Face Detection Settings
FACE_DETECTION_CONFIDENCE = 0.9  # 90% confidence threshold
MIN_FACE_SIZE = 20  # Minimum face size in pixels
EMBEDDING_DIMENSION = 512  # FaceNet embedding size

# Scraping Settings
MAX_IMAGES_PER_WEBSITE = 1000  # Limit per website
SCRAPING_TIMEOUT = 30  # Seconds
USER_AGENT = 'Mozilla/5.0...'  # Browser user agent

# Automatic Re-scraping
AUTO_RESCRAPE_ENABLED = True
AUTO_RESCRAPE_INTERVAL_DAYS = 14  # Re-scrape every 14 days
AUTO_RESCRAPE_TIME = '23:00'  # 11 PM daily check
RESCRAPE_AFTER_DAYS = 30  # Mark as "stale" after 30 days

# FAISS Settings
FAISS_INDEX_PATH = 'faiss_index.bin'
SIMILARITY_THRESHOLD = 0.6  # Face matching threshold
```

### 4️⃣ **Environment Variables (Optional)**
Create `.env` file:
```bash
# Admin Dashboard Security
ADMIN_SECRET_KEY=your-secret-key-here

# Database (if using PostgreSQL)
DATABASE_URL=postgresql://user:pass@localhost/dbname

# Selenium Settings
CHROME_DRIVER_PATH=/path/to/chromedriver
```

---

## 🔄 End-to-End Flow

### **Flow Diagram**
```
START
  │
  ▼
┌────────────────────────────────────────┐
│  1. USER ADDS WEBSITE VIA DASHBOARD   │
│     • Enter URL: https://example.com   │
│     • Click "Add Website" button       │
└──────────────┬─────────────────────────┘
               │
               ▼
┌────────────────────────────────────────┐
│  2. DATABASE CHECKS FOR DUPLICATES     │
│     • Query: SELECT url WHERE url=?    │
│     • If exists: Skip / Show warning   │
│     • If new: INSERT INTO websites     │
└──────────────┬─────────────────────────┘
               │
               ▼
┌────────────────────────────────────────┐
│  3. USER TRIGGERS SCRAPING             │
│     • Click "🔄 Scrape" button         │
│     • Background thread starts         │
└──────────────┬─────────────────────────┘
               │
               ▼
┌────────────────────────────────────────┐
│  4. SCRAPER MODULE (scraper.py)        │
│     ┌────────────────────────────────┐ │
│     │ a) Launch Selenium WebDriver   │ │
│     │ b) Navigate to URL             │ │
│     │ c) Wait for page load          │ │
│     │ d) Find all <img> tags         │ │
│     │ e) Extract image URLs          │ │
│     │ f) Download images (in-memory) │ │
│     │ g) Filter valid images         │ │
│     └────────────────────────────────┘ │
└──────────────┬─────────────────────────┘
               │
               ▼
┌────────────────────────────────────────┐
│  5. SMART MERGE CHECK                  │
│     • Calculate image hash (SHA-256)   │
│     • Query: SELECT WHERE hash=?       │
│     • Skip if duplicate                │
│     • Continue if new                  │
└──────────────┬─────────────────────────┘
               │
               ▼
┌────────────────────────────────────────┐
│  6. FACE DETECTION (face_processor.py) │
│     ┌────────────────────────────────┐ │
│     │ a) Load image from memory      │ │
│     │ b) MTCNN face detection        │ │
│     │ c) Extract face bounding boxes │ │
│     │ d) Filter by confidence > 90%  │ │
│     │ e) Crop face regions           │ │
│     └────────────────────────────────┘ │
└──────────────┬─────────────────────────┘
               │
               ▼
┌────────────────────────────────────────┐
│  7. FACE EMBEDDING (FaceNet)           │
│     ┌────────────────────────────────┐ │
│     │ a) Resize face to 160x160      │ │
│     │ b) Normalize pixel values      │ │
│     │ c) FaceNet forward pass        │ │
│     │ d) Generate 512-dim embedding  │ │
│     │ e) L2 normalize vector         │ │
│     └────────────────────────────────┘ │
└──────────────┬─────────────────────────┘
               │
               ▼
┌────────────────────────────────────────┐
│  8. DATABASE STORAGE                   │
│     ┌────────────────────────────────┐ │
│     │ a) INSERT image metadata       │ │
│     │ b) INSERT face record          │ │
│     │ c) STORE embedding (BLOB)      │ │
│     │ d) Save thumbnail (base64)     │ │
│     │ e) Update website stats        │ │
│     └────────────────────────────────┘ │
└──────────────┬─────────────────────────┘
               │
               ▼
┌────────────────────────────────────────┐
│  9. FAISS INDEX UPDATE                 │
│     ┌────────────────────────────────┐ │
│     │ a) Load existing FAISS index   │ │
│     │ b) Add new face vectors        │ │
│     │ c) Build/update index          │ │
│     │ d) Save to faiss_index.bin     │ │
│     └────────────────────────────────┘ │
└──────────────┬─────────────────────────┘
               │
               ▼
┌────────────────────────────────────────┐
│  10. ACTIVITY LOG UPDATE               │
│      • "✓ Completed: example.com"      │
│      • "New: +15 images, +23 faces"    │
│      • Real-time display in dashboard  │
└──────────────┬─────────────────────────┘
               │
               ▼
             [END]
```

---

## 🧩 Component Details

### **1. Admin Dashboard (`admin_dashboard.py`)**
```python
Purpose: Web interface for system management
Port: 5001
Framework: Flask

Key Features:
├── Website Management
│   ├── Add new websites
│   ├── View all websites
│   ├── Delete websites (cascade delete)
│   └── Bulk add from text file
│
├── Scraping Operations
│   ├── Scrape individual website
│   ├── Scrape all websites
│   ├── Re-scrape (smart merge)
│   └── Auto re-scrape scheduler
│
├── Monitoring
│   ├── Live activity log
│   ├── Statistics dashboard
│   └── Stale website detection
│
└── API Endpoints
    ├── POST /api/add_website
    ├── POST /api/scrape_website
    ├── POST /api/scrape_all
    ├── POST /api/rescrape_website
    ├── POST /api/delete_website
    └── GET  /api/scraping_status
```

### **2. Scraping Pipeline (`main_pipeline.py`)**
```python
Purpose: Orchestrate the scraping workflow

Workflow:
1. process_website(url, db, faiss, face_proc, scraper)
   │
   ├──► Get website_id from database
   ├──► Scrape images (Selenium)
   ├──► Filter valid images
   ├──► Check for duplicates (hash)
   ├──► Detect faces (MTCNN)
   ├──► Generate embeddings (FaceNet)
   ├──► Store in database
   ├──► Update FAISS index
   └──► Log results
```

### **3. Web Scraper (`scraper.py`)**
```python
Purpose: Extract images from websites

Technology: Selenium WebDriver + Chrome
Features:
├── Headless browser support
├── JavaScript rendering
├── Dynamic content handling
├── Image URL extraction
├── In-memory download
└── Timeout protection

Image Sources:
├── <img> tags (src attribute)
├── <img> tags (data-src lazy loading)
├── CSS background images
└── Inline SVG images
```

### **4. Face Processor (`face_processor.py`)**
```python
Purpose: Detect faces and generate embeddings

Models Used:
├── MTCNN: Face detection
│   ├── Confidence: 0.9 (90%)
│   └── Min face size: 20x20 pixels
│
└── FaceNet: Face embedding
    ├── Input: 160x160 RGB
    ├── Output: 512-dimensional vector
    └── L2 normalized

Process:
1. detect_faces(image_bytes) → List[face_box, confidence]
2. generate_embedding(face_box) → 512-dim vector
3. Return: [(embedding, bounding_box, confidence)]
```

### **5. Database Manager (`database_manager.py`)**
```python
Purpose: Handle all database operations

Database Schema:
├── websites
│   ├── id (PRIMARY KEY)
│   ├── url (UNIQUE)
│   ├── created_at
│   ├── scraped_at
│   └── deleted_at (soft delete)
│
├── images
│   ├── id (PRIMARY KEY)
│   ├── website_id (FOREIGN KEY)
│   ├── image_url
│   ├── image_hash (SHA-256, UNIQUE)
│   ├── created_at
│   └── deleted_at
│
├── faces
│   ├── id (PRIMARY KEY)
│   ├── image_id (FOREIGN KEY)
│   ├── face_box (JSON)
│   ├── confidence (FLOAT)
│   ├── thumbnail (base64)
│   ├── created_at
│   └── deleted_at
│
└── embeddings
    ├── id (PRIMARY KEY)
    ├── face_id (FOREIGN KEY)
    ├── embedding (512-dim BLOB)
    └── created_at

Key Methods:
├── add_website(url) → website_id
├── add_image(website_id, url, hash) → image_id
├── add_face(image_id, bbox, conf, thumb) → face_id
├── store_embedding(face_id, embedding)
├── get_stale_websites(days) → List[websites]
├── delete_website_complete(website_id) → stats
└── get_statistics() → {websites, images, faces}
```

### **6. FAISS Manager (`faiss_manager.py`)**
```python
Purpose: Vector similarity search

Index Type: IndexFlatL2 (L2 distance)
Features:
├── Add face embeddings
├── Search similar faces
├── Remove face IDs
├── Save/load index
└── Batch operations

Operations:
├── add_face(face_id, embedding)
├── search(embedding, k=10) → [(face_id, distance)]
├── remove_face_ids([ids])
├── save_index(path)
└── load_index(path)
```

---

## 📊 Data Flow

### **Scraping Data Flow**
```
Website URL
    │
    ▼
[Selenium Scraper]
    │
    ├──► HTML Page Content
    │
    ▼
[Image Extractor]
    │
    ├──► Image URLs List
    │
    ▼
[Image Downloader] (in-memory)
    │
    ├──► Raw Image Bytes
    │
    ▼
[Hash Calculator]
    │
    ├──► SHA-256 Hash
    │
    ▼
[Duplicate Check] ──► Database Query
    │                      │
    │                      ├──► Exists? → Skip
    │                      └──► New? → Continue
    ▼
[Face Detector] (MTCNN)
    │
    ├──► Face Bounding Boxes
    │
    ▼
[Face Cropper]
    │
    ├──► Face Image Regions
    │
    ▼
[Embedding Generator] (FaceNet)
    │
    ├──► 512-dim Vectors
    │
    ▼
[Database Storage]
    │
    ├──► websites table
    ├──► images table
    ├──► faces table
    └──► embeddings table
    │
    ▼
[FAISS Index Update]
    │
    └──► faiss_index.bin
```

### **Search Data Flow**
```
Upload Face Image
    │
    ▼
[Face Detection] (MTCNN)
    │
    ├──► Extract Face
    │
    ▼
[Embedding Generation] (FaceNet)
    │
    ├──► 512-dim Query Vector
    │
    ▼
[FAISS Search] (k=10)
    │
    ├──► Top 10 Similar Faces
    │
    ▼
[Database Lookup]
    │
    ├──► Face Details
    ├──► Image URLs
    └──► Website Info
    │
    ▼
[Result Formatting]
    │
    └──► JSON Response
```

---

## 🔌 API Endpoints

### **Admin Dashboard Endpoints**

#### **1. Add Website**
```http
POST /api/add_website
Content-Type: application/json

Request:
{
  "url": "https://example.com",
  "name": "Example Site" (optional)
}

Response:
{
  "success": true,
  "website_id": 123
}
```

#### **2. Scrape Website**
```http
POST /api/scrape_website
Content-Type: application/json

Request:
{
  "url": "https://example.com"
}

Response:
{
  "success": true
}

Note: Scraping runs in background thread
```

#### **3. Scrape All Websites**
```http
POST /api/scrape_all

Response:
{
  "success": true,
  "total_websites": 10
}
```

#### **4. Re-scrape Website (Smart Merge)**
```http
POST /api/rescrape_website
Content-Type: application/json

Request:
{
  "url": "https://example.com",
  "website_id": 123
}

Response:
{
  "success": true,
  "new_images": 5,
  "new_faces": 8,
  "total_images": 105
}
```

#### **5. Delete Website**
```http
POST /api/delete_website
Content-Type: application/json

Request:
{
  "website_id": 123
}

Response:
{
  "success": true,
  "deleted_images": 100,
  "deleted_faces": 234,
  "deleted_face_ids_count": 234
}
```

#### **6. Get Scraping Status**
```http
GET /api/scraping_status

Response:
{
  "logs": [
    "[12:34:56] 🔄 Starting: https://example.com",
    "[12:35:01] ✓ Completed: https://example.com"
  ]
}

Note: Rate limit exempt (for live polling)
```

---

## 🚀 Running the System

### **Start Admin Dashboard**
```bash
# Option 1: Using launcher script
python run_admin.py

# Option 2: Direct execution
python admin_dashboard.py
```

### **Access Dashboard**
```
http://localhost:5001
```

### **Common Operations**

#### **1. Add and Scrape Website**
1. Open dashboard at http://localhost:5001
2. Enter URL in "Add Website" form
3. Click "Add Website"
4. Click "🔄 Scrape" button for the website
5. Watch activity log for progress

#### **2. Bulk Add Websites**
1. Scroll to "Bulk Add" section
2. Enter multiple URLs (one per line)
3. Click "Add to Database"
4. Click "🚀 Scrape All" to process all

#### **3. Re-scrape Stale Websites**
1. Check "Stale Websites" section
2. Click "♻️ Update All Stale Websites"
3. System will find and process only NEW images

#### **4. Delete Website**
1. Click "🗑️ Delete" button
2. Type "DELETE" to confirm
3. All data (images, faces, embeddings) removed

---

## 🔧 Troubleshooting

### **Common Issues**

#### **1. ModuleNotFoundError**
```bash
# Solution: Install missing package
pip install <package-name>

# Common missing packages:
pip install mtcnn keras-facenet
```

#### **2. Selenium WebDriver Error**
```bash
# Solution: Update ChromeDriver
pip install --upgrade selenium

# Or manually download ChromeDriver matching your Chrome version
```

#### **3. Database Locked**
```bash
# Solution: Close other connections
# SQLite allows only one writer at a time
# Wait for previous operation to complete
```

#### **4. FAISS Index Error**
```bash
# Solution: Delete and rebuild index
rm faiss_index.bin
# Re-run scraping to rebuild
```

#### **5. Rate Limit 429 Error**
```bash
# Cause: /api/scraping_status being rate limited
# Solution: Ensure @limiter.exempt decorator is AFTER @app.route
# Already fixed in current version
```

### **Performance Tips**

1. **Batch Processing**
   - Use "Scrape All" instead of individual scrapes
   - More efficient for multiple websites

2. **Database Optimization**
   - Regularly vacuum SQLite database
   ```sql
   VACUUM;
   ```

3. **Memory Management**
   - Clear browser cache periodically
   - Restart dashboard after large scrapes

4. **FAISS Index**
   - Rebuild index monthly for optimization
   - Backup before major operations

---

## 📝 Summary

### **Key Points**
✅ All scraping is **in-memory** (no disk I/O for images)  
✅ **Smart merge** prevents duplicates (hash-based)  
✅ **Soft deletes** preserve data integrity  
✅ **Background scraping** doesn't block UI  
✅ **Auto re-scraping** keeps data fresh  
✅ **FAISS search** provides fast similarity matching  
✅ **Web dashboard** for easy management  

### **Project Status**
🟢 **Fully Functional** - All features working  
🟢 **Synced to GitHub** - Latest version  
🟢 **Dependencies Installed** - Ready to run  
🟢 **Documentation Complete** - This guide  

---

**Last Updated:** March 7, 2026  
**Version:** 3.0  
**Repository:** https://github.com/Ruwantha-Harshamal/Facial-Exposure-Detection
