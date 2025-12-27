"""
database_manager.py

Database Manager for OSINT Face Recognition System
Handles all database operations (SQLite/PostgreSQL)
"""

import os
import sqlite3
import pickle
import io
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import numpy as np
from PIL import Image


class DatabaseManager:
    """
    Manages database operations for face recognition system.
    Supports SQLite and PostgreSQL.
    """
    
    def __init__(self, db_path: str = "face_recognition.db", db_type: str = "sqlite"):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to database file (SQLite) or connection string (PostgreSQL)
            db_type: 'sqlite' or 'postgresql'
        """
        self.db_path = db_path
        self.db_type = db_type
        self.conn = None
        self._connect()
        self._create_tables()
    
    def _connect(self):
        """Establish database connection."""
        if self.db_type == "sqlite":
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        elif self.db_type == "postgresql":
            import psycopg2
            self.conn = psycopg2.connect(self.db_path)
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")
    
    def _create_tables(self):
        """Create all required tables."""
        # Find schema file - check if it's in the same directory or use absolute path
        schema_path = 'database_schema_v3.sql'
        if not os.path.exists(schema_path):
            # Try in the script's directory
            script_dir = os.path.dirname(os.path.abspath(__file__))
            schema_path = os.path.join(script_dir, 'database_schema_v3.sql')
        
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = f.read()
        
        cursor = self.conn.cursor()
        cursor.executescript(schema) if self.db_type == "sqlite" else cursor.execute(schema)
        self.conn.commit()
    
    # ========================================
    # WEBSITE OPERATIONS
    # ========================================
    
    def add_website(self, url: str) -> int:
        """
        Add a website to database (or return existing ID if already exists).
        
        Args:
            url: Website URL
            
        Returns:
            website_id
        """
        cursor = self.conn.cursor()
        
        # Check if website already exists
        cursor.execute("SELECT id FROM websites WHERE url = ?", (url,))
        row = cursor.fetchone()
        if row:
            return row[0]
        
        # Insert new website
        cursor.execute(
            "INSERT INTO websites (url, scraped_at, status) VALUES (?, ?, ?)",
            (url, datetime.utcnow(), 'pending')
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def update_website_status(self, website_id: int, status: str, total_images: int = 0, total_faces: int = 0):
        """Update website scraping status."""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE websites SET status = ?, total_images = ? WHERE id = ?",
            (status, total_images, website_id)
        )
        self.conn.commit()
    
    # ========================================
    # IMAGE OPERATIONS
    # ========================================
    
    def add_image(self, website_id: int, image_url: str, width: int = None, height: int = None) -> int:
        """
        Add an image to database (RAM-only architecture - no filename storage).
        Handles duplicates gracefully by returning existing image_id.
        
        Args:
            website_id: ID of parent website
            image_url: Original image URL
            width: Image width
            height: Image height
            
        Returns:
            image_id (new or existing)
        """
        cursor = self.conn.cursor()
        
        # Try to insert, if URL already exists, get the existing ID
        try:
            cursor.execute(
                """INSERT INTO images 
                   (website_id, image_url, width, height, scraped_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (website_id, image_url, width, height, datetime.utcnow())
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # Image URL already exists, return existing ID
            cursor.execute(
                """SELECT id FROM images WHERE image_url = ? AND is_active = TRUE""",
                (image_url,)
            )
            row = cursor.fetchone()
            return row[0] if row else None
    
    def insert_image(self, website_id: int, image_url: str, width: int = None, height: int = None) -> int:
        """
        Insert an image (convenience method for pipeline).
        
        Args:
            website_id: ID of parent website
            image_url: Original image URL
            width: Image width
            height: Image height
            
        Returns:
            image_id
        """
        return self.add_image(website_id, image_url, width, height)
    
    def update_image_has_faces(self, image_id: int, has_faces: bool):
        """Update whether image contains faces."""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE images SET has_faces = ? WHERE id = ?",
            (1 if has_faces else 0, image_id)
        )
        self.conn.commit()
    
    def get_images_without_faces(self, website_id: int = None) -> List[Dict]:
        """Get all images that don't have faces."""
        cursor = self.conn.cursor()
        if website_id:
            cursor.execute(
                "SELECT * FROM images WHERE has_faces = 0 AND website_id = ?",
                (website_id,)
            )
        else:
            cursor.execute("SELECT * FROM images WHERE has_faces = 0")
        
        return [dict(row) for row in cursor.fetchall()]
    
    # ========================================
    # FACE OPERATIONS
    # ========================================
    
    def add_face(self, image_id: int, bbox: Tuple[int, int, int, int],
                 confidence: float, detector: str = "MTCNN") -> int:
        """
        Add a detected face to database.
        
        Args:
            image_id: ID of parent image
            bbox: Bounding box (x, y, width, height)
            confidence: Detection confidence
            detector: Detector name
            
        Returns:
            face_id
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO faces 
               (image_id, bbox_x, bbox_y, bbox_width, bbox_height, confidence, detector, detected_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (image_id, bbox[0], bbox[1], bbox[2], bbox[3], confidence, detector, datetime.utcnow())
        )
        self.conn.commit()
        
        # Update parent image
        self.update_image_has_faces(image_id, True)
        
        return cursor.lastrowid
    
    def add_face_thumbnail(self, face_id: int, thumbnail_image: Image.Image):
        """
        Add face thumbnail to database.
        
        Args:
            face_id: ID of face
            thumbnail_image: PIL Image object
        """
        # Convert PIL Image to bytes
        buffer = io.BytesIO()
        thumbnail_image.save(buffer, format='JPEG')
        thumbnail_bytes = buffer.getvalue()
        
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO face_thumbnails (face_id, thumbnail_blob, width, height)
               VALUES (?, ?, ?, ?)""",
            (face_id, thumbnail_bytes, thumbnail_image.width, thumbnail_image.height)
        )
        self.conn.commit()
    
    def get_face_thumbnail(self, face_id: int) -> Optional[Image.Image]:
        """Get face thumbnail as PIL Image."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT thumbnail_blob FROM face_thumbnails WHERE face_id = ?",
            (face_id,)
        )
        row = cursor.fetchone()
        
        if row:
            thumbnail_bytes = row[0]
            return Image.open(io.BytesIO(thumbnail_bytes))
        return None
    
    # ========================================
    # EMBEDDING OPERATIONS (v2 schema - embeddings stored in faces table)
    # ========================================
    
    def add_embedding(self, face_id: int, embedding_vector: np.ndarray,
                     model: str = "FaceNet", dimensions: int = 512) -> int:
        """
        Add/Update face embedding in embeddings table (v3 schema).
        
        Args:
            face_id: ID of face
            embedding_vector: Numpy array (512-dimensional for FaceNet)
            model: Model name
            dimensions: Vector dimensions
            
        Returns:
            face_id (updated row)
        """
        # Serialize numpy array to bytes
        embedding_bytes = pickle.dumps(embedding_vector)
        
        # Calculate hash for deduplication
        import hashlib
        embedding_hash = hashlib.sha256(embedding_bytes).hexdigest()
        
        cursor = self.conn.cursor()
        # Insert into embeddings table (v3 schema)
        cursor.execute(
            """INSERT OR REPLACE INTO embeddings 
               (face_id, embedding_vector, embedding_model, embedding_dimensions, embedding_hash)
               VALUES (?, ?, ?, ?, ?)""",
            (face_id, embedding_bytes, model, dimensions, embedding_hash)
        )
        self.conn.commit()
        return face_id
    
    def get_embedding(self, face_id: int) -> Optional[np.ndarray]:
        """
        Get face embedding as numpy array from faces table (v2 schema).
        
        Args:
            face_id: ID of face
            
        Returns:
            Numpy array or None
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT embedding_vector FROM embeddings WHERE face_id = ? AND is_active = TRUE",
            (face_id,)
        )
        row = cursor.fetchone()
        
        if row and row[0]:
            embedding_bytes = row[0]
            return pickle.loads(embedding_bytes)
        return None
    
    def insert_face_complete(self, image_id: int, bbox: Tuple[int, int, int, int], 
                            confidence: float, thumbnail_bytes: bytes, 
                            embedding: np.ndarray) -> int:
        """
        Convenience method to insert face with thumbnail and embedding in one call.
        Used by main pipeline for efficient insertion.
        
        Args:
            image_id: ID of parent image
            bbox: Bounding box (x, y, width, height)
            confidence: Detection confidence
            thumbnail_bytes: Face thumbnail as bytes
            embedding: Face embedding vector
            
        Returns:
            face_id
        """
        # Insert face
        face_id = self.add_face(image_id, bbox, confidence, detector="MTCNN")
        
        # Convert thumbnail bytes to PIL Image and save
        thumbnail_image = Image.open(io.BytesIO(thumbnail_bytes))
        self.add_face_thumbnail(face_id, thumbnail_image)
        
        # Add embedding (FaceNet produces 512-dimensional vectors)
        self.add_embedding(face_id, embedding, model="FaceNet", dimensions=512)
        
        return face_id
    
    def get_all_embeddings(self, limit: int = None) -> List[Tuple[int, np.ndarray]]:
        """
        Get all embeddings from faces table (v2 schema).
        
        Args:
            limit: Maximum number of embeddings to return
            
        Returns:
            List of (face_id, embedding_vector) tuples
        """
        cursor = self.conn.cursor()
        query = "SELECT face_id, embedding_vector FROM embeddings WHERE is_active = TRUE"
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        
        results = []
        for row in cursor.fetchall():
            face_id = row[0]
            embedding_bytes = row[1]
            if embedding_bytes:
                embedding = pickle.loads(embedding_bytes)
                results.append((face_id, embedding))
        
        return results
    
    # ========================================
    # QUERY OPERATIONS
    # ========================================
    
    def get_face_details(self, face_id: int) -> Optional[Dict]:
        """Get complete face information."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM v_faces_complete WHERE face_id = ?",
            (face_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_all_faces(self, website_id: int = None, limit: int = None) -> List[Dict]:
        """Get all faces with complete information."""
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM v_faces_complete"
        params = []
        
        if website_id:
            query += " WHERE website_id = ?"
            params.append(website_id)
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_statistics(self) -> Dict:
        """Get database statistics."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM v_statistics")
        row = cursor.fetchone()
        return dict(row) if row else {}
    
    def search_similar_faces(self, query_embedding: np.ndarray, threshold: float = 0.6) -> List[Dict]:
        """
        Search for similar faces using cosine similarity.
        Note: This is a basic implementation. For large datasets, use FAISS.
        
        Args:
            query_embedding: Query embedding vector
            threshold: Similarity threshold (0-1)
            
        Returns:
            List of matching faces with similarity scores
        """
        all_embeddings = self.get_all_embeddings()
        results = []
        
        for face_id, embedding in all_embeddings:
            # Calculate cosine similarity
            similarity = 1 - np.dot(query_embedding, embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(embedding)
            )
            
            if similarity >= threshold:
                face_details = self.get_face_details(face_id)
                face_details['similarity'] = float(similarity)
                results.append(face_details)
        
        # Sort by similarity (highest first)
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results
    
    # ========================================
    # CLUSTERING OPERATIONS
    # ========================================
    
    def get_cluster_statistics(self) -> Dict:
        """Get clustering statistics."""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM face_clusters")
        total_clusters = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM face_cluster_members")
        total_members = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(face_count) FROM face_clusters")
        avg_cluster_size = cursor.fetchone()[0] or 0
        
        return {
            'total_clusters': total_clusters,
            'total_clustered_faces': total_members,
            'avg_cluster_size': float(avg_cluster_size)
        }
    
    def get_face_cluster(self, face_id: int) -> Optional[int]:
        """
        Get the cluster ID for a given face.
        
        Args:
            face_id: ID of the face
            
        Returns:
            cluster_id or None if face is not in any cluster
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT cluster_id FROM face_cluster_members WHERE face_id = ?",
            (face_id,)
        )
        row = cursor.fetchone()
        return row[0] if row else None

    # ========================================
    # UTILITY OPERATIONS
    # ========================================
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# ========================================
# EXAMPLE USAGE
# ========================================

if __name__ == "__main__":
    # Initialize database
    db = DatabaseManager("face_recognition.db")
    
    # Add a website
    website_id = db.add_website("https://example.com")
    print(f"Added website with ID: {website_id}")
    
    # Add an image
    image_id = db.add_image(
        website_id=website_id,
        image_url="https://example.com/image.jpg",
        filename="image.jpg",
        width=1920,
        height=1080
    )
    print(f"Added image with ID: {image_id}")
    
    # Add a face
    face_id = db.add_face(
        image_id=image_id,
        bbox=(100, 100, 200, 200),
        confidence=0.95
    )
    print(f"Added face with ID: {face_id}")
    
    # Add embedding
    dummy_embedding = np.random.rand(128)
    embedding_id = db.add_embedding(face_id, dummy_embedding)
    print(f"Added embedding with ID: {embedding_id}")
    
    # Get statistics
    stats = db.get_statistics()
    print(f"\nDatabase Statistics:")
    print(f"Total Websites: {stats.get('active_websites', 0)}")
    print(f"Total Images: {stats.get('active_images', 0)}")
    print(f"Total Faces: {stats.get('active_faces', 0)}")
    print(f"Total Embeddings: {stats.get('active_embeddings', 0)}")
    
    db.close()
