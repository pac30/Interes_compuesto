"""Interés compuesto: escenarios A (FV), B (PV), C (tasa) y D (tiempo)."""
import math

from . import rates as R
from .dates import add_months, months_between
from .precision import D, dpow, dln
from .steps import Procedure, N, M, P, T
from .validation import Reader, ValidationError

SCENARIOS = {
    "A": "Calcular el valor futuro (FV)",
    "B": "Calcular el capital inicial (PV)",
    "C": "Calcular la tasa de interés",
    "D": "Calcular el tiempo (número de periodos)",
}


def future_value(pv, i, n):
    return pv * dpow(1 + i, n)


def present_value(fv, i, n):
    return fv / dpow(1 + i, n)


def rate_needed(pv, fv, n):
    return dpow(fv / pv, 1 / D(n)) - 1


def periods_needed(pv, fv, i):
    return dln(fv / pv) / dln(1 + i)


def run(data):
    cat = R.load_catalog()
    rd = Reader(data)
    sc = rd.choice("scenario", "Escenario", list(SCENARIOS))
    rd.done()
    needs_pv = sc in ("A", "C", "D")
    needs_fv = sc in ("B", "C", "D")
    needs_rate = sc in ("A", "B", "D")
    needs_term = sc in ("A", "B", "C")

    pv = rd.dec("pv", "Capital inicial (PV)", required=needs_pv, gt=0)
    fv = rd.dec("fv", "Valor futuro (FV)", required=needs_fv, gt=0)
    rate_val = rd.dec("rate_value", "Tasa de interés", required=needs_rate, min=0)
    code = rd.text("rate_code")
    if not code:
        rd.errors["rate_code"] = "Tipo de tasa: seleccione una opción."
    unit = rd.choice("term_unit", "Unidad del plazo", ["months", "years"], "months")
    term = rd.dec("term_value", "Plazo", required=False, gt=0)
    start = rd.date("start_date", "Fecha inicial", required=False)
    end = rd.date("end_date", "Fecha final", required=False)
    calc_p = rd.text("calc_period_months", "auto")
    rd.done()

    warnings = []
    spec = R.get_spec(cat, code)
    p = spec.months
    if calc_p not in ("auto", ""):
        try:
            p = int(calc_p)
        except ValueError:
            p = 0
        if p not in R.VALID_MONTHS:
            raise ValidationError({"calc_period_months": "Periodo de cálculo no válido."})

    term_months = None
    if needs_term:
        if term is not None:
            term_months = term * (12 if unit == "years" else 1)
            if start and end:
                d_m = months_between(start, end)
                if abs(d_m - term_months) > D("0.5"):
                    warnings.append("El plazo ingresado no coincide con las fechas; se usó el plazo ingresado.")
        elif start and end:
            if end <= start:
                raise ValidationError({"end_date": "La fecha final debe ser posterior a la inicial."})
            term_months = months_between(start, end)
            warnings.append("Plazo calculado a partir de las fechas (meses completos + días/30).")
        else:
            raise ValidationError({"term_value": "Indique el plazo o las fechas inicial y final."})
    if sc in ("C", "D") and fv is not None and pv is not None:
        if fv < pv:
            raise ValidationError({"fv": "El valor futuro debe ser mayor o igual al capital: una tasa "
                                         "negativa no corresponde en este ejercicio."})
        if fv == pv:
            raise ValidationError({"fv": "Si FV = PV la tasa es 0 % (o el tiempo es indeterminado)."})
    if sc == "D" and rate_val == 0:
        raise ValidationError({"rate_value": "Con tasa 0 % el capital nunca crece: el tiempo no existe."})

    proc = Procedure()
    # ---------- Paso 1
    proc.step(1, "Identificación de los datos")
    rows = []
    if pv is not None:
        rows.append([T("PV"), "Capital inicial (valor presente)", M(pv)])
    if fv is not None:
        rows.append([T("FV"), "Valor futuro", M(fv)])
    if rate_val is not None:
        rows.append([T("tasa"), f"Tasa ingresada ({spec.name})", P(rate_val / 100)])
    else:
        rows.append([T("tasa"), f"Incógnita: se expresará como {spec.name} ({spec.code})", "?"])
    if term_months is not None:
        rows.append([T("t"), "Plazo (meses)", N(term_months, 6)])
        rows.append([T("p"), "Periodo de capitalización (meses)", str(p)])
        rows.append([T("n"), "Número de periodos $n = t/p$", N(term_months / p, 8)])
    else:
        rows.append([T("n"), "Incógnita: número de periodos", "?"])
    proc.text(f"Escenario {sc}: {SCENARIOS[sc]}.")
    proc.table(rows)

    n = term_months / p if term_months is not None else None
    i = ea = None
    out_value = None
    if sc in ("A", "B", "D"):
        res = R.resolve(rate_val, spec, p, proc)
        i, ea = res["i_target"], res["ea"]
    else:
        # C: la tasa es incógnita
        proc.step(2, "Identificación de la tasa")
        proc.text(f"La tasa es la **incógnita**. Se hallará la tasa efectiva del periodo y luego se expresará como "
                  f"**{spec.name} ({spec.code})**, que fue el tipo de tasa elegido para el resultado.")
        proc.step(3, "Conversión de tasas")
        proc.text("Primero se obtiene $i$ (efectiva del periodo) en el paso 6; después se convierte a la modalidad "
                  "pedida pasando por la EA (ver paso 7).")

    # ---------- Pasos 4-6 según escenario
    proc.step(4, "Identificación de la fórmula financiera")
    if sc == "A":
        proc.text("El capital crece con interés **compuesto**: los intereses de cada periodo se suman al capital.")
        proc.math("FV = PV\\,(1+i)^{n}", result=True)
        proc.where([("FV", "valor futuro"), ("PV", "valor presente (capital inicial)"),
                    ("i", "tasa **efectiva** del periodo"), ("n", "número de periodos")])
        proc.text("Es la adecuada porque hay un único pago inicial y una única cantidad final, sin cuotas intermedias.")
    elif sc == "B":
        proc.text("Se despeja el valor presente de la fórmula del valor futuro (descuento compuesto).")
        proc.math("PV = \\dfrac{FV}{(1+i)^{n}} = FV\\,(1+i)^{-n}", result=True)
        proc.where([("FV", "valor futuro"), ("PV", "valor presente (capital inicial)"),
                    ("i", "tasa **efectiva** del periodo"), ("n", "número de periodos")])
    elif sc == "C":
        proc.text("Se despeja la tasa de $FV = PV(1+i)^n$ elevando ambos lados a $1/n$.")
        proc.math("i = \\left(\\dfrac{FV}{PV}\\right)^{1/n}-1", result=True)
        proc.where([("FV", "valor futuro"), ("PV", "valor presente (capital inicial)"),
                    ("i", "tasa **efectiva** del periodo"), ("n", "número de periodos")])
    else:
        proc.text("Se despeja $n$ de $FV = PV(1+i)^n$ aplicando logaritmo natural.")
        proc.math("n = \\dfrac{\\ln(FV/PV)}{\\ln(1+i)}", result=True)
        proc.where([("FV", "valor futuro"), ("PV", "valor presente (capital inicial)"),
                    ("i", "tasa **efectiva** del periodo"), ("n", "número de periodos")])

    proc.step(5, "Sustitución de valores")
    if sc == "A":
        proc.math(f"FV = {M(pv)}\\,(1+{N(i, 12)})^{{{N(n, 8)}}}")
    elif sc == "B":
        proc.math(f"PV = \\dfrac{{{M(fv)}}}{{(1+{N(i, 12)})^{{{N(n, 8)}}}}}")
    elif sc == "C":
        proc.math(f"i = \\left(\\dfrac{{{M(fv)}}}{{{M(pv)}}}\\right)^{{1/{N(n, 8)}}}-1")
    else:
        proc.math(f"n = \\dfrac{{\\ln({M(fv)}/{M(pv)})}}{{\\ln(1+{N(i, 12)})}}")

    proc.step(6, "Desarrollo matemático")
    proc.text("Los valores intermedios se calculan con 50 dígitos; aquí se muestran con 8-12 decimales.")
    if sc == "A":
        f = dpow(1 + i, n)
        fv = pv * f
        proc.math(f"(1+i)^n = {N(1 + i, 12)}^{{{N(n, 8)}}} = {N(f, 12)}", academic=True)
        proc.math(f"FV = {M(pv)} \\times {N(f, 12)} = {M(fv)}", result=True)
    elif sc == "B":
        f = dpow(1 + i, n)
        pv = fv / f
        proc.math(f"(1+i)^n = {N(1 + i, 12)}^{{{N(n, 8)}}} = {N(f, 12)}", academic=True)
        proc.math(f"PV = {M(fv)} \\div {N(f, 12)} = {M(pv)}", result=True)
    elif sc == "C":
        q = fv / pv
        i = rate_needed(pv, fv, n)
        ea = R.ea_of(i, p)
        proc.math(f"\\dfrac{{FV}}{{PV}} = \\dfrac{{{M(fv)}}}{{{M(pv)}}} = {N(q, 12)}", academic=True)
        proc.math(f"({N(q, 12)})^{{1/{N(n, 8)}}} = {N(1 + i, 12)}", academic=True)
        proc.math(f"i = {N(1 + i, 12)}-1 = {N(i, 12)} = {P(i, 10)}", result=True)
    else:
        q = fv / pv
        n = periods_needed(pv, fv, i)
        term_months = n * p
        proc.math(f"\\ln({N(q, 12)}) = {N(dln(q), 12)}", academic=True)
        proc.math(f"\\ln(1+i) = \\ln({N(1 + i, 12)}) = {N(dln(1 + i), 12)}", academic=True)
        proc.math(f"n = {N(dln(q), 12)} \\div {N(dln(1 + i), 12)} = {N(n, 8)}\\ \\text{{periodos}}", result=True)

    interest = fv - pv
    n_f = float(n)
    if sc == "C":
        out_value = R.express(spec, ea)
    # ---------- Paso 7
    proc.step(7, "Resultado final")
    if sc == "C":
        proc.text("Conversión de la tasa periódica hallada a la modalidad pedida:")
        for ln in R.conversion_latex(spec, ea):
            proc.math(ln, academic=True)
        proc.math(f"{T(spec.code)} = {P(out_value, 10)}", result=True)
        proc.text(f"Para que {M(pv)} se conviertan en {M(fv)} en {N(term_months, 6)} meses se requiere una tasa de "
                  f"**{N(out_value * 100, 8)} % {spec.code}** (equivale a una EA de {N(ea * 100, 8)} %).")
    elif sc == "A":
        proc.text(f"Al cabo de {N(term_months, 6)} meses, el capital de {M(pv)} se convierte en **{M(fv)}**; "
                  f"los intereses generados son {M(interest)}.")
    elif sc == "B":
        proc.text(f"Para obtener {M(fv)} dentro de {N(term_months, 6)} meses hay que invertir hoy **{M(pv)}**; "
                  f"los intereses generados serían {M(interest)}.")
    else:
        proc.text(f"Se necesitan **{N(n, 6)} periodos de {p} mes(es)** (≈ {N(term_months, 4)} meses, "
                  f"{N(term_months / 12, 4)} años) para que {M(pv)} lleguen a {M(fv)}.")
    proc.math(f"I = FV - PV = {M(fv)} - {M(pv)} = {M(interest)}", result=True)

    # ---------- fecha final
    end_date = add_months(start, term_months) if start else (end or None)

    # ---------- serie y tabla
    growth, labels, values = [], [], []
    total_periods = math.ceil(n_f)
    schedule = None
    stride = max(1, total_periods // 400)
    if total_periods <= 1200:
        schedule = []
    else:
        warnings.append("Más de 1200 periodos: no se genera la tabla periódica, solo el gráfico.")
    bal = pv
    for t in range(0, total_periods + 1):
        tt = min(D(t), n)
        val = pv * dpow(1 + i, tt)
        if t % stride == 0 or t == total_periods:
            labels.append(f"{N(tt, 2)}")
            values.append(val)
        if schedule is not None and t >= 1:
            opening = pv * dpow(1 + i, D(t - 1))
            closing = val
            schedule.append({"n": t, "date": add_months(start, t * p) if start else None,
                             "opening": opening, "interest": closing - opening, "closing": closing})
    chart = {"kind": "line", "x_label": f"Periodos de {p} mes(es)", "labels": labels,
             "series": [{"name": "Capital acumulado", "values": values}], "pv": pv, "fv": fv}

    cards = [
        {"key": "pv", "label": "Capital inicial", "value": pv, "kind": "money", "step": 1},
        {"key": "fv", "label": "Valor futuro", "value": fv, "kind": "money", "step": 6},
        {"key": "rate", "label": f"Tasa utilizada ({code})", "value": (out_value * 100) if sc == "C" else rate_val,
         "kind": "pct", "step": 2},
        {"key": "ea", "label": "Tasa efectiva anual", "value": ea * 100, "kind": "pct", "step": 3},
        {"key": "ip", "label": f"Tasa periódica ({p} m)", "value": i * 100, "kind": "pct", "step": 3},
        {"key": "n", "label": "Número de periodos", "value": n, "kind": "num", "step": 6},
        {"key": "time", "label": "Tiempo de la operación", "value": term_months, "kind": "months", "step": 1},
        {"key": "interest", "label": "Intereses generados", "value": interest, "kind": "money", "step": 7},
    ]
    if end_date:
        cards.append({"key": "end", "label": "Fecha de finalización", "value": end_date, "kind": "date", "step": 1})
    return {"module": "compound", "scenario": sc, "cards": cards, "procedure": proc.to_list(),
            "schedule": schedule, "schedule_kind": "growth", "chart": chart, "warnings": warnings,
            "summary": {"pv": pv, "fv": fv, "interest": interest, "n": n, "i": i, "ea": ea, "p": p}}
