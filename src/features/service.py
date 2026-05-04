"""
Feature engineering stateless de CORE-MP.

Todas las funciones son puras (sin estado): se aplican idénticamente
en training e inferencia, garantizando cero training-serving skew.
"""
import numpy as np
import pandas as pd

from src.features.constants import CLF_FEATURES, PERSONALITY_TRAITS, REG_FEATURES


def create_pair_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Genera 23 features relacionales a partir de las columnas brutas a_* / b_*.
    Stateless: no ajusta parámetros ni guarda artefactos.
    """
    fe = pd.DataFrame(index=df.index)

    fe["age_gap"] = np.abs(df["a_age"] - df["b_age"])
    fe["education_diff"] = np.abs(df["a_education"] - df["b_education"])
    fe["ambition_diff"] = np.abs(df["a_career_ambition"] - df["b_career_ambition"])
    fe["spontaneity_diff"] = np.abs(df["a_spontaneity"] - df["b_spontaneity"])
    fe["emotional_expressiveness_diff"] = np.abs(
        df["a_emotional_expressiveness"] - df["b_emotional_expressiveness"]
    )

    for trait in PERSONALITY_TRAITS:
        fe[f"{trait}_diff"] = np.abs(df[f"a_{trait}"] - df[f"b_{trait}"])

    trait_cols = [f"{t}_diff" for t in PERSONALITY_TRAITS]
    fe["personality_distance_mean"] = fe[trait_cols].mean(axis=1)
    fe["personality_distance_sum"] = fe[trait_cols].sum(axis=1)

    fe["same_location"] = (df["a_location"] == df["b_location"]).astype(int)
    fe["same_career_field"] = (df["a_career_field"] == df["b_career_field"]).astype(int)
    fe["same_chronotype"] = (df["a_chronotype"] == df["b_chronotype"]).astype(int)
    fe["same_love_language"] = (df["a_love_language"] == df["b_love_language"]).astype(int)

    fe["age_gap_small"] = (fe["age_gap"] <= 5).astype(int)
    fe["age_gap_medium"] = ((fe["age_gap"] > 5) & (fe["age_gap"] <= 10)).astype(int)
    fe["age_gap_large"] = (fe["age_gap"] > 10).astype(int)
    fe["very_large_age_gap"] = (fe["age_gap"] > 15).astype(int)

    fe["high_personality_similarity"] = (fe["personality_distance_mean"] < 0.20).astype(int)
    fe["similar_ambition"] = (fe["ambition_diff"] < 0.20).astype(int)

    fe["same_location_and_love_language"] = fe["same_location"] * fe["same_love_language"]

    fe["overall_match_score"] = (
        (1 - fe["personality_distance_mean"]) * 0.45
        + (1 - fe["ambition_diff"]) * 0.25
        + fe["same_location"] * 0.10
        + fe["same_love_language"] * 0.10
        + (1 - np.clip(fe["age_gap"] / 20, 0, 1)) * 0.10
    )

    return fe


def get_clf_features(fe: pd.DataFrame) -> pd.DataFrame:
    return fe[CLF_FEATURES]


def get_reg_features(fe: pd.DataFrame) -> pd.DataFrame:
    return fe[REG_FEATURES]


def pair_dict_to_features(person_a: dict, person_b: dict) -> pd.DataFrame:
    """Convierte dos dicts de persona en un DataFrame de features listo para inferencia."""
    row = {f"a_{k}": v for k, v in person_a.items()}
    row.update({f"b_{k}": v for k, v in person_b.items()})
    return create_pair_features(pd.DataFrame([row]))
