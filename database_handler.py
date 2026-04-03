import psycopg2
import json
from datetime import datetime
from psycopg2.extras import RealDictCursor

# Database configuration
DB_CONFIG = {
    'host': '216.48.181.189',
    'port': 5432,
    'database': 'arkachatbot',
    'user': 'postgres',
    'password': 'arkachatbot'
}

# Fixed user ID
FIXED_USER_ID = "c8042fe5-b6c2-4c6b-af1a-1c4520a0d04f"


class DatabaseHandler:
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.conn.autocommit = True

    def __del__(self):
        if hasattr(self, 'conn'):
            self.conn.close()

    def save_chat_message(self, message, role, node):
        """Save a chat message to chat_history table"""
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO chat_history (user_id, message, role, timestamp, node)
                VALUES (%s, %s, %s, %s, %s)
            """, (FIXED_USER_ID, message, role, datetime.now(), node))

    def get_last_chat_entry(self):
        """Get the last chat entry for the fixed user"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM chat_history 
                WHERE user_id = %s 
                ORDER BY id DESC 
                LIMIT 1
            """, (FIXED_USER_ID,))
            return cur.fetchone()

    def get_chat_history(self):
        """Get all chat history for the fixed user"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT message, role, node FROM chat_history 
                WHERE user_id = %s 
                ORDER BY id ASC
            """, (FIXED_USER_ID,))
            return cur.fetchall()

    def get_user_input_fields(self):
        """Get user input fields from user_input_details table"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT input_fields FROM user_input_details 
                WHERE user_id = %s
            """, (FIXED_USER_ID,))
            result = cur.fetchone()
            return result['input_fields'] if result else {}

    def upsert_user_input_fields(self, fields_update):
        """Update or insert user input fields"""
        current_fields = self.get_user_input_fields()
        # Merge new fields with existing ones
        current_fields.update(fields_update)

        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_input_details (user_id, input_fields)
                VALUES (%s, %s)
                ON CONFLICT (user_id) 
                DO UPDATE SET input_fields = %s
            """, (FIXED_USER_ID, json.dumps(current_fields), json.dumps(current_fields)))

    def clear_user_data(self):
        """Clear all data for the fixed user (for testing/reset)"""
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM chat_history WHERE user_id = %s", (FIXED_USER_ID,))
            cur.execute("DELETE FROM user_input_details WHERE user_id = %s", (FIXED_USER_ID,))

    def get_last_node(self):
        """Get the last node from chat history"""
        last_entry = self.get_last_chat_entry()
        return last_entry['node'] if last_entry else None

    def save_session_state(self, state, next_step):
        """Save current session state to database"""
        # Save state as part of user_input_fields
        state_data = {
            'session_state': state,
            'next_step': next_step
        }
        self.upsert_user_input_fields(state_data)
