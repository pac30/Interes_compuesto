// Estado global de la interfaz y formato de valores (solo para mostrar; el servidor conserva la precisión).
export const state = { currency: "COP", view: "academic", last: {} };

export function store(key, value) {
  try {
    if (value === undefined) return localStorage.getItem(key);
    localStorage.setItem(key, value);
  } catch (e) { /* almacenamiento no disponible */ }
  return null;
}

export function money(v) {
  if (v === null || v === undefined || v === "") return "—";
  const n = Number(v);
  try {
    return new Intl.NumberFormat("es-CO", { style: "currency", currency: state.currency,
      minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n);
  } catch (e) { return n.toFixed(2); }
}
export const num = (v, dp = 4) => Number(v).toLocaleString("es-CO", { maximumFractionDigits: dp });
export const pct = (v, dp = 6) => num(v, dp) + " %";
export const int = (v) => String(Math.round(Number(v)));
export function months(v) {
  const n = Number(v), y = n / 12;
  return `${num(n, 2)} meses` + (n >= 12 ? ` (${num(y, 2)} años)` : "");
}
export function date(v) {
  if (!v) return "—";
  return new Date(v + "T00:00:00").toLocaleDateString("es-CO", { day: "2-digit", month: "short", year: "numeric" });
}
export function formatCard(c) {
  if (c.value === null || c.value === undefined) return "—";
  switch (c.kind) {
    case "money": return money(c.value);
    case "pct": return pct(c.value);
    case "num": return num(c.value, 4);
    case "int": return int(c.value);
    case "months": return months(c.value);
    case "date": return date(c.value);
    default: return String(c.value);
  }
}
export function esc(s) {
  return String(s).replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
}
