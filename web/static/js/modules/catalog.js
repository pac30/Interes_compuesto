import { get } from "../api.js";
import { esc } from "../format.js";

const PER = { 1: "mensual", 2: "bimestral", 3: "trimestral", 4: "cuatrimestral", 6: "semestral", 12: "anual" };

function rowHTML(s) {
  return `<tr><td class="left"><b>${esc(s.code)}</b></td><td class="left">${esc(s.name)}</td>
    <td>${s.kind === "effective" ? "Efectiva (periódica)" : "Nominal anual"}</td>
    <td>${esc(PER[s.months])}</td><td>${s.kind === "nominal" ? s.m : "—"}</td>
    <td>${s.anticipated ? "Anticipada" : "Vencida"}</td></tr>`;
}

// Catálogo fijo (solo lectura): alimenta las listas de tasas y la tabla de referencia.
export async function initCatalog(onChange) {
  const items = await get("/api/catalog");
  document.querySelector("#catalogTable tbody").innerHTML = items.map(rowHTML).join("");
  onChange(items);
}
