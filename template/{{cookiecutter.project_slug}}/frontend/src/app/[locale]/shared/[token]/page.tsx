{%- if cookiecutter.use_jwt and cookiecutter.use_database %}
{% raw %}
import { MessageSquare } from "lucide-react";

interface SharedConversationPageProps {
  params: Promise<{ token: string; locale: string }>;
}

async function fetchSharedConversation(token: string) {
  // Validate token contains only safe characters (base64url)
  if (!/^[A-Za-z0-9_-]+$/.test(token)) return null;
  const baseUrl = process.env.BACKEND_URL || "http://localhost:8000";
  const res = await fetch(`${baseUrl}/api/v1/conversations/shared/${encodeURIComponent(token)}`, {
    cache: "no-store",
  });
  if (!res.ok) return null;
  return res.json();
}

export default async function SharedConversationPage({
  params,
}: SharedConversationPageProps) {
  const { token } = await params;
  const data = await fetchSharedConversation(token);

  if (!data || !data.conversation) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <MessageSquare className="mx-auto h-12 w-12 text-muted-foreground" />
          <h1 className="mt-4 text-xl font-semibold">Share link not found</h1>
          <p className="mt-2 text-muted-foreground">
            This share link may have expired or been revoked.
          </p>
        </div>
      </div>
    );
  }

  const { conversation, share } = data;
  const messages = conversation.messages || [];

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <div className="mb-6 border-b pb-4">
        <h1 className="text-xl font-semibold">
          {conversation.title || "Shared Conversation"}
        </h1>
        <p className="text-sm text-muted-foreground">
          Shared conversation — {share.permission === "view" ? "read-only" : "view & edit"}
        </p>
      </div>

      <div className="space-y-4">
        {messages.map(
          (msg: {
            id: string;
            role: string;
            content: string;
            created_at: string;
          }) => (
            <div
              key={msg.id}
              className={`flex ${
                msg.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-[80%] rounded-lg px-4 py-3 ${
                  msg.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted"
                }`}
              >
                <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                <p className="text-xs opacity-60 mt-1">
                  {new Date(msg.created_at).toLocaleString()}
                </p>
              </div>
            </div>
          )
        )}

        {messages.length === 0 && (
          <p className="text-center text-muted-foreground py-12">
            This conversation has no messages yet.
          </p>
        )}
      </div>
    </div>
  );
}
{% endraw %}
{%- else %}
export default function SharedConversationPage() {
  return <div>Shared conversations require JWT authentication and database.</div>;
}
{%- endif %}
