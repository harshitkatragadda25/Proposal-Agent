import json
import os
import random
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider


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


# Setup Ollama model - Update model_name to match your available model
ollama_model = OpenAIModel(
    model_name='llama3.1',  # Change this to your available model (check with: ollama list)
    provider=OpenAIProvider(base_url='http://localhost:11434/v1')
)

# Create the agent with enhanced prompt
project_agent = Agent(
    model=ollama_model,
    deps_type=ProjectDataManager,
    output_type=str,
    system_prompt="""You are a helpful project data collection assistant. Your job is to collect exactly three details from the user:

1. Project Name  
2. Project Address  
3. Client Email

Then automatically generate a unique Project ID for future reference.

## WORKFLOW FOR EVERY USER MESSAGE:

### STEP 1: Check Current Data
- ALWAYS start by using the `check_project_data` tool to see what's already saved.

### STEP 2: Analyze User's Message for Data
Carefully scan the user's message for any of the three pieces of information:

**PROJECT NAME patterns to look for:**
- "project name is [NAME]"
- "project is called [NAME]" 
- "working on [NAME] project"
- "the [NAME] project"
- "project [NAME]"
- "[NAME] installation"
- "[NAME] system"

**PROJECT ADDRESS patterns to look for:**
- "address is [ADDRESS]"
- "located at [ADDRESS]"
- "installation at [ADDRESS]"
- "site at [ADDRESS]"
- "in [CITY/LOCATION]"
- Any street addresses, city names, or locations

**CLIENT EMAIL patterns to look for:**
- Any valid email address format: user@domain.com
- Must contain @ symbol and valid domain

### STEP 3: Save Any Detected Information
- If you find ANY of the above information in the user's message, IMMEDIATELY use the `save_project_info` tool to save it.
- Save each piece of information separately with the correct field name:
  - Use "project_name" for project names
  - Use "project_address" for addresses/locations  
  - Use "client_email" for email addresses
- ALWAYS save information before responding to the user.

### STEP 4: Check for Project Completion and Generate ID
- After saving any information, use `check_project_data` again to see the current status.
- **CRITICAL**: If the status shows all three fields are complete (project_name, project_address, client_email) BUT project_id is null/None:
  - IMMEDIATELY call the `generate_project_id` tool
  - Do NOT make up or invent a project ID number
  - Do NOT proceed without calling the generate_project_id tool
  - The tool will create and save the actual project ID

### STEP 5: Verify and Respond
- After any saves or ID generation, use `check_project_data` one more time to verify everything was saved correctly.
- Acknowledge what you saved: "✅ I've saved the project name as '[NAME]'"
- If project ID was generated, confirm it was saved: "✅ Generated and saved project ID: [ACTUAL_ID]"
- If not complete, ask for the next missing piece of information.

### STEP 6: Final Summary
- Only show final project summary after confirming all data (including project_id) is properly saved in the JSON file.
- Use the actual values from `check_project_data`, never make up information.

## CRITICAL RULES:
- NEVER make up or invent project ID numbers - ONLY use the generate_project_id tool
- ALWAYS call generate_project_id when basic info is complete but project_id is missing
- ALWAYS verify data with check_project_data before showing summaries
- NEVER skip calling the actual tools
- Extract actual values, not surrounding words

## TOOL USAGE PATTERN:
When project becomes complete:
1. check_project_data (see if project_id exists)
2. If project_id is null/None: generate_project_id 
3. check_project_data (verify project_id was saved)
4. Show final summary with real data

Remember: You must ACTUALLY call the generate_project_id tool, not just claim you did. Always verify with check_project_data that the ID was saved."""
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

    try:
        # Special validation for email field
        if field_name == "client_email":
            temp_data = {"client_email": value}
            ProjectDetails(**temp_data)  # Validate email format

        success = ctx.deps.update_field(field_name, value)
        if success:
            return f"✅ Successfully saved {field_name}: {value}"
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


def chat_with_agent():

    data_manager = ProjectDataManager()

    print("🤖 Project Data Collection Agent")
    print("=" * 50)
    print("I'll help you collect project information.")
    print(f"📁 Data will be saved to: {os.path.abspath(data_manager.filename)}")
    print("Type 'quit' to exit, 'status' to check current data")
    print("=" * 50)
    print()

    while True:
        # Get user input
        user_input = input("You: ").strip()

        if user_input.lower() in ['quit', 'exit', 'bye']:
            print("👋 Goodbye! Your data has been saved.")
            break

        if user_input.lower() == 'status':
            status = data_manager.get_status()
            print(f"📊 Current Status:")
            print(f"   Completion: {status['completion_percentage']:.0f}%")
            print(f"   Saved: {status['current_data']}")
            print(f"   Missing: {status['missing_fields']}")
            continue

        if not user_input:
            continue

        try:
            # Let the agent handle everything - detection, saving, and conversation
            result = project_agent.run_sync(user_input, deps=data_manager)
            print(f"Agent: {result.output}")

            # Check if complete
            data_manager.data = data_manager.load_data()  # Reload to get latest data
            if data_manager.data.is_complete() and data_manager.data.has_project_id():
                print("\n🎉 PROJECT SUCCESSFULLY CREATED!")
                print("📋 Complete Project Details:")
                print(f"   🆔 Project ID: {data_manager.data.project_id}")
                print(f"   📝 Project Name: {data_manager.data.project_name}")
                print(f"   📍 Address: {data_manager.data.project_address}")
                print(f"   📧 Email: {data_manager.data.client_email}")
                print(f"\n💡 Save this Project ID ({data_manager.data.project_id}) for future reference!")
                print("Type 'quit' to exit or continue chatting.")

        except Exception as e:
            print(f"❌ Error: {e}")
            print("💡 Troubleshooting tips:")
            print("   1. Make sure Ollama is running: ollama serve")
            print("   2. Check available models: ollama list")
            print("   3. Pull the model if needed: ollama pull llama3.1")
            print("   4. Test connection: curl http://localhost:11434/api/tags")

        print()  # Add spacing


if __name__ == "__main__":
    chat_with_agent()