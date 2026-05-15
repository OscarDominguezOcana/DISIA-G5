"""
generate_reference_data.py
──────────────────────────
Script para generar el CSV de datos de referencia que usa Evidently
para detectar drift. Ejecutad UNA SOLA VEZ antes de levantar el sistema.

Uso:
    python scripts/generate_reference_data.py

Genera:  data/monitoring/reference_data.csv
"""
import os
import pandas as pd

# ─── Rutas ────────────────────────────────────────────────────────────────────
DATASET_PATH   = "cupid_algorithm_dataset.csv"
OUTPUT_DIR     = "monitoring/reference"
OUTPUT_PATH    = os.path.join(OUTPUT_DIR, "reference_data.csv")
N_SAMPLES      = 2000   # muestra representativa del dataset original

# ─── Columnas del dataset original ───────────────────────────────────────────
# (ajustad estos nombres si los vuestros son diferentes)
COL = {
    "a_love_language":             "a_love_language",
    "b_love_language":             "b_love_language",
    "a_career_ambition":           "a_career_ambition",
    "b_career_ambition":           "b_career_ambition",
    "a_emotional_expressiveness":  "a_emotional_expressiveness",
    "b_emotional_expressiveness":  "b_emotional_expressiveness",
    "a_spontaneity":               "a_spontaneity",
    "b_spontaneity":               "b_spontaneity",
    "a_openness":                  "a_openness",
    "b_openness":                  "b_openness",
    "a_extraversion":              "a_extraversion",
    "b_extraversion":              "b_extraversion",
    "a_agreeableness":             "a_agreeableness",
    "b_agreeableness":             "b_agreeableness",
    "a_conscientiousness":         "a_conscientiousness",
    "b_conscientiousness":         "b_conscientiousness",
    "compatibility_score":         "compatibility_score",
}


def main():
    print(f"Leyendo dataset desde: {DATASET_PATH}")
    df = pd.read_csv(DATASET_PATH).sample(N_SAMPLES, random_state=42)

    reference = pd.DataFrame({
        "same_love_language": (
            df[COL["a_love_language"]] == df[COL["b_love_language"]]
        ).astype(int),

        "ambition_diff": abs(
            df[COL["a_career_ambition"]] - df[COL["b_career_ambition"]]
        ),

        "emotional_expressiveness_diff": abs(
            df[COL["a_emotional_expressiveness"]] - df[COL["b_emotional_expressiveness"]]
        ),

        "spontaneity_diff": abs(
            df[COL["a_spontaneity"]] - df[COL["b_spontaneity"]]
        ),

        # overall_match_score: aproximación con las features disponibles
        "overall_match_score": df[COL["compatibility_score"]] / 100.0,

        "personality_distance_sum": (
            abs(df[COL["a_openness"]]          - df[COL["b_openness"]])
            + abs(df[COL["a_extraversion"]]    - df[COL["b_extraversion"]])
            + abs(df[COL["a_agreeableness"]]   - df[COL["b_agreeableness"]])
            + abs(df[COL["a_conscientiousness"]]- df[COL["b_conscientiousness"]])
        ),
    })

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    reference.to_csv(OUTPUT_PATH, index=False)
    print(f"Datos de referencia generados: {OUTPUT_PATH}")
    print(f"  Filas: {len(reference)}")
    print(f"  Columnas: {list(reference.columns)}")
    print(reference.describe().round(3))


if __name__ == "__main__":
    main()
