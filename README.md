# weather-telegram-bot

Bot meteorologico en Python que consulta AEMET OpenData y envia notificaciones por Telegram cuando detecta lluvia probable, viento fuerte, calor, frio/heladas o avisos oficiales de AEMET. Tambien puede enviar un resumen diario.

El proyecto esta preparado para ejecutarse en local con `.env`, como endpoint HTTP para cron-job.org y, si quieres mantenerlo, tambien con GitHub Actions.

## Que hace

- Consulta la prediccion diaria por municipio de AEMET OpenData.
- Intenta consultar avisos oficiales AEMET.
- Aplica reglas configurables por variables de entorno.
- Envia mensajes con Telegram Bot API.
- Evita repetir alertas usando `.state/notified_alerts.json`.
- Expone endpoints HTTP protegidos para cron-job.org.
- Mantiene workflows de GitHub Actions como opcion secundaria.

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
RAIN_PROB_THRESHOLD=70
WIND_KMH_THRESHOLD=45
HEAT_TEMP_THRESHOLD=35
COLD_TEMP_THRESHOLD=0
CRON_SECRET=un_token_largo_y_privado
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

Alertas:

```bash
python -m src.main alerts
```

Resumen diario:

```bash
python -m src.main daily
```

Servidor HTTP para cron-job.org:

```bash
python -m src.web_app
```

Endpoints:

```text
GET /cron/alerts?token=CRON_SECRET
GET /cron/daily?token=CRON_SECRET
```

Tambien puedes enviar el token en el header `X-Cron-Secret`.

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
- `AEMET_ALERT_AREA` opcional, por defecto `esp`. Para Comunidad de Madrid usa `72`.

Hay tres workflows:

- `Weather alerts`: ejecucion manual con `workflow_dispatch`.
- `Weather daily summary`: ejecucion manual con `workflow_dispatch`.
- `CI`: ejecuta los tests con `pytest` en cada push, pull request o manualmente.

Las notificaciones programadas quedan delegadas a cron-job.org. Los workflows meteorologicos de GitHub Actions se mantienen solo para pruebas manuales.

## cron-job.org

cron-job.org no ejecuta tu codigo directamente: llama una URL publica. Por eso necesitas desplegar este proyecto en algun sitio que exponga HTTP, por ejemplo Render, Railway, Fly.io, PythonAnywhere o un VPS.

Variables necesarias en el hosting:

- `AEMET_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `MUNICIPIO_ID`
- `MUNICIPIO_NOMBRE`
- `TIMEZONE`
- `RAIN_PROB_THRESHOLD`
- `WIND_KMH_THRESHOLD`
- `HEAT_TEMP_THRESHOLD`
- `COLD_TEMP_THRESHOLD`
- `AEMET_ALERT_AREA`
- `CRON_SECRET`

Comando de arranque:

```bash
python -m src.web_app
```

Si el proveedor usa `gunicorn`, puedes usar:

```bash
gunicorn src.web_app:app
```

El repositorio incluye `Procfile` con:

```text
web: gunicorn src.web_app:app
```

Configura en cron-job.org estos jobs:

- Alertas: `https://TU_DOMINIO/cron/alerts?token=TU_CRON_SECRET`, cada 30 minutos.
- Resumen 09:00: `https://TU_DOMINIO/cron/daily?token=TU_CRON_SECRET`, todos los dias a las 09:00.
- Resumen 19:00: `https://TU_DOMINIO/cron/daily?token=TU_CRON_SECRET`, todos los dias a las 19:00.

Usa la zona horaria `Europe/Madrid` en cron-job.org para que los horarios coincidan con Espana.

No compartas `CRON_SECRET`. Si alguien conoce esa URL completa puede disparar el bot.

## Cambiar frecuencia y umbrales

La frecuencia se cambia editando los `cron` en:

- `.github/workflows/weather-alerts.yml`
- `.github/workflows/weather-daily.yml`

Los umbrales se cambian con variables del repositorio o en `.env` para local:

- `RAIN_PROB_THRESHOLD`: probabilidad de lluvia minima.
- `WIND_KMH_THRESHOLD`: viento minimo en km/h.
- `HEAT_TEMP_THRESHOLD`: temperatura maxima para alerta de calor.
- `COLD_TEMP_THRESHOLD`: temperatura minima para frio/helada.

## Privacidad y seguridad

- No subas `.env`.
- No subas tokens ni claves API.
- Si el repositorio es publico, cualquier archivo generado y subido al repo sera publico.
- El estado `.state/` esta ignorado por Git y se conserva en Actions mediante cache.

## Limitaciones

GitHub Actions no es tiempo real exacto. Las ejecuciones programadas pueden retrasarse, saltarse en momentos de alta carga o pausarse por reglas de GitHub. Para avisos criticos usa canales oficiales de AEMET y Proteccion Civil.

La API de AEMET funciona en dos pasos: primero devuelve metadatos con una URL `datos`, y despues el bot descarga el JSON real desde esa URL.

Los avisos oficiales pueden llegar como JSON, XML CAP o ZIP con XML CAP. El bot intenta normalizar esos formatos antes de aplicar las reglas.
