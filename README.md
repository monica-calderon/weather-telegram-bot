# weather-telegram-bot

Bot meteorologico en Python que consulta AEMET OpenData y envia resúmenes diarios por Telegram con prediccion, temperatura actual y avisos relevantes del dia.

El proyecto esta preparado para ejecutarse en local con `.env` y en GitHub Actions. La programacion se delega a cron-job.org, que llama a la API de GitHub para lanzar los workflows.

## Que hace

- Consulta la prediccion diaria por municipio de AEMET OpenData.
- Consulta observacion convencional de AEMET para incluir temperatura actual, con fallback a prediccion AEMET y Open-Meteo como ultimo recurso.
- Incluye estado de cielo previsto en el resumen diario.
- Incluye los proximos eventos de Google Calendar si lo configuras.
- Intenta consultar avisos oficiales AEMET.
- Aplica reglas configurables por variables de entorno e incluye los avisos dentro del resumen diario.
- Reutiliza datos cacheados para reducir llamadas a AEMET y resistir limites temporales de la API.
- Envia mensajes con Telegram Bot API, Ntfy, o ambos.
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

Para ejecutar tests en local, instala las dependencias de desarrollo:

```bash
pip install -r requirements-dev.txt
```

3. Crea tu `.env` desde el ejemplo:

```bash
copy .env.example .env
```

4. Rellena las variables:

```env
AEMET_API_KEY=tu_api_key
NTFY_METHOD=auto
TELEGRAM_BOT_TOKEN=123456:ABCDEF
TELEGRAM_CHAT_ID=123456789
NTFY_TOPIC=mi-topic-privado
NTFY_SERVER=https://ntfy.sh
NTFY_TOKEN=
NTFY_USERNAME=
NTFY_PASSWORD=
NTFY_PRIORITY=
NTFY_TAGS=partly_sunny
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
OPEN_METEO_LATITUDE=40.4818
OPEN_METEO_LONGITUDE=-3.3643
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"..."}
GOOGLE_OAUTH_CLIENT_JSON={"installed":{"client_id":"...","client_secret":"..."}}
GOOGLE_OAUTH_REFRESH_TOKEN=tu_refresh_token
GOOGLE_CALENDAR_IDS=calendario1@gmail.com,abc123@group.calendar.google.com
GOOGLE_CALENDAR_NAMES=Personal,Bubu
CALENDAR_EVENTS_MAX=10
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

## Configurar notificaciones

`NTFY_METHOD` controla que canales se usan:

- `auto`: usa todos los canales que tengan configuracion completa. Es el valor por defecto.
- `telegram`: usa solo Telegram y requiere `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`.
- `ntfy`: usa solo Ntfy y requiere `NTFY_TOPIC`.
- `both`: envia por Telegram y Ntfy, y requiere ambas configuraciones.

Para Ntfy, configura como minimo `NTFY_TOPIC`. Por defecto se envia a `https://ntfy.sh/<topic>`, pero puedes cambiar el servidor con `NTFY_SERVER` o poner una URL completa directamente en `NTFY_TOPIC`. Si tu servidor requiere autenticacion, usa `NTFY_TOKEN` para bearer token o `NTFY_USERNAME` y `NTFY_PASSWORD` para basic auth. `NTFY_PRIORITY` y `NTFY_TAGS` son opcionales.

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

En el resumen diario, `Actual` usa la ultima observacion disponible de AEMET; si no existe, muestra la temperatura prevista para la hora del resumen con el sufijo `prev.`; y, como ultimo recurso, consulta Open-Meteo por coordenadas. Nunca se muestra `Actual: No disponible` ni `Actual: 0°C`; si no hay dato util, se omite la linea. `Lluvia máx.` y `Viento máx.` no son valores actuales ni medias: son el valor maximo previsto por AEMET para algun tramo del dia. Si las reglas detectan lluvia, viento, calor, frio/helada o avisos oficiales, el resumen añade la seccion `Avisos del día` con el detalle y, cuando AEMET lo publica, el tramo horario afectado.

Para reducir errores `429 Too Many Requests`, el workflow guarda una cache persistente y minima en la rama `bot-state`:

- Prediccion municipal: se consulta como maximo una vez al dia y se guarda ya normalizada, incluyendo temperaturas por hora para calcular `Actual` si falta observacion real.
- Avisos oficiales: se consultan como maximo una vez al dia y se guardan ya normalizados.
- Observacion actual: se consulta en cada resumen; solo se usa cache si AEMET limita la API. La hora de la observacion se convierte a `TIMEZONE` y no se muestra como actual si supera `CURRENT_OBSERVATION_MAX_AGE_MINUTES`.
- Open-Meteo: se consulta solo como ultimo recurso para temperatura actual estimada.

Si un resumen usa cache por limite temporal de AEMET, el mensaje incluye la nota `datos cacheados por límite temporal de AEMET`.
Si la temperatura actual viene de Open-Meteo, el mensaje incluye la nota `temperatura actual estimada con Open-Meteo`.

Si configuras Google Calendar, el resumen añade `Proximos eventos` con los eventos restantes del dia, desde la hora del resumen hasta las 23:59 en `TIMEZONE`.

Tests:

```bash
pytest
```

El proyecto incluye `pytest.ini` para que `src` se pueda importar al ejecutar `pytest` directamente desde la raiz del repositorio.

## GitHub Actions

Configura estos `Secrets` en tu repositorio:

- `AEMET_API_KEY`
- `TELEGRAM_BOT_TOKEN` si usas Telegram.
- `TELEGRAM_CHAT_ID` si usas Telegram.
- `NTFY_TOPIC` si usas Ntfy; tambien puedes guardarlo como Variable.
- `NTFY_TOKEN` opcional si tu servidor Ntfy requiere bearer token.
- `NTFY_USERNAME` y `NTFY_PASSWORD` opcionales si tu servidor Ntfy requiere basic auth.
- `GOOGLE_SERVICE_ACCOUNT_JSON` opcional, JSON completo de la service account de Google.
- `GOOGLE_OAUTH_CLIENT_JSON` opcional, JSON del cliente OAuth si necesitas leer calendarios privados compartidos con tu cuenta.
- `GOOGLE_OAUTH_REFRESH_TOKEN` opcional, refresh token OAuth de tu cuenta de Google.
- `GOOGLE_CALENDAR_IDS` opcional si prefieres guardar tambien los IDs como secreto.
- `GOOGLE_CALENDAR_NAMES` opcional si prefieres guardar tambien los nombres visibles como secreto.
- `CALENDAR_EVENTS_MAX` opcional si prefieres guardarlo como secreto.

`GOOGLE_CALENDAR_IDS` y `GOOGLE_CALENDAR_NAMES` pueden estar en `Secrets` o en `Variables`; el workflow acepta ambas opciones.

Configura estas `Variables` del repositorio:

- `MUNICIPIO_ID`
- `MUNICIPIO_NOMBRE`
- `NTFY_METHOD` opcional, por defecto `auto`. Valores: `auto`, `telegram`, `ntfy`, `both`.
- `NTFY_SERVER` opcional, por defecto `https://ntfy.sh`.
- `NTFY_PRIORITY` opcional.
- `NTFY_TAGS` opcional, etiquetas Ntfy separadas por coma.
- `TIMEZONE`
- `RAIN_PROB_THRESHOLD`
- `WIND_KMH_THRESHOLD`
- `HEAT_TEMP_THRESHOLD`
- `COLD_TEMP_THRESHOLD`
- `AEMET_ALERT_AREA` opcional, por defecto `72` para Comunidad de Madrid.
- `AEMET_STATION_ID` opcional. Si lo configuras, se usa esa estacion AEMET para la temperatura actual. Para Alcala de Henares se recomienda `3170Y`; si `MUNICIPIO_ID=28005` y lo dejas vacio, el bot usa ese valor por defecto. Para otros municipios, si lo dejas vacio, el bot intenta encontrar una observacion cuyo nombre coincida con `MUNICIPIO_NOMBRE`.
- `CURRENT_OBSERVATION_MAX_AGE_MINUTES` opcional, por defecto `150`. Evita mostrar como actual una observacion de AEMET demasiado antigua.
- `OPEN_METEO_LATITUDE` y `OPEN_METEO_LONGITUDE` opcionales. Para Alcala de Henares se usan por defecto `40.4818` y `-3.3643`.
- `GOOGLE_CALENDAR_IDS` opcional, IDs de calendarios separados por coma.
- `GOOGLE_CALENDAR_NAMES` opcional, nombres visibles separados por coma y en el mismo orden que `GOOGLE_CALENDAR_IDS`. Ejemplo: `Personal,Bubu`.
- `CALENDAR_EVENTS_MAX` opcional, por defecto `10`.

Hay dos workflows:

- `Weather daily summary`: ejecucion manual o por API con `workflow_dispatch`.
- `CI`: ejecuta los tests con `pytest` en cada push, pull request o manualmente.

Las notificaciones programadas quedan delegadas a cron-job.org. GitHub Actions ejecuta el codigo cuando cron-job.org llama a la API de GitHub.

## Google Calendar

La integracion acepta dos modos:

- Service account: recomendado si puedes compartir cada calendario con el email de la service account.
- OAuth de usuario: recomendado si el calendario es privado, te lo han compartido a tu cuenta de Google y no puedes compartirlo con la service account.

Si configuras ambos, el bot usa OAuth de usuario porque permite ver los calendarios a los que tiene acceso tu cuenta.

### Opcion A. Service account

La service account es la opcion mas estable para GitHub Actions porque no requiere iniciar sesion manualmente ni renovar tokens OAuth.

#### 1. Crear credenciales en Google Cloud

1. Entra en [Google Cloud Console](https://console.cloud.google.com/).
2. Crea o selecciona un proyecto.
3. Ve a `APIs y servicios` -> `Biblioteca`.
4. Busca `Google Calendar API` y pulsa `Habilitar`.
5. Ve a `APIs y servicios` -> `Credenciales`.
6. Pulsa `Crear credenciales` -> `Cuenta de servicio`.
7. Ponle un nombre, por ejemplo `weather-telegram-bot`.
8. Abre la cuenta de servicio creada.
9. Entra en `Claves` -> `Agregar clave` -> `Crear clave nueva`.
10. Elige `JSON` y descarga el archivo.

Ese archivo JSON completo sera el valor de `GOOGLE_SERVICE_ACCOUNT_JSON`. No lo subas al repositorio.

#### 2. Compartir calendarios con la service account

1. Abre el JSON descargado.
2. Copia el valor de `client_email`; tendra forma parecida a:

```text
weather-telegram-bot@tu-proyecto.iam.gserviceaccount.com
```

3. Abre [Google Calendar](https://calendar.google.com/).
4. En la barra izquierda, pasa el raton sobre el calendario que quieras leer.
5. Pulsa `...` -> `Configuracion y uso compartido`.
6. En `Compartir con personas o grupos especificos`, añade el `client_email`.
7. Dale permiso `Ver todos los detalles del evento`.
8. Repite el proceso para cada calendario que quieras incluir.

#### 3. Obtener IDs de calendario

Para cada calendario:

1. Google Calendar -> `Configuracion y uso compartido`.
2. Baja hasta `Integrar calendario`.
3. Copia `ID del calendario`.

Puede ser un email, por ejemplo:

```text
tu-correo@gmail.com
```

O un ID largo, por ejemplo:

```text
abc123@group.calendar.google.com
```

Si quieres varios calendarios, ponlos separados por coma en `GOOGLE_CALENDAR_IDS`.
Si Google no devuelve el nombre del calendario y ves un ID largo en Telegram, configura tambien `GOOGLE_CALENDAR_NAMES` con nombres bonitos en el mismo orden. Por ejemplo:

```text
GOOGLE_CALENDAR_IDS=tu-correo@gmail.com,abc123@group.calendar.google.com
GOOGLE_CALENDAR_NAMES=Personal,Bubu
```

#### 4. Guardar en GitHub

En tu repositorio de GitHub:

1. Ve a `Settings` -> `Secrets and variables` -> `Actions`.
2. En `Secrets`, crea:

```text
GOOGLE_SERVICE_ACCOUNT_JSON
```

Pega como valor el contenido completo del JSON descargado.

3. En `Variables`, crea:

```text
GOOGLE_CALENDAR_IDS
GOOGLE_CALENDAR_NAMES
```

Ejemplo:

```text
tu-correo@gmail.com,abc123@group.calendar.google.com
Personal,Bubu
```

4. Opcionalmente, crea:

```text
CALENDAR_EVENTS_MAX=10
```

Tambien puedes guardar `GOOGLE_CALENDAR_IDS`, `GOOGLE_CALENDAR_NAMES` y `CALENDAR_EVENTS_MAX` como `Secrets`; el workflow acepta ambas opciones. Si existen como Variable y como Secret, se usa primero la Variable.

#### 5. Configurar en local

En `.env`, puedes usar las mismas variables:

```env
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"..."}
GOOGLE_CALENDAR_IDS=tu-correo@gmail.com,abc123@group.calendar.google.com
GOOGLE_CALENDAR_NAMES=Personal,Bubu
CALENDAR_EVENTS_MAX=10
```

Si el JSON te da problemas en `.env` por comillas o saltos de linea, prueba primero desde GitHub Actions, donde el secret acepta el JSON completo mejor. En local tambien puedes pegarlo en una sola linea.

Si Google Calendar falla, el bot envia igualmente el resumen meteorologico y añade una nota indicando que no se pudieron obtener eventos.

### Opcion B. OAuth para un calendario privado compartido contigo

Usa esta opcion cuando el calendario no es publico y aparece en tu Google Calendar porque otra persona te lo ha compartido, pero no puedes anadir la service account como invitada del calendario.

#### 1. Crear cliente OAuth para OAuth Playground

1. Entra en [Google Cloud Console](https://console.cloud.google.com/).
2. Usa el mismo proyecto donde habilitaste `Google Calendar API`, o crea uno.
3. Ve a `APIs y servicios` -> `Pantalla de consentimiento de OAuth`.
4. Configura la pantalla en modo `Externo` o `Interno`, segun tu cuenta. Para uso personal puede quedar en pruebas.
5. Anade tu email como usuario de prueba si la app esta en pruebas.
6. Ve a `APIs y servicios` -> `Credenciales`.
7. Pulsa `Crear credenciales` -> `ID de cliente de OAuth`.
8. Tipo de aplicacion: `Aplicacion web`.
9. En `URIs de redireccion autorizados`, anade:

```text
https://developers.google.com/oauthplayground
```

10. Descarga el JSON. Ese contenido sera `GOOGLE_OAUTH_CLIENT_JSON`.

No uses un cliente `Aplicacion de escritorio` con OAuth Playground; Playground necesita que el redirect URI anterior este autorizado en un cliente web.

#### 2. Obtener refresh token

1. Abre [OAuth 2.0 Playground](https://developers.google.com/oauthplayground/).
2. Pulsa el icono de ajustes.
3. Marca `Use your own OAuth credentials`.
4. Pega el `client_id` y `client_secret` del JSON OAuth web.
5. En scopes, usa:

```text
https://www.googleapis.com/auth/calendar.readonly
```

6. Pulsa `Authorize APIs`.
7. Entra con la cuenta de Google que ve el calendario privado compartido.
8. Pulsa `Exchange authorization code for tokens`.
9. Copia el `refresh_token`.

Necesitas guardar estos dos valores:

```text
GOOGLE_OAUTH_CLIENT_JSON
GOOGLE_OAUTH_REFRESH_TOKEN
```

Si Google devuelve `unauthorized_client`, normalmente el `refresh_token` se genero con otro `client_id/client_secret`, el cliente OAuth se cambio o borro, o el email no esta anadido como usuario de prueba en la pantalla de consentimiento.

Los archivos locales `client_secret*.json`, `get_refresh_token.py`, `refresh_token_weekly.bat`, `refresh_token_weekly.ps1` y `refresh_tokens.txt` estan ignorados por Git para evitar subir credenciales o helpers locales.

#### 3. Guardar en GitHub

En `Settings` -> `Secrets and variables` -> `Actions`, crea estos `Secrets`:

```text
GOOGLE_OAUTH_CLIENT_JSON
GOOGLE_OAUTH_REFRESH_TOKEN
```

Despues configura `GOOGLE_CALENDAR_IDS`, `GOOGLE_CALENDAR_NAMES` y `CALENDAR_EVENTS_MAX` igual que en la opcion A.

Para un calendario privado compartido contigo, puedes borrar `GOOGLE_SERVICE_ACCOUNT_JSON` si no lo usas. La service account no podra leer ese calendario salvo que el propietario tambien lo comparta con el `client_email` de la service account.

#### 4. Configurar en local

En `.env`:

```env
GOOGLE_OAUTH_CLIENT_JSON={"installed":{"client_id":"...","client_secret":"...","token_uri":"https://oauth2.googleapis.com/token"}}
GOOGLE_OAUTH_REFRESH_TOKEN=tu_refresh_token
GOOGLE_CALENDAR_IDS=abc123@group.calendar.google.com
GOOGLE_CALENDAR_NAMES=Compartido
CALENDAR_EVENTS_MAX=10
```

No subas ni el JSON OAuth ni el refresh token al repositorio.

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
- `OPEN_METEO_LATITUDE` y `OPEN_METEO_LONGITUDE`: coordenadas para Open-Meteo como ultimo recurso.
- `GOOGLE_CALENDAR_IDS`: calendarios de Google separados por coma para mostrar `Proximos eventos`.
- `GOOGLE_CALENDAR_NAMES`: nombres visibles de calendarios separados por coma, en el mismo orden que `GOOGLE_CALENDAR_IDS`.
- `CALENDAR_EVENTS_MAX`: maximo de eventos a mostrar, por defecto `10`.

## Privacidad y seguridad

- No subas `.env`.
- No subas tokens ni claves API.
- No subas el JSON de la service account de Google.
- Si el repositorio es publico, cualquier archivo generado y subido al repo sera publico.
- El estado `.state/` esta ignorado por Git.
- La rama `bot-state` guarda `aemet_cache.json` para reducir llamadas a AEMET. No contiene tokens; guarda prediccion/avisos normalizados y la ultima observacion seleccionada.

## Limitaciones

GitHub Actions no es tiempo real exacto. Las ejecuciones programadas pueden retrasarse, saltarse en momentos de alta carga o pausarse por reglas de GitHub. Para avisos criticos usa canales oficiales de AEMET y Proteccion Civil.

La API de AEMET funciona en dos pasos: primero devuelve metadatos con una URL `datos`, y despues el bot descarga el JSON real desde esa URL.

Los avisos oficiales pueden llegar como JSON, XML CAP o ZIP con XML CAP. El bot intenta normalizar esos formatos antes de aplicar las reglas.
