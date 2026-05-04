from src.exceptions import CupidAlgorithmError


class ModelNotFoundError(CupidAlgorithmError):
    """Se lanza cuando un fichero de modelo serializado no existe en disco."""


class PredictionError(CupidAlgorithmError):
    """Se lanza cuando el pipeline de inferencia falla de forma inesperada."""
