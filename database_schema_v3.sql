-- ═══════════════════════════════════════════════════════════
-- database_schema_v3.sql - IMPROVED VERSION
-- 
-- FIXES:
-- ✓ UNIQUE constraint on image_url (prevent duplicates at DB level)
-- ✓ Better embedding storage (separate vector table for scalability)
-- ✓ Partitioning-ready structure
-- ✓ Archival support (soft delete)
-- ✓ Better indexes for production scale
-- ═══════════════════════════════════════════════════════════

-- ═══════════════════════════════════════════════════════════
-- TABLE 1: websites
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS websites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL UNIQUE,
    name TEXT,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_images INTEGER DEFAULT 0,
    total_faces INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Soft delete support
    deleted_at TIMESTAMP DEFAULT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_websites_url ON websites(url);
CREATE INDEX IF NOT EXISTS idx_websites_status ON websites(status);
CREATE INDEX IF NOT EXISTS idx_websites_created_at ON websites(created_at);
CREATE INDEX IF NOT EXISTS idx_websites_active ON websites(is_active, deleted_at);

-- ═══════════════════════════════════════════════════════════
-- TABLE 2: images - WITH UNIQUE CONSTRAINT
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    website_id INTEGER NOT NULL REFERENCES websites(id) ON DELETE CASCADE,
    -- ✓ FIX: UNIQUE constraint prevents duplicates at DB level
    image_url TEXT NOT NULL UNIQUE,
    -- Normalized URL (for deduplication - without query params)
    normalized_url TEXT,
    width INTEGER,
    height INTEGER,
    file_size INTEGER,
    mime_type TEXT,
    has_faces BOOLEAN DEFAULT FALSE,
    face_count INTEGER DEFAULT 0,
    -- Quality metrics
    is_blurry BOOLEAN DEFAULT FALSE,
    quality_score REAL DEFAULT NULL,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Soft delete
    deleted_at TIMESTAMP DEFAULT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_images_website ON images(website_id);
CREATE INDEX IF NOT EXISTS idx_images_url ON images(image_url);
CREATE INDEX IF NOT EXISTS idx_images_normalized ON images(normalized_url);
CREATE INDEX IF NOT EXISTS idx_images_has_faces ON images(has_faces);
CREATE INDEX IF NOT EXISTS idx_images_created_at ON images(created_at);
CREATE INDEX IF NOT EXISTS idx_images_active ON images(is_active, deleted_at);
CREATE INDEX IF NOT EXISTS idx_images_website_faces ON images(website_id, has_faces);

-- ═══════════════════════════════════════════════════════════
-- TABLE 3: faces - Optimized structure
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS faces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_id INTEGER NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    -- Bounding box
    bbox_x INTEGER NOT NULL,
    bbox_y INTEGER NOT NULL,
    bbox_width INTEGER NOT NULL,
    bbox_height INTEGER NOT NULL,
    -- Detection metadata
    confidence REAL NOT NULL,
    detector TEXT DEFAULT 'MTCNN',
    detector_version TEXT DEFAULT '0.1.1',
    -- Face quality
    is_blurry BOOLEAN DEFAULT FALSE,
    quality_score REAL DEFAULT NULL,
    -- Face attributes (for future enhancement)
    landmarks_data BLOB DEFAULT NULL,
    -- ✓ FIX: Embedding moved to separate table for better performance
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Soft delete
    deleted_at TIMESTAMP DEFAULT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_faces_image ON faces(image_id);
CREATE INDEX IF NOT EXISTS idx_faces_confidence ON faces(confidence);
CREATE INDEX IF NOT EXISTS idx_faces_detected_at ON faces(detected_at);
CREATE INDEX IF NOT EXISTS idx_faces_created_at ON faces(created_at);
CREATE INDEX IF NOT EXISTS idx_faces_confidence_created ON faces(confidence DESC, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_faces_active ON faces(is_active, deleted_at);

-- ═══════════════════════════════════════════════════════════
-- TABLE 4: embeddings - SEPARATE for better scalability
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS embeddings (
    face_id INTEGER PRIMARY KEY REFERENCES faces(id) ON DELETE CASCADE,
    -- ✓ FIX: Separate table allows for easier archival/partitioning
    embedding_vector BLOB NOT NULL,
    embedding_model TEXT DEFAULT 'FaceNet',
    model_version TEXT DEFAULT '20180402-114759',
    embedding_dimensions INTEGER DEFAULT 512,
    -- Hash for quick duplicate detection
    embedding_hash TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Soft delete
    deleted_at TIMESTAMP DEFAULT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_embeddings_hash ON embeddings(embedding_hash);
CREATE INDEX IF NOT EXISTS idx_embeddings_active ON embeddings(is_active, deleted_at);

-- ═══════════════════════════════════════════════════════════
-- TABLE 5: face_thumbnails
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS face_thumbnails (
    face_id INTEGER PRIMARY KEY REFERENCES faces(id) ON DELETE CASCADE,
    thumbnail_blob BLOB NOT NULL,
    format TEXT DEFAULT 'JPEG',
    width INTEGER DEFAULT 144,
    height INTEGER DEFAULT 144,
    file_size INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ═══════════════════════════════════════════════════════════
-- TABLE 6: face_clusters (for grouping same person)
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS face_clusters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_name TEXT,
    centroid_embedding BLOB,
    face_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS face_cluster_members (
    cluster_id INTEGER REFERENCES face_clusters(id) ON DELETE CASCADE,
    face_id INTEGER REFERENCES faces(id) ON DELETE CASCADE,
    similarity_score REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (cluster_id, face_id)
);

CREATE INDEX IF NOT EXISTS idx_cluster_members_face ON face_cluster_members(face_id);

-- ═══════════════════════════════════════════════════════════
-- TABLE 7: search_logs (audit trail)
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS search_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    search_type TEXT,  -- 'face_search', 'url_search', etc.
    query_data BLOB,
    results_count INTEGER,
    execution_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_search_logs_type ON search_logs(search_type);
CREATE INDEX IF NOT EXISTS idx_search_logs_created ON search_logs(created_at);

-- ═══════════════════════════════════════════════════════════
-- VIEWS - Updated for v3
-- ═══════════════════════════════════════════════════════════

DROP VIEW IF EXISTS v_faces_complete;
CREATE VIEW v_faces_complete AS
SELECT 
    f.id as face_id,
    f.bbox_x, f.bbox_y, f.bbox_width, f.bbox_height,
    f.confidence,
    f.quality_score as face_quality,
    f.detector,
    f.detected_at,
    f.created_at as face_created_at,
    i.id as image_id,
    i.image_url,
    i.normalized_url,
    i.width as image_width,
    i.height as image_height,
    i.quality_score as image_quality,
    i.created_at as image_created_at,
    w.id as website_id,
    w.url as website_url,
    w.name as website_name,
    e.embedding_model,
    e.embedding_dimensions,
    e.model_version
FROM faces f
JOIN images i ON f.image_id = i.id
JOIN websites w ON i.website_id = w.id
LEFT JOIN embeddings e ON f.id = e.face_id
WHERE f.is_active = TRUE 
  AND i.is_active = TRUE 
  AND w.is_active = TRUE;

-- Statistics view
DROP VIEW IF EXISTS v_statistics;
CREATE VIEW v_statistics AS
SELECT 
    (SELECT COUNT(*) FROM websites WHERE is_active = TRUE) as active_websites,
    (SELECT COUNT(*) FROM images WHERE is_active = TRUE) as active_images,
    (SELECT COUNT(*) FROM faces WHERE is_active = TRUE) as active_faces,
    (SELECT COUNT(*) FROM embeddings WHERE is_active = TRUE) as active_embeddings,
    (SELECT AVG(confidence) FROM faces WHERE is_active = TRUE) as avg_confidence,
    (SELECT COUNT(*) FROM faces WHERE confidence >= 0.95 AND is_active = TRUE) as high_confidence_faces,
    (SELECT SUM(file_size) FROM face_thumbnails) as total_thumbnail_size_bytes,
    (SELECT MAX(created_at) FROM faces WHERE is_active = TRUE) as last_face_detected,
    (SELECT COUNT(*) FROM images WHERE deleted_at IS NOT NULL) as archived_images,
    (SELECT COUNT(*) FROM faces WHERE deleted_at IS NOT NULL) as archived_faces;

-- ═══════════════════════════════════════════════════════════
-- TRIGGERS - Auto-update timestamps and counts
-- ═══════════════════════════════════════════════════════════

-- Update website.updated_at on any change
CREATE TRIGGER IF NOT EXISTS trigger_websites_updated_at
AFTER UPDATE ON websites
FOR EACH ROW
BEGIN
    UPDATE websites SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Update face_count in images when face is added
CREATE TRIGGER IF NOT EXISTS trigger_images_face_count_insert
AFTER INSERT ON faces
FOR EACH ROW
BEGIN
    UPDATE images SET face_count = face_count + 1, has_faces = TRUE WHERE id = NEW.image_id;
END;

-- Update face_count in images when face is deleted
CREATE TRIGGER IF NOT EXISTS trigger_images_face_count_delete
AFTER UPDATE OF deleted_at ON faces
FOR EACH ROW
WHEN NEW.deleted_at IS NOT NULL AND OLD.deleted_at IS NULL
BEGIN
    UPDATE images SET face_count = face_count - 1 WHERE id = NEW.image_id;
END;

-- ═══════════════════════════════════════════════════════════
-- PERFORMANCE NOTES
-- ═══════════════════════════════════════════════════════════

-- For production scale (100k+ faces):
-- 1. Use PostgreSQL instead of SQLite
-- 2. Partition embeddings table by created_at (monthly)
-- 3. Use pgvector extension for embedding search
-- 4. Archive old data to separate tables
-- 5. Use connection pooling (pgbouncer)
-- 6. Consider TimescaleDB for time-series queries

-- For SQLite optimization:
-- PRAGMA journal_mode = WAL;
-- PRAGMA synchronous = NORMAL;
-- PRAGMA cache_size = -64000;  -- 64MB cache
-- PRAGMA temp_store = MEMORY;
-- PRAGMA mmap_size = 30000000000;  -- 30GB memory map
