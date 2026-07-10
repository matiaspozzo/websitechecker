# Dependency audit without SSH access

SiteWatch's preferred way to run `composer audit` / `npm audit` on a
Laravel/Next.js site is outbound SSH (configured per-site in the panel: host,
user, key path, project path) — SiteWatch connects out to the remote server
once a day, which works fine from behind NAT since it's the client, not the
server, in that connection.

If you don't want to hand out SSH access to a client's server, run the audit
locally on a cron job instead and expose the JSON output behind a token, and
configure the site's "audit fetch URL" + "audit fetch token" in the panel
instead of the SSH fields. SiteWatch will GET that URL once a day with an
`X-SiteWatch-Token` header instead of connecting over SSH.

## 1. Cron script on the remote server

```bash
#!/usr/bin/env bash
# /opt/sitewatch/audit-cron.sh
set -euo pipefail
cd /var/www/example.com
composer audit --format=json > /var/www/example.com/storage/sitewatch-audit.json
# or for a Next.js project:
# npm audit --json > /path/to/project/sitewatch-audit.json
```

```cron
# crontab -e
0 4 * * * /opt/sitewatch/audit-cron.sh
```

## 2. Expose the JSON behind a token

Don't just drop the file in the public webroot — put it behind a tiny
token-checked endpoint. Simplest option, a one-file PHP endpoint:

```php
<?php
// public/sitewatch-audit.php
$expected = getenv('SITEWATCH_AUDIT_TOKEN');
$provided = $_SERVER['HTTP_X_SITEWATCH_TOKEN'] ?? '';
if (!$expected || !hash_equals($expected, $provided)) {
    http_response_code(401);
    exit;
}
header('Content-Type: application/json');
readfile('/var/www/example.com/storage/sitewatch-audit.json');
```

Or, if the stack has no PHP (a pure Next.js deploy), an nginx `location`
block with a query-string or header check works too — the requirement is
just "not publicly readable without the token."

## 3. Configure in the SiteWatch panel

- Audit fetch URL: `https://example.com/sitewatch-audit.php`
- Audit fetch token: the same value as `SITEWATCH_AUDIT_TOKEN`

SiteWatch prefers SSH if both SSH and fetch-URL are configured for a site;
leave the SSH fields blank to use this method.
