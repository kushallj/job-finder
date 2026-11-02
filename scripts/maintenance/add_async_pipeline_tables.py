#!/usr/bin/env python
"""
Migration script to add processing_results and pipeline_metrics tables.
This implements Requirements 21.6 and 21.7 from system-architecture spec.
"""
import sqlite3
import os
from datetime import datetime


def add_tables():
    """Add processing_results and pipeline_metrics tables to existing database."""
    db_path = "job_automation.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        return False
    
    print("=" * 60)
    print("Migration: Add processing_results and pipeline_metrics tables")
    print("=" * 60)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        print(f"\n📋 Existing tables: {', '.join(sorted(existing_tables))}")
        
        # Add processing_results table (Requirement 21.6)
        if "processing_results" not in existing_tables:
            print("\n📝 Creating processing_results table...")
            cursor.execute("""
                CREATE TABLE processing_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    processing_time_ms REAL,
                    attempt_count INTEGER DEFAULT 1,
                    skills_extracted TEXT,
                    match_result TEXT,
                    error_message TEXT,
                    worker_id VARCHAR(100),
                    correlation_id VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (job_id) REFERENCES jobs(id)
                )
            """)
            print("   ✅ processing_results table created")
        else:
            print("\n✓ processing_results table already exists")
        
        # Add pipeline_metrics table (Requirement 21.7)
        if "pipeline_metrics" not in existing_tables:
            print("\n📝 Creating pipeline_metrics table...")
            cursor.execute("""
                CREATE TABLE pipeline_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_type VARCHAR(100) NOT NULL,
                    metric_name VARCHAR(100) NOT NULL,
                    value REAL NOT NULL,
                    unit VARCHAR(50),
                    worker_id VARCHAR(100),
                    pipeline_run_id VARCHAR(100),
                    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("   ✅ pipeline_metrics table created")
        else:
            print("\n✓ pipeline_metrics table already exists")
        
        conn.commit()
        
        # Verify tables were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        final_tables = [row[0] for row in cursor.fetchall()]
        print(f"\n📋 Final tables: {', '.join(sorted(final_tables))}")
        
        # Verify structure
        print("\n🔍 Verifying table structures...")
        
        cursor.execute("PRAGMA table_info(processing_results)")
        pr_columns = [row[1] for row in cursor.fetchall()]
        print(f"   processing_results columns: {', '.join(pr_columns)}")
        
        cursor.execute("PRAGMA table_info(pipeline_metrics)")
        pm_columns = [row[1] for row in cursor.fetchall()]
        print(f"   pipeline_metrics columns: {', '.join(pm_columns)}")
        
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ Migration completed successfully!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False


if __name__ == "__main__":
    success = add_tables()
    exit(0 if success else 1)
