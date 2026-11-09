from typing import List

from agno.workflow import Router
from dotenv import load_dotenv

from bug_sorting.models import CleanedFeedback

load_dotenv() # Carica le variabili d'ambiente dal file .env

from agno.tools import tool
from agno.workflow.workflow import Workflow

from bug_sorting.agents import filterInputAgent, formatFeedbackAgent, filterDev, formatFixAgent

def bugSortingWF(user_input: str):
    """
    Workflow per la pulizia, classificazione e formattazione dei feedback degli utenti.
    Questo workflow utilizza due agenti:
    1. filterInputAgent: Filtra il rumore dai feedback in input degli utenti e restituisce solo il testo rilevante.
    2. formatFeedbackAgent: Formatta il testo non strutturato all'interno di uno schema formale.

    Args:
        user_input (str): Il feedback dell'utente da elaborare.
    Returns:
        dict: Il feedback formattato o un messaggio di scarto.
    """
    # chiama il primo agente per filtrare il feedback ricevuto in input
    filter_response = filterInputAgent.run(user_input)
    cleaned_data = filter_response.content
    print(f"Cleaned user data: {cleaned_data}")

    # se il risultato è considerato non valido lo scarta
    if not cleaned_data.valid:
        return "Il feedback è stato scartato perché privo di informazioni tecniche utili."
    # passa il testo pulito all'agente di formattazione
    else:
        return formatFeedbackAgent.run(cleaned_data.content)

def devFixWF(dev_message: str):
    """
    Workflow per la pulizia, classificazione e formattazione dei messaggi degli sviluppatori.
    Questo workflow utilizza due agenti:
    1. filterDev: Filtra il rumore dai messaggi degli sviluppatori riguardanti la risoluzione dei bug, restituendo solo le informazioni utili per identificare il ticket.
    2. formatFixAgent: Formatta il testo non strutturato all'interno di uno schema formale.

    Args:
        dev_message (str): Il messaggio dello sviluppatore da elaborare.
    Returns:
        dict: Il messaggio formattato o un messaggio di scarto.
    """

    #chiama il primo agente per filtrare il messaggio ricevuto in input
    filter_response = filterDev.run(dev_message)
    cleaned_data = filter_response.content

    print(f"Cleaned dev data: {cleaned_data}")

    # se il risultato è considerato non valido lo scarta
    if not cleaned_data.valid:
        return "Il messaggio è stato scartato perché privo di informazioni tecniche utili."
    # passa il testo pulito all'agente di formattazione
    else:
        return formatFixAgent.run(cleaned_data.content)
