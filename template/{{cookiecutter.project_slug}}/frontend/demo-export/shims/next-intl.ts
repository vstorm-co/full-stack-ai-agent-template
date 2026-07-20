/** Stand-in for `next-intl` — replay has no i18n runtime, so translations echo the key. */
export function useTranslations(_namespace?: string) {
  return (key: string) => key;
}
export function useLocale() {
  return "en";
}
export function useFormatter() {
  return {} as Record<string, unknown>;
}
export function useMessages() {
  return {} as Record<string, unknown>;
}
export function useNow() {
  return new Date();
}
