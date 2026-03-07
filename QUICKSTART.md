# 🚀 Quick Start Guide - Privacy Exposure Checker

## ⚡ 5-Minute Setup

### Step 1: Install Dependencies (1 minute)
```bash
# Clone and enter project
git clone https://github.com/Ruwantha-Harshamal/Facial-Exposure-Detection.git
cd Facial-Exposure-Detection

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\Activate.ps1  # Windows PowerShell
# OR
.venv\Scripts\activate.bat  # Windows CMD
# OR
source .venv/bin/activate   # Linux/Mac

# Install packages
pip install -r requirements.txt
```

### Step 2: Configure (1 minute)
```bash
# Create .env file with secret key
echo "ADMIN_SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')" > .env

# That's it! Default config.py settings work out of the box
```

### Step 3: Launch Dashboard (30 seconds)
```bash
python run_admin.py
```

### Step 4: Access Dashboard (30 seconds)
```
Open browser: http://localhost:5001
```

### Step 5: Start Scraping (2 minutes)
1. **Add a website**: Enter URL → Click "Add Website"
2. **Scrape it**: Click "🔄 Scrape" button
3. **Watch the log**: Live updates in "Activity Log" section
4. **Done!** Faces detected and stored

---

## 🎯 First-Time Usage

### Example: Scrape Your First Website

```
1. Open http://localhost:5001
2. Enter URL: https://example.com
3. Click "Add Website" → Success! ✓
4. Click "🔄 Scrape" → Scraping starts...
5. Watch activity log:
   [12:34:56] 🔄 Starting: https://example.com
   [12:35:10] ✓ Completed: https://example.com
   [12:35:10] Found 15 images, detected 23 faces
```

---

## 📚 Documentation Index

| Document | Purpose | Read When |
|----------|---------|-----------|
| **PROJECT_FLOW.md** | Complete end-to-end flow | Understanding the entire system |
| **CONFIGURATION.md** | All configuration options | Customizing settings |
| **README.md** | Project overview | First time setup |
| **QUICKSTART.md** | This guide | Getting started quickly |

---

## 🔗 Quick Links

- **GitHub Repository**: https://github.com/Ruwantha-Harshamal/Facial-Exposure-Detection
- **Admin Dashboard**: http://localhost:5001 (after starting)
- **Issues**: Report bugs on GitHub Issues tab

---

## 💡 Common Commands

```bash
# Start admin dashboard
python run_admin.py

# Check what's running
netstat -ano | findstr :5001

# Stop dashboard (Ctrl+C in terminal)

# Update from GitHub
git pull origin main

# Push changes to GitHub
git add .
git commit -m "Your message"
git push origin main
```

---

## 🆘 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| Port 5001 in use | `netstat -ano \| findstr :5001` then kill process |
| Module not found | `pip install -r requirements.txt` |
| Database locked | Close other connections, restart dashboard |
| No faces detected | Lower `FACE_DETECTION_CONFIDENCE` in config.py |
| Rate limit errors | Restart dashboard (fixes /api/scraping_status) |

---

**Ready to go!** 🎉

Start with: `python run_admin.py`
