import streamlit as st
import requests
import json
from database_handler import DatabaseHandler, FIXED_USER_ID

# Page configuration
st.set_page_config(page_title="Arka Proposal Agent", page_icon="☀️")
st.title("☀️ Arka Proposal Agent")

# API endpoint
API_URL = "http://localhost:8000/api/chat/"

# Initialize session state
if 'db' not in st.session_state:
    st.session_state.db = DatabaseHandler()

    # Load chat history from database
    chat_history = st.session_state.db.get_chat_history()

    if chat_history:
        # Resume from existing chat
        st.session_state.messages = [
            {"role": msg['role'] if msg['role'] == 'user' else "assistant",
             "content": msg['message']}
            for msg in chat_history
        ]
    else:
        # New conversation - get initial message from API
        try:
            response = requests.post(
                API_URL,
                json={"query": "", "session_id": FIXED_USER_ID}
            )
            if response.status_code == 200:
                data = response.json()
                if data['response']:
                    st.session_state.messages = [
                        {"role": "assistant", "content": data['response']}
                    ]
            else:
                st.session_state.messages = []
        except:
            st.error("Failed to connect to backend. Make sure the FastAPI server is running.")
            st.session_state.messages = []

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Type your message here..."):
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get bot response from API
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = requests.post(
                    API_URL,
                    json={"query": prompt, "session_id": FIXED_USER_ID}
                )

                if response.status_code == 200:
                    data = response.json()
                    bot_response = data['response']
                    st.markdown(bot_response)

                    # Add assistant response to chat
                    st.session_state.messages.append(
                        {"role": "assistant", "content": bot_response}
                    )
                else:
                    st.error("Failed to get response from backend")

            except Exception as e:
                st.error(f"Error connecting to backend: {str(e)}")

# Sidebar with additional info
with st.sidebar:
    st.header("Chat Info")

    # Show current state from database
    input_fields = st.session_state.db.get_user_input_fields()

    if input_fields:
        # Show current step
        if 'next_step' in input_fields and input_fields['next_step']:
            st.info(
                f"Current Step: {input_fields['next_step'][0] if isinstance(input_fields['next_step'], list) else input_fields['next_step']}")

        # Show collected data
        if 'session_state' in input_fields and input_fields['session_state']:
            state = input_fields['session_state']

            st.subheader("Collected Information")

            # Project details
            if state.get('project_details'):
                for key, value in state['project_details'].items():
                    if value and value != 'null' and key not in ['token', 'latitude', 'longitude']:
                        display_key = key.replace('_', ' ').title()
                        st.text(f"{display_key}: {value}")

            # Other state information
            if state.get('consumption_type'):
                st.text(f"Consumption Type: {state['consumption_type']}")
            if state.get('consumption_value'):
                st.text(f"Consumption Value: {state['consumption_value']}")
            if state.get('final_price'):
                st.text(f"Price: ${state['final_price']}")

