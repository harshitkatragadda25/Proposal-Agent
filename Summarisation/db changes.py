import psycopg2
from psycopg2 import sql
import json
from datetime import datetime


class SolarChatDatabase:
    def __init__(self):
        self.connection_params = {
        'host': '216.48.181.189',
        'port': 5432,
        'database': 'arkachatbot',
        'user': 'postgres',
        'password': 'arkachatbot',
        }
        self.connection = None

    def connect(self):
        """Connect to PostgreSQL database"""
        try:
            self.connection = psycopg2.connect(**self.connection_params)
            print("✅ Successfully connected to PostgreSQL database")
            return True
        except psycopg2.Error as e:
            print(f"❌ Error connecting to PostgreSQL: {e}")
            return False

    def create_tables(self):
        """Create all required tables if they don't exist"""
        if not self.connection:
            print("❌ No database connection")
            return False

        cursor = self.connection.cursor()

        try:
            # Create ChatHistory table
            create_chathistory = """
            CREATE TABLE IF NOT EXISTS ChatHistory (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                message TEXT NOT NULL,
                role VARCHAR(20) CHECK (role IN ('user', 'assistant', 'system')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                intent VARCHAR(255)
            );
            """

            # Create Logging table
            create_logging = """
            CREATE TABLE IF NOT EXISTS Logging (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                message TEXT,
                response TEXT,
                model VARCHAR(255),
                input_tokens INTEGER,
                output_tokens INTEGER,
                time_taken_ms INTEGER,
                total_cost NUMERIC(10, 6),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """

            # Create UserInputInformation table
            create_userinput = """
            CREATE TABLE IF NOT EXISTS UserInputInformation (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                details JSONB,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """

            # Execute table creation
            cursor.execute(create_chathistory)
            print("✅ ChatHistory table created/verified")

            cursor.execute(create_logging)
            print("✅ Logging table created/verified")

            cursor.execute(create_userinput)
            print("✅ UserInputInformation table created/verified")

            # Create indexes for better performance
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_chathistory_user_id ON ChatHistory(user_id);",
                "CREATE INDEX IF NOT EXISTS idx_chathistory_created_at ON ChatHistory(created_at);",
                "CREATE INDEX IF NOT EXISTS idx_logging_user_id ON Logging(user_id);",
                "CREATE INDEX IF NOT EXISTS idx_logging_created_at ON Logging(created_at);",
                "CREATE INDEX IF NOT EXISTS idx_userinput_user_id ON UserInputInformation(user_id);"
            ]

            for index_sql in indexes:
                cursor.execute(index_sql)

            print("✅ Database indexes created/verified")

            # Commit changes
            self.connection.commit()
            print("🎉 All tables and indexes created successfully!")
            return True

        except psycopg2.Error as e:
            print(f"❌ Error creating tables: {e}")
            self.connection.rollback()
            return False
        finally:
            cursor.close()

    def insert_chat_message(self, user_id, message, role, intent=None):
        """Insert a new chat message"""
        cursor = self.connection.cursor()
        try:
            insert_sql = """
            INSERT INTO ChatHistory (user_id, message, role, intent)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
            """
            cursor.execute(insert_sql, (user_id, message, role, intent))
            message_id = cursor.fetchone()[0]
            self.connection.commit()
            print(f"✅ Chat message inserted with ID: {message_id}")
            return message_id
        except psycopg2.Error as e:
            print(f"❌ Error inserting chat message: {e}")
            self.connection.rollback()
            return None
        finally:
            cursor.close()

    def log_llm_interaction(self, user_id, message, response, model,
                            input_tokens=None, output_tokens=None,
                            time_taken_ms=None, total_cost=None):
        """Log LLM interaction details"""
        cursor = self.connection.cursor()
        try:
            insert_sql = """
            INSERT INTO Logging (user_id, message, response, model, 
                               input_tokens, output_tokens, time_taken_ms, total_cost)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
            """
            cursor.execute(insert_sql, (user_id, message, response, model,
                                        input_tokens, output_tokens, time_taken_ms, total_cost))
            log_id = cursor.fetchone()[0]
            self.connection.commit()
            print(f"✅ LLM interaction logged with ID: {log_id}")
            return log_id
        except psycopg2.Error as e:
            print(f"❌ Error logging LLM interaction: {e}")
            self.connection.rollback()
            return None
        finally:
            cursor.close()

    def update_user_information(self, user_id, address=None, consumption=None,
                                price=None, project_status=None, additional_data=None):
        """Update or insert user information"""
        cursor = self.connection.cursor()
        try:
            # Prepare JSONB data
            details = {}
            if address:
                details['address'] = address
            if consumption:
                details['consumption'] = consumption
            if price:
                details['price'] = price
            if project_status:
                details['project_status'] = project_status
            if additional_data:
                details.update(additional_data)

            # Check if user already exists
            cursor.execute("SELECT id FROM UserInputInformation WHERE user_id = %s", (user_id,))
            existing = cursor.fetchone()

            if existing:
                # Update existing record
                update_sql = """
                UPDATE UserInputInformation 
                SET details = COALESCE(details, '{}'::jsonb) || %s::jsonb,
                    last_updated = CURRENT_TIMESTAMP
                WHERE user_id = %s
                RETURNING id;
                """
                cursor.execute(update_sql, (json.dumps(details), user_id))
            else:
                # Insert new record
                insert_sql = """
                INSERT INTO UserInputInformation (user_id, details)
                VALUES (%s, %s)
                RETURNING id;
                """
                cursor.execute(insert_sql, (user_id, json.dumps(details)))

            record_id = cursor.fetchone()[0]
            self.connection.commit()
            print(f"✅ User information updated with ID: {record_id}")
            return record_id
        except psycopg2.Error as e:
            print(f"❌ Error updating user information: {e}")
            self.connection.rollback()
            return None
        finally:
            cursor.close()

    def get_user_chat_history(self, user_id, limit=50):
        """Get chat history for a user"""
        cursor = self.connection.cursor()
        try:
            select_sql = """
            SELECT id, message, role, created_at, intent
            FROM ChatHistory 
            WHERE user_id = %s 
            ORDER BY created_at DESC 
            LIMIT %s;
            """
            cursor.execute(select_sql, (user_id, limit))
            results = cursor.fetchall()
            return results
        except psycopg2.Error as e:
            print(f"❌ Error fetching chat history: {e}")
            return []
        finally:
            cursor.close()

    def get_user_information(self, user_id):
        """Get user information"""
        cursor = self.connection.cursor()
        try:
            select_sql = """
            SELECT details, last_updated
            FROM UserInputInformation 
            WHERE user_id = %s;
            """
            cursor.execute(select_sql, (user_id,))
            result = cursor.fetchone()
            return result
        except psycopg2.Error as e:
            print(f"❌ Error fetching user information: {e}")
            return None
        finally:
            cursor.close()

    def close_connection(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            print("✅ Database connection closed")


def main():
    """Main function to set up database"""
    print("🚀 Setting up Solar Chat Database...")
    print("=" * 50)

    # Initialize database
    db = SolarChatDatabase()

    # Connect to database
    if not db.connect():
        return

    # Create tables
    if not db.create_tables():
        return

    print("\n" + "=" * 50)
    print("🎉 Database setup completed successfully!")
    print("\n📋 Tables created:")
    print("   • ChatHistory - Store chat messages")
    print("   • Logging - Track LLM interactions")
    print("   • UserInputInformation - Store user data (address, consumption, etc.)")

    # Example usage
    print("\n💡 Testing with sample data...")

    # Test inserting sample data
    user_id = 1001

    # Insert chat messages
    db.insert_chat_message(user_id, "Hi, I need solar panels", "user", "solar_inquiry")
    db.insert_chat_message(user_id, "Great! What's your address?", "assistant", "address_request")
    db.insert_chat_message(user_id, "56 Palm Street, Bangalore", "user", "address_provided")

    # Log LLM interaction
    db.log_llm_interaction(
        user_id=user_id,
        message="Hi, I need solar panels",
        response="Great! What's your address?",
        model="llama3.2",
        input_tokens=10,
        output_tokens=15,
        time_taken_ms=1500,
        total_cost=0.001
    )

    # Update user information
    db.update_user_information(
        user_id=user_id,
        address="56 Palm Street, Bangalore",
        consumption="620 kWh",
        project_status="design_created"
    )

    print("✅ Sample data inserted successfully!")

    # Close connection
    db.close_connection()


if __name__ == "__main__":
    main()