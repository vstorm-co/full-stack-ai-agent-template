import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";
import jsxA11y from "eslint-plugin-jsx-a11y";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({ baseDirectory: __dirname });

const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    ignores: [".next/", "node_modules/", "out/", "next-env.d.ts"],
  },
  // Accessibility: enforce the jsx-a11y recommended ruleset explicitly.
  // next/core-web-vitals (loaded via FlatCompat above) already registers the
  // "jsx-a11y" plugin but only enables a small subset of its rules, so we
  // re-use that plugin registration and turn on the full recommended ruleset.
  {
    rules: {
      ...jsxA11y.flatConfigs.recommended.rules,
      // High-value rules — keep as errors so they block the build.
      "jsx-a11y/alt-text": "error",
      "jsx-a11y/label-has-associated-control": [
        "error",
        {
          // Treat these custom/Radix form controls as valid label targets so
          // labels that wrap them aren't flagged as orphaned.
          controlComponents: ["Checkbox", "Switch", "RadioGroupItem", "Slider"],
          assert: "either",
        },
      ],
      "jsx-a11y/aria-props": "error",
      "jsx-a11y/aria-proptypes": "error",
      "jsx-a11y/aria-unsupported-elements": "error",
      "jsx-a11y/role-has-required-aria-props": "error",
      "jsx-a11y/role-supports-aria-props": "error",
      "jsx-a11y/anchor-has-content": "error",
      "jsx-a11y/heading-has-content": "error",
      // Noisier / structural rules — surface as warnings so they're visible
      // without blocking the build. These typically require larger refactors
      // (keyboard handlers, captions, native-element swaps) to satisfy.
      "jsx-a11y/no-autofocus": "warn",
      "jsx-a11y/click-events-have-key-events": "warn",
      "jsx-a11y/no-static-element-interactions": "warn",
      "jsx-a11y/no-noninteractive-element-interactions": "warn",
      "jsx-a11y/media-has-caption": "warn",
      // Fires on a custom <CaseStudy role="COO" /> prop (job title, not an
      // ARIA role); downgraded to a warning to avoid the false positive.
      "jsx-a11y/aria-role": ["warn", { ignoreNonDOM: true }],
    },
  },
  {
    rules: {
      "@typescript-eslint/no-unused-vars": [
        "warn",
        {
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
          caughtErrorsIgnorePattern: "^_",
          destructuredArrayIgnorePattern: "^_",
        },
      ],
    },
  },
];

export default eslintConfig;
