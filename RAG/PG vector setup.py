

import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


os.environ["PG_CONFIG"] = r"D:\UMASS\CPT\proposalagent\pgvector\vector.control"


def connect_db():

    return psycopg2.connect(
        host='localhost',
        port='5434',
        database='proposalagentchatdb',
        user='postgres',
        password='Deadpool@123'
    )

def setup_pgvector():

    conn = None
    cur = None

    try:
        # Connect to database
        conn = connect_db()
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        print("Connected to PostgreSQL database")

        # Create pgvector extension
        print("Creating pgvector extension...")
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        print("✓ pgvector extension created successfully")

        # Create pgvectorscale extension (optional)
        try:
            print("Creating pgvectorscale extension...")
            cur.execute("CREATE EXTENSION IF NOT EXISTS vectorscale CASCADE;")
            print("✓ pgvectorscale extension created successfully")
        except psycopg2.Error as e:
            print(f"⚠ pgvectorscale not available: {e}")
            print("  Continuing with pgvector only...")

        # Verify installation
        cur.execute("""
            SELECT extname, extversion
              FROM pg_extension
             WHERE extname IN ('vector', 'vectorscale');
        """)
        print("\nInstalled extensions:")
        for ext_name, ext_version in cur.fetchall():
            print(f"  - {ext_name} v{ext_version}")

        print("\n✅ pgvector setup completed successfully!")

    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        raise
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    setup_pgvector()
