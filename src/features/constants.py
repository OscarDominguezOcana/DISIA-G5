"""Constantes de feature engineering — listas de features seleccionadas."""

PERSONALITY_TRAITS = ["openness", "extraversion", "agreeableness", "conscientiousness"]

# 20 features seleccionadas por mutual_info_classif
CLF_FEATURES = [
    "overall_match_score",
    "same_love_language",
    "ambition_diff",
    "similar_ambition",
    "emotional_expressiveness_diff",
    "same_location_and_love_language",
    "personality_distance_sum",
    "personality_distance_mean",
    "high_personality_similarity",
    "spontaneity_diff",
    "age_gap_large",
    "very_large_age_gap",
    "same_career_field",
    "same_location",
    "age_gap_small",
    "age_gap",
    "education_diff",
    "extraversion_diff",
    "agreeableness_diff",
    "openness_diff",
]

# 16 features seleccionadas por mutual_info_regression
REG_FEATURES = [
    "overall_match_score",
    "same_love_language",
    "personality_distance_mean",
    "personality_distance_sum",
    "ambition_diff",
    "emotional_expressiveness_diff",
    "same_location_and_love_language",
    "similar_ambition",
    "openness_diff",
    "spontaneity_diff",
    "conscientiousness_diff",
    "education_diff",
    "age_gap",
    "same_chronotype",
    "very_large_age_gap",
    "same_location",
]
