# Frontend Documentation

This document describes the Next.js frontend architecture.

## Technology Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| [Next.js](https://nextjs.org) | 15.x | React framework with App Router |
| [React](https://react.dev) | 19.x | UI library |
| [TypeScript](https://www.typescriptlang.org) | 5.x | Type safety |
| [Tailwind CSS](https://tailwindcss.com) | 4.x | Styling |
| [Zustand](https://zustand-demo.pmnd.rs) | 5.x | State management |
| [TanStack Query](https://tanstack.com/query) | 5.x | Server state management |
| [Bun](https://bun.sh) | Latest | Package manager & runtime |

---

## Project Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── layout.tsx          # Root layout
│   │   ├── page.tsx            # Home page
│   │   ├── providers.tsx       # Client providers
│   │   ├── (auth)/             # Auth route group
│   │   │   ├── login/
│   │   │   └── register/
│   │   ├── (dashboard)/        # Protected route group
│   │   │   ├── layout.tsx
│   │   │   ├── dashboard/
│   │   │   ├── chat/
│   │   │   └── profile/
│   │   └── api/                # API routes (BFF)
│   │       ├── health/
│   │       └── auth/
│   │           ├── login/
│   │           ├── logout/
│   │           ├── register/
│   │           ├── refresh/
│   │           └── me/
│   │
│   ├── components/             # React components
│   │   ├── ui/                 # Base UI components
│   │   │   ├── button.tsx
│   │   │   ├── input.tsx
│   │   │   ├── card.tsx
│   │   │   └── ...
│   │   ├── layout/             # Layout components
│   │   │   ├── header.tsx
│   │   │   └── sidebar.tsx
│   │   ├── auth/               # Auth components
│   │   │   ├── login-form.tsx
│   │   │   └── register-form.tsx
│   │   ├── chat/               # Chat components
│   │   │   ├── chat-container.tsx
│   │   │   ├── chat-input.tsx
│   │   │   ├── message-list.tsx
│   │   │   └── message-item.tsx
│   │   └── theme/              # Theme components
│   │       ├── theme-provider.tsx
│   │       └── theme-toggle.tsx
│   │
│   ├── hooks/                  # Custom React hooks
│   │   ├── use-auth.ts
│   │   ├── use-websocket.ts
│   │   ├── use-chat.ts
│   │   └── use-conversations.ts
│   │
│   ├── stores/                 # Zustand stores
│   │   ├── auth-store.ts
│   │   ├── chat-store.ts
│   │   ├── conversation-store.ts
│   │   └── theme-store.ts
│   │
│   ├── lib/                    # Utilities
│   │   ├── api-client.ts       # Fetch wrapper
│   │   ├── server-api.ts       # Server-side API calls
│   │   ├── utils.ts            # Helper functions
│   │   └── constants.ts
│   │
│   ├── types/                  # TypeScript types
│   │   ├── api.ts
│   │   ├── auth.ts
│   │   ├── chat.ts
│   │   └── conversation.ts
│   │
│   └── middleware.ts           # Next.js middleware
│
├── e2e/                        # Playwright tests
│   ├── auth.setup.ts
│   ├── auth.spec.ts
│   ├── home.spec.ts
│   └── chat.spec.ts
│
├── messages/                   # i18n translations
│   ├── en.json
│   └── pl.json
│
├── public/                     # Static assets
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── playwright.config.ts
└── vitest.config.ts
```

---

## Authentication

### Overview

Authentication uses HTTP-only cookies for secure token storage:

1. **Login** - Backend returns JWT tokens
2. **Cookies** - Frontend API routes set HTTP-only cookies
3. **Requests** - Cookies sent automatically with each request
4. **Refresh** - Automatic token refresh before expiry

### Auth Store

```typescript
// src/stores/auth-store.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  id: string;
  email: string;
  role: 'user' | 'admin';
  is_superuser: boolean;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setUser: (user: User | null) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      isLoading: true,
      setUser: (user) => set({ user, isAuthenticated: !!user, isLoading: false }),
      logout: () => set({ user: null, isAuthenticated: false }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ user: state.user }),
    }
  )
);
```

### Auth Hook

```typescript
// src/hooks/use-auth.ts
import { useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores/auth-store';

export function useAuth() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading, setUser, logout: storeLogout } = useAuthStore();

  // Check auth status on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const res = await fetch('/api/auth/me');
        if (res.ok) {
          const data = await res.json();
          setUser(data.user);
        } else {
          setUser(null);
        }
      } catch {
        setUser(null);
      }
    };
    checkAuth();
  }, [setUser]);

  const login = useCallback(async (email: string, password: string) => {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      throw new Error('Invalid credentials');
    }

    const data = await res.json();
    setUser(data.user);
    router.push('/dashboard');
  }, [router, setUser]);

  const logout = useCallback(async () => {
    await fetch('/api/auth/logout', { method: 'POST' });
    storeLogout();
    router.push('/login');
  }, [router, storeLogout]);

  return { user, isAuthenticated, isLoading, login, logout };
}
```

### API Routes (BFF Pattern)

Backend-for-Frontend routes handle token storage:

```typescript
// src/app/api/auth/login/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

const API_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  const body = await request.json();

  const res = await fetch(`${API_URL}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      username: body.email,
      password: body.password,
    }),
  });

  if (!res.ok) {
    return NextResponse.json({ error: 'Invalid credentials' }, { status: 401 });
  }

  const data = await res.json();

  // Set HTTP-only cookies
  const cookieStore = await cookies();
  cookieStore.set('access_token', data.access_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: 60 * 30, // 30 minutes
  });
  cookieStore.set('refresh_token', data.refresh_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: 60 * 60 * 24 * 7, // 7 days
  });

  return NextResponse.json({ user: data.user });
}
```

### Protected Routes

Use middleware to protect routes:

```typescript
// src/middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const protectedPaths = ['/dashboard', '/chat', '/profile'];
const authPaths = ['/login', '/register'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const accessToken = request.cookies.get('access_token')?.value;

  // Redirect to login if accessing protected route without token
  if (protectedPaths.some((path) => pathname.startsWith(path))) {
    if (!accessToken) {
      return NextResponse.redirect(new URL('/login', request.url));
    }
  }

  // Redirect to dashboard if accessing auth routes with token
  if (authPaths.some((path) => pathname.startsWith(path))) {
    if (accessToken) {
      return NextResponse.redirect(new URL('/dashboard', request.url));
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
};
```

---

## AI Chat

### WebSocket Connection

```typescript
// src/hooks/use-websocket.ts
import { useCallback, useEffect, useRef, useState } from 'react';

interface UseWebSocketOptions {
  onMessage?: (data: any) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
}

export function useWebSocket(url: string, options: UseWebSocketOptions = {}) {
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    const ws = new WebSocket(url);

    ws.onopen = () => {
      setIsConnected(true);
      options.onOpen?.();
    };

    ws.onclose = () => {
      setIsConnected(false);
      options.onClose?.();
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      options.onMessage?.(data);
    };

    ws.onerror = (error) => {
      options.onError?.(error);
    };

    wsRef.current = ws;
  }, [url, options]);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
  }, []);

  const send = useCallback((data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  useEffect(() => {
    return () => disconnect();
  }, [disconnect]);

  return { isConnected, connect, disconnect, send };
}
```

### Chat Hook

```typescript
// src/hooks/use-chat.ts
import { useCallback, useState } from 'react';
import { useChatStore } from '@/stores/chat-store';
import { useWebSocket } from './use-websocket';

// Origin only — the hook appends the endpoint path (/api/v1/ws/agent).
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

export function useChat() {
  const [isStreaming, setIsStreaming] = useState(false);
  const { messages, addMessage, updateLastMessage, clearMessages } = useChatStore();

  const handleMessage = useCallback((data: any) => {
    switch (data.type) {
      case 'start':
        setIsStreaming(true);
        addMessage({ role: 'assistant', content: '' });
        break;
      case 'token':
        updateLastMessage((prev) => prev + data.content);
        break;
      case 'tool_call':
        addMessage({
          role: 'tool',
          content: JSON.stringify(data.tool),
          tool_name: data.tool.name,
        });
        break;
      case 'end':
        setIsStreaming(false);
        break;
      case 'error':
        setIsStreaming(false);
        console.error('Chat error:', data.error);
        break;
    }
  }, [addMessage, updateLastMessage]);

  const { isConnected, connect, disconnect, send } = useWebSocket(WS_URL, {
    onMessage: handleMessage,
  });

  const sendMessage = useCallback((content: string) => {
    addMessage({ role: 'user', content });
    send({ type: 'message', content, history: messages });
  }, [addMessage, messages, send]);

  return {
    messages,
    isConnected,
    isStreaming,
    connect,
    disconnect,
    sendMessage,
    clearMessages,
  };
}
```

### Chat Container

```tsx
// src/components/chat/chat-container.tsx
'use client';

import { useEffect } from 'react';
import { useChat } from '@/hooks/use-chat';
import { ChatInput } from './chat-input';
import { MessageList } from './message-list';

export function ChatContainer() {
  const { messages, isConnected, isStreaming, connect, disconnect, sendMessage } = useChat();

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto">
        <MessageList messages={messages} isStreaming={isStreaming} />
      </div>
      <ChatInput onSend={sendMessage} disabled={!isConnected || isStreaming} />
    </div>
  );
}
```

---

## State Management

### Zustand Stores

```typescript
// src/stores/chat-store.ts
import { create } from 'zustand';
import { nanoid } from 'nanoid';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'tool';
  content: string;
  tool_name?: string;
  created_at: Date;
}

interface ChatState {
  messages: Message[];
  addMessage: (message: Omit<Message, 'id' | 'created_at'>) => void;
  updateLastMessage: (updater: (content: string) => string) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],

  addMessage: (message) =>
    set((state) => ({
      messages: [
        ...state.messages,
        { ...message, id: nanoid(), created_at: new Date() },
      ],
    })),

  updateLastMessage: (updater) =>
    set((state) => ({
      messages: state.messages.map((msg, idx) =>
        idx === state.messages.length - 1
          ? { ...msg, content: updater(msg.content) }
          : msg
      ),
    })),

  clearMessages: () => set({ messages: [] }),
}));
```

### TanStack Query

For server state management:

```typescript
// src/lib/api-client.ts
import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  },
});

// Example hook
export function useItems() {
  return useQuery({
    queryKey: ['items'],
    queryFn: async () => {
      const res = await fetch('/api/items');
      if (!res.ok) throw new Error('Failed to fetch items');
      return res.json();
    },
  });
}
```

---

## UI Components

### Button Component

```tsx
// src/components/ui/button.tsx
import { forwardRef } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:bg-primary/90',
        destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
        outline: 'border border-input bg-background hover:bg-accent hover:text-accent-foreground',
        secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
        ghost: 'hover:bg-accent hover:text-accent-foreground',
        link: 'text-primary underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-9 rounded-md px-3',
        lg: 'h-11 rounded-md px-8',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = 'Button';

export { Button, buttonVariants };
```

---

## Testing

### Unit Tests (Vitest)

```typescript
// src/lib/utils.test.ts
import { describe, it, expect } from 'vitest';
import { cn } from './utils';

describe('cn utility', () => {
  it('merges class names', () => {
    expect(cn('foo', 'bar')).toBe('foo bar');
  });

  it('handles conditional classes', () => {
    expect(cn('foo', false && 'bar', 'baz')).toBe('foo baz');
  });

  it('merges Tailwind classes correctly', () => {
    expect(cn('p-4', 'p-2')).toBe('p-2');
  });
});
```

### E2E Tests (Playwright)

```typescript
// e2e/auth.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  test('should login successfully', async ({ page }) => {
    await page.goto('/login');

    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');

    await expect(page).toHaveURL('/dashboard');
    await expect(page.locator('text=Dashboard')).toBeVisible();
  });

  test('should show error for invalid credentials', async ({ page }) => {
    await page.goto('/login');

    await page.fill('input[name="email"]', 'wrong@example.com');
    await page.fill('input[name="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');

    await expect(page.locator('text=Invalid credentials')).toBeVisible();
  });
});
```

### Running Tests

```bash
# Unit tests
bun test
bun test:run        # CI mode
bun test:coverage   # With coverage
bun test:ui         # UI mode

# E2E tests
bun test:e2e
bun test:e2e:ui     # UI mode
bun test:e2e:headed # With browser
bun test:e2e:debug  # Debug mode
```

---

## Internationalization (i18n)

When enabled, uses `next-intl`:

```typescript
// src/i18n.ts
import { getRequestConfig } from 'next-intl/server';

export default getRequestConfig(async ({ locale }) => ({
  messages: (await import(`../messages/${locale}.json`)).default,
}));
```

```json
// messages/en.json
{
  "common": {
    "login": "Login",
    "logout": "Logout",
    "loading": "Loading..."
  },
  "auth": {
    "email": "Email",
    "password": "Password",
    "loginButton": "Sign in"
  }
}
```

Usage in components:

```tsx
import { useTranslations } from 'next-intl';

export function LoginForm() {
  const t = useTranslations('auth');

  return (
    <form>
      <label>{t('email')}</label>
      <input name="email" />
      <button>{t('loginButton')}</button>
    </form>
  );
}
```

---

## Dark Mode

### Theme Store

```typescript
// src/stores/theme-store.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type Theme = 'light' | 'dark' | 'system';

interface ThemeState {
  theme: Theme;
  setTheme: (theme: Theme) => void;
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      theme: 'system',
      setTheme: (theme) => set({ theme }),
    }),
    { name: 'theme-storage' }
  )
);
```

### Theme Provider

```tsx
// src/components/theme/theme-provider.tsx
'use client';

import { useEffect } from 'react';
import { useThemeStore } from '@/stores/theme-store';

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const { theme } = useThemeStore();

  useEffect(() => {
    const root = window.document.documentElement;
    root.classList.remove('light', 'dark');

    if (theme === 'system') {
      const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light';
      root.classList.add(systemTheme);
    } else {
      root.classList.add(theme);
    }
  }, [theme]);

  return <>{children}</>;
}
```

---

## Development Commands

```bash
# Start development server
bun dev

# Build for production
bun build

# Start production server
bun start

# Linting
bun lint
bun lint:fix

# Formatting
bun format
bun format:check

# Type checking
bun type-check

# Testing
bun test
bun test:e2e
```

---

## Environment Variables

```bash
# .env.local

# Backend API URL (for server-side)
BACKEND_URL=http://localhost:8000

# Public WebSocket origin (for client-side). Inlined into the browser bundle at
# build time, so it must be reachable from the browser and needs a rebuild to
# change. The path (/api/v1/ws/agent) is appended by the chat hook.
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# Secure flag on the auth cookies (server-side). Unset follows NODE_ENV; a
# Secure cookie is dropped by the browser over plain http://.
# COOKIE_SECURE=false

# OpenTelemetry (if Logfire enabled)
OTEL_EXPORTER_OTLP_ENDPOINT=https://logfire-api.pydantic.dev
```
