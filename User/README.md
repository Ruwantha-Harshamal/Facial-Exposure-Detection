# User Backend & Frontend - Privacy Exposure Checker

Complete web application for users to check if their face is exposed online.

## 📁 Structure

```
User/
├── backend/                    # Flask API
│   ├── app.py                 # Main Flask server
│   ├── requirements.txt       # Flask dependencies
│   └── uploads/               # Temporary upload folder
│
└── frontend/                   # HTML/CSS/JS
    ├── index.html             # Home page (upload)
    ├── about.html             # About page
    ├── css/
    │   └── style.css          # Styling
    └── js/
        └── main.js            # JavaScript logic
```

## 🚀 Setup & Installation

### 1. Install Flask (Only New Package Needed)

```bash
# Navigate to backend folder
cd User/backend

# Install Flask
pip install -r requirements.txt
```

**Note:** All other packages (TensorFlow, MTCNN, FAISS, etc.) are already installed from your main project `requirements.txt`. Flask is the only new package!

### 2. Run the Backend Server

```bash
# Make sure you're in the User/backend folder
cd User/backend

# Run Flask server
python app.py
```

Server will start at: **http://localhost:5000**

### 3. Access the Web Interface

Open your browser and go to:
- **Home Page:** http://localhost:5000
- **About Page:** http://localhost:5000/about

## 🎯 Usage

### For Users:
1. Visit http://localhost:5000
2. Upload your photo (drag & drop or click to browse)
3. Click "Check My Privacy"
4. Wait a few seconds for analysis
5. View results showing where your face was found (if anywhere)

### For Admin (You):
The backend automatically uses your existing:
- Database: `../../face_recognition.db`
- FAISS Index: `../../faiss_index.bin`
- Python modules: `face_processor.py`, `database_manager.py`, `faiss_manager.py`

**No separate setup needed!** The user backend shares everything with the admin backend.

## 🔧 How It Works

```
User uploads photo → Flask receives it
     ↓
Detect face (MTCNN)
     ↓
Generate embedding (FaceNet)
     ↓
Search FAISS for similar faces
     ↓
Query database for match details
     ↓
DELETE user photo (privacy!)
     ↓
Return results to user
```

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Home page |
| `/about` | GET | About page |
| `/api/upload` | POST | Upload photo & search |
| `/api/stats` | GET | Get database statistics |
| `/api/thumbnail/<face_id>` | GET | Get face thumbnail |
| `/health` | GET | Health check |

## 🔐 Privacy Features

✅ User photos are deleted immediately after processing (within 6 seconds)
✅ No user data stored (no IP, no photos, no embeddings)
✅ All processing done locally (no third-party APIs)
✅ No tracking or analytics

## 🐛 Troubleshooting

### Error: "Module not found: face_processor"
**Solution:** The backend needs access to parent directory modules. This is handled by:
```python
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
```
Make sure this line is in `app.py` (it already is!).

### Error: "Database not found"
**Solution:** Run the admin backend first to create the database:
```bash
cd ../..  # Go to main project folder
python process_batch.py --urls websites.txt
```

### Error: "No faces in database"
**Solution:** The database is empty. Scrape some websites first using the admin backend.

### Port 5000 already in use
**Solution:** Change the port in `app.py`:
```python
app.run(host='0.0.0.0', port=5001)  # Use different port
```

## 📝 Development

### Running in Debug Mode
Debug mode is enabled by default in `app.py`:
```python
app.run(debug=True)
```

This provides:
- Auto-reload on code changes
- Detailed error pages
- Better logging

### Production Deployment
For production, use a proper WSGI server:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## 🎨 Customization

### Change Similarity Threshold
Edit `app.py` line ~160:
```python
similarity_threshold = 0.60  # Adjust (0.0-1.0)
```

### Change Upload Limits
Edit `app.py` lines 30-32:
```python
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
```

### Modify Styling
Edit `frontend/css/style.css` to change colors, fonts, layout, etc.

## ✅ Testing

### Test API Health
```bash
curl http://localhost:5000/health
```

### Test Stats Endpoint
```bash
curl http://localhost:5000/api/stats
```

### Test Photo Upload
```bash
curl -X POST -F "photo=@test.jpg" http://localhost:5000/api/upload
```

## 🚀 Next Steps

1. **Test locally:** Run the server and upload a few test photos
2. **Deploy to production:** Use a cloud service (DigitalOcean, AWS, Heroku)
3. **Add features:** 
   - User accounts
   - Search history
   - Email notifications
   - PDF reports
4. **Improve UI:** Add more styling, animations, better mobile support

## 📞 Support

If you encounter any issues, check:
1. All packages installed: `pip list`
2. Database exists: `ls ../../face_recognition.db`
3. FAISS index exists: `ls ../../faiss_index.bin`
4. Server logs for errors

---

**Ready to test!** Run `python app.py` and visit http://localhost:5000 🎉
