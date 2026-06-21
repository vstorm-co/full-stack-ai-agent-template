"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useInvitations, useAuth } from "@/hooks";

interface PageProps {
  params: Promise<{ token: string }>;
}

export default function AcceptInvitationPage({ params }: PageProps) {
  const { token } = use(params);
  const router = useRouter();
  const { isAuthenticated } = useAuth();
  const { acceptInvitation } = useInvitations("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");

  useEffect(() => {
    if (!isAuthenticated) {
      router.push(`/login?redirect=/invitations/${token}`);
    }
  }, [isAuthenticated, router, token]);

  const handleAccept = async () => {
    setStatus("loading");
    try {
      await acceptInvitation(token);
      setStatus("success");
      setTimeout(() => router.push("/orgs"), 2000);
    } catch {
      setStatus("error");
    }
  };

  if (!isAuthenticated) return null;

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle>Team invitation</CardTitle>
          <CardDescription>You&apos;ve been invited to join an organization.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col items-center gap-4">
          {status === "success" && (
            <>
              <CheckCircle2 className="text-foreground h-12 w-12" />
              <p className="text-sm font-medium">You joined the organization!</p>
              <p className="text-muted-foreground text-xs">Redirecting to your organizations...</p>
            </>
          )}
          {status === "error" && (
            <>
              <XCircle className="text-destructive h-12 w-12" />
              <p className="text-sm font-medium">Failed to accept invitation</p>
              <p className="text-muted-foreground text-xs">
                The invitation may have expired or already been used.
              </p>
              <Button variant="outline" onClick={() => router.push("/dashboard")}>
                Go to dashboard
              </Button>
            </>
          )}
          {(status === "idle" || status === "loading") && (
            <>
              {status === "loading" && <Loader2 className="text-primary h-8 w-8 animate-spin" />}
              <p className="text-muted-foreground text-sm">
                Click below to accept this invitation and join the team.
              </p>
              <Button onClick={handleAccept} disabled={status === "loading"} className="w-full">
                {status === "loading" ? "Joining..." : "Accept invitation"}
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
