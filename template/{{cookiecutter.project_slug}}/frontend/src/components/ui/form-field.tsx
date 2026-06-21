import * as React from "react";

import { cn } from "@/lib/utils";
import { Label } from "./label";

interface InjectableProps {
  id?: string;
  "aria-invalid"?: boolean;
  "aria-describedby"?: string;
}

export interface FormFieldProps {
  /** Visible label text. */
  label?: React.ReactNode;
  /** id of the control — used for the label's `htmlFor` and injected onto the child. */
  htmlFor: string;
  /** Helper text shown below the control when there's no error. */
  description?: React.ReactNode;
  /** Error message — when set, the control is marked invalid + described by it. */
  error?: string | null;
  required?: boolean;
  className?: string;
  /** The control (Input, Textarea, Select trigger, …). A single element. */
  children: React.ReactNode;
}

/**
 * Label + control + description/error, with accessible wiring done for you:
 * the label's `htmlFor` matches the control `id`, and `aria-describedby` /
 * `aria-invalid` are injected onto the control. Replaces the repeated
 * label+input+error markup across auth, settings, and dialog forms.
 */
export function FormField({
  label,
  htmlFor,
  description,
  error,
  required,
  className,
  children,
}: FormFieldProps) {
  const descId = `${htmlFor}-desc`;
  const errId = `${htmlFor}-err`;
  const describedBy = [error ? errId : null, description ? descId : null].filter(Boolean).join(" ");

  const control = React.isValidElement<InjectableProps>(children)
    ? React.cloneElement(children, {
        id: children.props.id ?? htmlFor,
        "aria-invalid": error ? true : children.props["aria-invalid"],
        "aria-describedby": describedBy || children.props["aria-describedby"] || undefined,
      })
    : children;

  return (
    <div className={cn("space-y-1.5", className)}>
      {label && (
        <Label htmlFor={htmlFor}>
          {label}
          {required && (
            <span className="text-destructive ml-0.5" aria-hidden="true">
              *
            </span>
          )}
        </Label>
      )}
      {control}
      {description && !error && (
        <p id={descId} className="text-muted-foreground text-xs leading-relaxed">
          {description}
        </p>
      )}
      {error && (
        <p id={errId} className="text-destructive text-xs leading-relaxed">
          {error}
        </p>
      )}
    </div>
  );
}
