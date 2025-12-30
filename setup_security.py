"""
setup_security.py

Quick setup script to generate secure keys and create .env file
Run this before deploying to production
"""

import secrets
import os

def generate_env_file():
    """Generate .env file with secure keys"""
    
    print("\n" + "="*70)
    print("SECURITY SETUP - Privacy Exposure Checker")
    print("="*70 + "\n")
    
    # Check if .env already exists
    if os.path.exists('.env'):
        response = input("⚠️  .env file already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("❌ Setup cancelled.")
            return
    
    # Generate secure keys
    print("🔐 Generating secure keys...")
    secret_key = secrets.token_hex(32)
    admin_api_key = secrets.token_hex(32)
    
    # Get configuration
    print("\n📋 Configuration:")
    print("-" * 70)
    
    flask_env = input("Environment (development/production) [production]: ").strip() or "production"
    flask_debug = "false" if flask_env == "production" else input("Enable debug mode? (true/false) [false]: ").strip() or "false"
    
    # Database configuration
    db_type = input("Database type (sqlite/postgresql) [sqlite]: ").strip() or "sqlite"
    
    postgres_config = ""
    if db_type == "postgresql":
        print("\n🗄️  PostgreSQL Configuration:")
        postgres_host = input("Host [localhost]: ").strip() or "localhost"
        postgres_port = input("Port [5432]: ").strip() or "5432"
        postgres_db = input("Database name [face_recognition]: ").strip() or "face_recognition"
        postgres_user = input("Username: ").strip()
        postgres_password = input("Password: ").strip()
        
        if not postgres_user or not postgres_password:
            print("❌ PostgreSQL username and password are required!")
            return
        
        postgres_config = f"""
# PostgreSQL Configuration
POSTGRES_HOST={postgres_host}
POSTGRES_PORT={postgres_port}
POSTGRES_DB={postgres_db}
POSTGRES_USER={postgres_user}
POSTGRES_PASSWORD={postgres_password}
"""
    
    # CORS configuration
    print("\n🌐 CORS Configuration:")
    allowed_origins = input("Allowed origins (comma-separated) [http://localhost:5000]: ").strip() or "http://localhost:5000"
    
    # Create .env file
    env_content = f"""# =================================================================
# SECURITY CONFIGURATION
# =================================================================
# Generated on: {os.popen('date').read().strip()}
# WARNING: Never commit this file to version control!
# =================================================================

# -----------------------------------------------------------------
# Flask Configuration
# -----------------------------------------------------------------
SECRET_KEY={secret_key}
FLASK_ENV={flask_env}
FLASK_DEBUG={flask_debug}

# -----------------------------------------------------------------
# API Authentication
# -----------------------------------------------------------------
ADMIN_API_KEY={admin_api_key}

# -----------------------------------------------------------------
# CORS Configuration
# -----------------------------------------------------------------
ALLOWED_ORIGINS={allowed_origins}

# -----------------------------------------------------------------
# Rate Limiting
# -----------------------------------------------------------------
# Use Redis for production: redis://localhost:6379
RATE_LIMIT_STORAGE_URI=memory://

# -----------------------------------------------------------------
# Database Configuration
# -----------------------------------------------------------------
DB_TYPE={db_type}
{postgres_config}
# -----------------------------------------------------------------
# Optional Settings
# -----------------------------------------------------------------
# MIN_FACE_CONFIDENCE=0.90
# MIN_SIMILARITY_THRESHOLD=0.70
# FACE_MATCH_THRESHOLD=0.6
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("\n✅ .env file created successfully!\n")
    print("="*70)
    print("🔑 IMPORTANT - Save these keys securely:")
    print("="*70)
    print(f"\nSECRET_KEY:\n{secret_key}\n")
    print(f"ADMIN_API_KEY:\n{admin_api_key}\n")
    print("="*70)
    print("\n⚠️  Security Reminders:")
    print("  1. Never share these keys")
    print("  2. Never commit .env to version control")
    print("  3. Regenerate keys if compromised")
    print("  4. Use different keys for dev/staging/production")
    print("="*70)
    print("\n📚 Next Steps:")
    print("  1. Review .env file")
    print("  2. Install security packages: pip install -r requirements.txt")
    print("  3. Set up HTTPS (see DEPLOYMENT_GUIDE.md)")
    print("  4. Test security features")
    print("  5. Deploy to production")
    print("\n✓ Setup complete!\n")

if __name__ == '__main__':
    try:
        generate_env_file()
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
