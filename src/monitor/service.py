"""
MetricsTracker — acumula métricas de latencia de forma thread-safe.

Fórmula de latencia media:
    L̄ = Σ(t_respuesta_i − t_solicitud_i) / N_peticiones
"""
import threading


class MetricsTracker:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._request_count: int = 0
        self._total_latency_ms: float = 0.0

    def record(self, latency_ms: float) -> None:
        with self._lock:
            self._request_count += 1
            self._total_latency_ms += latency_ms

    @property
    def request_count(self) -> int:
        with self._lock:
            return self._request_count

    @property
    def total_latency_ms(self) -> float:
        with self._lock:
            return self._total_latency_ms

    @property
    def mean_latency_ms(self) -> float:
        with self._lock:
            if self._request_count == 0:
                return 0.0
            return self._total_latency_ms / self._request_count
