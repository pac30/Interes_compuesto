import io
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .common import SCHEDULE_COLUMNS, card_text, procedure_lines, to_num

NAVY = colors.HexColor("#1F3A5F")


def _cell(v, typ):
    if v in (None, ""):
        return ""
    if typ == "money":
        return f"{to_num(v):,.2f}"
    if typ == "num":
        return f"{to_num(v):,.6f}"
    return str(v)


def _table(data, widths=None, font=8):
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), font), ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F6FA")]),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    return t


def build(result, meta):
    cur = meta["currency"]
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=1.2 * cm, rightMargin=1.2 * cm,
                            topMargin=1.2 * cm, bottomMargin=1.2 * cm, title=meta["title"])
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], textColor=NAVY, fontSize=18)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=NAVY)
    body = ParagraphStyle("b", parent=ss["BodyText"], fontSize=9, leading=12)
    mono = ParagraphStyle("m", parent=body, fontName="Courier", fontSize=8, leftIndent=14, textColor=colors.HexColor("#333"))
    story = [Paragraph(f"Simulador de matemáticas financieras — {escape(meta['title'])}", h1),
             Paragraph(f"Moneda: {cur}", body), Spacer(1, 8), Paragraph("Resultados", h2)]
    rows = [["Concepto", "Valor"]] + [[c["label"], card_text(c, cur)] for c in result.get("cards") or []]
    story.append(_table(rows, [9 * cm, 9 * cm], 9))
    for w in result.get("warnings") or []:
        story.append(Paragraph("Aviso: " + escape(w), body))

    if result.get("comparison"):
        story += [Spacer(1, 10), Paragraph("Comparación de simulaciones", h2)]
        data = [["Simulación", "Monto", "Cuotas", "Cuota", "Total intereses", "Total a pagar", "Dif. vs mejor"]]
        for x in result["comparison"]:
            data.append([x["name"], _cell(x["pv"], "money"), x["n"], _cell(x["cuota_total"], "money"),
                         _cell(x["total_interest"], "money"), _cell(x["total_paid"], "money"),
                         _cell(x["diff_paid"], "money")])
        story.append(_table(data))

    if result.get("rates"):
        story += [Spacer(1, 10), Paragraph("Equivalencias de tasas", h2)]
        data = [["Sigla", "Nombre", "Valor (%)"]]
        for x in result["rates"]:
            data.append([x["code"], x["name"], "por configurar" if x["value"] is None else f"{to_num(x['value']):,.8f}"])
        story.append(_table(data, [3 * cm, 12 * cm, 5 * cm], 9))

    kind = result.get("schedule_kind")
    if result.get("schedule") and kind in SCHEDULE_COLUMNS:
        cols = SCHEDULE_COLUMNS[kind]
        story += [Spacer(1, 10), Paragraph("Tabla", h2)]
        data = [[h for _, h, _ in cols]] + [[_cell(r.get(k), t) for k, _, t in cols] for r in result["schedule"]]
        story.append(_table(data))

    lines = procedure_lines(result)
    if lines:
        story += [Spacer(1, 12), Paragraph("Procedimiento matemático", h2)]
        for typ, txt in lines:
            if typ == "h":
                story.append(Spacer(1, 6))
                story.append(Paragraph(f"<b>{escape(txt)}</b>", body))
            elif typ == "m":
                story.append(Paragraph(escape(txt), mono))
            else:
                story.append(Paragraph(escape(txt), body))
    doc.build(story)
    buf.seek(0)
    return buf
