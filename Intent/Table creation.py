import psycopg2

DB_CONFIG = {
    'host': 'localhost',
    'port': 5434,
    'database': 'proposalagentchatdb',
    'user': 'postgres',
    'password': 'Deadpool@123'
}

def create_intent_table():
    # 1. Connect
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    cur = conn.cursor()

    # 2. Create table if it doesn't exist
    cur.execute("""
        CREATE TABLE IF NOT EXISTS intent (
            user_id UUID      NOT NULL,
            message TEXT      NOT NULL,
            intents TEXT[]    NOT NULL
        );
    """)

    # 3. Clean up
    cur.close()
    conn.close()
    print("✅ Table `intent` is ready.")

if __name__ == "__main__":
    create_intent_table()
