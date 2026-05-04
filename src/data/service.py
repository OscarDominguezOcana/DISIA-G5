import pandas as pd

from src.config import DATA_PATH


def load_dataset(path: str = DATA_PATH) -> pd.DataFrame:
    """Carga el CSV principal y devuelve un DataFrame sin modificar."""
    df = pd.read_csv(path)
    print(f"[data] Dataset cargado: {df.shape[0]} filas, {df.shape[1]} columnas.")
    return df
