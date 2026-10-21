TODO List Completa e Aggiornata 
Fase 1: Setup Ambiente e Discord
    [X] 1.1 Inizializzazione Ambiente Python: Creare il virtual environment e installare le dipendenze (agno, pydantic, lancedb, sqlite3, discord.py, python-dotenv e gli SDK per Gemini/Mistral/Groq).   
    [X] 1.2 Setup Discord Developer Portal: Creare l'applicazione su Discord, generare il Token del Bot e attivare il Message Content Intent nelle impostazioni.
    [X] 1.3 Setup Server Discord di Test: Creare un server con due canali (#segnalazione-bug pubblico e #validazione-admin privato), invitare il bot con i permessi di lettura/scrittura/reazioni e salvare nel file .env il Token, le API key dei modelli free tier e gli ID dei due canali.
    [ ] 1.4 Scelta Modello di Embedding: Configurare il modello di embedding (locale o via API gratuita) per la vettorizzazione dei testi su LanceDB.
Fase 2: Struttura Dati e Database
    [X] 2.1 Definizione Schema Pydantic: Creare il modello Pydantic per la validazione del JSON (title, category, platform, severity, steps, error_message, additional_context) con fallback automatico sul valore UNKNOWN per i dati non deducibili.
    [ ] 2.2 Setup Database Relazionale (SQLite): Scrivere lo script di creazione della tabella su SQLite includendo i campi del JSON, status (pending, validated, rejected), is_potential_duplicate e duplicate_of_id.  
    [ ] 2.3 Setup Database Vettoriale (LanceDB): Configurare la tabella LanceDB per memorizzare l'ID del ticket di SQLite, il testo di riferimento e il vettore semantico.
Fase 3: Sviluppo Agenti AI (Agno)
    [ ] 3.1 Sviluppo Agente 1 (Filtro e Routing): Scrivere il prompt e configurare l'agente per intercettare spam, insulti o lamentele non tecniche, restituendo un token di scarto e la motivazione da mostrare all'utente.  
    [ ] 3.2 Sviluppo Agente 2 (Formattazione JSON): Configurare il secondo agente con il modello Pydantic (punto 2.1) per estrarre i dati tecnici e categorizzare il problema (BUG, PERFORMANCE_ISSUE, FEATURE_REQUEST, BALANCEMENT_REQUEST).
Fase 4: Pipeline Core e Deduplicazione
    [ ] 4.1 Funzione di Ricerca Semantica: Implementare la conversione in embedding del JSON generato dall'Agente 2 e la query su LanceDB per calcolare la distanza semantica rispetto ai bug già validati.
    [ ] 4.2 Definizione Soglia di Similarità: Calibrare il valore di threshold sotto il quale un report viene flaggato come potenziale duplicato.
    [ ] 4.3 Orchestrazione Backend (Steps 1-5): Unire in un'unica funzione Python il passaggio tra Agente 1, Agente 2, controllo su LanceDB e inserimento in stato pending su SQLite-
Fase 5: Bot Discord - Lato Utente (Input)
    [ ] 5.1 Listener Canale Pubblico: Programmare l'evento on_message per leggere i messaggi non strutturati inviati solo nel canale #segnalazione-bug.
    [ ] 5.2 Esecuzione Asincrona Pipeline: Incapsulare la funzione della pipeline (punto 4.3) in asyncio.to_thread per non bloccare il bot durante le chiamate agli LLM e ai database.
    [ ] 5.3 Risposta all'Utente: Configurare le reazioni (⏳, ❌, ✅) e la risposta automatica del bot nel canale pubblico (messaggio di scarto dell'Agente 1 oppure conferma di presa in carico del ticket).  
Fase 6: Bot Discord - Lato Operatore (Validazione HITL)7
    [ ] 6.1 Generazione Embed di Notifica: Scrivere la funzione che, subito dopo il salvataggio in pending, invia nel canale #validazione-admin un riepilogo visivo del JSON generato e degli eventuali duplicati trovati su LanceDB.
    [ ] 6.2 Creazione Discord Views (Bottoni): Implementare la classe discord.ui.View con i bottoni Approva, Modifica, Merge e Scarta collegati all'ID del record su SQLite.
    [ ] 6.3 Creazione Discord Modals (Pop-up di modifica): Implementare la classe discord.ui.Modal per permettere all'operatore di correggere il testo delle allucinazioni o di unire gli steps di un ticket duplicato direttamente da Discord.
    [ ] 6.4 Logica di Sincronizzazione Finale (Callbacks dei bottoni): Collegare i bottoni e i pop-up alle query di aggiornamento su SQLite (cambio stato a validated o rejected) e all'inserimento/aggiornamento definitivo del vettore su LanceDB.
Fase 7: Testing End-to-End
    [ ] 7.1 Preparazione Scenari di Test: Scrivere una decina di messaggi di prova (spam, bug completi, bug parziali per verificare i campi UNKNOWN, e segnalazioni duplicate scritte con parole diverse).
    [ ] 7.2 Simulazione Completa su Discord: Inviare i messaggi nel canale pubblico, verificare i filtri e usare i bottoni nel canale admin per validare i primi bug e testare il riconoscimento dei duplicati sugli invii successivi.   