import json
import os
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider


# Project data models
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


# Setup Ollama model
ollama_model = OpenAIModel(
    model_name='llama3.1',  # Change this to your available model
    provider=OpenAIProvider(base_url='http://localhost:11434/v1')
)

# Create the design agent
design_agent = Agent(
    model=ollama_model,
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
- Ask if they want to create a new project
- Acknowledge their response but inform them that project creation functionality is not yet implemented

## CRITICAL RULES:
- NEVER make up project data - only show what's actually in the JSON file
- ALWAYS verify project IDs with the check_project_id tool
- Be clear and professional in your responses
- When project creation is requested, politely inform that this feature is coming soon

## EXAMPLES OF USER INPUTS TO HANDLE:
- "12345678" → Extract as project ID and check
- "My project ID is 87654321" → Extract 87654321 and check
- "Check project 11223344" → Extract 11223344 and check
- "I want to check my project" → Ask for project ID
- "Yes, create new project" → Acknowledge but inform feature is not yet available

Remember: Your primary job is to validate project access. Project creation will be added in a future update."""
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


def run_design_agent():

    data_manager = ProjectDataManager()

    print("🎨 Design Agent - Project Verification System")
    print("=" * 60)
    print("I can help you verify existing projects with their Project ID.")
    print()
    print("To get started:")
    print("• Provide your 8-digit Project ID to access existing project")
    print("• Type 'quit' to exit")
    print()
    print("Note: Project creation functionality coming soon!")
    print("=" * 60)
    print()

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in ['quit', 'exit', 'bye']:
            print("👋 Goodbye!")
            break

        if not user_input:
            continue

        try:
            result = design_agent.run_sync(user_input, deps=data_manager)
            print(f"Design Agent: {result.output}")

        except Exception as e:
            print(f"❌ Error: {e}")
            print("💡 Make sure Ollama is running and the model is available")

        print()


# Main execution
if __name__ == "__main__":
    run_design_agent()