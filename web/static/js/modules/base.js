// Controlador genérico de módulo: formulario -> API -> ventanas de resultado / procedimiento / tabla.
import { post } from "../api.js";
import { state } from "../format.js";
import { applyConditions, clearErrors, readForm, showErrors } from "../forms.js";
import { renderCards, renderCharts, renderExtras, renderProcedure, renderSchedule, renderWarnings } from "../render.js";

export function setupModule({ module, buildPayload, onOpenScenario }) {
  const host = document.querySelector(`.results-host[data-module="${module}"]`);
  const section = host.closest(".module");
  const form = section.querySelector("form");
  host.appendChild(document.getElementById("tpl-results").content.cloneNode(true));
  const root = host.querySelector(".results");
  const msg = root.querySelector(".msg");
  const panes = {};
  root.querySelectorAll(".pane").forEach((p) => { panes[p.dataset.pane] = p; });
  const tabs = {};
  root.querySelectorAll(".tab").forEach((t) => { tabs[t.dataset.tab] = t; });
  const tableLabel = host.dataset.tableTab;
  if (tableLabel) tabs.table.textContent = tableLabel;

  function showTab(name) {
    Object.entries(panes).forEach(([k, p]) => p.classList.toggle("hidden", k !== name));
    Object.entries(tabs).forEach(([k, t]) => t.classList.toggle("active", k === name));
  }
  Object.entries(tabs).forEach(([k, t]) => t.addEventListener("click", () => showTab(k)));

  function goToStep(n) {
    showTab("proc");
    const el = document.getElementById(`${module}-step-${n}`);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
      el.classList.add("flash");
      setTimeout(() => el.classList.remove("flash"), 1600);
    }
  }

  function render() {
    const entry = state.last[module];
    if (!entry || !entry.result) return;
    const r = entry.result;
    panes.result.innerHTML = '<div class="warnings"></div><div class="cards"></div><div class="extra"></div><div class="charts"></div>';
    renderWarnings(panes.result.querySelector(".warnings"), r.warnings);
    renderCards(panes.result.querySelector(".cards"), r.cards || [], goToStep);
    renderExtras(panes.result.querySelector(".extra"), module, r, { openScenario: onOpenScenario });
    renderCharts(panes.result.querySelector(".charts"), module, r.chart);
    renderProcedure(panes.proc, module, r.procedure);
    tabs.proc.classList.toggle("hidden", !(r.procedure && r.procedure.length));
    const has = renderSchedule(panes.table, r);
    tabs.table.classList.toggle("hidden", !has);
    if (panes.table.classList.contains("hidden") === false && !has) showTab("result");
  }

  async function run(opts = {}) {
    applyConditions(form);
    const payload = buildPayload(form);
    root.classList.add("loading");
    const { ok, data } = await post(`/api/${module}`, payload);
    root.classList.remove("loading");
    if (!ok) {
      const general = showErrors(form, data.errors);
      msg.className = "msg " + (data.needs_info ? "needs" : "error");
      msg.innerHTML = (data.needs_info ? "<b>Falta información:</b> " : "<b>Revise los datos:</b> ") +
        (Object.keys(data.errors || {}).length ? Object.values(data.errors).map((m) => `<div>• ${m}</div>`).join("") : data.message || "Error");
      void general;
      return;
    }
    clearErrors(form);
    msg.className = "msg"; msg.innerHTML = "";
    state.last[module] = { payload, result: data };
    render();
    if (opts.focus) showTab("result");
  }

  let timer = null;
  const debounced = () => { clearTimeout(timer); timer = setTimeout(run, 450); };
  form.addEventListener("submit", (e) => { e.preventDefault(); run({ focus: true }); });
  form.addEventListener("input", () => { applyConditions(form); debounced(); });
  form.addEventListener("change", () => { applyConditions(form); debounced(); });
  applyConditions(form);
  return { run, render, form, showTab };
}
