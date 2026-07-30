/**
 * Minimal parser for Python-repr values. Tool results that are Python objects reach
 * the frontend as `str(value)` — single-quoted keys, mixed quotes, `True`/`False`/`None` —
 * which `JSON.parse` can't read. This module normalizes those into JS values.
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
    return m[0] === "True"
      ? true
      : m[0] === "False"
        ? false
        : m[0] === "None"
          ? null
          : Number(m[0]);
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

