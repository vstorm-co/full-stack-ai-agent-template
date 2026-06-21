"use client";

import { PaymentMethodsPanel } from "@/components/billing";

export default function PaymentMethodsPage() {
  return (
    <div className="space-y-4">
      <p className="text-muted-foreground text-sm">
        Cards and bank accounts are managed in the Stripe billing portal — open it to add, remove, or
        set a default.
      </p>
      <PaymentMethodsPanel />
    </div>
  );
}
