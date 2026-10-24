import discord
import asyncio
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from bug_sorting.workflow import bugSortingWF
from bug_sorting.vector_db import init_lancedb, insert_feedback_vector
from bug_sorting.relational_db import *

load_dotenv()

# token identificatico dell'applicazione discord che farà girare questo script
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# identificativo del canale in cui gli utenti possono scrivere i feedback
FEEDBACK_CHANNEL_ID = int(os.getenv("FEEDBACK_CHAT_ID"))
DEVELOPER_CHANNEL_ID = int(os.getenv("DEVELOPER_CHAT_ID"))

# gli intents definiscono quali eventi e dati discord può inviare al bot
# crea gli intents predefiniti di discord
intents = discord.Intents.default()

# abilita la ricezione del contenuto testuale dei messaggi
intents.message_content = True

# istanzia il client del bot passando gli intents configurati
client = discord.Client(intents=intents)

# connessione al database vettoriale
v_db_conn = init_lancedb()

# region utilty

# utilizzata per cercare all'interno del database vettoriale
def find_similar_feedback(db, query_text: str, platform: str, category: str, top_k: int = 5) -> list[dict]:
    table = db.open_table("feedback_vectors")

    results = table.search(query_text) \
        .where(f"platform = '{platform}' AND category = '{category}'") \
        .limit(top_k) \
        .to_list()

    return results

# ricerca all'interno del database vettoriale una lista di risultati simili a quello in input
def deduplicate_vector_feedback(feedback_data: BaseModel) -> list:
    """
    Costruisce il vettore di embedding semantico, interroga LanceDB e filtra i risultati per soglia.
    Restituisce una lista di ID dei feedback duplicati.
    """

    # trasforma gli step per riprodurre un bug (se presenti) in una stringa
    steps = " ".join(feedback_data.steps_to_reproduce) if feedback_data.steps_to_reproduce else ""

    # concatena titolo, descrizione, steps, messaggi di errore e contesto aggiuntivo in una string sola
    testo_grezzo = f"{feedback_data.title} {feedback_data.description} {steps} {feedback_data.error_message} {feedback_data.additional_context}"
    
    vector_text = " ".join(testo_grezzo.split())

    # trova i valori simili
    risultati_grezzi = find_similar_feedback(
        db=v_db_conn, 
        query_text=vector_text, 
        platform=feedback_data.platform, 
        category=feedback_data.category.value, 
    )
    
    # print("DEBUG DISTANZE:", risultati_grezzi) 

    SOGLIA_DISTANZA = 0.85 
    duplicati_validati = [record["feedback_id"] for record in risultati_grezzi if record["_distance"] <= SOGLIA_DISTANZA]
    
    return duplicati_validati

# creazione embed discord
def create_feedback_embed(feedback_data: BaseModel, feedback_id: int, duplicate_id: list[int] = None) -> discord.Embed:
    color = discord.Color.red() if duplicate_id else discord.Color.green()
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

    if duplicate_id:
        embed.add_field(name="⚠️ Potenziali Duplicati", value=str(duplicate_id), inline=False)

    return embed

class FeedbackModerationView(discord.ui.View):
    def __init__(self, duplicate_ids: list[int] = None):
        # senza timeout il bot diventa persistente e non perde la possibilità di interagire con i bottoni dopo il riavvio
        super().__init__(timeout=None)

        if duplicate_ids:
            self.add_item(DuplicateSelect(duplicate_ids))

    @discord.ui.button(label="Approva", style=discord.ButtonStyle.green, custom_id="btn_approve")
    async def approve_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):

        embed = interaction.message.embeds[0]
        feedback_id = int(embed.title.split("#")[1].split(":")[0])  # non potendo passare parametri al costruttore in quanto statico, dobbiamo estrarre l'id dal titolo

        feedback_data = await asyncio.to_thread(get_feedback_by_id, feedback_id)
        if not feedback_data:
            await interaction.response.send_message("Errore critico: Record non trovato in SQLite.", ephemeral=True)
            return

        try:
            await asyncio.to_thread(insert_feedback_vector, feedback_data, v_db_conn)
        except Exception as e:
            await interaction.response.send_message(f"Errore di inserimento in LanceDB: {e}", ephemeral=True)
            return
        
        await asyncio.to_thread(update_feedback_status, feedback_id, "accepted")
        for child in self.children:
            child.disabled = True

        embed.color = discord.Color.green()
        embed.title = embed.title + " [APPROVATO]"

        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.followup.send(f"Feedback #{feedback_id} approvato.", ephemeral=True)

    @discord.ui.button(label="Rifiuta", style=discord.ButtonStyle.red, custom_id="btn_reject")
    async def reject_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):

        embed = interaction.message.embeds[0]
        feedback_id = int(embed.title.split("#")[1].split(":")[0])  # non potendo passare parametri al costruttore in quanto statico, dobbiamo estrarre l'id dal titolo

        await asyncio.to_thread(update_feedback_status, feedback_id, "rejected")
        for child in self.children:
            child.disabled = True

        
        embed.color = discord.Color.red()
        embed.title = embed.title + " [RIFIUTATO]"

        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.followup.send(f"Feedback #{feedback_id} rifiutato.", ephemeral=True)

    @discord.ui.button(label="Modifica", style=discord.ButtonStyle.blurple, custom_id="btn_edit")
    async def edit_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = interaction.message.embeds[0]
        feedback_id = int(embed.title.split("#")[1].split(":")[0])  # non potendo passare parametri al costruttore in quanto statico, dobbiamo estrarre l'id dal titolo

        # estrai i valori correnti dai campi dell'embed
        cur_title = embed.title.split(": ")[1]
        cur_category = embed.fields[0].value
        cur_severity = embed.fields[1].value
        cur_platform = embed.fields[2].value

        modal = EditFeedbackModal(feedback_id, cur_title, cur_category, cur_severity, cur_platform)
        await interaction.response.send_modal(modal)


class EditFeedbackModal(discord.ui.Modal, title="Modifica feedback"):
    titolo = discord.ui.TextInput(label="Titolo", style=discord.TextStyle.short)
    categoria = discord.ui.TextInput(label="Categoria", style=discord.TextStyle.short)
    gravita = discord.ui.TextInput(label="Gravità", style=discord.TextStyle.short)
    piattaforma = discord.ui.TextInput(label="Piattaforma", style=discord.TextStyle.short)

    def __init__(self, feedback_id: int, cur_title: str, cur_category: str, cur_severity: str, cur_platform: str):
        super().__init__()
        self.feedback_id = feedback_id
        self.titolo.default = cur_title
        self.categoria.default = cur_category
        self.gravita.default = cur_severity
        self.piattaforma.default = cur_platform

    async def on_submit(self, interaction: discord.Interaction):
        await asyncio.to_thread(update_feedback_data,
            feedback_id=self.feedback_id,
            feedback_title=self.titolo.value,
            feedback_category=self.categoria.value,
            feedback_severity=self.gravita.value,
            feedback_platform=self.piattaforma.value
        )

        embed = interaction.message.embeds[0]
        embed.title = f"Feedback #{self.feedback_id}: {self.titolo.value}"
        embed.set_field_at(0, name="Categoria", value=self.categoria.value, inline=True)
        embed.set_field_at(1, name="Gravità", value=self.gravita.value, inline=True)
        embed.set_field_at(2, name="Piattaforma", value=self.piattaforma.value, inline=True)

        await interaction.response.edit_message(embed=embed)
        await interaction.followup.send(f"Dati del feedback #{self.feedback_id} corretti.", ephemeral=True)

class DuplicateSelect(discord.ui.Select):
    def __init__(self, duplicates_info: list[tuple]):
        options = []
        for dup_id, dup_title in duplicates_info:
            # troncamento di sicurezza per rispettare i limiti API di Discord
            label_text = f"#{dup_id} - {dup_title}"[:100]
            options.append(discord.SelectOption(label=label_text, value=str(dup_id)))
        super().__init__(placeholder="Segna come duplicato di ", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        original_feedback_id = int(self.values[0])
        
        embed = interaction.message.embeds[0]
        current_feedback_id = int(embed.title.split("#")[1].split(":")[0])

        await asyncio.to_thread(mark_as_duplicate, current_feedback_id, original_feedback_id)
        
        # Disabilita l'interfaccia
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
    # stampa del nome del bot
    print(f'Bot connesso come {client.user}')
    init_db() #inizializza il database relazionale
    client.add_view(FeedbackModerationView())

# funzione che si attiva quando viene inviato un messaggio su #segnalazione-bug
@client.event
async def on_message(message):

    # ignora i messaggi inviati da se stesso
    if message.author == client.user:
        return
        
    # ignora i messaggi ricevuti al di fuori del canale #segnalazione-bug (altrimenti risponderebbe a qualsiasi messaggio ricevuto)
    if message.channel.id != FEEDBACK_CHANNEL_ID:
        return

    await message.add_reaction("⌛") # aggiunge una reazione 'clessidra' al messaggio in attesa di elaborazione
    print(f"Messaggio ricevuto: {message.content} da {message.author}") # stampa del messaggio ricevuto (debug)

    try:
        risultato = await asyncio.to_thread(bugSortingWF.run, message.content)  # esegue la funzione di elaborazione del feedback in un thread separato per non bloccare l'evento principale
        await message.remove_reaction("⌛", client.user) # rimuove la reazione 'clessidra' dal messaggio una volta finita l'elaborazione.

        # l'unico risultato del workflow risultante in un BaseModel è quello in cui il testo di input era valido
        if isinstance(risultato.content, BaseModel):
            feedback_estratto = risultato.content
            
            # esecuzione della deduplicazione
            id_duplicati = await asyncio.to_thread(deduplicate_vector_feedback, feedback_estratto)

            info_duplicati = await asyncio.to_thread(get_feedback_summaries, id_duplicati) if id_duplicati else []

            is_potential_duplicate = 1 if id_duplicati else 0

            new_feedback_id = await asyncio.to_thread(insert_feedback, feedback_estratto, is_potential_duplicate=is_potential_duplicate)

            dev_channel = client.get_channel(DEVELOPER_CHANNEL_ID)
            embed_feedback_for_dev = create_feedback_embed(feedback_estratto, new_feedback_id, duplicate_id=id_duplicati)
            
            await dev_channel.send(embed=embed_feedback_for_dev, view=FeedbackModerationView(duplicate_ids=info_duplicati))

            if id_duplicati:
                print(f"ATTENZIONE: Possibili duplicati trovati con ID: {id_duplicati}.")
                print(f"Nuovo feedback inserito con ID: {new_feedback_id}.")
            else:
                print(f"Nuovo feedback inserito con ID: {new_feedback_id}. Nessun duplicato trovato.")
            await message.add_reaction("✅") 
            print(feedback_estratto.model_dump_json(indent=4))  # stampa per debug
        else:
            await message.add_reaction("❌")

    except Exception as e:
        await message.remove_reaction("⌛", client.user)
        await message.add_reaction("❌")
        print(f"Errore durante l'elaborazione del messaggio: {e}")
        
# avvia la connessione del bot a discord utilizzando il token di autenticazione
client.run(DISCORD_TOKEN)