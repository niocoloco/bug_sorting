import discord
import asyncio
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from bug_sorting.workflow import bugSortingWF
from bug_sorting.vector_db import *
from bug_sorting.relational_db import *

load_dotenv()

# token identificatico dell'applicazione Discord che farà girare questo script
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# identificativo del canale in cui gli utenti possono scrivere i feedback
FEEDBACK_CHANNEL_ID = int(os.getenv("FEEDBACK_CHAT_ID"))
DEVELOPER_CHANNEL_ID = int(os.getenv("DEVELOPER_CHAT_ID"))

# gli intents definiscono quali eventi e dati Discord può inviare al bot
# crea gli intents predefiniti di discord
intents = discord.Intents.default()

# abilita la ricezione del contenuto testuale dei messaggi
intents.message_content = True

# istanzia il client del bot passando gli intents configurati
client = discord.Client(intents=intents)

# connessione al database vettoriale
v_db_conn = init_lancedb()

# region utilty

def find_similar_feedback(db, query_text: str, platform: str, category: str, top_k: int = 5) -> list[dict]:
    """
    Interroga il database vettoriale per trovare i feedback più semanticamente simili al testo in input.
    Utilizza una ricerca vettoriale basata su embedding semantici e filtra i risultati per piattaforma e categoria.
    Args:
        db: Connessione al database vettoriale.
        query_text (str): Testo del feedback da confrontare.
        platform (str): Piattaforma del feedback (es. "PC", "Android", "PS5", "Xbox Series X", ecc. ecc.).
        category (str): Categoria del feeback (es. "bug", "feature_request", "performance_issue", ecc. ecc.).
        top_k (int): Numero massimo di risultati da restituire.
    Returns:
        list[dict]: Lista di dizionari contenenti i feedback più simili.
    """

    # apertura della tabella dei feedback nel database vettoriale
    table = db.open_table("feedback_vectors")

    # esecuzione della ricerca vettoriale con filtro per piattaforma e categoria
    results = table.search(query_text) \
        .where(f"platform = '{platform}' AND category = '{category}'") \
        .limit(top_k) \
        .to_list()

    return results

def deduplicate_vector_feedback(feedback_data: BaseModel) -> list:
    """
    Esegue la deduplicazione dei feedback confrontando il testo del feedback in input con i feedback già presenti nel database vettoriale.
    Args:
        feedback_data (BaseModel): Oggetto contenente i dati del feedback da deduplicare.
    Returns:
        list: Lista di ID dei feedback duplicati.
    """

    ## trasforma gli step per riprodurre un bug (se presenti) in una stringa
    #steps = " ".join(feedback_data.steps_to_reproduce) if feedback_data.steps_to_reproduce else ""
#
    ## concatena titolo, descrizione, steps, messaggi di errore e contesto aggiuntivo in una stringa sola
    #testo_grezzo = f"{feedback_data.title} {feedback_data.description} {steps} {feedback_data.error_message} {feedback_data.additional_context}"
#
    ## rimuove eventuali spazi multipli e normalizza il testo
    #vector_text = " ".join(testo_grezzo.split())

    vector_text = genera_testo_embedding(
        titolo=feedback_data.title,
        descrizione=feedback_data.description,
        steps=feedback_data.steps_to_reproduce,
        error=feedback_data.error_message
    )

    # ricerca i valori simili
    risultati_grezzi = find_similar_feedback(
        db=v_db_conn, 
        query_text=vector_text, 
        platform=feedback_data.platform, 
        category=feedback_data.category.value, 
    )

    # soglia minima di similirità per considerare un feedback come duplicato 
    SOGLIA_DISTANZA = 0.85 

    # filtra i risultati per ottenere solo quelli che superano la soglia di distanza
    duplicati_validati = [record["feedback_id"] for record in risultati_grezzi if record["_distance"] <= SOGLIA_DISTANZA]
    
    return duplicati_validati

def create_feedback_embed(feedback_data: BaseModel, feedback_id: int, duplicates_info: list[tuple] = None) -> discord.Embed:
    """
    Crea un embed di Discord per visualizzare i dettagli del feedback elaborati dagli agenti.
    Args:
        feedback_data (BaseModel): Oggetto contenente i dati del feedback.
        feedback_id (int): ID del feedback nel database relazionale.
        duplicates_info (list[tuple], optional): Lista di tuple contenenti informazioni sui feedback duplicati, se presenti.
    Returns:
        discord.Embed: Embed di Discord contenente i dettagli del feedback.
    """
    color = discord.Color.red() if duplicates_info else discord.Color.green()
    embed = discord.Embed(
        title = f"Feedback #{feedback_id}: {feedback_data.title}",
        description = feedback_data.description,
        color = color
    )

    embed.add_field(name="Categoria", value=feedback_data.category.value, inline=True)
    embed.add_field(name="Gravità", value=feedback_data.severity.value, inline=True)
    embed.add_field(name="Piattaforma", value=feedback_data.platform, inline=True)
    embed.add_field(name="Passaggi per riprodurre", value="\n".join(feedback_data.steps_to_reproduce) if feedback_data.steps_to_reproduce else "Nessun dettaglio fornito", inline=False)
    embed.add_field(name="Messaggio di errore", value=feedback_data.error_message if feedback_data.error_message else "Nessun dettaglio fornito", inline=False)
    embed.add_field(name="Contesto aggiuntivo", value=feedback_data.additional_context if feedback_data.additional_context else "Nessun dettaglio fornito", inline=False)

    # se sono presenti dublicati, aggiunge un campo all'embed per elencarli
    if duplicates_info:
        testo_duplicati = "\n".join([f"• #{dup_id}: {dup_title}" for dup_id, dup_title in duplicates_info])
        embed.add_field(name="⚠️ Potenziali Duplicati", value=testo_duplicati[:1024], inline=False)

    return embed

class FeedbackModerationView(discord.ui.View):
    """
    View di Discord contenente i pulsanti per approvare, rifiutare o modificare un feedback.
    Se sono presenti duplicati, viene aggiunto un menù a tendina per selezionare il feedback originale a cui associare il record corrente.
    """
    def __init__(self, duplicate_ids: list[int] = None):
        """
        Inizializza la View di moderazione del feedback.
        Args:
            duplicate_ids (list[int], optional): Lista di ID dei feedback duplicati, se presenti.
        """
        # senza timeout il bot diventa persistente, altrimenti dopo il riavvio del bot i pulsanti diventano inutilizzabili
        super().__init__(timeout=None)

        # se sono presenti duplicati, aggiunge un menù a tendina
        if duplicate_ids:
            self.add_item(DuplicateSelect(duplicate_ids))

    # creazione dei callback per i pulsanti di approvazione, rifiuto e modifica del feedback
    @discord.ui.button(label="Approva", style=discord.ButtonStyle.green, custom_id="btn_approve")
    async def approve_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Callback per il pulsante di approvazione del feedback.
        Aggiorna lo stato del feedback nel database relazionale e inserisce il feedback nel database vettoriale.
        Args:
            interaction (discord.Interaction): L'interazione dell'utente con il pulsante.
            button (discord.ui.Button): Il pulsante premuto dall'utente.
        """

        # estrazione dell'embed del messaggio e dell'ID del feedback dal titolo dell'embed
        embed = interaction.message.embeds[0]
        feedback_id = int(embed.title.split("#")[1].split(":")[0])  # non potendo passare parametri al costruttore in quanto statico, dobbiamo estrarre l'id dal titolo

        # ricerca del feedback nel database relazionale
        feedback_data = await asyncio.to_thread(get_feedback_by_id, feedback_id)
        if not feedback_data:
            await interaction.response.send_message("Errore critico: Record non trovato in SQLite.", ephemeral=True)
            return

        # inserimento del feedback nel database vettoriale
        try:
            await asyncio.to_thread(insert_feedback_vector, feedback_data, v_db_conn)
        except Exception as e:
            await interaction.response.send_message(f"Errore di inserimento in LanceDB: {e}", ephemeral=True)
            return

        # aggiornamento dello stato del feedback nel database relazionale
        await asyncio.to_thread(update_feedback_status, feedback_id, "accepted")

        # disabilita tutti i pulsanti della view
        for child in self.children:
            child.disabled = True

        # modifica dell'embed per indicare che il feedback è stato approvato
        embed.color = discord.Color.green()
        embed.title = embed.title + " [APPROVATO]"

        # invio della risposta all'interazione e aggiornamento del messaggio originale con l'embed modificato
        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.followup.send(f"Feedback #{feedback_id} approvato.", ephemeral=True)

    @discord.ui.button(label="Rifiuta", style=discord.ButtonStyle.red, custom_id="btn_reject")
    async def reject_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Callback per il pulsante di rifiuto del feedback.
        Aggiorna lo stato del feedback nel database relazionale.
        Args:
            interaction (discord.Interaction): L'interazione dell'utente con il pulsante.
            button (discord.ui.Button): Il pulsante premuto dall'utente.
        """

        # estrazione dell'embed del messaggio e dell'ID del feedback dal titolo dell'embed
        embed = interaction.message.embeds[0]
        feedback_id = int(embed.title.split("#")[1].split(":")[0])  # non potendo passare parametri al costruttore in quanto statico, dobbiamo estrarre l'id dal titolo

        # aggiornamento dello stato del feedback nel database relazionale
        await asyncio.to_thread(update_feedback_status, feedback_id, "rejected")

        # disabilita tutti i pulsanti della View
        for child in self.children:
            child.disabled = True

        # modifica dell'embed per indicare che il feedback è stato rifiutato
        embed.color = discord.Color.red()
        embed.title = embed.title + " [RIFIUTATO]"

        # invio della risposta all'interazione e aggiornamento del messaggio originale con l'embed modificato
        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.followup.send(f"Feedback #{feedback_id} rifiutato.", ephemeral=True)

    @discord.ui.button(label="Modifica", style=discord.ButtonStyle.blurple, custom_id="btn_edit")
    async def edit_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Callback per il pulsante di modifica del feedback.
        Estrae i dati correnti del feedback dall'embed e apre un modal per la modifica dei campi.
        Utilizzato per correggere eventuali allucinazioni degli agenti.
        Args:
            interaction (discord.Interaction): L'interazione dell'utente con il pulsante
            button (discord.ui.Button): Il pulsante premuto dall'utente.
        """
        embed = interaction.message.embeds[0]
        feedback_id = int(embed.title.split("#")[1].split(":")[0])  # non potendo passare parametri al costruttore in quanto statico, dobbiamo estrarre l'id dal titolo

        # estrazione dei valori correnti dai campi dell'embed
        cur_title = embed.title.split(": ")[1]
        cur_category = embed.fields[0].value
        cur_severity = embed.fields[1].value
        cur_platform = embed.fields[2].value

        # apertura del modal per la modifica dei campi del feedback
        modal = EditFeedbackModal(feedback_id, cur_title, cur_category, cur_severity, cur_platform)

        # invio del modal all'utente che ha interagito con il pulsante
        await interaction.response.send_modal(modal)


class EditFeedbackModal(discord.ui.Modal, title="Modifica feedback"):
    """
    Modal di Discord per la modifica dei campi del feedback.
    Permette di correggere eventuali errori o allucinazioni degli agenti.
    Non è possibile modificare tutti i campi in quanto il modale ha un limite di 5 campi; sono stti scelti i campi più critici per la gestione del feedback.
    """

    # definizione dei campi del modal per la modifica dei dati del feedback
    titolo = discord.ui.TextInput(label="Titolo", style=discord.TextStyle.short)
    categoria = discord.ui.TextInput(label="Categoria", style=discord.TextStyle.short)
    gravita = discord.ui.TextInput(label="Gravità", style=discord.TextStyle.short)
    piattaforma = discord.ui.TextInput(label="Piattaforma", style=discord.TextStyle.short)

    def __init__(self, feedback_id: int, cur_title: str, cur_category: str, cur_severity: str, cur_platform: str):
        """
        Inizializza il modal per la modifica dei dati del feedback.
        Args:
            feedback_id (int): ID del feedback nel database relazionale.
            cur_title (str): Titolo del feedback.
            cur_category (str): Categoria del feedback.
            cur_severity (str): Gravità del feedback.
            cur_platform (str): Piattaforma del feedback.
        """
        super().__init__()
        self.feedback_id = feedback_id
        self.titolo.default = cur_title
        self.categoria.default = cur_category
        self.gravita.default = cur_severity
        self.piattaforma.default = cur_platform

    async def on_submit(self, interaction: discord.Interaction):
        """
        Definisce il comportamento del modale quando l'utente invia i dati modificati.
        Aggiorna i dati del feedback nel database relazionale e modifica l'embed del messaggio originale per riflettere le modifiche.
        Args:
            interaction (discord.Interaction): L'interazione dell'utente con il modale.
        """

        # aggiornamento del feedback nel database relazionale
        await asyncio.to_thread(update_feedback_data,
            feedback_id=self.feedback_id,
            feedback_title=self.titolo.value,
            feedback_category=self.categoria.value,
            feedback_severity=self.gravita.value,
            feedback_platform=self.piattaforma.value
        )

        # aggiornamento dell'embed di Discord
        embed = interaction.message.embeds[0]
        embed.title = f"Feedback #{self.feedback_id}: {self.titolo.value}"
        embed.set_field_at(0, name="Categoria", value=self.categoria.value, inline=True)
        embed.set_field_at(1, name="Gravità", value=self.gravita.value, inline=True)
        embed.set_field_at(2, name="Piattaforma", value=self.piattaforma.value, inline=True)

        await interaction.response.edit_message(embed=embed)
        await interaction.followup.send(f"Dati del feedback #{self.feedback_id} corretti.", ephemeral=True)

class DuplicateSelect(discord.ui.Select):
    """
    Select di Discord per la selezione del feedback originale a cui associare il record corrente in caso di duplicato.
    Viene mostrato solo se sono stati trovati duplicati durante l'elaborazione del feedback. L'utente può selezionare un solo feedback originale a cui associare il record corrente.
    """
    def __init__(self, duplicates_info: list[tuple]):
        """
        Inizializza il select.
        Args:
            duplicates_info (list[tuple]): Lista di tuple contenenti l'ID e il titolo dei feedback duplicati.
        """

        # creazione delle opzioni del select a partire dai duplicati trovati
        options = []

        # inserisce i titoli a partire dall'id dei duplicati
        for dup_id, dup_title in duplicates_info:
            # troncamento di sicurezza per rispettare i limiti di Discord (100 caratteri per il label)
            label_text = f"#{dup_id} - {dup_title}"[:100]
            # aggiunta dell'option al select
            options.append(discord.SelectOption(label=label_text, value=str(dup_id)))
        super().__init__(placeholder="Segna come duplicato di ", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        """
        Callback per il select di duplicati.
        Aggiorna lo stato del feedback corrente come duplicato del feedback selezionato e disabilita l'interfaccia.
        """

        # estrazione dell'ID del feedback originale selezionato dal select
        original_feedback_id = int(self.values[0])
        
        embed = interaction.message.embeds[0]
        current_feedback_id = int(embed.title.split("#")[1].split(":")[0]) # non potendo passare parametri al costruttore in quanto statico, dobbiamo estrarre l'id dal titolo

        # aggiorna lo stato del feedback corrente come duplicato del feedback originale selezionato
        await asyncio.to_thread(mark_as_duplicate, current_feedback_id, original_feedback_id)
        
        # disabilita tutti i pulsanti della view per evitare ulteriori interazioni
        for child in self.view.children:
            child.disabled = True
        
        embed.color = discord.Color.orange()
        embed.title = embed.title + " [DUPLICATO]"
        
        await interaction.response.edit_message(embed=embed, view=self.view)
        await interaction.followup.send(f"feedback #{current_feedback_id} archiviato come duplicato di #{original_feedback_id}.", ephemeral=True)
# endregion

# funzione che si attiva quando il bot fa il login per connettersi ai server di discord
@client.event
async def on_ready():
    """
    Definisce il comportamento del bot quando si connette a Discord.
    Inizializza il database relazionale e aggiunge la view di moderazione dei feedback.
    """
    # stampa del nome del bot
    print(f'Bot connesso come {client.user}')
    init_db() #inizializza il database relazionale
    client.add_view(FeedbackModerationView())

@client.event
async def on_message(message):
    """
    Definisce il comportamento del bot quando riceve un messaggio.
    In questo caso viene limitato solo ai messaggi ricevuti nel canale #segnalazione-bug e non risponde a se stesso.
    Args:
        message (discord.Message): Il messaggio ricevuto dal bot.
    """
    # ignora i messaggi inviati da se stesso
    if message.author == client.user:
        return
        
    # ignora i messaggi ricevuti al di fuori del canale #segnalazione-bug (altrimenti risponderebbe a qualsiasi messaggio ricevuto)
    if message.channel.id != FEEDBACK_CHANNEL_ID:
        return

    await message.add_reaction("⌛") # aggiunge una reazione 'clessidra' al messaggio in attesa di elaborazione
    print(f"Messaggio ricevuto: {message.content} da {message.author}") # stampa del messaggio ricevuto (debug)

    try:
        risultato = await asyncio.to_thread(bugSortingWF, message.content)  # esegue la funzione di elaborazione del feedback in un thread separato per non bloccare l'evento principale
        await message.remove_reaction("⌛", client.user) # rimuove la reazione 'clessidra' dal messaggio una volta finita l'elaborazione.

        # l'unico risultato del workflow risultante in un BaseModel è quello in cui il testo di input era valido
        if hasattr(risultato, 'content') and isinstance(risultato.content, BaseModel):
            feedback_estratto = risultato.content
            
            # esecuzione della deduplicazione
            id_duplicati = await asyncio.to_thread(deduplicate_vector_feedback, feedback_estratto)

            # se sono stati trovati duplicati, recupera le informazioni dei feedback duplicati per mostrarle nel menù a tendina
            info_duplicati = await asyncio.to_thread(get_feedback_summaries, id_duplicati) if id_duplicati else []

            # se sono stati trovati duplicati, imposta il flag is_potential_duplicate a 1
            is_potential_duplicate = 1 if id_duplicati else 0

            # inserisce il feedback nel database relazionale e ottiene l'ID del nuovo record
            new_feedback_id = await asyncio.to_thread(insert_feedback, feedback_estratto, is_potential_duplicate=is_potential_duplicate)

            # ottenimento del canale sviluppatori per inviare l'embed con i dettagli del feedback
            dev_channel = client.get_channel(DEVELOPER_CHANNEL_ID)

            # controllo per verificare che il canale sia stato trovato
            if not dev_channel:
                print("Errore: Canale sviluppatori non trovato.")
                return

            # creazione dell'embed con i dati del feedback
            embed_feedback_for_dev = create_feedback_embed(feedback_estratto, new_feedback_id, duplicates_info=info_duplicati)
            # invio dell'embed al canale sviluppatori con la view di moderazione dei feedback
            await dev_channel.send(embed=embed_feedback_for_dev, view=FeedbackModerationView(duplicate_ids=info_duplicati))

            # stampa a console per debug
            if id_duplicati:
                print(f"ATTENZIONE: Possibili duplicati trovati con ID: {id_duplicati}.")
                print(f"Nuovo feedback inserito con ID: {new_feedback_id}.")
            else:
                print(f"Nuovo feedback inserito con ID: {new_feedback_id}. Nessun duplicato trovato.")
            await message.add_reaction("✅") # aggiunge una reazione ✅ al messaggio per indicare che l'elaborazione è stata completata con successo
            print(feedback_estratto.model_dump_json(indent=4))  # stampa per debug
        else:
            await message.add_reaction("❌") # aggiunge una reazione ❌ al messaggio per indicare che l'elaborazione non è andata a buon fine

    except Exception as e:
        await message.remove_reaction("⌛", client.user)
        await message.add_reaction("❌")
        print(f"Errore durante l'elaborazione del messaggio: {e}")
        
# avvia la connessione del bot a discord utilizzando il token di autenticazione
client.run(DISCORD_TOKEN)