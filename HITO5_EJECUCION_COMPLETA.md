# Hito 5 — Documento de ejecución completa

**Proyecto:** CORE-MP (DISIA-G5)
**Hito:** 5 — Monitorización con Grafana y alertas vía Telegram
**Sistema operativo de desarrollo:** macOS

---

## Índice

1. [Resumen ejecutivo](#1-resumen-ejecutivo)
2. [Arquitectura del stack](#2-arquitectura-del-stack)
3. [Cambios sobre el código de partida](#3-cambios-sobre-el-código-de-partida)
4. [Ficheros nuevos y modificados](#4-ficheros-nuevos-y-modificados)
5. [Procedimiento de ejecución desde cero](#5-procedimiento-de-ejecución-desde-cero)
6. [Configuración del bot de Telegram](#6-configuración-del-bot-de-telegram)
7. [Configuración de alertas en Grafana](#7-configuración-de-alertas-en-grafana)
8. [Pruebas de validación](#8-pruebas-de-validación)
9. [Incidencias encontradas y resoluciones](#9-incidencias-encontradas-y-resoluciones)
10. [Cierre — commit y reproducibilidad](#10-cierre--commit-y-reproducibilidad)
11. [Enlaces del grupo](#11-enlaces-del-grupo)

---

## 1. Resumen ejecutivo

Se ha completado el Hito 5 consistente en:

- **Cuatro paneles en Grafana** sobre las métricas de la API:
  - Request Rate
  - Latencia P95
  - Total predicciones
  - Tasa de errores 5xx
- **Dashboard exportado** a JSON y provisionado automáticamente al arrancar el stack.
- **Dos alertas** con notificación a Telegram:
  - API caída (`up{job="core_mp_api"} == 0`)
  - Latencia P95 alta (`histogram_quantile(0.95, ...) > 0.5`)
- **Validación end-to-end** de ambas alertas, incluyendo los mensajes `FIRING` y `RESOLVED`.

Todo el stack se levanta con un único `docker compose up -d`, sin necesidad de configuración manual posterior en Grafana (datasource y dashboard se cargan vía provisioning).

---

## 2. Arquitectura del stack

El sistema completo se compone de seis contenedores orquestados por Docker Compose:

| Servicio | Imagen | Puerto en el host | Función |
| --- | --- | --- | --- |
| `train` | Build local (`Dockerfile.train`) | — | Entrena los modelos y termina |
| `api` | Build local (`Dockerfile.api`) | 8000 | API FastAPI de predicción + endpoint `/metrics/prometheus` |
| `prometheus` | `prom/prometheus:latest` | 9092 | Scraping de métricas, evaluación de queries |
| `pushgateway` | `prom/pushgateway:latest` | 9091 | Recepción de métricas de drift desde Airflow |
| `grafana` | `grafana/grafana:latest` | 3000 | Visualización + alerting |
| `airflow` | `apache/airflow:2.9.0-python3.11` | 8080 | Orquestador del feedback loop de drift |

> Nota: el puerto de Prometheus se movió de 9090 a 9092 por conflicto local con Proxyman. Dentro de la red Docker, Grafana sigue accediendo a Prometheus por `http://prometheus:9090`; el cambio solo afecta al acceso desde el navegador del host.

### Flujo de datos de la monitorización

```
                         ┌─────────────────────────┐
   Cliente ──POST───►    │  API FastAPI (:8000)    │
                         │  /predict               │
                         │  /metrics/prometheus    │
                         └──────────┬──────────────┘
                                    │ scrape /15s
                                    ▼
                         ┌─────────────────────────┐
                         │  Prometheus (:9090)     │
                         │  series temporales      │
                         └──────────┬──────────────┘
                                    │ query
                                    ▼
                         ┌─────────────────────────┐
                         │  Grafana (:3000)        │
                         │  - 4 paneles            │
                         │  - 2 alertas            │
                         └──────────┬──────────────┘
                                    │ webhook Telegram
                                    ▼
                         ┌─────────────────────────┐
                         │  Grupo Telegram (G5)    │
                         └─────────────────────────┘
```

---

## 3. Cambios sobre el código de partida

### 3.1 Métrica Prometheus custom (`predictions_total`)

El instrumentator que ya estaba en `src/main.py` (`prometheus_fastapi_instrumentator`) genera automáticamente las métricas `http_request_duration_seconds_*` (count, sum, bucket), pero **no** crea ninguna métrica que cuente predicciones por separado del recuento HTTP. El enunciado pedía un panel sobre `predictions_total`, por lo que se ha añadido esa métrica manualmente.

Modificación en `src/infer/router.py`:

```python
from prometheus_client import Counter

predictions_total = Counter(
    "predictions_total",
    "Número total de predicciones realizadas por la API CORE-MP",
    ["compatible"],
)

# Dentro del endpoint /predict, después de result = predictor.predict(...):
predictions_total.labels(
    compatible=str(result.get("compatible", False)).lower()
).inc()
```

La etiqueta `compatible=true/false` permite además ver el reparto entre predicciones positivas y negativas si se desea ampliar el dashboard en el futuro.

### 3.2 Puerto de Prometheus

Para evitar el conflicto con Proxyman (que en el equipo de desarrollo ocupaba el puerto 9090), se cambió el mapeo del contenedor en `docker-compose.yml`:

```yaml
prometheus:
  image: prom/prometheus:latest
  ports:
    - "9092:9090"   # antes: "9090:9090"
```

### 3.3 UID fijo en el datasource provisionado

Grafana genera por defecto un UID aleatorio para los datasources, lo que rompe los dashboards provisionados que referencian un UID concreto. Para evitarlo, se forzó el UID en `monitoring/grafana/provisioning/datasources/datasource.yml`:

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    uid: prometheus          # ← añadido
    url: http://prometheus:9090
    isDefault: true
    editable: true
```

Esto hace que el dashboard sea idempotente: se puede borrar Grafana y volver a levantar, y los paneles seguirán encontrando su datasource.

---

## 4. Ficheros nuevos y modificados

```
DISIA-G5/
├── GUIA_HITO5.md                                              ← nuevo (documentación)
├── HITO5_EJECUCION_COMPLETA.md                                ← este documento
├── docker-compose.yml                                         ← modificado (puerto Prometheus)
├── src/infer/router.py                                        ← modificado (Counter predictions_total)
└── monitoring/
    └── grafana/
        ├── dashboards/                                        ← carpeta nueva
        │   └── grafana_dashboard.json                         ← nuevo (dashboard exportado)
        └── provisioning/
            ├── datasources/
            │   └── datasource.yml                             ← modificado (uid: prometheus)
            └── dashboards/                                    ← carpeta nueva
                └── dashboards.yml                             ← nuevo (provisioning)
```

---

## 5. Procedimiento de ejecución desde cero

Pasos exactos para reproducir el hito en cualquier máquina con Docker Desktop instalado y arrancado.

### 5.1 Clonar el repositorio y situarse en la rama del hito

```bash
git clone <url-del-repo>
cd DISIA-G5
git checkout hito_5
```

### 5.2 Verificar que Docker Desktop está corriendo

```bash
docker info
```

Si responde con la información del daemon, todo OK. Si da `Cannot connect to the Docker daemon`, abrir Docker Desktop y esperar a que arranque por completo.

### 5.3 Levantar el stack completo

```bash
docker compose up -d --build
```

La primera vez tardará varios minutos descargando las imágenes de Prometheus, Grafana, Airflow y Pushgateway, y construyendo las imágenes locales de `train` y `api`.

Si los modelos `.pkl` no existen todavía:

```bash
docker compose run --rm train
docker compose up -d
```

### 5.4 Verificar que todos los contenedores están corriendo

```bash
docker compose ps
```

Salida esperada:

| Servicio | Estado |
| --- | --- |
| api | running |
| train | exited (0) |
| prometheus | running |
| pushgateway | running |
| grafana | running |
| airflow | running |

### 5.5 Validar la API

```bash
curl http://localhost:8000/health
```

Esperado:

```json
{"status":"ok","model_loaded":true,"version":"1.0.0"}
```

### 5.6 Generar tráfico inicial

```bash
for i in {1..10}; do
  curl -s -X POST http://localhost:8000/predict \
    -H "Content-Type: application/json" \
    -d '{
      "person_a":{"age":28,"education":0.75,"location":"Madrid","career_field":"Technology","career_ambition":0.8,"openness":0.72,"extraversion":0.55,"agreeableness":0.65,"conscientiousness":0.70,"chronotype":"morning","spontaneity":0.45,"love_language":"quality_time","emotional_expressiveness":0.60},
      "person_b":{"age":30,"education":0.80,"location":"Madrid","career_field":"Technology","career_ambition":0.75,"openness":0.68,"extraversion":0.60,"agreeableness":0.70,"conscientiousness":0.65,"chronotype":"morning","spontaneity":0.50,"love_language":"quality_time","emotional_expressiveness":0.55}
    }' >/dev/null
done
```

### 5.7 Validar la métrica custom

```bash
curl -s http://localhost:8000/metrics/prometheus | grep predictions_total
```

Esperado:

```
# HELP predictions_total Número total de predicciones realizadas por la API CORE-MP
# TYPE predictions_total counter
predictions_total{compatible="true"} 10.0
```

### 5.8 Validar Prometheus

Abrir `http://localhost:9092/targets` en el navegador.

Esperado: el job `core_mp_api` aparece con estado **UP** en verde.

### 5.9 Validar el dashboard

Abrir `http://localhost:3000` (Grafana), login con `admin` / `admin`, saltar el cambio de contraseña.

Navegar a **Dashboards** → debe aparecer **"CORE-MP — Monitorización API"** cargado automáticamente por provisioning. Abrirlo.

Generar más tráfico para visualizar datos en los paneles:

```bash
for i in {1..60}; do
  curl -s -X POST http://localhost:8000/predict \
    -H "Content-Type: application/json" \
    -d '{
      "person_a":{"age":28,"education":0.75,"location":"Madrid","career_field":"Technology","career_ambition":0.8,"openness":0.72,"extraversion":0.55,"agreeableness":0.65,"conscientiousness":0.70,"chronotype":"morning","spontaneity":0.45,"love_language":"quality_time","emotional_expressiveness":0.60},
      "person_b":{"age":30,"education":0.80,"location":"Madrid","career_field":"Technology","career_ambition":0.75,"openness":0.68,"extraversion":0.60,"agreeableness":0.70,"conscientiousness":0.65,"chronotype":"morning","spontaneity":0.50,"love_language":"quality_time","emotional_expressiveness":0.55}
    }' >/dev/null
  sleep 0.2
done
```

Verificar que los cuatro paneles muestran valores:

- **Request Rate (req/s)**: curva con valores ~5 req/s durante el bucle.
- **Latencia P95 (s)**: valores entre 0.005 y 0.05 s.
- **Total predicciones**: contador acumulado.
- **Tasa de errores 5xx**: plano a 0.

---

## 6. Configuración del bot de Telegram

> **Si el bot ya está creado** (porque otro miembro del grupo G5 lo creó, o porque ya se hizo en una ejecución anterior), **saltar directamente al apartado 6.2** y reutilizar el token existente. Solo hace falta crear un bot nuevo si no existe ninguno asociado al proyecto. Para recuperar el token de un bot ya creado: chat con @BotFather → `/mybots` → seleccionar el bot → **API Token**.

### 6.1 Crear el bot con @BotFather (solo si no existe ya)

1. En la app de Telegram, buscar **@BotFather** (oficial, con tick azul) y abrir el chat.
2. Enviar `/newbot`.
3. Responder con el **nombre** del bot (descriptivo, p. ej. `CORE-MP G5 Alerts`).
4. Responder con el **username** del bot (debe terminar en `bot` y ser único, p. ej. `core_mp_g5_alerts_bot`).
5. BotFather devuelve el HTTP API Token, en formato:

   ```
   1234567890:AAEhBOweik9ai8exAMPLEtoKEnW5dXq
   ```

   Este token se almacena de forma segura, **nunca se commitea al repositorio**.

### 6.2 Crear el grupo y obtener el chat_id

> Si el bot ya está añadido a un grupo del equipo y se conoce el `chat_id`, también se puede reutilizar y saltar directamente al apartado 6.3 para validar.

1. Crear un grupo nuevo en Telegram (`CORE-MP G5 Alerts`).
2. Añadir al bot como miembro del grupo.
3. **Importante** (solo si el bot es nuevo o no se hizo en una configuración anterior): desactivar el modo de privacidad del bot para que `getUpdates` funcione con mensajes normales:
   - Chat con @BotFather → `/mybots` → seleccionar bot → **Bot Settings** → **Group Privacy** → **Turn off**.
   - Eliminar el bot del grupo y volverlo a añadir (los cambios de privacidad solo aplican a memberships nuevas).
4. Escribir un mensaje cualquiera en el grupo (`/start` por ejemplo).
5. Abrir en el navegador:

   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```

6. En el JSON, localizar el bloque `"chat"`:

   ```json
   "chat": {
     "id": -4123456789,
     "title": "CORE-MP G5 Alerts",
     "type": "group"
   }
   ```

   Copiar el `id` completo, **incluyendo el signo `-` para grupos**.

### 6.3 Validar el bot desde terminal

```bash
TOKEN="..."        # token recibido de BotFather
CHAT_ID="..."      # chat_id del grupo, con signo -

curl -s "https://api.telegram.org/bot${TOKEN}/sendMessage" \
  -d "chat_id=${CHAT_ID}" \
  -d "text=Test desde terminal ✅"
```

Si el mensaje llega al grupo, las credenciales son correctas y se puede continuar con la configuración de Grafana.

---

## 7. Configuración de alertas en Grafana

### 7.1 Contact point Telegram

1. Grafana → **Alerts & IRM** → **Alerting** → pestaña **Contact points** → **+ Add contact point**.
2. Configuración:

   | Campo | Valor |
   | --- | --- |
   | Name | `telegram-g5` |
   | Integration | Telegram |
   | BOT API Token | (token de BotFather) |
   | Chat ID | (chat_id del grupo) |

3. Pulsar **Test** → seleccionar Predefined → **Send test notification**. Confirmar que llega al grupo.
4. **Save contact point**.

### 7.2 Apuntar la default policy

1. Pestaña **Notification policies** → bloque **Default policy** → `⋯` → **Edit**.
2. Cambiar **Default contact point** a `telegram-g5`.
3. **Update default policy**.

Verificación: en **Contact points**, la fila `telegram-g5` muestra "Used by 1 policy".

### 7.3 Alerta 1 — API caída

**Alerting** → **Alert rules** → **+ New alert rule**.

| Sección | Campo | Valor |
| --- | --- | --- |
| 1 | Name | `API caída — core_mp_api` |
| 2 | Datasource | Prometheus |
| 2 | Query (Code) | `up{job="core_mp_api"}` |
| 2 | Type | Instant |
| 2 | Alert condition: WHEN QUERY A | `Is below` `1` |
| 3 | Folder | `core-mp` (creada) |
| 3 | Labels | `severity = critical` |
| 4 | Evaluation group | `core-mp-critical`, interval `1m` |
| 4 | Pending period | `1m` |
| 5 | Contact point | `telegram-g5` |
| 6 | Summary | `API CORE-MP caída` |
| 6 | Description | `El job core_mp_api no responde al scrape de Prometheus.` |

**Save**.

### 7.4 Alerta 2 — Latencia P95 alta

| Sección | Campo | Valor |
| --- | --- | --- |
| 1 | Name | `Latencia P95 alta — core_mp_api` |
| 2 | Datasource | Prometheus |
| 2 | Query (Code) | `histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))` |
| 2 | Type | Instant |
| 2 | Alert condition: WHEN QUERY A | `Is above` `0.5` |
| 3 | Folder | `core-mp` |
| 3 | Labels | `severity = warning` |
| 4 | Evaluation group | `core-mp-warning`, interval `1m` |
| 4 | Pending period | `2m` |
| 5 | Contact point | `telegram-g5` |
| 6 | Summary | `Latencia P95 por encima de 500 ms` |
| 6 | Description | `El P95 de http_request_duration_seconds supera 0.5 s durante más de 2 minutos. Posible degradación del servicio.` |

**Save**.

### 7.5 Estado final esperado

En **Alert rules**, dentro de la carpeta `core-mp`, ambas reglas en estado **Normal** (verde) con la API corriendo y latencia baja.

---

## 8. Pruebas de validación

### 8.1 Prueba de la alerta "API caída"

**Procedimiento:**

```bash
docker compose stop api
```

**Timing observado:**
- T+15 s: Prometheus detecta el fallo de scrape → `up=0`.
- T+1 min: regla pasa a estado `Pending` en Grafana.
- T+2 min: regla pasa a `Firing` → notificación enviada a Telegram.

**Resultado:** mensaje recibido en el grupo de Telegram en estado `[FIRING:1]`, con summary y description correctos. ✅

**Restauración:**

```bash
docker compose start api
```

Tras ~1 min, regla vuelve a `Normal` y llega mensaje `[RESOLVED]`. ✅

### 8.2 Prueba de la alerta "Latencia P95 alta"

Como la API responde en milisegundos, el umbral real (0.5 s) no es alcanzable en condiciones normales. Para validar el mecanismo se bajó el umbral temporalmente.

**Procedimiento:**

1. Editar regla → cambiar threshold de `0.5` a `0.001` y pending period de `2m` a `1m`.
2. Generar tráfico:

   ```bash
   for i in {1..100}; do
     curl -s -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d '...' >/dev/null
     sleep 0.2
   done
   ```

3. Esperar ~2 min.

**Resultado:** mensaje recibido en el grupo de Telegram en estado `[FIRING:1]`. ✅

**Restauración:**

- Threshold → `0.5`.
- Pending period → `2m`.

Regla vuelve a `Normal` y llega mensaje `[RESOLVED]`. ✅

### 8.3 Resumen de validación

| Prueba | Resultado |
| --- | --- |
| API responde a `/health` con `model_loaded: true` | ✅ |
| Métrica `predictions_total` se incrementa con cada predicción | ✅ |
| Prometheus scrape de `core_mp_api` en estado UP | ✅ |
| Datasource Prometheus en Grafana en estado "Successfully queried" | ✅ |
| Los 4 paneles del dashboard muestran datos en tiempo real | ✅ |
| Contact point `telegram-g5` envía mensaje de Test correctamente | ✅ |
| Alerta `API caída` dispara FIRING al parar la API | ✅ |
| Alerta `API caída` envía RESOLVED al levantar la API | ✅ |
| Alerta `Latencia P95 alta` dispara FIRING con umbral bajado | ✅ |
| Alerta `Latencia P95 alta` envía RESOLVED al restaurar umbral | ✅ |

---

## 9. Incidencias encontradas y resoluciones

### 9.1 Conflicto de puerto 9090 con Proxyman

**Síntoma:** al abrir `http://localhost:9090/targets`, aparece la página de Proxyman en lugar de Prometheus.

**Causa:** Proxyman ocupaba el puerto 9090 en el equipo de desarrollo.

**Resolución:** se cambió el mapeo en `docker-compose.yml` a `9092:9090`. La comunicación interna entre Grafana y Prometheus no se ve afectada (sigue usando `http://prometheus:9090` por la red Docker).

### 9.2 Dashboard provisionado sin datos por UID de datasource incorrecto

**Síntoma:** dashboard cargado correctamente pero los cuatro paneles muestran "No data".

**Causa:** el JSON del dashboard referencia `"uid": "prometheus"`, pero Grafana había auto-generado un UID aleatorio para el datasource (`PBFA97CFB590B2093`).

**Resolución:** se forzó el UID en `monitoring/grafana/provisioning/datasources/datasource.yml` añadiendo `uid: prometheus`. Tras recrear el contenedor de Grafana, el UID coincide y los paneles encuentran su datasource.

### 9.3 Bot de Telegram con privacidad activada por defecto

**Síntoma:** la URL `https://api.telegram.org/bot<TOKEN>/getUpdates` devolvía `{"ok":true,"result":[]}` aunque el bot estaba en el grupo y había mensajes.

**Causa:** los bots de Telegram tienen "Privacy Mode" activado por defecto, por lo que solo reciben mensajes que empiecen por `/` o que mencionen explícitamente al bot.

**Resolución:** se desactivó el Privacy Mode desde @BotFather (`/mybots` → Bot Settings → Group Privacy → Turn off) y se quitó y volvió a añadir el bot al grupo para que el cambio surtiera efecto.

### 9.4 Métrica `predictions_total` no existía

**Síntoma:** el panel "Total predicciones" no encuentra datos aunque `prometheus-fastapi-instrumentator` esté activo.

**Causa:** el instrumentator solo genera `http_request_duration_seconds_*` por defecto. La métrica `predictions_total` no se crea automáticamente.

**Resolución:** se añadió un `Counter` de `prometheus_client` en `src/infer/router.py` que se incrementa tras cada predicción exitosa.

---

## 10. Cierre — commit y reproducibilidad

### 10.1 Comandos de cierre

```bash
git checkout hito_5

git add monitoring/grafana/dashboards/grafana_dashboard.json
git add monitoring/grafana/provisioning/dashboards/dashboards.yml
git add monitoring/grafana/provisioning/datasources/datasource.yml
git add src/infer/router.py
git add docker-compose.yml
git add GUIA_HITO5.md
git add HITO5_EJECUCION_COMPLETA.md

git commit -m "feat(hito5): monitorización con Grafana y alertas Telegram

- Dashboard provisionado con 4 paneles: request rate, latencia P95, total
  predicciones y tasa de errores 5xx.
- Datasource Prometheus con UID fijo para provisioning idempotente.
- Métrica custom predictions_total en src/infer/router.py.
- Alertas: API caída (up==0) y latencia P95 > 0.5s, ambas vía contact
  point telegram-g5.
- Puertos ajustados: Prometheus a 9092 (conflicto local con Proxyman)."

git push origin hito_5
```

### 10.2 Detener el stack

```bash
docker compose down
```

### 10.3 Reproducibilidad

Para reproducir el hito en una nueva máquina basta con:

```bash
git clone <repo>
cd DISIA-G5
git checkout hito_5
docker compose run --rm train     # solo la primera vez
docker compose up -d
```

El único paso manual restante es la configuración del contact point y las alertas en la UI de Grafana, ya que contienen credenciales sensibles (token del bot, chat_id) que no se versionan. Estos pasos están detallados en las secciones 6 y 7 de este documento.

---

## 11. Enlaces del grupo

> Pegar aquí, si el evaluador necesita verlo en vivo:
>
> - **Enlace de invitación al grupo de Telegram:** _[pegar aquí el enlace de invitación si procede]_
> - **Username del bot:** `@_______________bot`
>
> Para obtener el enlace de invitación al grupo: abrir la info del grupo → **Invite Link** → Copy.
>
> **Importante:** una vez evaluado el hito, revocar el enlace de invitación desde la misma pantalla para evitar accesos no deseados, y considerar rotar el token del bot si fuera necesario.

---

## Anexo — Capturas para la memoria

Capturas recomendadas a incluir en la memoria LaTeX del proyecto:

1. Vista de los 4 paneles del dashboard con datos.
2. Listado de Alert rules mostrando las dos reglas en estado Normal.
3. Pestaña Contact points con `telegram-g5` configurado.
4. Pestaña Notification policies con la default policy apuntando a `telegram-g5`.
5. Capturas del grupo de Telegram con los 4 mensajes (FIRING + RESOLVED de cada alerta).
6. Vista de Prometheus → Targets con `core_mp_api` en estado UP.

---

**Fin del documento.**
