import discord
import asyncio
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from bug_sorting.workflow import bugSortingWF
from bug_sorting.vector_db import init_lancedb
from bug_sorting.relational_db import init_db, insert_feedback, update_feedback_status

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
        category=feedback_data.category 
    )
    
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
    def __init__(self):
        # senza timeout il bot diventa persistente e non perde la possibilità di interagire con i bottoni dopo il riavvio
        super().__init__(timeout=None)

    @discord.ui.button(label="Approva", style=discord.ButtonStyle.green, custom_id="btn_approve")
    async def approve_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):

        embed = interaction.message.embeds[0]
        feedback_id = int(embed.title.split("#")[1].split(":")[0])  # non potendo passare parametri al costruttore in quanto statico, dobbiamo estrarre l'id dal titolo
        
        #TODO: inserire il valore in lancedb
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

            is_potential_duplicate = 1 if id_duplicati else 0

            new_feedback_id = await asyncio.to_thread(insert_feedback, feedback_estratto, is_potential_duplicate=is_potential_duplicate)

            dev_channel = client.get_channel(DEVELOPER_CHANNEL_ID)
            embed_feedback_for_dev = create_feedback_embed(feedback_estratto, new_feedback_id, duplicate_id=id_duplicati)
            await dev_channel.send(embed=embed_feedback_for_dev, view=FeedbackModerationView())

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