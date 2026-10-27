from typing import List

from agno.workflow import Router
from dotenv import load_dotenv

from bug_sorting.models import CleanedFeedback

load_dotenv() # Carica le variabili d'ambiente dal file .env

from agno.tools import tool
from agno.workflow.workflow import Workflow

from bug_sorting.agents import filterInputAgent, formatFeedbackAgent#, discardFeedbackAgent 

class BugSortingWorkflow(Workflow):
    """
    Workflow per la pulizia, classificazione e formattazione dei feedback degli utenti.
    Questo workflow utilizza due agenti:
    1. filterInputAgent: Filtra il rumore dai feedback in input degli utenti e restituisce solo il testo rilevante.
    2. formatFeedbackAgent: Formatta il testo non strutturato all'interno di uno schema formale.
    """
    def run(self, user_input: str): 
        """
        Esecuzione del workflow.
        Args:
            user_input (str): Il feedback dell'utente da elaborare.
        Returns:
            dict: Il feedback formattato o un messaggio di scarto.
        """
        # chiama il primo agente per filtrare il feedback ricevuto in input
        filter_response = filterInputAgent.run(user_input)
        cleaned_data = filter_response.content
        print(f"Cleaned data: {cleaned_data}")
        
        # se il risultato è considerato non valido lo scarta
        if not cleaned_data.valid:
            return "Il feedback è stato scartato perché privo di informazioni tecniche utili."
        else:
            # passa il testo pulito all'agente di formattazione
            return formatFeedbackAgent.run(cleaned_data.content)

# istanza del workflow
bugSortingWF = BugSortingWorkflow(
    name="BugSortingWorkflow",
    description="Pipeline per la pulizia dell'input, classificazione e formattazione dei feedback degli utenti."
)
