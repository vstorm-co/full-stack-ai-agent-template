import * as React from "react";

import { Button, type ButtonProps } from "./button";

export interface IconButtonProps extends Omit<ButtonProps, "size"> {
  /** Accessible name — required, since the button has no visible text. */
  "aria-label": string;
  size?: "icon-sm" | "icon" | "icon-lg";
}

/**
 * A square, icon-only button. Wraps Button with a ghost default + icon sizing,
 * replacing the dozens of ad-hoc `inline-flex h-7 w-7 … rounded-md` buttons
 * scattered across chat/settings/file-preview. Always requires an aria-label.
 */
const IconButton = React.forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ variant = "ghost", size = "icon-sm", ...props }, ref) => (
    <Button ref={ref} variant={variant} size={size} {...props} />
  ),
);
IconButton.displayName = "IconButton";

export { IconButton };
