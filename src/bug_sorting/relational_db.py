import sqlite3
from pathlib import Path

from pydantic import BaseModel


def connect_db():
    # definizione percorso del database
    base_path = Path(__file__).parent.parent.parent
    db_path = base_path / "data" / "feedbacks.db" 

    # connessione al database
    conn = sqlite3.connect(db_path)
    return conn

def init_db():
    conn = connect_db()
    cursor = conn.cursor()

    # query di crezione della tabella
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS feedbacks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT NOT NULL,
        severity TEXT NOT NULL,
        platform TEXT,
        steps_to_reproduce TEXT,
        error_message TEXT,
        status TEXT NOT NULL DEFAULT 'pending',
        additional_context TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        is_potential_duplicate INTEGER DEFAULT 0,
        duplicate_of_id INTEGER,

        CONSTRAINT category_check CHECK (category IN ('bug', 'feature_request', 'performance_issue', 'usability_issue', 'security_issue', 'balancement_request', 'other')),
        CONSTRAINT severity_check CHECK (severity IN ('low', 'medium', 'high', 'critical')),
        CONSTRAINT status_check CHECK (status IN ('pending', 'accepted', 'rejected', 'resolved')),

        FOREIGN KEY (duplicate_of_id) REFERENCES feedbacks(id)
    )
    ''')

    # commit delle modifiche
    conn.commit()
    # chiusura della connessione al database
    conn.close()

def insert_feedback(feedback_data: BaseModel, is_potential_duplicate: bool = False, duplicate_of_id: int = None):
    conn = connect_db()
    cursor = conn.cursor()

    steps = " ".join(feedback_data.steps_to_reproduce) if feedback_data.steps_to_reproduce else None
    error_message = feedback_data.error_message if feedback_data.error_message else None

    query = '''
    INSERT INTO feedbacks (title, description, category, severity, platform, steps_to_reproduce, error_message, additional_context, is_potential_duplicate, duplicate_of_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''

    values = (
        feedback_data.title,
        feedback_data.description,
        feedback_data.category,
        feedback_data.severity,
        None if feedback_data.platform == "UNKNOWN" else feedback_data.platform,
        steps,
        error_message,
        None if feedback_data.additional_context == "UNKNOWN" else feedback_data.additional_context,
        1 if is_potential_duplicate else 0,
        duplicate_of_id
    )

    cursor.execute(query, values)
    conn.commit()

    id = cursor.lastrowid

    conn.close()

    return id

def update_feedback_status(feedback_id: int, new_status: str):
    conn = connect_db()
    cursor = conn.cursor()

    query = '''
    UPDATE feedbacks
    SET status = ?
    WHERE id = ?
    '''

    cursor.execute(query, (new_status, feedback_id))
    conn.commit()
    conn.close()

def update_feedback_data(feedback_id: int, feedback_title: str, feedback_category: str, feedback_severity: str, feedback_platform: str):
    conn = connect_db()
    cursor = conn.cursor()

    query = '''
    UPDATE feedbacks
    SET title = ?, category = ?, severity = ?, platform = ?
    WHERE id = ?
    '''

    values = (feedback_title, feedback_category, feedback_severity, feedback_platform, feedback_id)

    cursor.execute(query, values)
    conn.commit()
    conn.close()

def get_feedback_by_id(feedback_id: int) -> dict:
    conn = connect_db()
    # imposta la row_factory per restituire i risultati come dizionario invece che come tupla
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM feedbacks WHERE id = ?", (feedback_id,))
    row = cursor.fetchone()
    
    conn.close()
    
    return dict(row) if row else None

def get_feedback_summaries(feedback_ids: list[int]) -> list[tuple]:
    if not feedback_ids:
        return []
    
    conn = connect_db()
    cursor = conn.cursor()
    
    # Genera i segnaposto in base al numero di ID trovati (es. "?, ?, ?")
    placeholders = ','.join(['?'] * len(feedback_ids))
    cursor.execute(f"SELECT id, title FROM feedbacks WHERE id IN ({placeholders})", feedback_ids)
    results = cursor.fetchall()
    
    conn.close()
    # restituisce una lista di tuple: [(1, "Titolo del primo bug"), (5, "Titolo del secondo")]
    return results

def mark_as_duplicate(feedback_id: int, original_feedback_id: int):
    conn = connect_db()
    cursor = conn.cursor()

    query = '''
    UPDATE feedbacks
    SET status = 'rejected', duplicate_of_id = ?
    WHERE id = ?
    '''

    cursor.execute(query, (original_feedback_id, feedback_id))
    conn.commit()
    conn.close()