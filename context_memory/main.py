import sys
import requests
import json
from typing import List, Dict
from message_store import MessageStore
from context_manager import ContextManager


class OllamaChatbot:
    def __init__(self, model: str = "mistral", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.api_url = f"{base_url}/api/generate"

    def is_ollama_running(self) -> bool:
        """Check if Ollama is running and accessible"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model["name"].split(":")[0] for model in data.get("models", [])]
            return []
        except requests.RequestException:
            return []

    def check_model_exists(self) -> bool:
        """Check if the selected model exists"""
        available_models = self.get_available_models()
        return any(self.model in model for model in available_models)

    def generate_response(self, user_message: str, context_messages: List[Dict[str, str]] = None) -> str:
        """
        Generate a response using Ollama with optional context
        """
        if not self.is_ollama_running():
            return "Error: Ollama is not running. Please check if Ollama is started."

        # Check if model exists
        if not self.check_model_exists():
            available_models = self.get_available_models()
            if available_models:
                return f"Error: Model '{self.model}' not found. Available models: {', '.join(available_models)}. Install with: ollama pull {self.model}"
            else:
                return f"Error: Model '{self.model}' not found. Install with: ollama pull {self.model}"

        # Build the prompt with context
        if context_messages:
            context_manager = ContextManager(None)  # We don't need the store here
            context_str = context_manager.format_context_for_prompt(context_messages)

            system_prompt = f"""You are a helpful AI assistant. You have access to previous conversation history to maintain context and provide coherent responses.

{context_str}

Current user message: {user_message}

Please respond naturally, taking into account the conversation history above."""
        else:
            system_prompt = f"You are a helpful AI assistant. User message: {user_message}"

        # Prepare the request payload
        payload = {
            "model": self.model,
            "prompt": system_prompt,
            "stream": False,
            "options": {
                "temperature": 0.5,
                "top_p": 0.9,
                "max_tokens": 500
            }
        }

        try:
            # Make the request to Ollama
            response = requests.post(
                self.api_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("response", "No response generated")
            else:
                return f"Error: {response.status_code} - {response.text}"

        except requests.RequestException as e:
            return f"Error connecting to Ollama: {str(e)}"


class ChatbotPipeline:
    def __init__(self, conversation_id: str = "imported", context_limit: int = 10):
        self.conversation_id = conversation_id
        self.context_limit = context_limit

        # Initialize components
        self.message_store = MessageStore()
        self.context_manager = ContextManager(self.message_store)
        self.chatbot = OllamaChatbot()

        print(f"🤖 Context-Aware Chatbot Pipeline")
        print(f"📁 Conversation ID: {conversation_id}")
        print(f"🔄 Context limit: {context_limit} message pairs")

    def chat(self, user_message: str) -> str:
        """
        Process a user message and return the chatbot response with context
        """
        # Get conversation context
        context_messages = self.context_manager.get_context_messages(
            self.conversation_id,
            self.context_limit
        )

        print(f"📖 Using {len(context_messages)} previous messages as context")

        # Generate response with context
        response = self.chatbot.generate_response(user_message, context_messages)

        # Store both user message and assistant response
        self.message_store.add_message("user", user_message, self.conversation_id)
        self.message_store.add_message("assistant", response, self.conversation_id)

        return response

    def show_available_conversations(self):
        """Show available conversation IDs"""
        try:
            with open(self.message_store.json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if "conversations" not in data or not data["conversations"]:
                print("📭 No conversations found")
                return

            # Get unique conversation IDs
            conversation_ids = list(set(msg["conversation_id"] for msg in data["conversations"]))

            print(f"\n📋 Available conversations:")
            for conv_id in sorted(conversation_ids):
                messages = self.message_store.get_messages(conv_id)
                print(f"   💬 '{conv_id}' - {len(messages)} messages")

        except Exception as e:
            print(f"❌ Error reading conversations: {str(e)}")

    def interactive_chat(self):
        """Run an interactive chat session"""
        print("\n🤖 Context-Aware Chatbot (Ollama + Mistral)")
        print("💡 Using imported conversation as context")
        print("\nCommands:")
        print("• Type 'quit', 'exit', or 'q' to end")
        print("• Type 'conversations' to see available conversations")
        print("• Type 'models' to see available models")
        print("• Type 'switch <conversation_id>' to change conversation")
        print("-" * 50)

        # Check if Ollama is running
        if not self.chatbot.is_ollama_running():
            print("❌ Error: Ollama is not running!")
            print("Please check if Ollama is started.")
            return

        # Check if model is available
        if not self.chatbot.check_model_exists():
            available_models = self.chatbot.get_available_models()
            print(f"❌ Error: Model '{self.chatbot.model}' not found!")
            if available_models:
                print(f"📋 Available models: {', '.join(available_models)}")
            print(f"💡 Install Mistral with: ollama pull mistral")
            return

        print(f"✅ Using model: {self.chatbot.model}")

        # Show available conversations at start
        self.show_available_conversations()

        while True:
            try:
                user_input = input(f"\n👤 You [{self.conversation_id}]: ").strip()

                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break

                elif user_input.lower() == 'conversations':
                    self.show_available_conversations()
                    continue

                elif user_input.lower() == 'models':
                    available_models = self.chatbot.get_available_models()
                    if available_models:
                        print(f"📋 Available models: {', '.join(available_models)}")
                        print(f"🔄 Current model: {self.chatbot.model}")
                    else:
                        print("❌ No models found or Ollama not accessible")
                    continue

                elif user_input.lower().startswith('switch '):
                    new_conv_id = user_input[7:].strip()
                    if new_conv_id:
                        self.conversation_id = new_conv_id
                        print(f"🔄 Switched to conversation: {new_conv_id}")
                    else:
                        print("❌ Please provide a conversation ID")
                    continue

                elif not user_input:
                    print("Please enter a message")
                    continue

                # Get chatbot response
                print("🤖 Assistant: ", end="", flush=True)
                response = self.chat(user_input)
                print(response)

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {str(e)}")


def main():
    """Main entry point"""
    print("🚀 Starting Context-Aware Chatbot Pipeline...")

    if len(sys.argv) > 1:
        # Handle different command line arguments
        if sys.argv[1] == "--conversation" and len(sys.argv) > 2:
            # Use specific conversation ID
            conversation_id = sys.argv[2]
            if len(sys.argv) > 3:
                # Single message mode with specific conversation
                user_message = " ".join(sys.argv[3:])
                pipeline = ChatbotPipeline(conversation_id)
                response = pipeline.chat(user_message)
                print(f"Response: {response}")
            else:
                # Interactive mode with specific conversation
                pipeline = ChatbotPipeline(conversation_id)
                pipeline.interactive_chat()
        else:
            # Single message mode with default conversation
            user_message = " ".join(sys.argv[1:])
            pipeline = ChatbotPipeline()
            response = pipeline.chat(user_message)
            print(f"Response: {response}")
    else:
        # Interactive mode with default conversation
        pipeline = ChatbotPipeline()
        pipeline.interactive_chat()


if __name__ == "__main__":
    main()
