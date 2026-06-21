"use client";

import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { CornerDownLeft, Pencil, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "./button";

export interface QuestionPromptItem {
  question: string;
  options?: string[];
  /** Allow a free-form answer via the "Something else" field (default true). */
  allowCustom?: boolean;
}

export interface QuestionPromptAnswer {
  answer: string;
  skipped: boolean;
}

export interface QuestionPromptProps {
  /** Questions to ask, in order. The card steps through them one at a time. */
  questions: QuestionPromptItem[];
  /** Disable all controls (e.g. while the socket is offline). */
  disabled?: boolean;
  /** Called once every question has been answered or skipped. */
  onComplete: (answers: QuestionPromptAnswer[]) => void;
}

/**
 * Reusable question card. Steps through `questions` one at a time, collecting an
 * answer (a chosen option, free text, or a skip) for each, then returns them all
 * via `onComplete`. Keyboard: digit keys pick an option, ↑/↓ move focus, Enter
 * selects the focused option (or submits the custom answer).
 */
export function QuestionPrompt({ questions, disabled = false, onComplete }: QuestionPromptProps) {
  const [step, setStep] = useState(0);
  const answersRef = useRef<QuestionPromptAnswer[]>([]);

  if (questions.length === 0) return null;
  const total = questions.length;
  const current = questions[step]!;

  const commit = (a: QuestionPromptAnswer) => {
    const next = [...answersRef.current, a];
    answersRef.current = next;
    if (next.length >= total) onComplete(next);
    else setStep((s) => s + 1);
  };

  const dismiss = () => {
    const remaining = questions
      .slice(answersRef.current.length)
      .map(() => ({ answer: "", skipped: true }));
    onComplete([...answersRef.current, ...remaining]);
  };

  return (
    <div className="bg-muted/40 border-foreground/10 overflow-hidden rounded-2xl border">
      <div className="flex items-center justify-between gap-3 px-4 pt-2.5 pb-0.5">
        {total > 1 ? (
          <span className="text-muted-foreground font-mono text-[10px] tracking-wider uppercase">
            Question {step + 1} of {total}
          </span>
        ) : (
          <span />
        )}
        <button
          type="button"
          onClick={dismiss}
          disabled={disabled}
          aria-label="Dismiss questions"
          className="text-muted-foreground hover:text-foreground shrink-0 rounded-md p-1 transition-colors"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <SingleQuestion
        key={step}
        question={current.question}
        options={current.options ?? []}
        allowCustom={current.allowCustom ?? true}
        isLast={step + 1 >= total}
        disabled={disabled}
        onAnswer={(text) => commit({ answer: text, skipped: false })}
        onSkip={() => commit({ answer: "", skipped: true })}
      />
    </div>
  );
}

interface SingleQuestionProps {
  question: string;
  options: string[];
  allowCustom: boolean;
  isLast: boolean;
  disabled: boolean;
  onAnswer: (answer: string) => void;
  onSkip: () => void;
}

function SingleQuestion({
  question,
  options,
  allowCustom,
  isLast,
  disabled,
  onAnswer,
  onSkip,
}: SingleQuestionProps) {
  const hasOptions = options.length > 0;
  const [focusIdx, setFocusIdx] = useState(0);
  // Open the free-form field straight away when there are no options to pick.
  const [customOpen, setCustomOpen] = useState(allowCustom && !hasOptions);
  const [customText, setCustomText] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (customOpen) inputRef.current?.focus();
    else containerRef.current?.focus();
  }, [customOpen]);

  const submitCustom = () => {
    const text = customText.trim();
    if (text) onAnswer(text);
  };

  const onListKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (disabled || customOpen || !hasOptions) return;
    if (/^[1-9]$/.test(e.key)) {
      const idx = Number(e.key) - 1;
      if (idx < options.length) {
        e.preventDefault();
        onAnswer(options[idx]!);
      }
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setFocusIdx((i) => Math.min(i + 1, options.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setFocusIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      onAnswer(options[focusIdx]!);
    }
  };

  return (
    <div
      ref={containerRef}
      tabIndex={-1}
      onKeyDown={onListKeyDown}
      role="group"
      aria-label="Question from the assistant"
      className="outline-none"
    >
      <p className="text-foreground px-4 pb-2.5 text-[15px] leading-snug font-medium">{question}</p>

      {hasOptions && (
        <ul className="divide-foreground/8 border-foreground/8 divide-y border-t">
          {options.map((option, i) => {
            const focused = i === focusIdx && !customOpen;
            return (
              <li key={`${option}-${i}`}>
                <button
                  type="button"
                  disabled={disabled}
                  onMouseEnter={() => setFocusIdx(i)}
                  onClick={() => onAnswer(option)}
                  className={cn(
                    "flex w-full items-center gap-3 px-4 py-3 text-left transition-colors",
                    focused ? "bg-foreground/[0.06]" : "hover:bg-foreground/[0.03]",
                  )}
                >
                  <span
                    className={cn(
                      "inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-lg font-mono text-xs tabular-nums",
                      focused
                        ? "bg-foreground/10 text-foreground"
                        : "bg-foreground/5 text-muted-foreground",
                    )}
                  >
                    {i + 1}
                  </span>
                  <span className="text-foreground min-w-0 flex-1 truncate text-sm">{option}</span>
                  {focused && <CornerDownLeft className="text-muted-foreground h-4 w-4 shrink-0" />}
                </button>
              </li>
            );
          })}
        </ul>
      )}

      <div className={cn("border-foreground/8", hasOptions && "border-t")}>
        {customOpen ? (
          <div className="flex items-center gap-2 px-4 py-2.5">
            <Pencil className="text-muted-foreground h-3.5 w-3.5 shrink-0" />
            <input
              ref={inputRef}
              type="text"
              value={customText}
              disabled={disabled}
              placeholder="Type your answer…"
              onChange={(e) => setCustomText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  submitCustom();
                }
              }}
              className="text-foreground placeholder:text-muted-foreground min-w-0 flex-1 bg-transparent text-sm outline-none"
            />
            <Button
              type="button"
              size="sm"
              className="h-7 text-xs"
              disabled={disabled || !customText.trim()}
              onClick={submitCustom}
            >
              {isLast ? "Done" : "Next"}
            </Button>
          </div>
        ) : (
          <div className="flex items-center justify-between gap-2 px-4 py-2.5">
            {allowCustom ? (
              <button
                type="button"
                disabled={disabled}
                onClick={() => setCustomOpen(true)}
                className="text-muted-foreground hover:text-foreground flex items-center gap-2 text-sm transition-colors"
              >
                <Pencil className="h-3.5 w-3.5" />
                Something else
              </button>
            ) : (
              <span />
            )}
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-7 text-xs"
              disabled={disabled}
              onClick={onSkip}
            >
              Skip
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
