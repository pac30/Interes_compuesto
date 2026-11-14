"""Comparación de escenarios de crédito (varía monto, tasa o plazo)."""
from . import annuities
from .validation import ValidationError, Reader


def run(data):
    base = dict(data.get("base") or {})
    scenarios = data.get("scenarios") or []
    if not scenarios:
        raise ValidationError({"scenarios": "Agregue al menos una simulación para comparar."})
    if len(scenarios) > 8:
        raise ValidationError({"scenarios": "Máximo 8 simulaciones."})
    base["mode"] = "cuota_pv"
    base.setdefault("annuity_type", "vencida")
    rows, errors = [], {}
    for k, sc in enumerate(scenarios):
        d = dict(base)
        for key in ("pv", "rate_value", "rate_code", "term_value", "pay_period_months"):
            if sc.get(key) not in (None, ""):
                d[key] = sc[key]
        d["term_unit"] = "months"
        d["n_cuotas"] = ""
        d["end_date"] = ""
        try:
            res = annuities.run(d)
        except ValidationError as e:
            errors[f"sim{k}"] = f"Simulación {k + 1}: {e.message}"
            continue
        s = res["summary"]
        rows.append({"name": sc.get("name") or f"Simulación {k + 1}", "pv": s["pv"], "rate_value": d["rate_value"],
                     "rate_code": d["rate_code"], "ea": s["ea"] * 100, "n": s["n"], "cuota": s["cuota"],
                     "insurance": s["first_insurance"], "cuota_total": s["cuota"] + s["first_insurance"],
                     "total_interest": s["total_interest"], "total_paid": s["total_paid"],
                     "end_date": s["end_date"], "inputs": d})
    if errors:
        raise ValidationError(errors)
    best = min(rows, key=lambda r: r["total_paid"])
    for r in rows:
        r["diff_paid"] = r["total_paid"] - best["total_paid"]
        r["best"] = r is best
    cards = [
        {"key": "best", "label": "Menor total a pagar", "value": best["name"], "kind": "text", "step": 7},
        {"key": "min_cuota", "label": "Cuota más baja", "value": min(r["cuota"] for r in rows), "kind": "money", "step": 7},
        {"key": "max_int", "label": "Mayor total de intereses", "value": max(r["total_interest"] for r in rows),
         "kind": "money", "step": 7},
    ]
    chart = {"kind": "bars", "labels": [r["name"] for r in rows],
             "series": [{"name": "Cuota", "values": [r["cuota_total"] for r in rows]},
                        {"name": "Total de intereses", "values": [r["total_interest"] for r in rows]},
                        {"name": "Total a pagar", "values": [r["total_paid"] for r in rows]}]}
    return {"module": "compare", "cards": cards, "comparison": rows, "chart": chart, "procedure": [],
            "schedule": None, "warnings": ["Cada simulación se calcula con el mismo procedimiento; abra una de "
                                           "ellas en el simulador para ver su desarrollo completo."]}
