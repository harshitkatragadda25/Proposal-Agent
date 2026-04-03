from pydantic_ai import Agent, RunContext

from Proposal_agent.backend.chatbot import design_create_chain

# Define your specialized agents
project_agent = Agent('openai:gpt-4o', system_prompt="You create new projects")
design_agent = Agent('openai:gpt-4o', system_prompt="You generate project summaries")

# Main orchestrator agent
main_agent = Agent(
    'openai:gpt-4o',
    system_prompt="You coordinate project operations using specialized agents"
)


@main_agent.tool
async def create_project_via_agent(ctx: RunContext) -> dict:
    """Tool that calls the project_agent to create a new project"""

    result = await project_agent.run(
        "Create a new project with default settings",
        deps=ctx.deps  # Pass current dependencies if needed
    )

    return {
        "action": "project_created",
        "project_id": result.output.get("project_id"),
        "details": result.output
    }


@main_agent.tool
async def get_project_summary_via_agent(
        ctx: RunContext,
        project_id: int
) -> str:
    """Tool that calls the summary_agent to generate project summary"""

    result = await design_agent.run(
        f"Generate a summary for project {project_id}",
        deps=ctx.deps
    )

    return result.output
