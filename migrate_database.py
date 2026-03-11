#!/usr/bin/env python3
"""
Database Migration Script
Adds missing columns to existing database
"""

import sqlite3
import os

def migrate_database():
    """Add missing columns to database"""
    
    db_path = "job_automation.db"
    
    if not os.path.exists(db_path):
        print("❌ Database not found. Run: python outreach_cli.py setup")
        return False
    
    print("🔄 Migrating database...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if outreach_records table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='outreach_records'")
        if not cursor.fetchone():
            print("⚠️  outreach_records table doesn't exist. Creating fresh database...")
            conn.close()
            
            # Backup old database
            if os.path.exists(db_path):
                backup_path = f"{db_path}.backup"
                os.rename(db_path, backup_path)
                print(f"   Old database backed up to: {backup_path}")
            
            # Reinitialize database
            from src.database import init_db
            init_db()
            print("✅ Fresh database created")
            return True
        
        # Get existing columns
        cursor.execute("PRAGMA table_info(outreach_records)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        
        # Define required columns with their SQL types
        required_columns = {
            'email_sent': 'BOOLEAN DEFAULT 0',
            'contact_email': 'VARCHAR(255)',
            'contact_name': 'VARCHAR(255)',
            'follow_up_count': 'INTEGER DEFAULT 0',
            'last_follow_up_at': 'DATETIME',
        }
        
        # Add missing columns
        added = []
        for column, sql_type in required_columns.items():
            if column not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE outreach_records ADD COLUMN {column} {sql_type}")
                    added.append(column)
                    print(f"   ✅ Added column: {column}")
                except sqlite3.OperationalError as e:
                    if "duplicate column" not in str(e).lower():
                        print(f"   ⚠️  Could not add {column}: {e}")
        
        conn.commit()
        
        if added:
            print(f"\n✅ Migration complete! Added {len(added)} columns")
        else:
            print("\n✅ Database is up to date")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("🔧 Database Migration Tool")
    print("=" * 40)
    
    success = migrate_database()
    
    if success:
        print("\n🎉 Database ready!")
        print("\nYou can now run:")
        print("   python comprehensive_job_search.py")
    else:
        print("\n❌ Migration failed")
        print("\nTry:")
        print("   1. Backup your database: cp job_automation.db job_automation.db.backup")
        print("   2. Delete database: rm job_automation.db")
        print("   3. Recreate: python outreach_cli.py setup")
