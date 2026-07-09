{% raw %}import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { DemoReplay } from "@/components/demo/demo-replay";
import type { RawMessage } from "@/lib/conversation-to-chat";
import { useAuthStore } from "@/stores";

import defaultAvatar from "./assets/user-avatar.jpg?inline";
import "./entry.css";

const dataEl = document.getElementById("demo-data");
let messages: RawMessage[] = [];
try {
  messages = JSON.parse(dataEl?.textContent || "[]") as RawMessage[];
} catch {
  messages = [];
}

// Default baked-in user avatar (the brand mark, frontend/demo-export/assets/user-avatar.jpg).
// Vite inlines it as a data URI, so it's permanently embedded in every export.
const DEFAULT_AVATAR = defaultAvatar;

// User avatar: exporter-injected override (--avatar) if present, else the default logo.
// Either way it's embedded, so user messages always show the avatar image. We seed the
// auth store so MessageItem takes the avatar branch, then rewrite its API-based <img src>
// to the embedded image (there is no backend offline).
const injectedAvatar = (document.getElementById("demo-user-avatar")?.textContent || "").trim();
const userAvatar = injectedAvatar || DEFAULT_AVATAR;
if (userAvatar) {
  useAuthStore.setState({
    user: { id: "demo-user", email: "", full_name: "", avatar_url: userAvatar },
  } as never);
  const applyAvatar = () => {
    document.querySelectorAll<HTMLImageElement>('img[src*="/api/users/avatar"]').forEach((img) => {
      if (img.getAttribute("src") !== userAvatar) img.setAttribute("src", userAvatar);
    });
  };
  new MutationObserver(applyAvatar).observe(document.documentElement, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ["src"],
  });
  applyAvatar();
}

// The exporter replaces the <title> sentinel, so document.title is the real title.
// (Never reference the sentinel string here — the exporter would rewrite this literal too.)
const title = document.title || "Agent session";
const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

function App() {
  return (
    <div className="bg-background flex h-screen flex-col overflow-hidden">
      <header className="bg-background/90 border-border sticky top-0 z-20 border-b backdrop-blur">
        <div className="flex h-14 items-center gap-3 px-6">
          <span className="bg-brand h-1.5 w-1.5 rounded-full" style={{ boxShadow: "0 0 8px var(--color-brand)" }} />
          <h1 className="text-foreground/70 truncate text-sm font-medium">{title}</h1>
        </div>
      </header>
      <DemoReplay rawMessages={messages} />
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
);
{% endraw %}
