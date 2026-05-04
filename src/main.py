"""
main.py
Punto de entrada de la API — crea la app FastAPI, gestiona el ciclo de vida
(carga de modelos) e incluye los routers de cada dominio.

Arranque:
    uvicorn src.main:app --host 0.0.0.0 --port 8000
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.monitor.router import router as monitoring_router
from src.monitor.service import MetricsTracker
from src.infer.router import router as predict_router
from src.infer.service import CupidPredictor


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Carga modelos y tracker de métricas al arrancar; los libera al apagar."""
    app.state.predictor = CupidPredictor()   # fail-fast si faltan los .pkl
    app.state.metrics = MetricsTracker()
    yield
    app.state.predictor = None
    app.state.metrics = None


app = FastAPI(
    title="CORE-MP API",
    description=(
        "API de predicción de compatibilidad amorosa. "
        "Devuelve si una pareja es compatible y la longevidad estimada."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(predict_router)
app.include_router(monitoring_router)
