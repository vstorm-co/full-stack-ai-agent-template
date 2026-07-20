/** Stand-in for `next/navigation` — no routing in a static replay. */
export function useRouter() {
  return {
    push: () => {},
    replace: () => {},
    back: () => {},
    forward: () => {},
    refresh: () => {},
    prefetch: async () => {},
  };
}
export function usePathname() {
  return "/";
}
export function useSearchParams() {
  return new URLSearchParams();
}
export function useParams() {
  return {} as Record<string, string>;
}
export const redirect = () => {};
export const notFound = () => {};
