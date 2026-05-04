from typing import Annotated

from pydantic import BaseModel, Field

_PERSON_EXAMPLE = {
    "age": 28,
    "education": 0.75,
    "location": "Madrid",
    "career_field": "Technology",
    "career_ambition": 0.8,
    "openness": 0.72,
    "extraversion": 0.55,
    "agreeableness": 0.65,
    "conscientiousness": 0.70,
    "chronotype": "morning",
    "spontaneity": 0.45,
    "love_language": "quality_time",
    "emotional_expressiveness": 0.60,
}


class PersonFeatures(BaseModel):
    age: float = Field(gt=0, le=120, description="Edad en años")
    education: float = Field(ge=0, le=1, description="Nivel educativo normalizado (0-1)")
    location: str = Field(description="Ciudad o región")
    career_field: str = Field(description="Sector profesional")
    career_ambition: float = Field(ge=0, le=1, description="Ambición profesional (0-1)")
    openness: float = Field(ge=0, le=1, description="Big Five: apertura a la experiencia")
    extraversion: float = Field(ge=0, le=1, description="Big Five: extraversión")
    agreeableness: float = Field(ge=0, le=1, description="Big Five: amabilidad")
    conscientiousness: float = Field(ge=0, le=1, description="Big Five: responsabilidad")
    chronotype: str = Field(description="Cronotipo (e.g. 'morning', 'evening', 'neutral')")
    spontaneity: float = Field(ge=0, le=1, description="Espontaneidad (0-1)")
    love_language: str = Field(description="Lenguaje del amor principal")
    emotional_expressiveness: float = Field(ge=0, le=1, description="Expresividad emocional (0-1)")

    model_config = {"json_schema_extra": {"example": _PERSON_EXAMPLE}}


class CompatibilityRequest(BaseModel):
    person_a: PersonFeatures
    person_b: PersonFeatures

    model_config = {
        "json_schema_extra": {
            "example": {
                "person_a": _PERSON_EXAMPLE,
                "person_b": {**_PERSON_EXAMPLE, "age": 30, "education": 0.80, "career_ambition": 0.75},
            }
        }
    }


class CompatibilityResponse(BaseModel):
    compatible: bool
    compatibility_probability: float
    estimated_longevity_months: float
    overall_match_score: float
    model_version: str = "1.0.0"
    latency_ms: float
