# {{ cookiecutter.project_name }} — Frontend

Next.js 15 (App Router) + React 19 + TypeScript + Tailwind CSS, with the AI chat
interface, auth, and dashboard for **{{ cookiecutter.project_name }}**.

## Prerequisites

- [Bun](https://bun.sh) (recommended) or Node.js 18+
- The backend running at `http://localhost:{{ cookiecutter.backend_port }}` (see the project root `README.md` — `make dev`)

## Getting Started

```bash
bun install        # install dependencies
bun dev            # start the dev server on http://localhost:{{ cookiecutter.frontend_port }}
```

Or run it in Docker from the project root: `make dev-frontend`.

## Environment

Copy `.env.example` to `.env.local` and adjust as needed:

| Variable | Read by | Description |
|----------|---------|-------------|
| `BACKEND_URL` | server | Backend HTTP base URL used by the route handlers in `src/app/api/*` |
| `COOKIE_SECURE` | server | `Secure` flag on the auth cookies. Unset follows `NODE_ENV`; set `false` only for an `http://` deployment on a trusted network |
| `NEXT_PUBLIC_WS_URL` | browser | Backend WebSocket origin for the chat stream (e.g. `wss://api.example.com`) |
| `NEXT_PUBLIC_API_URL` | browser | Public API URL (OAuth redirects, links to the API docs) |
| `NEXT_PUBLIC_SITE_URL` | browser | Canonical site origin for SEO metadata, OG tags, `sitemap.xml` |
{%- if cookiecutter.enable_oauth %}
| `NEXT_PUBLIC_OAUTH_PROVIDERS` | browser | Comma-separated providers shown on `/login` + `/register` |
{%- endif %}
{%- if cookiecutter.enable_rag %}
| `NEXT_PUBLIC_RAG_ENABLED` | browser | Show knowledge-base / RAG UI |
{%- endif %}

Two rules that cause most of the deployment confusion:

- **`NEXT_PUBLIC_*` is inlined into the browser bundle at build time.** Setting one
  at runtime does nothing — you have to set it before `bun run build`, which in
  Docker means a `build:` arg (see `docker-compose.frontend.yml`) followed by a
  rebuild. Everything else in the table is read at runtime.
- **`NEXT_PUBLIC_*` values must be reachable from the browser**, so never a Docker
  service name. `BACKEND_URL` is the opposite: it is resolved inside the
  container, so a service name is exactly right there.

## Scripts

```bash
bun dev              # dev server (hot reload)
bun run build        # production build
bun run start        # serve the production build
bun run lint         # ESLint
bun run lint:fix     # ESLint with autofix
bun run format       # Prettier
bun run type-check   # tsc --noEmit
bun run test:e2e     # Playwright end-to-end tests
```

## Project Structure

```
src/
├── app/            # Next.js App Router — locale-prefixed routes ([locale]/…)
├── components/     # React components (chat, auth, dashboard, marketing, ui, …)
├── hooks/          # useChat, useWebSocket, and friends
├── lib/            # API clients, query keys, helpers
├── stores/         # Zustand state
├── types/          # Shared TypeScript types
├── i18n.ts         # next-intl configuration
└── middleware.ts   # locale routing + auth guards
```

## Internationalization

Routes are locale-prefixed (`/{locale}/…`) via [next-intl](https://next-intl-docs.vercel.app/).
Add a locale by extending `i18n.ts` and providing its message catalog.

## Deployment (Vercel)

```bash
npx vercel --prod
```

In the Vercel dashboard set `BACKEND_URL=https://api.your-domain.com`,
`NEXT_PUBLIC_API_URL=https://api.your-domain.com`, `NEXT_PUBLIC_WS_URL=wss://api.your-domain.com`
and `NEXT_PUBLIC_SITE_URL=https://your-domain.com`, then redeploy — the
`NEXT_PUBLIC_*` ones only take effect on a fresh build. See the project root
`docs/deploy.md` for details.
