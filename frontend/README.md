Water Tank dashboard built with Next.js that talks to the Raspberry Pi FastAPI backend.

## Quick start

```bash
# inside the frontend/ folder
pnpm install    # or npm install / bun install
pnpm dev        # starts Next.js on http://localhost:3000
```

Set the backend origin with `NEXT_PUBLIC_API_BASE_URL` if it is not `http://localhost:8000`:

```bash
echo "NEXT_PUBLIC_API_BASE_URL=http://raspberrypi.local:8000" > .env.local
```

Create at least one user via the backend (`/auth/register`) or environment variables before signing in.

## Features

- HTTP Basic login screen wired to the backend `/auth/login` endpoint.
- Auto-refreshing dashboard with tank level, pump status, leak count, and usage metrics.
- Usage per-hour/day breakdowns and a recent telemetry table.
- Sparkline water-level trend and manual refresh / logout controls.

## Scripts

- `pnpm dev` – start the development server.
- `pnpm build` – create an optimized production build.
- `pnpm start` – serve the production build.
- `pnpm lint` – run ESLint.
