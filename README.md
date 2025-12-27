# 🔒 Privacy Exposure Checker

A comprehensive web application that allows users to check if their face has been exposed online without their knowledge. The system scrapes websites, detects faces, and enables users to search for their photos in the database.

## 🎯 Features

### Admin Backend (Scraping & Indexing)
- 🕷️ **Web Scraping**: Automated scraping of websites using Selenium WebDriver
- 👤 **Face Detection**: Advanced face detection using MTCNN (Multi-task Cascaded Convolutional Networks)
- 🧠 **Face Recognition**: Face embedding generation using FaceNet (512-dimensional vectors)
- 🔍 **Fast Search**: Ultra-fast similarity search using FAISS (Facebook AI Similarity Search)
- 💾 **Database Storage**: Efficient SQLite database for metadata and face information
- 📊 **Batch Processing**: Process multiple websites in batch mode

### User Backend (Web API)
- 📤 **Photo Upload**: Secure photo upload with file validation
- 🔎 **Face Matching**: Real-time face matching against database
- 🎨 **Color-Coded Results**: Similarity badges (High/Medium/Low confidence)
- 🔒 **Privacy-First**: Uploaded photos are deleted immediately after processing
- 📊 **Statistics**: Real-time database statistics

### Frontend (Web Interface)
- 🎨 **Modern UI**: Beautiful, responsive design with Bootstrap 5
- 📸 **Drag & Drop**: Easy file upload with drag-and-drop support
- 🖼️ **Image Preview**: Preview uploaded image before searching
- ⚡ **Real-time Results**: Instant search results with match details
- 🌐 **Source Information**: Shows exact URL and website where face was found
- 📱 **Responsive**: Works on desktop and mobile devices

## 🏗️ Project Structure

```
RP Scraper/
├── 🔧 Admin Backend (Scraping & Indexing)
│   ├── process_batch.py          # Main batch processing script
│   ├── scraper.py                # Web scraper (Selenium)
│   ├── face_processor.py         # Face detection & embedding
│   ├── face_clustering.py        # Face clustering utilities
│   ├── faiss_manager.py          # FAISS vector search
│   ├── database_manager.py       # SQLite database operations
│   ├── main_pipeline.py          # Main processing pipeline
│   ├── config.py                 # Configuration settings
│   ├── database_schema_v3.sql    # Database schema
│   ├── face_recognition.db       # SQLite database (ignored)
│   ├── faiss_index.bin           # FAISS index (ignored)
│   ├── websites.txt              # List of websites to scrape
│   ├── requirements.txt          # Python dependencies
│   └── view_database.py          # Database viewer utility
│
└── 👤 User Interface
    ├── backend/
    │   ├── app.py                # Flask API server
    │   ├── requirements.txt      # Backend dependencies
    │   └── uploads/              # Temporary upload storage
    │       └── .gitkeep
    └── frontend/
        ├── index.html            # Main page
        ├── about.html            # About page
        ├── css/
        │   └── style.css         # Custom styles
        └── js/
            └── main.js           # Frontend logic
```

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- Chrome browser (for Selenium)
- ChromeDriver (automatically managed by selenium)

### Step 1: Clone the Repository
```bash
git clone <repository-url>
cd "RP Scraper"
```

### Step 2: Install Dependencies

#### For Admin Backend:
```bash
pip install -r requirements.txt
```

#### For User Backend:
```bash
cd User/backend
pip install -r requirements.txt
cd ../..
```

### Step 3: Initialize Database
The database will be automatically created when you run the scraper for the first time.

## 📖 Usage

### 1. Scrape Websites (Admin)

#### Add websites to scrape:
Edit `websites.txt` and add URLs (one per line):
```
https://example.com
https://another-site.com
```

#### Run the batch processor:
```bash
python process_batch.py
```

This will:
- Scrape all websites in `websites.txt`
- Detect faces in images
- Generate face embeddings
- Store in database and FAISS index

### 2. Start User Web Interface

```bash
cd User/backend
python app.py
```

The server will start at: **http://localhost:5000**

### 3. Check Your Privacy

1. Open **http://localhost:5000** in your browser
2. Upload your photo (JPG, JPEG, or PNG)
3. Click "Check My Privacy"
4. View results:
   - ✅ **Safe**: No matches found
   - ⚠️ **Alert**: Face found with match details

## 🔧 Configuration

Edit `config.py` to customize:

```python
# Database settings
DB_TYPE = 'sqlite'
SQLITE_DB_PATH = 'face_recognition.db'

# FAISS settings
FAISS_INDEX_PATH = 'faiss_index.bin'
FAISS_INDEX_TYPE = 'flat'  # or 'ivf'

# Scraping settings
PAGE_LOAD_WAIT_SECONDS = 5
MAX_WORKERS = 4

# Face detection settings
MIN_FACE_SIZE = 80
CONFIDENCE_THRESHOLD = 0.95

# Similarity thresholds
SIMILARITY_THRESHOLD = 0.60  # 60% minimum
```

## 🛠️ Utilities

### View Database Statistics
```bash
python view_database.py
```

Shows:
- Total websites scraped
- Total images processed
- Total faces detected
- Database size and statistics

### Search API (Standalone)
```bash
python search_api.py
```

Command-line interface for searching faces.

## 🔒 Privacy & Security

- ✅ **No Photo Storage**: User photos are deleted immediately after processing
- ✅ **Local Processing**: All face detection happens locally
- ✅ **No Tracking**: No analytics or user tracking
- ✅ **Open Source**: Transparent codebase
- ⚠️ **Development Mode**: Use a production WSGI server for deployment (e.g., Gunicorn)
- ⚠️ **HTTPS**: Use HTTPS in production for secure uploads

## 📊 Technical Details

### Face Detection Pipeline
1. **MTCNN**: Detects faces with bounding boxes and confidence scores
2. **Alignment**: Aligns faces for consistent embedding generation
3. **FaceNet**: Generates 512-dimensional face embeddings
4. **Normalization**: L2 normalization for cosine similarity

### Search Algorithm
1. **FAISS**: Uses cosine similarity for vector search
2. **Threshold**: Filters matches above 60% similarity
3. **Database Join**: Retrieves full metadata for matches
4. **Ranking**: Results sorted by similarity score

### Similarity Badges
- 🔴 **High** (>85%): Strong match, likely same person
- 🟡 **Medium** (70-85%): Moderate match, possible same person
- 🟢 **Low** (60-70%): Weak match, may be different person

## 🐛 Troubleshooting

### Database Issues
```bash
# Reset database (WARNING: Deletes all data)
rm face_recognition.db faiss_index.bin
python process_batch.py
```

### ChromeDriver Issues
```bash
pip install --upgrade selenium
```

### Face Detection Issues
- Ensure good lighting in photos
- Use clear, front-facing photos
- Minimum face size: 80x80 pixels

## 📦 Dependencies

### Core Libraries
- **TensorFlow/Keras**: Deep learning framework
- **MTCNN**: Face detection
- **keras-facenet**: Face embedding generation
- **FAISS**: Similarity search
- **Flask**: Web framework
- **Selenium**: Web scraping
- **OpenCV**: Image processing
- **Pillow**: Image handling
- **SQLite**: Database

See `requirements.txt` for complete list.

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

This project is for educational and research purposes. Please respect privacy and legal considerations when scraping websites.

## ⚠️ Legal Disclaimer

- Only scrape websites you have permission to scrape
- Respect robots.txt and website terms of service
- Consider privacy laws (GDPR, CCPA, etc.)
- This tool is for legitimate privacy checking purposes
- Use responsibly and ethically

## 🙏 Acknowledgments

- **MTCNN**: Joint Face Detection and Alignment
- **FaceNet**: Face Recognition System
- **FAISS**: Facebook AI Similarity Search
- **Bootstrap**: Frontend framework

## 📞 Support

For issues, questions, or contributions, please open an issue on GitHub.

---

**Built with ❤️ for Privacy Awareness**
