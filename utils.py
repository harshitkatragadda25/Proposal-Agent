# # Define allowed mime types
# ALLOWED_MIME_TYPES = {
#     "application/pdf",
# }

# def get_mime_type(file_name: str, content: bytes) -> str:
#     # Guess mime type by file extension first
#     mime, _ = mimetypes.guess_type(file_name)
#     if mime:
#         return mime
#     # Fallback: use magic detection (optional)
#     return "application/octet-stream"


# async def upload_file(file: UploadFile = File(...)):
#     content = await file.read()
#     zip_buffer = io.BytesIO(content)

#     try:
#         with zipfile.ZipFile(zip_buffer, "r") as z:
#             valid_files = {}

#             for file_name in z.namelist():
#                 if file_name.endswith('/'):
#                     continue  # Skip folders

#                 file_data = z.read(file_name)

#                 mime_type = get_mime_type(file_name, file_data)

#                 if mime_type not in ALLOWED_MIME_TYPES:
#                     continue  # Skip disallowed files

#                 valid_files[file_name] = file_data  # Store valid file

#             if not valid_files:
#                 raise {"status_code":400, "detail":"No valid PDF file found."}

#             # Do something with `valid_files`, e.g., save or parse
#             return {
#                 "status": "success",
#                 "valid_files_received": list(valid_files.keys())
#             }

#     except zipfile.BadZipFile:
#         raise {"status_code":400, "detail":"Uploaded file is not a valid ZIP."}
    
    
from langchain.prompts import PromptTemplate
# from pdfminer.high_level import extract_text

electricity_rate_extraction_prompt = PromptTemplate(
    input_variables=["bill_text"],
    
    template = """
        You are a billing data extraction model.

        Given text extracted from a PG&E electricity bill PDF, 
        identify:
        • "month": the billing period month(e.g., "March"). Take the month from the Statement Date.
        • "usage": the total electricity consumption  that is in kWh for that period (e.g., 312.564)

        Return ONLY a Valid Python JSON object with keys exactly:
        ["month","amount"]

        {bill_text}
        """
)

from dev import GEMINI_API_KEY

api_key=GEMINI_API_KEY



 
import google.generativeai as genai
 
import json
genai.configure(api_key=api_key)
 

llm = genai.GenerativeModel(model_name="gemini-2.5-pro")
 

def extract_files_from_base64_zip(base64_str: str):
    zip_bytes = base64.b64decode(base64_str)
    zip_file = zipfile.ZipFile(BytesIO(zip_bytes))

    extracted = {}
    for name in zip_file.namelist():
        if name.lower().endswith(".pdf"):  # Filter only PDFs
            with zip_file.open(name) as f:
                extracted[name] = f.read()
    return extracted  # dict of {filename: binary_content}



def extract_bill_text(path):
    return extract_text(path)



def extract_electricity_bill(bill_text):
    # text = extract_bill_text(PDF_FILE)  
    # extracted_files = extract_files_from_base64_zip(base64_str)
    # all_texts = []

    # for filename, file_bytes in extracted_files.items():
    #     pdf_text = extract_text_from_pdf_bytes(file_bytes)
    #     all_texts.append(f"From file {filename}:\n{pdf_text}")

    # bill_text = "\n\n".join(all_texts)  
    filled_prompt = electricity_rate_extraction_prompt.format(bill_text= bill_text)
    return llm.generate_content(filled_prompt).text


def get_details_from_google_maps_result(all_results: list = None):
    def extract_component(components, target_type):
        for component in components:
            if target_type in component.get("types", []):
                return component
        return None

    state = None
    country_code = None
    county = None
    city = None
    postal_code = None

    # Get state from primary result
    address_components = result.get("address_components", [])
    state_component = extract_component(address_components, "administrative_area_level_1")
    if state_component:
        state = state_component.get("long_name")

    if all_results:
        for result_item in all_results:
            component = extract_component(result_item.get("address_components", []), "country")
            if component:
                country_code = component.get("short_name")
                break

        for result_item in all_results:
            component = extract_component(result_item.get("address_components", []), "administrative_area_level_2")
            if component:
                county = component.get("long_name")
                break

        for result_item in all_results:
            component = extract_component(result_item.get("address_components", []), "locality")
            if component:
                city = component.get("long_name")
                break

        for result_item in all_results:
            component = extract_component(result_item.get("address_components", []), "postal_code")
            if component:
                postal_code = component.get("long_name")
                break
    else:
        country_component = extract_component(address_components, "country")
        if country_component:
            country_code = country_component.get("short_name")

        county_component = extract_component(address_components, "administrative_area_level_2")
        if county_component:
            county = county_component.get("long_name")

        city_component = extract_component(address_components, "locality")
        if city_component:
            city = city_component.get("long_name")

        postal_component = extract_component(address_components, "postal_code")
        if postal_component:
            postal_code = postal_component.get("long_name")

    return {
        "state": state,
        "countryCode": country_code,
        "postalCode": postal_code,
        "county": county,
        "city": city,
    }

