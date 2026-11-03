"""
Database migration script to enforce tenant isolation (P0-3).
Adds user_id foreign keys and indices to contacts, outreach_records, and candidate_profiles in jobs.db,
and backfills unassigned legacy applications, contacts, and outreach records to user_id = 1 (admin).
"""
import sqlite3
import os
import sys

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "jobs.db")

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        sys.exit(1)

    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Migrate contacts
    contact_cols = [c[1] for c in cursor.execute("PRAGMA table_info(contacts)").fetchall()]
    if "user_id" not in contact_cols:
        print("Adding user_id column to contacts...")
        cursor.execute("ALTER TABLE contacts ADD COLUMN user_id INTEGER REFERENCES users(id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_contacts_user_id ON contacts (user_id)")
    
    cursor.execute("UPDATE contacts SET user_id = 1 WHERE user_id IS NULL")
    updated_contacts = cursor.rowcount
    print(f"Backfilled {updated_contacts} contacts to user_id = 1")

    # 2. Migrate outreach_records
    outreach_cols = [c[1] for c in cursor.execute("PRAGMA table_info(outreach_records)").fetchall()]
    if "user_id" not in outreach_cols:
        print("Adding user_id column to outreach_records...")
        cursor.execute("ALTER TABLE outreach_records ADD COLUMN user_id INTEGER REFERENCES users(id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_outreach_records_user_id ON outreach_records (user_id)")

    cursor.execute("UPDATE outreach_records SET user_id = 1 WHERE user_id IS NULL")
    updated_outreach = cursor.rowcount
    print(f"Backfilled {updated_outreach} outreach records to user_id = 1")

    # 3. Backfill applications
    cursor.execute("UPDATE applications SET user_id = 1 WHERE user_id IS NULL")
    updated_apps = cursor.rowcount
    print(f"Backfilled {updated_apps} applications to user_id = 1")

    # 4. Migrate candidate_profiles if needed
    profile_cols = [c[1] for c in cursor.execute("PRAGMA table_info(candidate_profiles)").fetchall()]
    if "user_id" not in profile_cols:
        print("Adding user_id column to candidate_profiles...")
        cursor.execute("ALTER TABLE candidate_profiles ADD COLUMN user_id INTEGER REFERENCES users(id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_candidate_profiles_user_id ON candidate_profiles (user_id)")
    cursor.execute("UPDATE candidate_profiles SET user_id = 1 WHERE user_id IS NULL")

    conn.commit()
    conn.close()
    print("Tenant isolation migration completed successfully.")

if __name__ == "__main__":
    migrate()
