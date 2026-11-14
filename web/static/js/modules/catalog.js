import { get, post } from "../api.js";
import { esc } from "../format.js";

let items = [];

function rowHTML(s, i) {
  return `<tr data-i="${i}">
    <td><input class="c-code" value="${esc(s.code)}" size="5"></td>
    <td><input class="c-name" value="${esc(s.name)}"></td>
    <td><select class="c-kind"><option value="effective"${s.kind === "effective" ? " selected" : ""}>Efectiva</option><option value="nominal"${s.kind === "nominal" ? " selected" : ""}>Nominal anual</option></select></td>
    <td><select class="c-months">${[1, 2, 3, 4, 6, 12].map((m) => `<option value="${m}"${s.months === m ? " selected" : ""}>${m}</option>`).join("")}</select></td>
    <td><input type="checkbox" class="c-ant"${s.anticipated ? " checked" : ""}></td>
    <td><input type="checkbox" class="c-pend"${s.pending ? " checked" : ""}></td>
    <td class="left"><input class="c-note" value="${esc(s.note || "")}" placeholder="Nota / significado"></td>
    <td><button class="btn ghost small c-del">✕</button></td></tr>`;
}

function collect(tbody) {
  return [...tbody.querySelectorAll("tr")].map((tr) => ({
    code: tr.querySelector(".c-code").value, name: tr.querySelector(".c-name").value,
    kind: tr.querySelector(".c-kind").value, months: Number(tr.querySelector(".c-months").value),
    anticipated: tr.querySelector(".c-ant").checked, pending: tr.querySelector(".c-pend").checked,
    note: tr.querySelector(".c-note").value }));
}

export async function initCatalog(onChange) {
  const tbody = document.querySelector("#catalogTable tbody");
  const msg = document.getElementById("catMsg");
  const draw = () => { tbody.innerHTML = items.map(rowHTML).join(""); };
  items = await get("/api/catalog");
  draw();
  onChange(items);
  tbody.addEventListener("click", (e) => {
    if (e.target.classList.contains("c-del")) {
      items = collect(tbody);
      items.splice(Number(e.target.closest("tr").dataset.i), 1);
      draw();
    }
  });
  document.getElementById("catAdd").addEventListener("click", () => {
    items = collect(tbody);
    items.push({ code: "", name: "", kind: "effective", months: 1, anticipated: false, pending: false, note: "" });
    draw();
  });
  document.getElementById("catSave").addEventListener("click", async () => {
    const { ok, data } = await post("/api/catalog", { items: collect(tbody) });
    if (ok) {
      items = data; draw(); onChange(items);
      msg.className = "msg ok"; msg.textContent = "Catálogo guardado. Las listas de tasas se actualizaron.";
    } else {
      msg.className = "msg error";
      msg.innerHTML = Object.values(data.errors || { _: data.message }).map((m) => `<div>• ${esc(m)}</div>`).join("");
    }
  });
  document.getElementById("catReset").addEventListener("click", async () => {
    const { ok, data } = await post("/api/catalog/reset", {});
    if (ok) { items = data; draw(); onChange(items); msg.className = "msg ok"; msg.textContent = "Catálogo restaurado."; }
  });
}
