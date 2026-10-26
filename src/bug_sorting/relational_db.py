import sqlite3
from pathlib import Path

from pydantic import BaseModel

def connect_db():
    """
    Connessione al database SQLite.
    Returns:
        sqlite3.Connection: Oggetto di connessione al database.
    """
    # definizione percorso del database
    base_path = Path(__file__).parent.parent.parent
    db_path = base_path / "data" / "feedbacks.db" 

    # connessione al database
    conn = sqlite3.connect(db_path)
    return conn

def init_db():
    """
    Inizializza il database creando la tabella 'feedbacks' se non esiste ancora.
    """

    # connessione al database
    conn = connect_db()

    # creazione del cursore per eseguire le query
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
    """
    Inserisce un nuovo feedback nel database.
    Args:
        feedback_data (BaseModel): Dati del feedback da inserire.
        is_potential_duplicate (bool, optional): Indica se il feedback è un potenziale duplicato.
        duplicate_of_id (int, optional): ID del feedback originale se è un duplicato.
    Returns:
        int: ID del feedback inserito.
    """

    # connessione al database
    conn = connect_db()

    # creazione del cursore per eseguire le query
    cursor = conn.cursor()

    # conversione della lista dei passaggi in una stringa separati da spazi, se presente
    steps = " ".join(feedback_data.steps_to_reproduce) if feedback_data.steps_to_reproduce else None

    # gestione del messaggio di errore, se presente
    error_message = feedback_data.error_message if feedback_data.error_message else None

    query = '''
    INSERT INTO feedbacks (title, description, category, severity, platform, steps_to_reproduce, error_message, additional_context, is_potential_duplicate, duplicate_of_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''

    # valori da inserire nella query
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

    # esecuzione della query di inserimento
    cursor.execute(query, values)
    conn.commit()

    # identificativo del feedback appena inserito
    id = cursor.lastrowid

    # chiusura della connessione al database
    conn.close()

    return id

def update_feedback_status(feedback_id: int, new_status: str):
    """
    Aggiorna lo stato di un feedback nel database.
    Args:
        feedback_id (int): ID del feedback da aggiornare.
        new_status (str): Nuovo stato del feedback.
    """

    # connessione al database
    conn = connect_db()

    # creazione del cursore per eseguire le query
    cursor = conn.cursor()

    query = '''
    UPDATE feedbacks
    SET status = ?
    WHERE id = ?
    '''

    # esecuzione della query di aggiornamento
    cursor.execute(query, (new_status, feedback_id))

    # commit delle modifiche
    conn.commit()

    # chiusura della connessione al database
    conn.close()

def update_feedback_data(feedback_id: int, feedback_title: str, feedback_category: str, feedback_severity: str, feedback_platform: str):
    """
    Aggiorna i dati principali di un feedback nel database.
    Args:
        feedback_id (int): ID del feedback da aggiornare.
        feedback_title (str): Nuovo titolo del feedback.
        feedback_category (str): Nuova categoria del feedback.
        feedback_severity (str): Nuova gravità del feedback.
        feedback_platform (str): Nuova piattaforma del feedback.
    """

    # connessione al database
    conn = connect_db()

    # creazione del cursore per eseguire le query
    cursor = conn.cursor()

    query = '''
    UPDATE feedbacks
    SET title = ?, category = ?, severity = ?, platform = ?
    WHERE id = ?
    '''

    # valori da inserire nella query
    values = (feedback_title, feedback_category, feedback_severity, feedback_platform, feedback_id)

    # esecuzione della query di aggiornamento
    cursor.execute(query, values)

    # commit delle modifiche
    conn.commit()

    # chiusura della connessione al database
    conn.close()

def get_feedback_by_id(feedback_id: int) -> dict:
    """
    Recupera un feedback dal database in base al suo ID.
    Args:
        feedback_id (int): ID del feedback da recuperare.
    Returns:    
        dict: Dizionario contenente i dati del feedback, o None se non trovato.
    """

    # connessione al database
    conn = connect_db()

    # imposta la row_factory per restituire i risultati come dizionario invece che come tupla
    conn.row_factory = sqlite3.Row 

    # cursore per eseguire le query
    cursor = conn.cursor()

    # esecuzione della query per recuperare il feedback in base all'ID
    cursor.execute("SELECT * FROM feedbacks WHERE id = ?", (feedback_id,))

    # recupera la prima (e unica) riga del risultato della query
    row = cursor.fetchone()

    # chiusura della connessione al database
    conn.close()

    # restituisce il feedback come dizionario se trovato, altrimenti None
    return dict(row) if row else None

def get_feedback_summaries(feedback_ids: list[int]) -> list[tuple]:
    """
    Recupera i titoli dei feedback in base ad una lista di ID.
    Args:
        feedback_ids (list[int]): Lista di ID dei feedback da recuperare.
    Returns:
        list[tuple]: Lista di tuple contenenti l'ID e il titolo dei feedback.
    """

    # se non ci sono feedback, ritorna una lista vuota
    if not feedback_ids:
        return []

    # connessione al database
    conn = connect_db()

    # cursore per eseguire le query
    cursor = conn.cursor()

    
    # genera i segnaposto in base al numero di ID
    placeholders = ','.join(['?'] * len(feedback_ids))

    # esecuzione della query per recuperare i titoli dei feedback in base agli ID
    cursor.execute(f"SELECT id, title FROM feedbacks WHERE id IN ({placeholders})", feedback_ids)

    # recupera tutti i risultati della query
    results = cursor.fetchall()
    
    # chiusura della connessione al database
    conn.close()
    # restituisce una lista di tuple: [(1, "Titolo del primo bug"), (5, "Titolo del secondo")]
    return results

def mark_as_duplicate(feedback_id: int, original_feedback_id: int):
    """
    Segna un feedback come duplicato di un altro feedback nel database.
    Args:
        feedback_id (int): ID del feedback da segnare come duplicato.
        original_feedback_id (int): ID del feedback originale a cui il duplicato si riferisce.
    """

    # connessione al database
    conn = connect_db()

    # creazione del cursore per eseguire le query
    cursor = conn.cursor()

    query = '''
    UPDATE feedbacks
    SET status = 'rejected', duplicate_of_id = ?
    WHERE id = ?
    '''

    # esecuzione della query di aggiornamento
    cursor.execute(query, (original_feedback_id, feedback_id))

    # commit delle modifiche
    conn.commit()

    # chiusura della connessione al database
    conn.close()