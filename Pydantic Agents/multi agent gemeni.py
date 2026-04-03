import json
import os
import asyncio
import random
import re
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, EmailStr
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.usage import Usage, UsageLimits
from secrets import GEMINI_API_KEY
from pydantic_ai.providers.google_gla import GoogleGLAProvider


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

        return {
            "session_start": self.session_start,
            "total_messages": len(self.messages),
            "token_usage": self.total_tokens,
            "messages_by_sender": {
                sender: len([msg for msg in self.messages if msg.sender == sender])
                for sender in ["user", "design_agent", "project_agent", "orchestrator"]
            }
        }


# Global chat history instance - accessible throughout the application
chat_history = None


# Data Models
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
                    return ProjectDetails(**data_dict)
            except Exception as e:
                print(f"❌ Error loading data: {e}")
                return ProjectDetails()
        return ProjectDetails()

    def save_data(self) -> None:
        try:
            data_dict = self.data.model_dump()
            with open(self.filename, 'w') as f:
                json.dump(data_dict, f, indent=2)
            print(f"💾 Data saved: {data_dict}")
        except Exception as e:
            print(f"❌ Error saving data: {e}")

    def update_field(self, field_name: str, value: Any) -> bool:
        if hasattr(self.data, field_name):
            setattr(self.data, field_name, value)
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


# Setup gemini model
gemini_model = GeminiModel(
    model_name='gemini-2.5-pro',
    provider=GoogleGLAProvider(api_key=GEMINI_API_KEY)
)

# DESIGN AGENT - handles project lookup and verification
design_agent = Agent(
    model=gemini_model,
    deps_type=ProjectDataManager,
    output_type=str,
    system_prompt="""You are a Design Agent that looks up existing projects by their 8-digit project ID.

## YOUR SIMPLE WORKFLOW:

1. **Extract Project ID**: Find the 8-digit number in the user's message
2. **Use Tool**: Call `check_project_id` tool with that number  
3. **Show Results**:
   - If found: Show complete project details
   - If not found: Tell user project doesn't exist

## RESPONSE FORMATS:

**If Project Found:**
```
✅ PROJECT FOUND!

📋 Project Summary:
🆔 Project ID: [ID]
📝 Project Name: [NAME] 
📍 Address: [ADDRESS]
📧 Client Email: [EMAIL]

You can now proceed with the design phase.
```

**If Project Not Found:**
```
❌ PROJECT NOT FOUND

The project ID [ID] does not exist in our system.
```

## CRITICAL RULES:
- ALWAYS use the check_project_id tool - never guess results
- Only show real data from the tool response
- Be clear and professional
- If no 8-digit number found, ask user for project ID"""
)


@design_agent.tool
async def check_project_id(ctx: RunContext[ProjectDataManager], project_id: int) -> Dict[str, Any]:
    ctx.deps.data = ctx.deps.load_data()

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


# PROJECT AGENT - handles project creation
project_agent = Agent(
    model=gemini_model,
    deps_type=ProjectDataManager,
    output_type=str,
    system_prompt="""You are a Project Creation Agent. Collect exactly 3 pieces of information in strict order.

## CRITICAL WORKFLOW - FOLLOW EXACTLY:

### STEP 1: ALWAYS CHECK STATUS FIRST
- Call `check_project_data` tool to see what's already saved
- Never ask for information that's already complete

### STEP 2: COLLECT IN ORDER (ONE AT A TIME)
1. **Project Name** (if missing) → Ask: "What is the project name?"
2. **Project Address** (if missing) → Ask: "What is the project address?"  
3. **Client Email** (if missing) → Ask: "What is the client email?"
4. **Generate ID** (if all complete) → Call `generate_project_id` tool

### STEP 3: EXTRACT AND SAVE IMMEDIATELY
When user provides info, extract and save using `save_project_info` tool:
- "project name is test1" → save_project_info("project_name", "test1")
- "address is 123 Main St" → save_project_info("project_address", "123 Main St")  
- "email is user@test.com" → save_project_info("client_email", "user@test.com")

### STEP 4: VALIDATION AND RETRY
- If email invalid → Ask again: "Please provide a valid email address (like user@domain.com)"
- If any field fails to save → Ask user to try again
- Always use ACTUAL tool results, never make up responses

### STEP 5: FINAL SUMMARY (ONLY WHEN COMPLETE)
When project ID is generated, show REAL data from the system:
```
✅ PROJECT CREATED SUCCESSFULLY!
📝 Project Name: [ACTUAL SAVED NAME]
📍 Address: [ACTUAL SAVED ADDRESS]  
📧 Email: [ACTUAL SAVED EMAIL]
🆔 Project ID: [ACTUAL GENERATED ID]
```

## CRITICAL RULES:
- ALWAYS use tools - never fake tool responses
- Show ONLY real data from tool results
- Ask for ONE missing field at a time
- Validate email format before saving
- Never hallucinate or make up data"""
)


@project_agent.tool
async def check_project_data(ctx: RunContext[ProjectDataManager]) -> Dict[str, Any]:
    ctx.deps.data = ctx.deps.load_data()
    return ctx.deps.get_status()


@project_agent.tool
async def save_project_info(ctx: RunContext[ProjectDataManager], field_name: str, value: str) -> str:
    valid_fields = ["project_name", "project_address", "client_email"]

    if field_name not in valid_fields:
        return f"Invalid field name. Must be one of: {valid_fields}"

    # Clean up the value - remove only obvious prefixes
    cleaned_value = value.strip()

    # Remove common prefixes but be careful not to remove actual content
    if field_name == "project_name":
        prefixes = ["project name is ", "the project name is ", "project is called "]
        for prefix in prefixes:
            if cleaned_value.lower().startswith(prefix.lower()):
                cleaned_value = cleaned_value[len(prefix):].strip()
                break

    elif field_name == "project_address":
        prefixes = ["address is ", "the address is ", "located at ", "site at "]
        for prefix in prefixes:
            if cleaned_value.lower().startswith(prefix.lower()):
                cleaned_value = cleaned_value[len(prefix):].strip()
                break

    elif field_name == "client_email":
        prefixes = ["email is ", "the email is ", "client email is "]
        for prefix in prefixes:
            if cleaned_value.lower().startswith(prefix.lower()):
                cleaned_value = cleaned_value[len(prefix):].strip()
                break

    # Validate email format if it's an email field
    if field_name == "client_email":
        if "@" not in cleaned_value or "." not in cleaned_value.split("@")[-1]:
            return f"Invalid email format '{cleaned_value}'. Please provide a valid email like: user@domain.com"

        # Additional validation with Pydantic
        try:
            temp_data = {"client_email": cleaned_value}
            ProjectDetails(**temp_data)
        except Exception:
            return f"Invalid email format '{cleaned_value}'. Please provide a valid email like: user@domain.com"

    # Check if field already has this exact value
    current_value = getattr(ctx.deps.data, field_name)
    if current_value is not None and current_value.strip().lower() == cleaned_value.strip().lower():
        return f"Field {field_name} is already saved as '{current_value}'"

    # Save the cleaned value
    success = ctx.deps.update_field(field_name, cleaned_value)
    if success:
        return f"Successfully saved {field_name}: '{cleaned_value}'"
    else:
        return f"Failed to save {field_name}"


@project_agent.tool
async def generate_project_id(ctx: RunContext[ProjectDataManager]) -> str:
    # Reload data to ensure current state
    ctx.deps.data = ctx.deps.load_data()

    # Check if all required fields are present
    if not ctx.deps.data.is_complete():
        missing = ctx.deps.data.get_missing_fields()
        return f"Cannot generate project ID. Missing fields: {', '.join(missing)}"

    # Check if project already has an ID
    if ctx.deps.data.has_project_id():
        return f"Project already has ID: {ctx.deps.data.project_id}"

    # Generate a random 8-digit project ID
    project_id = random.randint(10000000, 99999999)

    # Save the project ID
    success = ctx.deps.update_field("project_id", project_id)

    if success:
        return f"Project ID {project_id} generated successfully! Project creation complete."
    else:
        return "Failed to save project ID. Please try again."


# Helper function to extract tokens and log to chat history
async def run_agent_with_logging(agent, message, deps, sender_name):

    global chat_history

    try:
        result = await agent.run(message, deps=deps)

        # Extract token usage
        token_data = {
            "requests": result.usage().requests,
            "request_tokens": result.usage().request_tokens,
            "response_tokens": result.usage().response_tokens,
            "total_tokens": result.usage().total_tokens
        }

        # Add to chat history
        if chat_history:
            chat_history.add_message(sender_name, result.output, token_data)

        return result

    except Exception as e:
        error_msg = f"Error in {sender_name}: {e}"
        if chat_history:
            chat_history.add_message("system", error_msg)
        raise e


# ORCHESTRATOR AGENT - The main controller
orchestrator_agent = Agent(
    model=gemini_model,
    deps_type=ProjectDataManager,
    output_type=str,
    system_prompt="""You are the Project Management Orchestrator. You coordinate all project activities.

## YOUR ROLE:
Analyze user requests and decide the best action:

1. **DIRECT RESPONSES** - Handle these yourself (DO NOT USE TOOLS):
   - "SYSTEM_START": Welcome user warmly and explain your capabilities
   - "SYSTEM_END": Say goodbye professionally  
   - Greetings: "hello", "hi", "hey", "good morning"
   - Questions: "what can you do?", "how does this work?", "help"
   - Simple responses: "thanks", "okay", "yes", "no"
   - General conversation that doesn't require project work

2. **PROJECT CREATION** - Use create_project tool ONLY when users clearly want to:
   - "create project", "new project", "start project"  
   - "build project", "make a project", "setup project"
   - "I want to create", "help me create"

3. **DESIGN CREATION** - Use create_design tool ONLY when users:
   - Provide 8-digit numbers (project IDs) like "12345678"
   - Say "design", "lookup", "create design"
   - Want to see existing project details

## CRITICAL RULES:
- Respond directly to conversational messages - DO NOT use tools for chat
- Only use tools for actual project work (creation or lookup)
- Be helpful and encouraging

Remember: Only use tools for actual project work!"""
)


@orchestrator_agent.tool
async def create_project(ctx: RunContext[ProjectDataManager], user_message: str) -> str:

    global chat_history

    print("\n[Orchestrator → Project Agent] Starting project creation...")

    # Log the transition
    if chat_history:
        chat_history.add_message("system", "[Orchestrator → Project Agent] Starting project creation...")

    # Clear existing data for fresh start
    ctx.deps.data = ProjectDetails()
    ctx.deps.save_data()

    # Start project creation conversation
    response = await run_agent_with_logging(
        project_agent,
        "Start collecting project information. Check current status and ask for the first missing field.",
        ctx.deps,
        "project_agent"
    )
    print(f"[Project Agent] {response.output}")

    # Interactive loop for project creation with full logging
    while True:
        # Check current status
        ctx.deps.data = ctx.deps.load_data()  # Reload to get latest data
        status = ctx.deps.get_status()

        # If project is complete with ID, show REAL final summary
        if status["is_complete"] and ctx.deps.data.has_project_id():
            final_summary = f"""✅ PROJECT CREATED SUCCESSFULLY!

📝 Project Name: {ctx.deps.data.project_name}
📍 Address: {ctx.deps.data.project_address}
📧 Email: {ctx.deps.data.client_email}
🆔 Project ID: {ctx.deps.data.project_id}

Your project is now ready! Save the Project ID for future reference."""

            print(f"\n{final_summary}")

            # Log the final summary
            if chat_history:
                chat_history.add_message("project_agent", final_summary)

            return final_summary

        # Get user input with retry for empty input
        user_input = None
        while not user_input:
            user_input = input("\nYou: ").strip()
            if not user_input:
                print("Please provide some input to continue.")
                continue
            break

        # Log user input
        if chat_history:
            chat_history.add_message("user", user_input)

        try:
            # Process user input with project agent and log it
            response = await run_agent_with_logging(
                project_agent,
                user_input,
                ctx.deps,
                "project_agent"
            )
            print(f"[Project Agent] {response.output}")

            # Special handling for email validation errors
            if "invalid email" in response.output.lower() or "not a valid email" in response.output.lower():
                print("\n💡 Email format should be like: username@domain.com")
                print("Please try again with a valid email address.")
                continue

            # Check if we should auto-generate ID
            ctx.deps.data = ctx.deps.load_data()  # Reload after processing
            status = ctx.deps.get_status()

            if status["is_complete"] and not ctx.deps.data.has_project_id():
                print("\n[Project Agent] All information complete! Generating project ID...")

                # Log the ID generation step
                if chat_history:
                    chat_history.add_message("system",
                                             "[Project Agent] All information complete! Generating project ID...")

                id_response = await run_agent_with_logging(
                    project_agent,
                    "All three fields are now complete. Use the generate_project_id tool to create the project ID.",
                    ctx.deps,
                    "project_agent"
                )
                print(f"[Project Agent] {id_response.output}")

                # Final check - if ID generation was successful, we'll exit on next loop iteration
                ctx.deps.data = ctx.deps.load_data()

        except Exception as e:
            error_msg = f"❌ Error: {e}"
            print(error_msg)
            print("Let's try again. Please provide your input:")

            # Log the error
            if chat_history:
                chat_history.add_message("system", error_msg)
            continue


@orchestrator_agent.tool
async def create_design(ctx: RunContext[ProjectDataManager], user_message: str) -> str:

    global chat_history

    print("\n[Orchestrator → Design Agent] Starting project lookup...")

    # Log the transition
    if chat_history:
        chat_history.add_message("system", "[Orchestrator → Design Agent] Starting project lookup...")

    # Check if project ID is in the message
    project_id_match = re.search(r'\b(\d{8})\b', user_message)
    project_id = None

    # Get project ID with retry logic
    while not project_id:
        if not project_id_match:
            print("[Design Agent] I need an 8-digit project ID to look up your project.")
            print("Example: 12345678")
            project_id_input = input("Please enter your project ID: ").strip()

            # Log user input
            if chat_history:
                chat_history.add_message("user", project_id_input)
        else:
            project_id_input = str(project_id_match.group(1))
            print(f"[Design Agent] Looking up project ID: {project_id_input}")

        # Validate the input
        try:
            test_id = int(project_id_input)
            if 10000000 <= test_id <= 99999999:
                project_id = test_id
                break
            else:
                error_msg = "❌ Project ID must be exactly 8 digits (between 10000000 and 99999999)"
                print(error_msg)
                print("Please try again.")

                # Log validation error
                if chat_history:
                    chat_history.add_message("system", error_msg)

                project_id_match = None  # Reset to ask again
                continue
        except ValueError:
            error_msg = f"❌ '{project_id_input}' is not a valid number."
            print(error_msg)
            print("Please enter exactly 8 digits, like: 12345678")

            # Log validation error
            if chat_history:
                chat_history.add_message("system", error_msg)

            project_id_match = None  # Reset to ask again
            continue

    try:
        # Let design agent handle the lookup with logging
        message_to_check = f"Look up project ID {project_id}"
        response = await run_agent_with_logging(
            design_agent,
            message_to_check,
            ctx.deps,
            "design_agent"
        )
        print(f"[Design Agent] {response.output}")

        # Check if project was found by examining the actual data
        ctx.deps.data = ctx.deps.load_data()
        if not (ctx.deps.data.has_project_id() and ctx.deps.data.project_id == project_id):
            not_found_msg = f"\n[Design Agent] Project ID {project_id} was not found."
            print(not_found_msg)

            # Log the not found message
            if chat_history:
                chat_history.add_message("design_agent", not_found_msg)

            # Ask if user wants to create new project with retry logic
            while True:
                question = "Would you like to create a new project instead?"
                print(question)
                create_response = input("Please enter 'yes' or 'no': ").strip().lower()

                # Log the question and user response
                if chat_history:
                    chat_history.add_message("design_agent", question)
                    chat_history.add_message("user", create_response)

                if create_response in ['yes', 'y']:
                    print("\n[Orchestrator] Starting project creation...")
                    return await create_project(ctx, "Starting new project creation")
                elif create_response in ['no', 'n']:
                    final_msg = "Project lookup completed. No project found and user chose not to create a new project."
                    if chat_history:
                        chat_history.add_message("system", final_msg)
                    return final_msg
                else:
                    error_msg = f"❌ '{create_response}' is not a valid response."
                    print(error_msg)
                    print("Please answer with 'yes' or 'no'.")

                    # Log validation error
                    if chat_history:
                        chat_history.add_message("system", error_msg)
                    continue

        return response.output

    except Exception as e:
        error_msg = f"Error during project lookup: {e}. Please try the lookup again."
        if chat_history:
            chat_history.add_message("system", error_msg)
        return error_msg


# Main System with Complete Chat History Integration
async def main():
    global chat_history

    data_manager = ProjectDataManager("project_data.json")
    chat_history = ChatHistory("chat_history.json")  # Set global instance

    # Orchestrator welcomes user
    try:
        welcome = await run_agent_with_logging(
            orchestrator_agent,
            "SYSTEM_START",
            data_manager,
            "orchestrator"
        )
        print(f"\n🤖 {welcome.output}")

    except Exception as e:
        print(f"Error initializing orchestrator: {e}")
        welcome_msg = "Welcome to our Project Management System! I can help you create new projects or look up existing ones."
        chat_history.add_message("orchestrator", welcome_msg)
        print(f"\n🤖 {welcome_msg}")

    # Main loop - orchestrator handles everything
    while True:
        try:
            user_input = input("\nYou: ").strip()

            # Add user message to history
            chat_history.add_message("user", user_input)

            if user_input.lower() in {'quit', 'exit', 'bye'}:
                try:
                    goodbye = await run_agent_with_logging(
                        orchestrator_agent,
                        "SYSTEM_END",
                        data_manager,
                        "orchestrator"
                    )
                    print(f"\n🤖 {goodbye.output}")

                except Exception as e:
                    goodbye_msg = "Goodbye! Thanks for using our project management system."
                    chat_history.add_message("orchestrator", goodbye_msg)
                    print(f"\n🤖 {goodbye_msg}")

                # Save chat history before exiting
                chat_history.save_history()
                break

            # Handle save command
            if user_input.lower() == 'save':
                if chat_history.save_history():
                    print("✅ Chat history saved successfully!")
                else:
                    print("❌ Failed to save chat history.")
                continue

            if not user_input:
                help_msg = ("💡 Please enter a command. You can:\n"
                            "   • Type 'create project' to start a new project\n"
                            "   • Type 'lookup' and provide an 8-digit project ID\n"
                            "   • Type 'help' for more information\n"
                            "   • Type 'save' to save chat history")
                chat_history.add_message("system", help_msg)
                print(help_msg)
                continue

            # Process with orchestrator and log everything
            try:
                result = await run_agent_with_logging(
                    orchestrator_agent,
                    user_input,
                    data_manager,
                    "orchestrator"
                )
                print(f"\n🤖 {result.output}")

            except Exception as e:
                error_msg = f"An error occurred: {e}"
                chat_history.add_message("system", error_msg)
                print(f"\n❌ {error_msg}")
                print("💡 Don't worry! You can:")
                print("   • Try your request again")
                print("   • Type 'help' for assistance")
                print("   • Type 'quit' to exit")

        except KeyboardInterrupt:
            print("\n\n🤖 Goodbye! Thanks for using our project management system.")
            chat_history.save_history()
            break
        except Exception as e:
            print(f"\n❌ An error occurred: {e}")
            print("💡 Don't worry! You can:")
            print("   • Try your request again")
            print("   • Type 'help' for assistance")
            print("   • Type 'quit' to exit")
            continue


if __name__ == "__main__":
    asyncio.run(main())