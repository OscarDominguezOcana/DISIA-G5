"""Router de inferencia — POST /predict."""
import time

from fastapi import APIRouter, Depends, HTTPException, Request

from src.monitor.dependencies import get_metrics
from src.monitor.service import MetricsTracker
from src.monitor.drift_logger import log_input
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

    log_input(request.person_a.model_dump(), request.person_b.model_dump(), result)

    return CompatibilityResponse(**result, latency_ms=round(latency_ms, 3))


@router.post("/reload", tags=["Admin"], response_model=None)
def reload_models(app_request: Request):
    """Recarga los modelos desde disco sin reiniciar el servidor."""
    try:
        app_request.app.state.predictor = CupidPredictor()
        return {"status": "ok", "message": "Modelos recargados correctamente."}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))