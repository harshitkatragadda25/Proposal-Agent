
import os
import json
from langgraph.graph import StateGraph, END
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_community.llms import Ollama
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableLambda
from langchain_core.messages import HumanMessage, AIMessage
import requests
from langgraph.checkpoint.memory import MemorySaver
import asyncio
import httpx
from consumption import predict_annual_consumption
from datetime import datetime
from utils import get_details_from_google_maps_result
DEV_TOKEN = '0ef5d0d971b817c445cb3ddb0e8bc04c3150f44d'
# DEV_TOKEN = '3f428252dec9354748a1fb8d459582bd714721d2'
# DEV_TOKEN ='4d9a57bcd6de0bd1d9db340333c69a9aeadd6577'
CHATBOT_URL = ''
DEV_DESIGN_STUDIO_URL ='https://dev.arka360.com'
ANNUAL_ESCALATION_RATE = 3.5
assumed_price =  4.5
# from langgraph.graph import interrupt


# settings.recursion_limit = 50
# Required fields
REQUIRED_FIELDS = [
    "project_name",
    "longitude",
    "latitude",
    "state",
    "pincode",
    "country_code",
    "price",
]


CREATE_LEAD_REQUIRED_FIELDS = ["lead_name", "address", "lead_email"]

FIELD_SCHEMA = {
    "project_name": {"type": "text", "label": "project name"},
    "client_name": {"type": "text", "label": "client name"},
    "client_number": {"type": "number", "label": "phone number"},
    "client_email": {"type": "email", "label": "email address"},
    "address": {"type": "text", "label": "project address"},
    "price": {"type": "number", "label": "project price"},
    "energy_consumption": {"type": "number", "label": "monthly energy consumption (kWh)"},
}

missing_details_prompt = PromptTemplate(
    input_variables=["missing_fields"],
    template="""
You’re a helpful assistant setting up a solar project in our platform.

Ask the user for the missing details below in **one clear, friendly sentence**.

Guidelines:
- This is a request, not a confirmation.
- No greetings or sign-offs.
- Do not include any form of "thank you", "thanks", or polite closings.
- No fluff, no filler — just the missing info.
- Direct and natural — like a quick check-in.
- Keep it conversational, not robotic.

Missing fields:
{missing_fields}
"""
)

# print("env base url",os.getenv("OLLAMA_BASE_URL"))
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")


# llm = Ollama(
#     base_url=OLLAMA_BASE_URL,
#     model="mistral"  # Replace with your actual model
# )

# print(f"Connecting to Ollama at: {OLLAMA_BASE_URL}")
# Initialize LLM
llm = Ollama(
           base_url=OLLAMA_BASE_URL, # Replace with your server IP and port
           model="mistral",
           temperature=0.5
        
       )



extract_project_detail_prompt = PromptTemplate(
    input_variables=["user_input"],
    template="""
You are a helpful assistant for Arka360, a powerful solar design and proposal platform.

Your task is to extract lead information from the given user input. Only return data that can be clearly and confidently identified.

Extract the following details:
- lead_name: Full name of the homeowner or lead
- lead_email: A valid email address
- address: Full address of the property (street, city, state, and zip if available)

If any field is missing or unclear, set its value to "null".

Strictly respond with a valid JSON object with these exact keys: "lead_name", "lead_email", and "address". Do not include any extra text or explanation.

Text: {user_input}
"""
)
# extract_project_detail_prompt = PromptTemplate(
#     input_variables=["user_input"],
#     template="""
# Extract the following details from the given text:

# - project_name
# - address
# - client_name
# - client_number
# - client_email

# If any field is missing or cannot be confidently identified, return the value "null" for that field.

# Respond **only** with a valid JSON object with the exact keys mentioned above — do not include any explanations or additional text.

# Text: {user_input}
# """
# )



template="""
You are a friendly, professional sales assistant for Arka360 — a powerful solar design and proposal platform.

Welcome new users and ask them for:
- Lead Name
- Lead Address
- Lead Email


Tone: Warm, confident, and helpful — but concise.

### Instructions
Generate a **single message**, exactly **30 words**, focusing on welcoming the user and requesting the 3 details above.

### Example (30 words):
Welcome to Arka360! To begin your solar journey, kindly share the lead's name, email, and address.

"""
template2="""
You are a friendly, professional sales assistant for Arka360 — a powerful solar design and proposal platform.

Welcome new users and ask them for:
- Project name
- Client name
- Project address

Tone: Warm, confident, and helpful — but concise.

### Instructions
Generate a **single message**, exactly **30 words**, focusing on welcoming the user and requesting the 3 details above.

### Example (30 words):
Welcome to Arka360 — your complete solar design platform! To get started, please share your project name, client name, and the project address. We're excited to help you create amazing designs!

"""


# template = """You are a helpful onboarding assistant for a solar design platform.

# Your task is to guide new users through the first step of setting up their solar project.

# Here’s the context:
# - The user is likely interacting for the first time.
# - You need to collect three **mandatory project details** before any other steps:
#   1. Project location (city or full address)
#   2. Project name
#   3. Client’s name

# Your goals:


# - Respond conversationally and clearly, keeping tone warm, concise, and professional.
# - Avoid jargon; assume user may not be familiar with solar terminology.

# ### EXAMPLE
# Output: 
# "Welcome to Arka360 — the all-in-one platform for designing and selling solar with precision! Let’s get started. Could you share your project name, client name, and the project address?"

# Now generate your onboarding prompt.
# """

onboard_prompt = PromptTemplate(
    input_variables=[],
    template = template)
    


price_update_prompt = PromptTemplate(
    input_variables=["price"],
    template="""
You are confirming a price update from the user.
Ask for a numeric value in a concise way.

EXAMPLE:
Output: "Sure! What's the new price you'd like to set?"

Now ask for updated price:
(Default shown was: {price})
"""
)

energy_consumption_prompt = PromptTemplate(
    input_variables=[],
    template=(
        "You are a sales assistant helping users provide their monthly energy consumption for solar system sizing."
        "Format the response clearly using bullet points, markdown, or buttons."
        "Ensure response is structured for easy selection."
        "Re-prompt if the user does not select an option or gives an invalid response."
        "Ask the user to input their average monthly energy consumption in kWh or select from given options."
        "Keep your response brief and clear."
        "Example: 'To estimate your solar needs, please provide your average monthly energy consumption in kWh (e.g., 500 kWh) or choose from the options below.'"
    ),
)

design_create_prompt = PromptTemplate(
    input_variables=[],
    template=(
        "You're a warm, professional sales assistant for a solar tool. The user submitted a location. In exactly 30 words, confirm you're generating a layout using smart roof detection with default components."
        " Default to: 'Thanks! We're now using our smart roof detection system to design your solar layout. It won't take long — we’ll let you know when it’s ready!' Only change if context requires."
    ),
)

calculate_generation_prompt = PromptTemplate(
    input_variables=[],
    template=(
        "You're a friendly sales assistant for a solar platform. The user finished their roof design. "
        "In exactly 30 words, warmly confirm you're calculating energy generation for their proposal. "
        "Default: 'Great! Your design's ready. We're now calculating how much solar energy it can produce to build your proposal. It won’t take long — we’ll update you shortly.' "
        "Only change if prior context requires it."
    ),
)
price_confirmation_prompt = PromptTemplate(
    input_variables=[],
    template=(
        "You're a friendly sales assistant for a solar platform. The user finished their roof design. "
        "In exactly 30 words, warmly confirm you're calculating energy generation for their proposal. "
        "Default: 'Great! Your design's ready. We're now calculating how much solar energy it can produce to build your proposal. It won’t take long — we’ll update you shortly.' "
        "Only change if prior context requires it."
    ),
)
confirmation_prompt = PromptTemplate(
    input_variables=[],
    template=(
        "You're a friendly sales assistant for a solar platform. The user finished their roof design. "
        "In exactly 30 words, warmly confirm you're calculating energy generation for their proposal. "
        "Default: 'Great! Your design's ready. We're now calculating how much solar energy it can produce to build your proposal. It won’t take long — we’ll update you shortly.' "
        "Only change if prior context requires it."
    ),
)

confirm_utility_rate_prompt = PromptTemplate(
    input_variables=["project_id"],
    template=(
        "You are a friendly and professional sales assistant for a solar energy tool. The user has completed their roof design, "
        "but they still need to select their utility rate before the system can calculate energy generation and finalize their solar proposal.\n\n"
        "Kindly remind them to visit the following link to select their utility rate:\n"
        "https://dev.arka360.com/projectSummary/{project_id}\n\n"
        "Respond warmly and clearly. Be supportive and professional. Let them know this step is essential for tailoring their proposal to their local electricity rates.\n\n"
        "Here are a few examples of how to respond:\n\n"
        "Example 1:\n"
        "Almost there! Just one more step — please select your utility rate so we can accurately calculate your solar savings. "
        "You can do that here: https://dev.arka360.com/projectSummary/{project_id}. Once that’s done, we’ll finalize your design!\n\n"
        "Example 2:\n"
        "Please visit this link and select your utility rate: https://dev.arka360.com/projectSummary/{project_id}. "
        "This helps us tailor your solar proposal to your actual electricity costs.\n\n"
        "Example 3:\n"
        "You're doing great! Next, head over to https://dev.arka360.com/projectSummary/{project_id} and pick your utility rate. "
        "It’s the final piece we need to finish up your customized solar savings estimate.\n\n"
        "Now generate a similar message using this tone, keeping it short, confident, and helpful."
    ),
)

select_utility_rate_first_time_prompt = PromptTemplate(
    input_variables=["project_id"],
    template=(
        "You are a friendly and professional sales assistant for a solar energy tool. The user has just created a new solar project.\n\n"
        "Let them know that the first step in preparing their personalized solar proposal is to select their utility rate. "
        "This helps the system understand their electricity costs and calculate savings.\n\n"
        "Kindly ask them to visit the following link to select their utility rate:\n"
        "https://dev.arka360.com/projectSummary/{project_id}\n\n"
        "Respond clearly. Make sure the user feels guided and confident in what to do next.\n\n"
        

        "Here are a few example messages:\n\n"

        "Example 1:\n"
        "Your solar project is set up — great start. Next, please select your utility rate so we can begin tailoring your solar proposal. "
        "You can do that here: https://dev.arka360.com/projectSummary/{project_id}\n\n"

        "Example 2:\n"
        "Awesome, your project is ready to go! Let’s kick things off by selecting your utility rate. This helps us estimate how much you can save. "
        "Start here: https://dev.arka360.com/projectSummary/{project_id}"

        "Example 3:\n"
        "Thanks for creating your solar project! The first step is choosing your utility rate — it helps us customize your savings. "
        "You can select it here: https://dev.arka360.com/projectSummary/{project_id}"

        "Now, using the same tone and structure, generate a message asking the user to select their utility rate for the first time."
    ),
)

select_utility_rate_first_time_chain = LLMChain(llm=llm, prompt=select_utility_rate_first_time_prompt)
confirm_utility_rate_chain = LLMChain(llm=llm, prompt=confirm_utility_rate_prompt)
design_create_chain = LLMChain(llm=llm, prompt=design_create_prompt)
price_update_chain = LLMChain(llm=llm, prompt=price_update_prompt)

price_confirmation_chain = LLMChain(llm=llm, prompt=price_confirmation_prompt)

missing_details_chain = LLMChain(llm=llm, prompt=missing_details_prompt)

extract_chain = LLMChain(llm=llm, prompt=extract_project_detail_prompt)

onboard_chain = LLMChain(llm=llm, prompt=onboard_prompt)

confirmation_chain = LLMChain(llm=llm, prompt=confirmation_prompt)

price_confirmation_chain = LLMChain(llm=llm, prompt=price_confirmation_prompt)

energy_consumption_chain = LLMChain(llm=llm, prompt=energy_consumption_prompt)

calculate_genration_chain = LLMChain(llm=llm, prompt=calculate_generation_prompt)

# calculate_genration_chain ="tetts"
# def error_codes(state):

def call_design_api_async(referance_id,consumption):
    import requests
    
    url = "https://zkoso3uwruiqggyskdmqjhf3au0cgdna.lambda-url.ap-south-1.on.aws/"
    payload = json.dumps({"base_url": "https://dev.arka360.com/",
                          "token": DEV_TOKEN, "aiRoof": True,
                          "reference_id": referance_id,
                          "consumptionValue":consumption})
    
    print("paylod design", payload)
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.6',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Content-Type': 'text/plain;charset=UTF-8',
        'Origin': 'https://dev.arka360.com',
        'Pragma': 'no-cache',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'cross-site',
        'Sec-GPC': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        'dnt': '1',
        'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Brave";v="134"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"'
    }

    response = requests.request(
        "GET", url, headers=headers, data=payload, verify=False
    )
    print("response",response)
    return response.json()

def check_missing_fields(project_details):
    return [
        field
        for field in CREATE_LEAD_REQUIRED_FIELDS
        if project_details.get(field) == "null"
    ]

def extract_json_from_block(text: str) -> dict:
    import re
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
    return None


    
def onboarding_details(state):
    if not state.get("user_input"):
       
        return {"message": onboard_chain.run({}), "next_step": "extract_details", "state": state}

import re

def is_valid_email(email):
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email))


def extract_details(state):
    if state.get("user_input"):
        # user_input = state.get("user_input")
        # print("userinput", user_input)
        # filled_prompt = extract_project_detail_prompt.format(user_input= user_input)
        # response = llm.generate_content(filled_prompt).text
        # print("response", response)
        # json_response = extract_json_from_block(response)
        user_input = state.get("user_input")
       
        response = extract_chain.run(user_input = user_input)
       
        json_response = json.loads(response)
#         missing_fields = json_response
        missing_fields = json_response
        
        if state.get("project_details"):
            project_details = state.get("project_details")
            if state["project_details"]["lead_email"]!="null"  and not is_valid_email(project_details["lead_email"]):
                state[project_details["lead_email"]] = "null"  
                return {"message":"To move forward with your solar design, we’ll need a valid email address. Can you please confirm it?","next_step":"extract_details","state":state}
            if state["project_details"]["address"]!="null" and not state["address_confirmed"] :
                
                latitude, longitude, country_code, _, _, _, _ = get_address_details(project_details.get("address"))
                state["latitude"] = latitude
                state['longitude'] = longitude
                return {"message":"Can you please confirm your address?","next_step":"extract_details","state":state}
            for key, value in json_response.items():
                if state["address_confirmed"] and key=="address":
                    continue
                
                elif state["project_details"][key] == "null":
                    state["project_details"][key] = value
                
                    
            missing_fields = state["project_details"]
        else:
            state["project_details"] = json_response
            project_details = state["project_details"]
            print("project details",project_details)
            if state["project_details"]["lead_email"]!="null"  and not is_valid_email(project_details["lead_email"]):
                state[project_details["lead_email"]] = "null"  
                return {"message":"To move forward with your solar design, we’ll need a valid email address. Can you please confirm it?","next_step":"extract_details","state":state}
                
            if state["project_details"]["address"]!="null" and not state["address_confirmed"] :
                project_details = state["project_details"]
                latitude, longitude, country_code, _, _, _, _ = get_address_details(project_details.get("address"))
                state["latitude"] = latitude
                state['longitude'] = longitude
                return {"message":"Can you please confirm your address?","next_step":"extract_details","state":state}
        if "address" in state["project_details"].keys():
            project_details = state["project_details"]
            latitude, longitude, _, _, _, _, _ = get_address_details(project_details.get("address"))
            state["latitude"] = latitude
            state['longitude'] = longitude
            
        state["missing_fields"] = check_missing_fields(missing_fields)
        return {"next_step": "request_details", "state": state}
    else:
        return onboarding_details(state)

# def extract_details(state):
#     if state.get("user_input"):
#         user_input = state.get("user_input")
#         print("userinput", user_input)
#         response = extract_chain.run(user_input = user_input)
#         print("response", response)
#         json_response = json.loads(response)
#         missing_fields = json_response
#         if state.get("project_details"):
#             if state["project_details"]["address"]!="null" and not state["address_confirmed"] :
#                 project_details = state["project_details"]
#                 latitude, longitude = get_address_details(project_details.get("address"))
#                 state["latitude"] = latitude
#                 state['longitude'] = longitude
#                 return {"message":"Can you please confirm your address?","next_step":"extract_details","state":state}
#             for key, value in json_response.items():
#                 if state["address_confirmed"] and key=="address":
#                     continue
                
#                 elif state["project_details"][key] == "null":
#                     state["project_details"][key] = value
                
                    
#             missing_fields = state["project_details"]
#         else:
#             state["project_details"] = json_response
#             if state["project_details"]["address"]!="null" and not state["address_confirmed"] :
#                 project_details = state["project_details"]
#                 latitude, longitude = get_address_details(project_details.get("address"))
#                 state["latitude"] = latitude
#                 state['longitude'] = longitude
#                 return {"message":"Can you please confirm your address?","next_step":"extract_details","state":state}
#         if "address" in state["project_details"].keys():
#             project_details = state["project_details"]
#             latitude, longitude = get_address_details(project_details.get("address"))
#             state["latitude"] = latitude
#             state['longitude'] = longitude
            
#         state["missing_fields"] = check_missing_fields(missing_fields)
#         return {"next_step": "request_details", "state": state}
#     else:
#         return onboarding_details(state)




def request_missing_details(missing_fields):
    missing_message = missing_details_chain.run(
        missing_fields=", ".join(missing_fields)
    )

    return missing_message



def request_details(state):
    if state.get("missing_fields"):
        request_missing_details_message = request_missing_details(state["missing_fields"])
        next_step = "extract_details"
        return {"message": request_missing_details_message, "state": state, "next_step": next_step}
    
    else:
        print("stae", state)

        return {"state": state, "next_step": "call_create_lead_api"}
        # return {"state": state, "next_step": "call_create_project_api"}





def save_advanced_price(state):
    design_id = state["design_id"]

    url = f"https://98.70.40.35:8006/api/designs/{design_id}/advanced_update/"

    payload = "{}"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Authorization": f"Token {DEV_TOKEN}",
        "Content-Type": "application/json;charset=utf-8",
        "Origin": "https://dev.arka360.com",
        "Connection": "keep-alive",
        "Referer": "https://dev.arka360.com/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
        "Priority": "u=0",
        "TE": "trailers",
    }

    response = requests.request("PATCH", url, headers=headers, data=payload, verify=False)
    print("advance update", response)
    # print(response.text)


# Function to save project details via API after price confirmation
def save_price_details(state):
    import requests
    calculate_genration_message = calculate_genration_chain.run({})
    
    price = state["price"]
    project_details = state["project_details"]
    design_id = state["design_id"]

    save_advanced_price(state)

    print("design_id", design_id)

    url = f"https://98.70.40.35:8006/api/designs/{design_id}/financial/"

    payload = {}
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Authorization': f"Token {DEV_TOKEN}",
        'Origin': 'https://dev.arka360.com',
        'Connection': 'keep-alive',
        'Referer': 'https://dev.arka360.com/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'cross-site',
        'TE': 'trailers'
    }

    get_fianicnal_response = requests.request("GET", url, headers=headers, data=payload, verify=False)
   

    json_response_id = get_fianicnal_response.json().get("pricing")[0]["id"]

    url = f"https://98.70.40.35:8006/api/financial/pricing/{json_response_id}/"

    payload = json.dumps(
        {
            "absolute_price": None,
            "price_per_watt": str(price),
            "price_per_kw": None,
            "pricing_system_type": "default_pricing",
        }
    )
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Authorization": f"Token {DEV_TOKEN}",
        "Content-Type": "application/json;charset=utf-8",
        "Origin": "https://dev.arka360.com",
        "Connection": "keep-alive",
        "Referer": "https://dev.arka360.com/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
        "TE": "trailers",
    }

    response = requests.request("PATCH", url, headers=headers, data=payload, verify=False)
    

    url = f"https://98.70.40.35:8006/api/designs/{design_id}/calculate/"

    payload = {}
    headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:141.0) Gecko/20100101 Firefox/141.0',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Authorization': f'Token {DEV_TOKEN}',
    'Origin': 'https://dev.arka360.com',
    'Connection': 'keep-alive',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-site',
    'TE': 'trailers'
    }

    response = requests.request("GET", url, headers=headers, data=payload,verify=False)

    system_price = response.json().get("system_price")
    state["final_price"] = round(system_price,1)

    return {

        "state": state,
        "message": calculate_genration_message,
        "wait_for_input": False,
        "next_step": "calculate_generation"
    }

# Extract by type
def get_component(components, component_type, use_short=False):
    for comp in components:
        if component_type in comp["types"]:
            return comp["short_name"] if use_short else comp["long_name"]
    return None


def get_address_details(address):
    api_key = "AIzaSyCRKem7aP2ORcLP9jmBSIADnrmgxzQNWEg"
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={api_key}"

    response = requests.get(url)
    data = response.json()

    if data["status"] == "OK":
       
        location = data["results"][0]["geometry"]["location"]
        result = data["results"][0]
        # final_result = get_details_from_google_maps_result(location)
        street_number = get_component(result["address_components"], "street_number")
        route = get_component(result["address_components"], "route")
        city = get_component(result["address_components"], "locality")
        state = get_component(result["address_components"], "administrative_area_level_1")
        country = get_component(result["address_components"], "country")
        postal_code = get_component(result["address_components"], "postal_code")
        country_code = get_component(result["address_components"], "country", True)
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~", country_code, postal_code, state, country, city)
        return location["lat"], location["lng"], country_code, postal_code, state, country, city
        
    else:
        return None, None


def call_create_project_api(state):
    project_details = state["project_details"]

    url = "https://98.70.40.35:8006/api/ai/create_project/"

    latitude, longitude, _, _, _, _, _ = get_address_details(project_details["address"])

    project_details["name"] = project_details["project_name"]
    project_details["latitude"] = latitude
    project_details["longitude"] = longitude
    project_details["token"] = DEV_TOKEN
    clean_data = {k: v for k, v in project_details.items() if v != "null"}
    clean_data["zoom"] = 20
    print("clean data",clean_data)
    payload = json.dumps({"payload_details": clean_data})
    print("payload", payload)

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Authorization": f"Token {DEV_TOKEN}",
        "Content-Type": "application/json;charset=utf-8",
        "Origin": "https://dev.arka360.com",
        "Connection": "keep-alive",
        "Referer": "https://dev.arka360.com/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
        "Priority": "u=0",
        "TE": "trailers",
    }

    response = requests.request(
        "POST", url, headers=headers, data=payload, verify=False
    )
    print("Status Code:", response.status_code)
    print("Response Text:", response)

    response_data = response.json()
    if response_data:
        state["project_details"]["project_id"] = response_data.get("project_id")
        state["project_details"]["project_consumption_id"] = response_data.get(
            "project_consumption_id"
        )
        state["latitude"] = latitude
        state["longitude"] = longitude
        state["is_genability_enabled"] = True
        state["country_id"] = response_data.get("country_id")
        state["currency_symbol"] = "$" if response_data.get("country_id") != 91 else "Rs."

        return {"state": state, "next_step": "update_project_consumption"}

def call_create_lead_api(state):
    import requests

    url = "https://98.70.40.35:8006/api/ai/create_lead/"
    project_details = state["project_details"]

   

    latitude, longitude, country_code, postal_code, state_name, country, city = get_address_details(project_details["address"])

    project_details["name"] = project_details["lead_name"]
    project_details["latitude"] = latitude
    project_details["longitude"] = longitude
    project_details["token"] = DEV_TOKEN
    project_details["zoom"] = 20
    project_details["project_type"] = "residential"
    project_details["email"] = project_details["lead_email"]
    # Combine project_details + payload["payload_details"] into one flat dictionary
    payload = json.dumps({"payload_details":{
        **project_details,
        **{
           
            "country_code": country_code,
            "latitude": project_details.get("latitude"),
            "longitude": project_details.get("longitude"),
            "zoom": 20,
            "pincode": postal_code,
            "state": state_name,
            "county": country,
            "city": city,
        }
    }
    })
   

    headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Authorization': f'Token {DEV_TOKEN}',
    'Content-Type': 'application/json;charset=utf-8',
    'Origin': 'https://dev.arka360.com',
    'Connection': 'keep-alive',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-site',
    'Priority': 'u=0'
    }

    response = requests.request("POST", url, headers=headers, data=payload,verify=False)

    print(response.text)
    print("Status Code:", response.status_code)
    print("Response Text:", response)
    print('------------------------------------------------------------------', state, '----------------------------------------------------------------------------------------')
    response_data = response.json()
    if response_data:
        state["project_details"]["lead_id"] = response_data.get("lead_id")
        state["project_details"]["project_id"] = response_data.get("project_id")
        state["project_details"]["project_consumption_id"] = response_data.get(
            "project_consumption_id"
        )
        state["latitude"] = latitude
        state["longitude"] = longitude
        state["is_genability_enabled"] = True
        state["country_id"] = response_data.get("country_id")
        state["currency_symbol"] = "$" if response_data.get("country_id") != 91 else "Rs."

        return {"state": state, "next_step": "update_project_consumption"}

    

def select_monthly_details_node(state):
    month_consumption_details = state.get("month_consumption_details") 
    file_upload = state.get("file")
    user_input = True if (month_consumption_details or file_upload)  else False
    print("file upload",file_upload)
    print("month consumption",month_consumption_details)
    print("user_input",user_input)
    print("type",type(user_input))
    if not state.get("consumption_type"):
        if not user_input:
            return {
                "state": state,
                "message": "Great! Please enter your Average Monthly Energy (kWh) or Upload a File",
                "next_step": "select_monthly_details_node",
                "message_type": "dropdown",
                "is_document_rejected":True
                
            }
        else:
            
            state["consumption_type"] = "energy"
           

    if (not state.get("consumption_value")) and state.get("consumption_type"):
        print("state", state)
        if not user_input:
            if state["consumption_type"] == "energy":
                return {
                    "state": state,
                    "message": "Got it! Please enter your  monthly usage consumption (in kWh or Upload a file",
                    "next_step": "select_monthly_details_node",
                   "message_type": "dropdown",
                   "is_document_rejected":True
            }
                
           
        else:
           
                
                if file_upload:
                    print("yess file upload")
                    try :
                        print("yessss")
                        from utils import extract_electricity_bill
                        import base64
                        import io
                        base64_string = state.get("file").get("data") 
                       
                        from PyPDF2 import PdfReader

                        file_bytes = base64.b64decode(base64_string)
                        pdf_reader = PdfReader(io.BytesIO(file_bytes))
                        text_content = "\n".join(page.extract_text() or "" for page in pdf_reader.pages)
                        month_consumption = extract_electricity_bill(text_content)
                      
                        month_consumption = extract_json_from_block(month_consumption)
                       
                        consumption_month = month_consumption.get("month")
                        consumption_value = month_consumption.get("amount")
                        #TODO The file doesn’t look correct. Please enter your monthly electricity usage (in kWh) or upload a valid PDF bill again."
                        if (not consumption_month )or (not consumption_value ):
                            
                            return {
                            "state": state,
                            "message": "The file doesn't seem correct . Please enter your  monthly usage consumption (in kWh) or Upload a file.",
                            "next_step": "select_monthly_details_node",
                            "is_document_rejected":True,
                            "message_type": "dropdown"
                    }
                       
                    except:
                        return {
                            "state": state,
                            "message": "The file doesn't seem correct . Please enter your  monthly usage consumption (in kWh) or Upload a file",
                            "next_step": "select_monthly_details_node",
                            "is_document_rejected":True,
                            "message_type": "dropdown"
                    }
                elif month_consumption_details:
                    try:
                        consumption_month = month_consumption_details.get("month")
                        consumption_value = float(month_consumption_details.get("usage"))
                    
                    except ValueError:
                        # return {
                        #     "state": state,
                        #     "message": "Please enter a valid number for your usage.",
                        #     "next_step": "select_monthly_details_node"
                        # }
                        return {
                        
                        "state": state,
                        "message": "Please enter a valid number for your usage.",
                            "next_step": "select_monthly_details_node",
                            "is_document_rejected":True,
                    
                        "message_type": "dropdown"
                    }
                    
                    
               
                state["consumption_month"]= consumption_month
                state["consumption_value"] = consumption_value
                state["consumption_unit"] = "kWh"
                state["user_input"] = None
                if state.get("file"):
                    state["file"]["data"]= None
                return {
                    "state": state,
                    "message": "Thanks! We’ve noted your monthly usage.",
                    "wait_for_input": False,
                    "next_step": "save_monthly_consumption"
                }

   


def save_consumption_type(state):
    project_consumption_id = state["project_details"]["project_consumption_id"]
    print("projectconsumotionid", project_consumption_id)
    url = f"https://98.70.40.35:8006/api/project-consumption-details/{project_consumption_id}/"

    payload = json.dumps({"consumption_input_type": "Monthly Electricity Bill"})
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Authorization":f"Token {DEV_TOKEN}",
        "Content-Type": "application/json;charset=utf-8",
        "Origin": "https://dev.arka360.com",
        "Connection": "keep-alive",
        "Referer": "https://dev.arka360.com/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
        "Priority": "u=0",
        "TE": "trailers",
    }
    print("url url", url)
    response = requests.request("PATCH", url, headers=headers, data=payload, verify=False)

    return response


def save_monthly_consumption(state):
    design_message = design_create_chain.run({})

    project_id = state["project_details"]["project_id"]
    consumption_type = state["consumption_type"]
    consumption_input = state["consumption_value"]
    is_genability_enabled = state["is_genability_enabled"]
    response_save = save_consumption_type(state)
    genability_mode = False
    if is_genability_enabled:
        genability_mode = True
        
    url = f"https://98.70.40.35:8006/api/projects/{project_id}/project_consumption_calculation/"
    

   
    if genability_mode:
        #TODO month input
        month_to_index = {
            "January": 1, "February": 2, "March": 3, "April": 4,
            "May": 5, "June": 6, "July": 7, "August": 8,
            "September": 9, "October": 10, "November": 11, "December": 12
        }

        month_str = state["consumption_month"]
        month_index = month_to_index.get(month_str)-1

        # print(month_index)
        # month_index = datetime.now().month  
        consumption_input_arr = [0,0,0,0,0,0,0,0,0,0,0,0]
        user_input_values_arr = [None,None,None,None,None,None,None,None,None,None,None,None]
        consumption_input_arr[month_index] = consumption_input
        user_input_values_arr[month_index]=str(consumption_input)
        payload = json.dumps({"consumption_input":consumption_input_arr,
                   "consumption_profile":"Up to 12 Months Energy Usage (kWh)",
                   "genability_mode":True,
                   "user_input_values":user_input_values_arr
                   })
    else:
       
        month = state["consumption_month"] 

        predicted_consumption = predict_annual_consumption(month,consumption_input)
        monthly_predictions = [value for month,value in predicted_consumption["monthly_predictions"].items()]
        
        #annual which one to use annual predicted need to pass
        # payload = json.dumps(
        #     {
        #         "consumption_input": [consumption_input],
        #         "consumption_profile": (
        #             "Average Monthly Energy (kWh)"
        #             if consumption_type == "energy"
        #             else "Average Monthly Pre-tax bill ($)"
        #         ),
        #         "genability_mode": genability_mode,
        #         "month_index": 0,
        #         "user_input_values": monthly_predictions,
        #     }
        # )
        payload = json.dumps(
            {
                "consumption_input": [consumption_input],
                "consumption_profile": "All 12 Months Energy Usage (kWh)",
                "genability_mode": genability_mode,
                "month_index": 0,
                "user_input_values": monthly_predictions,
            }
        )
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Authorization": f"Token {DEV_TOKEN}",
        "Content-Type": "application/json;charset=utf-8",
        "Origin": "https://dev.arka360.com",
        "Connection": "keep-alive",
        "Referer": "https://dev.arka360.com/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
        "Priority": "u=0",
        "TE": "trailers",
    }

    response = requests.request("PATCH", url, headers=headers, data=payload, verify=False)
    
    response_json = response.json()
    if genability_mode:
        state["tariff_details"]["post_solar_utility_provider_name"]=response_json.get("utility_tariff_details").get("post_solar_utility_provider_name")
        state["tariff_details"]["post_solar_utility_rate_name"] = response_json.get("utility_tariff_details").get("post_solar_utility_rate_name")
    state["average_monthly_consumption"] = round(response_json.get("average_monthly_consumption"),3)
    state["annual_consumption"] = round(response_json.get("annual_consumption"),3)
    return {
        "state": state,
        "message": design_message,
        "wait_for_input": False,

        "next_step": "create_design"
    }


def create_design(state):
    url = "https://98.70.40.35:8006/api/designs/"
    project_id = state["project_details"]["project_id"]
    payload = json.dumps(
        {
            "name": "Design 1",
            "project": project_id,
            "created_by": 2303,
            "modified_by": 2303,
            "design_profile_id": 1414,
            "design_type": {},
            "system_type": "default_design",
            "map_data": {
                "latitude_for_map": float(state["project_details"]["latitude"]),
                "longitude_for_map": float(state["project_details"]["longitude"]),
                "zoomLevel": 20,
                "dimensions": 512,
                "hasOldImage": False,
                "groundMapImageVisible": True,
                "imgDimension": -1,
            },
        }
    )
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Authorization": f"Token {DEV_TOKEN}",
        "Content-Type": "application/json;charset=utf-8",
        "Origin": "https://dev.arka360.com",
        "Connection": "keep-alive",
        "Referer": "https://dev.arka360.com/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
        "Priority": "u=0",
        "TE": "trailers",
    }

    response = requests.request("POST", url, headers=headers, data=payload, verify=False)
    response_data = response.json()
    design_id = response_data["id"]
    state["design_id"] = response_data["id"]

    # url = "https://devapi.arka360.com/api/design-map-images/"

    # payload = {"url":"https://maps.googleapis.com/maps/api/staticmap?center=37.5669353,-122.0713424&scale=2&zoom=20&maptype=satellite&size=512x512&key=AIzaSyCRKem7aP2ORcLP9jmBSIADnrmgxzQNWEg&signature=stOkzBvbtKXXBvdGT5f89eX7ziw=",
    #            "rotation":0,"scale":0,"design":design_id,"source":"google_maps","zoom":20,"is_visible":True}
    # headers = {
    # 'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:138.0) Gecko/20100101 Firefox/138.0',
    # 'Accept': 'application/json, text/plain, */*',
    # 'Accept-Language': 'en-US,en;q=0.5',
    # 'Accept-Encoding': 'gzip, deflate, br, zstd',
    # 'Authorization': 'Token cb62796f1217974efff3a5775bd4d729501f189e',
    # 'Content-Type': 'application/json;charset=utf-8',
    # 'Origin': 'https://dev.arka360.com',
    # 'Connection': 'keep-alive',
    # 'Sec-Fetch-Dest': 'empty',
    # 'Sec-Fetch-Mode': 'cors',
    # 'Sec-Fetch-Site': 'same-site',
    # 'TE': 'trailers'
    # }

    # response = requests.request("POST", url, headers=headers, data=payload)

    # print(response.text)

    return {
        "state": state,

        "wait_for_input": False,
        "next_step": "save_design"
    }


def save_design(state):
    design_id = state["design_id"]

   

    if design_id:
        url = "https://98.70.40.35:8006/api/ai/get_reference_id/"
        design_id = state.get("design_id")

        payload = json.dumps({"design_id": design_id})
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Authorization': f"Token {DEV_TOKEN}",
            'Content-Type': 'application/json;charset=utf-8',
            'Origin': 'https://dev.arka360.com',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site',
            'TE': 'trailers'
        }

        response = requests.request("GET", url, headers=headers, data=payload, verify=False)
        print("response refence id", response)
        reference_id = response.json().get("reference_id")
        print("refernce_id", reference_id)
        
        response = call_design_api_async(reference_id,state["average_monthly_consumption"]
                                         )


       
        
        
    url = f"https://98.70.40.35:8006/api/designs/{design_id}/details/"

    payload = {}
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Authorization": f"Token {DEV_TOKEN}",
        "Origin": "https://dev.arka360.com",
        "Connection": "keep-alive",
        "Referer": "https://dev.arka360.com/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
        "TE": "trailers",
    }

    response = requests.request("GET", url, headers=headers, data=payload, verify=False)
    
    state["nameplate_dc_size"]= response.json().get("versions").get("summary").get("nameplate_dc_size")
    
    
    # import time

    # if response_text["versions"].get("scene"):

    #     state["scene_waiting"] = False
    # else:
    #     state["scene_waiting"] = True
    #     time.sleep(10)
    message = (
f"I'm assuming the base system price as {state['currency_symbol']}{assumed_price:,} per Watt. "
"Would you like to keep this value?"
)

    # price_details = f"Saving the base system price to  {state['currency_symbol']} 1000 per kW. This price will be used as the default cost for calculating the total price based on system size and roof design."
    # #TODO excluding tax this is 
    
    return {
    "message": message,
    "state": state,
    "next_step": "handle_price_confirmation",
    "options":["Yes, continue","No, I want to change this"],
    "message_type":"base_system_price_selection",
    "wait_for_input": True
    }
    
def handle_price_confirmation(state):
    user_input = state.get("user_input")
    # user_input = user_input.strip().lower()
    if user_input in ["No, I want to change this"]:
        message = "Sure! Please enter your preferred price per Watt."
        return {
        "message": message,
        "state": state,
        "next_step": "get_custom_price",
        "wait_for_input": True
        }
    elif user_input in ["Yes, continue"]:
    # Proceed with assumed price and ask for next input
        price_details = "Saving the base system price ."
        state["price"] = 4.5
    #TODO excluding tax this is 
        return {
            "state": state,
            "message": price_details,
            "wait_for_input": False,
            "next_step": "save_price_details"
        }

    else:
        message = f"Please select  'yes' or 'no'. Would you like to keep the assumed price of  {state['currency_symbol']}{assumed_price:,} per Watt.?"
        return {
        "message": message,
        "state": state,
        "options":["Yes, continue","No, I want to change this"],
        "message_type":"base_system_price_selection",
        "next_step": "handle_price_confirmation",
        "wait_for_input": True
        }

def get_custom_price(state):
    try:
        user_input = state.get("user_input")
        price = float(user_input)
        state["price"] = price
        message = f"Thanks! We'll use {state['currency_symbol']}{price:,.2f} per Watt."
        
         
        #TODO excluding tax this is 
        return {
            "state": state,
            "message": message,
            "wait_for_input": False,
            "next_step": "save_price_details"
        }

    except ValueError:
        return {
        "message": "That doesn't look like a valid price.",
        "state": state,
        "next_step": "get_custom_price",
        "wait_for_input": True
        }
    #     return {
    #     "state": state,
    #     "message": price_details,
    #     "wait_for_input": False,
    #     "next_step": "save_price_details"
    # }


def calculate_generation(state):
    design_id = state["design_id"]

    url = f"https://98.70.40.35:8006/api/designs/{design_id}/details/"

    payload = {}
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Authorization": f"Token {DEV_TOKEN}",
        "Origin": "https://dev.arka360.com",
        "Connection": "keep-alive",
        "Referer": "https://dev.arka360.com/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
        "TE": "trailers",
    }

    response = requests.request("GET", url, headers=headers, data=payload, verify=False)
    response_text = response.json()
    # print("response text",response_text)
    if response_text["versions"].get("scene"):
        token = DEV_TOKEN

        url = "https://integration.arka360.com/webhook/dev/generation"

        payload = json.dumps({"design_id": design_id, "token": token})
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Authorization": f"Token {DEV_TOKEN}",
            "Content-Type": "application/json;charset=utf-8",
            "Origin": "https://dev.arka360.com",
            "Connection": "keep-alive",
            "Referer": "https://dev.arka360.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site",
            "Priority": "u=0",
            "TE": "trailers",
        }

        response = requests.request("POST", url, headers=headers, data=payload, verify=False)
        response = response.json() 
    state["annual_generation"] = round(response[0]['annual_generation'],3)
    state["offset"]= response[0]["offset"]
    return {
        "state": state,
        "message": "Now  Generating Proposal For you..",
        "wait_for_input": False,
        "next_step": "generate_proposal"
    }



def generate_proposal(state):
    url = "https://98.70.40.35:8006/api/ai/generate_proposal/"
    design_id = state.get("design_id")

    payload = json.dumps({"design_id": design_id})

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Authorization': f"Token {DEV_TOKEN}",
        'Content-Type': 'application/json;charset=utf-8',
        'Origin': 'https://dev.arka360.com',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'cross-site',
        'TE': 'trailers'
    }

    response = requests.request("POST", url, headers=headers, data=payload, verify=False)
    print("response proposal", response)
    reference_id = response.json().get("reference_id")

    return {
        "state": state,
        "is_completed": True,
        "message": f"https://dev.arka360.com/documentProposalRef/{reference_id}/"
    }

def update_project_consumption(state):
    project_details = state.get("project_details", {})
    project_id = project_details.get("project_id")
    country_id = state.get("country_id")
    uses_genability = state.get("is_genability_enabled", False)
    project_consumption_id = project_details.get("project_consumption_id")
    if country_id ==52:
        if uses_genability:
            # Use Genability and continue flow
            message = "Thanks for setting up your solar project! To get started on your custom proposal, we’ll need your utility rate. We’ve selected your rate using Genability."
            import requests

            url = f"https://devapi.arka360.com/api/project-consumption-details/{project_consumption_id}/genability/"

            payload = {}
            headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Authorization': f'Token {DEV_TOKEN}',
            'Origin': 'https://dev.arka360.com',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'Priority': 'u=0',
            'TE': 'trailers'
            }

            response = requests.request("GET", url, headers=headers, data=payload)
            response_json = response.json()
            state["tariff_details"]["utility_provider_name"] = response_json.get("tariff_details").get("utility_provider_name")
            state["tariff_details"]["utility_rate_name"] = response_json.get('tariff_details').get("utility_rate_name")
            state["tariff_details"]["annual_escalation_rate"] = ANNUAL_ESCALATION_RATE 
            return {
                "message": message,
                "state": state,
                "next_step": "ask_for_consumption_units",
                "wait_for_input": False
            }
        else:
            # Fall back to custom tariff
            state["custom_tariff"]["net_metering"] = True
            message = (
                "Thanks for setting up your solar project! To get started on your custom proposal, we’ll need your utility rate. "
                "Let’s proceed with a custom tariff setup.We’ll use Net Metering and Annual Escalation Rate 3.5 by default .\n\n"
                f"Please enter your unit price (cost in {state['currency_symbol']} per kWh)\n"
                
            )
           
           
            return {
                "message": message,
                "state": state,
                "next_step": "get_unit_price_for_custom_tariff",
                "wait_for_input": True
            }
    else:
         # Fall back to custom tariff
            state["custom_tariff"]["net_metering"] = True
            
            message = (
                "Thanks for setting up your solar project! To get started on your custom proposal, we’ll need your utility rate. "
                "Let’s proceed with a custom tariff setup.We’ll use Net Metering and Annual Escalation Rate 3.5 by default .\n\n"
                f"Please enter your unit price (cost in {state['currency_symbol']} per kWh)\n"
                
            )
           
            return {
                "message": message,
                "state": state,
                "next_step": "get_unit_price_for_custom_tariff",
                "wait_for_input": True
            }
        


def get_unit_price_for_custom_tariff(state):
    user_input = state.get("user_input")
    project_details = state.get("project_details", {})
    project_id = project_details.get("project_id")
    project_consumption_id = project_details.get("project_consumption_id")
    print("gettariffuunitprice",state)
    try:
        unit_price = float(user_input)
       

        state["custom_tariff"]["unit_price"] = unit_price
        state["custom_tariff"]["annual_escalation_rate"] = ANNUAL_ESCALATION_RATE 
        
        import requests

        url = f"https://devapi.arka360.com/api/project-consumption-details/{project_consumption_id}/"
        print("uel",url)
        payload = json.dumps({
            "is_utility_rate_added": True,
            "utility_tariff_details": {
                "source": "default",
                "post_solar_source": "default"
            },
            "project": project_id,
            "average_price_per_unit": unit_price,
            "tariff_escalation_rate": "3.50",
            "average_export_price_per_unit": 0,
            "metering_type": "Net metering",
            "utility_details": {
                "lseId": "",
                "postLseId": "",
                "isPostSolarAvailable": True
            },
            "type_of_rate": "flat",
            "zero_export_enabled": False,
            "full_export_enabled": False
            })
        print("consumptionpayload",payload)
        print("yes",f'Token {DEV_TOKEN}',)
        headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:141.0) Gecko/20100101 Firefox/141.0',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Authorization': f'Token {DEV_TOKEN}',
        'Content-Type': 'application/json;charset=utf-8',
        'Origin': 'https://dev.arka360.com',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'Priority': 'u=0',
        'TE': 'trailers'
        }

        response = requests.request("PATCH", url, headers=headers, data=payload)

        print(response)

        message = (
            f"Thanks! You’ve entered {state['currency_symbol']}{unit_price:.2f}/kWh with net metering.\n\n"
        )
        return {
            "message": message,
            "state": state,
            "next_step": "ask_for_consumption_units",
            "wait_for_input": False
        }

    except ValueError:
        return {
            "message": "That doesn’t look like a valid unit price. Please enter a number like 0.12.",
            "state": state,
            "next_step": "get_unit_price_for_custom_tariff",
            "wait_for_input": True
        }

def ask_for_consumption_units(state):
    message = (
        "Please Enter Your Monthly Energy(kwh)."
        
    )
    return {
        "message": message,
        "state": state,
        "next_step": "select_monthly_details_node",
        "wait_for_input": True,
        "message_type": "dropdown"
    }




