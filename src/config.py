"""
config.py
Configuración centralizada — todos los parámetros del proyecto se leen
desde variables de entorno con valores por defecto reproducibles.
"""
import os

# ── Datos ────────────────────────────────────────────────────────────────────
DATA_PATH = os.getenv("DATA_PATH", "data/raw/cupid_algorithm_dataset.csv")

# ── Modelos ──────────────────────────────────────────────────────────────────
MODELS_DIR = os.getenv("MODELS_DIR", "models")
CLF_MODEL_PATH = os.getenv("CLF_MODEL_PATH", "models/clf_model.pkl")
REG_MODEL_PATH = os.getenv("REG_MODEL_PATH", "models/reg_model.pkl")

# ── Entrenamiento ────────────────────────────────────────────────────────────
RANDOM_STATE = 42
TEST_SIZE = 0.15   # 70 / 15 / 15
