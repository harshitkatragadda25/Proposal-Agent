

import json
import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from pydantic import BaseModel, EmailStr, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider


class ProjectCreateSchema(BaseModel):
    project_name: str = Field(description="Name of the Project")
    project_address: str = Field(description="Installation site (city/address)")
    client_email: EmailStr = Field(description="Client's contact email")
    created_at: str = Field(description="Creation timestamp")


def validate_email_simple(email: str) -> tuple[bool, str]:

    # Clean the email
    email = email.strip().lower()

    # Email regex pattern - covers 99% of real emails
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if re.match(pattern, email):
        return True, email
    else:
        return False, email


def load_projects(filename: str = "projects.json") -> list:

    try:
        if Path(filename).exists():
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"⚠️ Warning: Could not load existing projects: {e}")
        return []


def save_project(project: dict, filename: str = "projects.json") -> bool:

    try:
        # Load existing projects
        projects = load_projects(filename)

        # Add timestamp
        project['created_at'] = datetime.now().isoformat()

        # Add new project
        projects.append(project)

        # Save back to file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(projects, f, indent=2, ensure_ascii=False)

        return True
    except Exception as e:
        print(f"❌ Error saving project: {e}")
        return False


def show_existing_projects(filename: str = "projects.json"):

    projects = load_projects(filename)

    if not projects:
        print("📂 No existing projects found.")
        return

    print(f"\n📊 EXISTING PROJECTS ({len(projects)} total):")
    print("-" * 60)

    for i, project in enumerate(projects, 1):
        print(f"{i}. {project.get('project_name', 'N/A')}")
        print(f"   📍 {project.get('project_address', 'N/A')}")
        print(f"   📧 {project.get('client_email', 'N/A')}")
        print(f"   📅 {project.get('created_at', 'N/A')}")
        print("-" * 60)



def get_project_name() -> str:

    print("\n📋 PROJECT NAME")
    while True:
        name = input("Enter project name: ").strip()
        if name and len(name) >= 2:
            print(f"✅ Project name: {name}")
            return name
        print("❌ Please enter a valid project name (at least 2 characters)")


def get_project_address() -> str:

    print("\n🏠 PROJECT ADDRESS")
    while True:
        address = input("Enter installation site (city/address): ").strip()
        if address and len(address) >= 3:
            print(f"✅ Project address: {address}")
            return address
        print("❌ Please enter a valid address (at least 3 characters)")


def get_client_email() -> str:

    print("\n📧 CLIENT EMAIL")
    while True:
        email = input("Enter client email: ").strip()

        if not email:
            print("❌ Email cannot be empty")
            continue

        is_valid, normalized_email = validate_email_simple(email)

        if is_valid:
            print(f"✅ Valid email: {normalized_email}")
            return normalized_email
        else:
            print("❌ Invalid email format. Please try again.")
            print("   Example: user@example.com")



def collect_project_data() -> dict:

    print("\n🎯 CREATING NEW PROJECT")
    print("=" * 40)

    # Collect data step by step
    project_name = get_project_name()
    project_address = get_project_address()
    client_email = get_client_email()

    # Create project dictionary
    project = {
        'project_name': project_name,
        'project_address': project_address,
        'client_email': client_email
    }

    return project


def confirm_project_data(project: dict) -> bool:

    print("\n📝 CONFIRM PROJECT DETAILS")
    print("=" * 30)
    print(f"Project Name: {project['project_name']}")
    print(f"Address: {project['project_address']}")
    print(f"Client Email: {project['client_email']}")

    while True:
        confirm = input("\nSave this project? (yes/no): ").strip().lower()
        if confirm in ['yes', 'y']:
            return True
        elif confirm in ['no', 'n']:
            return False
        else:
            print("Please enter 'yes' or 'no'")



def setup_ollama_agent():

    try:
        # Configure Ollama model
        model = OpenAIModel(
            model_name='mistral',
            provider=OpenAIProvider(base_url='http://localhost:11434/v1')
        )

        # Create simple agent for generating responses
        agent = Agent(
            model=model,
            system_prompt="You are a helpful assistant. Provide brief, positive responses."
        )

        return agent
    except Exception as e:
        print(f"⚠️ Could not setup AI agent: {e}")
        return None



async def main_app():
    print("🚀 PYDANTIC AI PROJECT COLLECTION AGENT")
    print("=" * 50)
    print("Welcome! This tool helps you create and save project data.")
    print("=" * 50)

    # Show existing projects
    print("\n🔍 Checking existing projects...")
    show_existing_projects()

    # Collect new project data
    try:
        project_data = collect_project_data()

        # Confirm with user
        if confirm_project_data(project_data):
            # Save to JSON
            if save_project(project_data):
                print("\n🎉 SUCCESS!")
                print(f"✅ Project '{project_data['project_name']}' saved successfully!")

                # Try to generate AI response
                agent = setup_ollama_agent()
                if agent:
                    try:
                        response = await agent.run(
                            f"Write a brief congratulations message for creating project '{project_data['project_name']}'"
                        )
                        print(f"\n🤖 {response.output}")
                    except:
                        pass  # AI response is optional

                # Validate with Pydantic
                try:
                    validated = ProjectCreateSchema(**project_data)
                    print(f"\n✅ Data validation passed!")
                    print(f"📋 Final data: {validated.model_dump()}")
                except Exception as e:
                    print(f"⚠️ Validation warning: {e}")
                    print("📋 Data was still saved to JSON file.")

            else:
                print("\n❌ Failed to save project data")
        else:
            print("\n❌ Project creation cancelled")

    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")

def main():

    try:
        # Check basic requirements
        print("🔍 Checking system requirements...")

        # Test imports
        try:
            import pydantic_ai
            print("✅ Pydantic AI available")
        except ImportError:
            print("❌ Please install: pip install pydantic-ai")
            return

        # Test Ollama connection (optional)
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=3)
            if response.status_code == 200:
                models = response.json().get('models', [])
                if any('mistral' in model['name'] for model in models):
                    print("✅ Ollama + Mistral ready")
                else:
                    print("⚠️ Mistral not found. AI responses disabled.")
                    print("   Install with: ollama pull mistral")
            else:
                print("⚠️ Ollama not responding. AI responses disabled.")
        except:
            print("⚠️ Ollama check failed. AI responses disabled.")
            print("   Make sure Ollama is running for AI features.")

        # Run main application
        asyncio.run(main_app())

    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Startup error: {e}")


if __name__ == "__main__":
    main()