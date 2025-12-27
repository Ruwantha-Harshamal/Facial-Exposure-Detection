"""
main_pipeline.py

Main orchestration script for OSINT face recognition pipeline
RAM-only processing: scrape → detect → embed → save to DB + FAISS → auto-deduplicate
"""

import argparse
import logging
from urllib.parse import urlparse
from collections import defaultdict

from database_manager import DatabaseManager
from face_processor import FaceProcessor
from faiss_manager import FAISSManager
from scraper import WebScraper
from face_clustering import auto_cluster
import config

logger = logging.getLogger(__name__)


def extract_domain_name(url: str) -> str:
    """Extract clean domain name from URL"""
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path
    # Remove www. prefix
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain


def auto_deduplicate(db: DatabaseManager, db_path: str = 'face_recognition.db'):
    """
    Automatically remove duplicate images, keeping best versions
    Integrated deduplication - runs after each scrape
    """
    logger.info("\n" + "="*70)
    logger.info("AUTO-DEDUPLICATION")
    logger.info("="*70)
    
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all images with their IDs
    cursor.execute("""
        SELECT i.id, i.image_url, i.width, i.height, COUNT(f.id) as face_count
        FROM images i
        LEFT JOIN faces f ON i.id = f.image_id
        GROUP BY i.id
        ORDER BY i.image_url
    """)
    
    all_images = cursor.fetchall()
    
    # Group by base URL (without query parameters)
    base_url_groups = defaultdict(list)
    for img_id, url, width, height, face_count in all_images:
        base_url = url.split('?')[0]
        base_url_groups[base_url].append({
            'id': img_id,
            'url': url,
            'width': width,
            'height': height,
            'face_count': face_count
        })
    
    # Find duplicates to delete
    to_delete = []
    
    for base_url, variants in base_url_groups.items():
        if len(variants) == 1:
            continue
        
        # Multiple versions - choose the best one
        best = None
        
        # Check if it's a Gravatar avatar (prefer 144x144)
        if 'gravatar.com' in base_url or 's=' in variants[0]['url']:
            # Look for 144x144 version
            for variant in variants:
                if 's=144' in variant['url']:
                    best = variant
                    break
            
            # If no 144, take the largest
            if not best:
                best = max(variants, key=lambda x: x['width'] or 0)
        else:
            # For regular images, prefer:
            # 1. Images with faces
            # 2. Largest size
            variants_with_faces = [v for v in variants if v['face_count'] > 0]
            if variants_with_faces:
                best = max(variants_with_faces, key=lambda x: x['width'] or 0)
            else:
                best = max(variants, key=lambda x: x['width'] or 0)
        
        to_delete.extend([v for v in variants if v['id'] != best['id']])
    
    # Delete duplicates
    if to_delete:
        image_ids_to_delete = [img['id'] for img in to_delete]
        placeholders = ','.join(['?'] * len(image_ids_to_delete))
        
        cursor.execute(f"DELETE FROM images WHERE id IN ({placeholders})", image_ids_to_delete)
        conn.commit()
        
        logger.info(f"✓ Removed {len(image_ids_to_delete)} duplicate images")
    else:
        logger.info("✓ No duplicates found")
    
    conn.close()
    logger.info("="*70)


def process_website(
    website_url: str,
    db: DatabaseManager,
    faiss: FAISSManager,
    face_proc: FaceProcessor,
    scraper: WebScraper
):
    """
    Complete pipeline for single website
    
    1. Scrape image URLs
    2. Download images to RAM
    3. Detect faces + generate embeddings (RAM only)
    4. Save to database + FAISS
    5. Image destroyed (never touches disk!)
    """
    logger.info("="*70)
    logger.info(f"Processing website: {website_url}")
    logger.info("="*70)
    
    # Insert website record
    domain_name = extract_domain_name(website_url)
    website_id = db.add_website(website_url)
    
    # Scrape image URLs
    image_urls = scraper.scrape_image_urls(website_url)
    
    if not image_urls:
        logger.warning("No images found on website")
        db.update_website_status(website_id, 'completed', 0, 0)
        return
    
    logger.info(f"Processing {len(image_urls)} images...")
    
    total_faces = 0
    images_with_faces = 0
    
    # Process each image
    for i, image_url in enumerate(image_urls, 1):
        logger.info(f"\n[{i}/{len(image_urls)}] {image_url}")
        
        # Download image to RAM
        image_bytes, width, height = scraper.download_image(image_url, website_url)
        
        if not image_bytes:
            logger.debug("  Skipped (download failed)")
            continue
        
        # Insert image record
        image_id = db.insert_image(website_id, image_url, width, height)
        
        # Process faces (completely in RAM!)
        face_results = face_proc.process_image_bytes(image_bytes, image_url)
        
        # image_bytes is automatically garbage collected here - never saved to disk!
        
        if not face_results:
            continue
        
        images_with_faces += 1
        
        # Save each face to database + FAISS
        for bbox, confidence, thumbnail_bytes, embedding in face_results:
            # Save to database (atomic transaction)
            face_id = db.insert_face_complete(
                image_id=image_id,
                bbox=bbox,
                confidence=confidence,
                thumbnail_bytes=thumbnail_bytes,
                embedding=embedding
            )
            
            # Add to FAISS index
            faiss.add_embedding(face_id, embedding)
            
            total_faces += 1
    
    # Update website status
    db.update_website_status(website_id, 'completed', len(image_urls), total_faces)
    
    # Save FAISS index
    faiss.save_index()
    
    logger.info("\n" + "="*70)
    logger.info(f"✓ Website complete: {total_faces} faces from {images_with_faces} images")
    logger.info("="*70)
    
    # Auto-deduplicate (keep only unique images)
    auto_deduplicate(db, config.SQLITE_DB_PATH if config.DB_TYPE == 'sqlite' else 'face_recognition.db')
    
    # Auto-cluster faces (group similar faces)
    if total_faces > 0:
        logger.info("\nRunning auto-clustering...")
        try:
            num_clusters = auto_cluster(db, threshold=config.FACE_MATCH_THRESHOLD, min_samples=2)
            logger.info(f"✓ Created {num_clusters} face clusters")
        except Exception as e:
            logger.error(f"Clustering failed: {e}", exc_info=True)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="OSINT Face Recognition Pipeline - RAM-only processing"
    )
    parser.add_argument(
        '--url',
        required=True,
        help='Website URL to scrape'
    )
    parser.add_argument(
        '--db-type',
        choices=['sqlite', 'postgresql'],
        default=config.DB_TYPE,
        help='Database type (default: from config)'
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        default=config.HEADLESS_BROWSER,
        help='Run browser in headless mode'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default=config.LOG_LEVEL,
        help='Logging level'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format=config.LOG_FORMAT
    )
    
    logger.info("\n" + "="*70)
    logger.info("OSINT FACE RECOGNITION PIPELINE")
    logger.info("="*70)
    logger.info(f"Target URL: {args.url}")
    logger.info(f"Database: {args.db_type}")
    logger.info(f"Headless: {args.headless}")
    logger.info("="*70 + "\n")
    
    # Initialize components
    logger.info("Initializing components...")
    db = DatabaseManager(db_type=args.db_type)
    
    faiss_mgr = FAISSManager()
    face_processor = FaceProcessor()
    web_scraper = WebScraper(headless=args.headless)
    
    logger.info("✓ All components ready\n")
    
    try:
        # Process website
        process_website(
            args.url,
            db,
            faiss_mgr,
            face_processor,
            web_scraper
        )
        
        # Auto-deduplicate
        logger.info("\nRunning auto-deduplication...")
        auto_deduplicate(db)
        
        # Show statistics
        stats = db.get_statistics()
        logger.info("\n" + "="*70)
        logger.info("FINAL STATISTICS")
        logger.info("="*70)
        for key, value in stats.items():
            logger.info(f"{key}: {value}")
        logger.info("="*70)
        
    except KeyboardInterrupt:
        logger.warning("\n\nInterrupted by user")
    except Exception as e:
        logger.error(f"\n\nPipeline failed: {e}", exc_info=True)
    finally:
        db.close()
        logger.info("\n✓ Pipeline complete")


if __name__ == '__main__':
    main()
