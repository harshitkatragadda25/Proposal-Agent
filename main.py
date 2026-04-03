import os
from langchain_community.llms import Ollama
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from uuid import uuid4
import json
import streamlit as st
from langgraph.graph import StateGraph, END
import uvicorn 
# from database_handler import DatabaseHandler
from typing import List, Tuple, Dict
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any
import requests
import chatbot
import time
from database_handler import DatabaseHandler


app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or "*" for all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]

)



# OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
# llm = Ollama(
#     base_url=OLLAMA_BASE_URL,
#     model="llama2"  # Replace with your actual model
# )

# print(f"Connecting to Ollama at: {OLLAMA_BASE_URL}")
# Dictionary to store memory chains per session
user_sessions = {}
SESSION_STORE = {} 
DESIGN_STUDIO_APP_URL = "https://devapi.arka360.com/"
class OllamaResponse:
    def __init__(self, model_name="llama3"):
        ''' If No Model is Specified, Ollama will assume Meta-Llama-3.1-8B '''
        self.model_name = model_name
        self.session_id = None
        self.query = None
        self.response = None
        self.memory_chain = []
        self.wait_for_input=None
        self.is_proposal_link = False
        self.address_confirmed = None
        self.options = []
        self.message_type="text"
        self.month_consumption_details = None
        self.file={}
       

    def set_query(self, query,session_id,address_confirmed,month_consumption_details,file):
        ''' Get Query from Client, Set Query for Further Processing '''
        self.query = query
        self.session_id = session_id
        self.address_confirmed = address_confirmed
        self.month_consumption_details = month_consumption_details
        self.file = file
        self.memory_chain.append({"role": "user", "content": query})

    def get_response_from_ollama(self):
        
            session_id = self.session_id
           
            
            state = SESSION_STORE.get(session_id, {
            "project_details": None,
            "missing_fields": None,
            "confirmed_data": {},
            "final_price": None,
            "price_update": False,
            "consumption_value": None,
            "consumption_type": None,
            "design_id": None,
            "project_consumption_id": None,
            "address_confirmed": self.address_confirmed,
            "is_proposal_link":False,
            "tariff_details":{},
            "custom_tariff":{},
            "currency_symbol":None,
            "price":None,
            
        })  
             
            # state = SESSION_STORE.get(session_id, {'project_details': {'project_name': 'testprjectnew', 'address': '5067 Sloan Way, Union City, CA 94587, USA', 'client_name': 'tata', 'client_number': 'null', 'client_email': 'null', 'name': 'testprjectnew', 'latitude': 37.5669353, 'longitude': -122.0713424, 'token': 'cb62796f1217974efff3a5775bd4d729501f189e', 'project_id': 112207, 'project_consumption_id': 112156}, 'missing_fields': [], 'confirmed_data': {}, 'final_price': 1000, 'price_update': False, 'consumption_value': 20.0, 'consumption_type': 'energy', 'design_id': 80084, 'project_consumption_id': None, 'address_confirmed': False, 'user_input': '__auto__', 'consumption_unit': 'kWh'})  
            next_step = SESSION_STORE.get(session_id + "_next_step",[])
            print("next_step",next_step)
            if not next_step:
                state["file"]= self.file
                result = chatbot.onboarding_details(state)
                state = result["state"]
                self.response = result["message"]
                self.wait_for_input = True
                next_step.append(result["next_step"])
                SESSION_STORE[self.session_id] = state
                SESSION_STORE[self.session_id + "_next_step"] = next_step
            else:
            
                
                while True:
                    
                    func_name = next_step[0].strip('"')
                    state["user_input"] = self.query
                    state["month_consumption_details"] = self.month_consumption_details
                    state["file"]= self.file
                    func = getattr(chatbot, func_name)
                    if not state["address_confirmed"]:
                        state["address_confirmed"]= self.address_confirmed
                    
                    result = func(state)



                    
                    if result.get("is_completed") == True:
                        
                        self.response = result["message"]
                        self.wait_for_input = True
                        state["user_input"] = None 
                        next_step = [] 
                        state["is_proposal_link"] =True
                        self.is_proposal_link = True
                        break

                    
                    if result.get("message"):
                       
                        state = result["state"]
                        self.response = result["message"]
                        self.wait_for_input = result.get("wait_for_input",True)
                        self.options = result["options"] if result.get("options") else []
                        self.message_type = result.get("message_type","text")
                        state["is_document_rejected"]= result.get("is_document_rejected",False)
                        
                        next_step[0] = result["next_step"]
                        break

                    else:
                        
                        state = result["state"]
                        self.response = ""
                        next_step[0] = result["next_step"]


                    
                    state = result["state"]
                    next_step[0] = result["next_step"]
                    
                    # self.options = result["options"] if result.get("options") else []


                    SESSION_STORE[self.session_id] = state
                    SESSION_STORE[self.session_id + "_next_step"] = next_step


        
            
               

           





          
           
            self.memory_chain.append({"role": "assistant", "content": self.response, "state": state})



def get_chatbot(session_id: str):
    ''' Retrieves chatbot for a given session or creates a new one '''
    if session_id not in user_sessions:
        user_sessions[session_id] = OllamaResponse()
    return user_sessions[session_id]

# ✅ NEW: Pydantic model to parse JSON
class ChatRequest(BaseModel):
    query: str
    session_id: str = None
    address_confirmed :bool = None# Optional
    month_consumption_details:dict = None
    file :dict=None

@app.post("/api/chat/")
def chat(req: ChatRequest):
    print("req",req)
    session_id = req.session_id or str(uuid4())
    chatbot = get_chatbot(session_id)
    chatbot.set_query(req.query,session_id,req.address_confirmed,req.month_consumption_details,req.file)
    chatbot.get_response_from_ollama()
    
    if chatbot.memory_chain:
        last_state = chatbot.memory_chain[-1].get("state")
    else:
        last_state = None
    print("response",chatbot.response)
    return {"response": chatbot.response, "session_id": session_id,"wait_for_input":chatbot.wait_for_input, "state": last_state,"is_proposal_link":last_state.get("is_proposal_link"),"options":chatbot.options,"message_type":chatbot.message_type,"is_document_rejected":last_state.get("is_document_rejected")}


@app.get("/api/chat/design_image/")
def design_image(design_id: int):
    #TODO not foundd error is not coming 
    url = 'https://98.70.40.35:8006/api/ai/get_design_image/'
    headers = {
        'Authorization': f'Token {chatbot.DEV_TOKEN}',
        'Content-Type': 'application/json'
    }
    data = {
        'design_id': design_id
    }
    try:
        response = requests.get(url, headers=headers, json=data, verify=False)
        response.raise_for_status()  # raise error for non-200 responses
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Upstream error: {str(e)}")

    try:
        return response.json()
    except ValueError:
        raise HTTPException(status_code=500, detail="Invalid JSON from upstream")







# --- Models ---

class ActionModel(BaseModel):
    action: str
    options: Dict[str, Any]

class ChatbotResponse(BaseModel):
    message: str
    action: str
    options : Dict[str, Any]

class ChatbotRequest(BaseModel):
    message: str
    






def detect_intents(message: str) -> List[Tuple[str, Dict]]:
    intents_with_options = []

    if "panel" in message:
        intents_with_options.append(("updatePanel", {
            "panel_name": "SunPro 410W",
            "size": "5kw"
        }))
    if "inverter" in message:
        intents_with_options.append(("updateInverter", {
            "inv_name": "SMA Sunny Boy 5.0",
            "size": "20"
        }))
    if "tariff" in message or "rate" in message:
        intents_with_options.append(("updateTariff", {
            "rate": 6.5,
            "id": "tariff-xyz"
        }))
    if "consumption" in message or "units" in message:
        intents_with_options.append(("updateConsumption", {
            "consumption": 23
        }))
    if "create design" in message:
        intents_with_options.append(("designCreate", {
            "consumption": 23
        }))
    
    if "update price" in message:
        intents_with_options.append(("updatePrice", {
            "price": 30,
            "currency_symbol":"$"
        }))
        # Add sidebar update as a companion action
        intents_with_options.append(("updateSidebar", {
            "systemsize": 34,
            "unit":"kwh"
        }))
    if "map" in message or "location" in message:
        intents_with_options.append(("mapUpdate", {
            "zoom": 20,
            "address": "5064 Sloan Way, Union City, CA 94587, USA",
            "latitude": "27.176670099999999053",
            "longitude": "78.008074499999992213"
        }))
    if "update_address" in message:
        intents_with_options.append(("updateAdd", {
            "address": "5064 Sloan Way, Union City, CA 94587, USA",
            "latitude": "27.176670099999999053",
            "longitude": "78.008074499999992213"
        }))
        intents_with_options.append(("updateSidebar", {
            "address": "5064 Sloan Way, Union City, CA 94587, USA",
            "latitude": "27.176670099999999053",
            "longitude": "78.008074499999992213"
        }))
    if "follow_up" in message:
        intents_with_options.append(("showList", {
                "0":"Modify Inverter", "1":"Modify Panel"
            }))
    if "next_request" in message:
        intents_with_options.append(("await", {}))
    if "create lead" in message:
        intents_with_options.append(("updateSidebar", {
            "lead_name": "Nirmal",
            
        }))
        
    if "systemsize" in message:
        intents_with_options.append(("updateSystemsize", {
            "systemsize": "5.5",
            "unit":"kwh"
            
        }))
    if "project" in message:
        intents_with_options.append(("updateSidebar", {
            "project_name": "New Project",
            "client_name": "John Doe"
        }))
    if "generation" in message or "estimate generation" in message:
        intents_with_options.append(("updateSidebar", {
         "specific_generation":8.764 ,
         "unit":"kWp"
        }))
 
    if "proposal" in message or "generate proposal" in message:
        intents_with_options.append(("updateSidebar", {
        "proposal_link": "https://solar.example.com/proposals/abc123",
        
        }))
    if "hi" in message:
        intents_with_options.append(("onboardUser", {
    
        
        }))
        
    if not intents_with_options:
        intents_with_options.append(("unknown", {}))
    
    return intents_with_options
#TODO tariff
#TODO design image
def generate_actions(intent_data: List[Tuple[str, Dict]]) -> ChatbotResponse:
    actions = []
    messages = []

    for intent, options in intent_data:
        if intent == "updatePanel":
            messages.append("Updating the solar panel details.")
            actions.append(ActionModel(action="updatePanel", options=options))
        elif intent == "updateInverter":
            messages.append("Updated the inverter.")
            actions.append(ActionModel(action="updateInverter", options=options))
        elif intent == "updateTariff":
            messages.append("Tariff updated.")
            actions.append(ActionModel(action="updateTariff", options=options))
        elif intent == "updateConsumption":
            messages.append("Monthly consumption received.")
            actions.append(ActionModel(action="updateConsumption", options=options))
        elif intent == "designCreate":
            messages.append("Generating your solar design.")
            print("options1",options)
            actions.append(ActionModel(action="designCreate", options=options))
        elif intent == "updateSidebar":
            messages.append("Sidebar updated.")
            print("options2",options)
            actions.append(ActionModel(action="updateSidebar", options=options))
        elif intent == "mapUpdate":
            messages.append("Map updated.")
            actions.append(ActionModel(action="mapUpdate", options=options))
        elif intent == "showList":
            messages.append("What changes would you like to make?")
            actions.append(ActionModel(action="showList", options=options))
        elif intent == "updatePrice":
            messages.append("Updating the Price.")
            actions.append(ActionModel(action="", options=options))
        elif intent == "createProject":
            messages.append("Project created.")
            actions.append(ActionModel(action="", options=options))
        elif intent == "updateAdd":
            messages.append("Show this Updated Address")
            actions.append(ActionModel(action="", options=options))
        elif intent == "generationEstimate":
            time.sleep(10)
            messages.append("We’ve estimated your solar energy generation based on your setup.")
            actions.append(ActionModel(action="generationEstimate", options=options))

        elif intent == "generateProposal":
            messages.append(f"Here’s your proposal: View Proposal")
            actions.append(ActionModel(action="generateProposal", options=options))
        elif intent == "onboardUser":
            messages.append("welcome to arka360, start creating your project and explore the magic.")
            
        else:
            messages.append("Sorry, I didn't get that.")
    
    response = []
    for index in range(len(messages)):
        action_model = actions[index] if index < len(actions) else None
        response.append(ChatbotResponse(
            message=messages[index],
            action=action_model.action if action_model else "",
            options=action_model.options if action_model else {}
        ))
    return response



# --- Main Endpoint ---

@app.post("/chatbot/respond", response_model=List[ChatbotResponse])
async def respond_to_message(req: ChatbotRequest):
    intents = detect_intents(req.message)
    responses = generate_actions(intents)
    return responses

@app.get("/api/chat/history/")
def get_chat_history():
    
    
    print("yess")
    db = DatabaseHandler()
    print("dv",db)
    history = db.get_chat_history()
    print("history",history)
    proposal_details= {"lead_name": None,
              "address":None,
              "weather":None,
            
            "base_price": None,
            "consumption_value": None,
            "consumption_type": None,
            "design_id": None,
            "project_consumption_id": None,
            "specific_generation":None,
            "system_size":None,
            "proposal_link":False,
            "tariff_details":{},
            "custom_tariff":{},
            "currency_symbol":None,
            "latitude":"",
            "longitude":"",
            
    }
    return {"history": history,"data":proposal_details}



if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001)
