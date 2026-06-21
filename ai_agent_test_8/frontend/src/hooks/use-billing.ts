"use client";

import { useCallback, useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient } from "@/lib/api-client";
import { qk } from "@/lib/query-keys";
import type {
  CheckoutSessionResponse,
  PortalSessionResponse,
  CreateCheckoutInput,
  SubscriptionRead,
  CreditBalanceRead,
  CreditTransactionList,
  PlanRead,
  InvoiceList,
} from "@/types";

export function useBilling() {
  const [isLoading, setIsLoading] = useState(false);

  const startCheckout = useCallback(async (input: CreateCheckoutInput) => {
    setIsLoading(true);
    try {
      const { url } = await apiClient.post<CheckoutSessionResponse>("/billing/checkout", input);
      window.location.href = url;
    } catch {
      toast.error("Failed to start checkout");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const openPortal = useCallback(async () => {
    setIsLoading(true);
    try {
      const { url } = await apiClient.post<PortalSessionResponse>("/billing/portal");
      window.location.href = url;
    } catch {
      toast.error("Failed to open billing portal");
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { isLoading, startCheckout, openPortal };
}

export function useSubscription() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: qk.billing.subscription(),
    queryFn: () => apiClient.get<SubscriptionRead>("/billing/me/subscription"),
  });
  const subscription = data ?? null;

  // Kept for API compatibility: the query auto-fetches; this forces a refresh.
  const fetchSubscription = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: qk.billing.subscription() });
  }, [queryClient]);

  const cancelSubscription = useCallback(async () => {
    try {
      await apiClient.delete("/billing/me/subscription");
      toast.success("Subscription will cancel at the end of the billing period.");
      fetchSubscription();
    } catch {
      toast.error("Failed to cancel subscription");
    }
  }, [fetchSubscription]);

  const reactivateSubscription = useCallback(async () => {
    try {
      await apiClient.post("/billing/me/subscription/reactivate");
      toast.success("Subscription reactivated.");
      fetchSubscription();
    } catch {
      toast.error("Failed to reactivate subscription");
    }
  }, [fetchSubscription]);

  const updateSeats = useCallback(
    async (seats: number) => {
      try {
        await apiClient.patch("/billing/me/subscription", { seats_quantity: seats });
        toast.success("Seats updated.");
        fetchSubscription();
      } catch {
        toast.error("Failed to update seats");
      }
    },
    [fetchSubscription],
  );

  return {
    subscription,
    isLoading,
    fetchSubscription,
    cancelSubscription,
    reactivateSubscription,
    updateSeats,
  };
}

export function useInvoices() {
  const queryClient = useQueryClient();

  const { data: invoices = [], isLoading } = useQuery({
    queryKey: qk.billing.invoices(),
    queryFn: async () => (await apiClient.get<InvoiceList>("/billing/me/invoices")).items,
  });

  const fetchInvoices = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: qk.billing.invoices() });
  }, [queryClient]);

  return { invoices, isLoading, fetchInvoices };
}

export function useCredits() {
  const queryClient = useQueryClient();

  const { data: balanceData, isLoading } = useQuery({
    queryKey: qk.billing.credits(),
    queryFn: () => apiClient.get<CreditBalanceRead>("/billing/me/credits"),
    // Credits change after chat turns, so keep them fresher than the global default.
    staleTime: 30_000,
  });
  const balance = balanceData ?? null;

  const { data: transactionsData, isLoading: txLoading } = useQuery({
    queryKey: qk.billing.creditsTransactions(),
    queryFn: () =>
      apiClient.get<CreditTransactionList>("/billing/me/credits/transactions?skip=0&limit=20"),
  });
  const transactions = transactionsData ?? null;

  const fetchBalance = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: qk.billing.credits() });
  }, [queryClient]);

  const fetchTransactions = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: qk.billing.creditsTransactions() });
  }, [queryClient]);

  // Listen for billing-affecting events (e.g. a finished chat turn) and
  // invalidate so the UI doesn't show stale numbers.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const handler = () => {
      queryClient.invalidateQueries({ queryKey: qk.billing.all() });
    };
    window.addEventListener("billing:refresh", handler);
    return () => window.removeEventListener("billing:refresh", handler);
  }, [queryClient]);

  return { balance, transactions, isLoading, txLoading, fetchBalance, fetchTransactions };
}

export function usePlans() {
  const { data: plans = [], isLoading } = useQuery({
    queryKey: [...qk.billing.all(), "plans"] as const,
    queryFn: async () =>
      (await apiClient.get<{ items: PlanRead[]; total: number }>("/billing/plans")).items,
  });

  return { plans, isLoading };
}
