"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface UseWebSocketOptions {
  url: string;
  /** WebSocket subprotocols (e.g. ["access_token.<jwt>", "chat"]) */
  protocols?: string[];
  onMessage?: (event: MessageEvent) => void;
  onOpen?: () => void;
  onClose?: (event: CloseEvent) => void;
  onError?: (error: Event) => void;
  reconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

// Close codes that won't fix themselves by reconnecting with the same socket
// params: clean/intentional shutdowns and auth/policy rejections. Reconnecting
// on these just hammers the server (and, in Firefox, trips its built-in
// failed-reconnect throttle which then blocks every subsequent attempt locally
// before it even reaches the server). A dropped connection (1006) or an
// internal server error (1011+) is worth retrying; an auth close (4001) or a
// normal close (1000) is not.
const NO_RETRY_CLOSE_CODES = new Set([1000, 1001, 1005, 1008, 4001, 4401, 4403]);

const sigOf = (url: string, protocols?: string[]) =>
  JSON.stringify({ url, protocols: protocols ?? null });

/** Detach handlers before closing so a deliberate teardown can't re-enter the
 *  onclose logic (reconnect / token refresh) for a socket we're discarding. */
function silentClose(ws: WebSocket) {
  ws.onopen = null;
  ws.onmessage = null;
  ws.onclose = null;
  ws.onerror = null;
  try {
    ws.close();
  } catch {
    // already closing/closed — nothing to do
  }
}

export function useWebSocket({
  url,
  protocols,
  onMessage,
  onOpen,
  onClose,
  onError,
  reconnect = true,
  reconnectInterval = 1500,
  maxReconnectAttempts = 8,
}: UseWebSocketOptions) {
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  // Params the live socket was opened with — lets connect() tell a StrictMode
  // remount / quick nav-back (same params → reuse the socket) apart from a real
  // change like a refreshed token (different params → swap the socket).
  const wsSigRef = useRef<string | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  // Deferred teardown timer. disconnect() schedules the close instead of doing
  // it inline so an immediate remount can cancel it and keep the live socket —
  // abruptly closing a still-connecting socket is exactly what trips Firefox's
  // reconnect throttle and looks like "the request never reached the server".
  const closeTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  // Distinguishes a deliberate disconnect (don't reconnect) from a dropped
  // connection (do reconnect). Set true on connect(), false on disconnect().
  const shouldReconnectRef = useRef(false);

  // Use refs for callbacks to avoid recreating connect function
  const onMessageRef = useRef(onMessage);
  const onOpenRef = useRef(onOpen);
  const onCloseRef = useRef(onClose);
  const onErrorRef = useRef(onError);

  useEffect(() => {
    onMessageRef.current = onMessage;
    onOpenRef.current = onOpen;
    onCloseRef.current = onClose;
    onErrorRef.current = onError;
  }, [onMessage, onOpen, onClose, onError]);

  const connect = useCallback(() => {
    // A pending deferred close means we're mid-teardown; cancel it — we're
    // (re)connecting again, so don't drop the socket out from under ourselves.
    if (closeTimeoutRef.current) {
      clearTimeout(closeTimeoutRef.current);
      closeTimeoutRef.current = null;
    }

    const sig = sigOf(url, protocols);
    const live = wsRef.current;

    // Same params + live socket → reuse it (StrictMode double-mount, fast
    // navigate-back). Reconnecting here would needlessly churn the connection.
    if (
      live &&
      wsSigRef.current === sig &&
      (live.readyState === WebSocket.OPEN || live.readyState === WebSocket.CONNECTING)
    ) {
      shouldReconnectRef.current = true;
      return;
    }

    // Params changed (e.g. token refresh) or a stale socket lingers → discard it
    // silently before opening the replacement.
    if (live) {
      silentClose(live);
      wsRef.current = null;
    }

    shouldReconnectRef.current = true;
    const ws =
      protocols && protocols.length > 0 ? new WebSocket(url, protocols) : new WebSocket(url);
    wsRef.current = ws;
    wsSigRef.current = sig;

    ws.onopen = () => {
      setIsConnected(true);
      reconnectAttemptsRef.current = 0;
      onOpenRef.current?.();
    };

    ws.onmessage = (event) => {
      onMessageRef.current?.(event);
    };

    ws.onclose = (event) => {
      setIsConnected(false);

      // A deliberate disconnect() (unmount, logout, token swap) is not a failure
      // — don't surface it to the consumer (which would e.g. fire a token
      // refresh) and don't reconnect.
      if (!shouldReconnectRef.current) return;

      onCloseRef.current?.(event);

      // Auth/policy/clean closes won't recover by retrying the same socket.
      if (NO_RETRY_CLOSE_CODES.has(event.code)) return;

      if (reconnect && reconnectAttemptsRef.current < maxReconnectAttempts) {
        // Exponential backoff (capped) so a flapping/restarting server isn't
        // hammered, and the console isn't flooded with failed-connection noise.
        const delay = Math.min(reconnectInterval * 2 ** reconnectAttemptsRef.current, 15000);
        reconnectTimeoutRef.current = setTimeout(() => {
          reconnectAttemptsRef.current += 1;
          connect();
        }, delay);
      }
    };

    ws.onerror = (error) => {
      onErrorRef.current?.(error);
    };
  }, [url, protocols, reconnect, reconnectInterval, maxReconnectAttempts]);

  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false;
    reconnectAttemptsRef.current = 0;
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    const ws = wsRef.current;
    if (!ws) return;

    // Defer the actual close so a StrictMode remount (or fast navigate-back) can
    // cancel it in connect() and reuse the live socket instead of tearing down a
    // connection that's about to be re-requested.
    if (closeTimeoutRef.current) clearTimeout(closeTimeoutRef.current);
    closeTimeoutRef.current = setTimeout(() => {
      closeTimeoutRef.current = null;
      if (wsRef.current === ws) {
        wsRef.current = null;
        wsSigRef.current = null;
      }
      silentClose(ws);
    }, 150);
  }, []);

  const sendMessage = useCallback((data: string | object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const message = typeof data === "string" ? data : JSON.stringify(data);
      wsRef.current.send(message);
    }
  }, []);

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    isConnected,
    connect,
    disconnect,
    sendMessage,
  };
}
