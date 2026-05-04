from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    version: str


class MetricsResponse(BaseModel):
    total_requests: int
    total_latency_ms: float
    mean_latency_ms: float
