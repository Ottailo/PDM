"""
Fix users table schema to allow NULL company_id.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db

def fix_user_schema():
    app = create_app()
    with app.app_context():
        # Check if users table exists
        inspector = db.inspect(db.engine)
        if 'users' not in inspector.get_table_names():
            print("Users table doesn't exist. Creating with correct schema...")
            db.create_all()
            return
        
        # Get current schema
        with db.engine.connect() as conn:
            # SQLite doesn't support ALTER COLUMN, so we need to recreate the table
            conn.execute(db.text("""
                CREATE TABLE IF NOT EXISTS users_new (
                    id INTEGER PRIMARY KEY,
                    username VARCHAR(64) NOT NULL UNIQUE,
                    email VARCHAR(120) NOT NULL UNIQUE,
                    password_hash VARCHAR(128),
                    role VARCHAR(20) DEFAULT 'viewer',
                    company_id INTEGER REFERENCES companies(id),
                    created_at DATETIME,
                    last_login DATETIME
                )
            """))
            
            # Copy existing data
            conn.execute(db.text("""
                INSERT INTO users_new (id, username, email, password_hash, role, company_id, created_at, last_login)
                SELECT id, username, email, password_hash, role, company_id, created_at, last_login
                FROM users
            """))
            
            # Drop old table and rename new one
            conn.execute(db.text("DROP TABLE users"))
            conn.execute(db.text("ALTER TABLE users_new RENAME TO users"))
            conn.commit()
            
        print("Users table schema fixed: company_id now allows NULL")

if __name__ == "__main__":
    fix_user_schema()

