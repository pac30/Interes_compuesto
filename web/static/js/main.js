import { download } from "./api.js";
import { state, store } from "./format.js";
import { populateRateSelects, setFormValues, updateRateDesc } from "./forms.js";
import { initAnnuity } from "./modules/annuity.js";
import { initCatalog } from "./modules/catalog.js";
import { initCompare } from "./modules/compare.js";
import { initCompound } from "./modules/compound.js";
import { initFocal } from "./modules/focal.js";
import { initRates } from "./modules/rates.js";

const controllers = {};
let catalog = [];
let current = "annuity";

function toast(msg) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 2600);
}

function go(module) {
  current = module;
  document.querySelectorAll(".nav-item").forEach((b) => b.classList.toggle("active", b.dataset.module === module));
  document.querySelectorAll(".module").forEach((s) => s.classList.toggle("active", s.id === `mod-${module}`));
  document.getElementById("pageTitle").textContent = document.getElementById(`mod-${module}`).dataset.title;
  document.getElementById("exportBox").classList.toggle("hidden", module === "catalog");
  document.getElementById("sidebar").classList.remove("open");
  window.scrollTo({ top: 0 });
  const c = controllers[module];
  if (c) c.render();
}

function applyView(view) {
  state.view = view;
  document.body.classList.toggle("simple", view === "simple");
  document.querySelectorAll("#viewToggle button").forEach((b) => b.classList.toggle("active", b.dataset.view === view));
  store("fm-view", view);
}

function rerenderAll() { Object.values(controllers).forEach((c) => c.render()); }

async function boot() {
  if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
    document.documentElement.dataset.theme = "dark";
  }
  state.currency = store("fm-currency") || "COP";
  document.getElementById("currency").value = state.currency;
  applyView(store("fm-view") || "academic");

  // catálogo primero: los selects de tasa deben existir antes de simular
  await initCatalog((items) => {
    catalog = items;
    populateRateSelects(items);
  });
  document.querySelectorAll("select.rate-select").forEach((sel) =>
    sel.addEventListener("change", () => updateRateDesc(sel, catalog)));

  controllers.annuity = initAnnuity();
  controllers.compound = initCompound();
  controllers.rates = initRates();
  controllers.focal = initFocal();
  controllers.compare = initCompare();

  // cuando cambia el catálogo se vuelve a simular lo que esté abierto
  const reCalc = () => Object.values(controllers).forEach((c) => c.run());
  document.getElementById("catSave").addEventListener("click", () => setTimeout(reCalc, 400));
  document.getElementById("catReset").addEventListener("click", () => setTimeout(reCalc, 400));

  window.addEventListener("go-annuity", (e) => {
    go("annuity");
    window.dispatchEvent(new CustomEvent("open-annuity", { detail: e.detail }));
  });

  document.querySelectorAll(".nav-item").forEach((b) => b.addEventListener("click", () => go(b.dataset.module)));
  document.getElementById("menuBtn").addEventListener("click", () => document.getElementById("sidebar").classList.toggle("open"));
  document.getElementById("currency").addEventListener("change", (e) => {
    state.currency = e.target.value;
    store("fm-currency", state.currency);
    rerenderAll();
  });
  document.querySelectorAll("#viewToggle button").forEach((b) => b.addEventListener("click", () => applyView(b.dataset.view)));
  document.querySelectorAll("[data-export]").forEach((b) => b.addEventListener("click", async () => {
    const entry = state.last[current];
    if (!entry) { toast("Primero realice una simulación."); return; }
    const fmt = b.dataset.export;
    try {
      await download(`/api/export/${fmt}`, { module: current, payload: entry.payload, currency: state.currency },
        `simulacion_${current}.${fmt}`);
      toast(`Archivo ${fmt.toUpperCase()} generado.`);
    } catch (err) { toast(err.message); }
  }));
}

boot();
