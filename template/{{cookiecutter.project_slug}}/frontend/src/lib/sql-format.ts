{% raw %}const CLAUSE_RE =
  /\s+\b(FROM|WHERE|GROUP BY|ORDER BY|HAVING|LIMIT|OFFSET|UNION ALL|UNION|INNER JOIN|LEFT JOIN|RIGHT JOIN|FULL JOIN|CROSS JOIN|JOIN)\b/gi;
const BOOL_RE = /\s+\b(AND|OR)\b/gi;
const LITERAL_TOKEN_RE = /\{\{LIT(\d+)\}\}/g;

/**
 * Pretty-print a single-line SQL statement onto multiple lines so it reads like a
 * formatted code block instead of one long string. Major clauses start a new line
 * and boolean connectors in the WHERE clause are indented.
 *
 * String literals are masked with a `{{LITn}}` token before the newline pass and
 * restored afterwards. The token carries no whitespace and no bare digits of its own,
 * so a keyword inside quotes (e.g. an ILIKE pattern) is never broken onto a new line,
 * and a real number such as `LIMIT 20` is never mistaken for a masked literal. A SQL
 * string that already contains newlines is assumed pre-formatted and returned as-is.
 */
export function formatSql(sql: string): string {
  if (sql.includes("\n")) return sql.trim();
  const literals: string[] = [];
  let out = sql.replace(/'(?:[^']|'')*'/g, (m) => {
    literals.push(m);
    return `{{LIT${literals.length - 1}}}`;
  });
  out = out.replace(CLAUSE_RE, "\n$1").replace(BOOL_RE, "\n  $1");
  out = out.replace(LITERAL_TOKEN_RE, (_, i) => literals[Number(i)] ?? "");
  return out.trim();
}
{% endraw %}
