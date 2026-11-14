import io
from datetime import date

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .common import SCHEDULE_COLUMNS, card_text, procedure_lines, to_num

HEAD_FILL = PatternFill("solid", fgColor="1F3A5F")
HEAD_FONT = Font(bold=True, color="FFFFFF")


def _header(ws, row, titles):
    for c, t in enumerate(titles, 1):
        cell = ws.cell(row=row, column=c, value=t)
        cell.fill, cell.font = HEAD_FILL, HEAD_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def _widths(ws, widths):
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w


def build(result, meta):
    cur = meta["currency"]
    wb = Workbook()
    ws = wb.active
    ws.title = "Resumen"
    ws["A1"] = f"Simulador de matemáticas financieras — {meta['title']}"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = f"Moneda: {cur}"
    _header(ws, 4, ["Concepto", "Valor"])
    r = 5
    for c in result.get("cards") or []:
        ws.cell(row=r, column=1, value=c["label"])
        ws.cell(row=r, column=2, value=card_text(c, cur))
        r += 1
    for w in result.get("warnings") or []:
        r += 1
        ws.cell(row=r, column=1, value="Aviso: " + w)
    _widths(ws, [42, 38])

    kind = result.get("schedule_kind")
    if result.get("schedule") and kind in SCHEDULE_COLUMNS:
        cols = SCHEDULE_COLUMNS[kind]
        wt = wb.create_sheet("Tabla")
        _header(wt, 1, [h for _, h, _ in cols])
        for ri, row in enumerate(result["schedule"], 2):
            for ci, (key, _, typ) in enumerate(cols, 1):
                v = row.get(key)
                if typ in ("money", "num", "int") and v not in (None, ""):
                    v = to_num(v)
                elif typ == "date" and v:
                    v = date.fromisoformat(v)
                cell = wt.cell(row=ri, column=ci, value=v)
                if typ == "money":
                    cell.number_format = "#,##0.00"
                elif typ == "num":
                    cell.number_format = "0.000000"
                elif typ == "date":
                    cell.number_format = "yyyy-mm-dd"
        wt.freeze_panes = "A2"
        _widths(wt, [14] + [18] * (len(cols) - 1))

    if result.get("comparison"):
        wc = wb.create_sheet("Comparación")
        heads = ["Simulación", "Monto", "Tasa", "Tipo", "EA %", "Cuotas", "Cuota", "Seguro", "Cuota + seguro",
                 "Total intereses", "Total a pagar", "Diferencia vs mejor"]
        _header(wc, 1, heads)
        for ri, x in enumerate(result["comparison"], 2):
            vals = [x["name"], to_num(x["pv"]), to_num(x["rate_value"]), x["rate_code"], to_num(x["ea"]), x["n"],
                    to_num(x["cuota"]), to_num(x["insurance"]), to_num(x["cuota_total"]),
                    to_num(x["total_interest"]), to_num(x["total_paid"]), to_num(x["diff_paid"])]
            for ci, v in enumerate(vals, 1):
                wc.cell(row=ri, column=ci, value=v)
        _widths(wc, [18] + [16] * 11)

    if result.get("rates"):
        wr = wb.create_sheet("Equivalencias")
        _header(wr, 1, ["Sigla", "Nombre", "Descripción", "Valor equivalente (%)"])
        for ri, x in enumerate(result["rates"], 2):
            for ci, v in enumerate([x["code"], x["name"], x["description"],
                                    to_num(x["value"]) if x["value"] is not None else "por configurar"], 1):
                wr.cell(row=ri, column=ci, value=v)
        _widths(wr, [10, 40, 52, 22])

    lines = procedure_lines(result)
    if lines:
        wp = wb.create_sheet("Procedimiento")
        for ri, (typ, txt) in enumerate(lines, 1):
            cell = wp.cell(row=ri, column=1, value=txt)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            if typ == "h":
                cell.font = Font(bold=True, size=12)
            elif typ == "m":
                cell.font = Font(name="Consolas")
        wp.column_dimensions["A"].width = 130

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf
