from typing import List, Dict, Any
from message_store import MessageStore


class ContextManager:
    def __init__(self, message_store: MessageStore):
        self.message_store = message_store

    def get_context_messages(self, conversation_id: str = "imported", context_limit: int = 5) -> List[Dict[str, str]]:
        """
        Get the last N messages formatted for use as context in the chatbot prompt
        Returns list of dicts with 'role' and 'content' keys
        """
        messages = self.message_store.get_messages(conversation_id, limit=context_limit * 2)

        # Format messages for context (remove timestamp and conversation_id)
        context_messages = []
        for msg in messages:
            context_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        return context_messages

    def format_context_for_prompt(self, context_messages: List[Dict[str, str]]) -> str:
        """
        Format context messages into a readable string for the system prompt
        """
        if not context_messages:
            return "No previous conversation history."

        context_str = "Previous conversation history:\n"
        for msg in context_messages:
            role_label = "User" if msg["role"] == "user" else "Assistant"
            context_str += f"{role_label}: {msg['content']}\n"

        context_str += "\nBased on this conversation history, please respond appropriately to the current message."
        return context_str