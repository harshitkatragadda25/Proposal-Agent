from pathlib import Path
import json
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, Field, EmailStr, ValidationError
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider


#Pydantic data model for projects
class ProjectCreateSchema(BaseModel):
    project_name: str = Field(description="Name of the Project")
    project_address: str = Field(description="Installation site (city/address)")
    client_email: EmailStr = Field(description="Client's contact email")
    created_at: str = Field(description="Creation timestamp")


# 2. Storage dependency
@dataclass
class StoreDeps:
    json_path: Path = Path("projects.json")

    def save_project(self, project: ProjectCreateSchema):

        project_list = []
        if self.json_path.exists():
            try:
                with self.json_path.open("r", encoding="utf-8") as f:
                    project_list = json.load(f)
            except:
                project_list = []

        project_list.append(project.model_dump())

        with self.json_path.open("w", encoding="utf-8") as f:
            json.dump(project_list, f, indent=2, ensure_ascii=False)


# 3. Ollama Mistral model
model = OpenAIModel(
    model_name="mistral",
    provider=OpenAIProvider(base_url="http://localhost:11434/v1")
)

# 4. Smart project collection agent using message history
project_agent = Agent[StoreDeps, str](
    model=model,
    deps_type=StoreDeps,
    system_prompt=(
        "You are a helpful project information collector. You need to gather these 3 pieces of information:\n"
        "1. Project name\n"
        "2. Project address (installation site/location)\n"
        "3. Client email address\n\n"
        "IMPORTANT WORKFLOW:\n"
        "- FIRST: Always check the conversation history to see what information has already been provided\n"
        "- Look for project names in phrases like: 'project called X', 'project name is X', 'project for X'\n"
        "- Look for addresses in: location descriptions, street addresses, city names, installation sites\n"
        "- Look for email addresses in standard email format (user@domain.com)\n"
        "- If you find ALL THREE pieces of information in the conversation history, call save_project immediately\n"
        "- If information is missing, ask for only what's still needed\n"
        "- Be conversational and acknowledge what information you already have\n"
        "- Once you have everything, thank the user and save the project\n\n"
        "Remember: The user may provide information in any order and across multiple messages."
    )
)


# 5. Tool to save project data
@project_agent.tool
def save_project(
        ctx: RunContext[StoreDeps],
        project_name: str,
        project_address: str,
        client_email: str
) -> str:
    try:
        # Create project with timestamp
        project = ProjectCreateSchema(
            project_name=project_name,
            project_address=project_address,
            client_email=client_email,
            created_at=datetime.now().isoformat()
        )

        # Save to file
        ctx.deps.save_project(project)

        return (
            f"🎉 Perfect! Thank you for providing all the information!\n\n"
            f"📋 Project Summary:\n"
            f"✅ Project Name: {project_name}\n"
            f"✅ Installation Address: {project_address}\n"
            f"✅ Client Email: {client_email}\n\n"
            f"Your project has been successfully saved to the system. "
            f"Thank you for using our service! 🌟"
        )

    except ValidationError:
        return "❌ Invalid email format. Please provide a valid email address."
    except Exception as e:
        return f"❌ Error saving project: {str(e)}"


# 6. Main application
def main():
    deps = StoreDeps()

    print("=== Smart Project Data Entry ===")
    print("Hi! I'll help you create a new project by collecting some information.\n")

    try:
        # Start the conversation
        conversation_state = project_agent.run_sync(
            "I want to create a new project. Please help me by collecting the required information.",
            deps=deps
        )
        print("Assistant:", conversation_state.output)

        # Continue conversation loop
        while True:
            user_input = input("\nYou: ").strip()

            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("Goodbye!")
                break

            if not user_input:
                print("Please enter something or type 'quit' to exit.")
                continue

            # Continue conversation with full message history
            conversation_state = project_agent.run_sync(
                user_input,
                deps=deps,
                message_history=conversation_state.all_messages()
            )
            print("Assistant:", conversation_state.output)

            # Exit if project was saved successfully
            if "🎉 Perfect!" in conversation_state.output:
                print("\n🌟 Project creation completed successfully!")
                break

    except KeyboardInterrupt:
        print("\n\nGoodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()