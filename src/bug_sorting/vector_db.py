from typing import Optional

import lancedb
from lancedb import db
from lancedb.pydantic import LanceModel, Vector
from lancedb.embeddings import get_registry
from pathlib import Path

from pydantic import BaseModel
from torch import where

# inizializzazione dell'embedder locale
# la scelta di usare un embedder locale è motivata dalla necessità di non sprecare i token di cui hanno bisogno gli agenti per generare le risposte
embedder = get_registry().get("sentence-transformers").create(name="all-MiniLM-L6-v2")

class FeedbackVector(LanceModel):
    """
    Schema per rappresentare un vettore di feedback nel database.
    Contiene informazioni sul feedback, come l'ID, la piattaforma, la categoria, il testo e il vettore di embedding associato.
    """
    feedback_id: int
    platform: str
    category: str
    # definizione del campo di testo che verrà utilizzato per generare l'embedding
    text: str = embedder.SourceField()
    # definizione della dimensione del vettore di embedding (384 dimensioni per il modello all-MiniLM-L6-v2)
    vector: Vector(embedder.ndims()) = embedder.VectorField() # type: ignore

def init_lancedb():
    """
    Inizializzazione del database vettoriale LanceDB.
    Crea una tabella per memorizzare i vettori di feedback, se non esiste già.
    """
    # definizione del percorso del database
    base_dir = Path(__file__).resolve().parent.parent.parent
    db_path = base_dir / "data" / 'lancedb_data'

    # connessione al database
    db = lancedb.connect(db_path)

    table_name = "feedback_vectors"

    # exist_ok=True riutilizza la tabella esistente senza modificarne lo schema
    db.create_table(table_name, schema=FeedbackVector, exist_ok=True)

    return db

def insert_feedback_vector(feedback_data: dict, db_connection):
    """
    Inserisce un nuovo feedback nel database vettoriale LanceDB
    """

    # connessione alla tabella dei vettori di feedback
    table = db_connection.open_table("feedback_vectors")

    # creazione del contenuto testuale da cui generare l'embedding
    steps = feedback_data.get('steps_to_reproduce') or ""
    error = feedback_data.get('error_message') or ""
    text_content = f"{feedback_data['title']}. {feedback_data['description']}. {steps}. {error}".strip()

    # inserimento del nuovo feedback nella tabella
    table.add([
        {
            "feedback_id": feedback_data['id'],
            "platform": feedback_data.get('platform', 'unknown'),
            "category": feedback_data['category'],
            "text": text_content
        }
    ])
