#!/usr/bin/env bash
set -euo pipefail

if [ -f /app/data/sitewatch.db ]; then
    mkdir -p /app/data/backups
    cp /app/data/sitewatch.db "/app/data/backups/sitewatch-$(date +%Y%m%dT%H%M%S).db"
    # Keep the 30 most recent backups (one per container start) so the
    # directory doesn't grow unbounded on a long-running server.
    ls -1t /app/data/backups/sitewatch-*.db | tail -n +31 | xargs -r rm --
fi

alembic upgrade head

exec "$@"
