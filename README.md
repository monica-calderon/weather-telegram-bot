# weather-telegram-bot

Bot meteorologico en Python que consulta AEMET OpenData y envia resúmenes diarios por Telegram con prediccion, temperatura actual y avisos relevantes del dia.

El proyecto esta preparado para ejecutarse en local con `.env` y en GitHub Actions. La programacion se delega a cron-job.org, que llama a la API de GitHub para lanzar los workflows.

## Que hace

- Consulta la prediccion diaria por municipio de AEMET OpenData.
- Consulta observacion convencional de AEMET para incluir temperatura actual, con fallback a la temperatura prevista para la hora del resumen.
- Incluye estado de cielo previsto en el resumen diario.
- Intenta consultar avisos oficiales AEMET.
- Aplica reglas configurables por variables de entorno e incluye los avisos dentro del resumen diario.
- Reutiliza datos cacheados para reducir llamadas a AEMET y resistir limites temporales de la API.
- Envia mensajes con Telegram Bot API.
- Mantiene workflows de GitHub Actions para ejecucion manual o disparo por API.
- Usa cron-job.org como reloj externo mas fiable que el scheduler nativo de GitHub.

## Configuracion local

1. Crea y activa un entorno virtual:

```bash
python -m venv .venv
.venv\Scripts\activate
```

2. Instala dependencias:

```bash
pip install -r requirements.txt
```

3. Crea tu `.env` desde el ejemplo:

```bash
copy .env.example .env
```

4. Rellena las variables:

```env
AEMET_API_KEY=tu_api_key
TELEGRAM_BOT_TOKEN=123456:ABCDEF
TELEGRAM_CHAT_ID=123456789
MUNICIPIO_ID=28005
MUNICIPIO_NOMBRE=Alcalá de Henares
TIMEZONE=Europe/Madrid
RAIN_PROB_THRESHOLD=50
WIND_KMH_THRESHOLD=45
HEAT_TEMP_THRESHOLD=35
COLD_TEMP_THRESHOLD=0
AEMET_ALERT_AREA=72
AEMET_STATION_ID=3170Y
CURRENT_OBSERVATION_MAX_AGE_MINUTES=150
```

## Crear bot de Telegram

1. Abre Telegram y busca `@BotFather`.
2. Envia `/newbot`.
3. Ponle nombre y username.
4. BotFather te dara un token. Ese valor es `TELEGRAM_BOT_TOKEN`.
5. Inicia una conversacion con tu bot y mandale cualquier mensaje.

Para obtener `TELEGRAM_CHAT_ID`, abre en el navegador:

```text
https://api.telegram.org/bot<TU_TOKEN>/getUpdates
```

Busca el campo `chat.id` en la respuesta JSON.

## Obtener API key de AEMET

1. Entra en [AEMET OpenData](https://opendata.aemet.es/).
2. Pulsa `Obtencion de API Key`.
3. Introduce tu email y completa el proceso.
4. Usa la clave recibida como `AEMET_API_KEY`.

## Encontrar MUNICIPIO_ID

AEMET usa el codigo INE del municipio. Puedes encontrarlo en:

- El endpoint de AEMET `/api/maestro/municipios`.
- La documentacion de desarrolladores de AEMET OpenData.
- Listados oficiales del INE.

Ejemplo: `28005` corresponde a Alcala de Henares.

## Ejecutar

Alertas locales/manuales:

```bash
python -m src.main alerts
```

El modo `alerts` se conserva para pruebas locales puntuales. La automatizacion recomendada ya no lo usa para evitar llamadas frecuentes a AEMET.

Resumen diario:

```bash
python -m src.main daily
```

En el resumen diario, `Actual` usa la ultima observacion disponible de AEMET; si no existe, muestra la temperatura prevista para la hora del resumen con el sufijo `prev.`. `Lluvia máx.` y `Viento máx.` no son valores actuales ni medias: son el valor maximo previsto por AEMET para algun tramo del dia. Si las reglas detectan lluvia, viento, calor, frio/helada o avisos oficiales, el resumen añade la seccion `Avisos del día` con el detalle y, cuando AEMET lo publica, el tramo horario afectado.

Para reducir errores `429 Too Many Requests`, el workflow guarda una cache persistente y minima en la rama `bot-state`:

- Prediccion municipal: se consulta como maximo una vez al dia y se guarda ya normalizada, incluyendo temperaturas por hora para calcular `Actual` si falta observacion real.
- Avisos oficiales: se consultan como maximo una vez al dia y se guardan ya normalizados.
- Observacion actual: se consulta en cada resumen; solo se usa cache si AEMET limita la API. La hora de la observacion se convierte a `TIMEZONE` y no se muestra como actual si supera `CURRENT_OBSERVATION_MAX_AGE_MINUTES`.

Si un resumen usa cache por limite temporal de AEMET, el mensaje incluye la nota `datos cacheados por límite temporal de AEMET`.

Tests:

```bash
pytest
```

El proyecto incluye `pytest.ini` para que `src` se pueda importar al ejecutar `pytest` directamente desde la raiz del repositorio.

## GitHub Actions

Configura estos `Secrets` en tu repositorio:

- `AEMET_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Configura estas `Variables` del repositorio:

- `MUNICIPIO_ID`
- `MUNICIPIO_NOMBRE`
- `TIMEZONE`
- `RAIN_PROB_THRESHOLD`
- `WIND_KMH_THRESHOLD`
- `HEAT_TEMP_THRESHOLD`
- `COLD_TEMP_THRESHOLD`
- `AEMET_ALERT_AREA` opcional, por defecto `72` para Comunidad de Madrid.
- `AEMET_STATION_ID` opcional. Si lo configuras, se usa esa estacion AEMET para la temperatura actual. Para Alcala de Henares se recomienda `3170Y`; si `MUNICIPIO_ID=28005` y lo dejas vacio, el bot usa ese valor por defecto. Para otros municipios, si lo dejas vacio, el bot intenta encontrar una observacion cuyo nombre coincida con `MUNICIPIO_NOMBRE`.
- `CURRENT_OBSERVATION_MAX_AGE_MINUTES` opcional, por defecto `150`. Evita mostrar como actual una observacion de AEMET demasiado antigua.

Hay dos workflows:

- `Weather daily summary`: ejecucion manual o por API con `workflow_dispatch`.
- `CI`: ejecuta los tests con `pytest` en cada push, pull request o manualmente.

Las notificaciones programadas quedan delegadas a cron-job.org. GitHub Actions ejecuta el codigo cuando cron-job.org llama a la API de GitHub.

## cron-job.org + GitHub Actions

cron-job.org no ejecuta Python directamente. En este proyecto se usa para llamar a GitHub y lanzar los workflows mediante `workflow_dispatch`.

### 1. Crear token de GitHub para cron-job.org

En GitHub, crea un token para que cron-job.org pueda lanzar workflows:

1. Ve a `GitHub` -> `Settings` -> `Developer settings`.
2. Entra en `Personal access tokens` -> `Fine-grained tokens`.
3. Crea un token nuevo.
4. Repository access: selecciona solo `monica-calderon/weather-telegram-bot`.
5. Repository permissions: concede `Actions: Read and write`.
6. Copia el token. Solo se vera una vez.

Guarda ese token solo en cron-job.org. No lo subas al repo ni lo pongas en `.env`.

### 2. Jobs de resumen diario a las 08:15, 14:30 y 19:00

Crea tres jobs en cron-job.org, uno a las `08:15`, otro a las `14:30` y otro a las `19:00`, todos con:

- URL: `https://api.github.com/repos/monica-calderon/weather-telegram-bot/actions/workflows/weather-daily.yml/dispatches`
- Method: `POST`
- Timezone: `Europe/Madrid`
- Expected status: `204`

Headers:

```text
Accept: application/vnd.github+json
Authorization: Bearer TU_TOKEN_DE_GITHUB
X-GitHub-Api-Version: 2022-11-28
Content-Type: application/json
```

Body:

```json
{"ref":"main"}
```

### 3. Probar

Al ejecutar bien, GitHub responde `204 No Content`. Despues veras una ejecucion nueva en `Actions`.

Si cron-job.org devuelve `401`, el token de GitHub no es valido o no tiene permiso `Actions: Read and write`.

Si devuelve `404`, revisa que el repositorio, el workflow o el branch `main` esten bien escritos.

No compartas el token de GitHub usado en cron-job.org. Si se filtra, revocalo y crea otro.

## Cambiar frecuencia y umbrales

La frecuencia se cambia en cron-job.org. Los workflows del repo no tienen `schedule` propio para evitar ejecuciones duplicadas.

Los umbrales se cambian con variables del repositorio o en `.env` para local:

- `RAIN_PROB_THRESHOLD`: probabilidad de lluvia minima. Por defecto `50`.
- `WIND_KMH_THRESHOLD`: viento minimo en km/h.
- `HEAT_TEMP_THRESHOLD`: temperatura maxima para alerta de calor.
- `COLD_TEMP_THRESHOLD`: temperatura minima para frio/helada.
- `AEMET_ALERT_AREA`: area de avisos oficiales. `72` es Comunidad de Madrid.
- `AEMET_STATION_ID`: estacion AEMET para temperatura actual, opcional. Para Alcala de Henares usa `3170Y`.
- `CURRENT_OBSERVATION_MAX_AGE_MINUTES`: antiguedad maxima aceptada para la observacion actual, por defecto `150`.

## Privacidad y seguridad

- No subas `.env`.
- No subas tokens ni claves API.
- Si el repositorio es publico, cualquier archivo generado y subido al repo sera publico.
- El estado `.state/` esta ignorado por Git.
- La rama `bot-state` guarda `aemet_cache.json` para reducir llamadas a AEMET. No contiene tokens; guarda prediccion/avisos normalizados y la ultima observacion seleccionada.

## Limitaciones

GitHub Actions no es tiempo real exacto. Las ejecuciones programadas pueden retrasarse, saltarse en momentos de alta carga o pausarse por reglas de GitHub. Para avisos criticos usa canales oficiales de AEMET y Proteccion Civil.

La API de AEMET funciona en dos pasos: primero devuelve metadatos con una URL `datos`, y despues el bot descarga el JSON real desde esa URL.

Los avisos oficiales pueden llegar como JSON, XML CAP o ZIP con XML CAP. El bot intenta normalizar esos formatos antes de aplicar las reglas.
