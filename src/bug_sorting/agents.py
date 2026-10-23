from agno.agent import Agent
from agno.models.google import Gemini
from bug_sortingv1_0.models import FormattedFeedback, CleanedFeedback

MODEL = Gemini(id="gemini-3.5-flash-lite")

filterInputAgent = Agent(
    model=MODEL,
    description="Filtra il rumore dai feedback in input degli utenti e restituisce solo il testo rilevante.",
    instructions=[
        "Il tuo compito è quello di filtrare il rumore dai feedback degli utenti e restituire solo il testo rilevante.",
        "Elimina elementi come insulti, lamentele generiche sul software e commenti non pertinenti.",
        "Non scartare i dettagli sull'hardware o sull'ambiente di gioco. Se presenti, inseriscili sempre.",
        "Se il testo esprime solo lamentele, insulti o non contiene alcun dettaglio tecnico su un bug, devi impostare 'valid' a false e 'content' come stringa vuota.",
        "Input: 'Il software fa schifo vi odio!!!'",
        "Output: content='', valid=false",
        "Input: 'Siete dei cani! Ogni volta che provo ad esportare in PDF il programma si blocca. Siete una vergogna!!!'",
        "Output: content='Ogni volta che provo ad esportare in PDF il programma si blocca.', valid=true"
    ],
    markdown=False,
    output_schema=CleanedFeedback
)

formatFeedbackAgent = Agent(
    model=MODEL,
    output_schema=FormattedFeedback,
    description="Formatta il testo non strutturato all'interno di uno schema formale.",
    instructions=["Analizza il testo fornito e classifica la gravità del bug.",
                  "La piattaforma è il dispositivo sulla quale gira il gioco (es. PC, PS5, Xbox, Switch, Android, iOS).",
                  "Se la piattaforma non è specificata, imposta il campo 'platform' su 'UNKNOWN'.",
                  "Se non sono forniti passaggi per riprodurre il problema, imposta 'steps_to_reproduce' come lista vuota.",
                  "Se non è fornito alcun messaggio di errore, imposta 'error_message' come stringa vuota.",
                  "Il contesto aggiuntivo è un campo opzionale che può contenere informazioni aggiuntive sul feedback, come la scheda grafica utilizzata, patch del gioco, dov'era l'utente nel gioco, quando si è verificato il problema, ecc..",
                  "Se non è fornito alcun contesto aggiuntivo, imposta 'additional_context' come stringa vuota."
    ]
)

# TODO: capire se eliminare (o sostituire con un messaggio statico)
discardFeedbackAgent = Agent(
    model=MODEL,
    description="Offre una breve motivazione sul motivo per la quale il feedback è stato scartato.",
    instructions=[
        "Il messaggio fornito è stato classificato come irrilevante.",
        "Genera una risposta sintetica in cui spieghi che il feedback è stato scartato perché privo di informazioni tecniche utili."
    ]
)