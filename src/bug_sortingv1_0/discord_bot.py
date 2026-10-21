import discord
import asyncio
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from bug_sortingv1_0.bug_sorting import bugSortingWF

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

TARGET_CHANNEL_ID = os.getenv("FEEDBACK_CHAT_ID")

# Inizializza le intenzioni di default per il bot. 
# Gli intents definiscono quali eventi Discord invierà al bot.
intents = discord.Intents.default()

# Abilita esplicitamente l'intent per leggere il contenuto dei messaggi. 
# Richiede l'abilitazione del "Message Content Intent" nel portale Developer di Discord.
intents.message_content = True  

# Istanzia il client del bot passando gli intents configurati.
client = discord.Client(intents=intents)

# Decoratore che registra la funzione on_ready come callback per l'evento 'on_ready'
# (attivato quando il bot ha completato il login e si è connesso ai server Discord).
@client.event
async def on_ready():
    # Stampa in console il nome dell'utente del bot per confermare la connessione.
    print(f'Bot connesso come {client.user}')

@client.event
async def on_message(message):
    await message.add_reaction("⌛") # Aggiunge una reazione 'clessidra' al messaggio in attesa di elaborazione.
    print(f"Messaggio ricevuto: {message.content} da {message.author}")

    try:
        risultato = await asyncio.to_thread(bugSortingWF.run, message.content)  # Esegue la funzione di elaborazione del feedback in un thread separato per non bloccare l'evento principale.
        await message.remove_reaction("⌛", client.user) # Rimuove la reazione 'clessidra' dal messaggio una volta finita l'elaborazione.

        if isinstance(risultato.content, BaseModel):
            await message.add_reaction("✅") # Aggiunge una reazione 'check' al messaggio per indicare che l'elaborazione è stata completata con successo.
            print(risultato.content.model_dump_json(indent=4))
        else:
            await message.add_reaction("❌")

    except Exception as e:
        await message.remove_reaction("⌛", client.user)
        await message.add_reaction("❌")
        print(f"Errore durante l'elaborazione del messaggio: {e}")
        
# Avvia la connessione del bot a Discord utilizzando il token di autenticazione.
client.run(DISCORD_TOKEN)