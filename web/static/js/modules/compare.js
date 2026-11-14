import { readForm, todayISO } from "../forms.js";
import { esc } from "../format.js";
import { setupModule } from "./base.js";

function rowHTML(it) {
  return `<div class="item-row">
    <button type="button" class="del" title="Quitar">✕</button>
    <input class="full cp-name" placeholder="Nombre" value="${esc(it.name)}">
    <input class="cp-term" type="number" min="1" step="any" placeholder="Plazo (meses)" value="${esc(it.term)}">
    <input class="cp-pv" type="number" min="0" step="any" placeholder="Monto (opcional)" value="${esc(it.pv || "")}">
    <input class="cp-rate full" type="number" min="0" step="any" placeholder="Tasa % (opcional, mismo tipo)" value="${esc(it.rate || "")}">
  </div>`;
}

export function initCompare() {
  const list = document.getElementById("compareItems");
  const add = (it) => list.insertAdjacentHTML("beforeend", rowHTML(it));
  [12, 24, 36].forEach((m, i) => add({ name: `Simulación ${i + 1}`, term: String(m) }));
  document.getElementById("addCompare").addEventListener("click", () =>
    add({ name: `Simulación ${list.children.length + 1}`, term: "" }));
  list.addEventListener("click", (e) => {
    if (e.target.classList.contains("del")) {
      e.target.closest(".item-row").remove();
      list.dispatchEvent(new Event("input", { bubbles: true }));
    }
  });
  const build = (f) => ({
    base: readForm(f),
    scenarios: [...list.querySelectorAll(".item-row")].map((r) => ({
      name: r.querySelector(".cp-name").value, term_value: r.querySelector(".cp-term").value,
      pv: r.querySelector(".cp-pv").value, rate_value: r.querySelector(".cp-rate").value })),
  });
  const ctl = setupModule({
    module: "compare", buildPayload: build,
    onOpenScenario: (inputs) => window.dispatchEvent(new CustomEvent("go-annuity", { detail: inputs })),
  });
  ctl.form.elements.start_date.value = todayISO();
  ctl.run();
  return ctl;
}
