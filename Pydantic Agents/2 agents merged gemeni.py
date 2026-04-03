import json
import os
import asyncio
import random
from typing import Optional, Dict, Any, Union
from pydantic import BaseModel, Field, EmailStr
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.usage import Usage, UsageLimits

# ============================================================================
# API KEY CONFIGURATION
# ============================================================================
# METHOD 1: Set your API key directly here (LESS SECURE - for testing only)
GOOGLE_AI_API_KEY = "AIzaSyD0wYQv_DLhPi079X1JW1WEhMSktWMVhJ8"  # Replace with your actual API key

# METHOD 2: Use environment variable (MORE SECURE - recommended)
# Set environment variable: export GOOGLE_API_KEY="your_key_here"
# Then uncomment the line below and comment out the line above:
# GOOGLE_AI_API_KEY = os.getenv("GOOGLE_API_KEY")

# Simple validation - just check if key exists and starts with AIza
if not GOOGLE_AI_API_KEY or not GOOGLE_AI_API_KEY.startswith("AIza"):
    print("❌ ERROR: Please set a valid Google AI API key!")
    print("🔑 How to get your API key:")
    print("   1. Go to https://ai.google.dev/")
    print("   2. Sign in with Google account")
    print("   3. Click 'Get API key' → 'Create API key'")
    print("   4. Copy the key and paste it in this script")
    print("\n💡 Your API key should start with 'AIza'")
    exit(1)

print(f"✅ API key loaded: {GOOGLE_AI_API_KEY[:10]}...")  # Show first 10 chars for verification

# Set the correct environment variable name for pydantic-ai
os.environ['GOOGLE_API_KEY'] = GOOGLE_AI_API_KEY


# ============================================================================
# SHARED DATA MODELS
# ============================================================================

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


# ============================================================================
# GEMINI MODEL SETUP
# ============================================================================

# Initialize Gemini model with GoogleProvider
try:
    from pydantic_ai.providers.google import GoogleProvider

    # Create provider with API key
    google_provider = GoogleProvider(api_key=GOOGLE_AI_API_KEY)

    # Initialize GoogleModel with provider
    gemini_model = GoogleModel('gemini-2.0-flash-exp', provider=google_provider)
    print("✅ Gemini 2.0 Flash Experimental initialized successfully!")

except Exception as e:
    print(f"❌ Error with Gemini 2.0 Flash Experimental: {e}")

    # Try stable Gemini 1.5 Pro
    try:
        print("🔄 Trying Gemini 1.5 Pro...")
        google_provider = GoogleProvider(api_key=GOOGLE_AI_API_KEY)
        gemini_model = GoogleModel('gemini-1.5-pro', provider=google_provider)
        print("✅ Gemini 1.5 Pro initialized successfully!")

    except Exception as e2:
        print(f"❌ Error with Gemini 1.5 Pro: {e2}")

        # Try without specific provider (using environment variable)
        try:
            print("🔄 Trying with environment variable approach...")
            gemini_model = GoogleModel('gemini-1.5-flash')
            print("✅ Gemini 1.5 Flash initialized successfully!")

        except Exception as e3:
            print(f"❌ All initialization methods failed: {e3}")
            print("💡 Make sure you have the correct dependencies:")
            print("   pip install 'pydantic-ai[google]'")
            exit(1)

# ============================================================================
# DESIGN AGENT
# ============================================================================

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
- Return "NOT_FOUND" so the system can proceed with project creation

## CRITICAL RULES:
- NEVER make up project data - only show what's actually in the JSON file
- ALWAYS verify project IDs with the check_project_id tool
- Be clear and professional in your responses
- When project is not found, return "NOT_FOUND" for orchestration

Remember: Your primary job is to validate project access."""
)


@design_agent.tool
async def check_project_id(ctx: RunContext[ProjectDataManager], project_id: int) -> Dict[str, Any]:
    """Check if the provided project ID exists in the JSON file"""
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


# ============================================================================
# PROJECT AGENT
# ============================================================================

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

## MESSAGE HANDLING LOGIC (For EVERY User Message)

### STEP 1: CHECK EXISTING PROJECT STATE
- ALWAYS begin by calling `check_project_data`
- Use this tool to check which fields are already saved:
  - project_name
  - project_address
  - client_email
  - project_id

---

### STEP 2: EXTRACT FIELDS FROM USER MESSAGE

Parse the user's message using the following rules:

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

---

### STEP 3: SAVE ANY VALID FIELD IMMEDIATELY

If a valid value is found in the user's message:
- Call `save_project_info`
- Pass only the field and value, for example:
  {
    "field": "project_name",
    "value": "GreenTech Rooftop"
  }

- Save fields one at a time
- Do not continue the conversation until the save call is made
- Wait for save confirmation before asking the next question

---

### STEP 4: VERIFY COMPLETION AND GENERATE PROJECT ID

After saving a new field:
- Call `check_project_data` again

If all of these are present:
- project_name
- project_address
- client_email

But `project_id` is still missing or null:
- Immediately call `generate_project_id`
- Do not make up or insert any ID manually
- Let the tool generate and save it

---

### STEP 5: VERIFY POST-GENERATION STATE

After calling `generate_project_id`:
- Call `check_project_data` one more time
- Confirm the project_id is present and saved

---

### STEP 6: CONFIRMATION AND RESPONSE RULES

When a field is saved:
- Confirm it clearly:
  - "Saved project name: 'GreenTech Rooftop'"

When a project ID is generated:
- Confirm it like:
  - "Generated and saved Project ID: 12345678"

If more fields are needed:
- Ask for only one missing piece of information
  - Example: "What is the project address?" or
  - "Could you share the client's email?"

When all fields are complete:
- Present the final summary in this format:

Project setup complete:
- Project Name: [project_name]
- Project Address: [project_address]
- Client Email: [client_email]
- Project ID: [project_id]

---

## RULES (STRICTLY ENFORCED)

1. Do not make up project IDs — always use `generate_project_id`
2. Do not guess values — extract only confirmed, clean inputs
3. Always use `check_project_data` before responding
4. Always save each value using `save_project_info` immediately
5. Always call `generate_project_id` after the 3 main fields are filled
6. Never display the final summary unless all fields are confirmed saved via `check_project_data`
7. Never hallucinate tool calls — only call when conditions are satisfied
8. Always re-check project state after any save or generation step

---

## EXAMPLES

User: "This is for SolarCorp Villa"  
→ Extract "SolarCorp Villa", save as project_name

User: "located at 123 Elm Street, Austin"  
→ Extract and save as project_address

User: "client email is jon@solarhub.com"  
→ Extract and save as client_email, then generate project ID

User: "Yes"  
→ Only take action if the previous step asked a yes/no question

User: "What's my project ID?"  
→ Check `check_project_data`, return only if ID exists

---

Maintain a friendly, clear, and structured tone.
Always follow logic strictly and call tools at the appropriate time.
Do not skip, guess, or fabricate any step in the process.
""")


@project_agent.tool
async def check_project_data(ctx: RunContext[ProjectDataManager]) -> Dict[str, Any]:
    """Check current project data status"""
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
    """Save project information to the JSON file"""
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
    """Generate a unique project ID when all basic information is complete"""
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


# ============================================================================
# ORCHESTRATION
# ============================================================================

async def process_project(json_path: str = "project_data.json") -> Union[ProjectSummary, ProjectCreated]:
    """Main orchestration function to handle project lookup and creation"""

    # Initialize data manager
    data_manager = ProjectDataManager(json_path)

    # Initialize usage tracking with higher limits
    usage = Usage()
    limits = UsageLimits(request_limit=100)

    # Prompt for project ID
    print("🔍 Project Lookup & Creation System")
    print("=" * 50)

    try:
        project_id_input = input("Enter the project ID to lookup (8-digit number): ").strip()
        project_id = int(project_id_input)

        if not (10000000 <= project_id <= 99999999):
            print("❌ Project ID must be an 8-digit number")
            return None

    except ValueError:
        print("❌ Invalid project ID format. Please enter a number.")
        return None

    print(f"\n🔍 Step 1: Looking up project ID {project_id}...")

    # 1. Try lookup via design_agent
    try:
        design_result = await design_agent.run(
            f"Check project ID {project_id}",
            deps=data_manager,
            usage=usage,
            usage_limits=limits
        )

        print(f"Design Agent Response: {design_result.output}")

        # Check if project was found by looking at the actual data
        data_manager.data = data_manager.load_data()  # Reload latest data

        if (data_manager.data.has_project_id() and
                data_manager.data.project_id == project_id and
                data_manager.data.is_complete()):
            # Project found and complete - return summary
            summary = ProjectSummary(
                project_id=data_manager.data.project_id,
                project_name=data_manager.data.project_name,
                project_address=data_manager.data.project_address,
                client_email=data_manager.data.client_email,
                summary=f"Project '{data_manager.data.project_name}' found at {data_manager.data.project_address}"
            )

            print(f"\n✅ Found existing project!")
            return summary

    except Exception as e:
        print(f"❌ Error during lookup: {e}")

    # 2. Project not found - proceed with creation
    print(f"\n📝 Step 2: Project ID {project_id} not found. Creating new project...")
    print("I'll help you create a new project through conversation.")
    print("-" * 50)

    try:
        # Clear any existing data for fresh start
        data_manager.data = ProjectDetails()
        data_manager.save_data()
        print("🗑️ Cleared existing data for fresh project creation")

        # Start conversational collection with project_agent
        creation_result = await project_agent.run(
            "Hello! What project information would you like to provide?",
            deps=data_manager,
            usage=usage,
            usage_limits=limits
        )
        print(f"Project Agent: {creation_result.output}")

        # Continue conversation until project is complete
        while True:
            # Check current status
            current_data_status = data_manager.get_status()

            if current_data_status["is_complete"] and data_manager.data.has_project_id():
                print("\n🎉 Project information collection complete!")
                break

            # Get user input
            user_input = input("\nYou: ").strip()

            if user_input.lower() in ['done', 'finished', 'complete']:
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
                        print(f"Project Agent: {id_result.output}")
                        data_manager.data = data_manager.load_data()  # Reload after ID generation
                    break
                else:
                    missing = current_data_status["missing_fields"]
                    print(f"⚠️ Still missing: {', '.join(missing)}. Please provide the missing information.")
                    continue

            if not user_input:
                continue

            # Let project_agent handle the user input naturally
            creation_result = await project_agent.run(
                user_input,
                deps=data_manager,
                usage=usage,
                usage_limits=limits
            )
            print(f"Project Agent: {creation_result.output}")

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
                print(f"Project Agent: {id_result.output}")
                # Check if ID was successfully generated
                data_manager.data = data_manager.load_data()
                if data_manager.data.has_project_id():
                    print(f"✅ Project ID {data_manager.data.project_id} generated successfully!")
                    break

        # Reload data to get the final state
        data_manager.data = data_manager.load_data()

        if data_manager.data.is_complete() and data_manager.data.has_project_id():
            created = ProjectCreated(
                project_id=data_manager.data.project_id,
                project_name=data_manager.data.project_name,
                project_address=data_manager.data.project_address,
                client_email=data_manager.data.client_email,
                message=f"Successfully created project '{data_manager.data.project_name}' with ID {data_manager.data.project_id}"
            )

            print(f"\n🎉 Project creation successful!")
            return created
        else:
            print("❌ Project creation incomplete")
            return None

    except Exception as e:
        print(f"❌ Error during project creation: {e}")
        return None


# ============================================================================
# MAIN FUNCTION
# ============================================================================

async def main():
    """Main entry point for the application"""

    print("🚀 Project Management Orchestration System")
    print("🤖 Powered by Google Gemini 2.5 Pro")
    print("This system will first try to lookup a project, then create one if not found.")
    print("=" * 70)

    try:
        outcome = await process_project("project_data.json")

        if outcome is None:
            print("\n❌ Process failed or was cancelled")
            return

        print("\n" + "=" * 50)
        print("📊 FINAL RESULT:")
        print("=" * 50)

        if isinstance(outcome, ProjectSummary):
            print("✅ WORKFLOW COMPLETE: PROJECT FOUND")
            print(f"🆔 Project ID: {outcome.project_id}")
            print(f"📝 Project Name: {outcome.project_name}")
            print(f"📍 Address: {outcome.project_address}")
            print(f"📧 Email: {outcome.client_email}")
            print(f"📋 Summary: {outcome.summary}")

        elif isinstance(outcome, ProjectCreated):
            print("✅ WORKFLOW COMPLETE: PROJECT CREATED")
            print(f"🆔 Project ID: {outcome.project_id}")
            print(f"📝 Project Name: {outcome.project_name}")
            print(f"📍 Address: {outcome.project_address}")
            print(f"📧 Email: {outcome.client_email}")
            print(f"🎉 Message: {outcome.message}")
            print(f"\n💡 Save this Project ID ({outcome.project_id}) for future reference!")

        print("\n✨ System ready for next operation.")

    except Exception as e:
        print(f"❌ System error: {e}")
        print("💡 Troubleshooting tips:")
        print("   1. Check your internet connection")
        print("   2. Verify your Google AI API key is correct")
        print("   3. Make sure you have pydantic-ai installed: pip install pydantic-ai[google]")


# ============================================================================
# INSTALLATION REQUIREMENTS
# ============================================================================

if __name__ == "__main__":
    print("📋 Required Dependencies:")
    print("   pip install pydantic-ai[google]")
    print("   pip install pydantic")
    print("   pip install asyncio")
    print()

    # Check if required packages are installed
    try:
        import pydantic_ai

        print("✅ pydantic-ai is installed")
    except ImportError:
        print("❌ pydantic-ai not found. Install with: pip install pydantic-ai[google]")
        exit(1)

    asyncio.run(main())