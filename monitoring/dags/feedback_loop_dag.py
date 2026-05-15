"""
feedback_loop_dag.py
────────────────────
DAG de Airflow que se ejecuta cada hora y gestiona el feedback loop completo:

  1. evaluate_drift  → usa Evidently para comparar datos de referencia
                       con el tráfico actual. Empuja métricas a Prometheus.
  2a. retrain_task   → si hay drift: reentrena el modelo y recarga la API
  2b. skip_task      → si no hay drift: no hace nada

Colocad este archivo en:  monitoring/dags/feedback_loop_dag.py
"""
from __future__ import annotations

import os
import subprocess
from datetime import datetime, timedelta

import requests
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import BranchPythonOperator, PythonOperator

# ─── Configuración ────────────────────────────────────────────────────────────
MONITORING_DIR   = os.getenv("MONITORING_DIR", "/app/data/monitoring")
REFERENCE_PATH   = os.path.join(MONITORING_DIR, "reference_data.csv")
CURRENT_PATH     = os.path.join(MONITORING_DIR, "current_traffic.csv")
PUSHGATEWAY_URL  = "pushgateway:9091"
API_URL          = os.getenv("API_URL", "http://api:8000")
MIN_SAMPLES      = 50       # mínimo de muestras para analizar drift
DRIFT_THRESHOLD  = 0.5      # si >50% de features derivan, reentrenamos

DRIFT_FEATURES = [
    "same_love_language",
    "ambition_diff",
    "emotional_expressiveness_diff",
    "spontaneity_diff",
    "overall_match_score",
    "personality_distance_sum",
]

# ─── Tareas ───────────────────────────────────────────────────────────────────

def evaluate_drift(**context) -> str:
    """
    Compara datos de referencia con tráfico actual usando Evidently.
    Empuja las métricas a Prometheus via Push Gateway.
    Devuelve el nombre de la siguiente tarea ('retrain_task' o 'skip_task').
    """
    import pandas as pd
    from evidently.metric_preset import DataDriftPreset
    from evidently.report import Report
    from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

    # Comprobaciones previas
    if not os.path.exists(CURRENT_PATH):
        print("No hay datos de tráfico todavía. Saltando.")
        return "skip_task"

    reference = pd.read_csv(REFERENCE_PATH)[DRIFT_FEATURES]
    current   = pd.read_csv(CURRENT_PATH)[DRIFT_FEATURES]

    if len(current) < MIN_SAMPLES:
        print(f"Solo {len(current)} muestras en tráfico actual. "
              f"Mínimo requerido: {MIN_SAMPLES}. Saltando.")
        return "skip_task"

    # Análisis de drift con Evidently
    report = Report(metrics=[DataDriftPreset()])
    report.run(reference_data=reference, current_data=current)
    results = report.as_dict()

    drift_detected = results["metrics"][0]["result"]["dataset_drift"]
    drift_share    = results["metrics"][0]["result"]["share_of_drifted_columns"]

    print(f"[Drift] Detectado: {drift_detected} | "
          f"Features derivadas: {drift_share:.0%} "
          f"(umbral: {DRIFT_THRESHOLD:.0%})")

    # Empujar métricas a Prometheus via Push Gateway
    registry = CollectorRegistry()
    Gauge("core_mp_drift_detected", "1 si hay drift de datos, 0 si no",
          registry=registry).set(1 if drift_detected else 0)
    Gauge("core_mp_drift_share", "Porcentaje de features con drift",
          registry=registry).set(drift_share)
    push_to_gateway(PUSHGATEWAY_URL, job="drift_check", registry=registry)

    return "retrain_task" if drift_detected else "skip_task"


def retrain_model(**context) -> None:
    """
    Lanza el contenedor de entrenamiento (train) y recarga la API
    con el nuevo modelo una vez terminado.
    """
    print("Drift detectado. Iniciando reentrenamiento...")

    result = subprocess.run(
        ["docker", "compose", "run", "--rm", "train"],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        print(f"[ERROR] Reentrenamiento fallido:\n{result.stderr}")
        raise RuntimeError("El reentrenamiento ha fallado.")

    print("Reentrenamiento completado. Recargando modelos en la API...")
    response = requests.post(f"{API_URL}/reload", timeout=30)
    response.raise_for_status()
    print(f"API recargada correctamente: {response.json()}")


# ─── Definición del DAG ───────────────────────────────────────────────────────

default_args = {
    "owner": "core-mp",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="core_mp_feedback_loop",
    default_args=default_args,
    description=(
        "Detecta drift en los datos de entrada del modelo CORE-MP "
        "y reentrena automáticamente si es necesario."
    ),
    schedule=timedelta(hours=1),
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["core-mp", "mlops", "drift"],
) as dag:

    evaluate_task = BranchPythonOperator(
        task_id="evaluate_drift",
        python_callable=evaluate_drift,
    )

    retrain_task = PythonOperator(
        task_id="retrain_task",
        python_callable=retrain_model,
    )

    skip_task = EmptyOperator(
        task_id="skip_task",
    )

    # Flujo: evaluar → reentrenar O saltar
    evaluate_task >> [retrain_task, skip_task]
