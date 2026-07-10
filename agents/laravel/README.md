# Laravel health endpoint

SiteWatch's health check expects `GET <health_endpoint_url>` to return
`{"status": "ok"}` (any other body, or a non-200 status, counts as unhealthy
and opens an incident). A good Laravel health route checks the things that
actually break silently: the database connection, the cache, and whether the
scheduler is still running.

## Route

```php
// routes/api.php
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Route;

Route::get('/health', function () {
    try {
        DB::connection()->getPdo();
    } catch (\Throwable $e) {
        return response()->json(['status' => 'error', 'reason' => 'database'], 503);
    }

    try {
        Cache::store()->put('sitewatch_health_check', true, 5);
        if (Cache::store()->get('sitewatch_health_check') !== true) {
            return response()->json(['status' => 'error', 'reason' => 'cache'], 503);
        }
    } catch (\Throwable $e) {
        return response()->json(['status' => 'error', 'reason' => 'cache'], 503);
    }

    $lastRun = Cache::get('scheduler_last_run');
    if (!$lastRun || now()->diffInMinutes($lastRun) > 5) {
        return response()->json(['status' => 'error', 'reason' => 'scheduler_stale'], 503);
    }

    return response()->json(['status' => 'ok']);
});
```

## Scheduler heartbeat

The health route above depends on the scheduler writing a timestamp to cache
every time it runs. Add this to the top of `schedule()` in
`app/Console/Kernel.php` (or the `Schedule` facade in Laravel 11+'s
`routes/console.php`):

```php
$schedule->call(fn () => Cache::put('scheduler_last_run', now(), 3600))
    ->everyMinute();
```

If `schedule:run` isn't actually firing every minute via cron (the classic
Laravel deploy footgun), `scheduler_last_run` goes stale and the health
check catches it within 5 minutes.

## Dependency audit

See the main README's SSH pull setup, or
[`../remote-audit-cron/README.md`](../remote-audit-cron/README.md) for the
no-SSH alternative. Laravel's side of it is just making sure `composer` is
on the `$PATH` for the SSH user (or the cron user, for the alternative).
