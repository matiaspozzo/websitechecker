import json
import logging

import aiohttp
from sqlalchemy.orm import Session

from app import incident_manager
from app.checks.base import CheckOutcome
from app.checks.registry import register
from app.models.dependency_audit import DependencyAudit
from app.models.incident import CheckType, Severity
from app.models.site import Site, SiteType

logger = logging.getLogger(__name__)


class HealthChecker:
    check_type = "health"

    async def run(self, site: Site, db: Session, http: aiohttp.ClientSession) -> CheckOutcome:
        if not site.health_endpoint_url:
            return CheckOutcome(success=True, check_type=self.check_type)

        ok = False
        error: str | None = None
        try:
            async with http.get(site.health_endpoint_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    try:
                        body = await resp.json(content_type=None)
                        ok = isinstance(body, dict) and body.get("status") == "ok"
                    except (aiohttp.ContentTypeError, ValueError):
                        ok = False
                else:
                    error = f"HTTP {resp.status}"
        except aiohttp.ClientError as exc:
            error = str(exc)

        if ok:
            await incident_manager.close_incident(db, site, CheckType.health)
        else:
            reason = error or 'response body was not {"status": "ok"}'
            await incident_manager.open_incident(
                db,
                site,
                CheckType.health,
                Severity.critical,
                cause=f"{site.name} health check failed: {reason}",
                detail={"error": error},
            )

        return CheckOutcome(success=ok, check_type=self.check_type, error_message=error)


register(HealthChecker(), applies_to={SiteType.laravel, SiteType.nextjs})


class DependencyAuditChecker:
    check_type = "deps"

    async def run(self, site: Site, db: Session, http: aiohttp.ClientSession) -> CheckOutcome:
        tool = "composer" if site.type == SiteType.laravel else "npm"

        if site.ssh_host and site.ssh_user and site.ssh_key_path and site.ssh_project_path:
            raw_output, error = await self._run_via_ssh(site, tool)
        elif site.audit_fetch_url:
            raw_output, error = await self._run_via_fetch(http, site)
        else:
            return CheckOutcome(success=True, check_type=self.check_type, error_message="no audit method configured")

        if error:
            return CheckOutcome(success=False, check_type=self.check_type, error_message=error)

        try:
            data = json.loads(raw_output)
        except (json.JSONDecodeError, TypeError):
            return CheckOutcome(success=False, check_type=self.check_type, error_message="could not parse audit JSON")

        high_critical_count, summary = self._summarize(tool, data)

        db.add(
            DependencyAudit(
                site_id=site.id, tool=tool, raw_json=data, high_critical_count=high_critical_count, summary=summary
            )
        )
        db.commit()

        if high_critical_count > 0:
            await incident_manager.open_incident(
                db,
                site,
                CheckType.dependency_cve,
                Severity.critical,
                cause=f"{site.name}: {high_critical_count} high/critical {tool} vulnerabilities found",
                detail={"summary": summary},
            )
        else:
            await incident_manager.close_incident(db, site, CheckType.dependency_cve)

        return CheckOutcome(success=True, check_type=self.check_type)

    async def _run_via_ssh(self, site: Site, tool: str) -> tuple[str | None, str | None]:
        import asyncssh

        command = "composer audit --format=json" if tool == "composer" else "npm audit --json"
        try:
            async with asyncssh.connect(
                site.ssh_host, username=site.ssh_user, client_keys=[site.ssh_key_path], known_hosts=None
            ) as conn:
                result = await conn.run(f"cd {site.ssh_project_path} && {command}", check=False)
                # composer/npm audit exit non-zero when vulnerabilities are found; that's expected, not a failure.
                return result.stdout, None
        except (asyncssh.Error, OSError) as exc:
            return None, f"SSH audit failed: {exc}"

    async def _run_via_fetch(self, http: aiohttp.ClientSession, site: Site) -> tuple[str | None, str | None]:
        headers = {"X-SiteWatch-Token": site.audit_fetch_token} if site.audit_fetch_token else {}
        try:
            async with http.get(
                site.audit_fetch_url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status != 200:
                    return None, f"HTTP {resp.status} fetching audit JSON"
                return await resp.text(), None
        except aiohttp.ClientError as exc:
            return None, f"fetch audit failed: {exc}"

    def _summarize(self, tool: str, data: dict) -> tuple[int, str]:
        if tool == "npm":
            meta = data.get("metadata", {}).get("vulnerabilities", {})
            high_critical = meta.get("high", 0) + meta.get("critical", 0)
            summary = ", ".join(f"{k}={v}" for k, v in meta.items() if v) or "no vulnerabilities"
            return high_critical, summary

        # composer audit --format=json -> {"advisories": {package: [...]}, "abandoned": {...}}
        advisories = data.get("advisories", {})
        count = sum(len(v) for v in advisories.values()) if isinstance(advisories, dict) else 0
        return count, (f"{count} advisories" if count else "no vulnerabilities")


register(DependencyAuditChecker(), applies_to={SiteType.laravel, SiteType.nextjs})
