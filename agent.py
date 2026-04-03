from pydantic import BaseModel
from pydantic_ai import Agent, tool, RunContext
from dataclasses import dataclass
import uuid

# Dependency container (empty for now, can hold API clients etc.)
@dataclass
class Deps:
    pass

# --- Schema definitions ---

class ProjectCreateSchema(BaseModel):
    project_name: str
    client_name: str
    address: str

class CreateDesignSchema(BaseModel):
    project_id: str
    layout: str

# --- Tool functions ---

@tool
def create_project(ctx: RunContext[Deps], project_name: str, client_name: str, address: str) -> str:
    print(f"Creating project: {project_name}, Client: {client_name}, Address: {address}")
    return str(uuid.uuid4())  # mock project_id

@tool
def create_design(ctx: RunContext[Deps], project_id: str, layout: str) -> str:
    print(f"Creating design for Project ID: {project_id}, Layout: {layout}")
    return f"Design created for project {project_id} with layout {layout}"

# --- Agent setup ---

agent = Agent("ollama:mistral", tools=[create_project, create_design], deps_type=Deps)

# --- Run the agent ---

async def main():
    prompt = "Create a design using a south-facing layout"
    result = await agent.run(prompt)
    print("Agent Response:", result)

# To run: await main() (in an async environment like Jupyter or asyncio loop)
