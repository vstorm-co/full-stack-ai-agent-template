"use client";

import { useState } from "react";
import { CreditCard, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { useBilling } from "@/hooks";
import { SeatSelectorDialog } from "./seat-selector-dialog";
import type { Organization } from "@/types";

interface BillingCardProps {
  org: Organization;
  memberCount: number;
}

const tierLabels: Record<string, string> = {
  free: "Free",
  solo: "Solo",
  team: "Team",
  business: "Business",
};

export function BillingCard({ org, memberCount }: BillingCardProps) {
  const { isLoading, openPortal } = useBilling();
  const [seatDialogOpen, setSeatDialogOpen] = useState(false);

  const seatsUsed = memberCount;
  const seatsLimit = org.seats_limit;
  const seatsPercent = seatsLimit ? Math.round((seatsUsed / seatsLimit) * 100) : 0;
  const tier = org.subscription_tier ?? "free";

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <CreditCard className="h-4 w-4" />
              Billing & Subscription
            </CardTitle>
            <Badge variant={tier === "free" ? "secondary" : "default"}>
              {tierLabels[tier] ?? tier}
            </Badge>
          </div>
          <CardDescription>
            {tier === "free"
              ? "Upgrade to add more seats and unlock features."
              : "Manage your subscription and billing details."}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {seatsLimit !== null && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground flex items-center gap-1.5">
                  <Users className="h-3.5 w-3.5" />
                  Seats used
                </span>
                <span className="font-medium">
                  {seatsUsed} / {seatsLimit}
                </span>
              </div>
              <Progress value={seatsPercent} className="h-1.5" />
            </div>
          )}
          <div className="flex gap-2">
            {tier === "free" ? (
              <Button
                onClick={() => setSeatDialogOpen(true)}
                disabled={isLoading}
                className="flex-1"
              >
                Upgrade plan
              </Button>
            ) : (
              <Button
                variant="outline"
                onClick={openPortal}
                disabled={isLoading}
                className="flex-1"
              >
                {isLoading ? "Redirecting…" : "Manage billing"}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      <SeatSelectorDialog
        open={seatDialogOpen}
        onOpenChange={setSeatDialogOpen}
        mode="checkout"
        initialSeats={Math.max(seatsUsed + 1, 5)}
      />
    </>
  );
}
