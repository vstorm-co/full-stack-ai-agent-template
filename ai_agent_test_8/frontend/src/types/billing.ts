export interface CheckoutSessionResponse {
  url: string;
  session_id?: string;
}

export interface PortalSessionResponse {
  url: string;
}

export interface CreateCheckoutInput {
  seats?: number;
  price_id?: string;
  success_url: string;
  cancel_url: string;
}

export interface PlanRead {
  id: string;
  code: string;
  display_name: string;
  description: string | null;
  is_active: boolean;
  monthly_credits_base: number;
  monthly_credits_per_seat: number;
  features: Record<string, unknown>;
  prices: PriceRead[];
}

export interface PriceRead {
  id: string;
  stripe_price_id: string;
  interval: string;
  amount_cents: number;
  currency: string;
  trial_period_days: number | null;
  is_active: boolean;
  billing_scheme: string;
  credits_grant: number | null;
}

export type SubscriptionStatus =
  | "trialing"
  | "active"
  | "past_due"
  | "canceled"
  | "unpaid"
  | "incomplete"
  | "incomplete_expired"
  | "paused";

export interface SubscriptionRead {
  id: string;
  organization_id: string;
  price_id: string | null;
  seats_quantity: number;
  status: SubscriptionStatus;
  current_period_start: string;
  current_period_end: string;
  cancel_at_period_end: boolean;
  canceled_at: string | null;
  trial_start: string | null;
  trial_end: string | null;
  created_at: string;
  price?: PriceRead & { plan?: PlanRead };
}

export interface CreditBalanceRead {
  balance: number;
  low_threshold: number;
}

export interface CreditTransactionRead {
  id: string;
  organization_id: string;
  delta: number;
  balance_after: number;
  type: string;
  description: string | null;
  created_at: string;
}

export interface CreditTransactionList {
  items: CreditTransactionRead[];
  total: number;
}

export type InvoiceStatus = "draft" | "open" | "paid" | "void" | "uncollectible";

export interface InvoiceRead {
  id: string;
  number: string | null;
  status: InvoiceStatus;
  amount_due: number;
  amount_paid: number;
  currency: string;
  period_start: string;
  period_end: string;
  invoice_pdf: string | null;
  hosted_invoice_url: string | null;
  created_at: string;
}

export interface InvoiceList {
  items: InvoiceRead[];
  total: number;
}

export interface PaymentMethodCard {
  brand: string;
  last4: string;
  exp_month: number;
  exp_year: number;
}

export interface PaymentMethodRead {
  id: string;
  type: string;
  is_default: boolean;
  card: PaymentMethodCard | null;
  created_at: string;
}

export interface UpdateSeatsInput {
  seats_quantity: number;
}
