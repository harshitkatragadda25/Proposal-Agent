import json
import os
import psycopg2
from datetime import datetime
from typing import List, Dict, Any
from psycopg2.extras import RealDictCursor

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5434,
    'database': 'proposalagentchatdb',
    'user': 'postgres',
    'password': 'Deadpool@123'
}


class MessageStore:
    def __init__(self, json_file: str = "conversation_history.json"):
        self.json_file = json_file
        self.ensure_file_exists()

    def ensure_file_exists(self):
        """Create the JSON file if it doesn't exist"""
        if not os.path.exists(self.json_file):
            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump({"conversations": []}, f, indent=2)

    def add_message(self, role: str, content: str, conversation_id: str = "imported", timestamp: str = None):
        """Add a message to the conversation history"""
        if timestamp is None:
            timestamp = datetime.now().isoformat()

        message = {
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "timestamp": timestamp
        }

        # Read existing data
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if "conversations" not in data:
                data = {"conversations": []}
        except (FileNotFoundError, json.JSONDecodeError):
            data = {"conversations": []}

        # Add new message
        data["conversations"].append(message)

        # Write back to file
        with open(self.json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_messages(self, conversation_id: str = "imported", limit: int = None) -> List[Dict[str, Any]]:
        """Get messages for a conversation, optionally limited to recent N messages"""
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if "conversations" not in data:
                return []

            # Filter messages for this conversation
            messages = [
                msg for msg in data["conversations"]
                if msg["conversation_id"] == conversation_id
            ]

            # Sort by timestamp (most recent last)
            messages.sort(key=lambda x: x["timestamp"])

            # Apply limit if specified
            if limit:
                messages = messages[-limit:]

            return messages

        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def clear_conversation(self, conversation_id: str = "imported"):
        """Clear all messages for a specific conversation"""
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if "conversations" not in data:
                data = {"conversations": []}
        except (FileNotFoundError, json.JSONDecodeError):
            data = {"conversations": []}

        # Filter out messages from this conversation
        data["conversations"] = [
            msg for msg in data["conversations"]
            if msg["conversation_id"] != conversation_id
        ]

        with open(self.json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def test_database_connection(self):
        """Test database connection"""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            conn.close()
            return True, "Database connection successful"
        except psycopg2.Error as e:
            return False, f"Database connection failed: {str(e)}"

    def import_from_database(self, conversation_id: str = "database_import"):
        """Import ALL messages from chat_history table in database"""

        print("🔗 Connecting to database...")

        # Test connection first
        success, message = self.test_database_connection()
        if not success:
            print(f"❌ {message}")
            return 0

        print("✅ Database connection successful")

        try:
            # Connect to database
            conn = psycopg2.connect(**DB_CONFIG)

            # Clear existing conversation first
            self.clear_conversation(conversation_id)

            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get ALL messages from chat_history table
                print("📊 Fetching all messages from chat_history table...")

                cur.execute("""
                    SELECT id, user_id, message, role, timestamp, node
                    FROM chat_history 
                    ORDER BY id ASC
                """)

                db_messages = cur.fetchall()

                if not db_messages:
                    print("📭 No messages found in chat_history table")
                    return 0

                print(f"📋 Found {len(db_messages)} messages in database")
                print("🔄 Importing messages to JSON...")

                imported_count = 0

                for db_msg in db_messages:
                    # Convert database message to our format
                    timestamp_str = db_msg['timestamp'].isoformat() if db_msg[
                        'timestamp'] else datetime.now().isoformat()

                    # Add message to JSON store
                    self.add_message(
                        role=db_msg['role'],
                        content=db_msg['message'],
                        conversation_id=conversation_id,
                        timestamp=timestamp_str
                    )
                    imported_count += 1

                conn.close()
                return imported_count

        except psycopg2.Error as e:
            print(f"❌ Database error: {str(e)}")
            return 0
        except Exception as e:
            print(f"❌ Import error: {str(e)}")
            return 0

    def show_database_stats(self):
        """Show statistics about the database"""
        try:
            conn = psycopg2.connect(**DB_CONFIG)

            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get total message count
                cur.execute("SELECT COUNT(*) as total FROM chat_history")
                total_count = cur.fetchone()['total']

                # Get message count by role
                cur.execute("""
                    SELECT role, COUNT(*) as count 
                    FROM chat_history 
                    GROUP BY role 
                    ORDER BY role
                """)
                role_counts = cur.fetchall()

                # Get unique users
                cur.execute("SELECT COUNT(DISTINCT user_id) as unique_users FROM chat_history")
                unique_users = cur.fetchone()['unique_users']

                # Get date range
                cur.execute("""
                    SELECT 
                        MIN(timestamp) as earliest,
                        MAX(timestamp) as latest 
                    FROM chat_history
                """)
                date_range = cur.fetchone()

                print(f"\n📊 Database Statistics:")
                print(f"   📝 Total messages: {total_count}")
                print(f"   👥 Unique users: {unique_users}")

                if role_counts:
                    print(f"   📋 Messages by role:")
                    for role_count in role_counts:
                        print(f"      • {role_count['role']}: {role_count['count']}")

                if date_range['earliest'] and date_range['latest']:
                    print(f"   📅 Date range: {date_range['earliest'].date()} to {date_range['latest'].date()}")

            conn.close()

        except psycopg2.Error as e:
            print(f"❌ Database error: {str(e)}")


def main():
    """Database import interface"""
    store = MessageStore()

    print("🗄️  Database Import Manager")
    print("=" * 30)

    # Show database configuration
    print(f"🔗 Database: {DB_CONFIG['database']}")
    print(f"🏠 Host: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"👤 User: {DB_CONFIG['user']}")

    try:
        # Test database connection
        print("\n🔍 Testing database connection...")
        success, message = store.test_database_connection()

        if not success:
            print(f"❌ {message}")
            print("\n🔧 Please check:")
            print("   - Database is running")
            print("   - Database credentials are correct")
            print("   - Port 5434 is accessible")
            print("   - Database 'proposalagentchatdb' exists")
            return

        print("✅ Database connection successful!")

        # Show database statistics
        store.show_database_stats()

        # Ask for confirmation
        print(f"\n📥 Import all messages from database?")
        confirm = input("Type 'yes' to proceed: ").strip().lower()

        if confirm != 'yes':
            print("❌ Import cancelled")
            return

        # Import all messages from database
        print("\n🔄 Starting database import...")
        imported_count = store.import_from_database("database_import")

        if imported_count > 0:
            print(f"\n✅ Import Successful!")
            print(f"📁 Conversation ID: database_import")
            print(f"📝 Messages imported: {imported_count}")
            print(f"💾 Saved to: conversation_history.json")
            print(f"\n💡 You can now use the chatbot with:")
            print(f"   python chatbot_main.py --conversation database_import")
        else:
            print("❌ No messages were imported from database")

    except KeyboardInterrupt:
        print("\n❌ Operation cancelled")
    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    main()