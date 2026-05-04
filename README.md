# CORE-MP — Despliegue en Producción (Hito 4)

## Arquitectura de Despliegue

El sistema se compone de **dos contenedores Docker independientes** que comparten un volumen de modelos:

```
┌─────────────────────────┐                         ┌───────────────────────────┐
│   Contenedor: train     │                         │   Contenedor: api         │
│                         │                         │                           │
│  data_ingestion.py      │                         │  infer.py (CupidPredictor)│
│  features.py            │                         │  features.py (stateless)  │
│  train.py               │                         │  api.py (FastAPI)         │
│                         │                         │                           │
│  Salida:                │                         │  Escucha: :8000           │
│  clf_model.pkl          │                         │  POST /predict            │
│  reg_model.pkl          │                         │  GET  /health             │
└─────────────────────────┘                         │  GET  /metrics            │
                                                    └───────────────────────────┘
```

### Decisiones de diseño

| Decisión                             | Justificación                                                                                                 |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------- |
| 2 contenedores separados             | Training y serving tienen ciclos de vida distintos. El contenedor de training termina; la API es persistente. |
| Volumen compartido de modelos        | Desacoplamiento: la API no necesita saber cómo se entrena el modelo.                                          |
| Fail-fast en arranque de API         | Si los `.pkl` no existen, la API no arranca. Evita servir peticiones sin modelo.                              |
| Features stateless en `features.py`  | Aplicar la misma función en training e inferencia elimina el riesgo de _training-serving skew_.               |
| Log-transform en regresión           | `np.log1p(y)` estabiliza la distribución del target; se invierte con `np.expm1()` en inferencia.              |
| `StandardScaler` dentro del Pipeline | El scaler se ajusta solo sobre train y se serializa con el modelo; nunca se re-ajusta en inferencia.          |

---

## Puesta en Marcha

### Prerrequisitos

- Docker Desktop (o Docker Engine + Compose plugin)
- El dataset `cupid_algorithm_dataset.csv` en `data/raw/`

```bash
# Crear carpetas necesarias
mkdir -p data/raw models_output

# Copiar el dataset
cp cupid_algorithm_dataset.csv data/raw/
```

### Paso 1 — Entrenar los modelos

```bash
docker compose run --rm train
```

Al finalizar, aparecerán en `models_output/`:

- `clf_model.pkl` — Pipeline LogisticRegression + StandardScaler
- `reg_model.pkl` — Ridge Regression

### Paso 2 — Levantar la API

```bash
docker compose up api
```

La API queda disponible en `http://localhost:8000`.
Documentación interactiva (Swagger): `http://localhost:8000/docs`

---

## Endpoints

| Método | Ruta       | Descripción                  |
| ------ | ---------- | ---------------------------- |
| `GET`  | `/health`  | Estado del servicio          |
| `GET`  | `/metrics` | Latencia media acumulada     |
| `POST` | `/predict` | Predicción de compatibilidad |

---

## Ejemplo de Request

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "person_a": {
      "age": 28,
      "education": 0.75,
      "location": "Madrid",
      "career_field": "Technology",
      "career_ambition": 0.8,
      "openness": 0.72,
      "extraversion": 0.55,
      "agreeableness": 0.65,
      "conscientiousness": 0.70,
      "chronotype": "morning",
      "spontaneity": 0.45,
      "love_language": "quality_time",
      "emotional_expressiveness": 0.60
    },
    "person_b": {
      "age": 30,
      "education": 0.80,
      "location": "Madrid",
      "career_field": "Technology",
      "career_ambition": 0.75,
      "openness": 0.68,
      "extraversion": 0.60,
      "agreeableness": 0.70,
      "conscientiousness": 0.65,
      "chronotype": "morning",
      "spontaneity": 0.50,
      "love_language": "quality_time",
      "emotional_expressiveness": 0.55
    }
  }'
```

### Ejemplo de Respuesta

```json
{
  "compatible": true,
  "compatibility_probability": 0.7832,
  "estimated_longevity_months": 74.5,
  "overall_match_score": 0.8215,
  "model_version": "1.0.0",
  "latency_ms": 4.217
}
```

---

## Monitoreo y Validación

### Latencia media

Cada respuesta incluye `latency_ms`. La latencia media acumulada se calcula como:

```
          Σ (t_respuesta_i − t_solicitud_i)
L̄  =  ─────────────────────────────────────
                  N_peticiones
```

Disponible en tiempo real en `GET /metrics`:

```bash
curl http://localhost:8000/metrics
```

```json
{
  "total_requests": 42,
  "total_latency_ms": 187.4,
  "mean_latency_ms": 4.46
}
```

### Health check

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "ok",
  "model_loaded": true,
  "version": "1.0.0"
}
```

### Validación del modelo en producción

Métricas del modelo final (Hito 3):

| Tarea         | Modelo              | Métrica  | Valor       |
| ------------- | ------------------- | -------- | ----------- |
| Clasificación | Logistic Regression | F1-Score | 0.6828      |
| Clasificación | Logistic Regression | ROC-AUC  | 0.7917      |
| Regresión     | Ridge (α=1.0)       | MAE      | 16.27 meses |
| Regresión     | Ridge (α=1.0)       | RMSE     | 20.33 meses |

---

## Estructura del Proyecto

```
DISIA-G5/
├── src/
│   ├── data_ingestion.py   # Carga del CSV
│   ├── features.py         # Feature engineering (stateless)
│   ├── train.py            # Entrenamiento y serialización
│   ├── infer.py            # CupidPredictor (carga y predicción)
│   └── api.py              # FastAPI (endpoints REST)
├── data/
│   └── raw/                # Dataset de entrada (montar como volumen)
├── models_output/          # Modelos serializados (generado por train)
├── Dockerfile.train
├── Dockerfile.api
├── docker-compose.yml
└── requirements.txt
```
