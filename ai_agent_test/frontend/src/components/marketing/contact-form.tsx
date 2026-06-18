"use client";

import { useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { ArrowRight, Check } from "lucide-react";

import { Input, Label } from "@/components/ui";
import { apiClient, ApiError } from "@/lib/api-client";
import { CONTACT_INFO } from "@/lib/contact-info";

const TOPIC_KEYS = ["support", "sales", "partnerships", "press"] as const;
type TopicKey = (typeof TOPIC_KEYS)[number];

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function ContactForm() {
  const t = useTranslations("marketing.contact.form");

  const [submitted, setSubmitted] = useState<"sent" | "mailto" | null>(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [topic, setTopic] = useState<TopicKey>("support");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const TOPIC_LABEL: Record<TopicKey, string> = {
    support: t("topic_support"),
    sales: t("topic_sales"),
    partnerships: t("topic_partnerships"),
    press: t("topic_press"),
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!name.trim() || !EMAIL_RE.test(email) || !message.trim()) {
      setError(t("errorRequired"));
      return;
    }

    setSubmitting(true);

    // Try the backend endpoint first; if it doesn't exist, fall back to mailto.
    try {
      await apiClient.post("/contact", {
        name: name.trim(),
        email: email.trim(),
        topic,
        message: message.trim(),
      });
      setSubmitted("sent");
      setSubmitting(false);
      return;
    } catch (err) {
      // 404 = endpoint not implemented yet → fall through to mailto.
      // Other 5xx = retry might help, but mailto is still a reasonable escape hatch.
      const status = err instanceof ApiError ? err.status : 0;
      if (status >= 500) {
        setError("Server error — please try again or email us directly.");
        setSubmitting(false);
        return;
      }
    }

    // Mailto fallback: opens user's mail client, prefilled.
    const subject = `[${TOPIC_LABEL[topic]}] ${name.trim()} via website`;
    const body = `${message}\n\n— ${name.trim()} <${email.trim()}>`;
    const href = `mailto:${CONTACT_INFO.emails.support}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    window.location.href = href;
    setSubmitted("mailto");
    setSubmitting(false);
  };

  if (submitted) {
    return (
      <div className="border-foreground/10 bg-card rounded-2xl border p-8 text-center">
        <div className="bg-brand text-brand-foreground mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-full">
          <Check className="h-5 w-5" />
        </div>
        <h3 className="font-display text-foreground text-xl font-semibold">
          {submitted === "sent" ? t("sentTitle") : t("fallbackOpened")}
        </h3>
        <p className="text-foreground/65 mt-2 text-sm">
          {submitted === "sent" ? t("sentBody") : t("fallbackBody")}
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label
            htmlFor="cf-name"
            className="text-foreground/80 text-xs font-medium tracking-wider uppercase"
          >
            {t("name")}
          </Label>
          <Input
            id="cf-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Maya Chen"
            required
            className="h-11 rounded-xl"
          />
        </div>
        <div className="space-y-1.5">
          <Label
            htmlFor="cf-email"
            className="text-foreground/80 text-xs font-medium tracking-wider uppercase"
          >
            {t("email")}
          </Label>
          <Input
            id="cf-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@company.com"
            required
            className="h-11 rounded-xl"
          />
        </div>
      </div>

      <div className="space-y-1.5">
        <Label className="text-foreground/80 text-xs font-medium tracking-wider uppercase">
          {t("topic")}
        </Label>
        <div className="flex flex-wrap gap-2">
          {TOPIC_KEYS.map((tk) => (
            <button
              key={tk}
              type="button"
              onClick={() => setTopic(tk)}
              className={`border-foreground/15 inline-flex rounded-full border px-3 py-1.5 font-mono text-[11px] tracking-wider uppercase transition-colors ${
                topic === tk
                  ? "bg-foreground text-background border-foreground"
                  : "text-foreground/65 hover:text-foreground hover:border-foreground/40"
              }`}
            >
              {TOPIC_LABEL[tk]}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-1.5">
        <Label
          htmlFor="cf-message"
          className="text-foreground/80 text-xs font-medium tracking-wider uppercase"
        >
          {t("message")}
        </Label>
        <textarea
          id="cf-message"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder={t("messagePlaceholder")}
          required
          rows={5}
          className="border-input bg-background placeholder:text-muted-foreground focus-visible:ring-ring block w-full scrollbar-thin rounded-xl border px-3 py-2.5 text-sm transition-colors focus-visible:ring-2 focus-visible:ring-offset-1 focus-visible:outline-none"
        />
      </div>

      {error && (
        <p className="border-destructive/30 bg-destructive/5 text-destructive rounded-lg border px-3 py-2 text-sm">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="bg-foreground text-background hover:bg-foreground/90 disabled:bg-foreground/30 inline-flex h-11 items-center justify-center gap-2 rounded-full px-6 text-sm font-medium transition-colors disabled:cursor-not-allowed"
      >
        {submitting ? t("sending") : t("send")}
        {!submitting && <ArrowRight className="h-4 w-4" />}
      </button>

      <p className="text-foreground/50 text-xs">
        {t("policyHint")}{" "}
        <Link
          href="/legal/privacy"
          className="text-foreground/70 hover:text-foreground underline-offset-4 hover:underline"
        >
          {t("policy")}
        </Link>
        .
      </p>
    </form>
  );
}
