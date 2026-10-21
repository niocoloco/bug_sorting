import sqlite3
from pathlib import Path



def init_db():
    base_path = Path(__file__).parent.parent.parent
    db_path = base_path / "data" / "tickets.db" 

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT NOT NULL,
        severity TEXT NOT NULL,
        steps_to_reproduce TEXT,
        error_message TEXT,
        status TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ADD CONSTRAINT category_check CHECK (category IN ('bug', 'feature_request', 'performance_issue', 'usability_issue', 'security_issue', 'balancement_request', 'other')),
        ADD CONSTRAINT severity_check CHECK (severity IN ('low', 'medium', 'high', 'critical')),
        ADD CONSTRAINT status_check CHECK (status IN ('pending', 'accepted', 'rejected', 'resolved'))
    )
    ''')

    conn.commit()
    conn.close()


