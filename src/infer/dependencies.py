from fastapi import HTTPException, Request

from src.infer.service import CupidPredictor


def get_predictor(request: Request) -> CupidPredictor:
    """Devuelve el predictor cargado en app.state (inyectado en el lifespan)."""
    predictor: CupidPredictor | None = request.app.state.predictor
    if predictor is None:
        raise HTTPException(status_code=503, detail="Modelos no disponibles.")
    return predictor
