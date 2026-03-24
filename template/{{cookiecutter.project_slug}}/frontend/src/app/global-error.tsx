{%- if cookiecutter.use_frontend %}
{% raw %}"use client";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body style={{ margin: 0, fontFamily: "Inter, system-ui, sans-serif" }}>
        <div
          style={{
            minHeight: "100vh",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: "1rem",
            textAlign: "center",
            backgroundColor: "#09090b",
            color: "#fafafa",
          }}
        >
          <p
            style={{
              fontSize: "0.875rem",
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              color: "#ef4444",
            }}
          >
            500
          </p>
          <h1
            style={{
              marginTop: "0.5rem",
              fontSize: "2.25rem",
              fontWeight: 700,
              letterSpacing: "-0.025em",
            }}
          >
            Something went wrong
          </h1>
          <p
            style={{
              marginTop: "1rem",
              color: "#a1a1aa",
              maxWidth: "28rem",
            }}
          >
            An unexpected error occurred. Please try again or contact support if the problem
            persists.
          </p>
          {error.digest && (
            <p
              style={{
                marginTop: "0.5rem",
                fontSize: "0.75rem",
                color: "#71717a",
              }}
            >
              Error ID: {error.digest}
            </p>
          )}
          <div style={{ marginTop: "2rem", display: "flex", gap: "0.75rem" }}>
            <button
              onClick={reset}
              style={{
                padding: "0.625rem 1rem",
                fontSize: "0.875rem",
                fontWeight: 500,
                borderRadius: "0.5rem",
                border: "none",
                cursor: "pointer",
                backgroundColor: "#3b82f6",
                color: "#fff",
              }}
            >
              Try again
            </button>
            {/* eslint-disable-next-line @next/next/no-html-link-for-pages */}
            <a
              href="/"
              style={{
                padding: "0.625rem 1rem",
                fontSize: "0.875rem",
                fontWeight: 500,
                borderRadius: "0.5rem",
                border: "1px solid #27272a",
                backgroundColor: "transparent",
                color: "#fafafa",
                textDecoration: "none",
              }}
            >
              Go home
            </a>
          </div>
        </div>
      </body>
    </html>
  );
}
{% endraw %}
{%- endif %}
