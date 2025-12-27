"""
face_processor.py

RAM-only face detection and embedding generation
No disk I/O - processes images entirely in memory
"""

import io
import logging
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image
from mtcnn import MTCNN
from keras_facenet import FaceNet

import config

logger = logging.getLogger(__name__)


class FaceProcessor:
    """Detects faces and generates embeddings entirely in RAM"""
    
    def __init__(self):
        """Initialize face detector and embedding model"""
        logger.info("Initializing face processor...")
        self.detector = MTCNN()
        self.embedder = FaceNet()
        logger.info("Face processor ready (MTCNN + FaceNet)")
    
    def process_image_bytes(
        self,
        image_bytes: bytes,
        image_url: str
    ) -> List[Tuple[Tuple[int, int, int, int], float, bytes, np.ndarray]]:
        """
        Process image from bytes - completely in RAM
        
        Args:
            image_bytes: Raw image data
            image_url: Source URL (for logging only)
        
        Returns:
            List of (bbox, confidence, thumbnail_bytes, embedding) for each face
            Empty list if no faces detected
        """
        try:
            # Load image to RAM
            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            image_array = np.array(image)
            
        except Exception as e:
            logger.warning(f"Failed to load image {image_url}: {e}")
            return []
        
        # Detect faces
        try:
            detections = self.detector.detect_faces(image_array)
        except Exception as e:
            logger.warning(f"Face detection failed for {image_url}: {e}")
            return []
        
        if not detections:
            logger.debug(f"No faces in {image_url}")
            return []
        
        logger.info(f"Found {len(detections)} face(s) in {image_url}")
        
        # Process each face
        results = []
        for i, detection in enumerate(detections):
            confidence = detection['confidence']
            
            # Skip low confidence faces
            if confidence < config.MIN_FACE_CONFIDENCE:
                logger.debug(f"  Face {i+1}: {confidence:.2%} (skipped - below threshold)")
                continue
            
            bbox = detection['box']  # [x, y, width, height]
            x, y, w, h = bbox
            
            # Extract face region
            try:
                face_image = image.crop((x, y, x+w, y+h))
            except Exception as e:
                logger.warning(f"  Face {i+1}: Failed to crop - {e}")
                continue
            
            # Create thumbnail in RAM
            try:
                thumbnail = face_image.resize(config.THUMBNAIL_SIZE, Image.LANCZOS)
                thumb_buffer = io.BytesIO()
                thumbnail.save(thumb_buffer, format='JPEG', quality=config.THUMBNAIL_QUALITY)
                thumbnail_bytes = thumb_buffer.getvalue()
            except Exception as e:
                logger.warning(f"  Face {i+1}: Failed to create thumbnail - {e}")
                continue
            
            # Generate embedding from thumbnail
            try:
                thumbnail_array = np.array(thumbnail)
                # FaceNet expects 160x160, resize if needed
                if thumbnail_array.shape[:2] != (160, 160):
                    resized = Image.fromarray(thumbnail_array).resize((160, 160), Image.LANCZOS)
                    thumbnail_array = np.array(resized)
                
                # Get embedding
                embedding = self.embedder.embeddings([thumbnail_array])[0]
                
            except Exception as e:
                logger.warning(f"  Face {i+1}: Failed to generate embedding - {e}")
                continue
            
            logger.info(f"  Face {i+1}: {confidence:.2%} confidence ✓")
            results.append(((x, y, w, h), confidence, thumbnail_bytes, embedding))
        
        return results
    
    def process_user_photo(self, image_bytes: bytes) -> Optional[np.ndarray]:
        """
        Process user-uploaded photo and return embedding
        
        Args:
            image_bytes: Raw image data from user upload
        
        Returns:
            128-dim embedding array, or None if no face detected
        """
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            image_array = np.array(image)
        except Exception as e:
            logger.error(f"Failed to load user photo: {e}")
            return None
        
        # Detect face
        try:
            detections = self.detector.detect_faces(image_array)
        except Exception as e:
            logger.error(f"Face detection failed on user photo: {e}")
            return None
        
        if not detections:
            logger.warning("No face detected in user photo")
            return None
        
        if len(detections) > 1:
            logger.warning(f"Multiple faces detected ({len(detections)}), using first one")
        
        # Use the face with highest confidence
        best_detection = max(detections, key=lambda d: d['confidence'])
        bbox = best_detection['box']
        confidence = best_detection['confidence']
        
        logger.info(f"Detected face in user photo (confidence: {confidence:.2%})")
        
        # Extract and process face
        x, y, w, h = bbox
        face_image = image.crop((x, y, x+w, y+h))
        face_image = face_image.resize((160, 160), Image.LANCZOS)
        face_array = np.array(face_image)
        
        # Generate embedding
        try:
            embedding = self.embedder.embeddings([face_array])[0]
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None


if __name__ == '__main__':
    # Test the processor
    logging.basicConfig(level=logging.INFO)
    
    processor = FaceProcessor()
    
    # Test with a sample image URL
    import requests
    test_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Cat03.jpg/1200px-Cat03.jpg"
    
    print(f"\nTesting with: {test_url}")
    response = requests.get(test_url, timeout=10)
    
    if response.status_code == 200:
        results = processor.process_image_bytes(response.content, test_url)
        print(f"\nResults: {len(results)} face(s) processed")
        for i, (bbox, conf, thumb_bytes, emb) in enumerate(results):
            print(f"  Face {i+1}: bbox={bbox}, confidence={conf:.2%}, "
                  f"thumbnail={len(thumb_bytes)} bytes, embedding shape={emb.shape}")
