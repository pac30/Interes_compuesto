import { get } from "../api.js";
import { readForm, applyConditions, setFormValues } from "../forms.js";
import { esc } from "../format.js";
import { setupModule } from "./base.js";

const DEFAULTS = [
  { label: "Deuda 1", group: "deuda", period: "3", date: "2025-03-01", amount: "3000000" },
  { label: "Deuda 2", group: "deuda", period: "9", date: "2025-09-01", amount: "4000000" },
  { label: "Pago único", group: "pago", period: "12", date: "2026-01-01", amount: "" },
];

// Ejercicios de ejemplo (enunciados resumidos). Mes 0 = hoy.
const P = (label, group, period, amount = "", own = {}) => ({ label, group, period: String(period), amount: String(amount), ...own });
const PRESETS = [
  { name: "1 · Depósito y retiros: saldo a los 6 meses",
    text: "Deposita $100.000 al 30 % anual (EA); al mes 1 retira $20.000 y al mes 3 retira $30.000. ¿Saldo en el mes 6?",
    form: { time_mode: "periods", period_months: "1", focal_period: "6", rate_value: "30", rate_code: "EA" },
    items: [P("Depósito", "deuda", 0, 100000), P("Retiro 1", "pago", 1, 20000), P("Retiro 2", "pago", 3, 30000), P("Saldo", "pago", 6)] },
  { name: "2 · Sebastián: pago único dentro de un año",
    text: "Debe Q10.000 que vencen en 6 meses (préstamo a 18 meses al 12 %) y Q25.000 sin intereses a 9 meses. Paga Q20.000 hoy y el resto en un pago único a 12 meses. Rendimiento 10 %, foco en 12 meses. (Interés compuesto, tasas como EA.)",
    form: { time_mode: "periods", period_months: "1", focal_period: "12", rate_value: "10", rate_code: "EA" },
    items: [P("Préstamo Q10.000", "deuda", 6, 10000, { own_rate: "12", own_rate_code: "EA", own_term_months: "18" }),
      P("Deuda sin intereses", "deuda", 9, 25000), P("Pago inmediato", "pago", 0, 20000), P("Pago único", "pago", 12)] },
  { name: "3 · Deuda de $320.000 en el periodo 3",
    text: "Se paga con $100.000 hoy, $200.000 en el periodo 5 y el saldo en el periodo 3. Tasa 3 % efectiva del periodo.",
    form: { time_mode: "periods", period_months: "1", focal_period: "3", rate_value: "3", rate_code: "EM" },
    items: [P("Deuda", "deuda", 3, 320000), P("Pago inmediato", "pago", 0, 100000), P("Pago periodo 5", "pago", 5, 200000), P("Saldo", "pago", 3)] },
  { name: "4 · Empresa xyz: saldo al mes 12",
    text: "Deuda de $10.000.000 a 12 meses al 2 % mensual; paga $7.000.000 al final del mes 5. ¿Saldo al mes 12?",
    form: { time_mode: "periods", period_months: "1", focal_period: "12", rate_value: "2", rate_code: "EM" },
    items: [P("Préstamo", "deuda", 0, 10000000), P("Abono mes 5", "pago", 5, 7000000), P("Saldo", "pago", 12)] },
  { name: "5 · Pablo Pérez: saldo del auto en el mes 10",
    text: "Auto de $60.000.000. Pagos: $15.000.000 hoy y en el mes 5; $10.000.000 en los meses 1 y 12; el saldo en el mes 10. Tasa 24 % nominal mes vencido.",
    form: { time_mode: "periods", period_months: "1", focal_period: "10", rate_value: "24", rate_code: "MV" },
    items: [P("Valor del auto", "deuda", 0, 60000000), P("Cuota inicial", "pago", 0, 15000000), P("Pago mes 1", "pago", 1, 10000000),
      P("Pago mes 5", "pago", 5, 15000000), P("Saldo mes 10", "pago", 10), P("Pago mes 12", "pago", 12, 10000000)] },
  { name: "6 · Angelo Pulido: tres cuotas iguales (oct, nov, dic)",
    text: "Plan original: $600.000 en enero, $1.500.000 en febrero y $800.000 en agosto (meses 1, 2 y 8). Se reemplaza por tres cuotas iguales en los meses 10, 11 y 12. Tasa 24 % nominal trimestral anticipada.",
    form: { time_mode: "periods", period_months: "1", focal_period: "12", rate_value: "24", rate_code: "TA" },
    items: [P("Pago enero", "deuda", 1, 600000), P("Pago febrero", "deuda", 2, 1500000), P("Pago agosto", "deuda", 8, 800000),
      P("Cuota octubre", "pago", 10), P("Cuota noviembre", "pago", 11), P("Cuota diciembre", "pago", 12)] },
];

let rateOptions = "";

function rowHTML(it) {
  const hasOwn = it.own_rate !== undefined && it.own_rate !== "";
  const opts = rateOptions.replace(`value="${esc(it.own_rate_code || "EA")}"`, `value="${esc(it.own_rate_code || "EA")}" selected`);
  return `<div class="item-row">
    <button type="button" class="del" title="Quitar">✕</button>
    <input class="full it-label" placeholder="Nombre" value="${esc(it.label)}">
    <select class="it-group"><option value="deuda"${it.group === "deuda" ? " selected" : ""}>Deuda / depósito</option><option value="pago"${it.group === "pago" ? " selected" : ""}>Pago / retiro</option></select>
    <input class="it-period" type="number" min="0" step="any" placeholder="Periodo (0 = hoy)" title="Periodo" value="${esc(it.period ?? "")}">
    <input class="it-date" type="date" value="${esc(it.date ?? "")}">
    <input class="it-amount full" type="number" min="0" step="any" placeholder="Valor (vacío = incógnita x)" value="${esc(it.amount ?? "")}">
    <details class="full it-own"${hasOwn ? " open" : ""}><summary>Intereses propios (opcional)</summary>
      <div class="own-grid">
        <input class="it-own-rate" type="number" min="0" step="any" placeholder="Tasa %" value="${esc(it.own_rate ?? "")}">
        <select class="it-own-code">${opts}</select>
        <input class="it-own-term" type="number" min="0" step="any" placeholder="Plazo original (meses)" value="${esc(it.own_term_months ?? "")}">
      </div></details>
  </div>`;
}

export function initFocal() {
  const list = document.getElementById("focalItems");
  const form = list.closest("form");
  const add = (it) => list.insertAdjacentHTML("beforeend", rowHTML(it));
  const syncMode = () => { list.dataset.mode = form.elements.time_mode.value; };

  const build = (f) => ({
    ...readForm(f),
    items: [...list.querySelectorAll(".item-row")].map((r) => {
      const it = { label: r.querySelector(".it-label").value, group: r.querySelector(".it-group").value,
        period: r.querySelector(".it-period").value, date: r.querySelector(".it-date").value,
        amount: r.querySelector(".it-amount").value };
      const own = r.querySelector(".it-own-rate").value;
      if (own !== "") Object.assign(it, { own_rate: own, own_rate_code: r.querySelector(".it-own-code").value,
        own_term_months: r.querySelector(".it-own-term").value });
      return it;
    }),
  });
  const ctl = setupModule({ module: "focal", buildPayload: build });

  // las filas necesitan el catálogo para el selector de la tasa propia
  get("/api/catalog").then((cat) => {
    rateOptions = cat.map((s) => `<option value="${esc(s.code)}">${esc(s.code)}</option>`).join("");
    DEFAULTS.forEach(add);
    syncMode();
    ctl.run();
  });

  const preset = document.getElementById("focalPreset");
  preset.innerHTML += PRESETS.map((p, k) => `<option value="${k}">${esc(p.name)}</option>`).join("");
  preset.addEventListener("change", () => {
    const p = PRESETS[Number(preset.value)];
    document.getElementById("focalPresetText").textContent = p ? p.text : "";
    if (!p) return;
    setFormValues(form, p.form);
    applyConditions(form);
    list.innerHTML = "";
    p.items.forEach(add);
    syncMode();
    ctl.run();
  });
  form.elements.time_mode.addEventListener("change", syncMode);
  document.getElementById("addFocalItem").addEventListener("click", () => {
    add({ label: `Valor ${list.children.length + 1}`, group: "deuda", period: "", date: "", amount: "" });
  });
  list.addEventListener("click", (e) => {
    if (e.target.classList.contains("del")) {
      e.target.closest(".item-row").remove();
      list.dispatchEvent(new Event("input", { bubbles: true }));
    }
  });
  return ctl;
}
