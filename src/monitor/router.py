"""Router de monitoreo — GET /health y GET /metrics."""
from fastapi import APIRouter, Depends, Request

from src.monitor.dependencies import get_metrics
from src.monitor.schemas import HealthResponse, MetricsResponse
from src.monitor.service import MetricsTracker

router = APIRouter(tags=["Monitoreo"])


@router.get("/health", response_model=HealthResponse)
def health(request: Request):
    """Comprueba que el servicio y los modelos están operativos."""
    return HealthResponse(
        status="ok",
        model_loaded=request.app.state.predictor is not None,
        version=request.app.version,
    )


@router.get("/metrics", response_model=MetricsResponse)
def metrics(tracker: MetricsTracker = Depends(get_metrics)):
    """
    Devuelve métricas acumuladas de latencia.

    L̄ = Σ(t_respuesta_i − t_solicitud_i) / N_peticiones
    """
    return MetricsResponse(
        total_requests=tracker.request_count,
        total_latency_ms=round(tracker.total_latency_ms, 2),
        mean_latency_ms=round(tracker.mean_latency_ms, 2),
    )
