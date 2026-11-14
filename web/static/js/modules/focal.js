import { readForm } from "../forms.js";
import { esc } from "../format.js";
import { setupModule } from "./base.js";

const DEFAULTS = [
  { label: "Deuda 1", group: "deuda", date: "2025-03-01", amount: "3000000" },
  { label: "Deuda 2", group: "deuda", date: "2025-09-01", amount: "4000000" },
  { label: "Pago único", group: "pago", date: "2025-06-01", amount: "" },
];

function rowHTML(it) {
  return `<div class="item-row">
    <button type="button" class="del" title="Quitar">✕</button>
    <input class="full it-label" placeholder="Nombre" value="${esc(it.label)}">
    <select class="it-group"><option value="deuda"${it.group === "deuda" ? " selected" : ""}>Deuda original</option><option value="pago"${it.group === "pago" ? " selected" : ""}>Pago nuevo</option></select>
    <input class="it-date" type="date" value="${esc(it.date)}">
    <input class="it-amount full" type="number" min="0" step="any" placeholder="Valor (vacío = incógnita)" value="${esc(it.amount)}">
  </div>`;
}

export function initFocal() {
  const list = document.getElementById("focalItems");
  const add = (it) => list.insertAdjacentHTML("beforeend", rowHTML(it));
  DEFAULTS.forEach(add);
  document.getElementById("addFocalItem").addEventListener("click", () => {
    add({ label: `Obligación ${list.children.length + 1}`, group: "deuda", date: "", amount: "" });
  });
  list.addEventListener("click", (e) => {
    if (e.target.classList.contains("del")) {
      e.target.closest(".item-row").remove();
      list.dispatchEvent(new Event("input", { bubbles: true }));
    }
  });
  const build = (f) => ({
    ...readForm(f),
    items: [...list.querySelectorAll(".item-row")].map((r) => ({
      label: r.querySelector(".it-label").value, group: r.querySelector(".it-group").value,
      date: r.querySelector(".it-date").value, amount: r.querySelector(".it-amount").value })),
  });
  const ctl = setupModule({ module: "focal", buildPayload: build });
  ctl.run();
  return ctl;
}
