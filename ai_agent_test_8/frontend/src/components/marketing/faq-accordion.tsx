"use client";

import * as Accordion from "@radix-ui/react-accordion";
import { ChevronDown } from "lucide-react";

interface FaqItem {
  q: string;
  a: string;
}

interface FaqAccordionProps {
  items: FaqItem[];
}

export function FaqAccordion({ items }: FaqAccordionProps) {
  return (
    <Accordion.Root
      type="single"
      collapsible
      className="border-foreground/10 divide-foreground/10 mx-auto max-w-3xl divide-y border-y"
    >
      {items.map((item, i) => (
        <Accordion.Item key={i} value={`item-${i}`} className="">
          <Accordion.Header>
            <Accordion.Trigger className="text-foreground hover:text-foreground/80 group font-display flex w-full items-center justify-between gap-6 py-6 text-left text-lg font-semibold transition-colors">
              <span>{item.q}</span>
              <ChevronDown className="text-foreground/50 h-5 w-5 shrink-0 transition-transform group-data-[state=open]:rotate-180" />
            </Accordion.Trigger>
          </Accordion.Header>
          <Accordion.Content className="data-[state=closed]:animate-accordion-up data-[state=open]:animate-accordion-down overflow-hidden">
            <p className="text-foreground/70 pr-12 pb-6 leading-relaxed">{item.a}</p>
          </Accordion.Content>
        </Accordion.Item>
      ))}
    </Accordion.Root>
  );
}
