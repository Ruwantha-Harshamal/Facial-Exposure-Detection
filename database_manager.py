"""
database_manager.py

Database Manager for Face Recognition System
Handles all SQLite database operations
"""

import os
import sqlite3
import io
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages database operations for face recognition system.
    Uses SQLite for data storage.
    """
    
    def __init__(self, db_path: str = "face_recognition.db", db_type: str = "sqlite"):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
            db_type: Database type (only 'sqlite' supported)
        """
        self.db_path = db_path
        self.db_type = db_type
        self.conn = None
        self._connect()
        self._create_tables()
    
    def _connect(self):
        """Establish database connection."""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    
    def _create_tables(self):
        """Create all required tables from schema file."""
        # Find schema file
        schema_path = 'database_schema_v3.sql'
        if not os.path.exists(schema_path):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            schema_path = os.path.join(script_dir, 'database_schema_v3.sql')
        
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = f.read()
        
        cursor = self.conn.cursor()
        cursor.executescript(schema)
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
            "UPDATE websites SET status = ?, total_images = ?, total_faces = ? WHERE id = ?",
            (status, total_images, total_faces, website_id)
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
    # EMBEDDING OPERATIONS
    # ========================================
    
    def add_embedding(self, face_id: int, embedding_vector: np.ndarray,
                     model: str = "FaceNet", dimensions: int = 512) -> int:
        """
        Add/Update face embedding in embeddings table.
        
        Args:
            face_id: ID of face
            embedding_vector: Numpy array (512-dimensional for FaceNet)
            model: Model name
            dimensions: Vector dimensions
            
        Returns:
            face_id
        """
        import hashlib
        
        # SECURITY FIX: Use safe numpy serialization instead of pickle
        # Convert numpy array to bytes (more secure than pickle)
        embedding_bytes = embedding_vector.astype(np.float32).tobytes()
        
        # Calculate hash for deduplication
        embedding_hash = hashlib.sha256(embedding_bytes).hexdigest()
        
        cursor = self.conn.cursor()
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
        Get face embedding as numpy array.
        
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
            # SECURITY FIX: Deserialize numpy array safely (no pickle vulnerability)
            embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
            return embedding
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
        Get all embeddings from database.
        
        Args:
            limit: Maximum number of embeddings to return
            
        Returns:
            List of (face_id, embedding_vector) tuples
        """
        cursor = self.conn.cursor()
        query = "SELECT face_id, embedding_vector FROM embeddings WHERE is_active = TRUE"
        
        # SECURITY FIX: Use parameterized query for LIMIT clause
        if limit:
            cursor.execute(query + " LIMIT ?", (limit,))
        else:
            cursor.execute(query)
        
        results = []
        for row in cursor.fetchall():
            face_id = row[0]
            embedding_bytes = row[1]
            if embedding_bytes:
                # SECURITY FIX: Deserialize numpy array safely (no pickle vulnerability)
                embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
                results.append((face_id, embedding))
        
        return results
    
    def get_face_ids_by_website(self, website_id: int) -> List[int]:
        """
        Get all face IDs for a specific website.
        Used for FAISS deletion when deleting a website.
        
        Args:
            website_id: ID of website
            
        Returns:
            List of face IDs
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT f.id FROM faces f
               JOIN images i ON f.image_id = i.id
               WHERE i.website_id = ? AND f.deleted_at IS NULL""",
            (website_id,)
        )
        return [row[0] for row in cursor.fetchall()]
    
    def delete_website_complete(self, website_id: int) -> Dict:
        """
        Completely delete a website and all related data.
        This is a HARD DELETE (permanent removal, not soft delete).
        
        Deletes:
        - Website record
        - All images
        - All faces
        - All face thumbnails
        - All embeddings
        
        Note: FAISS vectors must be deleted separately by caller.
        
        Args:
            website_id: ID of website to delete
            
        Returns:
            Dictionary with deletion statistics
        """
        cursor = self.conn.cursor()
        
        # Get statistics before deletion
        cursor.execute(
            """SELECT COUNT(DISTINCT i.id) as images, COUNT(DISTINCT f.id) as faces
               FROM images i
               LEFT JOIN faces f ON i.id = f.image_id
               WHERE i.website_id = ? AND i.deleted_at IS NULL""",
            (website_id,)
        )
        stats = cursor.fetchone()
        image_count = stats[0] if stats else 0
        face_count = stats[1] if stats else 0
        
        # Delete in correct order (respect foreign keys)
        # 1. Delete embeddings
        cursor.execute(
            """DELETE FROM embeddings WHERE face_id IN (
               SELECT f.id FROM faces f JOIN images i ON f.image_id = i.id WHERE i.website_id = ?)""",
            (website_id,)
        )
        
        # 2. Delete face thumbnails
        cursor.execute(
            """DELETE FROM face_thumbnails WHERE face_id IN (
               SELECT f.id FROM faces f JOIN images i ON f.image_id = i.id WHERE i.website_id = ?)""",
            (website_id,)
        )
        
        # 3. Delete faces
        cursor.execute(
            "DELETE FROM faces WHERE image_id IN (SELECT id FROM images WHERE website_id = ?)",
            (website_id,)
        )
        
        # 4. Delete images
        cursor.execute("DELETE FROM images WHERE website_id = ?", (website_id,))
        
        # 5. Delete website
        cursor.execute("DELETE FROM websites WHERE id = ?", (website_id,))
        
        self.conn.commit()
        
        logger.info("Deleted website %d: %d images, %d faces", website_id, image_count, face_count)
        
        return {
            'deleted_images': image_count,
            'deleted_faces': face_count
        }
    
    # ========================================
    # QUERY OPERATIONS
    # ========================================
    
    def get_statistics(self) -> Dict:
        """Get database statistics."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM v_statistics")
        row = cursor.fetchone()
        return dict(row) if row else {}
    
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
