"use client";

import { useState } from "react";
import { format } from "date-fns";
import { AlertCircle, CheckCircle, Clock, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { useSubscription, useBilling } from "@/hooks";
import { formatCurrency } from "@/lib/utils";
import { SeatSelectorDialog } from "./seat-selector-dialog";
import type { SubscriptionRead } from "@/types";

function StatusBadge({ status }: { status: SubscriptionRead["status"] }) {
  const map: Record<
    string,
    { label: string; variant: "default" | "secondary" | "destructive" | "outline" }
  > = {
    active: { label: "Active", variant: "default" },
    trialing: { label: "Trial", variant: "secondary" },
    past_due: { label: "Past due", variant: "destructive" },
    canceled: { label: "Canceled", variant: "outline" },
    unpaid: { label: "Unpaid", variant: "destructive" },
    paused: { label: "Paused", variant: "secondary" },
  };
  const { label, variant } = map[status] ?? { label: status, variant: "outline" };
  return <Badge variant={variant}>{label}</Badge>;
}

function StatusIcon({ status }: { status: SubscriptionRead["status"] }) {
  if (status === "active") return <CheckCircle className="h-5 w-5 text-green-500" />;
  if (status === "trialing") return <Clock className="h-5 w-5 text-blue-500" />;
  if (status === "canceled") return <XCircle className="text-muted-foreground h-5 w-5" />;
  return <AlertCircle className="text-destructive h-5 w-5" />;
}

export function SubscriptionPanel() {
  const { subscription, isLoading, cancelSubscription, reactivateSubscription, updateSeats } =
    useSubscription();
  const { isLoading: billingLoading, openPortal, startCheckout } = useBilling();
  const [canceling, setCanceling] = useState(false);
  const [seatDialogOpen, setSeatDialogOpen] = useState(false);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Subscription</CardTitle>
          <CardDescription>Loading subscription details…</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="bg-muted h-24 animate-pulse rounded-md" />
        </CardContent>
      </Card>
    );
  }

  if (!subscription) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>No active subscription</CardTitle>
          <CardDescription>Upgrade to unlock premium features.</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-sm">
            You&apos;re currently on the free plan. Choose a plan to get started.
          </p>
        </CardContent>
        <CardFooter>
          <Button
            onClick={() =>
              startCheckout({
                success_url: window.location.href + "?success=1",
                cancel_url: window.location.href,
              })
            }
            disabled={billingLoading}
          >
            View Plans
          </Button>
        </CardFooter>
      </Card>
    );
  }

  const planName = subscription.price?.plan?.display_name ?? "Subscription";
  const periodEnd = format(new Date(subscription.current_period_end), "MMM d, yyyy");
  const trialEnd = subscription.trial_end
    ? format(new Date(subscription.trial_end), "MMM d, yyyy")
    : null;

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <StatusIcon status={subscription.status} />
              <CardTitle>{planName}</CardTitle>
            </div>
            <StatusBadge status={subscription.status} />
          </div>
          <CardDescription>
            {subscription.status === "trialing" && trialEnd
              ? `Trial ends ${trialEnd}`
              : `Renews ${periodEnd}`}
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">Seats</p>
              <p className="font-medium">{subscription.seats_quantity}</p>
            </div>
            {subscription.price && (
              <div>
                <p className="text-muted-foreground">Price</p>
                <p className="font-medium">
                  {formatCurrency(subscription.price.amount_cents, subscription.price.currency)}{" "}
                  / {subscription.price.interval}
                </p>
              </div>
            )}
            <div>
              <p className="text-muted-foreground">Billing period ends</p>
              <p className="font-medium">{periodEnd}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Auto-renew</p>
              <p className="font-medium">{subscription.cancel_at_period_end ? "Off" : "On"}</p>
            </div>
          </div>

          {subscription.cancel_at_period_end && (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Your subscription will cancel on <strong>{periodEnd}</strong>. You&apos;ll retain
                access until then.
              </AlertDescription>
            </Alert>
          )}

          {subscription.status === "past_due" && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Your last payment failed. Update your payment method to avoid service interruption.
              </AlertDescription>
            </Alert>
          )}
        </CardContent>

        <CardFooter className="flex gap-2">
          <Button variant="outline" onClick={openPortal} disabled={billingLoading}>
            Manage Billing
          </Button>

          <Button
            variant="outline"
            onClick={() => setSeatDialogOpen(true)}
            disabled={billingLoading}
          >
            Change seats
          </Button>

          {subscription.cancel_at_period_end ? (
            <Button onClick={reactivateSubscription} disabled={billingLoading}>
              Reactivate
            </Button>
          ) : subscription.status !== "canceled" ? (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="ghost" className="text-destructive hover:text-destructive">
                  Cancel Subscription
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Cancel subscription?</AlertDialogTitle>
                  <AlertDialogDescription>
                    Your subscription will remain active until <strong>{periodEnd}</strong>, then
                    cancel automatically. You can reactivate at any time before that date.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Keep subscription</AlertDialogCancel>
                  <AlertDialogAction
                    className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                    onClick={async () => {
                      setCanceling(true);
                      await cancelSubscription();
                      setCanceling(false);
                    }}
                    disabled={canceling}
                  >
                    Yes, cancel
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          ) : null}
        </CardFooter>
      </Card>

      <SeatSelectorDialog
        open={seatDialogOpen}
        onOpenChange={setSeatDialogOpen}
        mode="update"
        initialSeats={subscription.seats_quantity}
        onUpdate={updateSeats}
      />
    </>
  );
}
