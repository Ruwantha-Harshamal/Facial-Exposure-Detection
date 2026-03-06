"""
run_user.py

Start User Application
Access at: http://localhost:5000
"""

import subprocess
import sys
import os

if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("STARTING USER APPLICATION")
    print("=" * 70)
    print("Access at: http://localhost:5000")
    print("=" * 70 + "\n")
    
    # Change to User/backend directory
    os.chdir(os.path.join(os.path.dirname(__file__), 'User', 'backend'))
    
    subprocess.run([sys.executable, 'app.py'])
