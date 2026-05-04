"""CupidPredictor — carga los modelos serializados y ejecuta inferencia."""
import numpy as np
import joblib

from src.config import CLF_MODEL_PATH, REG_MODEL_PATH
from src.features.service import get_clf_features, get_reg_features, pair_dict_to_features
from src.infer.exceptions import PredictionError


class CupidPredictor:
    def __init__(
        self,
        clf_path: str = CLF_MODEL_PATH,
        reg_path: str = REG_MODEL_PATH,
    ):
        self.clf = joblib.load(clf_path)
        self.reg = joblib.load(reg_path)
        print(f"[predict] Modelos cargados desde {clf_path} y {reg_path}")

    def predict(self, person_a: dict, person_b: dict) -> dict:
        try:
            fe = pair_dict_to_features(person_a, person_b)
            prob = float(self.clf.predict_proba(get_clf_features(fe))[0, 1])
            longevity = max(0.0, round(float(np.expm1(self.reg.predict(get_reg_features(fe))[0])), 1))
        except Exception as exc:
            raise PredictionError(str(exc)) from exc

        return {
            "compatible": prob >= 0.5,
            "compatibility_probability": round(prob, 4),
            "estimated_longevity_months": longevity,
            "overall_match_score": round(float(fe["overall_match_score"].iloc[0]), 4),
        }
