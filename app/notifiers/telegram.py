import logging
from datetime import datetime, timedelta, timezone
from html import escape as _esc

from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes

from app.config import settings
from app.database import SessionLocal
from app.models.config import GlobalConfig
from app.models.incident import Incident, Severity
from app.models.site import Site
from app.notifiers.formatting import SEVERITY_EMOJI, format_duration, format_timestamp, site_link

logger = logging.getLogger(__name__)

_bot: Bot | None = None
_application: Application | None = None


def _get_bot() -> Bot | None:
    global _bot
    if not settings.telegram_bot_token:
        return None
    if _bot is None:
        _bot = Bot(token=settings.telegram_bot_token)
    return _bot


def _panel_base_url(db) -> str:
    config = db.get(GlobalConfig, 1)
    return (config.panel_base_url if config and config.panel_base_url else settings.panel_base_url)


def _chat_id(db) -> str | None:
    config = db.get(GlobalConfig, 1)
    if config and config.telegram_chat_id:
        return config.telegram_chat_id
    return settings.telegram_chat_id or None


async def send_message(text: str, chat_id: str | None = None) -> None:
    bot = _get_bot()
    db = SessionLocal()
    try:
        target = chat_id or _chat_id(db)
    finally:
        db.close()

    if bot is None or not target:
        logger.info("Telegram not configured; message suppressed: %s", text.replace("\n", " | "))
        return

    await bot.send_message(chat_id=target, text=text, parse_mode="HTML", disable_web_page_preview=True)


async def send_incident_open(incident: Incident, site: Site) -> None:
    db = SessionLocal()
    try:
        link = site_link(_panel_base_url(db), site.id)
    finally:
        db.close()
    emoji = SEVERITY_EMOJI.get(incident.severity.value, "\U0001F534")
    text = (
        f"{emoji} <b>{_esc(site.name)}</b>\n"
        f"{_esc(incident.cause)}\n"
        f"Check: {incident.check_type.value} | {format_timestamp(incident.opened_at)}\n"
        f"{link}"
    )
    await send_message(text)


async def send_incident_close(incident: Incident, site: Site) -> None:
    db = SessionLocal()
    try:
        link = site_link(_panel_base_url(db), site.id)
    finally:
        db.close()
    duration = ""
    if incident.opened_at and incident.closed_at:
        duration = f" (down {format_duration(incident.closed_at - incident.opened_at)})"
    text = (
        f"\U0001F7E2 <b>{_esc(site.name)}</b> recovered{duration}\n"
        f"Check: {incident.check_type.value} | {format_timestamp(incident.closed_at)}\n"
        f"{link}"
    )
    await send_message(text)


async def send_startup_downtime_notice(downtime_seconds: float) -> None:
    from datetime import timedelta

    text = (
        f"⚠️ SiteWatch was down for {format_duration(timedelta(seconds=downtime_seconds))}. "
        "Running an immediate check of all sites now."
    )
    await send_message(text)


async def send_digest() -> None:
    from sqlalchemy import func

    from app.models.check_result import CheckResult
    from app.models.incident import Incident as IncidentModel
    from app.models.ssl_domain_status import SslDomainStatus
    from app.models.wp_snapshot import WpSnapshot

    db = SessionLocal()
    try:
        sites = db.query(Site).filter(Site.active.is_(True)).all()
        if not sites:
            return

        lines = ["\U0001F4CA <b>SiteWatch daily digest</b>"]
        now = datetime.now(timezone.utc)
        since_24h = now - timedelta(hours=24)

        for site in sites:
            results = (
                db.query(CheckResult)
                .filter(CheckResult.site_id == site.id, CheckResult.timestamp >= since_24h)
                .filter(CheckResult.check_type == "uptime")
                .all()
            )
            if results:
                uptime_pct = 100.0 * sum(1 for r in results if r.success) / len(results)
                latencies = [r.latency_ms for r in results if r.latency_ms is not None]
                avg_latency = sum(latencies) / len(latencies) if latencies else None
                latency_str = f"{avg_latency:.0f}ms" if avg_latency is not None else "n/a"
                lines.append(f"- {_esc(site.name)}: {uptime_pct:.1f}% uptime 24h, {latency_str} avg")
            else:
                lines.append(f"- {_esc(site.name)}: no data")

            snapshot = (
                db.query(WpSnapshot)
                .filter(WpSnapshot.site_id == site.id)
                .order_by(WpSnapshot.timestamp.desc())
                .first()
            )
            if snapshot:
                outdated = [p for p in snapshot.plugins_json if p.get("available") and p.get("available") != p.get("installed")]
                if outdated:
                    lines.append(f"  outdated (no known CVE): {_esc(', '.join(p['slug'] for p in outdated))}")

            ssl_status = (
                db.query(SslDomainStatus)
                .filter(SslDomainStatus.site_id == site.id)
                .order_by(SslDomainStatus.timestamp.desc())
                .first()
            )
            if ssl_status and ssl_status.ssl_expires_at:
                lines.append(f"  SSL expires: {ssl_status.ssl_expires_at.date()}")
            if ssl_status and ssl_status.domain_expires_at:
                lines.append(f"  Domain expires: {ssl_status.domain_expires_at.date()}")

        await send_message("\n".join(lines))
    finally:
        db.close()


# --- Bot commands ---


def _authorized(update: Update, db) -> bool:
    chat_id = _chat_id(db)
    return chat_id is not None and str(update.effective_chat.id) == str(chat_id)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = SessionLocal()
    try:
        if not _authorized(update, db):
            return
        sites = db.query(Site).all()
        lines = []
        for site in sites:
            state = "paused" if not site.active else "active"
            lines.append(f"- {site.name} ({state})")
        await update.message.reply_text("\n".join(lines) or "No sites configured.")
    finally:
        db.close()


async def cmd_site(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = SessionLocal()
    try:
        if not _authorized(update, db):
            return
        if not context.args:
            await update.message.reply_text("Usage: /site <name>")
            return
        name = " ".join(context.args)
        site = db.query(Site).filter(Site.name.ilike(f"%{name}%")).first()
        if not site:
            await update.message.reply_text(f"No site matching '{name}'")
            return
        open_incidents = (
            db.query(Incident).filter(Incident.site_id == site.id, Incident.closed_at.is_(None)).count()
        )
        await update.message.reply_text(
            f"{site.name}\nURL: {site.url}\nActive: {site.active}\nOpen incidents: {open_incidents}"
        )
    finally:
        db.close()


async def cmd_silence(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from datetime import timedelta

    from app.models.silence import Silence

    db = SessionLocal()
    try:
        if not _authorized(update, db):
            return
        if len(context.args) < 2:
            await update.message.reply_text("Usage: /silence <name> <hours>")
            return
        *name_parts, hours_str = context.args
        name = " ".join(name_parts)
        try:
            hours = float(hours_str)
        except ValueError:
            await update.message.reply_text("Hours must be a number")
            return
        site = db.query(Site).filter(Site.name.ilike(f"%{name}%")).first()
        if not site:
            await update.message.reply_text(f"No site matching '{name}'")
            return
        silence = Silence(site_id=site.id, until=datetime.now(timezone.utc) + timedelta(hours=hours))
        db.add(silence)
        db.commit()
        await update.message.reply_text(f"Silenced {site.name} for {hours}h")
    finally:
        db.close()


async def cmd_incidents(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = SessionLocal()
    try:
        if not _authorized(update, db):
            return
        open_incidents = (
            db.query(Incident).filter(Incident.closed_at.is_(None)).order_by(Incident.opened_at.desc()).limit(20).all()
        )
        if not open_incidents:
            await update.message.reply_text("No open incidents.")
            return
        lines = []
        for inc in open_incidents:
            site = db.get(Site, inc.site_id)
            lines.append(f"- {site.name if site else inc.site_id}: {inc.check_type.value} since {format_timestamp(inc.opened_at)}")
        await update.message.reply_text("\n".join(lines))
    finally:
        db.close()


def build_application() -> Application | None:
    global _application
    if not settings.telegram_bot_token:
        return None
    _application = Application.builder().token(settings.telegram_bot_token).build()
    _application.add_handler(CommandHandler("status", cmd_status))
    _application.add_handler(CommandHandler("site", cmd_site))
    _application.add_handler(CommandHandler("silence", cmd_silence))
    _application.add_handler(CommandHandler("incidents", cmd_incidents))
    return _application


async def start_bot() -> None:
    app = build_application()
    if app is None:
        logger.info("TELEGRAM_BOT_TOKEN not set; bot commands disabled")
        return
    await app.initialize()
    await app.start()
    await app.updater.start_polling()


async def stop_bot() -> None:
    if _application is None:
        return
    if _application.updater and _application.updater.running:
        await _application.updater.stop()
    await _application.stop()
    await _application.shutdown()
