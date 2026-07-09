/// <reference types="vite/client" />

// Vite `?inline` asset imports resolve to a base64 data-URI string at build time. Declared
// here (rather than relying on Next's generated next-env.d.ts, which is absent in CI and types
// bare `*.jpg` as StaticImageData) so `tsc --noEmit` passes standalone.
declare module "*.jpg?inline" {
  const src: string;
  export default src;
}
