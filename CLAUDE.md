# Prompt para Claude Code — Sistema de monitoreo de sitios web (v2: panel web + servidor local)

Copiá todo lo que sigue y pegalo en Claude Code (VSCode):

---

Quiero que construyas un sistema de monitoreo de sitios web llamado **SiteWatch**, que corre en un **servidor local en mi casa** (Linux, detrás de NAT, sin IP pública). Monitoreo sitios propios y de clientes construidos en Laravel, WordPress y Next.js. Todas las alertas van a **Telegram** y la administración de sitios se hace desde un **panel web con ABM completo**.

## Stack y arquitectura

- **Backend:** Python 3.12, **FastAPI** (sirve tanto la API como el panel web), `SQLAlchemy` + **SQLite**, `APScheduler` para los checks, `aiohttp` como cliente HTTP de los checks.
- **Frontend del panel:** React con Vite, servido como build estático por FastAPI. Estética dark, acento verde ácido/chartreuse, tipografía monoespaciada para datos. Sin frameworks de UI pesados; Tailwind alcanza.
- **Deploy:** `docker-compose.yml` con un solo servicio + volumen para el SQLite. Incluir también systemd unit como alternativa sin Docker.
- Secretos en `.env` (bot token, chat ID, API keys, secret de sesión). Incluir `.env.example`.
- Estructura: `app/` (FastAPI: `api/`, `checks/`, `notifiers/`, `models/`, `scheduler.py`), `frontend/` (React), `agents/` (scripts para servidores remotos).
- Logging estructurado con rotación. Type hints en todo el código. Tests con `pytest` para la lógica de incidentes, matching de patrones y el ABM (API).

## Panel web (ABM de sitios)

- **Login** simple con usuario/contraseña (hash con bcrypt, sesión con cookie firmada). Un solo usuario configurado por `.env` o comando CLI de creación. Rate-limit en el login.
- **CRUD de sitios** con estos campos: nombre, URL, tipo (wordpress / laravel / nextjs), intervalo de check (segundos), keyword esperado en el HTML, activo/pausado, token del mu-plugin (solo WP), health endpoint (opcional), notas.
- Al crear/editar/pausar un sitio, el scheduler debe **recargar en caliente** sin reiniciar el servicio.
- **Dashboard principal:** grilla de sitios con estado actual (🟢/🔴/⏸️), uptime % 24h y 7 días, latencia promedio, sparkline de latencia, próximos vencimientos SSL/dominio, badge de plugins vulnerables.
- **Detalle de sitio:** histórico de incidentes, gráfico de latencia (7/30 días), inventario de plugins/themes/core con versiones y CVEs (WP), resultado del último audit de dependencias (Laravel/Next.js), botón "chequear ahora", botón "silenciar N horas".
- **Vista de incidentes:** lista global filtrable, con duración y causa.
- **Configuración global desde el panel:** chat ID de Telegram, horario del digest, patrones sospechosos (editable como lista), umbrales de alerta SSL/dominio. Todo persiste en SQLite — nada de YAML.

## Checks a implementar

### 1. Uptime (todos los sitios)
- GET a la URL según el intervalo configurado. Caído si: status >= 400, timeout (10s), error de conexión/DNS.
- Anti-falsos positivos: reintentar 3 veces con backoff (5s, 15s, 30s) antes de declarar incidente.
- Registrar latencia de cada check. Al recuperarse, cerrar incidente y notificar con duración del downtime.

### 2. Integridad de contenido (todos los sitios)
- Verificar presencia del keyword esperado en el HTML.
- Escanear contra patrones sospechosos configurables desde el panel: `eval(atob(`, `String.fromCharCode` en scripts inline, iframes hacia dominios desconocidos, meta-refresh externos, patrones de ClickFix/ClearFake (falsos prompts de verificación en el DOM).
- Redirects inesperados: si la cadena termina en un dominio distinto al configurado → alerta crítica de posible compromiso.

### 3. SSL y dominio (todos los sitios)
- Diario: expiración de certificado SSL (alertar a 14/7/3 días, o si es inválido/mismatch) y expiración de dominio vía WHOIS (`python-whois`, alertar a 30/14/7 días).

### 4. WordPress: plugins, core y vulnerabilidades
- Crear un **mu-plugin de WordPress** (PHP, un archivo, para `wp-content/mu-plugins/`) que exponga `GET /wp-json/sitewatch/v1/report` protegido por header `X-SiteWatch-Token`. Devuelve JSON: versión de core y update disponible, plugins (slug, versión instalada, versión disponible, activo), themes, versión de PHP, y usernames de administradores (para detectar admins creados por atacantes).
- SiteWatch consulta ese endpoint 1 vez por día (esto funciona perfecto desde el server local porque es **pull saliente**, no requiere IP pública).
- Cruzar cada componente desactualizado contra la **API de WPScan** (key en `.env`):
  - ⚠️ Desactualizado sin CVE → digest diario.
  - 🔴 Desactualizado CON CVE conocido → alerta inmediata con el CVE y la versión que parchea.
- Alertar si aparece un admin nuevo respecto al último snapshot.

### 5. Laravel y Next.js: dependencias y health
- Health endpoint opcional por sitio: esperar `{"status": "ok"}`. Documentar en el README un ejemplo para Laravel (verifica DB, cache y que `schedule:run` corrió en los últimos 5 min vía timestamp en cache) y para Next.js (API route).
- **Audit de dependencias en modo PULL (importante: el server local no tiene IP pública, no puede recibir POSTs de internet):** SiteWatch se conecta por **SSH saliente** (clave configurada por sitio desde el panel: host, usuario, path del proyecto) y ejecuta `composer audit --format=json` o `npm audit --json` según el tipo, 1 vez al día. Usar `asyncssh`. High/critical → alerta inmediata; el resto → digest.
- Alternativa documentada en el README para quien no quiera dar SSH: script cron en el servidor remoto que escribe el JSON del audit en una ruta web protegida por token, y SiteWatch lo fetchea.

### 6. Blacklists (diario)
- Google Safe Browsing API: alerta inmediata si un sitio figura flaggeado. VirusTotal opcional si hay key.

### 7. Auto-monitoreo (dead man's switch) — crítico por correr en server local
- Como SiteWatch corre en mi casa, si se corta la luz o internet nadie me avisa. Implementar un **heartbeat saliente**: ping HTTP cada 5 minutos a una URL configurable de **Healthchecks.io** (o compatible). Si SiteWatch muere, Healthchecks me alerta por Telegram por su lado. Documentar el setup en el README.
- Al arrancar después de un downtime propio, SiteWatch debe notificar a Telegram cuánto tiempo estuvo apagado y correr un check inmediato de todos los sitios.

## Notificaciones a Telegram

- `python-telegram-bot`. Alertas con emoji de severidad, nombre del sitio, qué pasó, timestamp en hora de Buenos Aires (America/Argentina/Buenos_Aires).
- **Inmediatas:** 🔴 caída/recuperación, 🔴 posible compromiso (contenido sospechoso, redirect externo, admin nuevo, blacklist), 🔴 CVE en plugin/dependencia, 🟠 SSL/dominio por vencer.
- **Digest diario 09:00:** estado de todos los sitios, uptime 24h, latencias, desactualizados sin CVE, próximos vencimientos.
- **Comandos:** `/status`, `/site <nombre>`, `/silence <nombre> <horas>`, `/incidents`. El bot responde solo a mi chat ID.
- Incluir en las alertas un link al detalle del sitio en el panel (URL base del panel configurable, ej. `http://192.168.1.x:8000` o el hostname de Tailscale).

## Acceso remoto al panel (documentar en README, no implementar)

Explicar en el README dos opciones para acceder al panel desde afuera de casa: **Tailscale** (recomendada, cero exposición) o **Cloudflare Tunnel**. No abrir puertos en el router.

## Criterios de calidad

- Un sitio que falla no debe frenar el loop de los demás.
- User-Agent identificable: `SiteWatch/1.0`.
- Migraciones de DB con Alembic.
- El panel debe funcionar bien en mobile (para mirar desde el teléfono cuando llega una alerta).

Empezá por los modelos de datos y el ABM (API + panel), después el scheduler con recarga en caliente, después los checks en orden, y al final el mu-plugin de WordPress y la documentación de agents/acceso remoto.

---

## Notas para vos (fuera del prompt)

- **API keys:** bot de Telegram (@BotFather), WPScan (free: 25 req/día), Google Safe Browsing (gratis en GCP), cuenta free de Healthchecks.io para el dead man's switch.
- **Por qué pull y no push:** tu server local no tiene IP pública, así que todo lo diseñé saliente (checks HTTP, SSH hacia los servidores, heartbeat hacia Healthchecks). No necesitás abrir ni un puerto.
- **Tailscale** te resuelve en 10 minutos el acceso al panel desde el teléfono estando afuera, y de paso te sirve para el Mac mini.
- Ojo con una limitación real del server hogareño: si tu ISP corta, durante ese rato no monitoreás nada — el dead man's switch te avisa que el monitor está ciego, pero no reemplaza el monitoreo. Si algún cliente es crítico, podés correr una segunda instancia mínima (solo uptime) en un VPS de USD 3-5 como respaldo.