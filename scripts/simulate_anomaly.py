"""
simulate_anomaly.py
───────────────────
Script para simular un entorno anómalo y demostrar que el sistema
de alertas y detección de drift funciona correctamente.

Envía peticiones con datos completamente aleatorios (fuera de la
distribución de entrenamiento) para forzar la detección de drift.

Uso:
    # Simular drift en los datos (para probar Evidently + Airflow)
    python scripts/simulate_anomaly.py --mode drift --n 200

    # Simular carga masiva (para probar alerta de latencia/CPU en Grafana)
    python scripts/simulate_anomaly.py --mode load --n 500
"""
import argparse
import random
import time

import requests

API_URL = "http://localhost:8000/predict"

LOVE_LANGUAGES = ["quality_time", "words_of_affirmation", "acts_of_service",
                  "receiving_gifts", "physical_touch"]
CAREER_FIELDS  = ["Technology", "Finance", "Healthcare", "Education",
                  "Law", "Marketing", "Engineering", "Science"]
LOCATIONS      = ["Madrid", "Barcelona", "Valencia", "Sevilla", "Bilbao"]
CHRONOTYPES    = ["morning", "evening", "neutral"]


def random_person(anomalous: bool = False) -> dict:
    """Genera un perfil de persona. Si anomalous=True, usa valores extremos."""
    if anomalous:
        # Valores extremos que se alejan de la distribución de entrenamiento
        return {
            "age": random.choice([18, 19, 54, 55]),   # edades extremas
            "education": random.uniform(0.0, 0.05),   # casi 0
            "location": random.choice(LOCATIONS),
            "career_field": random.choice(CAREER_FIELDS),
            "career_ambition": random.uniform(0.95, 1.0),  # muy alto
            "openness": random.uniform(0.0, 0.05),          # muy bajo
            "extraversion": random.uniform(0.95, 1.0),      # muy alto
            "agreeableness": random.uniform(0.0, 0.05),     # muy bajo
            "conscientiousness": random.uniform(0.95, 1.0),
            "chronotype": random.choice(CHRONOTYPES),
            "spontaneity": random.uniform(0.95, 1.0),       # muy alto
            "love_language": random.choice(LOVE_LANGUAGES),
            "emotional_expressiveness": random.uniform(0.0, 0.05),  # muy bajo
        }
    else:
        return {
            "age": random.uniform(22, 45),
            "education": random.uniform(0.3, 0.9),
            "location": random.choice(LOCATIONS),
            "career_field": random.choice(CAREER_FIELDS),
            "career_ambition": random.uniform(0.3, 0.8),
            "openness": random.uniform(0.3, 0.8),
            "extraversion": random.uniform(0.3, 0.8),
            "agreeableness": random.uniform(0.3, 0.8),
            "conscientiousness": random.uniform(0.3, 0.8),
            "chronotype": random.choice(CHRONOTYPES),
            "spontaneity": random.uniform(0.3, 0.8),
            "love_language": random.choice(LOVE_LANGUAGES),
            "emotional_expressiveness": random.uniform(0.3, 0.8),
        }


def simulate_drift(n: int):
    """Envía n peticiones con datos anómalos para forzar detección de drift."""
    print(f"Simulando drift con {n} peticiones anómalas...")
    ok = 0
    for i in range(n):
        payload = {
            "person_a": random_person(anomalous=True),
            "person_b": random_person(anomalous=True),
        }
        try:
            r = requests.post(API_URL, json=payload, timeout=10)
            if r.status_code == 200:
                ok += 1
        except requests.exceptions.ConnectionError:
            print("ERROR: La API no está disponible en http://localhost:8000")
            break
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{n} peticiones enviadas...")

    print(f"Completado: {ok}/{n} peticiones exitosas.")
    print("Ahora ejecutad el DAG en Airflow (http://localhost:8080) "
          "para ver la detección de drift.")


def simulate_load(n: int):
    """Envía n peticiones normales rápidas para simular pico de carga."""
    print(f"Simulando carga con {n} peticiones rápidas...")
    ok = 0
    start = time.time()
    for i in range(n):
        payload = {
            "person_a": random_person(anomalous=False),
            "person_b": random_person(anomalous=False),
        }
        try:
            r = requests.post(API_URL, json=payload, timeout=10)
            if r.status_code == 200:
                ok += 1
        except requests.exceptions.ConnectionError:
            print("ERROR: La API no está disponible en http://localhost:8000")
            break

    elapsed = time.time() - start
    print(f"Completado: {ok}/{n} peticiones en {elapsed:.1f}s "
          f"({n/elapsed:.1f} req/s)")
    print("Comprobad el spike en Grafana: http://localhost:3000")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simula entorno anómalo para CORE-MP")
    parser.add_argument("--mode", choices=["drift", "load"], required=True,
                        help="'drift': datos anómalos | 'load': carga masiva")
    parser.add_argument("--n", type=int, default=200,
                        help="Número de peticiones a enviar (default: 200)")
    args = parser.parse_args()

    if args.mode == "drift":
        simulate_drift(args.n)
    else:
        simulate_load(args.n)
