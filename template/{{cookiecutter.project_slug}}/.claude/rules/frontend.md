---
description: Frontend conventions for Next.js
globs: ["frontend/**/*.ts", "frontend/**/*.tsx", "frontend/**/*.css"]
---

# Frontend Conventions

## Stack

- Next.js 15 with App Router
- TypeScript strict mode
- Tailwind CSS for styling
- i18n support built-in

## Structure

- Pages in `frontend/src/app/` following Next.js App Router conventions
- Reusable components in `frontend/src/components/`
- API client functions in `frontend/src/lib/`
- Types in `frontend/src/types/`

## Conventions

- Use `"use client"` directive only when component needs client-side interactivity
- Prefer Server Components by default
- Use `fetch` with proper error handling for API calls
- Keep components small and focused — extract when a component exceeds ~100 lines
