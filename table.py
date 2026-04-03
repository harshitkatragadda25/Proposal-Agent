import psycopg2

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'arkachatbot',
    'user': 'postgres',
    'password': 'arkachatbot'
}

def create_tables():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # SQL to create tables and indexes
        sql_statements = """
        CREATE TABLE IF NOT EXISTS chat_history (
            id SERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            message TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('user', 'bot')),
            timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            node TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_chat_history_user_id ON chat_history(user_id);
        CREATE INDEX IF NOT EXISTS idx_chat_history_timestamp ON chat_history(timestamp DESC);

        CREATE TABLE IF NOT EXISTS user_input_details (
            id SERIAL PRIMARY KEY,
            user_id TEXT NOT NULL UNIQUE,
            input_fields JSONB NOT NULL DEFAULT '{}'::jsonb
        );

        CREATE INDEX IF NOT EXISTS idx_user_input_details_user_id ON user_input_details(user_id);
        """

        # Execute SQL
        cursor.execute(sql_statements)
        conn.commit()

        print("✅ Tables and indexes created successfully.")

    except psycopg2.Error as e:
        print("❌ Error while creating tables:", e)
        if conn:
            conn.rollback()

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    create_tables()
