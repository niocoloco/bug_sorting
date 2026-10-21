# region Imports
from typing import List

from agno.workflow import Router
from dotenv import load_dotenv

from bug_sortingv1_0.models import CleanedFeedback

load_dotenv() # Carica le variabili d'ambiente dal file .env

from pydantic import BaseModel, Field
import json
from pathlib import Path
from agno.db.sqlite import SqliteDb
from agno.os import AgentOS
from agno.tools import tool
from agno.tools.reasoning import ReasoningTools
from agno.workflow.step import Step, StepInput, StepOutput
from agno.workflow.workflow import Workflow
from agno.knowledge.knowledge import Knowledge
from agno.knowledge.embedder.google import GeminiEmbedder
from agno.vectordb.lancedb import LanceDb, SearchType
from agno.learn import (
    LearningMachine,
    LearningMode,
    UserProfileConfig,
    UserMemoryConfig,
)

# agenti
from bug_sortingv1_0.agents import filterInputAgent, formatFeedbackAgent, discardFeedbackAgent 

# endregion

# region Workflow

class BugSortingWorkflow(Workflow):
    def run(self, user_input: str):
        # 1. Filtra l'input originale tramite il primo agente
        filter_response = filterInputAgent.run(user_input)
        cleaned_data = filter_response.content
        
        # Gestione in caso di mancato rispetto dello schema da parte del modello
        if not isinstance(cleaned_data, CleanedFeedback):
            return discardFeedbackAgent.run(user_input)
        
        # 2. Indirizza il flusso analizzando il flag booleano
        if not cleaned_data.valid:
            # Passa l'input originale all'agente di scarto per fargli capire cosa sta rifiutando
            return discardFeedbackAgent.run(user_input)
        else:
            # Passa solo il testo ripulito all'agente di formattazione
            return formatFeedbackAgent.run(cleaned_data.content)

bugSortingWF = BugSortingWorkflow(
    name="BugSortingWorkflow",
    description="Pipeline per la pulizia dell'input, classificazione e formattazione dei feedback degli utenti."
)

# endregion

# region Test
#if __name__ == "__main__":
#    response = bugSortingWF.run(
#        "Vi odio, non funziona nulla, è tutto un disastro! Non capisco perché non riuscite a fare un software decente. Spero che prendiate sul serio questo feedback e miglioriate il vostro prodotto."
#    )
#
#    if isinstance(response.content, BaseModel):
#        print(response.content.model_dump_json(indent=4))
#    else:
#        print("Risultato testuale:\n", response.content)
#
#    response = bugSortingWF.run(
#        "Ciao, ho scaricato la patch 1.04. Siete degli incompetenti, avete rovinato il mio sabato sera! "
#        "Mio fratello stava guardando e si è messo a ridere. Se provo a equipaggiare la 'Spada Lunga' "
#        "mentre il personaggio sta saltando vicino a un muro nel dungeon 2, il modello "
#        "compenetra la geometria e il gioco crasha. Nei log di Unity compare "
#        "un 'NullReferenceException' nello script di movimento. Sto giocando su Steam Deck. "
#        "Sistemate questa spazzatura o chiedo il rimborso su Steam."
#    )
#
#    if isinstance(response.content, BaseModel):
#        print("Feedback formattato correttamente (JSON):\n")
#        print(response.content.model_dump_json(indent=4))
#    else:
#        print("Risultato testuale:\n", response.content)

# endregion