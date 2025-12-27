"""
search_api.py

Simple search API for user queries
Upload face photo → Get matching faces from database
"""

import argparse
import base64
import json
import logging
from datetime import datetime

from database_manager import DatabaseManager
from face_processor import FaceProcessor
from faiss_manager import FAISSManager
import config

logger = logging.getLogger(__name__)


def search_face(
    image_path: str,
    db: DatabaseManager,
    faiss: FAISSManager,
    face_proc: FaceProcessor,
    top_k: int = 50,
    min_similarity: float = None
) -> dict:
    """
    Search for similar faces
    
    Args:
        image_path: Path to user's face photo
        db: Database manager
        faiss: FAISS manager
        face_proc: Face processor
        top_k: Number of results to return
        min_similarity: Minimum similarity threshold
    
    Returns:
        Dict with search results
    """
    min_similarity = min_similarity or config.MIN_SIMILARITY_THRESHOLD
    
    logger.info(f"Searching with: {image_path}")
    
    # Load user image
    with open(image_path, 'rb') as f:
        image_bytes = f.read()
    
    # Generate embedding
    logger.info("Detecting face and generating embedding...")
    embedding = face_proc.process_user_photo(image_bytes)
    
    if embedding is None:
        return {
            'success': False,
            'error': 'No face detected in uploaded image',
            'results': []
        }
    
    logger.info("✓ Embedding generated")
    
    # Search FAISS
    logger.info(f"Searching FAISS index (min similarity: {min_similarity:.0%})...")
    similarities, face_ids = faiss.search(
        embedding,
        k=top_k,
        threshold=min_similarity
    )
    
    if not face_ids:
        return {
            'success': True,
            'message': f'No matches found above {min_similarity:.0%} similarity',
            'results': []
        }
    
    logger.info(f"✓ Found {len(face_ids)} matches")
    
    # Get details from database
    logger.info("Retrieving details from database...")
    face_details = db.get_face_details(face_ids)
    
    # Combine with similarity scores
    results = []
    for i, detail in enumerate(face_details):
        # Find matching similarity score
        similarity = similarities[face_ids.index(detail['face_id'])]
        
        # Convert thumbnail to base64 for JSON
        thumbnail_base64 = base64.b64encode(detail['thumbnail']).decode('utf-8')
        
        results.append({
            'face_id': detail['face_id'],
            'similarity': f"{similarity:.1%}",
            'similarity_score': float(similarity),
            'thumbnail': thumbnail_base64,
            'thumbnail_format': detail['thumbnail_format'],
            'source_image_url': detail['image_url'],
            'website_url': detail['website_url'],
            'website_name': detail['website_name'],
            'detection_confidence': f"{detail['confidence']:.1%}",
            'bbox': {
                'x': detail['bbox_x'],
                'y': detail['bbox_y'],
                'width': detail['bbox_width'],
                'height': detail['bbox_height']
            },
            'detected_at': detail['detected_at'].isoformat() if hasattr(detail['detected_at'], 'isoformat') else str(detail['detected_at'])
        })
    
    # Sort by similarity (highest first)
    results.sort(key=lambda x: x['similarity_score'], reverse=True)
    
    return {
        'success': True,
        'query_time': datetime.utcnow().isoformat() + 'Z',
        'total_matches': len(results),
        'min_similarity_threshold': f"{min_similarity:.0%}",
        'results': results
    }


def main():
    """Command-line interface for search"""
    parser = argparse.ArgumentParser(
        description="Search for similar faces in database"
    )
    parser.add_argument(
        '--image',
        required=True,
        help='Path to user face photo'
    )
    parser.add_argument(
        '--top-k',
        type=int,
        default=50,
        help='Maximum number of results (default: 50)'
    )
    parser.add_argument(
        '--min-similarity',
        type=float,
        default=config.MIN_SIMILARITY_THRESHOLD,
        help='Minimum similarity threshold 0.0-1.0 (default: 0.70)'
    )
    parser.add_argument(
        '--output',
        help='Save results to JSON file (optional)'
    )
    parser.add_argument(
        '--db-type',
        choices=['sqlite', 'postgresql'],
        default=config.DB_TYPE,
        help='Database type'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format=config.LOG_FORMAT
    )
    
    logger.info("="*70)
    logger.info("FACE SEARCH")
    logger.info("="*70)
    
    # Initialize components
    logger.info("Loading components...")
    db = DatabaseManager(args.db_type)
    faiss_mgr = FAISSManager()
    face_processor = FaceProcessor()
    
    if faiss_mgr.get_total_vectors() == 0:
        logger.error("FAISS index is empty! Run main_pipeline.py first to collect faces.")
        return
    
    logger.info(f"✓ FAISS index loaded ({faiss_mgr.get_total_vectors()} faces)")
    
    # Perform search
    result = search_face(
        args.image,
        db,
        faiss_mgr,
        face_processor,
        top_k=args.top_k,
        min_similarity=args.min_similarity
    )
    
    # Display results
    logger.info("\n" + "="*70)
    logger.info("SEARCH RESULTS")
    logger.info("="*70)
    
    if not result['success']:
        logger.error(f"Error: {result['error']}")
        return
    
    if not result['results']:
        logger.info(result.get('message', 'No matches found'))
        return
    
    logger.info(f"Found {result['total_matches']} matches:\n")
    
    for i, match in enumerate(result['results'][:10], 1):  # Show top 10
        logger.info(f"{i}. Similarity: {match['similarity']}")
        logger.info(f"   Website: {match['website_name']}")
        logger.info(f"   Source: {match['source_image_url']}")
        logger.info(f"   Detection: {match['detection_confidence']} confidence")
        logger.info(f"   Detected: {match['detected_at']}")
        logger.info("")
    
    if result['total_matches'] > 10:
        logger.info(f"... and {result['total_matches'] - 10} more matches")
    
    # Save to file if requested
    if args.output:
        # Remove thumbnail data for file output (too large)
        output_data = result.copy()
        for match in output_data['results']:
            match['thumbnail'] = f"<{len(match['thumbnail'])} bytes>"
        
        with open(args.output, 'w') as f:
            json.dump(output_data, f, indent=2)
        logger.info(f"\n✓ Results saved to {args.output}")
    
    db.close()
    logger.info("\n" + "="*70)


if __name__ == '__main__':
    main()
