import os
import json
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
import logging

# Set up logging to see what's happening
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Single JSON file for all user data
SOLAR_USERS_FILE = 'solar_users.json'

# Questions to ask, in order
questions = [
    ('client_name', 'Client Name'),
    ('project_name', 'Project Name'),
    ('address', 'Address'),
    ('usage_of_electricity', 'Usage of Electricity')
]

# Initialize Ollama LLM with better error handling
try:
    llm = Ollama(model="mistral", temperature=0.5)
    # Test the LLM connection
    test_response = llm("Hello")
    logger.info(f"LLM test successful: {test_response[:50]}...")
except Exception as e:
    logger.error(f"Failed to initialize LLM: {e}")
    llm = None

fresh_start_template = PromptTemplate(
    input_variables=[],
    template="""
You are a friendly solar sales assistant. Generate a greeting for a new user that:
- Greets and explains you'll collect four details
- Asks for Client Name
- Keep it ≤ 30 words, warm and professional

Example: "Welcome! I'll help create your solar proposal by collecting 4 details. Let's start - what's your Client Name?"
"""
)

welcome_back_yesno_template = PromptTemplate(
    input_variables=["filled_fields", "missing_fields"],
    template="""
You are a solar sales assistant welcoming back a user with saved project data.

Details already provided:
{filled_fields}

Details still needed:
{missing_fields}

Generate a message that:
- Shows what they've filled and what's missing
- Asks "Reply yes/no to continue"
- Keep it ≤ 40 words

Example: "Hey, good to see you again! Filled: [filled items]. Missing: [missing items]. Shall we pick up where we left off? Type yes to continue or no to start over."
"""
)

continue_same_session_template = PromptTemplate(
    input_variables=["filled_fields", "missing_fields", "next_field"],
    template="""
You are continuing with a user in the same session.

Progress so far:
Filled: {filled_fields}
Missing: {missing_fields}

Generate a message that:
- Shows what's filled and what's missing
- Asks for next field: {next_field}
- Keep it ≤ 30 words

Example: "Great progress! Filled: [filled items]. Still need: [missing items]. Next, your {next_field}?"
"""
)

welcome_back_missing_template = PromptTemplate(
    input_variables=["filled_fields", "missing_fields", "next_field"],
    template="""
You are welcoming back a user with incomplete project data.

Filled: {filled_fields}
Missing: {missing_fields}

Generate a message with:
- 20 words: warm welcome back
- 20 words: show progress and ask for {next_field}
- Total ≤ 40 words

Example: "Hey, good to see you again! Progress: [items]. Still need: [missing]. What's your {next_field}?"
"""
)

all_complete_template = PromptTemplate(
    input_variables=["project_details"],
    template="""
User has completed all project details.

Complete project:
{project_details}

Generate a congratulatory message that:
- Congratulates completion
- Mentions proposal creation
- Keep it ≤ 30 words

Example: "Perfect! All details complete: [summary]. Your solar proposal is ready for creation!"
"""
)

def load_solar_db():
    if os.path.exists(SOLAR_USERS_FILE):
        try:
            with open(SOLAR_USERS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading database: {e}")
            return {}
    return {}

def save_solar_db(db):
    try:
        with open(SOLAR_USERS_FILE, 'w') as f:
            json.dump(db, f, indent=2)
        logger.info(f"Database saved to {SOLAR_USERS_FILE}")
    except Exception as e:
        logger.error(f"Error saving database: {e}")

def get_user_data(db, user_id):
    if user_id not in db:
        db[user_id] = {
            "sessions": [],
            "project": {}
        }
    return db[user_id]

def get_user_project(db, user_id):
    user_data = get_user_data(db, user_id)
    return user_data.get("project", {})

def add_user_session(db, user_id, session_id):
    user_data = get_user_data(db, user_id)
    if session_id not in user_data["sessions"]:
        user_data["sessions"].append(session_id)
        return True  # New session added
    return False  # Session already exists

def update_user_project(db, user_id, project_data):
    user_data = get_user_data(db, user_id)
    user_data["project"] = project_data

def wipe_user_project(db, user_id):
    user_data = get_user_data(db, user_id)
    user_data["project"] = {}

def get_prompt(template_name, **kwargs):
    """
    Generate dynamic prompts using LLM or fallback to hard-coded messages
    """
    templates = {
        'fresh_start': fresh_start_template,
        'welcome_back_yesno': welcome_back_yesno_template,
        'continue_same_session': continue_same_session_template,
        'welcome_back_missing': welcome_back_missing_template,
        'all_complete': all_complete_template
    }

    # Fallback messages
    fallbacks = {
        'fresh_start': "Welcome! I'll help create your solar proposal. What's your Client Name?",
        'welcome_back_yesno': f"Hey, good to see you again! Filled: {kwargs.get('filled_fields', 'None')}. Missing: {kwargs.get('missing_fields', 'None')}. Shall we pick up where we left off? Type yes to continue or no to start over.",
        'continue_same_session': f"Progress: {kwargs.get('filled_fields', 'None')}. Missing: {kwargs.get('missing_fields', 'None')}. Next: {kwargs.get('next_field', 'next detail')}?",
        'welcome_back_missing': f"Hey, good to see you again! What's your {kwargs.get('next_field', 'next detail')}? Shall we pick up where we left off? Type yes to continue or no to start over.",
        'all_complete': "Perfect! All details complete. Your solar proposal is ready!"
    }

    if template_name not in templates:
        logger.error(f"Unknown template '{template_name}'")
        return f"Error: Unknown template '{template_name}'"

    # If LLM is not available, use fallback immediately
    if llm is None:
        logger.warning("LLM not available, using fallback message")
        return fallbacks.get(template_name, "Please continue...")

    try:
        template = templates[template_name]
        logger.debug(f"Formatting template '{template_name}' with kwargs: {kwargs}")
        
        # Format the template with provided arguments
        prompt_text = template.format(**kwargs)
        logger.debug(f"Formatted prompt: {prompt_text[:100]}...")
        
        # Call LLM
        logger.debug("Calling LLM...")
        response = llm(prompt_text)
        logger.debug(f"LLM response: {response[:100]}...")
        
        return response.strip()
        
    except Exception as e:
        logger.error(f"Error in get_prompt for template '{template_name}': {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Template args: {kwargs}")
        
        # Return fallback message
        logger.warning(f"Using fallback message for template '{template_name}'")
        return fallbacks.get(template_name, "Please continue...")

def get_missing_fields(project):
    return [(k, label) for k, label in questions if not project.get(k)]

def get_next_missing_field(project):
    missing = get_missing_fields(project)
    return missing[0] if missing else None

def format_project_details(project):
    items = []
    for key, label in questions:
        if project.get(key):
            items.append(f"{label}: {project[key]}")
    return ", ".join(items) if items else "No details"

def format_filled_fields(project):
    items = []
    for key, label in questions:
        if project.get(key):
            items.append(f"{label}: {project[key]}")
    return "; ".join(items) if items else "None"

def format_missing_fields(missing):
    return ", ".join([label for _, label in missing])

def is_project_complete(project):
    return len(get_missing_fields(project)) == 0

def resolve_flow_type(db, user_id, session_id):
    # Check if user exists
    if user_id not in db:
        return 'fresh_start'

    user_data = db[user_id]
    project = user_data.get("project", {})
    sessions = user_data.get("sessions", [])

    project_complete = is_project_complete(project)
    session_exists = session_id in sessions

    if not session_exists:
        # New session for existing user
        if project_complete:
            return 'welcome_back_complete'
        else:
            return 'welcome_back_missing'
    else:
        # Existing session
        if project_complete:
            return 'continue_complete'
        else:
            return 'continue_progress'

class StateEngine:
    def __init__(self, user_id, session_id):
        self.user_id = user_id
        self.session_id = session_id
        self.project = {}
        self.next_step = 'initial'
        self.awaiting_yesno = False
        self.db = load_solar_db()

    def get_initial_state(self):
        flow_type = resolve_flow_type(self.db, self.user_id, self.session_id)
        self.project = get_user_project(self.db, self.user_id)

        # Add session if new
        is_new_session = add_user_session(self.db, self.user_id, self.session_id)
        if is_new_session:
            save_solar_db(self.db)

        logger.info(f"Flow Type: {flow_type}")

        if flow_type == 'fresh_start':
            self.next_step = 'collect_details'
            message = get_prompt('fresh_start')

        elif flow_type == 'welcome_back_complete':
            self.next_step = 'project_complete'
            message = get_prompt('all_complete',
                                 project_details=format_project_details(self.project))

        elif flow_type == 'welcome_back_missing':
            self.next_step = 'await_yesno'
            self.awaiting_yesno = True
            missing_fields = get_missing_fields(self.project)
            message = get_prompt('welcome_back_yesno',
                                 filled_fields=format_filled_fields(self.project),
                                 missing_fields=format_missing_fields(missing_fields))

        elif flow_type == 'continue_complete':
            self.next_step = 'project_complete'
            message = get_prompt('all_complete',
                                 project_details=format_project_details(self.project))

        elif flow_type == 'continue_progress':
            self.next_step = 'collect_details'
            next_field = get_next_missing_field(self.project)
            missing_fields = get_missing_fields(self.project)
            message = get_prompt('continue_same_session',
                                 filled_fields=format_filled_fields(self.project),
                                 missing_fields=format_missing_fields(missing_fields),
                                 next_field=next_field[1] if next_field else "next detail")

        return message

    def handle_yesno_response(self, user_input):
        response = user_input.strip().lower()

        if response in ['yes', 'y', 'continue']:
            # Continue with existing project
            self.next_step = 'collect_details'
            self.awaiting_yesno = False

            next_field = get_next_missing_field(self.project)
            if next_field:
                return f"Great! Let's continue. What's your {next_field[1]}?"
            else:
                self.next_step = 'project_complete'
                return get_prompt('all_complete',
                                  project_details=format_project_details(self.project))

        elif response in ['no', 'n', 'fresh', 'start over']:
            # Fresh start - wipe project
            wipe_user_project(self.db, self.user_id)
            self.project = {}
            self.next_step = 'collect_details'
            self.awaiting_yesno = False
            save_solar_db(self.db)

            return get_prompt('fresh_start')

        else:
            # Invalid response
            return "Please reply 'yes' to continue or 'no' for fresh start."

    def collect_details(self, user_input):
        next_field = get_next_missing_field(self.project)

        if next_field:
            # Save the answer
            field_key, field_label = next_field
            self.project[field_key] = user_input.strip()

            # Update database
            update_user_project(self.db, self.user_id, self.project)
            save_solar_db(self.db)

            # Check if more fields needed
            remaining_field = get_next_missing_field(self.project)

            if remaining_field:
                # Ask next question
                next_key, next_label = remaining_field
                return f"Great! Now, please provide your {next_label}:"
            else:
                # All complete
                self.next_step = 'project_complete'
                return get_prompt('all_complete',
                                  project_details=format_project_details(self.project))

        return "All details already collected!"

def test_llm_connection():
    """Test if LLM is working properly"""
    print("🔧 Testing LLM Connection...")
    try:
        if llm is None:
            print("❌ LLM is None - check Ollama installation and model")
            return False
            
        test_prompt = "Say hello in exactly 5 words."
        response = llm(test_prompt)
        print(f"✅ LLM Test Response: {response}")
        return True
    except Exception as e:
        print(f"❌ LLM Test Failed: {e}")
        return False

def get_user_credentials():
    print("\n🔐 Solar Proposal Assistant")
    print("-" * 30)

    user_id = input("Enter User ID: ").strip()
    session_id = input("Enter Session ID: ").strip()

    if not user_id or not session_id:
        print("❌ Both User ID and Session ID are required!")
        return None, None

    print(f"👤 User: {user_id}")
    print(f"🔑 Session: {session_id}")
    print()

    return user_id, session_id

def display_database():
    db = load_solar_db()

    print("\n📊 Solar Users Database:")
    print("-" * 40)

    if not db:
        print("No users in database yet.")
        return

    for user_id, user_data in db.items():
        sessions = user_data.get("sessions", [])
        project = user_data.get("project", {})
        completed_count = len([v for v in project.values() if v])

        print(f"👤 User: {user_id}")
        print(f"   Sessions ({len(sessions)}): {sessions}")
        print(f"   Project Progress: {completed_count}/4")

        for key, label in questions:
            value = project.get(key, "")
            status = "✅" if value else "❌"
            print(f"      {status} {label}: {value if value else 'Not provided'}")
        print()

def main():
    print("🌟 Integrated Solar Proposal Chatbot")
    print("=" * 45)

    # Test LLM connection first
    test_llm_connection()

    # Show current database
    display_database()

    # Get credentials
    user_id, session_id = get_user_credentials()
    if not user_id or not session_id:
        return

    # Initialize state engine
    state = StateEngine(user_id, session_id)

    # Get initial message
    initial_message = state.get_initial_state()

    print("=" * 45)
    print(f"🤖 Bot: {initial_message}")
    print()

    # Main conversation loop
    while state.next_step != 'project_complete':
        user_input = input("👤 You: ").strip()
        print()

        if user_input.lower() in ['quit', 'exit', 'bye']:
            print("👋 Goodbye! Your data has been saved.")
            break

        # Route based on current state
        if state.awaiting_yesno:
            response = state.handle_yesno_response(user_input)
        elif state.next_step == 'collect_details':
            response = state.collect_details(user_input)
        else:
            response = "Session complete!"

        print(f"🤖 Bot: {response}")
        print()

        if state.next_step == 'project_complete':
            print("✅ Solar proposal setup complete!")
            break

    # Show final database state
    print("\n" + "=" * 45)
    display_database()

if __name__ == "__main__":
    main()