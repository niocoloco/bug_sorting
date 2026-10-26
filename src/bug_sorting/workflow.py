from typing import List

from agno.workflow import Router
from dotenv import load_dotenv

from bug_sorting.models import CleanedFeedback

load_dotenv() # Carica le variabili d'ambiente dal file .env

from agno.tools import tool
from agno.workflow.workflow import Workflow

from bug_sorting.agents import filterInputAgent, formatFeedbackAgent, discardFeedbackAgent 


class BugSortingWorkflow(Workflow):
    """
    Workflow per la pulizia, classificazione e formattazione dei feedback degli utenti.
    Questo workflow utilizza tre agenti:
    1. filterInputAgent: Filtra il rumore dai feedback in input degli utenti e restituisce solo il testo rilevante.
    2. formatFeedbackAgent: Formatizza il testo non strutturato all'interno di uno schema formale.
    3. discardFeedbackAgent: Offre una breve motivazione sul motivo per la quale il feedback è stato scartato.
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
        
        # se per qualche motivo il risultato non è stato formattato, lo scarta
        if not isinstance(cleaned_data, CleanedFeedback):
            return discardFeedbackAgent.run(user_input)
        
        # se il risultato è considerato non valido lo scarta
        if not cleaned_data.valid:
            # passa l'input all'agente per scartare, in modo che possa scrivere un messaggio con le motivazioni
            return discardFeedbackAgent.run(user_input)
        else:
            # passa il testo pulito all'agente di formattazione
            return formatFeedbackAgent.run(cleaned_data.content)

# istanza del workflow
bugSortingWF = BugSortingWorkflow(
    name="BugSortingWorkflow",
    description="Pipeline per la pulizia dell'input, classificazione e formattazione dei feedback degli utenti."
)