"""
View Face Recognition Database
Simple script to browse database contents
"""

import sqlite3
from datetime import datetime

def view_database(db_path='face_recognition.db'):
    """View database contents in a user-friendly format"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n" + "="*70)
    print("FACE RECOGNITION DATABASE VIEWER")
    print("="*70)
    
    # Summary Statistics
    print("\n📊 SUMMARY STATISTICS:")
    print("-" * 70)
    
    cursor.execute("SELECT COUNT(*) FROM websites")
    print(f"Total Websites: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM images")
    print(f"Total Images: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM faces")
    total_faces = cursor.fetchone()[0]
    print(f"Total Faces: {total_faces}")
    
    # Count faces with embeddings (v3 schema - embeddings in separate table)
    cursor.execute("SELECT COUNT(*) FROM embeddings WHERE is_active = TRUE")
    print(f"Total Embeddings: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM face_thumbnails")
    print(f"Total Thumbnails: {cursor.fetchone()[0]}")
    
    # Website Details
    print("\n🌐 WEBSITES:")
    print("-" * 70)
    cursor.execute("""
        SELECT id, url, status, total_images, scraped_at 
        FROM websites 
        ORDER BY scraped_at DESC
    """)
    
    for row in cursor.fetchall():
        website_id, url, status, total_imgs, scraped_at = row
        print(f"\n  ID: {website_id}")
        print(f"  URL: {url}")
        print(f"  Status: {status}")
        print(f"  Images Scraped: {total_imgs}")
        print(f"  Scraped At: {scraped_at}")
    
    # Face Statistics
    print("\n😊 FACE DETECTION STATISTICS:")
    print("-" * 70)
    
    cursor.execute("SELECT AVG(confidence), MIN(confidence), MAX(confidence) FROM faces")
    avg, min_conf, max_conf = cursor.fetchone()
    if avg:
        print(f"Average Confidence: {avg:.2%}")
        print(f"Minimum Confidence: {min_conf:.2%}")
        print(f"Maximum Confidence: {max_conf:.2%}")
    
    cursor.execute("SELECT COUNT(*) FROM faces WHERE confidence >= 0.95")
    print(f"High Confidence Faces (≥95%): {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM faces WHERE confidence >= 0.90")
    print(f"Good Confidence Faces (≥90%): {cursor.fetchone()[0]}")
    
    # Top 10 Most Confident Faces
    print("\n🎯 TOP 10 MOST CONFIDENT FACE DETECTIONS:")
    print("-" * 70)
    cursor.execute("""
        SELECT f.id, f.confidence, f.bbox_x, f.bbox_y, f.bbox_width, f.bbox_height,
               i.image_url
        FROM faces f
        JOIN images i ON f.image_id = i.id
        ORDER BY f.confidence DESC
        LIMIT 10
    """)
    
    for idx, row in enumerate(cursor.fetchall(), 1):
        face_id, conf, x, y, w, h, img_url = row
        print(f"\n  {idx}. Face ID: {face_id}")
        print(f"     Confidence: {conf:.2%}")
        print(f"     Location: ({x}, {y}) - Size: {w}x{h}px")
        print(f"     Image: {img_url[:80]}...")
    
    # Images with Most Faces
    print("\n🖼️  IMAGES WITH MOST FACES:")
    print("-" * 70)
    cursor.execute("""
        SELECT i.image_url, COUNT(f.id) as face_count
        FROM images i
        LEFT JOIN faces f ON i.id = f.image_id
        GROUP BY i.id
        HAVING face_count > 0
        ORDER BY face_count DESC
        LIMIT 5
    """)
    
    for idx, row in enumerate(cursor.fetchall(), 1):
        img_url, face_count = row
        print(f"\n  {idx}. {face_count} face(s)")
        print(f"     {img_url[:70]}...")
    
    # FAISS Index Info
    print("\n🔍 FAISS INDEX:")
    print("-" * 70)
    try:
        with open('faiss_index.bin', 'rb') as f:
            size_bytes = len(f.read())
            size_mb = size_bytes / (1024 * 1024)
            print(f"Index File Size: {size_mb:.2f} MB")
            print(f"Vectors Indexed: {total_faces}")
            print(f"Dimensions: 512")
    except FileNotFoundError:
        print("FAISS index not found!")
    
    print("\n" + "="*70)
    print("✓ Database view complete")
    print("="*70 + "\n")
    
    conn.close()


if __name__ == "__main__":
    view_database()
