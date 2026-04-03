import streamlit as st
import numpy as np
import pandas as pd
import time
import uuid
import requests
import streamlit.components.v1 as components
from streamlit_js_eval import streamlit_js_eval
import base64

import json

import socket

# deciding the paylod structire 
# context for that 
# and also resume back 
# address not correct  vlaidations we need to do
# 120% of annual consumption 
# kauhsla testing and let us knowwhat we cando 
# remove hello there 
# currency symbol form here also 
# basedon the review we can change

# Usage

host_ip = "216.48.181.189"
local_ip = "127.0.0.1"
server_port_number = "8000"
print("server port number",server_port_number)
server_ip_and_port = f"{local_ip}:{server_port_number}"





# CONSTANT
AI_PROCESS_TYPES = [
    ("FETCH_DESIGN_LINK", "fetch_design_link"),
    ("FETCH_LEAD_DETAILS", "fetch_lead_details"),
    ("FETCH_IMAGES", "fetch_images"),
    ("FETCH_DESIGN_OPTIONS", "fetch_design_options"),
    ("SELECT_LOCATION", "select_location"),
    ("OTHER", "other")
]
GOOGLE_MAPS_API_KEY = "AIzaSyCRKem7aP2ORcLP9jmBSIADnrmgxzQNWEg"
default_location = [28.6139, 77.2090]

AUTO_TRIGGER_TOKEN = "__auto__"

# states
# # Initialize session state
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "lead_details" not in st.session_state:
    st.session_state.lead_details = None

if "tariff" not in st.session_state:
    st.session_state.tariff = None

if "design" not in st.session_state:
    st.session_state.design = None

if "messages" not in st.session_state:
    st.session_state.messages = []

if "is_processing" not in st.session_state:
    st.session_state.is_processing = False

if "is_disabled" not in st.session_state:
    st.session_state.is_disabled = False

if "pending_input" not in st.session_state:
    st.session_state.pending_input = ""

if "mimic_user_input" not in st.session_state:
    st.session_state.mimic_user_input = None

if "user" not in st.session_state:
    st.session_state.user = {
        "name": "User"
    }
if "clicked_location" not in st.session_state:
    st.session_state.clicked_location = None

if "counter" not in st.session_state:
    st.session_state.counter = 0

if "sidebar_states" not in st.session_state:
    st.session_state.sidebar_states = None

if "active_design_id" not in st.session_state:
    st.session_state.active_design_id = None
    
if "manual_rerun" not in st.session_state:
    st.session_state.manual_rerun = False

if "user_selected_address" not in st.session_state:
    st.session_state.user_selected_address = None

if "show_google_map" not in st.session_state:
    st.session_state.show_google_map = False

if "show_location_selection_button" not in st.session_state:
    st.session_state.show_location_selection_button = False

if "is_location_button_shown" not in st.session_state:
    st.session_state.is_location_button_shown = False

if "show_helper_prompts" not in st.session_state:
    st.session_state.show_helper_prompts = True
    
if "address_confirmed" not in st.session_state:
    st.session_state.address_confirmed = False

if "is_confirm_address_shown" not in st.session_state:
    st.session_state.is_confirm_address_shown = False
    
if "address_confirmed_sent" not in st.session_state:
    st.session_state.address_confirmed_sent = None
    
if "month_consumption_details" not in st.session_state:
    st.session_state.month_consumption_details = None
    
if "is_file_upload_enabled" not in st.session_state:
    st.session_state.is_file_upload_enabled = False
    
if "uploaded_bill" not in st.session_state:
    st.session_state.uploaded_bill = None

# FONT & STYLING
st.markdown("""
    <style>
    @import url('https://api.fontshare.com/v2/css?f[]=switzer@300,400,500,600&display=swap');

    html, body, div, p, span, label, input, textarea, button, h1, h2, h3, h4, h5, h6 {
        font-family: 'Switzer', sans-serif !important;
    }
        /* Base button style */
    div.stButton > button {
        color: #1E90FF;                  /* Blue text */
        background-color: white;        /* White background */
        border: 1px solid #1E90FF;      /* Blue border */
        border-radius: 6px;             /* Rounded corners */
        padding: 0.5em 1.2em;
        font-weight: 600;
        font-size: 16px;
        transition: all 0.3s ease;
    }
    .sidebar-header-text {
        font-size: 1.25rem;
        font-weight: 600;
        margin-top: 16px;
    }
    .stSidebar {
        background-color: #FAFAFA !important;
    }
    
    /* Hover style */
    div.stButton > button:hover {
        color: white !important;              /* White text */
        background-color: #1E90FF !important; /* Blue background */
        border: 1px solid white !important;   /* White border */
    }
    button > svg {
            fill: #1E90FF !important;
            }
    .stChatInput > div {
            border-radius: 4px !important;
            }
    .lead-container {
        display: flex;
        flex-direction: column;
        gap: 16px;
        padding-top: 8px;
        margin-bottom: 16px;
    }
    # .lead-container > div{
    #     display: grid;
    #     grid-template-columns: 50% 50%;
    #     justify-content: space-between;
    # }
    .side-bar-subheader{
            font-weight: 400;
            font-size: 18px;
            color: #222222;
            margin-bottom: 8px;
        }
    .lead-container > div > div, .sidebar-normal-text, .sidebar-bold-text {
        font-weight: 400;
        font-size: 16px;
        color: #777777;
    }
    .lead-container > div > div:nth-child(even), .sidebar-bold-text {
        color: #222222;
    }
    .highlighted {
        background-color: yellow !imporant;
        font-weight: bold;
    }
    .stChatInput > div:focus-within {
        border-color: #1E90FF !important;
    }
    .stAppToolbar > span {
        font-family: "Material Symbols Rounded" !important;
    }
    .file-outer-container {
        display: flex;
        gap: 8px;
        margin-bottom: 20px;
    }
    .file-info {
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    @media only screen and (min-width: 400px) {
        .stSidebar {
            min-width: 180px !important;
        }
    }
    @media only screen and (min-width: 600px) {
        .stSidebar {
            min-width: 280px !important;
        }
    }
    @media only screen and (min-width: 900px) {
        .stSidebar {
            min-width: 400px !important;
        }
    }
    .stNumberInput button:not(:disabled) {
        display: None !important;        
    }
    .stSidebar > :first-child > :first-child {
        display: None !important;
    }
    .st-ae > :first-child > :first-child {
        display: flex;
        justify-content: space-evenly;    
    }
    .st-ae > :first-child > :first-child > button {
        width: 100%;
        position: relative;
    }
    .st-ae > :first-child > :first-child > button:hover p, .st-bd p{
        color: black !important;
        font-weight: 600;
    }
    .st-ae > :first-child > :first-child > button:hover, .st-bd {
        color: black !important;
    }
    .st-c2 {
        background-color: black;    
    }
    .hide {
        display: None;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)


# ------------- sidebar ---------------
col1, col2, col3 = st.sidebar.columns([1, 6, 2])
with col1:
    st.markdown(
        """
        <div style='padding: 9px;'>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.image("./static/Ai Chipset.svg", width=120)
with col2:
    st.markdown("""<div class="sidebar-header-text">Proposal AI</div>""", unsafe_allow_html=True)    

lead_tab, tariff_tab, system_tab = st.sidebar.tabs(["Lead", "Tariff", "System"])
if st.session_state.sidebar_states:
    project_details = st.session_state.sidebar_states.get('project_details')
    project_name = None
    address = None
    weather = None
    system_price = None
    consumption = None
    generation = None
    system_size = None
    if project_details.get('project_name'):
        project_name = '-' if project_details.get('project_name') == 'null' else project_details.get('project_name')
        address = '-' if project_details.get('address') == 'null' else project_details.get('address')
        latitude = '' if project_details.get('latitude') == 'null' else project_details.get('latitude')
        longitude = '' if project_details.get('longitude') == 'null' else project_details.get('longitude')
        system_price = None if st.session_state.sidebar_states.get('final_price') == 'null' else st.session_state.sidebar_states.get('final_price')
        consumption_unit = None if st.session_state.sidebar_states.get("consumption_unit") == 'null' else st.session_state.sidebar_states.get("consumption_unit")
        annual_consumption = None if st.session_state.sidebar_states.get("annual_consumption") == 'null' else st.session_state.sidebar_states.get("annual_consumption")
        generation = None if st.session_state.sidebar_states.get("annual_generation") == 'null' else st.session_state.sidebar_states.get("annual_generation")
        energy_offset = None if st.session_state.sidebar_states.get("offset") == 'null' else st.session_state.sidebar_states.get("offset")
        system_size = None if st.session_state.sidebar_states.get("nameplate_dc_size") == 'null' else st.session_state.sidebar_states.get("nameplate_dc_size")
        tariff_details = st.session_state.sidebar_states.get('tariff_details')
        custom_tariff = st.session_state.sidebar_states.get('custom_tariff')
        with lead_tab:
            st.markdown(f""" 
                <div class="lead-container">
                    <div>
                    <div>Name</div><div>{project_name}</div>
                    </div>
                    <div>
                    <div>Address</div><div>{address}</div>
                    </div>
                    <div>
                    <div>Weather</div><div>({latitude if latitude else ''}) - ({longitude if longitude else ''})</div>
                    </div>
                    <div>
                    <div>Annual Usage Estimate</div>
                    <div>
                    {(consumption_unit if (consumption_unit != 'kWh' and annual_consumption) else '')}{annual_consumption if annual_consumption else '-'} {(consumption_unit if consumption_unit == 'kWh' else '')}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True) 
        with tariff_tab:
            if tariff_details or custom_tariff:
                details = custom_tariff if custom_tariff else tariff_details
                pre_solar_utility_rate = '-' if details.get('utility_rate_name') == 'null' else details.get('utility_rate_name')
                pre_solar_utility_provider = '-' if details.get('utility_provider_name') == 'null' else details.get('utility_provider_name')
                post_solar_utility_provider = '-' if details.get('post_solar_utility_provider_name') == 'null' else details.get('post_solar_utility_provider_name')
                post_solar_utility_rate = '-' if details.get('post_solar_utility_rate_name') == 'null' else details.get('post_solar_utility_rate_name')
                annual_escalation_rate = '-' if details.get('annual_escalation_rate') == 'null' else details.get('annual_escalation_rate')
                
                st.markdown(f""" 
                    <div class="lead-container">
                        <div>
                        <div>Pre Solar Utility Provider</div><div>{pre_solar_utility_provider if pre_solar_utility_provider else '-'}</div>
                        </div>
                        <div>
                        <div>Pre Solar Utility Rate</div><div>{pre_solar_utility_rate if pre_solar_utility_rate else '-'}</div>
                        </div>
                        <div>
                        <div>Post Solar Utility Provider</div><div>{post_solar_utility_provider if post_solar_utility_provider else '-'}</div>
                        </div>
                        <div>
                        <div>Post Solar Utility Rate</div><div>{post_solar_utility_rate if post_solar_utility_rate else '-'}</div>
                        </div>
                        <div>
                        <div>Annual Escalation Rate</div><div>
                        {annual_escalation_rate if annual_escalation_rate else '-'}</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
        with system_tab:
            unit_price = None
            is_net_metering = None
            annual_escalation_rate = None
            currency_symbol = None
            if tariff_details or custom_tariff:
                details = custom_tariff if custom_tariff else tariff_details
                unit_price = '-' if st.session_state.sidebar_states.get('price') == 'null' else st.session_state.sidebar_states.get('price')
                if unit_price:
                    currency_symbol = "" if st.session_state.sidebar_states.get('currency_symbol') == 'null' else st.session_state.sidebar_states.get('currency_symbol')
                is_net_metering = '-' if details.get('net_metering') == 'null' else details.get('net_metering')
            
            st.markdown(f""" 
                <div class="lead-container">
                    <div class="{"" if is_net_metering else "hide"}">
                    <div>Type</div><div>{'Net Metering' if is_net_metering else '-'}</div>
                    </div>
                    <div>
                    <div>Price per Watt</div><div>{currency_symbol if currency_symbol else ''}{unit_price if unit_price else '-'}</div>
                    </div>
                    <div>
                    <div>System Size</div><div>{system_size if system_size else '-'} {'kWp' if system_size else ''}</div>
                    </div>
                    <div>
                    <div>Annual Generation</div><div>
                    {generation if generation else '-'} 
                    {'kWh' if generation else ''}</div>
                    </div>
                    <div>
                    <div>Energy Offset</div><div>
                    {energy_offset if energy_offset else '-'} 
                    {'%' if energy_offset else ''}</div>
                    </div>
                    <div>
                    <div>System Price</div><div>{st.session_state.sidebar_states.get("currency_symbol") if system_price else ''}{system_price if system_price else '-'}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            if st.session_state.design:
                st.image(st.session_state.design, width=200)
# with st.sidebar.container(border=True):

#     # st.markdown(f"""<div class="side-bar-subheader">Lead Details</div>""", unsafe_allow_html=True)
#     # if st.session_state.sidebar_states:
#     #     project_details = st.session_state.sidebar_states.get('project_details')
#     #     project_name = None
#     #     address = None
#     #     weather = None
#     #     system_price = None
#     #     consumption = None
#     #     generation = None
#     #     system_size = None
#     #     if project_details.get('project_name'):
#     #         project_name = '-' if project_details.get('project_name') == 'null' else project_details.get('project_name')
#     #         address = '-' if project_details.get('address') == 'null' else project_details.get('address')
#     #         latitude = '' if project_details.get('latitude') == 'null' else project_details.get('latitude')
#     #         longitude = '' if project_details.get('longitude') == 'null' else project_details.get('longitude')
#     #         system_price = None if st.session_state.sidebar_states.get('final_price') == 'null' else st.session_state.sidebar_states.get('final_price')
#     #         consumption_unit = None if st.session_state.sidebar_states.get("consumption_unit") == 'null' else st.session_state.sidebar_states.get("consumption_unit")
#     #         annual_consumption = None if st.session_state.sidebar_states.get("annual_consumption") == 'null' else st.session_state.sidebar_states.get("annual_consumption")
#     #         generation = None if st.session_state.sidebar_states.get("annual_generation") == 'null' else st.session_state.sidebar_states.get("annual_generation")
#     #         energy_offset = None if st.session_state.sidebar_states.get("offset") == 'null' else st.session_state.sidebar_states.get("offset")
#     #         system_size = None if st.session_state.sidebar_states.get("nameplate_dc_size") == 'null' else st.session_state.sidebar_states.get("nameplate_dc_size")
                
#     #     st.markdown(f""" 
#     #         <div class="lead-container">
#     #             <div>
#     #             <div>Lead Name</div><div>{project_name}</div>
#     #             </div>
#     #             <div>
#     #             <div>Lead Address</div><div>{address}</div>
#     #             </div>
#     #             <div>
#     #             <div>Weather</div><div>({latitude if latitude else ''}) - ({longitude if longitude else ''})</div>
#     #             </div>
#     #             <div>
#     #             <div>System Price</div><div>{st.session_state.sidebar_states.get("currency_symbol") if system_price else ''}{system_price if system_price else '-'}</div>
#     #             </div>
#     #             <div>
#     #             <div>Estimated Annual Usage</div><div>
#     #             {(consumption_unit if (consumption_unit != 'kWh' and annual_consumption) else '')}{annual_consumption if annual_consumption else '-'} {(consumption_unit if consumption_unit == 'kWh' else '')}</div>
#     #             </div>
#     #             <div>
#     #             <div>Annual Generation</div><div>
#     #             {generation if generation else '-'} 
#     #             {'kWh' if generation else ''}</div>
#     #             </div>
#     #             <div>
#     #             <div>Energy Offset</div><div>
#     #             {energy_offset if energy_offset else '-'} 
#     #             {'%' if energy_offset else ''}</div>
#     #             </div>
#     #             <div>
#     #             <div>System Size</div><div>{system_size if system_size else '-'} {'kWp' if system_size else ''}</div>
#     #             </div>
#     #         </div>
#     #      """, unsafe_allow_html=True)
#     #     # st.write(f"Lead Name: **{st.session_state.lead_details['name']}**")
#     #     # st.write(f"Address: **{st.session_state.lead_details['address']}**")
#     #     # st.write(f"Weather: **{st.session_state.lead_details['project_details']['state']} ({st.session_state.lead_details['project_details']['latitude']} {st.session_state.lead_details['project_details']['longitude']})**")
#     #     # st.write(f"System Price: **{st.session_state.lead_details['deal_value']}**")
#     #     # st.write(f"Consumption: **{st.session_state.lead_details['deal_value']}**")
#     #     # st.write(f"Generation: **{st.session_state.lead_details['deal_value']}**")
#     #     # st.write(f"System Size: **{st.session_state.lead_details['deal_value']}**")

#     st.markdown(f"""<div class="side-bar-subheader">Tariff</div>""", unsafe_allow_html=True)
#     # if st.session_state.sidebar_states:
#         #TODO for cusotm tariffs
#         # tariff_details = st.session_state.sidebar_states.get('tariff_details')
#         # custom_tariff = st.session_state.sidebar_states.get('custom_tariff')
#         # if not custom_tariff and tariff_details:
#         #     pre_solar_utility_rate = '-' if tariff_details.get('utility_rate_name') == 'null' else tariff_details.get('utility_rate_name')
#         #     pre_solar_utility_provider = '-' if tariff_details.get('utility_provider_name') == 'null' else tariff_details.get('utility_provider_name')
#         #     post_solar_utility_provider = '-' if tariff_details.get('post_solar_utility_provider_name') == 'null' else tariff_details.get('post_solar_utility_provider_name')
#         #     post_solar_utility_rate = '-' if tariff_details.get('post_solar_utility_rate_name') == 'null' else tariff_details.get('post_solar_utility_rate_name')
#         #     annual_escalation_rate = '-' if tariff_details.get('annual_escalation_rate') == 'null' else tariff_details.get('annual_escalation_rate')
            
#         #     st.markdown(f""" 
#         #         <div class="lead-container">
#         #             <div>
#         #             <div>Pre Solar Utility Provider</div><div>{pre_solar_utility_provider if pre_solar_utility_provider else '-'}</div>
#         #             </div>
#         #             <div>
#         #             <div>Pre Solar Utility Rate</div><div>{pre_solar_utility_rate if pre_solar_utility_rate else '-'}</div>
#         #             </div>
#         #             <div>
#         #             <div>Post Solar Utility Provider</div><div>{post_solar_utility_provider if post_solar_utility_provider else '-'}</div>
#         #             </div>
#         #             <div>
#         #             <div>Post Solar Utility Rate</div><div>{post_solar_utility_rate if post_solar_utility_rate else '-'}</div>
#         #             </div>
#         #             <div>
#         #             <div>Annual Escalation Rate</div><div>
#         #             {annual_escalation_rate if annual_escalation_rate else '-'}</div>
#         #             </div>
#         #         </div>
#         #     """, unsafe_allow_html=True)

#         # if custom_tariff:
#         #     unit_price = '-' if custom_tariff.get('unit_price') == 'null' else custom_tariff.get('unit_price')
#         #     is_net_metering = '-' if custom_tariff.get('net_metering') == 'null' else custom_tariff.get('net_metering')
#         #     annual_escalation_rate = '-' if custom_tariff.get('annual_escalation_rate') == 'null' else custom_tariff.get('annual_escalation_rate')
            
#         #     st.markdown(f""" 
#         #         <div class="lead-container">
#         #             <div>
#         #             <div>Type</div><div>{'Net Metering' if is_net_metering else '-'}</div>
#         #             </div>
#         #             <div>
#         #             <div>Unit Price</div><div>{unit_price if unit_price else '-'}</div>
#         #             </div>
#         #             <div>
#         #             <div>Annual Escalation Rate</div><div>
#         #             {annual_escalation_rate if annual_escalation_rate else '-'}</div>
#         #             </div>
#         #         </div>
#         #     """, unsafe_allow_html=True)


#     st.markdown(f"""<div class="side-bar-subheader">Design</div>""", unsafe_allow_html=True)
    


def handle_choice_selection(choice):
    st.session_state.messages.append({"author": "user", "message": choice})
    st.session_state.mimic_user_input = choice

def get_address_from_google(lat, lng, api_key):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lng}&key={api_key}"
    response = requests.get(url)
    data = response.json()
   
    if data['status'] == 'OK' and data['results']:
        return data['results'][0]['formatted_address']
    else:
        return "Address not found"
    
def handle_location_selection():
    st.session_state.counter = st.session_state.counter + 1
    # This will evaluate JS and return the value of localStorage.getItem("myKey")
    st.session_state.clicked_location = None
    
def handle_options_click(choice):
    # st.session_state.messages.append({"author": "user", "message": choice})
    st.session_state.messages[-1] = ({"author": st.session_state.messages[-1].get("author"), "message": st.session_state.messages[-1].get("message")})
    st.session_state.mimic_user_input = choice

def handle_month_consumption(month, amount):
    st.session_state.messages[-1] = ({"author": st.session_state.messages[-1].get("author"), "message": st.session_state.messages[-1].get("message")})
    st.session_state.mimic_user_input = f"Month: {month}, Usage: {str(amount)}kWh"
    st.session_state.month_consumption_details = {
        "month": month, "usage": amount
    }
    st.session_state.is_file_upload_enabled = False
    
def handle_upload_click(file):
    st.session_state.messages[-1] = ({"author": st.session_state.messages[-1].get("author"), "message": st.session_state.messages[-1].get("message")})
    st.session_state.mimic_user_input = "Utility Bill File "
    st.session_state.uploaded_bill = file
    st.session_state.is_file_upload_enabled = False
    
def generate_layout_image(design_id):
    if design_id == st.session_state.active_design_id: return
    try:
        response = requests.get(
            f"http://{server_ip_and_port}/api/chat/design_image/",
            params={
                "design_id": design_id,
            },
        )

        if response.status_code == 200:
            response_data = response.json()
            bot_reply = response_data.get("layout_image_url", None)
            if bot_reply:
                st.session_state.design = bot_reply
            st.session_state.active_design_id = design_id
        else:
            st.session_state.design = None
        print ("DESIGN IMG URL", st.session_state.design)

    except requests.exceptions.RequestException as e:
        st.session_state.design = None
    

def handle_bot_response():
    print("reached handle_bot_response")
    while True:
        with st.spinner("🤖 Processing... Please wait..."):
                    try:
                        request_body = {
                            "query": st.session_state.pending_input,
                            "session_id": st.session_state.session_id,
                        }
                        if st.session_state.address_confirmed and st.session_state.clicked_location and not st.session_state.address_confirmed_sent:
                            request_body["address_confirmed"] = True
                            st.session_state.address_confirmed_sent = True
                        if st.session_state.month_consumption_details:
                            request_body["month_consumption_details"] = st.session_state.month_consumption_details
                            st.session_state.month_consumption_details = None
                        if st.session_state.messages[-1].get("file") or st.session_state.uploaded_bill:
                            file = st.session_state.uploaded_bill if st.session_state.uploaded_bill else st.session_state.messages[-1].get("file")
                            file_content = file.read()
                            encoded_file = base64.b64encode(file_content).decode('utf-8')
                            #TODO compress this
                            request_body["file"] = {
                                "file_name": file.name,
                                "content_type": file.type,
                                "data": encoded_file,
                            }
                            st.session_state.uploaded_bill = None
                            # import zipfile
                            # import io
                            
                            # uploaded_file = st.session_state.messages[-1].get("file")
                            # # if uploaded_file is not None:
                            #     # Compress the file in memory
                            # compressed_buffer = io.BytesIO()
                            # with zipfile.ZipFile(compressed_buffer, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
                            #     zf.writestr(uploaded_file.name, uploaded_file.read())

                            # compressed_buffer.seek(0)  # Reset buffer pointer

                            # # Send to FastAPI
                            # files = {'file': ('compressed.zip', compressed_buffer, 'application/zip')}
                            
                            # # print("file",files)

                            # # encoded_file = base64.b64encode(file_content).decode('utf-8')
                            # request_body["file"] = files
                            # # request_body["file"] = file
                        response = requests.post(
                            f"http://{server_ip_and_port}/api/chat/",
                            json=request_body,
                        )
                        if response.status_code == 200:
                            response_data = response.json()
                            bot_reply = response_data.get("response", "No response received.")
                            state = response_data.get("state", None)
                            wait_for_input = response_data.get("wait_for_input", True)
                            is_proposal_link = response_data.get("is_proposal_link")
                            options = response_data.get("options")
                            message_type = response_data.get("message_type")
                            is_document_rejected = response_data.get("is_document_rejected")
                            
                            if message_type == "base_system_price_selection":
                                # check for old message with base price option and remove if found
                                if st.session_state.messages[-2].get("message_type") == message_type:
                                    st.session_state.messages[-2]["options"] = None
                                    
                            if message_type == "dropdown":
                                st.session_state.is_file_upload_enabled = True
                            if state:
                                if state.get("project_details"):
                                    if state.get("project_details").get("address"):
                                        st.session_state.user_selected_address = None if state.get("project_details").get("address") == "null" else state.get("project_details").get("address")
                                    if state.get("project_details").get("project_name"):
                                        st.session_state.sidebar_states = state
                                        if st.session_state.sidebar_states.get("design_id"):
                                            generate_layout_image(st.session_state.sidebar_states.get("design_id"))
                            if st.session_state.user_selected_address and (not st.session_state.address_confirmed and not st.session_state.is_confirm_address_shown):
                                # this block of code runs to confirm address
                                st.session_state.messages.append({
                                    "author": "assistant",
                                    "message": "",
                                    "show_location_confirmation": True,
                                })
                                st.session_state.is_location_button_shown = True
                                st.session_state.is_confirm_address_shown = True
                            elif st.session_state.is_location_button_shown or st.session_state.user_selected_address: 
                                # this block of code runs when address is confirmed
                                st.session_state.messages.append({
                                    "author": "assistant",
                                    "message": bot_reply,
                                    "is_proposal_link": is_proposal_link,
                                    "options": options,
                                    "message_type": message_type,
                                    "is_document_rejected": is_document_rejected, 
                                })
                            else:
                                # this block of code runs on fresh start
                                st.session_state.messages.append({
                                    "author": "assistant",
                                    "message": bot_reply,
                                    "show_location_button": True,
                                })
                                st.session_state.show_location_selection_button = True
                                st.session_state.is_location_button_shown = True

                    # Display updated chat history
                    

                            if not wait_for_input:
                                
                                time.sleep(0.5)
                                st.session_state.pending_input = AUTO_TRIGGER_TOKEN
                                st.session_state.is_processing = False
                                
                            else:
                                st.session_state.pending_input = None
                                break
                        else:
                            st.session_state.pending_input = None
                            st.session_state.messages.append({
                                "author": "assistant",
                                "message": "❌ Error: Server returned an error."
                            })
                            break

                    except requests.exceptions.RequestException as e:
                        st.session_state.pending_input = None
                        st.session_state.messages.append({
                            "author": "assistant",
                            "message": f"❌ Request failed: {str(e)}"
                        })
                        break
               

        break
    if not st.session_state.pending_input:
        st.session_state.is_disabled = False

def handle_show_location_click():
    st.session_state.show_location_selection_button = False
    st.session_state.show_google_map = True
# if a new location is selected
if not st.session_state.clicked_location and st.session_state.counter > 0: 
    location = streamlit_js_eval(js_expressions="localStorage.getItem('clicked_location')", key=f"getLocalStorage_{st.session_state.counter}")
    if location:
        st.session_state.clicked_location = json.loads(location)
        address = get_address_from_google(st.session_state.clicked_location.get("lat"), st.session_state.clicked_location.get("lng"), GOOGLE_MAPS_API_KEY)
        # st.session_state.messages[-1] = {
        #                 "author": "assistant",
        #                 "message": f"Selected Address: **{address}**",
        #                 "coordinates": [st.session_state.clicked_location.get("lat"), st.session_state.clicked_location.get("lng")]
        #             }
        # st.session_state.messages.append({"author": "user", "message": address})
        st.session_state.user_selected_address = address
        st.session_state.show_google_map = False
        st.session_state.mimic_user_input = "Confirmed Location: " + address
        st.session_state.address_confirmed = True

# st.button("Click me", on_click=set_lead_details)
user_choice = None

# init messages

if len(st.session_state.messages) == 0:
    with st.chat_message("assistant", avatar="./static/Ai Chipset.svg"):
        print(st.session_state.user)
        st.subheader("")
        st.subheader("👋 Welcome to Proposal AI Chat!")
        st.write("I’m here to help you start a new solar project by collecting a few quick details.")
        st.markdown("Let’s get started.")
    # st.session_state.messages.append({"author": "user"})
else:
    # Insert a chat message container.
    for index, message in enumerate(st.session_state.messages):
        avatar = "./static/Ai Chipset.svg" if message.get("author") == "assistant" else message.get("author")
        if message.get("is_helper_prompt"):
            avatar = "./static/Ai Chipset.svg"
        with st.chat_message(message.get("author"), avatar=avatar):
            if message.get("coordinates"):
                html_code = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        #map {{
                            height: 350px;
                            width: 100%;
                            border-radius: 16px;  /* 👈 rounded corners */
                            overflow: hidden;     /* 👈 prevents map content from overflowing corners */
                        }}
                    </style>
                    <script src="https://maps.googleapis.com/maps/api/js?key={GOOGLE_MAPS_API_KEY}&libraries=places"></script>
                    <script>
                        let map;
                        let marker;

                        function initMap() {{
                            const defaultLocation = {{ lat: {message.get("coordinates")[0]}, lng: {message.get("coordinates")[1]} }};
                            map = new google.maps.Map(document.getElementById("map"), {{
                                center: defaultLocation,
                                zoom: 20,
                                mapTypeId: "satellite",
                                mapTypeControl: false,
                                disableDefaultUI: true,
                                draggable: false
                            }});
                        }}

                        window.addEventListener("load", initMap);
                    </script>
                </head>
                <body>
                    <div id="map"></div>
                </body>
                </html>
                """
                components.html(html_code, height=370, width=420)
            if message.get("is_proposal_link"):
                st.link_button("Click here for proposal.", message.get("message"))
            else:
                if message.get("show_location_confirmation") and st.session_state.address_confirmed:
                    st.write("Address Confirmed")
                else:
                    if message.get("is_document_rejected"):
                        st.write("Please Enter Your Monthly Energy(kwh).")
                    else:
                        st.write(message.get("message"))
                if message.get("images"):
                    for image in message.get("images"):
                        st.image(image)
                if message.get("links"):
                    for link in message.get("links"):
                        st.write(link)
                # if message.get("choices"):
                #     for choice in message.get("choices"):
                #         st.button(choice, on_click=handle_choice_selection, args=(choice,))
                if message.get("show_location_button") and not st.session_state.user_selected_address:
                    if st.session_state.show_location_selection_button:
                        st.button("Click here to select a location", on_click=handle_show_location_click, disabled=st.session_state.is_disabled, key=index)
                    elif st.session_state.show_google_map:
                        st.markdown("""<div style="color:red;"><h4>(Please select a roof)</h4></div>""", unsafe_allow_html=True)
                        last_clicked = None
                        html_code = f"""
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <style>
                                #map {{
                                    height: 350px;
                                    width: 100%;
                                    border-radius: 16px;  /* 👈 rounded corners */
                                    overflow: hidden;     /* 👈 prevents map content from overflowing corners */
                                }}
                                #pac-input {{
                                    margin: 10px;
                                    padding: 8px;
                                    width: 300px;
                                    font-size: 16px;
                                    position: absolute;
                                    top: 10px;
                                    left: 50%;
                                    transform: translateX(-50%);
                                    z-index: 5;
                                    background-color: white;
                                    border: 1px solid #ccc;
                                    border-radius: 4px;
                                }}
                            </style>
                            <script src="https://maps.googleapis.com/maps/api/js?key={GOOGLE_MAPS_API_KEY}&libraries=places"></script>
                            <script>
                                let map;
                                let marker;

                            function initMap() {{
                                const defaultLocation = {{ lat: 37.5664701, lng: -122.0714272 }};
                                map = new google.maps.Map(document.getElementById("map"), {{
                                    center: defaultLocation,
                                    zoom: 20,
                                    mapTypeId: "satellite",
                                    mapTypeControl: false
                                }});

                                const input = document.getElementById("pac-input");
                                const autocomplete = new google.maps.places.Autocomplete(input);
                                autocomplete.bindTo("bounds", map);

                                autocomplete.addListener("place_changed", () => {{
                                    const place = autocomplete.getPlace();
                                    if (!place.geometry || !place.geometry.location) {{
                                        alert("No details available for input: '" + place.name + "'");
                                        return;
                                    }}

                                    const location = place.geometry.location;

                                    if (marker) {{
                                        marker.setMap(null);
                                    }}

                                    marker = new google.maps.Marker({{
                                        map: map,
                                        position: location
                                    }});

                                    map.setCenter(location);
                                    map.setZoom(20);

                                    const locationData = {{ lat: location.lat(), lng: location.lng() }};
                                    localStorage.setItem("clicked_location", JSON.stringify(locationData));
                                }});

                                map.addListener("click", function(e) {{
                                    const lat = e.latLng.lat();
                                    const lng = e.latLng.lng();

                                    if (marker) {{
                                        marker.setMap(null);
                                    }}

                                    marker = new google.maps.Marker({{
                                        position: {{ lat: lat, lng: lng }},
                                        map: map
                                    }});

                                    const locationData = {{ lat: lat, lng: lng }};
                                    localStorage.setItem("clicked_location", JSON.stringify(locationData));
                                }});
                            }}

                            window.addEventListener("load", initMap);
                        </script>
                    </head>
                    <body>
                        <input id="pac-input" type="text" placeholder="Search location" style="position: absolute; left: 170px"/>
                        <div id="map"></div>
                    </body>
                    </html>
                    """
                        components.html(html_code, height=370, width=420)

                        st.button("Confirm Location", on_click=handle_location_selection)
                if message.get("show_location_confirmation") and not st.session_state.address_confirmed:
                    lat = st.session_state.sidebar_states.get("latitude")
                    lng = st.session_state.sidebar_states.get("longitude")
                    address = get_address_from_google(lat, lng, GOOGLE_MAPS_API_KEY)
                    st.markdown("""<div style="color:red;"><h4>(Please select a roof)</h4></div>""", unsafe_allow_html=True)
                    last_clicked = None
                    html_code = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <style>
                            #map {{
                                height: 350px;
                                width: 100%;
                                border-radius: 16px;  /* 👈 rounded corners */
                                overflow: hidden;     /* 👈 prevents map content from overflowing corners */
                            }}
                            #pac-input {{
                                margin: 10px;
                                padding: 8px;
                                width: 300px;
                                font-size: 16px;
                                position: absolute;
                                top: 10px;
                                left: 50%;
                                transform: translateX(-50%);
                                z-index: 5;
                                background-color: white;
                                border: 1px solid #ccc;
                                border-radius: 4px;
                            }}
                        </style>
                        <script src="https://maps.googleapis.com/maps/api/js?key={GOOGLE_MAPS_API_KEY}&libraries=places"></script>
                        <script>
                            let map;
                            let marker;

                        function initMap() {{
                            const defaultLocation = {{ lat: {lat}, lng: {lng} }};
                            map = new google.maps.Map(document.getElementById("map"), {{
                                center: defaultLocation,
                                zoom: 20,
                                mapTypeId: "satellite",
                                mapTypeControl: false
                            }});

                            const input = document.getElementById("pac-input");
                            input.value = "{address}";  // 👈 Set default value here
                            const autocomplete = new google.maps.places.Autocomplete(input);
                            autocomplete.bindTo("bounds", map);

                            autocomplete.addListener("place_changed", () => {{
                                const place = autocomplete.getPlace();
                                if (!place.geometry || !place.geometry.location) {{
                                    alert("No details available for input: '" + place.name + "'");
                                    return;
                                }}

                                const location = place.geometry.location;

                                if (marker) {{
                                    marker.setMap(null);
                                }}

                                marker = new google.maps.Marker({{
                                    map: map,
                                    position: location
                                }});

                                map.setCenter(location);
                                map.setZoom(20);

                                const locationData = {{ lat: location.lat(), lng: location.lng() }};
                                localStorage.setItem("clicked_location", JSON.stringify(locationData));
                            }});

                            map.addListener("click", function(e) {{
                                const lat = e.latLng.lat();
                                const lng = e.latLng.lng();

                                if (marker) {{
                                    marker.setMap(null);
                                }}

                                marker = new google.maps.Marker({{
                                    position: {{ lat: lat, lng: lng }},
                                    map: map
                                }});

                                const locationData = {{ lat: lat, lng: lng }};
                                localStorage.setItem("clicked_location", JSON.stringify(locationData));

                                // 👇 Reverse geocode clicked location
                                const geocoder = new google.maps.Geocoder();
                                geocoder.geocode({{ location: {{ lat: lat, lng: lng }} }}, (results, status) => {{
                                    if (status === "OK" && results[0]) {{
                                        document.getElementById("pac-input").value = results[0].formatted_address;
                                    }} else {{
                                        console.warn("Geocoder failed due to: " + status);
                                    }}
                                }});
                            }});
                        }}

                        window.addEventListener("load", initMap);
                    </script>
                </head>
                <body>
                    <input id="pac-input" type="text" placeholder="Search location" style="position: absolute; left: 170px"/>
                    <div id="map"></div>
                </body>
                </html>
                """
                    components.html(html_code, height=370, width=420)

                    st.button("Confirm Location", on_click=handle_location_selection)
                print("message",message)
                if message.get("options"):
                    if len(message.get("options")) > 0:
                        for option in message.get("options"):
                            st.button(option, on_click=handle_options_click, args=(option,))
                if message.get("message_type"):
                    if message.get("message_type") == "dropdown":
                        col1, col2 = st.columns([1,1])
                        with col1:
                            selected_month = st.selectbox("Select a month", ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"])
                        with col2:
                            consumption_amount = st.number_input("Enter Usage (kWh)")
                        st.button("Confirm", on_click=handle_month_consumption, args=(selected_month, consumption_amount), disabled=(True if st.session_state.month_consumption_details else False) or consumption_amount < 1)
                        st.write("or")
                        file = st.file_uploader("Upload your latest utility bill and let us fill it for you.", type=["pdf"], accept_multiple_files=False)
                        st.button("Upload", on_click=handle_upload_click, args=(file,), disabled= (not file or not st.session_state.is_file_upload_enabled))
                        if message.get("is_document_rejected"):
                            st.markdown(f"""<div style="color: red;">{message.get("message")}</div>""", unsafe_allow_html=True)
                if message.get("file"):
                    st.markdown(f"""<div class="file-outer-container"><div class="file-container"><img height="50" src="https://www.iconpacks.net/icons/2/free-file-icon-1453-thumb.png"></img></div><div class="file-info"><div style="font-weight: 500;">{message.get("file").name}</div> <div style="opacity: 0.8;">{(message.get("file").size)/1000}KB</div></div></div>""", unsafe_allow_html=True)
# Display a chat input widget at the bottom of the app.
# st.session_state.user_input = st.chat_input("Say something", accept_file=True, disabled=st.session_state.is_disabled, on_submit=handle_submit)

user_input = st.chat_input("Write your prompts", accept_file=False, disabled=(st.session_state.is_disabled or st.session_state.is_file_upload_enabled))
submitted = False
if st.session_state.mimic_user_input:
    user_input = st.session_state.mimic_user_input
    st.session_state.mimic_user_input = None
if user_input:
    submitted = True
    st.session_state.messages.append({
            "author": "user",
            "message": (user_input.text.strip() if len(user_input.text.strip()) else 'Utility Bill File  ') if type(user_input) is not str else user_input,
            "file": None if type(user_input) is str else ( None if len(user_input.files) == 0 else user_input.files[0]),
        })
    if st.session_state.uploaded_bill:
        st.session_state.messages[-1]["file"] = st.session_state.uploaded_bill
    st.session_state.manual_rerun = True
    st.session_state.is_disabled = True
    st.rerun()
# Check if auto advancing
if st.session_state.manual_rerun:
    submitted = True
    user_input = st.session_state.messages[-1].get("message")
    st.session_state.manual_rerun = False
    
auto_trigger = st.session_state.pending_input == AUTO_TRIGGER_TOKEN









# Simulate submission in auto mode
if auto_trigger:
    submitted = True
    user_input = st.session_state.pending_input

# Handle submission
if submitted and (user_input.strip() or auto_trigger):
    st.session_state.is_processing = True

    if not auto_trigger:
        st.session_state.pending_input = user_input.strip()
        # st.session_state.messages.append({
        #     "author": "user",
        #     "message": st.session_state.pending_input
        # })

    handle_bot_response()
   
    st.session_state.is_processing = False
   
    st.rerun() 

# hard coded - to be removed
# if st.session_state.is_disabled:
#     if st.session_state.messages[-1].get("author") == "user":
#         if "design" in st.session_state.messages[-1].get("message"):
#             with st.spinner("🤖 Generating Design image..."):
#                 try:
#                     response = requests.get(
#                         f"http://{server_ip_and_port}/api/chat/design_image/",
#                         params={
#                             "design_id": 80860,
#                         },
#                     )

#                     if response.status_code == 200:
#                         response_data = response.json()
#                         bot_reply = response_data.get("layout_image_url", None)
#                         if bot_reply:
#                             st.session_state.design = bot_reply
#                         st.session_state.messages.append({
#                             "author": "assistant",
#                             "message": "No response received." if not bot_reply else bot_reply
#                         })
#                     else:
#                         st.session_state.messages.append({
#                             "author": "assistant",
#                             "message": "❌ Error: Server returned an error."
#                         })

#                 except requests.exceptions.RequestException as e:
#                     st.session_state.messages.append({
#                         "author": "assistant",
#                         "message": f"❌ Request failed: {str(e)}"
#                     })

#             st.session_state.is_disabled = False
#         elif "lead" in st.session_state.messages[-1].get("message"):
#             st.session_state.messages.append({"author": "assistant", "message": "Fetching the lead details.", "action_type": AI_PROCESS_TYPES[1][1]})
#         elif "images" in st.session_state.messages[-1].get("message"):
#             st.session_state.messages.append({"author": "assistant", "message": "Fetching the image.", "action_type": AI_PROCESS_TYPES[2][1]})
#         elif "changes" in st.session_state.messages[-1].get("message"):
#             st.session_state.messages.append({"author": "assistant", "message": "Fetching the options.", "action_type": AI_PROCESS_TYPES[3][1]})
#         elif "map" in st.session_state.messages[-1].get("message"):
#             st.session_state.messages.append({"author": "assistant", "message": "Loading googlemaps...", "action_type": AI_PROCESS_TYPES[4][1]}) 
#         else:
#             # st.session_state.messages.append({"author": "assistant", "message": st.session_state.messages[-1].get("message")})
            
#             st.session_state.pending_input = st.session_state.messages[-1].get("message")
#             while True:
#                 with st.spinner("🤖 Processing... Please wait..."):
#                     try:
#                         response = requests.post(
#                             f"http://{server_ip_and_port}/api/chat/",
#                             json={
#                                 "query": st.session_state.pending_input,
#                                 "session_id": st.session_state.session_id
#                             },
#                         )

#                         if response.status_code == 200:
#                             response_data = response.json()
#                             bot_reply = response_data.get("response", "No response received.")
#                             state = response_data.get("state", None)
#                             wait_for_input = response_data.get("wait_for_input", True)
#                             print(bot_reply, ' here')
#                             if state:
#                                 if state.get("project_details"): 
#                                     st.session_state.sidebar_states = state
#                                     if st.session_state.sidebar_states.get("design_id"):
#                                         generate_layout_image(st.session_state.sidebar_states.get("design_id"))
#                             st.session_state.messages.append({
#                                 "author": "assistant",
#                                 "message": bot_reply
#                             })
#                             if not wait_for_input:
#                                 time.sleep(0.5)
#                                 st.session_state.pending_input = AUTO_TRIGGER_TOKEN
#                                 # st.session_state.is_processing = False
                                
#                             else:
#                                 st.session_state.pending_input = ""
#                                 break
#                         else:
#                             st.session_state.messages.append({
#                                 "role": "assistant",
#                                 "message": "Server is busy, please try again in some time."
#                             })

#                     except requests.exceptions.RequestException as e:
#                         st.session_state.messages.append({
#                             "role": "assistant",
#                             "message": f"Server is busy, please try again in some time."
#                         })

#             st.session_state.is_disabled = False
#         st.rerun()

#     if st.session_state.is_disabled:
#         with st.spinner("Processing..."):
#             time.sleep(2)
#         if st.session_state.messages[-1].get("action_type") == AI_PROCESS_TYPES[0][1]:
#             st.session_state.messages[-1] = {"author": "assistant", "message": "https://dev.arka360.com/webProposal/b46f9030-88d5-406e-ba34-6ccec36dd638"}
#         if st.session_state.messages[-1].get("action_type") == AI_PROCESS_TYPES[1][1]:
#             st.session_state.messages[-1] = {"author": "assistant", "message": "You can find the lead details on the sidebar"}
#             set_lead_details()
#         if st.session_state.messages[-1].get("action_type") == AI_PROCESS_TYPES[2][1]:
#             st.session_state.messages[-1] = {
#                     "author": "assistant",
#                     "message": "here you go!",
#                     "images": ["https://cdn2.picryl.com/thumbnail/2013/12/07/525-of-the-students-manual-of-modern-geography-mathematical-physical-and-descriptive-bf0a99-200.jpg",
#                             "https://static.vecteezy.com/system/resources/thumbnails/050/819/558/small/blank-physical-topographic-map-of-cote-d-ivoire-photo.jpg"]
#                 }
#         if st.session_state.messages[-1].get("action_type") == AI_PROCESS_TYPES[3][1]:
#             st.session_state.messages[-1] = {
#                     "author": "assistant",
#                     "message": "What changes would you like to Implement?",
#                     "choices": ["Changing roof tilt and azimuth", "Chaning panel placement", "Chaning panels or inverters", "Modifying losses"]
#                 }
#         if st.session_state.messages[-1].get("action_type") == AI_PROCESS_TYPES[4][1]:
#             st.session_state.messages[-1] = {
#                     "author": "assistant",
#                     "message": "",
#                     "is_location_selection": True,
#                 }
                
#         st.session_state.is_disabled = False
#     st.rerun()










# import requests
# import uuid           
# import streamlit as st
# from dotenv import load_dotenv

# load_dotenv()

# # Server configuration
# server_ip_address = "backend"
# server_port_number = "8001"
# server_ip_and_port = f"127.0.0.1:{server_port_number}"
# import streamlit as st
# import uuid
# import requests

# # Set up the Streamlit page
# st.set_page_config(page_title="OllamaBot")
# st.title("💬 Arka Proposal Agent")

# # Initialize session state
# if "session_id" not in st.session_state:
#     st.session_state.session_id = str(uuid.uuid4())

# if "chat_history" not in st.session_state:
#     st.session_state.chat_history = []

# if "pending_input" not in st.session_state:
#     st.session_state.pending_input = ""

# if "is_processing" not in st.session_state:
#     st.session_state.is_processing = False

# # Display chat history
# st.subheader("Chat History")
# # for message in st.session_state.chat_history:
# #     sender = "🧑 You" if message["role"] == "user" else "🤖 Assistant"
# #     st.markdown(f"**{sender}:** {message['content']}")

# for msg in st.session_state.chat_history:
#     with st.chat_message(msg["role"]):
#         st.markdown(msg["content"])

# import time
# import streamlit as st
# import requests 

# AUTO_TRIGGER_TOKEN = "__auto__"
# TYPING_ANIMATION_INTERVAL = 0.5  # Seconds between dots

# def show_typing_animation():
#     placeholder = st.empty()
#     dots = ["", ".", "..", "..."]
#     for _ in range(6):  # 3 seconds total
#         for d in dots:
#             placeholder.markdown(f"🤖 *Assistant is typing{d}*")
#             time.sleep(TYPING_ANIMATION_INTERVAL)

# def handle_bot_response():
#     while True:
      
          

#         with st.spinner("🤖 Processing... Please wait..."):
#             try:
#                 response = requests.post(
#                     f"http://{server_ip_and_port}/api/chat/",
#                     json={
#                         "query": st.session_state.pending_input,
#                         "session_id": st.session_state.session_id
#                     },
#                 )

#                 if response.status_code == 200:
#                     response_data = response.json()
#                     bot_reply = response_data.get("response", "No response received.")
#                     wait_for_input = response_data.get("wait_for_input", True)
#                     print(bot_reply)

#                     st.session_state.chat_history.append({
#                         "role": "assistant",
#                         "content": bot_reply
#                     })
#                     # Display updated chat history
                    

#                     if not wait_for_input:
#                         time.sleep(0.5)
#                         st.session_state.pending_input = AUTO_TRIGGER_TOKEN
#                         st.session_state.is_processing = False
                        
#                     else:
#                         st.session_state.pending_input = ""
#                         break
#                 else:
#                     st.session_state.chat_history.append({
#                         "role": "assistant",
#                         "content": "❌ Error: Server returned an error."
#                     })
#                     break

#             except requests.exceptions.RequestException as e:
#                 st.session_state.chat_history.append({
#                     "role": "assistant",
#                     "content": f"❌ Request failed: {str(e)}"
#                 })
#                 break

#         break




# # Check if auto advancing
# auto_trigger = st.session_state.pending_input == AUTO_TRIGGER_TOKEN



# # Chat form (disabled in auto mode)
# with st.form("chat_form", clear_on_submit=True):
#     user_input = st.text_area(
#         "Type your message:",
#         value=st.session_state.pending_input if not auto_trigger else "",
#         key="input_field",
#         disabled=st.session_state.is_processing or auto_trigger
#     )
#     submitted = st.form_submit_button("Send", disabled=st.session_state.is_processing or auto_trigger)

# # Simulate submission in auto mode
# if auto_trigger:
#     submitted = True
#     user_input = st.session_state.pending_input

# # Handle submission
# if submitted and (user_input.strip() or auto_trigger):
#     st.session_state.is_processing = True

#     if not auto_trigger:
#         st.session_state.pending_input = user_input.strip()
#         st.session_state.chat_history.append({
#             "role": "user",
#             "content": st.session_state.pending_input
#         })

#     handle_bot_response()
   
#     st.session_state.is_processing = False
#     st.rerun()



# # -------------------- sidebar ----------------------

# st.sidebar.title("PropAgent")
# st.sidebar.subheader("Lead Details")
# add_selectbox = st.sidebar.selectbox(
#     'How would you like to be contacted?',
#     ('Email', 'Home phone', 'Mobile phone')
# )

# # Add a slider to the sidebar:
# add_slider = st.sidebar.slider(
#     'Select a range of values',
#     0.0, 100.0, (25.0, 75.0)
# )
# # Push down content with empty markdown
# st.markdown("<div style='height:70vh'></div>", unsafe_allow_html=True)

# # Group widgets in a container (renders after the pushed space)
# with st.container():
#     st.text_area("Type your message here...", height=100)
#     st.button("Send")

# st.write("**Helper Prompts**")
# express, standard, detailed = st.columns([1, 1, 1])
# with express:
#     st.button("Express")
#     st.write("Create proposal using default panels & inverters.")
# with standard:
#     st.button("Standard")
#     st.write("Fetch Genability data, then create proposal.")
# with detailed:
#     st.button("Detailed")
#     st.write("Review Genability & design before proposal.")

# col1, col2 = st.columns([1,1])
# with col1:
#     selected_month = st.selectbox("Select a month", ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"])
# with col2:
#     consumption_amount = st.number_input("Enter amount")
# st.button("Confirm", on_click=handle_month_consumption, args=(selected_month, consumption_amount))



