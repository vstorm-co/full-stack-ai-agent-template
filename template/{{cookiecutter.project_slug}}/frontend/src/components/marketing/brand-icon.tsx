import type { SVGProps } from "react";
import type { IconType } from "react-icons";
import { FaAws, FaMicrosoft } from "react-icons/fa6";
import {
  SiDropbox,
  SiFigma,
  SiGithub,
  SiGmail,
  SiGoogle,
  SiGoogledrive,
  SiIntercom,
  SiLinear,
  SiLoom,
  SiNotion,
  SiSlack,
  SiStripe,
  SiVercel,
} from "react-icons/si";

/** Brand glyphs sourced from a maintained icon set (Simple Icons via
 *  react-icons, Font Awesome for Microsoft) — never hand-authored SVG paths,
 *  so the marks stay correct and recognizable. Monochrome (currentColor) so
 *  they inherit the surrounding text color. */

type BrandName =
  | "gdrive"
  | "slack"
  | "notion"
  | "github"
  | "dropbox"
  | "gmail"
  | "google"
  | "microsoft"
  | "stripe"
  | "linear"
  | "vercel"
  | "figma"
  | "loom"
  | "intercom"
  | "s3"
  | "aws";

const ICONS: Record<BrandName, IconType> = {
  gdrive: SiGoogledrive,
  slack: SiSlack,
  notion: SiNotion,
  github: SiGithub,
  dropbox: SiDropbox,
  gmail: SiGmail,
  google: SiGoogle,
  microsoft: FaMicrosoft,
  stripe: SiStripe,
  linear: SiLinear,
  vercel: SiVercel,
  figma: SiFigma,
  loom: SiLoom,
  intercom: SiIntercom,
  s3: FaAws,
  aws: FaAws,
};

interface BrandIconProps extends SVGProps<SVGSVGElement> {
  name: BrandName;
}

export function BrandIcon({ name, "aria-label": ariaLabel, ...props }: BrandIconProps) {
  const Icon = ICONS[name];
  // Decorative by default — paired with a text label in our layouts. Pass
  // `aria-label` explicitly to make it semantic (e.g. icon-only buttons).
  const a11y = ariaLabel ? { role: "img", "aria-label": ariaLabel } : { "aria-hidden": true };
  return <Icon {...a11y} {...props} />;
}
