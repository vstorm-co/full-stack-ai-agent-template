"use client";

import { useState } from "react";
import { Minus, Plus, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useBilling, usePlans } from "@/hooks";
import { formatCurrency } from "@/lib/utils";

interface SeatSelectorDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /**
   * "checkout" (default) — starts a Stripe checkout session.
   * "update" — calls onUpdate(seats) to patch the existing subscription.
   */
  mode?: "checkout" | "update";
  initialSeats?: number;
  onUpdate?: (seats: number) => Promise<void>;
}

export function SeatSelectorDialog({
  open,
  onOpenChange,
  mode = "checkout",
  initialSeats = 5,
  onUpdate,
}: SeatSelectorDialogProps) {
  const { plans, isLoading: plansLoading } = usePlans();
  const { startCheckout, isLoading: checkoutLoading } = useBilling();
  const [seats, setSeats] = useState(initialSeats);
  const [isUpdating, setIsUpdating] = useState(false);

  const change = (delta: number) => setSeats((s) => Math.max(1, s + delta));

  const activePlan = plans.find((p) => p.prices.some((pr) => pr.is_active));
  const price = activePlan?.prices.find((pr) => pr.is_active && pr.interval === "month");
  const perSeatCentsCents = price?.amount_cents ?? null;
  const fmt = (cents: number) => formatCurrency(cents, price?.currency ?? "USD");

  const handleConfirm = async () => {
    if (mode === "update" && onUpdate) {
      setIsUpdating(true);
      await onUpdate(seats);
      setIsUpdating(false);
      onOpenChange(false);
      return;
    }
    await startCheckout({
      seats,
      price_id: price?.id,
      success_url: `${window.location.origin}/billing?success=1`,
      cancel_url: window.location.href,
    });
  };

  const busy = checkoutLoading || isUpdating;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>{mode === "update" ? "Change seat count" : "Choose your seats"}</DialogTitle>
          <DialogDescription>
            {mode === "update"
              ? "Adjust the number of seats on your current subscription."
              : "Each seat lets one team member access the workspace."}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-2">
          <div className="flex items-center justify-between gap-4">
            <span className="flex items-center gap-2 text-sm font-medium">
              <Users className="text-muted-foreground h-4 w-4" />
              Seats
            </span>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => change(-1)}
                disabled={seats <= 1}
                aria-label="Remove a seat"
              >
                <Minus className="h-3.5 w-3.5" aria-hidden />
              </Button>
              <span
                className="w-8 text-center text-lg font-bold tabular-nums"
                aria-live="polite"
                aria-label={`${seats} seats selected`}
              >
                {seats}
              </span>
              <Button
                variant="outline"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => change(1)}
                aria-label="Add a seat"
              >
                <Plus className="h-3.5 w-3.5" aria-hidden />
              </Button>
            </div>
          </div>

          {!plansLoading && perSeatCents !== null && (
            <div className="bg-muted/50 rounded-lg p-4 text-sm">
              <div className="text-muted-foreground flex justify-between">
                <span>Per seat / month</span>
                <span>{fmt(perSeatCents)}</span>
              </div>
              <div className="mt-2 flex justify-between border-t pt-2">
                <span className="font-semibold">Total / month</span>
                <span className="text-lg font-bold">{fmt(perSeatCents * seats)}</span>
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={busy}>
            Cancel
          </Button>
          <Button onClick={handleConfirm} disabled={busy}>
            {busy ? "Please wait…" : mode === "update" ? "Save changes" : "Continue to checkout"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
