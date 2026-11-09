from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

class CleanedFeedback(BaseModel):
    """
    JSON schema per il feedback pulito e filtrato.
    """
    content: str = Field(description="Contenuto del feedback pulito e filtrato")
    valid: bool = Field(description="Indica se il feedback è valido o irrilevante")

class FeedbackCategory(str, Enum):
    """
    Enumeratori per le categorie del feedback.
    """
    BUG = "bug"
    FEATURE_REQUEST = "feature_request"
    PERFORMANCE_ISSUE = "performance_issue"
    USABILITY_ISSUE = "usability_issue"
    SECURITY_ISSUE = "security_issue"
    BALANCEMENT_REQUEST = "balancement_request"
    OTHER = "other"

class FeedbackSeverity(str, Enum):
    """
    Enumeratori per la gravità del feedback.
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class FormattedFeedback(BaseModel):
    """
    JSON schema per il feedback formattato.
    """
    title: str = Field(description="Titolo del feedback")
    description: str = Field(description="Descrizione dettagliata del feedback")
    category: FeedbackCategory = Field(description="Categoria del feedback")
    severity: FeedbackSeverity = Field(description="Gravità del feedback")
    platform: str = Field(default="UNKNOWN", description="Piattaforma a cui il feedback si riferisce")
    steps_to_reproduce: Optional[list[str]] = Field(default=[], description="Passaggi per riprodurre il problema")
    error_message: Optional[str] = Field(default="UNKNOWN", description="Messaggio di errore provocato dal problema")
    additional_context: Optional[str] = Field(default="UNKNOWN", description="Qualsiasi contesto aggiuntivo utile. Restituisci UNKNOWN se assente")

class DevFixExtraction(BaseModel):
    """
    JSON schema per l'estrazione dei parametri di ricerca dal messaggio del programmatore.
    """
    search_query: str = Field(description="Il sintomo vissuto dall'utente. Riscrivi la frase all'indicativo presente come se fosse scritta dal giocatore stesso. Questo testo verrà usato per la ricerca vettoriale.")
    category: FeedbackCategory = Field(description="Categoria probabile del bug risolto. Fondamentale per il filtro esatto su database.")
    platform: str = Field(default="UNKNOWN", description="Piattaforma a cui il fix si riferisce (es. PS5, PC). Restituisci UNKNOWN se non specificata.")
    fix: str = Field(default="UNKNOWN",description="Causa tecnica che causava il problema o breve descrizione del fix applicato (es. 'memory leak', 'aggiornata query', ...). Restituisci UNKNOWN se non specificata.")

class DevFixList(BaseModel):
    fixes: list[DevFixExtraction] = Field(description="Lista dei bug risolti estratti dal messaggio.")