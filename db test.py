import psycopg2
from psycopg2.extras import Json

# Configuration for the 'arkachatbot' database
db_config = {
    'host': '216.48.181.189',
    'port': 5432,
    'database': 'arkachatbot',
    'user': 'postgres',
    'password': 'arkachatbot',
}

def get_connection():
    """
    Establish and return a new database connection using psycopg2.
    """
    return psycopg2.connect(**db_config)


def insert_chat_history(user_id: str, message: str, role: str, node: str):
    """
    Insert a record into the chat_history table.

    :param user_id:   unique identifier for the user
    :param message:   the chat message content
    :param role:      'user' or 'bot'
    :param node:      the conversation node or step name
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO chat_history (user_id, message, role, node)
                    VALUES (%s, %s, %s, %s);
                    """,
                    (user_id, message, role, node)
                )
    finally:
        conn.close()


def insert_user_input_details(user_id: str, input_fields: dict):
    """
    Insert or update a record in the user_input_details table.

    :param user_id:      unique identifier for the user
    :param input_fields: dict of user-provided fields (JSONB)
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO user_input_details (user_id, input_fields)
                    VALUES (%s, %s)
                    ON CONFLICT (user_id) DO UPDATE
                      SET input_fields = user_input_details.input_fields || EXCLUDED.input_fields;
                    """,
                    (user_id, Json(input_fields))
                )
    finally:
        conn.close()


if __name__ == '__main__':
    # Example usage:
    insert_chat_history(
        user_id='user_123',
        message='Hello, this is a test message.',
        role='user',
        node='Greeting'
    )
    insert_user_input_details(
        user_id='user_123',
        input_fields={
            'project_name': 'Solar Proposal',
            'address': '123 Main St'
        }
    )
    print("✅ Data inserted into both tables successfully.")
