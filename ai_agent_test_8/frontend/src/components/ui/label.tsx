import * as React from "react";
import { cn } from "@/lib/utils";

const Label = React.forwardRef<HTMLLabelElement, React.LabelHTMLAttributes<HTMLLabelElement>>(
  ({ className, ...props }, ref) => {
    return (
      // Reusable primitive: htmlFor / nested control are supplied by callers,
      // so the static association can't be verified at the definition site.
      // eslint-disable-next-line jsx-a11y/label-has-associated-control
      <label
        ref={ref}
        className={cn(
          "text-sm leading-none font-medium peer-disabled:cursor-not-allowed peer-disabled:opacity-70",
          className,
        )}
        {...props}
      />
    );
  },
);
Label.displayName = "Label";

export { Label };
