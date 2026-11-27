"""Formato compartido por las exportaciones a Excel y PDF."""
import re
from decimal import Decimal

MODULE_TITLES = {"rates": "Tasas de interés", "compound": "Interés compuesto",
                 "annuity": "Anualidades y cuotas", "focal": "Fechas focales", "compare": "Comparación"}

# (clave, encabezado, tipo)  tipo: int | money | text | date | rate | num
SCHEDULE_COLUMNS = {
    "loan": [("n", "Cuota", "int"), ("date", "Fecha de pago", "date"), ("opening", "Saldo inicial", "money"),
             ("interest", "Interés", "money"), ("capital", "Abono a capital", "money"),
             ("payment", "Valor de la cuota", "money"), ("extra", "Abono extra", "money"),
             ("insurance", "Seguro", "money"), ("total", "Cuota + seguro", "money"), ("closing", "Saldo final", "money")],
    "savings": [("n", "Aporte", "int"), ("date", "Fecha", "date"), ("opening", "Saldo inicial", "money"),
                ("interest", "Interés", "money"), ("capital", "Aporte a capital", "money"),
                ("payment", "Valor de la cuota", "money"), ("closing", "Saldo final", "money")],
    "growth": [("n", "Periodo", "int"), ("date", "Fecha", "date"), ("opening", "Saldo inicial", "money"),
               ("interest", "Interés", "money"), ("closing", "Saldo final", "money")],
    "focal": [("n", "#", "int"), ("label", "Valor", "text"), ("group", "Lado", "text"),
              ("when", "Momento", "text"), ("original", "Valor inicial", "money"),
              ("amount", "Valor al vencimiento", "money"), ("t", "t", "num"),
              ("factor", "Factor (1+i)^t", "num"), ("value_f", "Valor en fecha focal", "money")],
}


def schedule_columns(kind, rows):
    """Columnas del plan de pagos; "Abono extra" solo aparece si hay algún abono."""
    cols = SCHEDULE_COLUMNS[kind]
    if not any(r.get("extra") not in (None, "") for r in rows or []):
        cols = [c for c in cols if c[0] != "extra"]
    return cols


def to_num(v):
    return None if v in (None, "") else float(Decimal(str(v)))


def money(v, cur):
    n = to_num(v)
    return "" if n is None else f"{cur} {n:,.2f}"


def card_text(c, cur):
    kind, v = c.get("kind"), c.get("value")
    if v is None:
        return ""
    if kind == "money":
        return money(v, cur)
    if kind == "pct":
        return f"{to_num(v):,.6f} %"
    if kind == "int":
        return str(int(Decimal(str(v))))
    if kind == "num":
        return f"{to_num(v):,.4f}"
    if kind == "months":
        n = to_num(v)
        return f"{n:,.2f} meses ({n / 12:,.2f} años)"
    return str(v)


def clean(text):
    """Quita marcas Markdown/LaTeX simples para exportación."""
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", str(text))
    return t.replace("$", "")


def latex_plain(s):
    s = re.sub(r"\\text\{([^}]*)\}", r"\1", s)
    s = s.replace("\\dfrac", "").replace("\\times", "×").replace("\\cdot", "·").replace("\\,", " ")
    s = s.replace("\\%", "%").replace("\\left", "").replace("\\right", "").replace("\\ ", " ")
    s = s.replace("\\Rightarrow", "=>").replace("\\Longleftrightarrow", "<=>").replace("\\to", "->")
    s = s.replace("\\ddot", "").replace("\\ln", "ln").replace("\\sum", "Σ").replace("\\quad", "  ")
    s = s.replace("\\;", " ").replace("\\div", "÷").replace("{", "").replace("}", "")
    return s


def procedure_lines(result):
    """Lista plana de (tipo, texto) para exportar el procedimiento."""
    out = []
    for st in result.get("procedure") or []:
        out.append(("h", f"Paso {st['n']}. {st['title']}"))
        for it in st["items"]:
            if it["kind"] == "text":
                out.append(("t", clean(it["content"])))
            elif it["kind"] == "math":
                out.append(("m", latex_plain(it["content"])))
            else:
                for r in it["rows"]:
                    out.append(("t", f"{latex_plain(r[0])}: {clean(r[1])} = {latex_plain(r[2])}"))
    return out
