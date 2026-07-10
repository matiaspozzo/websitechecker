import base64
import logging

import aiohttp
from sqlalchemy.orm import Session

from app import incident_manager
from app.checks.base import CheckOutcome
from app.checks.registry import register
from app.config import settings
from app.models.blacklist_status import BlacklistStatus
from app.models.config import GlobalConfig
from app.models.incident import CheckType, Severity
from app.models.site import Site

logger = logging.getLogger(__name__)

GSB_URL = "https://safebrowsing.googleapis.com/v4/threatMatches:find"
VT_URL_SCAN = "https://www.virustotal.com/api/v3/urls"


class BlacklistChecker:
    check_type = "blacklist"

    async def run(self, site: Site, db: Session, http: aiohttp.ClientSession) -> CheckOutcome:
        config = db.get(GlobalConfig, 1)
        gsb_key = (config.gsb_api_key if config else None) or settings.google_safe_browsing_api_key
        vt_key = (config.vt_api_key if config else None) or settings.virustotal_api_key

        gsb_flagged = False
        vt_flagged: bool | None = None
        raw: dict = {}

        if gsb_key:
            gsb_flagged, gsb_raw = await self._check_gsb(http, gsb_key, site.url)
            raw["gsb"] = gsb_raw

        if vt_key:
            vt_flagged, vt_raw = await self._check_vt(http, vt_key, site.url)
            raw["vt"] = vt_raw

        db.add(
            BlacklistStatus(
                site_id=site.id,
                google_safe_browsing_flagged=gsb_flagged,
                virustotal_flagged=vt_flagged,
                raw_json=raw,
            )
        )
        db.commit()

        if gsb_flagged or vt_flagged:
            sources = []
            if gsb_flagged:
                sources.append("Google Safe Browsing")
            if vt_flagged:
                sources.append("VirusTotal")
            await incident_manager.open_incident(
                db,
                site,
                CheckType.blacklist,
                Severity.critical,
                cause=f"{site.name} flagged by: {', '.join(sources)}",
                detail=raw,
            )
        else:
            await incident_manager.close_incident(db, site, CheckType.blacklist)

        return CheckOutcome(success=not (gsb_flagged or vt_flagged), check_type=self.check_type)

    async def _check_gsb(self, http: aiohttp.ClientSession, key: str, url: str) -> tuple[bool, dict]:
        body = {
            "client": {"clientId": "sitewatch", "clientVersion": "1.0"},
            "threatInfo": {
                "threatTypes": [
                    "MALWARE",
                    "SOCIAL_ENGINEERING",
                    "UNWANTED_SOFTWARE",
                    "POTENTIALLY_HARMFUL_APPLICATION",
                ],
                "platformTypes": ["ANY_PLATFORM"],
                "threatEntryTypes": ["URL"],
                "threatEntries": [{"url": url}],
            },
        }
        try:
            async with http.post(
                f"{GSB_URL}?key={key}", json=body, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    return False, {"error": f"HTTP {resp.status}"}
                data = await resp.json()
                return bool(data.get("matches")), data
        except aiohttp.ClientError as exc:
            return False, {"error": str(exc)}

    async def _check_vt(self, http: aiohttp.ClientSession, key: str, url: str) -> tuple[bool, dict]:
        url_id = base64.urlsafe_b64encode(url.encode()).decode().strip("=")
        headers = {"x-apikey": key}
        try:
            async with http.get(
                f"{VT_URL_SCAN}/{url_id}", headers=headers, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 404:
                    return False, {"note": "not previously scanned"}
                if resp.status != 200:
                    return False, {"error": f"HTTP {resp.status}"}
                data = await resp.json()
                stats = data.get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
                flagged = stats.get("malicious", 0) > 0 or stats.get("suspicious", 0) > 0
                return flagged, stats
        except aiohttp.ClientError as exc:
            return False, {"error": str(exc)}


register(BlacklistChecker())
