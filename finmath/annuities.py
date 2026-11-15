"""Anualidades y cuotas: vencidas y anticipadas; créditos (plan de pagos) y ahorros."""
import math
from datetime import date

from . import amortization as AM
from . import rates as R
from .dates import add_months, months_between, age_on
from .precision import D, ZERO, ONE, dpow, dln
from .steps import Procedure, N, M, P, T
from .validation import Reader, ValidationError, NeedsInfo

MODES = {
    "cuota_pv": "Valor de la cuota (dada la deuda o monto)",
    "pv_cuota": "Monto que puedo financiar (dada mi cuota)",
    "cuota_fv": "Cuota de ahorro para alcanzar una meta (FV)",
    "fv_cuota": "Valor futuro acumulado con mis aportes",
    "n_pv_cuota": "Número de cuotas (dadas la deuda y la cuota)",
}
TYPES = {"vencida": "Anualidad vencida", "anticipada": "Anualidad anticipada"}
PAY_PERIODS = {1: "Mensual", 2: "Bimestral", 3: "Trimestral", 6: "Semestral", 12: "Anual"}
INSURANCE = ("none", "pct_balance", "pct_initial", "fixed")


def factor_pv(i, n, due=False):
    """a_n (vencida) o ä_n (anticipada)."""
    n = D(n)
    a = n if i == 0 else (1 - dpow(1 + i, -n)) / i
    return a * (1 + i) if due else a


def factor_fv(i, n, due=False):
    n = D(n)
    s = n if i == 0 else (dpow(1 + i, n) - 1) / i
    return s * (1 + i) if due else s


def cuota_from_pv(pv, i, n, due=False):
    return pv / factor_pv(i, n, due)


def pv_from_cuota(cuota, i, n, due=False):
    return cuota * factor_pv(i, n, due)


def cuota_from_fv(fv, i, n, due=False):
    return fv / factor_fv(i, n, due)


def fv_from_cuota(cuota, i, n, due=False):
    return cuota * factor_fv(i, n, due)


def n_from_pv_cuota(pv, cuota, i, due=False):
    if i == 0:
        return pv / cuota
    base = pv * i / (cuota * (1 + i) if due else cuota)
    if base >= 1:
        raise ValidationError({"cuota": "La cuota no alcanza a cubrir los intereses del primer periodo: "
                                        "la deuda nunca se pagaría. Aumente la cuota."})
    return -dln(1 - base) / dln(1 + i)


# ------------------------- helpers de pasos -------------------------

def _sym_pv(due):
    return "PV = A\,\dfrac{1-(1+i)^{-n}}{i}" + ("\,(1+i)" if due else "")


def _num_pv(A, i, n, due):
    return f"PV = {A}\,\dfrac{{1-(1+{N(i, 12)})^{{-{n}}}}}{{{N(i, 12)}}}" + (f"\,(1+{N(i, 12)})" if due else "")

def _develop_pv_factor(proc, i, n, due):
    if i == 0:
        proc.text("Con tasa 0 % no hay intereses: el factor es simplemente $n$.")
        F = D(n)
        proc.math(f"F = n = {n}", academic=True)
        return F
    g = dpow(1 + i, -n)
    a = (1 - g) / i
    proc.math(f"(1+i)^{{-n}} = {N(1 + i, 12)}^{{-{n}}} = {N(g, 14)}", academic=True)
    proc.math(f"a_{{n|i}} = \\dfrac{{1-{N(g, 14)}}}{{{N(i, 12)}}} = {N(a, 12)}", academic=True)
    F = a
    if due:
        F = a * (1 + i)
        proc.math(f"\\ddot a_{{n|i}} = a_{{n|i}}\\,(1+i) = {N(a, 12)} \\times {N(1 + i, 12)} = {N(F, 12)}",
                  academic=True)
    return F


def _develop_fv_factor(proc, i, n, due):
    if i == 0:
        proc.text("Con tasa 0 % el factor es simplemente $n$.")
        F = D(n)
        proc.math(f"F = n = {n}", academic=True)
        return F
    g = dpow(1 + i, n)
    s = (g - 1) / i
    proc.math(f"(1+i)^n = {N(1 + i, 12)}^{{{n}}} = {N(g, 14)}", academic=True)
    proc.math(f"s_{{n|i}} = \\dfrac{{{N(g, 14)}-1}}{{{N(i, 12)}}} = {N(s, 12)}", academic=True)
    F = s
    if due:
        F = s * (1 + i)
        proc.math(f"\\ddot s_{{n|i}} = s_{{n|i}}\\,(1+i) = {N(F, 12)}", academic=True)
    return F


# ------------------------- ejecución -------------------------

def run(data):
    cat = R.load_catalog()
    rd = Reader(data)
    mode = rd.choice("mode", "¿Qué desea calcular?", list(MODES))
    atype = rd.choice("annuity_type", "Tipo de anualidad", list(TYPES), "vencida")
    rd.done()
    savings = mode in ("cuota_fv", "fv_cuota")
    due = atype == "anticipada"
    need_pv = mode in ("cuota_pv", "n_pv_cuota")
    need_fv = mode == "cuota_fv"
    need_cuota = mode in ("pv_cuota", "fv_cuota", "n_pv_cuota")

    pv = rd.dec("pv", "Valor presente / monto", required=need_pv, gt=0)
    fv = rd.dec("fv", "Valor futuro deseado", required=need_fv, gt=0)
    cuota_in = rd.dec("cuota", "Cuota", required=need_cuota, gt=0)
    rate_val = rd.dec("rate_value", "Tasa de interés", min=0)
    code = rd.text("rate_code")
    if not code:
        rd.errors["rate_code"] = "Tipo de tasa: seleccione una opción."
    p = rd.integer("pay_period_months", "Periodicidad de pago", min=1)
    if p is not None and p not in PAY_PERIODS:
        rd.errors["pay_period_months"] = "Periodicidad no válida (mensual, bimestral, trimestral, semestral o anual)."
    start = rd.date("start_date", "Fecha inicial", required=False)
    end = rd.date("end_date", "Fecha final", required=False)
    birth = rd.date("birth_date", "Fecha de nacimiento", required=False)
    age_in = rd.integer("age", "Edad", required=False, min=0, max=120)
    ins_kind = rd.choice("insurance_type", "Tipo de seguro", INSURANCE, "none")
    ins_val = rd.dec("insurance_value", "Valor del seguro", required=ins_kind != "none", min=0) or ZERO
    rd.done()

    warnings = []
    spec = R.get_spec(cat, code)
    if not start:
        start = date.today()
        warnings.append("No indicó fecha inicial: se usó la fecha de hoy.")
    age = age_in
    if birth:
        age = age_on(birth, start)
        if age < 0:
            raise ValidationError({"birth_date": "La fecha de nacimiento es posterior a la fecha inicial."})
    if age is not None and age < 18:
        warnings.append("La persona es menor de 18 años: revise si puede contraer la obligación.")

    # ---------- número de cuotas
    n = None
    n_in = rd.integer("n_cuotas", "Número de cuotas", required=False, min=1, max=1200)
    rd.done()
    term_months = None
    if rd.has("term_value"):
        t = rd.dec("term_value", "Plazo", gt=0)
        rd.done()
        unit = rd.choice("term_unit", "Unidad del plazo", ["months", "years"], "months")
        term_months = t * (12 if unit == "years" else 1)
    elif start and end and mode != "n_pv_cuota":
        if end <= start:
            raise ValidationError({"end_date": "La fecha final debe ser posterior a la inicial."})
        term_months = months_between(start, end)
        warnings.append("Plazo calculado a partir de las fechas inicial y final.")
    if mode != "n_pv_cuota":
        n_t = None
        if term_months is not None:
            ratio = term_months / p
            if ratio != ratio.to_integral_value():
                raise ValidationError({"term_value": f"Plazo y periodicidad incompatibles: {N(term_months, 4)} meses "
                                                     f"no es múltiplo de {p} mes(es) entre pagos."})
            n_t = int(ratio)
        if n_in and n_t and n_in != n_t:
            raise ValidationError({"n_cuotas": f"El número de cuotas ({n_in}) no coincide con el plazo "
                                               f"({n_t} pagos de {p} mes(es))."})
        n = n_in or n_t
        if not n:
            raise NeedsInfo({"term_value": "Indique el plazo (meses o años), el número de cuotas o las fechas "
                                           "inicial y final."})
        if n > 1200:
            raise ValidationError({"term_value": "Máximo 1200 cuotas."})

    proc = Procedure()
    # ---------- Paso 1
    proc.step(1, "Identificación de los datos")
    rows = []
    if pv is not None:
        rows.append([T("PV"), "Valor presente / deuda inicial", M(pv)])
    if fv is not None:
        rows.append([T("FV"), "Valor futuro deseado", M(fv)])
    if cuota_in is not None:
        rows.append([T("A"), "Cuota (pago periódico igual)", M(cuota_in)])
    rows.append([T("tasa"), f"Tasa ingresada ({spec.name})", P(D(rate_val) / 100)])
    rows.append([T("p"), f"Periodicidad de pago ({PAY_PERIODS[p]})", f"{p} mes(es)"])
    if n:
        rows.append([T("n"), "Número de cuotas", str(n)])
    rows.append([T("tipo"), TYPES[atype], "pagos al inicio" if due else "pagos al final"])
    if age is not None:
        rows.append([T("edad"), "Edad de la persona", str(age)])
    proc.text(f"Cálculo: **{MODES[mode]}**. Tipo: **{TYPES[atype]}**.")
    proc.table(rows)

    res = R.resolve(rate_val, spec, p, proc)
    i, ea = res["i_target"], res["ea"]

    # ---------- Paso 4: fórmula y significado de cada variable
    cuota = pv_res = fv_res = None
    n_exact = D(n) if n else None
    proc.step(4, "Identificación de la fórmula financiera")
    desc_due = "anticipada (los pagos se hacen al inicio de cada periodo, por eso se multiplica por $(1+i)$)" \
        if due else "vencida (los pagos se hacen al final de cada periodo)"
    if savings:
        proc.text(f"Se acumulan aportes iguales que ganan interés compuesto; la anualidad es {desc_due}.")
        proc.math("FV = A\\,\\dfrac{(1+i)^{n}-1}{i}" + ("\\,(1+i)" if due else ""), result=True)
        proc.where([("FV", "valor futuro acumulado al final"), ("A", "cuota o aporte periódico igual"),
                    ("i", "tasa **efectiva** del periodo de pago (ya convertida en el paso 3)"),
                    ("n", "número de cuotas")])
        proc.text("Es la adecuada porque se conoce una meta de valor futuro y se paga con cuotas periódicas iguales.")
        if mode == "cuota_fv":
            proc.text("Se despeja la cuota $A$:")
            proc.math("A = \\dfrac{FV}{F}, \\quad F = \\dfrac{(1+i)^{n}-1}{i}" + ("(1+i)" if due else ""))
    else:
        proc.text(f"Se paga una deuda con cuotas iguales; la anualidad es {desc_due}.")
        proc.math(_sym_pv(due), result=True)
        proc.where([("PV", "valor presente: deuda o monto financiado"), ("A", "cuota periódica igual"),
                    ("i", "tasa **efectiva** del periodo de pago (ya convertida en el paso 3)"),
                    ("n", "número de cuotas")])
        proc.text("Es la adecuada porque el valor presente de todas las cuotas debe igualar la deuda.")
        if mode == "cuota_pv":
            proc.text("Se despeja la cuota $A$:")
            proc.math("A = \\dfrac{PV}{F}" + ", \\quad F = \\dfrac{1-(1+i)^{-n}}{i}" + ("(1+i)" if due else ""))
        if mode == "n_pv_cuota":
            proc.text("Se despeja $n$ con logaritmos:")
            proc.math("n = -\\dfrac{\\ln\\left(1-\\dfrac{PV \\, i}{A" + ("(1+i)" if due else "") +
                      "}\\right)}{\\ln(1+i)}")

    proc.step(5, "Sustitución de valores")
    proc.step(6, "Desarrollo matemático")
    if mode == "cuota_pv":
        F = _develop_pv_factor(proc, i, n, due)
        cuota = pv / F
        pv_res = pv
        proc.math(f"A = \\dfrac{{{M(pv)}}}{{{N(F, 12)}}} = {M(cuota)}", result=True)
    elif mode == "pv_cuota":
        F = _develop_pv_factor(proc, i, n, due)
        A_base = cuota_in
        if ins_kind == "fixed":
            A_base = cuota_in - ins_val * p
            if A_base <= 0:
                raise ValidationError({"cuota": "La cuota no alcanza ni para cubrir el seguro."})
            proc.text(f"La cuota ingresada incluye el seguro fijo ({M(ins_val * p)} por periodo): la cuota "
                      f"para el crédito es {M(cuota_in)} − {M(ins_val * p)} = {M(A_base)}.")
        if ins_kind == "pct_initial":
            pv_res = cuota_in / (1 / F + ins_val / 100 * p)
            proc.text("Como el seguro es un porcentaje del monto inicial, se resuelve "
                      "$PV = \\dfrac{A_{total}}{1/F + s\\,p}$ con $s$ = % mensual.")
            A_base = pv_res / F
        elif ins_kind == "pct_balance":
            raise ValidationError({"insurance_type": "Con seguro sobre saldo la cuota total no es constante; "
                                                     "para calcular el monto financiable elija seguro fijo, "
                                                     "porcentaje del monto inicial o sin seguro."})
        else:
            pv_res = A_base * F
        cuota = A_base
        proc.math(f"PV = {M(A_base)} \\times {N(F, 12)} = {M(pv_res)}", result=True)
    elif mode == "cuota_fv":
        F = _develop_fv_factor(proc, i, n, due)
        cuota = fv / F
        fv_res = fv
        proc.math(f"A = \\dfrac{{FV}}{{F}} = \\dfrac{{{M(fv)}}}{{{N(F, 12)}}} = {M(cuota)}", result=True)
    elif mode == "fv_cuota":
        F = _develop_fv_factor(proc, i, n, due)
        cuota = cuota_in
        fv_res = cuota * F
        proc.math(f"FV = {M(cuota)} \\times {N(F, 12)} = {M(fv_res)}", result=True)
    else:  # n_pv_cuota
        n_exact = n_from_pv_cuota(pv, cuota_in, i, due)
        cuota = cuota_in
        pv_res = pv
        if i > 0:
            arg = pv * i / (cuota * (1 + i) if due else cuota)
            proc.math(f"1-\\dfrac{{PV\\,i}}{{A}}" + ("(1+i)" if due else "") + f" = 1-{N(arg, 14)} = {N(1 - arg, 14)}",
                      academic=True)
            proc.math(f"\\ln({N(1 - arg, 14)}) = {N(dln(1 - arg), 14)}; \\quad \\ln(1+i) = {N(dln(1 + i), 14)}",
                      academic=True)
        proc.math(f"n = {N(n_exact, 8)}\\ \\text{{periodos}}", result=True)
        n = math.ceil(float(n_exact) - 1e-12)

    # sustitución (paso 5) se rellena ahora que se conocen los valores
    step5 = next(s for s in proc.steps if s["n"] == 5)
    sub = []
    if savings:
        sub.append(f"FV = A\\,\\dfrac{{(1+{N(i, 12)})^{{{n}}}-1}}{{{N(i, 12)}}}" + (f"\\,(1+{N(i, 12)})" if due else ""))
    elif mode == "n_pv_cuota":
        sub.append(f"n = -\\dfrac{{\\ln\\left(1-\\dfrac{{{M(pv)}\\,{N(i, 12)}}}{{{M(cuota_in)}}}"
                   f"\\right)}}{{\\ln(1+{N(i, 12)})}}")
    elif mode == "cuota_pv":
        fx = f"\\dfrac{{1-(1+{N(i, 12)})^{{-{n}}}}}{{{N(i, 12)}}}" + (f"\\,(1+{N(i, 12)})" if due else "")
        sub.append(f"A = \\dfrac{{{M(pv)}}}{{{fx}}}")
    else:
        sub.append(_num_pv(M(cuota), i, n, due))
    step5["items"].append({"kind": "text", "content": "Se reemplazan las variables por los datos reales "
                                                      "(con la tasa periódica ya convertida):", "academic": True})
    for s in sub:
        step5["items"].append({"kind": "math", "content": s, "academic": False, "result": False})

    # ---------- plan de pagos y totales
    schedule = None
    if savings:
        schedule = AM.savings_schedule(i, n, cuota, due, start, p)
        total_cuotas = cuota * n
        total_interest = (fv_res or fv) - total_cuotas
        total_ins = ZERO
        total_paid = total_cuotas
    else:
        ins_obj = AM.Insurance(ins_kind, ins_val, pv_res, p)
        adjust = mode == "n_pv_cuota" and abs(n_exact - n) > D("1e-12")
        schedule = AM.loan_schedule(pv_res, i, n, cuota, due, start, p, ins_obj, adjust)
        total_cuotas = sum((r["payment"] for r in schedule), ZERO)
        total_ins = sum((r["insurance"] for r in schedule), ZERO)
        total_interest = total_cuotas - pv_res
        total_paid = total_cuotas + total_ins
        if ins_kind != "none":
            warnings.append("Seguro: el valor ingresado es mensual; en periodos de varios meses se multiplica "
                            "por el número de meses del periodo.")
    end_date = add_months(start, n * p)

    # ---------- Paso 7
    proc.step(7, "Resultado final")
    if savings:
        proc.text(f"Aportando **{M(cuota)}** cada {p} mes(es) durante {n} periodos se acumulan **{M(fv_res)}**. "
                  f"Se aportan {M(total_cuotas)} y los intereses ganados son {M(total_interest)}.")
        proc.math(f"I = FV - nA = {M(fv_res)} - {n}\\times{M(cuota)} = {M(total_interest)}", result=True)
    else:
        if mode == "cuota_pv":
            what = f"La cuota es **{M(cuota)}** por periodo de {p} mes(es)."
        elif mode == "pv_cuota":
            what = f"Con una cuota de {M(cuota_in)} se puede financiar **{M(pv_res)}**."
        else:
            what = f"Se requieren **{N(n_exact, 4)}** cuotas (se pagan {n})."
        proc.text(what)
        proc.math(f"\\text{{Total pagado}} = nA = {M(total_cuotas)}; \\quad I = {M(total_cuotas)} - {M(pv_res)} = "
                  f"{M(total_interest)}", result=True)
        if ins_kind != "none":
            proc.text(f"Seguros pagados: {M(total_ins)}; total a pagar con seguros: {M(total_paid)}.")
        proc.text("El plan de pagos muestra cómo cada cuota se divide en interés (sobre el saldo) y abono a capital.")

    # ---------- gráficos
    stride = max(1, len(schedule) // 400)
    init = pv_res if not savings else ZERO
    labels, vals = ["0"], [init]
    cap, intr, lab2 = [], [], []
    for idx, r in enumerate(schedule):
        if idx % stride == 0 or idx == len(schedule) - 1:
            labels.append(str(r["n"]))
            vals.append(r["closing"])
        if idx % stride == 0:
            lab2.append(str(r["n"]))
            cap.append(max(r["capital"], ZERO))
            intr.append(r["interest"])
    name = "Capital ahorrado" if savings else "Saldo de la deuda"
    chart = {"kind": "line", "x_label": f"Periodos de {p} mes(es)", "labels": labels,
             "series": [{"name": name, "values": vals}],
             "stack": {"labels": lab2, "capital": cap, "interest": intr,
                       "cap_name": "Aporte" if savings else "Abono a capital"}}

    # ---------- tarjetas
    per_label = {1: "mensual", 2: "bimestral", 3: "trimestral", 6: "semestral", 12: "anual"}[p]
    cards = [{"key": "ea", "label": "Tasa efectiva anual", "value": ea * 100, "kind": "pct", "step": 3},
             {"key": "ip", "label": f"Tasa periódica utilizada ({p} m)", "value": i * 100, "kind": "pct", "step": 3}]
    first_ins = ZERO
    if not savings:
        first_ins = schedule[0]["insurance"]
    if pv_res is not None:
        cards.append({"key": "pv", "label": "Capital inicial / monto", "value": pv_res, "kind": "money", "step": 6 if mode == "pv_cuota" else 1})
    if fv_res is not None:
        cards.append({"key": "fv", "label": "Valor futuro", "value": fv_res, "kind": "money", "step": 6})
    cards.append({"key": "cuota", "label": f"Cuota {per_label}", "value": cuota, "kind": "money", "step": 6})
    if not savings and ins_kind != "none":
        cards.append({"key": "seguro", "label": f"Seguro {per_label}" + (" (1.ª cuota)" if ins_kind == "pct_balance" else ""),
                      "value": first_ins, "kind": "money", "step": 7})
        cards.append({"key": "cuota_seguro", "label": f"Cuota {per_label} con seguros",
                      "value": cuota + first_ins, "kind": "money", "step": 7})
    cards.append({"key": "n", "label": "Cantidad de cuotas", "value": n_exact if mode == "n_pv_cuota" else n,
                  "kind": "num" if mode == "n_pv_cuota" else "int", "step": 6 if mode == "n_pv_cuota" else 1})
    cards.append({"key": "plazo", "label": "Plazo total", "value": n * p, "kind": "months", "step": 1})
    cards.append({"key": "interest", "label": "Total de intereses", "value": total_interest, "kind": "money", "step": 7})
    cards.append({"key": "paid", "label": "Total a pagar" if not savings else "Total aportado",
                  "value": total_paid, "kind": "money", "step": 7})
    if not savings:
        cards.append({"key": "amort", "label": "Capital amortizado", "value": pv_res, "kind": "money", "step": 7})
    cards.append({"key": "end", "label": "Fecha de finalización", "value": end_date, "kind": "date", "step": 1})
    if age is not None:
        cards.append({"key": "age", "label": "Edad", "value": age, "kind": "int", "step": 1})

    return {"module": "annuity", "mode": mode, "cards": cards, "procedure": proc.to_list(),
            "schedule": schedule, "schedule_kind": "savings" if savings else "loan", "chart": chart,
            "warnings": warnings,
            "summary": {"pv": pv_res, "fv": fv_res, "cuota": cuota, "n": n, "i": i, "ea": ea, "p": p,
                        "total_interest": total_interest, "total_paid": total_paid, "total_insurance": total_ins,
                        "first_insurance": first_ins, "end_date": end_date, "age": age}}
