from typing import Optional

import lancedb
from lancedb import db
from lancedb.pydantic import LanceModel, Vector
from lancedb.embeddings import get_registry
from pathlib import Path

from torch import where

# Inizializza l'embedder 
embedder = get_registry().get("sentence-transformers").create(name="all-MiniLM-L6-v2")

class TicketVector(LanceModel):
    ticket_id: int
    platform: str
    category: str
    text: str = embedder.SourceField()
    vector: Vector(embedder.ndims()) = embedder.VectorField() # type: ignore

def init_lancedb():
    base_dir = Path(__file__).resolve().parent.parent.parent
    db_path = base_dir / "data" / 'lancedb_data'

    db = lancedb.connect(db_path)

    table_name = "feedback_vectors"

    if table_name not in db.list_tables():
        db.create_table(table_name, TicketVector)

    return db

def find_similar_feedback(db: db, query_text: str, platform: str, category: str, top_k: int = 5):
    table_name = "feedback_vectors"
    table = db.table(table_name)

    # Esegue la ricerca dei feedback simili
    results = table.search(query_text, limit=top_k).where(f"platform = '{platform}' AND category = '{category}'").limit(top_k).to_list()

    return results