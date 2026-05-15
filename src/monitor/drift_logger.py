"""
drift_logger.py
Guarda los datos de entrada de cada predicción en un CSV
para ser comparados con los datos de referencia por Evidently.

Se invoca desde src/infer/router.py tras cada predicción.
"""
import csv
import os

MONITORING_DIR = os.getenv("MONITORING_DIR", "./data/monitoring")
CURRENT_TRAFFIC_PATH = os.path.join(MONITORING_DIR, "current_traffic.csv")

# Las features más importantes según el análisis del Hito 3
DRIFT_FEATURES = [
    "same_love_language",
    "ambition_diff",
    "emotional_expressiveness_diff",
    "spontaneity_diff",
    "overall_match_score",
    "personality_distance_sum",
]


def log_input(person_a: dict, person_b: dict, result: dict) -> None:
    """
    Añade una fila al CSV de tráfico actual con las features derivadas.
    Se calcula igual que en src/features/service.py para ser consistente
    con los datos de referencia.
    """
    os.makedirs(MONITORING_DIR, exist_ok=True)

    row = {
        "same_love_language": int(
            person_a["love_language"] == person_b["love_language"]
        ),
        "ambition_diff": abs(
            person_a["career_ambition"] - person_b["career_ambition"]
        ),
        "emotional_expressiveness_diff": abs(
            person_a["emotional_expressiveness"] - person_b["emotional_expressiveness"]
        ),
        "spontaneity_diff": abs(
            person_a["spontaneity"] - person_b["spontaneity"]
        ),
        "overall_match_score": result["overall_match_score"],
        "personality_distance_sum": (
            abs(person_a["openness"] - person_b["openness"])
            + abs(person_a["extraversion"] - person_b["extraversion"])
            + abs(person_a["agreeableness"] - person_b["agreeableness"])
            + abs(person_a["conscientiousness"] - person_b["conscientiousness"])
        ),
    }

    write_header = not os.path.exists(CURRENT_TRAFFIC_PATH)
    with open(CURRENT_TRAFFIC_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=DRIFT_FEATURES)
        if write_header:
            writer.writeheader()
        writer.writerow(row)
