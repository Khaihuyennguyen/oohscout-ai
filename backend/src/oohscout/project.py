import uuid
from enum import Enum
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator

# ==============================================================================
# Domain Enums
# ==============================================================================
class RegulatoryStatus(str, Enum):
    """
    Strict hard-gates for a candidate's status.
    Per project rules: 'LEGAL' is forbidden. Only human lawyers declare legality.
    """
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"

# ==============================================================================
# Data Schemas (The "Nouns")
# ==============================================================================
class Corridor(BaseModel):
    """
    Represents a specific stretch of highway being scouted.
    Example: "IH-35 through McLennan County"
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str = Field(..., description="Human-readable name of the corridor")
    geometry: str = Field(..., description="GeoJSON string or WKT of the corridor bounds")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Candidate(BaseModel):
    """
    Represents a specific land parcel being evaluated for a billboard.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    corridor_id: uuid.UUID = Field(..., description="Link to the parent Corridor")
    parcel_id: str = Field(..., description="County parcel identification number")
    geometry: str = Field(..., description="GeoJSON string or WKT of the parcel bounds")
    regulatory_status: RegulatoryStatus = Field(..., description="Must be PASS, FAIL, or REVIEW")
    setback_distance_ft: Optional[float] = Field(None, description="Distance from highway ROW in feet")

    @field_validator('regulatory_status', mode='before')
    @classmethod
    def block_legal_status(cls, v: Any) -> Any:
        """
        Extra defensive check to completely intercept and block the word 'LEGAL',
        even if someone tries to pass it as a string before enum validation.
        """
        if isinstance(v, str) and v.upper() == "LEGAL":
            raise ValueError(
                "CRITICAL: AI attempted to classify candidate as 'LEGAL'. "
                "This violates core compliance rules. Status must be PASS, FAIL, or REVIEW."
            )
        return v
