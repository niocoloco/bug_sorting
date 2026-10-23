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