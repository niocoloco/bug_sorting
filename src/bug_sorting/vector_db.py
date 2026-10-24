from typing import Optional

import lancedb
from lancedb import db
from lancedb.pydantic import LanceModel, Vector
from lancedb.embeddings import get_registry
from pathlib import Path

from pydantic import BaseModel
from torch import where

# inizializzazione dell'embedder locale
embedder = get_registry().get("sentence-transformers").create(name="all-MiniLM-L6-v2")

# struttura un vettore di feedback
class FeedbackVector(LanceModel):
    feedback_id: int
    platform: str
    category: str
    text: str = embedder.SourceField()
    # definzione della dimensione del vettore di embedding (384 dimensioni per il modello all-MiniLM-L6-v2)
    vector: Vector(embedder.ndims()) = embedder.VectorField() # type: ignore

def init_lancedb():
    # definizione del percorso del database
    base_dir = Path(__file__).resolve().parent.parent.parent
    db_path = base_dir / "data" / 'lancedb_data'

    # connessione al database
    db = lancedb.connect(db_path)

    table_name = "feedback_vectors"

    # exist_ok=True riutilizza la tabella esistente senza modificarne lo schema.
    db.create_table(table_name, schema=FeedbackVector, exist_ok=True)

    return db

def insert_feedback_vector(feedback_data: dict, db_connection):
    table = db_connection.open_table("feedback_vectors")
    
    steps = feedback_data.get('steps_to_reproduce') or ""
    error = feedback_data.get('error_message') or ""
    text_content = f"{feedback_data['title']}. {feedback_data['description']}. {steps}. {error}".strip()
    
    table.add([
        {
            "feedback_id": feedback_data['id'],
            "platform": feedback_data.get('platform', 'unknown'),
            "category": feedback_data['category'],
            "text": text_content
        }
    ])
