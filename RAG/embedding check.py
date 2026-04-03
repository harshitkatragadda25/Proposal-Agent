import psycopg2
from tabulate import tabulate

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5434,
    'database': 'proposalagentchatdb',
    'user': 'postgres',
    'password': 'Deadpool@123'
}

def check_embeddings_table():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # Query to select all data from embeddings table
        cur.execute("SELECT * FROM embeddings;")
        rows = cur.fetchall()

        # Fetch column names for headers
        colnames = [desc[0] for desc in cur.description]

        if rows:
            print(tabulate(rows, headers=colnames, tablefmt="grid"))
        else:
            print("No data found in embeddings table.")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    check_embeddings_table()
