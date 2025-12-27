"""
process_batch.py

Batch processing script for multiple websites
Reads URLs from a file and processes them sequentially
"""

import argparse
import logging
import sys
from pathlib import Path

from database_manager import DatabaseManager
from face_processor import FaceProcessor
from faiss_manager import FAISSManager
from main_pipeline import process_website
from scraper import WebScraper
from face_clustering import auto_cluster
import config

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT,
    handlers=[
        logging.FileHandler('batch_processing.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def read_urls_from_file(filepath: str) -> list:
    """
    Read URLs from a text file (one URL per line)
    
    Args:
        filepath: Path to file containing URLs
    
    Returns:
        List of URLs
    """
    urls = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if line and not line.startswith('#'):
                urls.append(line)
    return urls


def main():
    parser = argparse.ArgumentParser(
        description='Batch process multiple websites for face recognition'
    )
    parser.add_argument(
        '--urls',
        type=str,
        required=True,
        help='Path to file containing website URLs (one per line)'
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        default=True,
        help='Run browser in headless mode (default: True)'
    )
    parser.add_argument(
        '--skip-errors',
        action='store_true',
        help='Continue processing even if a website fails'
    )
    
    args = parser.parse_args()
    
    # Read URLs from file
    logger.info(f"Reading URLs from: {args.urls}")
    try:
        urls = read_urls_from_file(args.urls)
    except FileNotFoundError:
        logger.error(f"File not found: {args.urls}")
        sys.exit(1)
    
    if not urls:
        logger.error("No URLs found in file")
        sys.exit(1)
    
    logger.info(f"Found {len(urls)} websites to process")
    
    # Initialize components
    logger.info("Initializing components...")
    db = DatabaseManager(
        db_path=config.SQLITE_DB_PATH if config.DB_TYPE == 'sqlite' else None,
        db_type=config.DB_TYPE
    )
    faiss = FAISSManager()
    face_proc = FaceProcessor()
    scraper = WebScraper(headless=args.headless)
    
    logger.info("="*70)
    logger.info("BATCH PROCESSING STARTED")
    logger.info("="*70)
    
    # Process each website
    successful = 0
    failed = 0
    
    for i, url in enumerate(urls, 1):
        logger.info(f"\n[{i}/{len(urls)}] Processing: {url}")
        
        try:
            process_website(url, db, faiss, face_proc, scraper)
            successful += 1
            logger.info(f"✓ Successfully processed {url}")
            
        except Exception as e:
            failed += 1
            logger.error(f"✗ Failed to process {url}: {e}")
            
            if not args.skip_errors:
                logger.error("Stopping due to error (use --skip-errors to continue)")
                break
            else:
                logger.info("Continuing to next website...")
    
    # Save FAISS index
    logger.info("\nSaving FAISS index...")
    faiss.save_index()
    
    # Run clustering on all faces
    if successful > 0:
        logger.info("\nRunning auto-clustering on all faces...")
        try:
            num_clusters = auto_cluster(
                db, 
                threshold=config.FACE_MATCH_THRESHOLD,
                min_samples=config.MIN_CLUSTER_SIZE
            )
            logger.info(f"✓ Created {num_clusters} face clusters")
        except Exception as e:
            logger.error(f"Clustering failed: {e}", exc_info=True)
    
    # Summary
    logger.info("="*70)
    logger.info("BATCH PROCESSING COMPLETE")
    logger.info("="*70)
    logger.info(f"Total websites: {len(urls)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Success rate: {(successful/len(urls)*100):.1f}%")
    
    # Database statistics
    stats = db.get_statistics()
    logger.info("\nDatabase Statistics:")
    logger.info(f"  Total websites: {stats.get('active_websites', 0)}")
    logger.info(f"  Total images: {stats.get('active_images', 0)}")
    logger.info(f"  Total faces: {stats.get('active_faces', 0)}")
    logger.info(f"  Average confidence: {stats.get('avg_confidence', 0):.1%}")
    
    logger.info(f"\nFAISS index: {faiss.get_total_vectors()} embeddings")
    logger.info(f"Saved to: {faiss.index_path}")
    
    logger.info("\n✓ All done! Ready for searching.")
    logger.info(f"\nTry: python search_api.py --image test_photo.jpg")


if __name__ == '__main__':
    main()
