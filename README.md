# BugSorting

BugSorting è un sistema intelligente il cui scopo è raccogliere e filtrare i feedback riguardanti un videogioco inviati dalla community tramite un canale Discord per aiutare il lavoro degli sviluppatori indipendenti.

## Deployment

Per testarlo rapidamente senza il bisogno di creare un server Discord è necessario innanzitutto accedere nel server Discord che abbiamo usato per il testing durante lo sviluppo. Forniremo il link e il token nella mail di consegna.

### 1. Variabili d'ambiente
Una volta effettuato l'accesso è necessario scaricare il codice e creare un file .env nella root del progetto per inserire le seguenti variabili:
```
- GOOGLE_API_KEY
    - necessaria per gli agenti AI 
- DISCORD_BOT_TOKEN
    - necessario per identificare l'applicazione Discord a cui si lega (fornito nella consegna)
- FEEDBACK_CHAT_ID
    - identificatore del canale #segnalazione-bug
- DEVELOPER_CHAT_ID
    - identificatore del canale #developer-only

- HF_TOKEN [OPZIONALE]
    - token legato al proprio account di Hugging Face, utilizzato per rendere il download del modello di embedding locale più rapido
```

### 2. Installazione delle dipendenze

Il progetto utilizza uv come gestore dei pacchetti. Per sincronizzare le dipendenze esegui questo comando nella cartella root del progetto:
```bash
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

Una volta avviato il programma, si può notare come l'utente Bugsorting con label APP all'interno appaia ora online. Se l'utente è già online significa che c'è già un'altra istanza attiva, averne due causa la duplicazione di tutte le operazioni effettuate.

### 1. Inserimento Segnalazione
Nel canale #segnalazione-bug, l'utente descrive il bug in linguaggio naturale, senza dover seguire template prestabiliti.
* Appena il messaggio viene inviato, il bot aggiunge una reazione ⌛ per confermare la presa in carico.
* Al termine dell'estrazione semantica, il bot rimuove la clessidra e assegna ✅ se il bug è stato elaborato con successo, o ❌ se il testo è stato scartato (es. off-topic, spam) o se ci sono stati problemi con i modelli AI (token terminati o modelli irraggiungibili a causa del traffico a cui sono sottoposte; solitamente questo problema avviene dopo le 21).

### 2. Validazione Feedback
Nel canale #developer-only, il sistema genera un Embed riassuntivo contenente i dati estratti e categorizzati dall'LLM. Sotto il messaggio sono presenti i controlli operativi:

* **Bottone APPROVA:** Accetta il feedback. Lo stato viene aggiornato e i dati vettoriali vengono inseriti in LanceDB per fungere da confronto per le future segnalazioni.
* **Bottone RIFIUTA:** Scarta il feedback aggiornandone lo stato.
* **Bottone MODIFICA:** Apre un modale che permette al moderatore di sovrascrivere manualmente il titolo, la categoria, la gravità o la piattaforma in caso di allucinazioni da parte dell'AI.
* **Menu "Segna come duplicato...":** Questo menu a tendina appare **solo** se il motore vettoriale ha riscontrato un'alta similitudine semantica con feedback già approvati in passato. Selezionando una voce, il feedback corrente viene chiuso e contrassegnato come duplicato del bug originale selezionato.