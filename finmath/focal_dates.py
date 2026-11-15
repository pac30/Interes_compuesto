"""Fechas focales: equivalencia financiera trasladando valores a una fecha de referencia."""
from . import rates as R
from .dates import year_fraction
from .precision import D, ZERO, dpow
from .steps import Procedure, N, M, P, T
from .validation import Reader, ValidationError, NeedsInfo, blank

GROUPS = {"deuda": "Obligación original (deuda)", "pago": "Pago / obligación nueva"}
BASES = {"365": "Años de 365 días (días reales)", "360": "Años de 360 días (días reales)",
         "30/360": "Convención 30/360"}


def move_factor(ea, years):
    """Factor (1+i)^t: capitaliza si t>0 (fecha anterior al foco) y descuenta si t<0."""
    return dpow(1 + ea, years)


def run(data):
    cat = R.load_catalog()
    rd = Reader(data)
    focal = rd.date("focal_date", "Fecha focal")
    start = rd.date("start_date", "Fecha inicial", required=False)
    end = rd.date("end_date", "Fecha final", required=False)
    rate_val = rd.dec("rate_value", "Tasa de interés", min=0)
    code = rd.text("rate_code")
    if not code:
        rd.errors["rate_code"] = "Tipo de tasa: seleccione una opción."
    basis = rd.choice("basis", "Base de días", list(BASES), "365")
    raw_items = data.get("items") or []
    if not raw_items:
        rd.errors["items"] = "Registre al menos una obligación o pago con su fecha."
    rd.done()
    if start and end and end <= start:
        raise ValidationError({"end_date": "La fecha final debe ser posterior a la inicial."})

    items, errors, unknown_idx = [], {}, []
    for k, it in enumerate(raw_items):
        r = Reader(it)
        d = r.date("date", f"Fecha de la fila {k + 1}")
        grp = r.choice("group", f"Grupo de la fila {k + 1}", list(GROUPS), "deuda")
        amt = None
        if blank(it.get("amount")):
            unknown_idx.append(k)
        else:
            amt = r.dec("amount", f"Valor de la fila {k + 1}", gt=0)
        if r.errors:
            errors[f"item{k}"] = "; ".join(r.errors.values())
        items.append({"date": d, "group": grp, "amount": amt, "label": str(it.get("label") or f"Obligación {k + 1}")})
    if errors:
        raise ValidationError(errors)
    if len(unknown_idx) > 1:
        raise NeedsInfo({"items": "Solo puede haber un valor desconocido (déjelo en blanco) por ecuación de "
                                  "equivalencia."})

    warnings = []
    spec = R.get_spec(cat, code)
    proc = Procedure()
    proc.step(1, "Identificación de los datos")
    rows = [[T("fecha focal"), "Fecha de referencia a la que se trasladan los valores", focal.isoformat()],
            [T("base"), "Conteo de tiempo", BASES[basis]], [T("tasa"), f"Tasa ingresada ({spec.name})", P(rate_val / 100)]]
    if start:
        rows.append([T("inicio"), "Fecha inicial", start.isoformat()])
    if end:
        rows.append([T("fin"), "Fecha final", end.isoformat()])
    for k, it in enumerate(items):
        rows.append([T(f"V_{k + 1}"), f"{it['label']} — {GROUPS[it['group']]} — {it['date'].isoformat()}",
                     M(it["amount"]) if it["amount"] is not None else "x (incógnita)"])
    proc.table(rows)
    res = R.resolve(rate_val, spec, 12, proc)
    ea = res["ea"]
    proc.text("En las ecuaciones de valor **nunca** se usa una tasa nominal: siempre se convierte a efectiva. Como el "
              "tiempo se mide en **años**, se usa la tasa efectiva anual (EA) como tasa de traslado.", academic=False)

    # factores
    for k, it in enumerate(items):
        t = year_fraction(it["date"], focal, basis)
        it["t"] = t
        it["factor"] = move_factor(ea, t)
        it["value_f"] = it["amount"] * it["factor"] if it["amount"] is not None else None
        it["dir"] = "capitaliza" if t > 0 else ("descuenta" if t < 0 else "ya está en la fecha focal")

    proc.step(4, "Identificación de la fórmula financiera")
    proc.text("En una ecuación de valor la suma de activos es igual a la de pasivos, la de ingresos a la de egresos y "
              "la de deudas a la de pagos. Dos conjuntos son **equivalentes** si, al trasladarlos a una misma fecha "
              "(fecha focal) con la misma tasa efectiva, suman lo mismo. Cada valor se traslada con:", academic=False)
    proc.math("V_F = V\\,(1+i)^{t}", result=True)
    proc.where([("V_F", "valor trasladado a la fecha focal"), ("V", "valor de la deuda o del pago en su fecha"),
                ("i", "tasa **efectiva** (nunca nominal)"),
                ("t", "diferencia entre la fecha focal y la fecha del valor, en años")])
    proc.text("donde $t$ es el tiempo en años desde la fecha del valor hasta la fecha focal: **positivo** si el valor "
              "está antes del foco (se capitaliza) y **negativo** si está después (se descuenta). La ecuación de "
              "equivalencia es:")
    proc.math("\\sum V_{deudas}(1+i)^{t} = \\sum V_{pagos}(1+i)^{t}", result=True)

    def term(it):
        a = "x" if it["amount"] is None else M(it["amount"])
        return f"{a}\\,(1+{N(ea, 10)})^{{{N(it['t'], 8)}}}"

    deudas = [it for it in items if it["group"] == "deuda"]
    pagos = [it for it in items if it["group"] == "pago"]
    proc.step(5, "Sustitución de valores")
    for it in items:
        proc.math(f"V_F({it['label']}) = {term(it)}", academic=True)
    lhs = " + ".join(term(it) for it in deudas) or "0"
    rhs = " + ".join(term(it) for it in pagos) or "0"
    proc.text("Ecuación de equivalencia con los datos reales:")
    proc.math(f"{lhs} = {rhs}", result=True)

    proc.step(6, "Desarrollo matemático")
    for it in items:
        proc.math(f"(1+{N(ea, 10)})^{{{N(it['t'], 8)}}} = {N(it['factor'], 12)}", academic=True)
        if it["amount"] is not None:
            proc.math(f"V_F({it['label']}) = {M(it['amount'])} \\times {N(it['factor'], 12)} = {M(it['value_f'])}")
    sum_d = sum((it["value_f"] for it in deudas if it["value_f"] is not None), ZERO)
    sum_p = sum((it["value_f"] for it in pagos if it["value_f"] is not None), ZERO)
    unknown = None
    cards = []
    if unknown_idx:
        u = items[unknown_idx[0]]
        if u["group"] == "deuda":
            x_f = sum_p - sum_d
        else:
            x_f = sum_d - sum_p
        if x_f <= 0:
            warnings.append("El valor desconocido resulta ≤ 0: el otro grupo ya cubre (o excede) la equivalencia.")
        x = x_f / u["factor"]
        u["amount"], u["value_f"] = x, x_f
        unknown = x
        sd = sum_d + (x_f if u["group"] == "deuda" else 0)
        sp = sum_p + (x_f if u["group"] == "pago" else 0)
        proc.text("Se despeja la incógnita: su valor en la fecha focal es la diferencia entre ambos lados.")
        proc.math(f"x\\,(1+i)^{{t}} = {M(x_f)} \\;\\Rightarrow\\; x = \\dfrac{{{M(x_f)}}}{{{N(u['factor'], 12)}}} = {M(x)}",
                  result=True)
    else:
        sd, sp = sum_d, sum_p
    proc.step(7, "Resultado final")
    proc.math(f"\\sum V_{{deudas}} = {M(sd)}; \\quad \\sum V_{{pagos}} = {M(sp)}", result=True)
    if unknown is not None:
        proc.text(f"El valor desconocido es **{M(unknown)}** ({items[unknown_idx[0]]['label']}, "
                  f"{items[unknown_idx[0]]['date'].isoformat()}). Con él, ambos conjuntos valen {M(sd)} el "
                  f"{focal.isoformat()}.")
    else:
        diff = sd - sp
        if abs(diff) < D("0.005"):
            proc.text("Ambos conjuntos son **equivalentes** en la fecha focal.")
        else:
            proc.text(f"Los conjuntos **no son equivalentes**: la diferencia en la fecha focal es {M(abs(diff))} "
                      f"({'las deudas superan a los pagos' if diff > 0 else 'los pagos superan a las deudas'}).")

    for it in items:
        if start and it["date"] < start or end and it["date"] > end:
            warnings.append(f"«{it['label']}» está fuera del rango fecha inicial–final.")
    if not (min(it["date"] for it in items) <= focal <= max(it["date"] for it in items)):
        warnings.append("La fecha focal queda fuera del rango de las obligaciones (todo se capitaliza o todo se "
                        "descuenta).")

    cards.append({"key": "ea", "label": "Tasa efectiva anual utilizada", "value": ea * 100, "kind": "pct", "step": 3})
    cards.append({"key": "focal", "label": "Fecha focal", "value": focal, "kind": "date", "step": 1})
    cards.append({"key": "sd", "label": "Deudas en la fecha focal", "value": sd, "kind": "money", "step": 7})
    cards.append({"key": "sp", "label": "Pagos en la fecha focal", "value": sp, "kind": "money", "step": 7})
    if unknown is not None:
        cards.append({"key": "x", "label": "Valor desconocido (x)", "value": unknown, "kind": "money", "step": 7})
    else:
        cards.append({"key": "diff", "label": "Diferencia", "value": sd - sp, "kind": "money", "step": 7})

    schedule = [{"n": k + 1, "label": it["label"], "group": it["group"], "date": it["date"],
                 "amount": it["amount"], "t": it["t"], "factor": it["factor"], "value_f": it["value_f"],
                 "dir": it["dir"], "unknown": k in unknown_idx} for k, it in enumerate(items)]
    chart = {"kind": "timeline", "focal": focal, "start": start, "end": end, "items": schedule}
    return {"module": "focal", "cards": cards, "procedure": proc.to_list(), "schedule": schedule,
            "schedule_kind": "focal", "chart": chart, "warnings": warnings,
            "summary": {"sum_debts": sd, "sum_payments": sp, "unknown": unknown, "ea": ea}}
