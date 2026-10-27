# BugSorting

BugSorting è un sistema intelligente il cui scopo è raccogliere e filtrare i feedback riguardanti un videogioco inviati dalla community tramite un canale Discord per aiutare il lavoro degli sviluppatori indipendenti.

## Deployment rapido

Per testarlo rapidamente senza il bisogno di creare un server Discord è necessario innanzitutto accedere nel server Discord che abbiamo usato per il testing durante lo sviluppo. Forniremo il link e il token nella mail di consegna.

### 1. Variabili d'ambiente
Una volta effettuato l'accesso al server, scaricare il progetto da github e creare un file .env nella root per inserire le seguenti variabili:
```
- GOOGLE_API_KEY
    - necessaria per gli agenti AI.
- DISCORD_BOT_TOKEN
    - necessario per identificare l'applicazione Discord a cui si lega (fornito nella consegna).
- FEEDBACK_CHAT_ID
    - identificatore del canale #segnalazione-bug.
- DEVELOPER_CHAT_ID
    - identificatore del canale #developer-only.

- HF_TOKEN [OPZIONALE]
    - token legato al proprio account di Hugging Face utilizzato per rendere il download del modello di embedding locale più rapido.
```

### 2. Installazione delle dipendenze

Il progetto utilizza uv come gestore dei pacchetti. Per sincronizzare le dipendenze eseguire questi comandi nella cartella root del progetto:
```bash
uv venv
.venv\Scripts\activate
uv sync
```

### 3. Esecuzione
Per eseguire il codice eseguire il comando:
```bash
uv run .\src\bug_sorting\discord_bot.py
```
L'avvio a me richiede dai 30 secondi ai 2 minuti, con una connessione rapida è probabile che questo tempo sia ridotto.

### 4. Esempio di flusso di lavoro

Una volta avviato il programma, si può notare come l'utente **Bugsorting** con label APP all'interno del server appaia ora online. Se l'utente è già online prima dell'avvio, significa che c'è già un'altra istanza attiva, averne due causa la duplicazione di tutte le operazioni effettuate.

#### 1. Inserimento Segnalazione
Nel canale **#segnalazione-bug**, l'utente descrive il bug in linguaggio naturale, senza dover seguire template prestabiliti.
- Appena il messaggio viene inviato, il bot aggiunge una reazione ⌛ per confermare la presa in carico.
- Al termine dell'elaborazione, il bot rimuove la clessidra e assegna ✅ se il bug è stato elaborato con successo, o ❌ se il testo è stato scartato (es. off-topic, spam) o se ci sono stati problemi con i modelli AI (token terminati o modelli irraggiungibili a causa del traffico a cui sono sottoposte; quest'ultimo problema sembra accentuarsi nelle ore serali e accade sporadicamente durante il giorno).

#### 2. Validazione Feedback
Nel canale **#developer-only**, il sistema genera un Embed riassuntivo contenente i dati estratti e categorizzati dall'LLM. Sotto il messaggio sono presenti i seguenti pulsanti:

- **Pulsante APPROVA:** Accetta il feedback. Lo stato viene aggiornato e i dati vettoriali vengono inseriti in LanceDB per fungere da confronto per le future segnalazioni.
- **Pulsante RIFIUTA:** Scarta il feedback aggiornandone lo stato.
- **Pulsante MODIFICA:** Apre un modale che permette al moderatore di sovrascrivere manualmente il titolo, la categoria, la gravità o la piattaforma in caso di allucinazioni da parte dell'AI.
- **Menù "Segna come duplicato...":** Questo menù a tendina appare **solo** se il motore vettoriale ha riscontrato un'alta similitudine semantica con feedback già approvati in passato. Selezionando una voce, il feedback corrente viene chiuso e contrassegnato come duplicato del bug originale selezionato.

## Test

### Test 1: Estrazione dei dati e filtraggio delle informazioni non rilevanti

Input
```
Ciao, oggi mentre giocavo mi è successa una cosa strana. Ero fuori dal castello e stavo combattendo la guardia davanti al portone. Arrivato alla seconda fase, la mia spada è sparita. Ho riavviato il gioco e la spada non è tornata. Ho farmato un paio d'ore per trovarla e ora non c'è più, spero risolviate al più presto, incompetenti! Gioco da PS5.
```

Dati filtrati:
```
content='Ero fuori dal castello e stavo combattendo la guardia davanti al portone. Arrivato alla seconda fase, la mia spada è sparita. Ho riavviato il gioco e la spada non è tornata. Gioco da PS5.' valid=True
```

Dati formattati:
```
{
    "title": "Sparizione spada nella seconda fase della guardia",
    "description": "Durante il combattimento con la guardia fuori dal castello, arrivato alla seconda fase, la spada del personaggio è sparita e non è ricomparsa nemmeno dopo il riavvio del gioco.",
    "category": "bug",
    "severity": "high",
    "platform": "PS5",
    "steps_to_reproduce": [
        "Andare fuori dal castello",
        "Iniziare il combattimento con la guardia davanti al portone",
        "Arrivare alla seconda fase del combattimento"
    ],
    "error_message": "",
    "additional_context": "Il problema si è verificato fuori dal castello contro la guardia del portone."
}
```

### Test 2: Messaggio non rilevante
Input
```
Il vostro gioco fa schifo, spero che falliate!
```

Dati filtrati:
```
content='' valid=False
```

Dati formattati: nessuno, il flusso viene fermato prima.

### Test 3: Segnalazione con dati mancanti
Input
```
Stavo giocando la nuova patch e i miei dati di salvataggio sono scomparsi
```

Dati filtrati:
```
content='I miei dati di salvataggio sono scomparsi dopo la nuova patch.' valid=True
```

Dati formattati:
```
{
    "title": "Dati di salvataggio scomparsi",
    "description": "I miei dati di salvataggio sono scomparsi dopo la nuova patch.",
    "category": "bug",
    "severity": "critical",
    "platform": "UNKNOWN",
    "steps_to_reproduce": [],
    "error_message": "",
    "additional_context": "Dopo la nuova patch"
}
```

### Test 4: Deduplicazione:
Input
```
Non è possibile succedano cose del genere! Stavo giocando da PS5, sono riuscito finalmente a superare il dungeon del vulcano e sono arrivato al castello. Stavo per fare la guardia al first try e appena è entrata in seconda fase la mia alabarda è sparita facendomi sconfiggere. L'ultimo checkpoint era all'inizio del vulcano  e ora devo rifare tutto.
```

Dati filtrati:
```
content="Stavo giocando da PS5. Appena il boss è entrato in seconda fase la mia alabarda è sparita facendomi sconfiggere. L'ultimo checkpoint era all'inizio del vulcano." valid=True
```

Dati formattati:
```
{
    "title": "Sparizione alabarda nella seconda fase del boss",
    "description": "Durante la seconda fase del combattimento con il boss, l'alabarda del personaggio è sparita improvvisamente causando la sconfitta. L'ultimo checkpoint utile si trovava all'inizio del vulcano.",
    "category": "bug",
    "severity": "high",
    "platform": "PS5",
    "steps_to_reproduce": [
        "Entrare nel combattimento contro il boss",
        "Portare il boss alla seconda fase"
    ],
    "error_message": "",
    "additional_context": "L'utente stava giocando su PS5 ed è resuscitato all'inizio del vulcano dopo la sconfitta."
}
```

Nell'embed di Discord è apparso un menù a tendina con gli identificatori dei feedback ritenuti simili attraverso la ricerca nel database vettoriale. In questo caso è apparso selezionabile il feedback inserito nel test 1.

### Test 4: Nuovo feedback e modifica ai dati
Input
```
stavo andando a cavallo sella zona della neve e il gioco è calato sotto i 30 fps. considerando che uso una rtx5090 non penso il problema sia mio, ma vostro. imparate ad ottimizzare il gioco prima di pubblicarlo da niocoloco
```

Dati filtrati:
```
content='Stavo andando a cavallo nella zona della neve e il gioco è calato sotto i 30 fps. Uso una RTX 5090.' valid=True
```

Dati formattati:
```
{
    "title": "Calo di frame rate nella zona della neve",
    "description": "Il gioco è calato sotto i 30 fps mentre andavo a cavallo nella zona della neve.",
    "category": "performance_issue",
    "severity": "medium",
    "platform": "PC",
    "steps_to_reproduce": [
        "Andare a cavallo nella zona della neve"
    ],
    "error_message": "",
    "additional_context": "Uso una RTX 5090"
}
```

Dall'embed di Discord è possibile modificare i valori assegnati dall'agente. Ad esempio la severity a medium, abbassabile in questo caso a low. Si può anche notare come la piattaforma sia diventata PC senza specificarlo, in questo caso è corretto, ma la funzione di modifica è implementata per risolvere eventuali allucinazioni.
Inoltre in questo caso non appare il menù a tendina in quanto il feedback non è simile ad altri precedentemente inseriti.

### Test 5: Riavvio del bot con feedback 'pending'
Inserendo un feedback e riavviando il bot, i pulsanti rimangono funzionanti ed è possibile interagire con i feedback inviati prima del riavvio.

## Deployment nel proprio server Discord

1. Accedere a Discord Developer Portal (https://discord.com/developers/applications).
2. In alto a destra premere su **Create**.
3. All'interno della scheda aperta, premere in alto a destra su **Crea app nuova** e assegnare un nome all'applicazione.
4. Accedere al menù **Bot** e premere su **Reset Token**. Copiare la stringa ottenuta, sarà il valore della variabile DISCORD_BOT_TOKEN da inserire nel file .env.
5. Sotto **Privileged Gateway Intents** abilitare **Message Content Intents** necessario per leggere i messaggi nei canali.
6. Generare l'URL di invito nella sezione **OAuth2** -> **URL Generator**. Sotto la colonna **ambiti** premere **bot**. Una volta premuto si aprirà la schermata bot permission, bisogna selezionare **Visualizzare i canali**, **Leggere la cronologia dei messaggi**, **Invia messaggi**, **Aggiungere reazioni** e **Incorporare i link**.
7. Una volta fatto tutto si può generare il link scegliendo **Installazione per guild**.
8. Una volta ottenuto il link è sufficiente incollarlo nella barra di ricerca del browser e selezionare nella pagina che si apre il server nella quale si vuole implementare il sistema.
9. Aprire il client di Discord, andare in **Impostazioni utente** -> **Avanzate** e attivare **Modalità sviluppatore**.
10. Creare all'interno del server due canali, uno per l'invio dei feedback e uno per i moderatori.
11. Fare tasto destro sui canali e premere su copia ID. Assegnare questi valori nel file .env rispettivamente alle chiavi FEEDBACK_CHAT_ID e DEVELOPER_CHAT_ID.
