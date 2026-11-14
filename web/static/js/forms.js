// Utilidades de formularios: lectura, campos condicionales, errores y selects de tasas.
import { esc } from "./format.js";

export function readForm(form) {
  const out = {};
  new FormData(form).forEach((v, k) => { out[k] = v; });
  return out;
}

export function applyConditions(form) {
  const get = (name) => {
    const el = form.elements[name];
    return el ? el.value : undefined;
  };
  // varias pasadas: un campo oculto puede depender de otro que también se oculta
  for (let pass = 0; pass < 2; pass++) {
    form.querySelectorAll("[data-when]").forEach((node) => {
      const ok = node.dataset.when.split(";").every((cond) => {
        const [name, values] = cond.split("=");
        const current = get(name.trim());
        const owner = form.elements[name.trim()];
        if (owner && owner.closest && owner.closest(".hidden")) return false;
        return values.split("|").includes(current);
      });
      node.classList.toggle("hidden", !ok);
      node.querySelectorAll("input,select,textarea").forEach((i) => { i.disabled = !ok; });
    });
  }
  // etiqueta especial: escenario C cambia el texto del tipo de tasa
  const sc = form.elements["scenario"];
  const lab = form.querySelector("[data-when-label]");
  if (sc && lab) lab.textContent = sc.value === "C" ? "Expresar tasa como" : "Tipo de tasa";
}

export function clearErrors(form) {
  form.querySelectorAll(".invalid").forEach((e) => e.classList.remove("invalid"));
  form.querySelectorAll(".field-error").forEach((e) => e.remove());
}

export function showErrors(form, errors) {
  clearErrors(form);
  const general = [];
  Object.entries(errors || {}).forEach(([key, msg]) => {
    const el = form.elements[key];
    if (el && el.classList) {
      el.classList.add("invalid");
      const span = document.createElement("div");
      span.className = "field-error";
      span.textContent = msg;
      (el.closest(".field") || el.parentNode).appendChild(span);
    } else {
      general.push(msg);
    }
  });
  return general;
}

export function populateRateSelects(catalog) {
  document.querySelectorAll("select.rate-select").forEach((sel) => {
    const prev = sel.value || sel.dataset.default;
    sel.innerHTML = catalog.map((s) =>
      `<option value="${esc(s.code)}">${esc(s.code)} — ${esc(s.name)}${s.pending ? " (por configurar)" : ""}</option>`).join("");
    if (catalog.some((s) => s.code === prev)) sel.value = prev;
    updateRateDesc(sel, catalog);
  });
}

export function updateRateDesc(sel, catalog) {
  const box = sel.closest("fieldset")?.querySelector(".rate-desc");
  if (!box) return;
  const s = catalog.find((x) => x.code === sel.value);
  box.textContent = s ? (s.pending ? "⚠ " + s.note : `${s.description}.${s.note ? " " + s.note : ""}`) : "";
}

export function setFormValues(form, values) {
  Object.entries(values).forEach(([k, v]) => {
    const el = form.elements[k];
    if (el && v !== undefined && v !== null) el.value = v;
  });
  applyConditions(form);
}

export function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
