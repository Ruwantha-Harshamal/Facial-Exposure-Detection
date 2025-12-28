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
            
        except Exception as e:  # Catch all image loading errors
            logger.warning("Failed to load image %s: %s", image_url, e)
            return []
        
        # Detect faces
        try:
            detections = self.detector.detect_faces(image_array)
        except Exception as e:  # Catch all detection errors
            logger.warning("Face detection failed for %s: %s", image_url, e)
            return []
        
        if not detections:
            logger.debug("No faces in %s", image_url)
            return []
        
        logger.info("Found %d face(s) in %s", len(detections), image_url)
        
        # Process each face
        results = []
        for i, detection in enumerate(detections):
            confidence = detection['confidence']
            
            # Skip low confidence faces
            if confidence < config.MIN_FACE_CONFIDENCE:
                logger.debug("  Face %d: %.2f%% (skipped - below threshold)", i+1, confidence * 100)
                continue
            
            bbox = detection['box']  # [x, y, width, height]
            x, y, w, h = bbox
            
            # Extract face region
            try:
                face_image = image.crop((x, y, x+w, y+h))
            except Exception as e:  # Catch all crop errors
                logger.warning("  Face %d: Failed to crop - %s", i+1, e)
                continue
            
            # Create thumbnail in RAM
            try:
                thumbnail = face_image.resize(config.THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
                thumb_buffer = io.BytesIO()
                thumbnail.save(thumb_buffer, format='JPEG', quality=config.THUMBNAIL_QUALITY)
                thumbnail_bytes = thumb_buffer.getvalue()
            except Exception as e:  # Catch all thumbnail errors
                logger.warning("  Face %d: Failed to create thumbnail - %s", i+1, e)
                continue
            
            # Generate embedding from thumbnail
            try:
                thumbnail_array = np.array(thumbnail)
                # FaceNet expects 160x160, resize if needed
                if thumbnail_array.shape[:2] != (160, 160):
                    resized = Image.fromarray(thumbnail_array).resize((160, 160), Image.Resampling.LANCZOS)
                    thumbnail_array = np.array(resized)
                
                # Get embedding
                embedding = self.embedder.embeddings([thumbnail_array])[0]
                
            except Exception as e:  # Catch all embedding errors
                logger.warning("  Face %d: Failed to generate embedding - %s", i+1, e)
                continue
            
            logger.info("  Face %d: %.2f%% confidence ✓", i+1, confidence * 100)
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
        except Exception as e:  # Catch all image loading errors
            logger.error("Failed to load user photo: %s", e)
            return None
        
        # Detect face
        try:
            detections = self.detector.detect_faces(image_array)
        except Exception as e:  # Catch all detection errors
            logger.error("Face detection failed on user photo: %s", e)
            return None
        
        if not detections:
            logger.warning("No face detected in user photo")
            return None
        
        if len(detections) > 1:
            logger.warning("Multiple faces detected (%d), using first one", len(detections))
        
        # Use the face with highest confidence
        best_detection = max(detections, key=lambda d: d['confidence'])
        bbox = best_detection['box']
        confidence = best_detection['confidence']
        
        logger.info("Detected face in user photo (confidence: %.2f%%)", confidence * 100)
        
        # Extract and process face
        x, y, w, h = bbox
        face_image = image.crop((x, y, x+w, y+h))
        face_image = face_image.resize((160, 160), Image.Resampling.LANCZOS)
        face_array = np.array(face_image)
        
        # Generate embedding
        try:
            embedding = self.embedder.embeddings([face_array])[0]
            return embedding
        except Exception as e:  # Catch all embedding errors
            logger.error("Failed to generate embedding: %s", e)
            return None
