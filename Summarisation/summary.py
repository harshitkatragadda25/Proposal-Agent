#!/usr/bin/env python3
"""
Simple Terminal-Based Solar Conversation Summarizer
Usage: python solar_summarizer.py
"""

import json
import requests


def get_summary_from_ollama(conversation_text):
    """Generate exactly 100-word summary using robust prompt template."""

    prompt = f"""You are a solar consultation expert. Summarize this conversation in EXACTLY 100 words.

CONVERSATION:
{conversation_text}

EXTRACT THESE MANDATORY DETAILS (write "Not provided" if missing):
🏠 ADDRESS: Complete street address with city
⚡ CONSUMPTION: Monthly electricity usage (kWh/units) or bill amount (₹)
💰 PRICING: System cost estimates or quotes mentioned
📋 PROJECT STATUS: What was created/completed (project created, design generated, proposal made)
🔄 OUTCOME: Current status or next steps discussed

FORMATTING RULES:
- Write EXACTLY 100 words (no more, no less)
- Use this structure: "Customer from [ADDRESS] inquired about solar installation. Monthly consumption: [CONSUMPTION]. Project status: [STATUS]. Pricing discussed: [PRICING]. Conversation outcome: [OUTCOME]. [Additional relevant details]."
- Include ALL extracted information even if brief
- Use clear, professional language
- If multiple conversations, separate key points with semicolons

SUMMARY (exactly 100 words):"""

    # Call Ollama API
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.1",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temperature for consistency
                    "top_p": 0.9,
                    "max_tokens": 150
                }
            },
            timeout=60
        )

        if response.status_code == 200:
            result = response.json()
            return result.get('response', '').strip()
        else:
            return f"❌ Ollama API Error: {response.status_code}"

    except requests.exceptions.ConnectionError:
        return "❌ Cannot connect to Ollama. Make sure it's running: ollama serve"
    except Exception as e:
        return f"❌ Error: {str(e)}"


def convert_json_to_text(conversation_json):
    """Convert JSON conversation to readable text format."""
    try:
        # Handle if input is already a parsed list/dict
        if isinstance(conversation_json, (list, dict)):
            conversation = conversation_json
        else:
            # Clean and fix common JSON issues for string input
            conversation_input = conversation_json.strip()

            # Remove comment lines (lines starting with #)
            lines = conversation_input.split('\n')
            cleaned_lines = []
            for line in lines:
                stripped_line = line.strip()
                if not stripped_line.startswith('#'):
                    cleaned_lines.append(line)
            conversation_input = '\n'.join(cleaned_lines)

            # If user didn't add square brackets, add them
            if not conversation_input.startswith('['):
                conversation_input = '[' + conversation_input + ']'

            # Remove trailing comma before closing bracket
            conversation_input = conversation_input.replace(',]', ']')

            # Parse the JSON string
            conversation = json.loads(conversation_input)

        # Ensure it's a list
        if not isinstance(conversation, list):
            return None, "❌ Error: Input must be a JSON array of conversation messages"

        # Convert to readable format
        conversation_text = ""
        for msg in conversation:
            if not isinstance(msg, dict) or 'role' not in msg or 'content' not in msg:
                return None, "❌ Error: Each message must be a dict with 'role' and 'content' fields"

            role = "Customer" if msg['role'] == 'user' else "Assistant"
            conversation_text += f"{role}: {msg['content']}\n"

        return conversation_text, None

    except json.JSONDecodeError as e:
        return None, f"❌ Invalid JSON format: {str(e)}\n💡 Tip: Remove # comments or make sure JSON is properly formatted"
    except Exception as e:
        return None, f"❌ Error processing input: {str(e)}\n💡 Make sure input is valid JSON format"


def main():
    """Main function to handle terminal input and generate summaries."""

    print("🤖 Solar Conversation Summarizer")
    print("=" * 50)
    print("📝 Paste your conversation in JSON format below.")
    print("💡 You can paste with or without [ ] brackets - I'll fix it automatically!")
    print("📋 Example format:")
    print('   {"role": "user", "content": "Hi"},')
    print('   {"role": "assistant", "content": "Hello!"}')
    print("⚡ Commands: 'demo' for test example, 'multiline' for multi-line input, 'quit' to exit")
    print("=" * 50)

    while True:
        try:
            # Get input from user
            print("\n📋 Enter conversation JSON (or command):")
            user_input = input("> ").strip()

            # Handle multiline input
            if user_input.lower() == 'multiline':
                print("📝 Enter your JSON (press Enter twice to finish):")
                lines = []
                while True:
                    line = input()
                    if line == "":
                        break
                    lines.append(line)
                user_input = "".join(lines)

            # Handle special commands
            if user_input.lower() == 'quit':
                print("👋 Goodbye!")
                break

            if user_input.lower() == 'demo':
                # Demo conversation
                user_input = '''[
    {"role": "user", "content": "Hi, I want a solar proposal."},
    {"role": "assistant", "content": "Sure! Could you provide your address first?"},
    {"role": "user", "content": "Uh, just put Mumbai for now."},
    {"role": "assistant", "content": "To proceed, I'll need a specific street address in Mumbai. Could you share the complete address?"},
    {"role": "user", "content": "Okay, it's 221B Baker Street, Mumbai."},
    {"role": "assistant", "content": "Thanks, project created at that address. Should I generate the design now?"},
    {"role": "user", "content": "Yes, please."},
    {"role": "assistant", "content": "Design created. Now, what's your average monthly electricity consumption in kWh?"},
    {"role": "user", "content": "I don't know exactly."},
    {"role": "assistant", "content": "No worries! Can you share an approximate monthly bill in ₹ or average units consumed? Even an estimate will work."},
    {"role": "user", "content": "Around 700 units."},
    {"role": "assistant", "content": "Great, I'll record 700 kWh. We're all set to create your proposal now!"}
]'''
                print("🎯 Using demo conversation...")

            # Convert JSON to text format
            conversation_text, error = convert_json_to_text(user_input)
            if error:
                print(error)
                continue

            # Generate summary
            print("\n🔄 Generating summary with Llama3.1...")
            print("⏳ Please wait...")

            summary = get_summary_from_ollama(conversation_text)

            # Display results
            word_count = len(summary.split())
            print(f"\n📋 SUMMARY ({word_count} words):")
            print("=" * 60)
            print(summary)
            print("=" * 60)

            if word_count != 100:
                print(f"⚠️  Note: Got {word_count} words instead of exactly 100")

            print("\n✅ Summary complete!")
            print("🔄 Enter another conversation or type 'quit' to exit")

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")


if __name__ == "__main__":
    # Quick connectivity check
    try:
        test_response = requests.get("http://localhost:11434/api/tags", timeout=3)
        if test_response.status_code == 200:
            print("✅ Ollama is running and accessible")
        else:
            print("⚠️  Ollama might not be properly configured")
    except:
        print("❌ Cannot connect to Ollama!")
        print("🔧 Please ensure Ollama is running:")
        print("   1. ollama serve")
        print("   2. ollama pull llama3.1")
        exit(1)

    main()