<?php
/**
 * Plugin Name: SiteWatch Report
 * Description: Token-protected REST endpoint reporting WordPress core/plugin/theme
 *              versions, PHP version, and admin usernames, for the SiteWatch
 *              monitoring system to poll once a day.
 * Version: 1.0.0
 */

if (!defined('ABSPATH')) {
    exit;
}

add_action('rest_api_init', function () {
    register_rest_route('sitewatch/v1', '/report', [
        'methods' => 'GET',
        'callback' => 'sitewatch_report_handler',
        'permission_callback' => 'sitewatch_check_token',
    ]);
});

function sitewatch_check_token(WP_REST_Request $request) {
    if (!defined('SITEWATCH_TOKEN') || empty(SITEWATCH_TOKEN)) {
        return new WP_Error(
            'sitewatch_not_configured',
            'SITEWATCH_TOKEN is not defined in wp-config.php',
            ['status' => 500]
        );
    }

    $provided = $request->get_header('x-sitewatch-token');
    if (!$provided || !hash_equals(SITEWATCH_TOKEN, $provided)) {
        return new WP_Error(
            'sitewatch_unauthorized',
            'Invalid or missing X-SiteWatch-Token header',
            ['status' => 401]
        );
    }

    return true;
}

function sitewatch_report_handler(WP_REST_Request $request) {
    if (!function_exists('get_plugins')) {
        require_once ABSPATH . 'wp-admin/includes/plugin.php';
    }
    if (!function_exists('get_core_updates')) {
        require_once ABSPATH . 'wp-admin/includes/update.php';
    }

    // Force a fresh update check instead of trusting whatever's already in the
    // update_plugins/update_themes/update_core transients. Those are normally
    // only populated by wp-cron (twice daily) -- on a site where wp-cron isn't
    // running reliably (very common: depends on real traffic or a working
    // server cron entry), the transients just sit empty and every "available"
    // field below would silently report null even when real updates exist.
    // This adds a couple of outbound requests to WordPress.org, so it's only
    // worth it because SiteWatch polls this endpoint once a day, not per-minute.
    wp_version_check();
    wp_update_plugins();
    wp_update_themes();

    // --- Core ---
    $core_version = get_bloginfo('version');
    $core_update_available = null;
    $core_updates = get_core_updates();
    if (is_array($core_updates) && !empty($core_updates)) {
        $latest = $core_updates[0];
        if (isset($latest->response) && $latest->response === 'upgrade') {
            $core_update_available = $latest->current;
        }
    }

    // --- Plugins ---
    $all_plugins = get_plugins();
    $active_plugins = (array) get_option('active_plugins', []);
    $plugin_updates = get_site_transient('update_plugins');
    $plugin_update_map = [];
    if ($plugin_updates && !empty($plugin_updates->response)) {
        foreach ($plugin_updates->response as $file => $data) {
            $plugin_update_map[$file] = $data->new_version ?? null;
        }
    }

    $plugins = [];
    foreach ($all_plugins as $file => $data) {
        $slug = dirname($file);
        if ($slug === '.') {
            $slug = basename($file, '.php');
        }
        $plugins[] = [
            'slug' => $slug,
            'installed' => $data['Version'] ?? '',
            'available' => $plugin_update_map[$file] ?? null,
            'active' => in_array($file, $active_plugins, true),
        ];
    }

    // --- Themes ---
    $theme_updates = get_site_transient('update_themes');
    $theme_update_map = [];
    if ($theme_updates && !empty($theme_updates->response)) {
        foreach ($theme_updates->response as $stylesheet => $data) {
            $theme_update_map[$stylesheet] = $data['new_version'] ?? null;
        }
    }

    $themes = [];
    foreach (wp_get_themes() as $stylesheet => $theme) {
        $themes[] = [
            'slug' => $stylesheet,
            'installed' => $theme->get('Version'),
            'available' => $theme_update_map[$stylesheet] ?? null,
        ];
    }

    // --- Admins (detect attacker-created admin accounts) ---
    $admins = get_users(['role' => 'administrator', 'fields' => ['user_login']]);
    $admin_usernames = array_map(fn($u) => $u->user_login, $admins);

    return new WP_REST_Response([
        'core_version' => $core_version,
        'core_update_available' => $core_update_available,
        'php_version' => phpversion(),
        'plugins' => $plugins,
        'themes' => $themes,
        'admin_usernames' => $admin_usernames,
    ], 200);
}
