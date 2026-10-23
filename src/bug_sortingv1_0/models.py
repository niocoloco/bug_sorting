from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

# JSON schema per il feedback filtrato
class CleanedFeedback(BaseModel):
    content: str = Field(description="Contenuto del feedback pulito e filtrato")
    valid: bool = Field(description="Indica se il feedback è valido o irrilevante")

# enumeratori per la categoria del feedback
class FeedbackCategory(str, Enum):
    BUG = "bug"
    FEATURE_REQUEST = "feature_request"
    PERFORMANCE_ISSUE = "performance_issue"
    USABILITY_ISSUE = "usability_issue"
    SECURITY_ISSUE = "security_issue"
    BALANCEMENT_REQUEST = "balancement_request"
    OTHER = "other"

# enumeratori per la gravità del feedback
class FeedbackSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

# JSON schema per il feedback formattato
class FormattedFeedback(BaseModel):
    title: str = Field(description="Titolo del feedback")
    description: str = Field(description="Descrizione dettagliata del feedback")
    category: FeedbackCategory = Field(description="Categoria del feedback")
    severity: FeedbackSeverity = Field(description="Gravità del feedback")
    platform: str = Field(default="UNKNOWN", description="Piattaforma a cui il feedback si riferisce")
    steps_to_reproduce: Optional[list[str]] = Field(default=[], description="Passaggi per riprodurre il problema")
    error_message: Optional[str] = Field(default="UNKNOWN", description="Messaggio di errore provocato dal problema")
    additional_context: Optional[str] = Field(default="UNKNOWN", description="Qualsiasi contesto aggiuntivo utile. Restituisci UNKNOWN se assente")