import logging

import aiohttp
from sqlalchemy.orm import Session

from app import incident_manager
from app.checks import wpscan_client
from app.checks.base import CheckOutcome
from app.checks.registry import register
from app.models.incident import CheckType, Severity
from app.models.site import Site, SiteType
from app.models.wp_snapshot import WpSnapshot

logger = logging.getLogger(__name__)


class WordPressChecker:
    check_type = "wp"

    # WP_Error codes the mu-plugin itself returns (sitewatch-report.php) -- prefer
    # these over guessing from the HTTP status alone, since e.g. a 500 could be our
    # own "not configured" error or an unrelated PHP fatal, and only the body tells
    # them apart.
    _KNOWN_ERROR_CODES = {
        "sitewatch_not_configured": "SITEWATCH_TOKEN is not defined in wp-config.php on the site",
        "sitewatch_unauthorized": "token mismatch -- the mu-plugin token in the panel doesn't match SITEWATCH_TOKEN in wp-config.php",
    }

    async def _describe_error(self, resp: aiohttp.ClientResponse) -> str:
        try:
            body = await resp.json(content_type=None)
        except (aiohttp.ContentTypeError, ValueError):
            body = None

        code = body.get("code") if isinstance(body, dict) else None
        if code in self._KNOWN_ERROR_CODES:
            return self._KNOWN_ERROR_CODES[code]
        if resp.status == 404:
            return "mu-plugin not installed or the REST route isn't registered"
        if resp.status == 401:
            return "token mismatch (check X-SiteWatch-Token vs SITEWATCH_TOKEN)"
        message = body.get("message") if isinstance(body, dict) else None
        return message or f"HTTP {resp.status}"

    async def run(self, site: Site, db: Session, http: aiohttp.ClientSession) -> CheckOutcome:
        if not site.mu_plugin_token:
            return CheckOutcome(success=True, check_type=self.check_type, error_message="mu-plugin token not configured")

        url = site.url.rstrip("/") + "/wp-json/sitewatch/v1/report"
        try:
            async with http.get(
                url, headers={"X-SiteWatch-Token": site.mu_plugin_token}, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status != 200:
                    reason = await self._describe_error(resp)
                    await incident_manager.open_incident(
                        db,
                        site,
                        CheckType.wp_unreachable,
                        Severity.warning,
                        cause=f"{site.name}: can't reach the SiteWatch mu-plugin report endpoint ({reason})",
                        detail={"status": resp.status, "url": url},
                    )
                    return CheckOutcome(
                        success=False, check_type=self.check_type, status_code=resp.status, error_message=f"HTTP {resp.status}"
                    )
                report = await resp.json()
        except aiohttp.ClientError as exc:
            await incident_manager.open_incident(
                db,
                site,
                CheckType.wp_unreachable,
                Severity.warning,
                cause=f"{site.name}: can't reach the SiteWatch mu-plugin report endpoint ({exc})",
                detail={"error": str(exc), "url": url},
            )
            return CheckOutcome(success=False, check_type=self.check_type, error_message=str(exc))

        await incident_manager.close_incident(db, site, CheckType.wp_unreachable)

        previous = (
            db.query(WpSnapshot)
            .filter(WpSnapshot.site_id == site.id)
            .order_by(WpSnapshot.timestamp.desc())
            .first()
        )

        snapshot = WpSnapshot(
            site_id=site.id,
            core_version=report.get("core_version"),
            core_update_available=report.get("core_update_available"),
            php_version=report.get("php_version"),
            plugins_json=report.get("plugins", []),
            themes_json=report.get("themes", []),
            admin_usernames_json=report.get("admin_usernames", []),
            raw_report_json=report,
        )
        db.add(snapshot)
        db.commit()

        if previous is not None:
            new_admins = set(snapshot.admin_usernames_json) - set(previous.admin_usernames_json)
            if new_admins:
                await incident_manager.open_incident(
                    db,
                    site,
                    CheckType.new_admin,
                    Severity.critical,
                    cause=f"{site.name}: new WordPress admin user(s) detected: {', '.join(sorted(new_admins))}",
                    detail={"new_admins": sorted(new_admins)},
                )

        # Note: all plugin/theme/core CVEs share the single wp_cve incident type per site,
        # so if multiple components are simultaneously vulnerable only the most recently
        # checked one is reflected in the open incident's cause/detail.
        for plugin in snapshot.plugins_json:
            available = plugin.get("available")
            if not available or available == plugin.get("installed"):
                continue
            vulns = await wpscan_client.get_plugin_vulnerabilities(db, http, plugin.get("slug", ""))
            if vulns:
                titles = [v.get("title", "unknown vulnerability") for v in vulns]
                await incident_manager.open_incident(
                    db,
                    site,
                    CheckType.wp_cve,
                    Severity.critical,
                    cause=(
                        f"{site.name}: plugin '{plugin.get('slug')}' has known CVEs: "
                        f"{'; '.join(titles)} (patched in {available})"
                    ),
                    detail={"slug": plugin.get("slug"), "vulnerabilities": vulns},
                )

        for theme in snapshot.themes_json:
            available = theme.get("available")
            if not available or available == theme.get("installed"):
                continue
            vulns = await wpscan_client.get_theme_vulnerabilities(db, http, theme.get("slug", ""))
            if vulns:
                titles = [v.get("title", "unknown vulnerability") for v in vulns]
                await incident_manager.open_incident(
                    db,
                    site,
                    CheckType.wp_cve,
                    Severity.critical,
                    cause=(
                        f"{site.name}: theme '{theme.get('slug')}' has known CVEs: "
                        f"{'; '.join(titles)} (patched in {available})"
                    ),
                    detail={"slug": theme.get("slug"), "vulnerabilities": vulns},
                )

        if report.get("core_update_available") and snapshot.core_version:
            core_vulns = await wpscan_client.get_core_vulnerabilities(db, http, snapshot.core_version)
            if core_vulns:
                titles = [v.get("title", "unknown vulnerability") for v in core_vulns]
                await incident_manager.open_incident(
                    db,
                    site,
                    CheckType.wp_cve,
                    Severity.critical,
                    cause=(
                        f"{site.name}: WordPress core {snapshot.core_version} has known CVEs: "
                        f"{'; '.join(titles)} (update to {report.get('core_update_available')})"
                    ),
                    detail={"vulnerabilities": core_vulns},
                )

        return CheckOutcome(success=True, check_type=self.check_type)


register(WordPressChecker(), applies_to={SiteType.wordpress})
