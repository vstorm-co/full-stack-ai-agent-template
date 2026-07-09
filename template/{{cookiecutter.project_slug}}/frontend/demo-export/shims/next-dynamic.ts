import { type ComponentType, createElement, lazy, Suspense } from "react";

type Loader = () => Promise<unknown>;
interface DynamicOptions {
  ssr?: boolean;
  loading?: ComponentType;
}

/** Stand-in for `next/dynamic`: React.lazy + Suspense. Handles both
 *  `import(...)` (has `.default`) and `import(...).then(m => m.Named)` loaders. */
export default function dynamic(loader: Loader, options: DynamicOptions = {}) {
  const Lazy = lazy(async () => {
    const mod = (await loader()) as { default?: ComponentType } | ComponentType;
    const Comp = (mod as { default?: ComponentType }).default ?? (mod as ComponentType);
    return { default: Comp };
  });
  const Loading = options.loading;
  return function DynamicShim(props: Record<string, unknown>) {
    return createElement(
      Suspense,
      { fallback: Loading ? createElement(Loading) : null },
      createElement(Lazy, props),
    );
  };
}
