import asyncio
import hashlib
import re
from typing import Dict, Optional, Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

#  Ollama model configuration

ollama_model = OpenAIModel(
    model_name="llama3.1",
    provider=OpenAIProvider(base_url="http://localhost:11434/v1")
)


#  Specialized agents

project_agent = Agent(
    ollama_model,
    system_prompt=(
        "You are a highly professional project-creation specialist and consultant.\n"
        "• Always greet clients with utmost professionalism and courtesy\n"
        "• Use formal language, proper titles, and business etiquette\n"
        "• Create new projects with appropriate settings when requested\n"
        "• Provide detailed explanations and professional guidance\n"
        "• Always address the client respectfully (e.g., 'Dear Client', 'Esteemed Customer')\n"
        "• Maintain professional demeanor throughout the conversation\n"
        "• You will continue conversations until the client says 'thank you'"
    )
)

design_agent = Agent(
    ollama_model,
    system_prompt=(
        "You are a quirky design agent who loves making jokes and being playful.\n"
        "• NEVER directly answer questions - always deflect with humor\n"
        "• Make jokes, puns, and witty remarks instead of giving useful answers\n"
        "• Be sarcastic and playful in your responses\n"
        "• Change the topic to something completely random\n"
        "• Make dad jokes, puns, or silly observations\n"
        "• If asked about design, talk about pizza, weather, or anything else\n"
        "• You will continue this playful behavior until the client says 'thank you'"
    )
)


#  Main orchestrator agent

main_agent = Agent(
    ollama_model,
    system_prompt=(
        "You are an intelligent project orchestrator that coordinates between specialized agents.\n\n"
        "Your responsibilities:\n"
        "1. Analyze user requests to understand their intent\n"
        "2. Route requests to appropriate specialized agents via tools\n"
        "3. Provide helpful responses based on the tool outputs\n"
        "4. Handle follow-up questions and clarifications\n\n"
        "Request Classification:\n"
        "- PROJECT CREATION requests: \"create project\", \"new project\", \"start project\", "
        "\"build project\", \"initialize project\", \"setup project\"\n"
        "- DESIGN/SUMMARY requests: \"design\", \"summary\", \"generate design\", "
        "\"project summary\", \"design proposal\", \"show design\"\n\n"
        "Guidelines:\n"
        "- Always use tools to handle specialized requests\n"
        "- Provide context and explanation with tool results\n"
        "- Ask for clarification if the request is ambiguous\n"
        "- Be helpful and guide users through the process\n"
        "- If a request doesn't match any tool, provide general assistance\n\n"
        "Remember: You coordinate and enhance the work of specialized agents, don't replace them."
    )
)

#  Agent conversation loops
async def project_agent_loop() -> Dict[str, Any]:
    print("\n[Main Agent] -> [Project Agent] Transferring you to our professional project consultant...")

    # Initial professional greeting
    greeting = await project_agent.run(
        "Greet the client professionally and introduce yourself as their project consultant. "
        "Ask how you can assist them with their project needs today.",
        deps={}
    )
    print(f"\n[Project Agent] {greeting.data}")

    project_data = None

    while True:
        user_input = input("\nYou: ").strip()

        if user_input.lower() in ["thank you", "thanks", "thank you!", "thanks!"]:
            farewell = await project_agent.run(
                "The client is thanking you. Give a professional farewell and mention they're being transferred back to the main system.",
                deps={}
            )
            print(f"\n[Project Agent] {farewell.data}")
            break

        # Handle project creation or general professional consultation
        if any(keyword in user_input.lower() for keyword in ["create", "new", "start", "build", "project"]):
            response = await project_agent.run(
                f"Client said: '{user_input}'. Create a new project professionally and provide details. "
                "Generate a project_id and provide comprehensive project information.",
                deps={}
            )
            # Generate project data
            project_id = f"proj_{hashlib.md5(user_input.encode()).hexdigest()[:8]}"
            project_data = {
                "project_id": project_id,
                "status": "created",
                "details": str(response.data)
            }
        else:
            response = await project_agent.run(
                f"Client said: '{user_input}'. Respond professionally and helpfully as their project consultant.",
                deps={}
            )

        print(f"\n[Project Agent] {response.data}")

    return {
        "action": "project_session_completed",
        "project_data": project_data,
        "message": "Professional consultation completed successfully."
    }


async def design_agent_loop() -> Dict[str, Any]:
    print("\n[Main Agent] -> [Design Agent] Connecting you to our... unique design specialist...")

    # Initial joke greeting
    greeting = await design_agent.run(
        "Greet the user but instead of talking about design, make a joke or talk about something completely random like pizza or penguins.",
        deps={}
    )
    print(f"\n[Design Agent] {greeting.data}")

    while True:
        user_input = input("\nYou: ").strip()

        if user_input.lower() in ["thank you", "thanks", "thank you!", "thanks!"]:
            farewell = await design_agent.run(
                "The user is thanking you. Make a final joke and mention they're going back to the boring main system.",
                deps={}
            )
            print(f"\n[Design Agent] {farewell.data}")
            break

        # Always deflect with jokes, never answer the actual question
        response = await design_agent.run(
            f"User said: '{user_input}'. DO NOT answer their question directly. "
            "Instead, make a joke, change the topic, or talk about something completely unrelated. "
            "Be playful and avoid giving any actual design advice.",
            deps={}
        )

        print(f"\n[Design Agent] {response.data}")

    return {
        "action": "design_session_completed",
        "design_content": "No actual design work was done, just lots of jokes!",
        "message": "Comedy session completed successfully."
    }



#  Tools available to the main agent

@main_agent.tool
async def create_project_via_agent(ctx: RunContext) -> Dict[str, Any]:

    return await project_agent_loop()


@main_agent.tool
async def get_design_via_agent(
        ctx: RunContext,
        project_id: Optional[str] = None,
        design_request: Optional[str] = None
) -> Dict[str, Any]:

    return await design_agent_loop()



#  Helper: simple intent classification

def classify_intent(msg: str) -> str:
    msg_l = msg.lower()
    if any(k in msg_l for k in (
            "create project", "new project", "start project",
            "build project", "initialize project", "setup project"
    )):
        return "project_creation"
    if any(k in msg_l for k in (
            "design", "summary", "generate design",
            "project summary", "design proposal", "show design"
    )):
        return "design_request"
    return "general"



#  Public function to handle a single user message

async def handle_user_message(message: str) -> None:
    intent = classify_intent(message)

    if intent == "project_creation":
        print("\n[Main Agent] Understood: project creation requested.")
        result = await main_agent.run(
            f"User said: '{message}'. Call create_project_via_agent.",
            deps={}
        )
        print(f"\n[Main Agent] Session completed. {result.data}")

    elif intent == "design_request":
        print("\n[Main Agent] Understood: design/summary requested.")
        result = await main_agent.run(
            f"User said: '{message}'. Call get_design_via_agent.",
            deps={}
        )
        print(f"\n[Main Agent] Session completed. {result.data}")

    else:
        print("\n[Main Agent] Providing general assistance.")
        result = await main_agent.run(
            f"User said: '{message}'. Reply helpfully without tools.",
            deps={}
        )
        print(f"\n[Main Agent] {result.data}")



#  Main CLI loop
if __name__ == "__main__":
    async def chat():
        print("🦙  Ollama Llama 3.1 Orchestrator (type 'quit' to exit)")
        print("━" * 60)
        print("Available commands:")
        print("• Say anything with 'project' to meet our professional consultant")
        print("• Say anything with 'design' to meet our... creative specialist")
        print("• Say 'thank you' to exit from any agent back to main menu")
        print("━" * 60)

        while True:
            user = input("\nYou: ").strip()
            if user.lower() in {"quit", "exit"}:
                print("\n[Main Agent] Goodbye! Thank you for using our services.")
                break
            try:
                await handle_user_message(user)
            except Exception as err:
                print(f"[Main Agent] ⚠️  Error: {err}")


    asyncio.run(chat())
