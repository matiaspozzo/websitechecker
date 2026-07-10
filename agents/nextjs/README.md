# Next.js health endpoint

SiteWatch's health check expects `GET <health_endpoint_url>` to return
`{"status": "ok"}`. For a Next.js app this is mostly a way to distinguish
"the process is up and serving" from "the reverse proxy is up but the app
crashed" — uptime checks already cover the homepage, so keep this route
cheap and specific to app-level health (e.g. a DB or upstream API your app
depends on).

## App Router (`app/api/health/route.ts`)

```ts
import { NextResponse } from "next/server"

export async function GET() {
  try {
    // Add real checks here if the app has state to verify, e.g.:
    // await db.query("select 1")
    return NextResponse.json({ status: "ok" })
  } catch {
    return NextResponse.json({ status: "error" }, { status: 503 })
  }
}
```

## Pages Router (`pages/api/health.ts`)

```ts
import type { NextApiRequest, NextApiResponse } from "next"

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  try {
    // Add real checks here if needed.
    res.status(200).json({ status: "ok" })
  } catch {
    res.status(503).json({ status: "error" })
  }
}
```

For a static/SSG-only Next.js site with no backing services, this endpoint
degenerates to "the Node process can execute a route handler" — still
useful, since it's a different failure mode than the homepage 200ing from a
CDN cache while the origin is actually down.

## Dependency audit

See the main README's SSH pull setup, or
[`../remote-audit-cron/README.md`](../remote-audit-cron/README.md) for the
no-SSH alternative. SiteWatch runs `npm audit --json` in the project
directory either way.
