import psycopg2

DB_CONFIG = {
    'host': 'localhost',
    'port': 5434,
    'database': 'proposalagentchatdb',
    'user': 'postgres',
    'password': 'Deadpool@123'
}

def show_intent_table_schema():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # List all columns of the `intent` table
    cur.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'intent'
        ORDER BY ordinal_position;
    """)
    columns = cur.fetchall()

    print("Schema of table `intent`:")
    for name, dtype in columns:
        print(f" - {name}: {dtype}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    show_intent_table_schema()
