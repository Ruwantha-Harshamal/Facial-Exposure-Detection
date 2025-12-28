"""
face_clustering.py

Automatic face clustering module for grouping similar faces.
Uses DBSCAN to identify faces belonging to the same person.
"""

import logging
import numpy as np
from typing import Dict, List
import pickle

try:
    from sklearn.cluster import DBSCAN  # type: ignore
except ImportError:
    DBSCAN = None

import config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def cluster_faces(db, threshold: float = 0.6, min_samples: int = 2) -> Dict[int, List[int]]:
    """
    Cluster all faces in the database using DBSCAN.
    
    Args:
        db: DatabaseManager instance
        threshold: Distance threshold for clustering (0-1). Lower = stricter.
        min_samples: Minimum faces to form a cluster
        
    Returns:
        Dictionary mapping cluster_id -> list of face_ids
    """
    if DBSCAN is None:
        logger.error("scikit-learn not installed. Install with: pip install scikit-learn")
        return {}
    
    logger.info("Starting face clustering with threshold=%.2f, min_samples=%d", threshold, min_samples)
    
    # Get all embeddings from database
    embeddings_data = db.get_all_embeddings()
    
    if not embeddings_data:
        logger.warning("No embeddings found in database. Skipping clustering.")
        return {}
    
    logger.info("Retrieved %d embeddings from database", len(embeddings_data))
    
    # Separate face_ids and embeddings
    face_ids = [face_id for face_id, _ in embeddings_data]
    embeddings = np.array([emb for _, emb in embeddings_data])
    
    # Normalize embeddings for cosine distance
    embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
    
    # Run DBSCAN clustering
    logger.info("Running DBSCAN clustering...")
    clustering = DBSCAN(
        eps=threshold,
        min_samples=min_samples,
        metric='cosine'
    )
    labels = clustering.fit_predict(embeddings)
    
    # Count clusters (excluding noise points labeled as -1)
    unique_labels = set(labels)
    n_clusters = len(unique_labels) - (1 if -1 in unique_labels else 0)
    n_noise = list(labels).count(-1)
    
    logger.info("Clustering complete: %d clusters, %d noise points", n_clusters, n_noise)
    
    # Group faces by cluster
    clusters = {}
    for face_id, cluster_label in zip(face_ids, labels):
        if cluster_label == -1:
            # Noise point - skip or create singleton cluster
            continue
        
        if cluster_label not in clusters:
            clusters[cluster_label] = []
        clusters[cluster_label].append(face_id)
    
    return clusters


def save_clusters_to_database(db, clusters: Dict[int, List[int]]):
    """
    Save clustering results to the database.
    
    Args:
        db: DatabaseManager instance
        clusters: Dictionary mapping cluster_label -> list of face_ids
    """
    logger.info("Saving %d clusters to database...", len(clusters))
    
    cursor = db.conn.cursor()
    
    for cluster_label, face_ids in clusters.items():
        if len(face_ids) < 2:
            # Skip singleton clusters
            continue
        
        # Calculate centroid embedding (average of all faces in cluster)
        embeddings = []
        for face_id in face_ids:
            emb = db.get_embedding(face_id)
            if emb is not None:
                embeddings.append(emb)
        
        if not embeddings:
            continue
        
        centroid = np.mean(embeddings, axis=0)
        centroid_bytes = pickle.dumps(centroid)
        
        # Create cluster in database
        cursor.execute(
            """INSERT INTO face_clusters 
               (cluster_name, centroid_embedding, face_count, created_at)
               VALUES (?, ?, ?, datetime('now'))""",
            (f"Cluster_{cluster_label}", centroid_bytes, len(face_ids))
        )
        cluster_id = cursor.lastrowid
        
        # Add cluster members
        for face_id in face_ids:
            # Calculate similarity score to centroid
            emb = db.get_embedding(face_id)
            if emb is not None:
                similarity = float(np.dot(emb, centroid) / (np.linalg.norm(emb) * np.linalg.norm(centroid)))
                
                cursor.execute(
                    """INSERT INTO face_cluster_members 
                       (cluster_id, face_id, similarity_score, created_at)
                       VALUES (?, ?, ?, datetime('now'))""",
                    (cluster_id, face_id, similarity)
                )
        
        logger.info("Created cluster %d with %d faces", cluster_id, len(face_ids))
    
    db.conn.commit()
    logger.info("All clusters saved to database")


def clear_existing_clusters(db):
    """
    Clear all existing clusters from the database.
    
    Args:
        db: DatabaseManager instance
    """
    cursor = db.conn.cursor()
    cursor.execute("DELETE FROM face_cluster_members")
    cursor.execute("DELETE FROM face_clusters")
    db.conn.commit()
    logger.info("Cleared existing clusters from database")


def auto_cluster(db, threshold: float = 0.6, min_samples: int = 2, clear_existing: bool = True):
    """
    Automatically cluster all faces in the database.
    
    Args:
        db: DatabaseManager instance
        threshold: Distance threshold for clustering (0-1)
        min_samples: Minimum faces to form a cluster
        clear_existing: Whether to clear existing clusters first
        
    Returns:
        Number of clusters created
    """
    logger.info("=" * 70)
    logger.info("AUTO FACE CLUSTERING")
    logger.info("=" * 70)
    
    # Clear existing clusters if requested
    if clear_existing:
        clear_existing_clusters(db)
    
    # Run clustering
    clusters = cluster_faces(db, threshold=threshold, min_samples=min_samples)
    
    if not clusters:
        logger.info("No clusters found")
        return 0
    
    # Save to database
    save_clusters_to_database(db, clusters)
    
    # Print summary
    logger.info("=" * 70)
    logger.info("CLUSTERING SUMMARY")
    logger.info("=" * 70)
    logger.info("Total clusters created: %d", len(clusters))
    for cluster_label, face_ids in clusters.items():
        logger.info("  Cluster %d: %d faces", cluster_label, len(face_ids))
    logger.info("=" * 70)
    
    return len(clusters)


def main():
    """Main function for running clustering as standalone script."""
    from database_manager import DatabaseManager
    
    # Initialize database
    database = DatabaseManager(db_path=config.SQLITE_DB_PATH, db_type=config.DB_TYPE)
    
    # Run auto clustering
    cluster_threshold = 0.6  # Adjust based on your needs (lower = stricter)
    cluster_min_samples = 2  # Minimum 2 faces to form a cluster
    
    num_clusters = auto_cluster(database, threshold=cluster_threshold, min_samples=cluster_min_samples)
    
    print(f"\n✓ Clustering complete! Created {num_clusters} clusters.")
    print("\nTo view clusters, check the database or use view_database.py")
    
    database.close()


if __name__ == '__main__':
    main()
