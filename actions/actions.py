# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions


# This is a simple example for a custom action which utters "Hello World!"

# from typing import Any, Text, Dict, List
#
# from rasa_sdk import Action, Tracker
# from rasa_sdk.executor import CollectingDispatcher
#
#
# class ActionHelloWorld(Action):
#
#     def name(self) -> Text:
#         return "action_hello_world"
#
#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#
#         dispatcher.utter_message(text="Hello World!")
#
#         return []

from typing import Any, Text, Dict, List
from rasa_sdk import Tracker, FormValidationAction
from rasa_sdk.types import DomainDict
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk import Action, Tracker

from rasa_sdk.events import SlotSet

class ValidateProjectCreationForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_project_creation_form"

    def validate_project_name(
        self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        if not slot_value:
            dispatcher.utter_message(text="The project name cannot be empty.")
            return {"project_name": None}
        return {"project_name": slot_value}

    def validate_address(
        self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        if not slot_value:
            dispatcher.utter_message(text="The project address cannot be empty.")
            return {"address": None}
        return {"address": slot_value}
    
    from typing import Dict, Text, Any, List


class ActionCreateProject(Action):
    def name(self) -> Text:
        return "action_create_project"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        project_name = tracker.get_slot("project_name")
        address = tracker.get_slot("address")

        if not project_name or not address:
            dispatcher.utter_message(text="Project name or address is missing. Please provide both.")
            return []

        # Assume backend API call here to create the project
        # payload = {
        #     "project_name": project_name,
        #     "address": address
        # }
        # api_response = requests.post('http://api.example.com/create_project', json=payload)

        dispatcher.utter_message(text=f"Your project '{project_name}' at '{address}' has been successfully created.")
        return [SlotSet("project_name", None), SlotSet("address", None)]

