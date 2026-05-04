"""Router de inferencia — POST /predict."""
import time

from fastapi import APIRouter, Depends, HTTPException

from src.monitor.dependencies import get_metrics
from src.monitor.service import MetricsTracker
from src.infer.dependencies import get_predictor
from src.infer.exceptions import PredictionError
from src.infer.schemas import CompatibilityRequest, CompatibilityResponse
from src.infer.service import CupidPredictor

router = APIRouter(tags=["Inferencia"])


@router.post("/predict", response_model=CompatibilityResponse)
def predict(
    request: CompatibilityRequest,
    predictor: CupidPredictor = Depends(get_predictor),
    metrics: MetricsTracker = Depends(get_metrics),
):
    """
    Predice la compatibilidad entre dos personas.

    - **compatible**: clasificación binaria.
    - **compatibility_probability**: probabilidad estimada (0-1).
    - **estimated_longevity_months**: duración estimada de la relación.
    - **overall_match_score**: score ponderado del feature engineering.
    - **latency_ms**: tiempo de procesamiento de esta petición.
    """
    t_start = time.perf_counter()

    try:
        result = predictor.predict(
            request.person_a.model_dump(),
            request.person_b.model_dump(),
        )
    except PredictionError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    latency_ms = (time.perf_counter() - t_start) * 1000
    metrics.record(latency_ms)

    return CompatibilityResponse(**result, latency_ms=round(latency_ms, 3))
