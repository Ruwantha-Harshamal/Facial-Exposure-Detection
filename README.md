# 🔍 Privacy Exposure Checker

A secure face recognition system that helps you discover if your face appears in publicly scraped web images.

[![Security](https://img.shields.io/badge/security-hardened-green)]() [![Python](https://img.shields.io/badge/python-3.11%2B-blue)]() [![License](https://img.shields.io/badge/license-MIT-blue)]()

---

## 🎯 Features

- **Face Detection:** MTCNN with 90% confidence threshold
- **Face Recognition:** FaceNet 512-dimensional embeddings  
- **Fast Search:** FAISS vector similarity search
- **Web Scraping:** Automated image collection with Selenium
- **Secure Upload:** Rate limiting, image validation, SSRF protection
- **User Privacy:** Photos deleted immediately after processing

---

## 🔒 Security Features

✅ Rate limiting (10 uploads/hour per IP)  
✅ Image content validation (prevents malware/bombs)  
✅ SSRF protection (blocks private networks)  
✅ API key authentication for admin  
✅ HTTPS enforcement (production)  
✅ CORS protection  
✅ Session security with SECRET_KEY  
✅ File size limits (10MB max)  
✅ Automatic temp file cleanup  
✅ No default database credentials  

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Generate Security Configuration

```bash
python setup_security.py
```

This creates a `.env` file with secure random keys.

### 3. Start the Application

```bash
cd User/backend
python app.py
```

Visit **http://localhost:5000**

---

## 📁 Project Structure

```
RP Scraper/
├── User/
│   ├── backend/
│   │   ├── app.py           # Flask API (secured)
│   │   ├── uploads/         # Temp uploads (auto-cleanup)
│   │   └── test_app.py      # App test script
│   └── frontend/
│       ├── index.html       # Main UI
│       ├── about.html       # About page
│       ├── css/style.css
│       └── js/main.js
│
├── config.py                # Configuration
├── database_manager.py      # SQLite/PostgreSQL manager
├── face_processor.py        # MTCNN + FaceNet
├── faiss_manager.py         # Vector search
├── scraper.py               # Web scraper (SSRF protected)
├── process_batch.py         # Batch scraping
├── main_pipeline.py         # Main pipeline
├── face_clustering.py       # Face clustering
├── search_api.py            # Search utilities
├── view_database.py         # Database viewer
│
├── requirements.txt         # Python packages
├── .env.example             # Config template
├── setup_security.py        # Security setup tool
├── test_security.py         # Security test
├── verify_security.py       # Security verification
│
├── DEPLOYMENT_GUIDE.md      # Production deployment
├── SECURITY.md              # Security documentation
└── README.md                # This file
```

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file (use `setup_security.py` or copy from `.env.example`):

```bash
# Required
SECRET_KEY=your-64-character-secret-key
ADMIN_API_KEY=your-64-character-api-key

# Environment
FLASK_ENV=production
FLASK_DEBUG=false

# Optional
ALLOWED_ORIGINS=https://yourdomain.com
RATE_LIMIT_STORAGE_URI=memory://
DB_TYPE=sqlite
MIN_FACE_CONFIDENCE=0.90
MIN_SIMILARITY_THRESHOLD=0.70
```

### Database Options

**SQLite (Default):**
- Simple, no setup required
- Good for development/small scale

**PostgreSQL (Production):**
```bash
DB_TYPE=postgresql
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=face_recognition
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_secure_password
```

---

## 🎨 How It Works

### User Flow

1. **Upload Photo** → User submits a photo via web interface
2. **Face Detection** → MTCNN detects faces (90%+ confidence)
3. **Generate Embedding** → FaceNet creates 512-D vector
4. **Search Database** → FAISS finds similar faces
5. **Show Results** → Display matching images with confidence scores
6. **Delete Photo** → User photo immediately deleted (privacy!)

### Admin Pipeline

1. **Add URLs** → Admin provides websites to scrape
2. **Scrape Images** → Selenium extracts image URLs
3. **Download** → Images downloaded to memory
4. **Detect Faces** → MTCNN finds all faces
5. **Generate Embeddings** → FaceNet processes each face
6. **Store in Database** → SQLite/PostgreSQL + FAISS index
7. **Cluster Faces** → Group same person across images

---

## 📡 API Endpoints

### Public Endpoints

| Method | Endpoint | Description | Rate Limit |
|--------|----------|-------------|------------|
| GET | `/` | Home page | - |
| GET | `/about.html` | About page | - |
| POST | `/api/upload` | Upload photo for search | 10/hour |
| GET | `/api/thumbnail/<id>` | Get face thumbnail | - |
| GET | `/health` | Health check | - |

### Protected Endpoints (API Key Required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stats` | Database statistics |

**Authentication:**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     http://localhost:5000/api/stats
```

---

## 🧪 Testing

### Test Security Features
```bash
python test_security.py
```

### Verify Configuration
```bash
python verify_security.py
```

### Test Application
```bash
cd User/backend
python test_app.py
```

---

## 🌐 Web Scraping

### Add Websites

Edit `websites.txt`:
```
https://example.com
https://another-site.com
```

### Run Scraper

```bash
python process_batch.py
```

### Safety Features

- SSRF protection (blocks localhost, private IPs)
- Rate limiting (configurable delays)
- Headless browser (no GUI required)
- Error handling and retries

---

## 📊 Performance

| Operation | Time |
|-----------|------|
| Face Detection | 2-5 seconds/image |
| Embedding Generation | <1 second |
| FAISS Search | <100ms for 10K vectors |
| Upload Validation | <200ms |

---

## 🔐 Security Best Practices

### Development

✅ Use `.env` for secrets (never commit!)  
✅ Different keys for dev/staging/prod  
✅ Test security features regularly  
✅ Keep dependencies updated  

### Production

✅ Enable HTTPS (nginx + Let's Encrypt)  
✅ Use Redis for rate limiting  
✅ Set `FLASK_ENV=production`  
✅ Set `FLASK_DEBUG=false`  
✅ Strong database credentials  
✅ Monitor logs and security events  

See **`DEPLOYMENT_GUIDE.md`** for complete setup.

---

## 📚 Documentation

| File | Description |
|------|-------------|
| `DEPLOYMENT_GUIDE.md` | Production deployment steps |
| `SECURITY.md` | Security features & configuration |
| `.env.example` | All environment variables |

---

## 🛠️ Tech Stack

- **Backend:** Flask 3.0
- **Face Detection:** MTCNN
- **Face Recognition:** FaceNet (keras-facenet)
- **Deep Learning:** TensorFlow 2.14+
- **Vector Search:** FAISS
- **Database:** SQLite / PostgreSQL
- **Web Scraping:** Selenium
- **Security:** Flask-Limiter, Flask-CORS, Flask-Talisman

---

## ⚠️ Privacy & Legal

### Privacy

- User photos deleted immediately after processing
- No persistent storage of user images
- Temporary files auto-cleaned
- Only scraped images stored in database

### Legal Considerations

⚠️ **Important:** This tool is for legitimate privacy research only.

- Verify website ToS allows scraping
- Respect robots.txt
- Consider copyright implications
- Comply with GDPR/privacy laws
- Define acceptable use policy

---

## 🤝 Contributing

1. **Security issues:** Report privately (not public GitHub)
2. **Bug reports:** Create GitHub issue
3. **Feature requests:** Create GitHub issue
4. **Pull requests:** Follow existing code style

---

## 📝 License

MIT License - See LICENSE file

---

## 🙏 Acknowledgments

- **MTCNN** - Face detection
- **FaceNet** - Face recognition embeddings
- **FAISS** - Facebook AI Similarity Search
- **Flask** - Web framework
- **Selenium** - Web automation

---

## 📞 Support

- **Documentation:** See docs above
- **Issues:** [Create GitHub issue](https://github.com/your-repo/issues)
- **Security:** Report privately to security@yourdomain.com

---

## 🚀 What's New in v2.0

✅ Complete security hardening  
✅ Rate limiting protection  
✅ Image validation  
✅ SSRF protection  
✅ API authentication  
✅ HTTPS enforcement  
✅ Production-ready configuration  
✅ Comprehensive documentation  

---

**Version:** 2.0 (Secured)  
**Last Updated:** December 28, 2025  
**Status:** ✅ Production Ready

---

Made with ❤️ for privacy awareness
