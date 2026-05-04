from fastapi import Request

from src.monitor.service import MetricsTracker


def get_metrics(request: Request) -> MetricsTracker:
    """Devuelve el tracker de métricas almacenado en app.state."""
    return request.app.state.metrics
