{%- if cookiecutter.use_jwt and cookiecutter.use_database %}
{% raw %}
"use client";

import { useEffect, useState } from "react";
import { Copy, Link2, Trash2, UserPlus } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { useConversationShares } from "@/hooks";
import type { ConversationShare } from "@/types";

interface ShareDialogProps {
  conversationId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ShareDialog({
  conversationId,
  open,
  onOpenChange,
}: ShareDialogProps) {
  const {
    shares,
    isLoading,
    shareConversation,
    fetchShares,
    revokeShare,
  } = useConversationShares();
  const [email, setEmail] = useState("");
  const [permission, setPermission] = useState<"view" | "edit">("view");
  const [shareLink, setShareLink] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (open && conversationId) {
      fetchShares(conversationId);
    }
  }, [open, conversationId, fetchShares]);

  const handleShare = async () => {
    if (!email.trim()) return;
    try {
      await shareConversation(conversationId, {
        shared_with: email.trim(),
        permission,
      });
      setEmail("");
    } catch {
      // error handled in hook
    }
  };

  const handleGenerateLink = async () => {
    try {
      const share = await shareConversation(conversationId, {
        generate_link: true,
        permission,
      });
      if (share?.share_token) {
        const url = `${window.location.origin}/shared/${share.share_token}`;
        setShareLink(url);
      }
    } catch {
      // error handled in hook
    }
  };

  const handleCopyLink = async () => {
    if (shareLink) {
      try {
        await navigator.clipboard.writeText(shareLink);
      } catch {
        // Fallback for non-secure contexts
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleRevoke = async (share: ConversationShare) => {
    await revokeShare(conversationId, share.id);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Share Conversation</DialogTitle>
          <DialogDescription>
            Share this conversation with other users or generate a public link.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Share with user */}
          <div className="flex gap-2">
            <Input
              placeholder="User ID or email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleShare()}
            />
            <Select
              value={permission}
              onValueChange={(v) => setPermission(v as "view" | "edit")}
            >
              <SelectTrigger className="w-24">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="view">View</SelectItem>
                <SelectItem value="edit">Edit</SelectItem>
              </SelectContent>
            </Select>
            <Button onClick={handleShare} disabled={isLoading} size="icon">
              <UserPlus className="h-4 w-4" />
            </Button>
          </div>

          {/* Generate link */}
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={handleGenerateLink}
              disabled={isLoading}
              className="flex-1"
            >
              <Link2 className="mr-2 h-4 w-4" />
              Generate share link
            </Button>
            {shareLink && (
              <Button
                variant="secondary"
                size="icon"
                onClick={handleCopyLink}
              >
                <Copy className="h-4 w-4" />
              </Button>
            )}
          </div>
          {shareLink && (
            <p className="text-xs text-muted-foreground break-all">
              {copied ? "Copied!" : shareLink}
            </p>
          )}

          {/* Current shares */}
          {shares.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium">Shared with</p>
              {shares.map((share) => (
                <div
                  key={share.id}
                  className="flex items-center justify-between rounded-md border p-2"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-sm">
                      {share.shared_with_email || share.shared_with || "Link"}
                    </span>
                    <Badge variant="secondary">{share.permission}</Badge>
                    {share.share_token && (
                      <Badge variant="outline">Link</Badge>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleRevoke(share)}
                    className="h-8 w-8"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
{% endraw %}
{%- endif %}
