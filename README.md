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

### systemd (no Docker, Linux)

See [`deploy/sitewatch.service`](deploy/sitewatch.service). Copy it to
`/etc/systemd/system/`, adjust the paths, then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now sitewatch
```

### Windows 10/11 (client)

The `deploy/sitewatch.service` systemd unit doesn't apply on Windows — use
Docker instead, which needs no code or config changes since the container
itself still runs Linux:

1. Install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
   (it sets up the WSL2 backend automatically on Windows 10/11).
2. Copy this project folder onto the Windows machine (git clone, network
   share, USB, whatever's convenient), and copy your working `.env` over too
   if you already have one configured elsewhere.
3. In **Docker Desktop → Settings → General**, enable "Start Docker Desktop
   when you log in" so it survives a reboot the same way the systemd unit
   would on Linux.
4. Open PowerShell in the project folder and run the same commands as the
   [Docker section above](#docker):
   ```powershell
   copy .env.example .env   # or use your existing .env
   docker compose up -d --build
   ```
5. Find the Windows machine's LAN IP with `ipconfig` (look for "IPv4
   Address" under your active adapter) and browse to
   `http://<that-ip>:8000` from any device on the network. Set
   `PANEL_BASE_URL` in `.env` (and Settings → panel base URL in the panel)
   to that same address so Telegram alert links resolve correctly.
6. For access from outside the network, the same [Tailscale](#remote-access-to-the-panel)
   setup applies — install the Tailscale Windows client on the server the
   same way.

### Windows Server (2016/2019/2022)

**Docker Desktop does not work here** — it's a client-OS product, not
licensed or built for Server editions, and on 2016/2019 there's no WSL2 to
fall back to either (WSL2 support on Server starts at 2022, and even there
it's less battle-tested than the client path above). Symptom if you try it
anyway: Docker Desktop simply won't start.

The reliable path: run a small Linux VM under **Hyper-V** (already a role on
Windows Server) and deploy exactly the way this project was actually built
and tested — a real Linux host with Docker on it. No code changes.

1. Download an **Ubuntu Server 24.04 LTS** ISO.
2. In Hyper-V Manager, confirm you have an **External** virtual switch
   (Virtual Switch Manager → New → External, bound to the physical NIC) so
   the VM lands on your real LAN with its own IP, not an isolated one.
3. New VM → **Generation 2**, 2GB+ RAM (4GB+ better), 20GB+ disk, attach the
   ISO, connect to that External switch. In VM Settings → Security, keep
   Secure Boot on but switch the template to **"Microsoft UEFI Certificate
   Authority"** — the default Windows template won't boot the Ubuntu
   installer.
4. Install Ubuntu Server, enabling OpenSSH server when offered so you can
   manage it remotely afterward instead of through the VM console.
5. SSH in and install Docker:
   ```bash
   curl -fsSL https://get.docker.com | sh
   sudo usermod -aG docker $USER   # log out/in after this
   ```
6. Copy the project onto the VM (`scp`/`rsync` from wherever you're
   developing, or `git clone` if it's pushed somewhere) and run it:
   ```bash
   cd website-checker
   cp .env.example .env   # or copy over your existing working .env
   docker compose up -d --build
   ```
7. Browse to `http://<vm-ip>:8000` from any device on the LAN (`ip addr`
   inside the VM to find it). Set `PANEL_BASE_URL` to that address the same
   way as the other deploy paths.
8. For reboot survival: set the VM's **Automatic Start Action** (VM Settings)
   to "Always start this virtual machine automatically" so it comes back
   after the Windows Server host reboots — `docker-compose.yml`'s
   `restart: unless-stopped` already handles the container itself once
   Docker starts inside the VM.

No native (non-Docker, non-VM) Windows path is documented for either
edition — running Python/uvicorn directly on Windows as a background
service is possible (e.g. via [NSSM](https://nssm.cc/) or Task Scheduler)
but untested against this project.

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
