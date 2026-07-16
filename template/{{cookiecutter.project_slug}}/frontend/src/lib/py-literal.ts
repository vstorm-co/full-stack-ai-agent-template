/**
 * Minimal parser for Python-repr values, plus helpers for the pydantic-ai builtins that
 * return them. Several builtin tools (`duckduckgo_search`, `web_fetch`) return a *Python-repr*
 * string — single-quoted keys, mixed quotes, `True`/`False`/`None` — which `JSON.parse` can't
 * read. This module normalizes those into JS values.
 */

export type PyValue = string | number | boolean | null | PyValue[] | { [k: string]: PyValue };

/** Recursive-descent parser for a Python literal (list/dict/str/num/bool/None).
 *  Robust to the mixed single/double quoting and embedded apostrophes the builtins emit;
 *  returns null on anything it can't parse (e.g. lowercase JSON true/false/null). */
export function parsePyLiteral(src: string): PyValue | null {
  let i = 0;
  const isWs = (c: string | undefined) => c === " " || c === "\n" || c === "\t" || c === "\r";
  const ws = () => {
    while (i < src.length && isWs(src[i])) i += 1;
  };
  const parseString = (q: string): string => {
    i += 1; // opening quote
    let out = "";
    while (i < src.length) {
      const ch = src[i]!;
      if (ch === "\\") {
        const next = src[i + 1];
        out += next === "n" ? "\n" : next === "t" ? "\t" : next === "r" ? "\r" : (next ?? "");
        i += 2;
        continue;
      }
      if (ch === q) {
        i += 1;
        return out;
      }
      out += ch;
      i += 1;
    }
    throw new Error("unterminated string");
  };
  const parseValue = (): PyValue => {
    ws();
    const c = src[i];
    if (c === "[") return parseList();
    if (c === "{") return parseDict();
    if (c === "'" || c === '"') return parseString(c);
    const m = /^(True|False|None|-?\d+\.?\d*(?:[eE][+-]?\d+)?)/.exec(src.slice(i));
    if (!m) throw new Error("bad literal");
    i += m[0].length;
    return m[0] === "True" ? true : m[0] === "False" ? false : m[0] === "None" ? null : Number(m[0]);
  };
  const parseList = (): PyValue[] => {
    i += 1; // [
    const arr: PyValue[] = [];
    ws();
    if (src[i] === "]") {
      i += 1;
      return arr;
    }
    for (;;) {
      arr.push(parseValue());
      ws();
      const c = src[i];
      i += 1;
      if (c === "]") return arr;
      if (c !== ",") throw new Error("expected , or ]");
      ws();
      if (src[i] === "]") {
        i += 1;
        return arr;
      }
    }
  };
  const parseDict = (): { [k: string]: PyValue } => {
    i += 1; // {
    const obj: { [k: string]: PyValue } = {};
    ws();
    if (src[i] === "}") {
      i += 1;
      return obj;
    }
    for (;;) {
      ws();
      const q = src[i];
      if (q !== "'" && q !== '"') throw new Error("expected string key");
      const key = parseString(q);
      ws();
      if (src[i] !== ":") throw new Error("expected :");
      i += 1;
      obj[key] = parseValue();
      ws();
      const c = src[i];
      i += 1;
      if (c === "}") return obj;
      if (c !== ",") throw new Error("expected , or }");
      ws();
      if (src[i] === "}") {
        i += 1;
        return obj;
      }
    }
  };
  try {
    return parseValue();
  } catch {
    return null;
  }
}

export interface FetchedPage {
  url: string;
  title: string;
  content: string;
}

/** Parse a `web_fetch` / `fetch_url` result into `{url, title, content}`.
 *  The pydantic-ai `web_fetch` builtin returns a Python-repr dict
 *  `{'url': …, 'title': …, 'content': …}`; older shapes may be JSON or plain text.
 *  Returns null when the result isn't a dict-shaped page (caller treats it as raw content). */
export function parseFetchedPage(result: string): FetchedPage | null {
  const trimmed = result.trim();
  if (!trimmed.startsWith("{")) return null;
  let obj: Record<string, unknown> | null = null;
  try {
    const j = JSON.parse(trimmed);
    if (j && typeof j === "object" && !Array.isArray(j)) obj = j as Record<string, unknown>;
  } catch {
    const p = parsePyLiteral(trimmed);
    if (p && typeof p === "object" && !Array.isArray(p)) obj = p as Record<string, unknown>;
  }
  if (!obj) return null;
  const content = typeof obj.content === "string" ? obj.content : typeof obj.text === "string" ? obj.text : "";
  if (!content && typeof obj.url !== "string") return null;
  return {
    url: typeof obj.url === "string" ? obj.url : "",
    title: typeof obj.title === "string" ? obj.title : "",
    content,
  };
}

/** Strip the inline `<script>`/`<style>` blocks and JS boilerplate that scraped page text
 *  carries (gtm/dataLayer snippets, `window.*`/`document.*` statements) so it reads as prose.
 *  Conservative: only drops lines that clearly look like code — real page copy rarely does. */
export function cleanPageText(content: string): string {
  let s = content
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ");
  const looksLikeCode = (line: string): boolean => {
    const t = line.trim();
    if (!t) return false;
    return (
      /^\(?function\b|^!function\b|^\(function\b/.test(t) ||
      /^(var|let|const)\s+\w/.test(t) ||
      /^(window|document)\.[\w.]+\s*[=({]/.test(t) ||
      /^if\s*\(\s*typeof\b/.test(t) ||
      /googletagmanager|dataLayer|gtm\.(start|js)|\.getElementsByTagName|\.createElement|\.parentNode|addEventListener\(/.test(t) ||
      /^[)}\];]+[)}\];,\s]*$/.test(t)
    );
  };
  s = s
    .split("\n")
    .filter((line) => !looksLikeCode(line))
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .replace(/[ \t]{2,}/g, " ")
    .trim();
  return s;
}
