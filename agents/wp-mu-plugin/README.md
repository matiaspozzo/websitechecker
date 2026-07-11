# SiteWatch WordPress mu-plugin

Exposes `GET /wp-json/sitewatch/v1/report`, protected by a shared token, so
SiteWatch can pull core/plugin/theme/PHP versions and admin usernames once a
day. This is an outbound *pull* from SiteWatch's side, so it works fine even
though the WordPress site is a normal internet-facing host and SiteWatch
itself sits behind NAT with no public IP.

## Install

1. Copy `sitewatch-report.php` into the site's `wp-content/mu-plugins/`
   directory (create the directory if it doesn't exist — anything dropped
   there is auto-loaded by WordPress, no activation step needed).
2. Add a token constant to `wp-config.php` (above the
   `/* That's all, stop editing! */` line):

   ```php
   define('SITEWATCH_TOKEN', 'REPLACE_WITH_A_GENERATED_TOKEN');
   ```

   Generate one with `openssl rand -hex 32` or similar — never commit the
   real value anywhere in this repo (docs included); it only belongs in each
   site's own `wp-config.php` and in the panel's "mu-plugin token" field,
   which is stored in the gitignored SQLite database, not in source control.
3. In the SiteWatch panel, edit the site and paste the same value into the
   "mu-plugin token" field.

## Verify

```bash
curl -H "X-SiteWatch-Token: a-long-random-string-shared-with-sitewatch" \
  https://example.com/wp-json/sitewatch/v1/report
```

Should return JSON with `mu_plugin_version`, `core_version`, `plugins`,
`themes`, `php_version`, and `admin_usernames`. A wrong or missing token
returns `401`.

## Updating an existing install

Just re-uploading `sitewatch-report.php` isn't always enough to take effect
immediately: if the site runs a page-cache plugin (LiteSpeed Cache confirmed
in the wild caching this exact endpoint, alongside regular pages), whatever
response was cached *before* your update can keep being served until it's
purged or naturally expires — so the panel may keep showing "mu-plugin
outdated" for a while even though the new file is in place. As of v1.2.0 the
plugin sends `Cache-Control: no-store` and explicitly tells LiteSpeed Cache
not to cache this route, but that only takes effect once the *new* code
actually runs once. After updating the file on a site with any caching
plugin, purge that site's cache once (e.g. LiteSpeed Cache → Dashboard →
Purge All) so the next SiteWatch check sees the new version right away
instead of waiting out the old cache entry.

## Notes

- The endpoint requires no WordPress login — auth is entirely the shared
  token, checked with `hash_equals()` to avoid timing attacks.
- Uses `get_plugins()` / `get_core_updates()` from `wp-admin/includes/`,
  which the mu-plugin loads on demand since REST requests don't normally
  pull in wp-admin code.
- Forces a fresh `wp_version_check()` / `wp_update_plugins()` /
  `wp_update_themes()` on every call rather than trusting WordPress's own
  cron-populated transients, since wp-cron reliability varies a lot across
  hosting setups and a stale transient makes every "available" field
  silently report null.
- Sends explicit no-cache headers and opts out of LiteSpeed Cache
  specifically, since page-cache plugins don't know on their own that a
  REST API route needs to stay live. See "Updating an existing install"
  above if you're on an older copy and the panel won't clear a stale
  "outdated" badge.
- Rotate the token by changing it in both `wp-config.php` and the panel.

