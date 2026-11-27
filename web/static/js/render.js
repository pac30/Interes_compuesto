// Renderizado de resultados: tarjetas, gráficos, línea de tiempo, procedimiento y tablas.
import { state, money, num, pct, date, formatCard, esc } from "./format.js";

/* ---------- KaTeX ---------- */
export function tex(latex, display = false) {
  if (window.katex) {
    try { return window.katex.renderToString(latex, { displayMode: display, throwOnError: false }); } catch (e) { /* cae al texto */ }
  }
  return `<code>${esc(latex)}</code>`;
}

export function richText(text) {
  let s = esc(text);
  s = s.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
  s = s.replace(/\$([^$]+)\$/g, (_, m) => tex(m.replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">")));
  return s;
}

/* ---------- Tarjetas ---------- */
export function renderCards(el, cards, onStep) {
  el.innerHTML = "";
  cards.forEach((c, idx) => {
    const d = document.createElement("div");
    d.className = "card" + (c.hero ? " hero" : "");
    d.style.animationDelay = `${idx * 35}ms`;
    d.innerHTML = `<span class="label">${esc(c.label)}</span><strong class="value">${esc(formatCard(c))}</strong>` +
      (c.step && onStep ? `<button type="button" class="link" data-step="${c.step}">Ver procedimiento →</button>` : "");
    el.appendChild(d);
  });
  el.querySelectorAll(".link").forEach((b) => b.addEventListener("click", () => onStep(Number(b.dataset.step))));
}

export function renderWarnings(el, warnings) {
  el.innerHTML = (warnings || []).map((w) => `<div class="warn">⚠ ${esc(w)}</div>`).join("");
}

/* ---------- Gráficos ---------- */
const charts = {};
function css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
function mkChart(id, cfg) {
  const canvas = document.getElementById(id);
  if (!canvas || !window.Chart) return;
  if (charts[id]) charts[id].destroy();
  charts[id] = new window.Chart(canvas, cfg);
}
const compact = new Intl.NumberFormat("es-CO", { notation: "compact", maximumFractionDigits: 1 });
function baseOpts(xTitle) {
  return {
    responsive: true, maintainAspectRatio: true, aspectRatio: 1.8, interaction: { mode: "index", intersect: false },
    animation: { duration: 600 },
    plugins: { tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${money(c.parsed.y)}` } } },
    scales: {
      y: { ticks: { callback: (v) => compact.format(v) }, grid: { color: css("--line") } },
      x: { title: { display: !!xTitle, text: xTitle }, grid: { display: false }, ticks: { maxTicksLimit: 12 } },
    },
  };
}

export function renderCharts(el, module, chart) {
  el.innerHTML = "";
  if (!chart) return;
  const primary = css("--primary") || "#1f3a5f", accent = css("--accent") || "#0f8b8d";
  const box = (id, title) => {
    const d = document.createElement("div");
    d.className = "chart-box";
    d.innerHTML = `<h3>${title}</h3><canvas id="${id}"></canvas>`;
    el.appendChild(d);
  };
  if (chart.kind === "line") {
    box(`${module}-c1`, module === "compound" ? "Evolución del capital en el tiempo" : "Evolución del capital / saldo");
    mkChart(`${module}-c1`, {
      type: "line",
      data: { labels: chart.labels, datasets: chart.series.map((s) => ({
        label: s.name, data: s.values.map(Number), borderColor: primary, backgroundColor: primary + "22",
        fill: true, tension: 0.25, pointRadius: chart.labels.length > 60 ? 0 : 3 })) },
      options: baseOpts(chart.x_label),
    });
    if (chart.stack) {
      box(`${module}-c2`, "Distribución de cada cuota: capital vs. intereses");
      const o = baseOpts(chart.x_label);
      o.scales.x.stacked = true; o.scales.y.stacked = true;
      mkChart(`${module}-c2`, {
        type: "bar",
        data: { labels: chart.stack.labels, datasets: [
          { label: chart.stack.cap_name, data: chart.stack.capital.map(Number), backgroundColor: primary },
          { label: "Intereses", data: chart.stack.interest.map(Number), backgroundColor: accent }] },
        options: o,
      });
    }
  } else if (chart.kind === "bars") {
    box(`${module}-c1`, "Comparación de escenarios");
    const colors = [primary, accent, "#8a6d3b"];
    mkChart(`${module}-c1`, {
      type: "bar",
      data: { labels: chart.labels, datasets: chart.series.map((s, i) => ({ label: s.name, data: s.values.map(Number), backgroundColor: colors[i % 3] })) },
      options: baseOpts(""),
    });
  } else if (chart.kind === "timeline") {
    const d = document.createElement("div");
    d.className = "chart-box timeline-box";
    d.style.gridColumn = "1 / -1";
    d.innerHTML = "<h3>Línea de tiempo y traslado a la fecha focal</h3>" + timelineSVG(chart);
    el.appendChild(d);
  }
}

function timelineSVG(ch) {
  const W = 1000, H = 330, L = 70, R = 930, AX = 165;
  const byPeriod = ch.mode === "periods";
  const t = (s) => byPeriod ? Number(s) : new Date(s + "T00:00:00").getTime();
  const when = (s) => byPeriod ? `${ch.unit} ${num(s, 4)}` : date(s);
  const pos = (it) => byPeriod ? it.period : it.date;
  const all = ch.items.map((i) => t(pos(i))).concat([t(ch.focal)]);
  if (ch.start) all.push(t(ch.start));
  if (ch.end) all.push(t(ch.end));
  let min = Math.min(...all), max = Math.max(...all);
  if (min === max) { const d = byPeriod ? 1 : 864e5 * 15; min -= d; max += d; }
  const pad = (max - min) * 0.04; min -= pad; max += pad;
  const X = (s) => L + ((t(s) - min) / (max - min)) * (R - L);
  const xf = X(ch.focal);
  let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Línea de tiempo">
  <defs><marker id="arr" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" style="fill:var(--accent)"/></marker></defs>
  <line x1="${L - 20}" y1="${AX}" x2="${R + 20}" y2="${AX}" style="stroke:var(--muted)" stroke-width="2"/>`;
  [["start", "Inicio"], ["end", "Fin"]].forEach(([k, n]) => {
    if (ch[k]) svg += `<line x1="${X(ch[k])}" y1="${AX - 8}" x2="${X(ch[k])}" y2="${AX + 8}" style="stroke:var(--muted)" stroke-width="2"/>
    <text x="${X(ch[k])}" y="${AX + 24}" text-anchor="middle" font-size="11" style="fill:var(--muted)">${n} ${date(ch[k])}</text>`;
  });
  svg += `<line x1="${xf}" y1="14" x2="${xf}" y2="${H - 14}" stroke-dasharray="6 5" stroke-width="2" style="stroke:var(--accent)"/>
  <text x="${xf}" y="12" text-anchor="middle" font-size="12" font-weight="700" style="fill:var(--accent)">FECHA FOCAL · ${when(ch.focal)}</text>`;
  const ups = [], downs = [];
  ch.items.forEach((it, idx) => {
    const x = X(pos(it)), up = it.side === "deuda";
    const list = up ? ups : downs, lvl = list.length % 3; list.push(idx);
    const ty = up ? 38 + lvl * 38 : AX + 52 + lvl * 38 + 0;
    const col = up ? "#b03a2e" : "#1e7e4f";
    const dist = Math.abs(x - xf);
    if (dist > 6) {
      const cy = up ? AX - 46 : AX + 46, mx = (x + xf) / 2;
      svg += `<path d="M${x},${AX} Q${mx},${cy} ${xf},${AX}" fill="none" stroke-width="1.6" stroke-dasharray="4 3" marker-end="url(#arr)" style="stroke:var(--accent)"/>`;
      svg += `<text x="${mx}" y="${up ? AX - 26 : AX + 36}" text-anchor="middle" font-size="10.5" style="fill:var(--accent)">×${num(it.factor, 4)}</text>`;
    }
    svg += `<line x1="${x}" y1="${AX}" x2="${x}" y2="${up ? ty + 28 : ty - 14}" stroke="${col}" stroke-width="1.5"/>
    <circle cx="${x}" cy="${AX}" r="7" fill="${col}"/>`;
    const anchor = x > R - 90 ? "end" : x < L + 90 ? "start" : "middle";
    const amount = it.unknown ? "x = " + money(it.amount) : money(it.amount);
    svg += `<text x="${x}" y="${ty}" text-anchor="${anchor}" font-size="12" font-weight="700" fill="${col}">${esc(it.label)}</text>
    <text x="${x}" y="${ty + 14}" text-anchor="${anchor}" font-size="11" style="fill:var(--ink)">${when(pos(it))} · ${esc(amount)}</text>
    <text x="${x}" y="${ty + 27}" text-anchor="${anchor}" font-size="11" style="fill:var(--muted)">→ ${esc(money(it.value_f))} en foco</text>`;
  });
  svg += `<text x="${L - 20}" y="${H - 4}" font-size="11" fill="#b03a2e">● Deudas / depósitos</text>
  <text x="${L + 150}" y="${H - 4}" font-size="11" fill="#1e7e4f">● Pagos / retiros</text>
  <text x="${L + 220}" y="${H - 4}" font-size="11" style="fill:var(--accent)">⤳ Traslado a la fecha focal</text></svg>`;
  return svg;
}

/* ---------- Procedimiento ---------- */
export function renderProcedure(el, prefix, steps) {
  el.innerHTML = "";
  if (!steps || !steps.length) {
    el.innerHTML = '<div class="empty">Este módulo no genera procedimiento propio. Abra una simulación individual para ver su desarrollo.</div>';
    return;
  }
  steps.forEach((st) => {
    const div = document.createElement("div");
    div.className = "step";
    div.id = `${prefix}-step-${st.n}`;
    let html = `<h3><span class="num">${st.n}</span>Paso ${st.n}. ${esc(st.title)}</h3>`;
    let allAcademic = true;
    st.items.forEach((it) => {
      if (!it.academic) allAcademic = false;
      const cls = it.academic ? " academic" : "";
      if (it.kind === "text") html += `<p class="${cls.trim()}">${richText(it.content)}</p>`;
      else if (it.kind === "math") html += `<div class="math${it.result ? " result" : ""}${cls}">${tex(it.content, true)}</div>`;
      else if (it.kind === "table") {
        html += `<table class="vars${cls}">` + it.rows.map((r) =>
          `<tr><td>${tex(r[0])}</td><td>${richText(r[1])}</td><td>${tex(r[2])}</td></tr>`).join("") + "</table>";
      }
    });
    if (allAcademic) div.classList.add("only-academic");
    div.innerHTML = html;
    el.appendChild(div);
  });
}

/* ---------- Tablas ---------- */
const COLS = {
  loan: [["n", "Cuota", "int"], ["date", "Fecha de pago", "date"], ["opening", "Saldo inicial", "money"], ["interest", "Interés", "money"],
    ["capital", "Abono a capital", "money"], ["payment", "Valor de la cuota", "money"], ["extra", "Abono extra", "money", "extra"], ["insurance", "Seguro", "money", "ins"],
    ["total", "Cuota + seguro", "money", "ins"], ["closing", "Saldo final", "money"]],
  savings: [["n", "Aporte", "int"], ["date", "Fecha", "date"], ["opening", "Saldo inicial", "money"], ["interest", "Interés", "money"],
    ["capital", "Aporte a capital", "money"], ["payment", "Valor de la cuota", "money"], ["closing", "Saldo final", "money"]],
  growth: [["n", "Periodo", "int"], ["date", "Fecha", "date"], ["opening", "Saldo inicial", "money"], ["interest", "Interés", "money"],
    ["closing", "Saldo final", "money"]],
  focal: [["n", "#", "int"], ["label", "Valor", "text"], ["group", "Lado", "text"], ["when", "Momento", "text"],
    ["original", "Valor inicial", "money"], ["amount", "Valor al vencimiento", "money"], ["dir", "Movimiento", "text"], ["t", "t", "num"], ["factor", "Factor (1+i)^t", "num"],
    ["value_f", "Valor en fecha focal", "money"]],
};

function cell(v, type) {
  if (v === null || v === undefined || v === "") return "—";
  if (type === "money") return money(v);
  if (type === "date") return date(v);
  if (type === "num") return num(v, 6);
  return esc(v);
}

export function renderSchedule(el, result) {
  const kind = result.schedule_kind;
  if (!result.schedule || !COLS[kind]) { el.innerHTML = ""; return false; }
  let cols = COLS[kind];
  const hasIns = result.schedule.some((r) => Number(r.insurance) > 0);
  const hasExtra = result.schedule.some((r) => r.extra !== null && r.extra !== undefined);
  cols = cols.filter((c) => (c[3] !== "ins" || hasIns) && (c[3] !== "extra" || hasExtra));
  let h = '<div class="table-wrap"><table class="data"><thead><tr>' +
    cols.map((c) => `<th class="${c[2] === "text" ? "left" : ""}">${c[1]}</th>`).join("") + "</tr></thead><tbody>";
  result.schedule.forEach((r) => {
    h += `<tr class="${r.extra ? "best" : ""}">` + cols.map((c) =>
      `<td class="${c[2] === "text" ? "left" : ""}">${cell(r[c[0]], c[2])}</td>`).join("") + "</tr>";
  });
  el.innerHTML = h + "</tbody></table></div>";
  return true;
}

/* ---------- Extras por módulo ---------- */
export function renderExtras(el, module, result, handlers) {
  el.innerHTML = "";
  if (module === "rates" && result.rates) {
    let h = '<h3 class="sub-title">Equivalencias en todas las modalidades</h3><div class="table-wrap"><table class="data"><thead><tr><th class="left">Sigla</th><th class="left">Nombre completo</th><th class="left">Significado</th><th>Tasa equivalente</th></tr></thead><tbody>';
    result.rates.forEach((r) => {
      h += `<tr class="${r.same ? "best" : ""}"><td class="left"><b>${esc(r.code)}</b></td><td class="left">${esc(r.name)}</td><td class="left">${esc(r.description)}</td><td>` +
        (`<b>${pct(r.value, 8)}</b>` + (r.same ? "" : `<details class="formula"><summary>fórmula</summary><div class="math">${r.latex.map((l) => tex(l, true)).join("")}</div></details>`)) + "</td></tr>";
    });
    el.innerHTML = h + "</tbody></table></div>";
  }
  if (module === "compare" && result.comparison) {
    let h = '<h3 class="sub-title">Diferencias entre simulaciones</h3><div class="table-wrap"><table class="data"><thead><tr>' +
      '<th class="left">Simulación</th><th>Monto</th><th>Tasa</th><th>Cuotas</th><th>Cuota (con seguro)</th><th>Total intereses</th><th>Total a pagar</th><th>Dif. vs. mejor</th><th></th></tr></thead><tbody>';
    result.comparison.forEach((r, i) => {
      h += `<tr class="${r.best ? "best" : ""}"><td class="left">${esc(r.name)}${r.best ? " ★" : ""}</td><td>${money(r.pv)}</td><td>${num(r.rate_value, 4)} % ${esc(r.rate_code)}</td><td>${r.n}</td>` +
        `<td>${money(r.cuota_total)}</td><td>${money(r.total_interest)}</td><td>${money(r.total_paid)}</td><td>${Number(r.diff_paid) ? "+" + money(r.diff_paid) : "—"}</td>` +
        `<td><button type="button" class="btn ghost small" data-open="${i}">Ver procedimiento</button></td></tr>`;
    });
    el.innerHTML = h + "</tbody></table></div>";
    el.querySelectorAll("[data-open]").forEach((b) => b.addEventListener("click", () => handlers.openScenario(result.comparison[Number(b.dataset.open)].inputs)));
  }
}
