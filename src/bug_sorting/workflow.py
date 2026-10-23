# region Imports
from typing import List

from agno.workflow import Router
from dotenv import load_dotenv

from bug_sorting.models import CleanedFeedback

load_dotenv() # Carica le variabili d'ambiente dal file .env

from agno.tools import tool
from agno.workflow.workflow import Workflow

# agenti
from bug_sorting.agents import filterInputAgent, formatFeedbackAgent, discardFeedbackAgent 

# endregion

# region Workflow

class BugSortingWorkflow(Workflow):
    def run(self, user_input: str): 
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

# endregion

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