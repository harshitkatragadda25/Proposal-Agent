

import psycopg2
from psycopg2.extras import RealDictCursor
import json


def connect_db():

    return psycopg2.connect(
        host='localhost',
        port='5434',
        database='proposalagentchatdb',
        user='postgres',
        password='Deadpool@123'
    )


def check_database_content():

    conn = None
    cur = None

    try:
        conn = connect_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        print("🔍 CHECKING DATABASE CONTENT")
        print("=" * 50)

        # Get total count
        cur.execute("SELECT COUNT(*) as total FROM embeddings")
        total = cur.fetchone()['total']
        print(f"Total rows: {total}")

        if total == 0:
            print("❌ No data in database!")
            return

        # Get all data to see what's there
        cur.execute("""
            SELECT 
                id,
                metadata,
                contents,
                LENGTH(contents) as content_length
            FROM embeddings 
            ORDER BY id
        """)

        rows = cur.fetchall()

        print(f"\n📄 ALL ROWS IN DATABASE:")
        print("-" * 80)

        for row in rows:
            print(f"\nID: {row['id']}")
            print(f"Content Length: {row['content_length']}")
            print(f"Metadata: {row['metadata']}")
            print(f"Content: '{row['contents']}'")
            print("-" * 40)

        # Check embedding dimensions
        try:
            cur.execute("SELECT vector_dims(embedding) as dim FROM embeddings LIMIT 1")
            result = cur.fetchone()
            if result:
                print(f"\nEmbedding Dimension: {result['dim']}")
        except Exception as e:
            print(f"\nCould not get embedding dimension: {e}")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    check_database_content()