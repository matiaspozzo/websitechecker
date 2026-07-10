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
   define('SITEWATCH_TOKEN', 'REDACTED_MU_PLUGIN_TOKEN');
   ```

   Generate one with `openssl rand -hex 32` or similar.
3. In the SiteWatch panel, edit the site and paste the same value into the
   "mu-plugin token" field.

## Verify

```bash
curl -H "X-SiteWatch-Token: a-long-random-string-shared-with-sitewatch" \
  https://example.com/wp-json/sitewatch/v1/report
```

Should return JSON with `core_version`, `plugins`, `themes`, `php_version`,
and `admin_usernames`. A wrong or missing token returns `401`.

## Notes

- The endpoint requires no WordPress login — auth is entirely the shared
  token, checked with `hash_equals()` to avoid timing attacks.
- Uses `get_plugins()` / `get_core_updates()` from `wp-admin/includes/`,
  which the mu-plugin loads on demand since REST requests don't normally
  pull in wp-admin code.
- Rotate the token by changing it in both `wp-config.php` and the panel.

