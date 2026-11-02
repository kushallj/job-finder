#!/usr/bin/env python
"""
Migration script to add required indexes from Requirements 21.8-21.11.
This improves query performance for common database operations.
"""
import sqlite3
import os


def add_indexes():
    """Add required indexes to the database."""
    db_path = "job_automation.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        return False
    
    print("=" * 60)
    print("Migration: Add Required Indexes (Requirements 21.8-21.11)")
    print("=" * 60)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Requirement 21.8: Compound index on jobs(company, fetched_at)
        print("\n📝 Creating compound index on jobs(company, fetched_at)...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_jobs_company_fetched_at
            ON jobs(company, fetched_at)
        """)
        print("   ✅ idx_jobs_company_fetched_at created")
        
        # Requirement 21.9: Compound index on contacts(email, company)
        print("\n📝 Creating compound index on contacts(email, company)...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_contacts_email_company
            ON contacts(email, company)
        """)
        print("   ✅ idx_contacts_email_company created")
        
        # Requirement 21.10: Compound index on outreach_records(job_id, contact_id)
        print("\n📝 Creating compound index on outreach_records(job_id, contact_id)...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_outreach_job_contact
            ON outreach_records(job_id, contact_id)
        """)
        print("   ✅ idx_outreach_job_contact created")
        
        # Requirement 21.11: Index on applications(match_score)
        print("\n📝 Creating index on applications(match_score)...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_applications_match_score
            ON applications(match_score)
        """)
        print("   ✅ idx_applications_match_score created")
        
        conn.commit()
        
        # Verify indexes were created
        print("\n🔍 Verifying indexes...")
        cursor.execute("""
            SELECT name, tbl_name, sql
            FROM sqlite_master
            WHERE type='index'
            AND name LIKE 'idx_%'
        """)
        indexes = cursor.fetchall()
        
        for idx_name, table_name, sql in indexes:
            print(f"   ✅ {idx_name} on {table_name}")
        
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ All required indexes created successfully!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False


if __name__ == "__main__":
    success = add_indexes()
    exit(0 if success else 1)
