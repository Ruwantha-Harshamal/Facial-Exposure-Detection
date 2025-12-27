"""
face_clustering.py

Automatic face clustering module for grouping similar faces.
Uses DBSCAN to identify faces belonging to the same person.
"""

import logging
import numpy as np
from sklearn.cluster import DBSCAN
from typing import Dict, List, Tuple
import pickle

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
    logger.info(f"Starting face clustering with threshold={threshold}, min_samples={min_samples}")
    
    # Get all embeddings from database
    embeddings_data = db.get_all_embeddings()
    
    if not embeddings_data:
        logger.warning("No embeddings found in database. Skipping clustering.")
        return {}
    
    logger.info(f"Retrieved {len(embeddings_data)} embeddings from database")
    
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
    
    logger.info(f"Clustering complete: {n_clusters} clusters, {n_noise} noise points")
    
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
    logger.info(f"Saving {len(clusters)} clusters to database...")
    
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
        
        logger.info(f"Created cluster {cluster_id} with {len(face_ids)} faces")
    
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
    logger.info(f"Total clusters created: {len(clusters)}")
    for cluster_label, face_ids in clusters.items():
        logger.info(f"  Cluster {cluster_label}: {len(face_ids)} faces")
    logger.info("=" * 70)
    
    return len(clusters)


def get_cluster_info(db, cluster_id: int) -> Dict:
    """
    Get detailed information about a cluster.
    
    Args:
        db: DatabaseManager instance
        cluster_id: ID of the cluster
        
    Returns:
        Dictionary with cluster information
    """
    cursor = db.conn.cursor()
    
    # Get cluster details
    cursor.execute(
        """SELECT id, cluster_name, face_count, created_at, updated_at
           FROM face_clusters
           WHERE id = ?""",
        (cluster_id,)
    )
    cluster_row = cursor.fetchone()
    
    if not cluster_row:
        return None
    
    # Get member faces
    cursor.execute(
        """SELECT face_id, similarity_score
           FROM face_cluster_members
           WHERE cluster_id = ?
           ORDER BY similarity_score DESC""",
        (cluster_id,)
    )
    members = cursor.fetchall()
    
    return {
        'cluster_id': cluster_row[0],
        'cluster_name': cluster_row[1],
        'face_count': cluster_row[2],
        'created_at': cluster_row[3],
        'updated_at': cluster_row[4],
        'members': [{'face_id': m[0], 'similarity': m[1]} for m in members]
    }


def get_all_clusters(db) -> List[Dict]:
    """
    Get all clusters from the database.
    
    Args:
        db: DatabaseManager instance
        
    Returns:
        List of cluster dictionaries
    """
    cursor = db.conn.cursor()
    cursor.execute(
        """SELECT id, cluster_name, face_count, created_at
           FROM face_clusters
           ORDER BY face_count DESC"""
    )
    
    clusters = []
    for row in cursor.fetchall():
        clusters.append({
            'cluster_id': row[0],
            'cluster_name': row[1],
            'face_count': row[2],
            'created_at': row[3]
        })
    
    return clusters


if __name__ == '__main__':
    """
    Run clustering as standalone script
    Usage: python face_clustering.py
    """
    from database_manager import DatabaseManager
    
    # Initialize database
    db = DatabaseManager(db_path=config.SQLITE_DB_PATH, db_type=config.DB_TYPE)
    
    # Run auto clustering
    threshold = 0.6  # Adjust based on your needs (lower = stricter)
    min_samples = 2  # Minimum 2 faces to form a cluster
    
    n_clusters = auto_cluster(db, threshold=threshold, min_samples=min_samples)
    
    print(f"\n✓ Clustering complete! Created {n_clusters} clusters.")
    print(f"\nTo view clusters, check the database or use view_database.py")
    
    db.close()
