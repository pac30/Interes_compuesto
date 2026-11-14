export async function post(url, body) {
  let res;
  try {
    res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  } catch (e) {
    return { ok: false, data: { message: "No se pudo conectar con el servidor.", errors: {} } };
  }
  let data = {};
  try { data = await res.json(); } catch (e) { data = { message: "Respuesta inválida del servidor." }; }
  return { ok: res.ok, data, status: res.status };
}

export async function get(url) {
  const res = await fetch(url);
  return res.json();
}

export async function download(url, body, filename) {
  const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!res.ok) {
    let msg = "No se pudo generar el archivo.";
    try { msg = (await res.json()).message || msg; } catch (e) { /* noop */ }
    throw new Error(msg);
  }
  const blob = await res.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}
