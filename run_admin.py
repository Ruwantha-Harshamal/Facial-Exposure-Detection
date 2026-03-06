"""
run_admin.py

Start Admin Dashboard Web Application
Manage websites, scraping, and view statistics
"""

import subprocess
import sys

if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("ADMIN DASHBOARD - PRIVACY EXPOSURE CHECKER")
    print("=" * 70)
    print("Starting web interface...")
    print("Access at: http://localhost:5001")
    print("=" * 70 + "\n")
    
    subprocess.run([sys.executable, 'admin_dashboard.py'])
