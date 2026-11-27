"""Ecuaciones de valor y fechas focales.

Σ (lado A: deudas, depósitos, ingresos) trasladados al foco = Σ (lado B: pagos, retiros, egresos) trasladados al foco.
Cada valor se traslada con V_F = V (1+i)^t, donde t = momento focal − momento del valor y la tasa i es SIEMPRE
efectiva (nunca nominal).

Dos formas de medir el tiempo:
  * periods: el tiempo se cuenta en periodos (mes, bimestre, trimestre...) y se usa la tasa efectiva de ese periodo.
  * dates:   fechas reales; t en años (base 365, 360 o 30/360) y se usa la tasa efectiva anual.
Todas las filas con el valor en blanco son la MISMA incógnita x (p. ej. "tres cuotas iguales").
Una fila puede tener intereses propios (tasa y plazo originales): primero se calcula su valor al vencimiento.
"""
from . import rates as R
from .dates import year_fraction
from .precision import D, ZERO, dpow
from .steps import Procedure, N, M, P, T
from .validation import Reader, ValidationError, blank

GROUPS = {"deuda": "Deuda / depósito / ingreso", "pago": "Pago / retiro / egreso"}
BASES = {"365": "Años de 365 días (días reales)", "360": "Años de 360 días (días reales)",
         "30/360": "Convención 30/360"}
MODES = {"periods": "Periodos", "dates": "Fechas"}


def move_factor(i, t):
    """Factor (1+i)^t: capitaliza si t>0 (valor anterior al foco) y descuenta si t<0."""
    return dpow(1 + i, t)


def _when(it, mode, pname):
    return it["date"].isoformat() if mode == "dates" else f"{pname.capitalize()} {N(it['period'], 4)}"


def run(data):
    cat = R.load_catalog()
    rd = Reader(data)
    default_mode = "dates" if not blank(data.get("focal_date")) else "periods"
    mode = rd.choice("time_mode", "Medir el tiempo en", list(MODES), data.get("time_mode") or default_mode)
    focal = start = end = None
    basis, pm, focal_p = "365", 12, None
    if mode == "dates":
        focal = rd.date("focal_date", "Fecha focal")
        start = rd.date("start_date", "Fecha inicial", required=False)
        end = rd.date("end_date", "Fecha final", required=False)
        basis = rd.choice("basis", "Base de días", list(BASES), "365")
    else:
        pm = rd.integer("period_months", "Duración del periodo", min=1)
        if pm is not None and pm not in R.VALID_MONTHS:
            rd.errors["period_months"] = "El periodo debe ser de 1, 2, 3, 4, 6 o 12 meses."
        focal_p = rd.dec("focal_period", "Periodo focal", min=0)
    rate_val = rd.dec("rate_value", "Tasa de interés", min=0)
    code = rd.text("rate_code")
    if not code:
        rd.errors["rate_code"] = "Tipo de tasa: seleccione una opción."
    raw_items = data.get("items") or []
    if not raw_items:
        rd.errors["items"] = "Registre al menos una deuda o pago."
    rd.done()
    if start and end and end <= start:
        raise ValidationError({"end_date": "La fecha final debe ser posterior a la inicial."})
    pname = R.PER_NAME[pm].replace("anual", "año").replace("mensual", "mes").replace("bimestral", "bimestre") \
        .replace("trimestral", "trimestre").replace("cuatrimestral", "cuatrimestre").replace("semestral", "semestre")

    items, errors = [], {}
    for k, it in enumerate(raw_items):
        r = Reader(it)
        row = {"label": str(it.get("label") or f"Valor {k + 1}"),
               "group": r.choice("group", f"Grupo de la fila {k + 1}", list(GROUPS), "deuda")}
        if mode == "dates":
            row["date"] = r.date("date", f"Fecha de la fila {k + 1}")
        else:
            row["period"] = r.dec("period", f"Periodo de la fila {k + 1}", min=0)
        row["amount"] = None if blank(it.get("amount")) else r.dec("amount", f"Valor de la fila {k + 1}", gt=0)
        row["own"] = None
        if not blank(it.get("own_rate")):
            o_rate = r.dec("own_rate", f"Tasa propia de la fila {k + 1}", min=0)
            o_months = r.dec("own_term_months", f"Plazo original (meses) de la fila {k + 1}", gt=0)
            o_code = it.get("own_rate_code") or "EA"
            if row["amount"] is None:
                r.errors["own_rate"] = "Una fila con intereses propios necesita su valor inicial."
            if not r.errors:
                row["own"] = {"rate": o_rate, "months": o_months, "spec": R.get_spec(cat, o_code)}
        if r.errors:
            errors[f"item{k}"] = f"Fila {k + 1}: " + "; ".join(r.errors.values())
        items.append(row)
    if errors:
        raise ValidationError(errors)
    unknown_idx = [k for k, it in enumerate(items) if it["amount"] is None]

    warnings = []
    spec = R.get_spec(cat, code)
    proc = Procedure()
    proc.step(1, "Identificación de los datos")
    if mode == "dates":
        rows = [[T("fecha focal"), "Fecha a la que se trasladan los valores", focal.isoformat()],
                [T("base"), "Conteo de tiempo", BASES[basis]]]
        if start:
            rows.append([T("inicio"), "Fecha inicial", start.isoformat()])
        if end:
            rows.append([T("fin"), "Fecha final", end.isoformat()])
    else:
        rows = [[T("periodo"), "Duración de cada periodo", f"{pm} mes(es) ({pname})"],
                [T("foco"), "Periodo focal (a donde se trasladan los valores)", N(focal_p, 4)]]
    rows.append([T("tasa"), f"Tasa ingresada ({spec.name})", P(rate_val / 100)])
    for k, it in enumerate(items):
        extra = ""
        if it["own"]:
            extra = f" — con intereses propios {N(it['own']['rate'], 6)} % {it['own']['spec'].code} a " \
                    f"{N(it['own']['months'], 4)} meses"
        rows.append([T(f"V_{k + 1}"), f"{it['label']} — {GROUPS[it['group']]} — {_when(it, mode, pname)}{extra}",
                     M(it["amount"]) if it["amount"] is not None else "x (incógnita)"])
    proc.table(rows)
    if len(unknown_idx) > 1:
        proc.text(f"Las {len(unknown_idx)} filas sin valor son **la misma incógnita** $x$ (pagos iguales).",
                  academic=False)

    # ---------- tasa efectiva del periodo de traslado
    res = R.resolve(rate_val, spec, 12 if mode == "dates" else pm, proc)
    i = res["ea"] if mode == "dates" else res["i_target"]
    if mode == "dates":
        proc.text("En las ecuaciones de valor **nunca** se usa una tasa nominal: siempre se convierte a efectiva. Como "
                  "el tiempo se mide en **años**, se usa la tasa efectiva anual (EA).", academic=False)
    else:
        proc.text(f"En las ecuaciones de valor **nunca** se usa una tasa nominal: siempre se convierte a efectiva. Como "
                  f"el tiempo se mide en periodos de {pm} mes(es), se usa la tasa **efectiva {R.PER_NAME[pm]}**.",
                  academic=False)

    # ---------- valores al vencimiento (intereses propios)
    for it in items:
        it["original"] = it["amount"]
        if it["own"]:
            o = it["own"]
            o["ea"] = R.ea_from(o["spec"], o["rate"])
            o["factor"] = dpow(1 + o["ea"], o["months"] / 12)
            it["amount"] = it["original"] * o["factor"]

    # ---------- factores de traslado
    for it in items:
        if mode == "dates":
            it["t"] = year_fraction(it["date"], focal, basis)
        else:
            it["t"] = focal_p - it["period"]
        it["factor"] = move_factor(i, it["t"])
        it["value_f"] = it["amount"] * it["factor"] if it["amount"] is not None else None
        it["dir"] = "capitaliza" if it["t"] > 0 else ("descuenta" if it["t"] < 0 else "ya está en el foco")

    proc.step(4, "Identificación de la fórmula financiera")
    proc.text("En una **ecuación de valor** la suma de activos es igual a la de pasivos, la de ingresos a la de "
              "egresos y la de deudas a la de pagos. Todo se traslada a un mismo momento (la **fecha focal**) con la "
              "misma tasa **efectiva**:", academic=False)
    proc.math("\\sum V_{deudas}\\,(1+i)^{t} = \\sum V_{pagos}\\,(1+i)^{t}", result=True)
    unit = "años" if mode == "dates" else f"periodos de {pm} mes(es)"
    proc.where([("V", "valor de cada deuda o pago en su momento"), ("i", "tasa **efectiva** (nunca nominal)"),
                ("t", f"fecha focal − momento del valor, en {unit} (positivo: se capitaliza; negativo: se descuenta)")])
    if any(it["own"] for it in items):
        proc.text("Las deudas que ya tienen intereses propios se llevan primero a su **valor al vencimiento** con su "
                  "tasa y su plazo originales:", academic=False)
        proc.math("S = P\\,(1+i_{propia})^{n}")
        proc.where([("S", "valor al vencimiento"), ("P", "valor inicial de la deuda"),
                    ("i_{propia}", "tasa efectiva anual original"), ("n", "plazo original en años")])

    def term(it):
        a = "x" if it["amount"] is None else M(it["amount"])
        return f"{a}\\,(1+{N(i, 10)})^{{{N(it['t'], 8)}}}"

    deudas = [it for it in items if it["group"] == "deuda"]
    pagos = [it for it in items if it["group"] == "pago"]
    proc.step(5, "Sustitución de valores")
    for it in items:
        if it["own"]:
            o = it["own"]
            proc.math(f"S_{{\\text{{{it['label']}}}}} = {M(it['original'])}\\,(1+{N(o['ea'], 10)})^{{{N(o['months'] / 12, 8)}}} "
                      f"= {M(it['amount'])}")
    lhs = " + ".join(term(it) for it in deudas) or "0"
    rhs = " + ".join(term(it) for it in pagos) or "0"
    proc.text("Ecuación de valor con los datos reales:")
    proc.math(f"{lhs} = {rhs}", result=True)

    proc.step(6, "Desarrollo matemático")
    for it in items:
        proc.math(f"(1+{N(i, 10)})^{{{N(it['t'], 8)}}} = {N(it['factor'], 12)}", academic=True)
        if it["amount"] is not None:
            proc.math(f"V_F(\\text{{{it['label']}}}) = {M(it['amount'])} \\times {N(it['factor'], 12)} = {M(it['value_f'])}")
    sum_d = sum((it["value_f"] for it in deudas if it["value_f"] is not None), ZERO)
    sum_p = sum((it["value_f"] for it in pagos if it["value_f"] is not None), ZERO)
    unknown = None
    if unknown_idx:
        fd = sum((items[k]["factor"] for k in unknown_idx if items[k]["group"] == "deuda"), ZERO)
        fp = sum((items[k]["factor"] for k in unknown_idx if items[k]["group"] == "pago"), ZERO)
        if fd == fp:
            raise ValidationError({"items": "La incógnita se cancela en la ecuación (aparece igual en ambos lados): "
                                            "no se puede despejar."})
        x = (sum_p - sum_d) / (fd - fp)
        if x <= 0:
            warnings.append("El valor desconocido resulta ≤ 0: el otro lado de la ecuación ya cubre (o excede) "
                            "la equivalencia.")
        for k in unknown_idx:
            items[k]["amount"] = x
            items[k]["value_f"] = x * items[k]["factor"]
        unknown = x
        fac = fd - fp if fd > fp else fp - fd
        known_side = sum_p - sum_d if fd > fp else sum_d - sum_p
        proc.text("Se despeja la incógnita: los valores conocidos se agrupan en un lado y los factores de $x$ en el "
                  "otro.", academic=False)
        if len(unknown_idx) > 1:
            proc.math(" + ".join(N(items[k]["factor"], 10) for k in unknown_idx) + f" = {N(fac, 12)}", academic=True)
        proc.math(f"x \\times {N(fac, 12)} = {M(known_side)} \\;\\Rightarrow\\; x = \\dfrac{{{M(known_side)}}}"
                  f"{{{N(fac, 12)}}} = {M(x)}", result=True)
    sd = sum((it["value_f"] for it in deudas), ZERO)
    sp = sum((it["value_f"] for it in pagos), ZERO)

    proc.step(7, "Resultado final")
    proc.math(f"\\sum V_{{deudas}} = {M(sd)}; \\quad \\sum V_{{pagos}} = {M(sp)}", result=True)
    where_focal = focal.isoformat() if mode == "dates" else f"el {pname} {N(focal_p, 4)}"
    if unknown is not None:
        names = ", ".join(f"{items[k]['label']} ({_when(items[k], mode, pname)})" for k in unknown_idx)
        proc.text(f"El valor desconocido es **{M(unknown)}** ({names}). Con él, ambos lados valen {M(sd)} en "
                  f"{where_focal}.")
    else:
        diff = sd - sp
        if abs(diff) < D("0.005"):
            proc.text("Ambos lados son **equivalentes** en la fecha focal.")
        else:
            proc.text(f"Los dos lados **no son equivalentes**: la diferencia en la fecha focal es {M(abs(diff))} "
                      f"({'las deudas superan a los pagos' if diff > 0 else 'los pagos superan a las deudas'}).")

    if mode == "dates":
        for it in items:
            if start and it["date"] < start or end and it["date"] > end:
                warnings.append(f"«{it['label']}» está fuera del rango fecha inicial–final.")
        moments, fpos = [it["date"] for it in items], focal
    else:
        moments, fpos = [it["period"] for it in items], focal_p
    if not (min(moments) <= fpos <= max(moments)):
        warnings.append("La fecha focal queda fuera del rango de los valores (todo se capitaliza o todo se descuenta).")

    rate_label = "Tasa efectiva anual utilizada" if mode == "dates" else f"Tasa efectiva {R.PER_NAME[pm]} utilizada"
    cards = [{"key": "rate", "label": rate_label, "value": i * 100, "kind": "pct", "step": 3}]
    if mode == "dates":
        cards.append({"key": "focal", "label": "Fecha focal", "value": focal, "kind": "date", "step": 1})
    else:
        cards.append({"key": "focal", "label": f"Periodo focal ({pname})", "value": focal_p, "kind": "num", "step": 1})
    cards.append({"key": "sd", "label": "Deudas en la fecha focal", "value": sd, "kind": "money", "step": 7})
    cards.append({"key": "sp", "label": "Pagos en la fecha focal", "value": sp, "kind": "money", "step": 7})
    if unknown is not None:
        lab = "Valor desconocido (x)" if len(unknown_idx) == 1 else f"Valor de cada pago igual (x) × {len(unknown_idx)}"
        cards.append({"key": "x", "label": lab, "value": unknown, "kind": "money", "step": 6})
    else:
        cards.append({"key": "diff", "label": "Diferencia", "value": sd - sp, "kind": "money", "step": 7})

    schedule = [{"n": k + 1, "label": it["label"], "group": GROUPS[it["group"]].split(" / ")[0],
                 "side": it["group"], "when": _when(it, mode, pname), "date": it.get("date"),
                 "period": it.get("period"), "original": it["original"], "amount": it["amount"], "t": it["t"],
                 "factor": it["factor"], "value_f": it["value_f"], "dir": it["dir"], "unknown": k in unknown_idx}
                for k, it in enumerate(items)]
    chart = {"kind": "timeline", "mode": mode, "focal": focal if mode == "dates" else focal_p,
             "unit": pname, "start": start, "end": end, "items": schedule}
    return {"module": "focal", "cards": cards, "procedure": proc.to_list(), "schedule": schedule,
            "schedule_kind": "focal", "chart": chart, "warnings": warnings,
            "summary": {"sum_debts": sd, "sum_payments": sp, "unknown": unknown, "rate": i, "ea": res["ea"],
                        "unknown_count": len(unknown_idx)}}
