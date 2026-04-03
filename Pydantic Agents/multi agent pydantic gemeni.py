import json
import os
import asyncio
import random
import re
from datetime import datetime
from typing import Optional, Dict, Any, Union, List
from pydantic import BaseModel, Field, EmailStr
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import Usage, UsageLimits
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.usage import Usage, UsageLimits
from secrets import GEMINI_API_KEY


# Chat History Management
class ChatMessage(BaseModel):
    timestamp: str
    sender: str  # 'user', 'design_agent', 'project_agent', 'orchestrator'
    message: str
    tokens_used: Optional[Dict[str, int]] = None  # request_tokens, response_tokens, total_tokens


class ChatHistory:
    def __init__(self, filename: str = "chat_history.json"):
        self.filename = filename
        self.messages: List[ChatMessage] = []
        self.session_start = datetime.now().isoformat()
        self.total_tokens = {
            "total_requests": 0,
            "total_request_tokens": 0,
            "total_response_tokens": 0,
            "total_tokens_used": 0
        }
        print(f"💬 Chat history will be saved to: {os.path.abspath(self.filename)}")

    def add_message(self, sender: str, message: str, tokens_used: Optional[Dict[str, int]] = None):
        """Add a message to the chat history"""
        chat_message = ChatMessage(
            timestamp=datetime.now().isoformat(),
            sender=sender,
            message=message,
            tokens_used=tokens_used
        )
        self.messages.append(chat_message)

        # Update token totals if provided
        if tokens_used:
            self.total_tokens["total_requests"] += tokens_used.get("requests", 0)
            self.total_tokens["total_request_tokens"] += tokens_used.get("request_tokens", 0)
            self.total_tokens["total_response_tokens"] += tokens_used.get("response_tokens", 0)
            self.total_tokens["total_tokens_used"] += tokens_used.get("total_tokens", 0)

            print(
                f"🔢 Tokens used - Input: {tokens_used.get('request_tokens', 0)}, Output: {tokens_used.get('response_tokens', 0)}, Total: {tokens_used.get('total_tokens', 0)}")

    def save_history(self) -> bool:
        """Save chat history to JSON file"""
        try:
            history_data = {
                "session_info": {
                    "session_start": self.session_start,
                    "session_end": datetime.now().isoformat(),
                    "total_messages": len(self.messages),
                    "token_usage": self.total_tokens
                },
                "messages": [msg.model_dump() for msg in self.messages]
            }

            with open(self.filename, 'w') as f:
                json.dump(history_data, f, indent=2)

            print(f"💾 ✅ Chat history saved successfully to {self.filename}")
            print(f"📊 Session Stats:")
            print(f"   📝 Total Messages: {len(self.messages)}")
            print(f"   🔢 Total Requests: {self.total_tokens['total_requests']}")
            print(f"   📥 Input Tokens: {self.total_tokens['total_request_tokens']}")
            print(f"   📤 Output Tokens: {self.total_tokens['total_response_tokens']}")
            print(f"   🎯 Total Tokens: {self.total_tokens['total_tokens_used']}")

            return True
        except Exception as e:
            print(f"❌ Error saving chat history: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get current session statistics"""
        return {
            "session_start": self.session_start,
            "total_messages": len(self.messages),
            "token_usage": self.total_tokens,
            "messages_by_sender": {
                sender: len([msg for msg in self.messages if msg.sender == sender])
                for sender in ["user", "design_agent", "project_agent", "orchestrator"]
            }
        }


# Shared data models
class ProjectDetails(BaseModel):
    project_name: Optional[str] = Field(None, description="Name of the Project")
    project_address: Optional[str] = Field(None, description="Installation site (city/address)")
    client_email: Optional[EmailStr] = Field(None, description="Client's contact email")
    project_id: Optional[int] = Field(None, description="Unique project identifier (auto-generated)")

    def get_missing_fields(self) -> list[str]:
        missing = []
        if not self.project_name:
            missing.append("project_name")
        if not self.project_address:
            missing.append("project_address")
        if not self.client_email:
            missing.append("client_email")
        return missing

    def is_complete(self) -> bool:
        return len(self.get_missing_fields()) == 0

    def has_project_id(self) -> bool:
        return self.project_id is not None


# Session State Management
class SessionState:
    def __init__(self):
        self.current_agent = None
        self.last_action = None
        self.context = {}

    def set_agent(self, agent_name: str):
        self.current_agent = agent_name

    def set_context(self, key: str, value: Any):
        self.context[key] = value

    def get_context(self, key: str, default=None):
        return self.context.get(key, default)

    def clear(self):
        self.current_agent = None
        self.last_action = None
        self.context = {}


# Orchestration result models
class ProjectSummary(BaseModel):
    found: bool = True
    project_id: int
    project_name: str
    project_address: str
    client_email: str
    summary: str


class ProjectCreated(BaseModel):
    created: bool = True
    project_id: int
    project_name: str
    project_address: str
    client_email: str
    message: str


class ProjectDataManager:
    def __init__(self, filename: str = "project_data.json"):
        self.filename = filename
        self.data = self.load_data()
        print(f"📂 Using data file: {os.path.abspath(self.filename)}")

    def load_data(self) -> ProjectDetails:
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    data_dict = json.load(f)
                    print(f"📖 Loaded existing data: {data_dict}")
                    return ProjectDetails(**data_dict)
            except Exception as e:
                print(f"❌ Error loading data: {e}")
                return ProjectDetails()
        else:
            print(f"📄 No existing data file found. Will create new one.")
        return ProjectDetails()

    def save_data(self) -> None:
        try:
            data_dict = self.data.model_dump()
            with open(self.filename, 'w') as f:
                json.dump(data_dict, f, indent=2)
            print(f"💾 ✅ Data successfully saved to {self.filename}")
            print(f"📝 Saved: {data_dict}")
        except Exception as e:
            print(f"❌ Error saving data: {e}")

    def update_field(self, field_name: str, value: Any) -> bool:
        if hasattr(self.data, field_name):
            old_value = getattr(self.data, field_name)
            setattr(self.data, field_name, value)
            print(f"🔄 Updated {field_name}: '{old_value}' → '{value}'")
            self.save_data()
            return True
        return False

    def get_status(self) -> Dict[str, Any]:
        missing = self.data.get_missing_fields()
        return {
            "current_data": self.data.model_dump(exclude_none=True),
            "missing_fields": missing,
            "is_complete": self.data.is_complete(),
            "completion_percentage": ((3 - len(missing)) / 3) * 100
        }

from pydantic_ai.providers.google_gla import GoogleGLAProvider

# Setup gemini model
gemini_model = GeminiModel(
    'gemini-2.5-pro',
    provider=GoogleGLAProvider(api_key=GEMINI_API_KEY)
)

# DESIGN AGENT
design_agent = Agent(
    model=gemini_model,
    deps_type=ProjectDataManager,
    output_type=str,
    system_prompt="""You are a Design Agent that validates project IDs and manages project access.

## YOUR CAPABILITIES:
1. **Check existing projects** by project ID
2. **Ask if users want to create new projects** when project ID is not found

## WORKFLOW FOR PROJECT ID VERIFICATION:

### STEP 1: Extract Project ID
- Look for any number in the user's message that could be a project ID
- Project IDs are 8-digit numbers (between 10000000 and 99999999)
- If no valid project ID is found, ask the user to provide one

### STEP 2: Check Project Data
- ALWAYS use the `check_project_id` tool to verify if the project ID exists
- The tool will return:
  - If ID matches: Complete project details
  - If ID doesn't match or no data exists: "No match found"

### STEP 3: Take Action Based on Result

#### If Project ID MATCHES:
- Display a professional project summary with all details:
  ```
  ✅ PROJECT FOUND!

  📋 Project Summary:
  🆔 Project ID: [ID]
  📝 Project Name: [NAME]
  📍 Address: [ADDRESS]
  📧 Client Email: [EMAIL]

  You can now proceed with the design phase.
  ```

#### If Project ID DOES NOT MATCH:
- Inform the user that the project ID was not found
- Ask if they want to create a new project instead

## CRITICAL RULES:
- NEVER make up project data - only show what's actually in the JSON file
- ALWAYS verify project IDs with the check_project_id tool
- Be clear and professional in your responses
- If no project ID is provided, ask for it explicitly

Remember: Your primary job is to validate project access."""
)


@design_agent.tool
async def check_project_id(ctx: RunContext[ProjectDataManager], project_id: int) -> Dict[str, Any]:
    # Reload data from file to get latest state
    ctx.deps.data = ctx.deps.load_data()

    # Check if there's data and if the project ID matches
    if ctx.deps.data.has_project_id() and ctx.deps.data.project_id == project_id:
        return {
            "match_found": True,
            "project_details": {
                "project_id": ctx.deps.data.project_id,
                "project_name": ctx.deps.data.project_name,
                "project_address": ctx.deps.data.project_address,
                "client_email": ctx.deps.data.client_email
            }
        }
    else:
        return {"match_found": False, "message": "No match found"}


# PROJECT AGENT
project_agent = Agent(
    model=gemini_model,
    deps_type=ProjectDataManager,
    output_type=str,
    system_prompt="""You are a helpful and structured Project Data Collection Assistant.

Your job is to:
1. Collect exactly three required fields from the user:
   - Project Name
   - Project Address  
   - Client Email
2. Once all three are collected, call a tool to generate a unique Project ID
3. Save all values using tools — do NOT assume or invent anything

---

## CRITICAL: CONVERSATION HISTORY AWARENESS

YOU HAVE ACCESS TO THE FULL CONVERSATION HISTORY. Before asking for any information:
1. Look at the message history to see what has already been discussed
2. Check what information the user has already provided in previous messages
3. NEVER ask for the same information twice
4. If user says "okay", "yes", or gives a general response, check what was already discussed

---

## MESSAGE HANDLING LOGIC (For EVERY User Message)

### STEP 1: REVIEW CONVERSATION HISTORY AND CURRENT DATA
- ALWAYS begin by calling `check_project_data`
- Look at the message history to see what has already been discussed
- Identify what information has already been provided by the user
- Check which fields are already saved and confirmed in previous messages
- DO NOT ask for information that was already provided in the conversation

### STEP 2: DETERMINE WHAT'S STILL NEEDED (WITHOUT ASKING TWICE)
Based on conversation history and saved data:
- If project_name is missing AND was not discussed before → ask for project name
- If project_address is missing AND was not discussed before → ask for project address  
- If client_email is missing AND was not discussed before → ask for client email
- If all fields are present → generate project ID

NEVER ask: "What is the project name?" if the user already provided it in conversation history.

### STEP 3: EXTRACT NEW FIELDS FROM CURRENT MESSAGE

Only look for NEW information in the user's current message:

PROJECT NAME:
- "project name is [NAME]"
- "working on [NAME] project"  
- "project is called [NAME]"
- "the [NAME] installation"
- "for [NAME] system"

PROJECT ADDRESS:
- Full or partial street addresses
- Phrases like:
  - "address is [ADDRESS]"
  - "located at [ADDRESS]"
  - "site at [LOCATION]"
  - "in [CITY/STATE/PLACE]"

CLIENT EMAIL:
- Match valid email formats only (e.g., user@example.com)
- Must contain @ and a domain
- Do not accept malformed or partial inputs

### STEP 4: SAVE NEW INFORMATION IMMEDIATELY

If NEW valid information is found in the current message:
- Call `save_project_info`
- Pass only the field and value that was explicitly provided
- Save fields one at a time
- Confirm what was saved

### STEP 5: CHECK COMPLETION AND NEXT STEPS

After saving new information:
- Call `check_project_data` to get current status
- If all fields are present but project_id is missing → call `generate_project_id`
- If fields are still missing → ask for the NEXT missing field (not already discussed)

---

## RESPONSE EXAMPLES BASED ON CONVERSATION HISTORY

**Scenario 1**: User previously said "project name is SolarVilla", now says "okay"
→ Response: "Great! I've saved the project name 'SolarVilla'. Now I need the project address."

**Scenario 2**: User provided name and address before, now asks "what do you need?"
→ Response: "I have your project name and address saved. I just need the client email address to complete the project setup."

**Scenario 3**: User provided all info but says "what's my status?"
→ Check saved data and respond with current status without asking for info again.

---

## CRITICAL RULES FOR CONVERSATION CONTINUITY

1. **HISTORY FIRST**: Always check message history before asking questions
2. **NO DUPLICATE REQUESTS**: Never ask for information already provided in conversation
3. **CONTEXT AWARE**: Understand when user gives general responses like "okay", "yes"
4. **PROGRESSIVE COLLECTION**: Ask for next missing field, not all missing fields
5. **ACCURACY CHECK**: Always verify saved data matches conversation history

---

Example of WRONG behavior:
- User: "project name is test1" → Agent saves it
- User: "okay" → Agent asks: "What is the project name?" ❌ WRONG!

Example of CORRECT behavior:
- User: "project name is test1" → Agent saves it  
- User: "okay" → Agent says: "Great! I saved 'test1'. What's the project address?" ✅ CORRECT!

---

YOU MUST MAINTAIN PERFECT CONVERSATION CONTINUITY. The user should never feel like you forgot what they just told you.
"""
)


@project_agent.tool
async def check_project_data(ctx: RunContext[ProjectDataManager]) -> Dict[str, Any]:
    # Reload data from file to get latest state
    ctx.deps.data = ctx.deps.load_data()
    status = ctx.deps.get_status()
    return status


@project_agent.tool
async def save_project_info(
        ctx: RunContext[ProjectDataManager],
        field_name: str,
        value: str
) -> str:
    valid_fields = ["project_name", "project_address", "client_email"]

    if field_name not in valid_fields:
        return f"Invalid field name. Must be one of: {valid_fields}"

    # Clean up the value - remove common prefixes that shouldn't be saved
    cleaned_value = value.strip()

    # Remove pattern prefixes if they were accidentally included
    if field_name == "project_name":
        prefixes = ["project name is ", "my project name is ", "the project name is "]
        for prefix in prefixes:
            if cleaned_value.lower().startswith(prefix.lower()):
                cleaned_value = cleaned_value[len(prefix):].strip()
                break

    elif field_name == "project_address":
        prefixes = ["address is ", "project address is ", "located at ", "location is "]
        for prefix in prefixes:
            if cleaned_value.lower().startswith(prefix.lower()):
                cleaned_value = cleaned_value[len(prefix):].strip()
                break

    elif field_name == "client_email":
        prefixes = ["email is ", "client email is ", "contact email is "]
        for prefix in prefixes:
            if cleaned_value.lower().startswith(prefix.lower()):
                cleaned_value = cleaned_value[len(prefix):].strip()
                break

    try:
        # Special validation for email field
        if field_name == "client_email":
            # Basic format check
            if "@" not in cleaned_value or "." not in cleaned_value.split("@")[-1] or len(
                    cleaned_value.split("@")) != 2:
                return f"❌ Invalid email format '{cleaned_value}'. Please provide a valid email address like: user@domain.com"

            # Validate with Pydantic
            temp_data = {"client_email": cleaned_value}
            try:
                ProjectDetails(**temp_data)
            except Exception:
                return f"❌ Invalid email format '{cleaned_value}'. Please provide a valid email address like: user@domain.com"

        # Check if field already has the same data
        current_value = getattr(ctx.deps.data, field_name)
        if current_value is not None and current_value.strip() == cleaned_value.strip():
            return f"ℹ️ {field_name} is already saved as '{current_value}'"

        # Save the cleaned value
        success = ctx.deps.update_field(field_name, cleaned_value)
        if success:
            return f"✅ Successfully saved {field_name}: {cleaned_value}"
        else:
            return f"❌ Failed to save {field_name}"

    except Exception as e:
        return f"❌ Error saving {field_name}: {str(e)}"


@project_agent.tool
async def generate_project_id(ctx: RunContext[ProjectDataManager]) -> str:
    # Check if project is complete and doesn't already have an ID
    if not ctx.deps.data.is_complete():
        return "❌ Cannot generate project ID: Basic project information is not complete yet"

    if ctx.deps.data.has_project_id():
        return f"ℹ️ Project already has ID: {ctx.deps.data.project_id}"

    # Generate a random 8-digit project ID
    project_id = random.randint(10000000, 99999999)

    # Save the project ID
    success = ctx.deps.update_field("project_id", project_id)

    if success:
        return f"🎉 Generated project ID: {project_id} - This ID can be used for future reference!"
    else:
        return "❌ Failed to save project ID"


# ORCHESTRATOR AGENT
orchestrator_agent = Agent(
    model=gemini_model,
    system_prompt=(
        "You are an intelligent project orchestrator that coordinates between specialized agents.\n\n"
        "Your responsibilities:\n"
        "1. Analyze user requests to understand their intent\n"
        "2. Route requests to appropriate specialized agents via tools\n"
        "3. Provide helpful responses based on the tool outputs\n"
        "4. Handle follow-up questions and clarifications\n\n"
        "Request Classification:\n"
        "- PROJECT CREATION requests: \"create project\", \"new project\", \"start project\", "
        "\"build project\", \"initialize project\", \"setup project\", \"I need to create\", \"help me create\"\n"
        "- DESIGN/LOOKUP requests: \"design\", \"summary\", \"generate design\", "
        "\"project summary\", \"design proposal\", \"show design\", \"lookup project\", \"find project\", "
        "\"check project\", \"project ID\", contains 8-digit numbers\n\n"
        "For simple responses like 'no', 'yes', 'thanks' - provide appropriate general responses.\n\n"
        "Guidelines:\n"
        "- Always use tools to handle specialized requests\n"
        "- Provide context and explanation with tool results\n"
        "- Ask for clarification if the request is ambiguous\n"
        "- Be helpful and guide users through the process\n"
        "- For general conversation, respond normally without tools\n\n"
        "Remember: You coordinate and enhance the work of specialized agents, don't replace them."
    )
)


# Agent conversation loops with chat history tracking
async def design_agent_loop(data_manager: ProjectDataManager, initial_message: str, session_state: SessionState,
                            chat_history: ChatHistory) -> Dict[str, Any]:
    print("\n[Orchestrator] -> [Design Agent] Transferring you to project lookup specialist...")
    session_state.set_agent("design_agent")

    # Initialize usage tracking
    usage = Usage()
    limits = UsageLimits(request_limit=100)

    try:
        # Check if project ID is in the initial message
        project_id_match = re.search(r'\b(\d{8})\b', initial_message)

        if not project_id_match:
            # Ask for project ID if not provided
            print("\n[Design Agent] I need an 8-digit project ID to look up your project.")
            project_id_input = input("Please enter your project ID: ").strip()

            # Track user input
            chat_history.add_message("user", project_id_input)

            # Validate the input
            try:
                project_id = int(project_id_input)
                if not (10000000 <= project_id <= 99999999):
                    print("❌ Project ID must be an 8-digit number")
                    return {
                        "action": "invalid_input",
                        "message": "Invalid project ID format."
                    }
            except ValueError:
                print("❌ Invalid project ID format. Please enter a number.")
                return {
                    "action": "invalid_input",
                    "message": "Invalid project ID format."
                }

            # Now check with the provided project ID
            message_to_check = f"Check project ID {project_id}"
        else:
            project_id = int(project_id_match.group(1))
            message_to_check = initial_message

        # Check project with design agent
        response = await design_agent.run(
            message_to_check,
            deps=data_manager,
            usage=usage,
            usage_limits=limits
        )

        # Track agent response and tokens
        tokens_dict = {
            "requests": response.usage().requests,
            "request_tokens": response.usage().request_tokens,
            "response_tokens": response.usage().response_tokens,
            "total_tokens": response.usage().total_tokens
        }
        chat_history.add_message("design_agent", response.output, tokens_dict)

        print(f"\n[Design Agent] {response.output}")

        # Check if project was found
        data_manager.data = data_manager.load_data()

        if (data_manager.data.has_project_id() and
                data_manager.data.project_id == project_id and
                data_manager.data.is_complete()):
            # Project found - return success
            session_state.clear()
            return {
                "action": "project_found",
                "project_data": {
                    "project_id": data_manager.data.project_id,
                    "project_name": data_manager.data.project_name,
                    "project_address": data_manager.data.project_address,
                    "client_email": data_manager.data.client_email
                },
                "message": f"Project '{data_manager.data.project_name}' found and ready for design phase."
            }
        else:
            # Project not found - ask for creation
            print("\n[Design Agent] Project not found. Would you like to create a new project? (yes/no)")
            create_response = input("You: ").strip().lower()

            # Track user response
            chat_history.add_message("user", create_response)

            if create_response in ['yes', 'y', 'sure', 'ok', 'okay', 'create']:
                session_state.set_context("transfer_to_creation", True)
                return {
                    "action": "transfer_to_project_creation",
                    "message": "Project not found, user wants to create new project."
                }
            else:
                session_state.clear()
                return {
                    "action": "design_session_completed",
                    "message": "Design session completed without finding project."
                }

    except Exception as e:
        print(f"❌ Error in design agent loop: {e}")
        session_state.clear()
        return {
            "action": "error",
            "message": f"Error in design agent: {e}"
        }


async def project_agent_loop(data_manager: ProjectDataManager, initial_message: str = None,
                             session_state: SessionState = None, chat_history: ChatHistory = None) -> Dict[str, Any]:
    print("\n[Orchestrator] -> [Project Agent] Transferring you to project creation specialist...")
    if session_state:
        session_state.set_agent("project_agent")

    # Initialize usage tracking
    usage = Usage()
    limits = UsageLimits(request_limit=100)

    try:
        # Clear any existing data for fresh start
        data_manager.data = ProjectDetails()
        data_manager.save_data()
        print("🗑️ Cleared existing data for fresh project creation")

        # Initial greeting or handle initial message
        if initial_message and not initial_message.startswith("Hello"):
            response = await project_agent.run(
                initial_message,
                deps=data_manager,
                usage=usage,
                usage_limits=limits
            )
        else:
            response = await project_agent.run(
                "Hello! I'll help you create a new project. What project information would you like to provide?",
                deps=data_manager,
                usage=usage,
                usage_limits=limits
            )

        # Track agent response and tokens
        tokens_dict = {
            "requests": response.usage().requests,
            "request_tokens": response.usage().request_tokens,
            "response_tokens": response.usage().response_tokens,
            "total_tokens": response.usage().total_tokens
        } if chat_history else None

        if chat_history:
            chat_history.add_message("project_agent", response.output, tokens_dict)

        print(f"\n[Project Agent] {response.output}")

        # Continue conversation until project is complete
        while True:
            # Check current status
            current_data_status = data_manager.get_status()

            if current_data_status["is_complete"] and data_manager.data.has_project_id():
                print("\n🎉 Project information collection complete!")
                break

            # Get user input
            user_input = input("\nYou: ").strip()

            # Track user input
            if chat_history:
                chat_history.add_message("user", user_input)

            if user_input.lower() in ["thank you", "thanks", "done", "finished", "complete"]:
                # Check if we have all required information
                current_data_status = data_manager.get_status()
                if current_data_status["is_complete"]:
                    # Generate project ID if missing
                    if not data_manager.data.has_project_id():
                        print("🎲 All information complete! Generating project ID...")
                        id_result = await project_agent.run(
                            "Generate project ID - all required info is complete",
                            deps=data_manager,
                            usage=usage,
                            usage_limits=limits
                        )

                        # Track ID generation response
                        if chat_history:
                            tokens_dict = {
                                "requests": id_result.usage().requests,
                                "request_tokens": id_result.usage().request_tokens,
                                "response_tokens": id_result.usage().response_tokens,
                                "total_tokens": id_result.usage().total_tokens
                            }
                            chat_history.add_message("project_agent", id_result.output, tokens_dict)

                        print(f"[Project Agent] {id_result.output}")
                        data_manager.data = data_manager.load_data()  # Reload after ID generation
                    break
                else:
                    missing = current_data_status["missing_fields"]
                    print(f"⚠️ Still missing: {', '.join(missing)}. Please provide the missing information.")
                    continue

            if not user_input:
                continue

            # Let project_agent handle the user input naturally
            response = await project_agent.run(
                user_input,
                deps=data_manager,
                usage=usage,
                usage_limits=limits
            )

            # Track agent response and tokens
            if chat_history:
                tokens_dict = {
                    "requests": response.usage().requests,
                    "request_tokens": response.usage().request_tokens,
                    "response_tokens": response.usage().response_tokens,
                    "total_tokens": response.usage().total_tokens
                }
                chat_history.add_message("project_agent", response.output, tokens_dict)

            print(f"[Project Agent] {response.output}")

            # Check if project became complete after this interaction
            current_data_status = data_manager.get_status()
            if current_data_status["is_complete"] and not data_manager.data.has_project_id():
                print("\n🎲 All information complete! Auto-generating project ID...")
                id_result = await project_agent.run(
                    "Auto-generate project ID now - all required fields are complete",
                    deps=data_manager,
                    usage=usage,
                    usage_limits=limits
                )

                # Track auto ID generation response
                if chat_history:
                    tokens_dict = {
                        "requests": id_result.usage().requests,
                        "request_tokens": id_result.usage().request_tokens,
                        "response_tokens": id_result.usage().response_tokens,
                        "total_tokens": id_result.usage().total_tokens
                    }
                    chat_history.add_message("project_agent", id_result.output, tokens_dict)

                print(f"[Project Agent] {id_result.output}")
                # Check if ID was successfully generated
                data_manager.data = data_manager.load_data()
                if data_manager.data.has_project_id():
                    print(f"✅ Project ID {data_manager.data.project_id} generated successfully!")
                    break

        # Reload data to get the final state
        data_manager.data = data_manager.load_data()

        if session_state:
            session_state.clear()

        if data_manager.data.is_complete() and data_manager.data.has_project_id():
            return {
                "action": "project_created",
                "project_data": {
                    "project_id": data_manager.data.project_id,
                    "project_name": data_manager.data.project_name,
                    "project_address": data_manager.data.project_address,
                    "client_email": data_manager.data.client_email
                },
                "message": f"Successfully created project '{data_manager.data.project_name}' with ID {data_manager.data.project_id}"
            }
        else:
            return {
                "action": "project_creation_incomplete",
                "message": "Project creation was not completed successfully."
            }

    except Exception as e:
        print(f"❌ Error in project agent loop: {e}")
        if session_state:
            session_state.clear()
        return {
            "action": "error",
            "message": f"Error in project agent: {e}"
        }


# Tools available to the orchestrator agent
@orchestrator_agent.tool
async def handle_project_creation(ctx: RunContext, user_message: str) -> Dict[str, Any]:
    """Handle project creation requests by calling the project agent loop"""
    return {"message": "Project creation tool called", "action": "route_to_project_agent"}


@orchestrator_agent.tool
async def handle_design_lookup(ctx: RunContext, user_message: str) -> Dict[str, Any]:
    """Handle design/lookup requests by calling the design agent loop"""
    return {"message": "Design lookup tool called", "action": "route_to_design_agent"}


# Helper: Intent classification with context awareness
def classify_intent(msg: str, session_state: SessionState) -> str:
    msg_l = msg.lower().strip()

    # Handle save command
    if msg_l == 'save':
        return "save_history"

    # Handle simple responses that don't need agent routing
    if msg_l in ['no', 'yes', 'thanks', 'thank you', 'bye', 'goodbye', 'ok', 'okay']:
        return "simple_response"

    # Check for project creation keywords
    if any(k in msg_l for k in (
            "create project", "new project", "start project",
            "build project", "initialize project", "setup project",
            "i need to create", "help me create", "create a", "make a project"
    )):
        return "project_creation"

    # Check for design/lookup keywords or 8-digit numbers (project IDs)
    if (any(k in msg_l for k in (
            "design", "summary", "generate design",
            "project summary", "design proposal", "show design",
            "lookup project", "find project", "check project", "project id"
    )) or re.search(r'\b\d{8}\b', msg)):
        return "design_lookup"

    return "general"


# Public function to handle a single user message
async def handle_user_message(message: str, data_manager: ProjectDataManager, session_state: SessionState,
                              chat_history: ChatHistory) -> None:
    intent = classify_intent(message, session_state)

    # Track user message
    chat_history.add_message("user", message)

    # Handle save command
    if intent == "save_history":
        success = chat_history.save_history()
        if success:
            print("\n[Orchestrator] 💾 Chat history saved successfully! You can continue the conversation.")
        else:
            print("\n[Orchestrator] ❌ Failed to save chat history. Please try again.")
        return

    # Check if we need to handle transfer from design agent to project agent
    if session_state.get_context("transfer_to_creation"):
        session_state.clear()
        print("\n[Orchestrator] Transferring from design lookup to project creation...")
        result = await project_agent_loop(data_manager, "Hello! Let's create a new project.", session_state,
                                          chat_history)
        orchestrator_response = f"Project creation completed: {result['message']}"
        chat_history.add_message("orchestrator", orchestrator_response)
        print(f"\n[Orchestrator] {orchestrator_response}")
        return

    if intent == "simple_response":
        # Handle simple responses without routing to agents
        if message.lower().strip() in ['no', 'thanks', 'thank you']:
            response = "You're welcome! Is there anything else I can help you with?"
        elif message.lower().strip() in ['yes', 'ok', 'okay']:
            response = "Great! What would you like to do? You can create a project or lookup an existing one."
        elif message.lower().strip() in ['bye', 'goodbye']:
            response = "Goodbye! Thank you for using our project management system."
        else:
            response = "I understand. Is there anything else I can help you with?"

        chat_history.add_message("orchestrator", response)
        print(f"\n[Orchestrator] {response}")
        return

    elif intent == "project_creation":
        orchestrator_response = "Understood: project creation requested."
        chat_history.add_message("orchestrator", orchestrator_response)
        print(f"\n[Orchestrator] {orchestrator_response}")

        result = await project_agent_loop(data_manager, message, session_state, chat_history)

        final_response = f"Project creation completed: {result['message']}"
        chat_history.add_message("orchestrator", final_response)
        print(f"\n[Orchestrator] {final_response}")

    elif intent == "design_lookup":
        orchestrator_response = "Understood: design/lookup requested."
        chat_history.add_message("orchestrator", orchestrator_response)
        print(f"\n[Orchestrator] {orchestrator_response}")

        result = await design_agent_loop(data_manager, message, session_state, chat_history)
        if result['action'] == "transfer_to_project_creation":
            # Handle transfer to project creation
            result2 = await project_agent_loop(data_manager, "Hello! Let's create a new project.", session_state,
                                               chat_history)
            final_response = f"Project creation completed: {result2['message']}"
        else:
            final_response = f"Design/lookup completed: {result['message']}"

        chat_history.add_message("orchestrator", final_response)
        print(f"\n[Orchestrator] {final_response}")

    else:
        response = ("I'm here to help you with project management. You can:\n"
                    "• Create a new project by saying 'create project'\n"
                    "• Look up an existing project by providing an 8-digit project ID\n"
                    "• Ask for help or clarification about our services\n"
                    "• Type 'save' to save the conversation history")

        chat_history.add_message("orchestrator", response)
        print(f"\n[Orchestrator] {response}")


# Main function
async def main():
    print("🚀 Project Management Orchestration System")
    print("=" * 70)

    # Initialize data manager, session state, and chat history
    data_manager = ProjectDataManager("project_data.json")
    session_state = SessionState()
    chat_history = ChatHistory("chat_history.json")

    print("🤖 Orchestrator Agent Ready!")
    print("━" * 60)
    print("Available commands:")
    print("• Say anything with 'create project' or 'new project' to create a project")
    print("• Say anything with 'design' or provide an 8-digit project ID to lookup/design")
    print("• Type 'save' to save the chat history and token usage")
    print("• Type 'quit' to exit")
    print("━" * 60)

    while True:
        user_input = input("\nYou: ").strip()

        if user_input.lower() in {'quit', 'exit'}:
            # Auto-save on exit
            print("\n[Orchestrator] Saving chat history before exit...")
            chat_history.save_history()
            print("\n[Orchestrator] Goodbye! Thank you for using our project management system.")
            break

        if not user_input:
            continue

        try:
            await handle_user_message(user_input, data_manager, session_state, chat_history)
        except Exception as e:
            error_message = f"⚠️ Error: {e}"
            chat_history.add_message("system", error_message)
            print(f"[Orchestrator] {error_message}")
            print("💡 Troubleshooting tips:")
            print("   1. Make sure your API key is correctly set")
            print("   2. Check your internet connection")
            print("   3. Try a different model if available")


if __name__ == "__main__":
    asyncio.run(main())