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

| Variable | Description |
|----------|-------------|
| `BACKEND_URL` | Backend HTTP base URL (server-side calls / proxying) |
| `BACKEND_WS_URL` | Backend WebSocket URL for the chat stream |
| `NEXT_PUBLIC_AUTH_ENABLED` | Toggle auth UI (`true` when JWT/OAuth is enabled) |
{%- if cookiecutter.enable_oauth %}
| `NEXT_PUBLIC_API_URL` | Public API URL used by OAuth redirects |
{%- endif %}
{%- if cookiecutter.enable_rag %}
| `NEXT_PUBLIC_RAG_ENABLED` | Show knowledge-base / RAG UI |
{%- endif %}

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

In the Vercel dashboard set `BACKEND_URL`, `BACKEND_WS_URL`, and
`NEXT_PUBLIC_AUTH_ENABLED=true`. See the project root `docs/deploy.md` for details.
