# SiteWatch

A self-hosted monitoring system for a home server behind NAT: uptime,
content-integrity/compromise detection, SSL & domain expiry, WordPress
plugin/core CVEs, Laravel/Next.js dependency audits, and blacklist checks —
all alerting to Telegram, all administered from a web panel. Everything
SiteWatch does is an *outbound* connection (HTTP checks, SSH, WHOIS,
Telegram, Healthchecks.io), so it needs no public IP and no open router
ports.

## Stack

- **Backend:** FastAPI + SQLAlchemy + SQLite + APScheduler + aiohttp
- **Frontend:** React + Vite + Tailwind, built as a static bundle served by FastAPI
- **Alerts:** Telegram bot (alerts + daily digest + `/status`, `/site`, `/silence`, `/incidents` commands)

## Quick start (no Docker)

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env        # then edit .env — see "Configuration" below

cd frontend && npm install && npm run build && cd ..   # builds into app/static

.venv/bin/alembic upgrade head
.venv/bin/python -m app.cli create-user --username admin   # prompts for a password

.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Visit `http://<server-ip>:8000`, log in, and add your first site.

For local frontend development with hot reload, run the backend as above
and separately `cd frontend && npm run dev` — Vite proxies `/api` to
`localhost:8000`.

## Configuration

All secrets and bootstrap config live in `.env` (see `.env.example`).
Operational settings that you'll want to tweak from the panel — Telegram
chat ID, digest hour, SSL/domain alert thresholds, suspicious content
patterns, API keys — live in the database instead and are editable from
**Settings** in the panel; `.env` values seed them on first boot.

| Key | Where to get it |
|---|---|
| `TELEGRAM_BOT_TOKEN` | [@BotFather](https://t.me/BotFather) on Telegram |
| `TELEGRAM_CHAT_ID` | message your bot, then check `https://api.telegram.org/bot<token>/getUpdates` |
| `WPSCAN_API_KEY` | [wpscan.com](https://wpscan.com/api) — free tier: 25 requests/day |
| `GOOGLE_SAFE_BROWSING_API_KEY` | free in [Google Cloud Console](https://console.cloud.google.com/) (Safe Browsing API) |
| `VIRUSTOTAL_API_KEY` | optional, free at [virustotal.com](https://www.virustotal.com/) |
| `HEALTHCHECKS_URL` | free account at [healthchecks.io](https://healthchecks.io) — see below |

## Dead man's switch (Healthchecks.io)

SiteWatch runs on a home server: if the power or internet goes out, nothing
tells *you* that monitoring stopped. Healthchecks.io solves this from the
outside:

1. Create a free account at [healthchecks.io](https://healthchecks.io) and
   add a check with a period of **10 minutes** (SiteWatch pings every 5).
2. Connect its Telegram integration so *Healthchecks* — not SiteWatch —
   messages you if pings stop.
3. Paste the check's ping URL into `HEALTHCHECKS_URL` (or the panel's
   Settings page).

SiteWatch also detects its own downtime on startup (comparing the current
time against a last-alive marker) and sends a Telegram message with how long
it was down, followed by an immediate check of every site — so a reboot
tells you both "I was down for 47 minutes" and "here's the current status
of everything now."

**Real limitation:** while SiteWatch itself is down (power/ISP outage), it
monitors nothing — the dead man's switch tells you monitoring is blind, it
doesn't substitute for it. For a client site where that gap matters, run a
second minimal instance (uptime-only) on a $3–5/mo VPS as backup.

## WordPress, Laravel, Next.js agents

- [`agents/wp-mu-plugin/`](agents/wp-mu-plugin/) — drop-in mu-plugin exposing a
  token-protected report endpoint (core/plugin/theme versions, PHP version,
  admin usernames).
- [`agents/laravel/`](agents/laravel/) — health endpoint example (DB, cache,
  `schedule:run` freshness).
- [`agents/nextjs/`](agents/nextjs/) — health endpoint example.
- [`agents/remote-audit-cron/`](agents/remote-audit-cron/) — dependency-audit
  alternative for sites where you don't want to hand out SSH access.

## Remote access to the panel

Don't open a port on your router. Two options, from home:

**Tailscale (recommended).** Install it on the home server and your phone;
they join the same private mesh network and you reach the panel at the
server's Tailscale IP/hostname (e.g. `http://sitewatch.tailXXXX.ts.net:8000`)
from anywhere, with no exposure to the public internet. Setup is about 10
minutes: `curl -fsSL https://tailscale.com/install.sh | sh`, `tailscale up`,
install the Tailscale app on your phone, log into the same account. Set
`PANEL_BASE_URL` (and the panel's Settings → panel base URL) to the
Tailscale hostname so Telegram alert links work from your phone.

**Cloudflare Tunnel.** If you want the panel reachable at a normal HTTPS
domain without opening a port, `cloudflared tunnel` proxies through
Cloudflare's edge to a locally-running `cloudflared` daemon. More setup than
Tailscale, but doesn't require installing a client on every device you check
from.

Either way: never forward a port on the router directly to SiteWatch.

## Deploy

### Docker

```bash
cp .env.example .env   # edit it
docker compose up -d --build
```

Data (SQLite DB + logs) persists in `./data`, mounted as a volume. Migrations
run automatically on container start.

### systemd (no Docker)

See [`deploy/sitewatch.service`](deploy/sitewatch.service). Copy it to
`/etc/systemd/system/`, adjust the paths, then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now sitewatch
```

## Development

```bash
# backend
.venv/bin/pytest

# frontend
cd frontend && npm run build   # type-checks + builds
```

## Known limitations

- All plugin/theme/core CVE alerts for a given WordPress site share a single
  "open incident" slot (`wp_cve`). If two different plugins on the same site
  are simultaneously vulnerable, only the most recently checked one is
  reflected in the incident's visible cause/detail — both are still
  discoverable in the raw WP inventory snapshot on the site detail page, but
  a second Telegram alert won't fire until the first incident closes.
- Domain-expiry WHOIS lookups use a naive "last two labels" heuristic to
  derive the registrable domain from a hostname (e.g. `www.example.com` →
  `example.com`). This is wrong for multi-part public suffixes like
  `example.co.uk`; if you monitor sites on those TLDs, expect WHOIS lookups
  to target the wrong domain.
