"""
Database Maintenance & Retention Service.
Keeps time-series sensor data bounded to prevent SQLite bloat.
"""
import os
import sqlite3
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def get_db_path(app=None):
    if app:
        uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if uri.startswith('sqlite:///'):
            path = uri.replace('sqlite:///', '')
            if not os.path.isabs(path):
                path = os.path.join(app.instance_path, path)
            return path
    # Default fallback
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    return os.path.join(base_dir, 'instance', 'maintenance.db')

def fast_prune_and_vacuum(keep_recent_count=150000, db_path=None):
    """
    Fast retention cleanup: keeps the most recent N records and vacuums.
    Uses SQLite shadow-table swap for instantaneous execution on multi-million row tables.
    """
    db_file = db_path or get_db_path()
    if not os.path.exists(db_file):
        logger.warning(f"Database file not found: {db_file}")
        return False, "Database file not found"

    logger.info(f"Starting database retention cleanup on {db_file} (keeping latest {keep_recent_count} records)...")
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT max(id), count(*) FROM sensor_data")
        row = cursor.fetchone()
        max_id = row[0] or 0
        total_count = row[1] or 0
        
        logger.info(f"Current sensor_data count: {total_count}, max_id: {max_id}")
        
        if total_count <= keep_recent_count:
            logger.info("Table row count is within retention threshold. No pruning needed.")
            conn.close()
            return True, f"Already within bounds ({total_count} records)"
            
        cutoff_id = max_id - keep_recent_count
        
        # Fast SQLite table swap
        cursor.execute("PRAGMA foreign_keys = OFF")
        cursor.execute("BEGIN TRANSACTION")
        
        cursor.execute("CREATE TABLE sensor_data_keep AS SELECT * FROM sensor_data WHERE id >= ?", (cutoff_id,))
        cursor.execute("DROP TABLE sensor_data")
        cursor.execute("ALTER TABLE sensor_data_keep RENAME TO sensor_data")
        
        # Recreate required indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_sensor_data_timestamp ON sensor_data (timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_sensor_data_sensor_id ON sensor_data (sensor_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sensor_timestamp ON sensor_data (sensor_id, timestamp)")
        
        cursor.execute("COMMIT")
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Get count after swap
        cursor.execute("SELECT count(*) FROM sensor_data")
        new_count = cursor.fetchone()[0]
        conn.close()
        
        # Run VACUUM outside transaction to reclaim disk space
        logger.info("Executing VACUUM to reclaim disk space...")
        vacuum_conn = sqlite3.connect(db_file)
        vacuum_conn.execute("VACUUM")
        vacuum_conn.close()
        
        final_size_mb = os.path.getsize(db_file) / (1024 * 1024)
        msg = f"Pruned {total_count - new_count} records. New count: {new_count}. Database size: {final_size_mb:.2f} MB"
        logger.info(msg)
        return True, msg
        
    except Exception as e:
        logger.error(f"Error during fast prune: {e}", exc_info=True)
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return False, str(e)

def prune_older_than(hours=48, app=None):
    """Periodic rolling window maintenance: deletes sensor records older than N hours."""
    from app import db
    from app.models.sensor_data import SensorData
    try:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        deleted = SensorData.query.filter(SensorData.timestamp < cutoff).delete(synchronize_session=False)
        db.session.commit()
        if deleted > 0:
            logger.info(f"Pruned {deleted} sensor readings older than {hours} hours.")
        return deleted
    except Exception as e:
        logger.error(f"Error pruning old sensor readings: {e}")
        db.session.rollback()
        return 0
