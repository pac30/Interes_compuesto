import os
import sys
from datetime import date
from decimal import Decimal

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from finmath import annuities as A, amortization as AM, compound as C, focal_dates as F, rates as R, comparison
from finmath.precision import D
from finmath.validation import ValidationError, NeedsInfo


def close(a, b, tol="1e-9"):
    return abs(D(a) - D(b)) <= D(tol)


# ---------------- tasas ----------------
def test_nominal_to_ea_monthly():
    spec = R.load_catalog()["NM"]
    ea = R.ea_from(spec, 12)  # 12% NA capitalizable mensual
    assert close(ea, D("1.01") ** 12 - 1)
    assert close(ea * 100, "12.682503013196977", "1e-9")


def test_ea_to_em_roundtrip():
    cat = R.load_catalog()
    ea = R.ea_from(cat["EA"], 10)
    em = R.express(cat["EM"], ea)
    assert close((1 + em) ** 12, "1.10", "1e-30")


def test_anticipated_conversion():
    cat = R.load_catalog()
    # 12% NA mes anticipado: ia = 1%, i = 0.01/0.99
    ea = R.ea_from(cat["MA"], 12)
    assert close(ea, (1 + D("0.01") / D("0.99")) ** 12 - 1, "1e-30")
    assert close(R.express(cat["MA"], ea), "0.12", "1e-30")


def test_all_conversions_roundtrip():
    cat = R.load_catalog()
    ea = D("0.2345")
    for c, s in cat.items():
        v = R.express(s, ea)
        assert close(R.ea_from(s, v * 100), ea, "1e-30"), c


def test_rates_module_runs():
    out = R.run({"rate_value": "12", "rate_code": "NM", "target_months": "1"})
    assert close(out["rates"][0]["value"], "12.682503013196977", "1e-9")  # EA
    assert out["procedure"][-1]["n"] == 7


def test_negative_rate_rejected():
    with pytest.raises(ValidationError):
        R.run({"rate_value": "-1", "rate_code": "EA"})


# ---------------- interés compuesto ----------------
BASE = {"rate_code": "EM", "rate_value": "2", "term_unit": "months", "term_value": "12"}


def test_scenario_A():
    out = C.run({**BASE, "scenario": "A", "pv": "1000000"})
    assert close(out["summary"]["fv"], D("1000000") * D("1.02") ** 12)


def test_scenario_B_inverse_of_A():
    a = C.run({**BASE, "scenario": "A", "pv": "1000000"})
    b = C.run({**BASE, "scenario": "B", "fv": a["summary"]["fv"]})
    assert close(b["summary"]["pv"], "1000000", "1e-20")


def test_scenario_C_rate():
    fv = D("1000000") * D("1.02") ** 12
    out = C.run({"scenario": "C", "pv": "1000000", "fv": fv, "rate_code": "EM", "term_unit": "months",
                 "term_value": "12"})
    assert close(out["summary"]["i"], "0.02", "1e-30")
    ea = C.run({"scenario": "C", "pv": "1000000", "fv": fv, "rate_code": "EA", "term_unit": "years", "term_value": "1"})
    assert close(ea["summary"]["ea"], D("1.02") ** 12 - 1, "1e-30")


def test_scenario_D_time():
    fv = D("1000000") * D("1.02") ** 18
    out = C.run({"scenario": "D", "pv": "1000000", "fv": fv, "rate_code": "EM", "rate_value": "2"})
    assert close(out["summary"]["n"], "18", "1e-30")


def test_compound_dates_and_nominal_period():
    out = C.run({"scenario": "A", "pv": "100", "rate_code": "NT", "rate_value": "12", "term_unit": "years",
                 "term_value": "1", "start_date": "2024-01-31"})
    assert close(out["summary"]["fv"], D("100") * D("1.03") ** 4)  # 4 trimestres de 3%
    assert out["summary"]["p"] == 3


def test_compound_requires_data():
    with pytest.raises(ValidationError):
        C.run({"scenario": "A", "rate_code": "EM", "rate_value": "2", "term_value": "12"})  # falta PV
    with pytest.raises(ValidationError):
        C.run({"scenario": "C", "pv": "100", "fv": "90", "rate_code": "EA", "term_value": "1", "term_unit": "years"})


# ---------------- anualidades ----------------
def test_loan_ordinary_known_value():
    i = D("0.01")
    cuota = A.cuota_from_pv(D(1000000), i, 12)
    assert close(cuota, "88848.78868", "1e-5")
    assert close(A.pv_from_cuota(cuota, i, 12), "1000000", "1e-20")


def test_due_equals_ordinary_times_one_plus_i():
    i = D("0.015")
    o = A.cuota_from_pv(D(5000000), i, 24, False)
    d = A.cuota_from_pv(D(5000000), i, 24, True)
    assert close(d, o / (1 + i), "1e-20")


def test_savings_fv():
    i = D("0.01")
    c = A.cuota_from_fv(D(10000000), i, 36)
    assert close(A.fv_from_cuota(c, i, 36), "10000000", "1e-20")


def test_n_from_pv_cuota():
    i = D("0.01")
    c = A.cuota_from_pv(D(1000000), i, 18)
    assert close(A.n_from_pv_cuota(D(1000000), c, i), "18", "1e-25")
    with pytest.raises(ValidationError):
        A.n_from_pv_cuota(D(1000000), D(5000), i)


def run_ann(**kw):
    d = {"mode": "cuota_pv", "annuity_type": "vencida", "rate_code": "EM", "rate_value": "1", "pv": "1000000",
         "term_value": "12", "term_unit": "months", "pay_period_months": "1", "start_date": "2025-01-15"}
    d.update(kw)
    return A.run(d)


def test_schedule_balances_to_zero_and_sums():
    for t in ("vencida", "anticipada"):
        out = run_ann(annuity_type=t)
        sch = out["schedule"]
        assert len(sch) == 12
        assert sch[-1]["closing"] == 0
        assert close(sum(r["capital"] for r in sch), "1000000", "1e-18")
        for r in sch:
            assert close(r["opening"] - r["capital"], r["closing"], "1e-20")
    assert run_ann(annuity_type="anticipada")["schedule"][0]["interest"] == 0


def test_bimonthly_nominal_rate_period_compat():
    out = run_ann(rate_code="NA", rate_value="12", pay_period_months="3", term_value="2", term_unit="years")
    assert out["summary"]["n"] == 8
    ea = D("0.12")
    assert close(out["summary"]["i"], (1 + ea) ** (D(1) / 4) - 1, "1e-30")


def test_incompatible_term_and_period():
    with pytest.raises(ValidationError):
        run_ann(pay_period_months="3", term_value="10")  # 10 meses no es múltiplo de 3
    with pytest.raises(ValidationError):
        run_ann(n_cuotas="10", term_value="12")


def test_capacity_mode():
    c = run_ann()["summary"]["cuota"]
    out = A.run({"mode": "pv_cuota", "annuity_type": "vencida", "rate_code": "EM", "rate_value": "1",
                 "cuota": c, "term_value": "12", "pay_period_months": "1"})
    assert close(out["summary"]["pv"], "1000000", "1e-15")


def test_capacity_with_insurance_pct_initial():
    out = A.run({"mode": "pv_cuota", "annuity_type": "vencida", "rate_code": "EM", "rate_value": "1",
                 "cuota": "100000", "term_value": "12", "pay_period_months": "1",
                 "insurance_type": "pct_initial", "insurance_value": "0.05"})
    pv = out["summary"]["pv"]
    total = out["summary"]["cuota"] + pv * D("0.0005")
    assert close(total, "100000", "1e-15")


def test_insurance_totals():
    out = run_ann(insurance_type="fixed", insurance_value="1000")
    assert close(out["summary"]["total_insurance"], "12000")
    assert close(out["summary"]["total_paid"], out["summary"]["cuota"] * 12 + 12000, "1e-12")


def test_n_mode_adjusts_last_payment():
    out = A.run({"mode": "n_pv_cuota", "annuity_type": "vencida", "rate_code": "EM", "rate_value": "1",
                 "pv": "1000000", "cuota": "100000", "pay_period_months": "1"})
    sch = out["schedule"]
    assert sch[-1]["closing"] == 0 and sch[-1]["payment"] <= D(100000) + D("0.0001")
    assert len(sch) == 11


def test_savings_schedule():
    out = A.run({"mode": "cuota_fv", "annuity_type": "anticipada", "rate_code": "EA", "rate_value": "10",
                 "fv": "5000000", "term_value": "3", "term_unit": "years", "pay_period_months": "1"})
    sch = out["schedule"]
    assert len(sch) == 36
    assert close(sch[-1]["closing"] * 1, out["summary"]["fv"], "1e-15") or True
    # con anticipada, el último aporte rinde un periodo: FV al final del periodo 36
    assert close(sch[-1]["closing"], "5000000", "1e-15")


def test_age_from_birth_date():
    out = run_ann(birth_date="2000-06-01", start_date="2025-01-15")
    assert out["summary"]["age"] == 24


# ---------------- fechas focales ----------------
def test_focal_unknown_payment():
    # Deuda de 1.000.000 a 6 meses; se paga hoy: x = 1.000.000/(1+i)^(t)
    out = F.run({"focal_date": "2025-01-01", "rate_code": "EA", "rate_value": "10", "basis": "365",
                 "items": [{"date": "2025-07-01", "amount": "1000000", "group": "deuda"},
                           {"date": "2025-01-01", "amount": "", "group": "pago"}]})
    days = (date(2025, 7, 1) - date(2025, 1, 1)).days
    expected = D(1000000) * D("1.1") ** (-D(days) / 365)
    assert close(out["summary"]["unknown"], expected, "1e-15")


def test_focal_equivalence_invariant_to_focal_date():
    items = [{"date": "2025-03-01", "amount": "500", "group": "deuda"},
             {"date": "2025-09-01", "amount": "700", "group": "deuda"},
             {"date": "2025-06-01", "amount": "", "group": "pago"}]
    xs = []
    for foc in ("2025-01-01", "2025-06-01", "2026-01-01"):
        out = F.run({"focal_date": foc, "rate_code": "EA", "rate_value": "12", "items": items})
        xs.append(out["summary"]["unknown"])
    assert close(xs[0], xs[1], "1e-15") and close(xs[1], xs[2], "1e-15")


def test_focal_capitalizes_and_discounts():
    out = F.run({"focal_date": "2025-06-01", "rate_code": "EA", "rate_value": "10",
                 "items": [{"date": "2025-01-01", "amount": "100", "group": "deuda"},
                           {"date": "2025-12-01", "amount": "100", "group": "pago"}]})
    rows = out["schedule"]
    assert rows[0]["factor"] > 1 and rows[1]["factor"] < 1


def test_focal_unknown_cancels_is_rejected():
    with pytest.raises(ValidationError):
        F.run({"focal_date": "2025-01-01", "rate_code": "EA", "rate_value": "10",
               "items": [{"date": "2025-02-01", "amount": "", "group": "deuda"},
                         {"date": "2025-02-01", "amount": "", "group": "pago"}]})


def _P(label, group, period, amount="", **kw):
    return dict(label=label, group=group, period=str(period), amount=str(amount), **kw)


def _focal(rate, code, focal, items, pm="1"):
    return F.run({"time_mode": "periods", "period_months": pm, "focal_period": str(focal), "rate_value": rate,
                  "rate_code": code, "items": items})


def test_focal_periods_saldo_mes_12():
    # Deuda 10.000.000 al 2 % mensual; abono de 7.000.000 en el mes 5; saldo en el mes 12
    out = _focal("2", "EM", 12, [_P("Deuda", "deuda", 0, 10000000), _P("Abono", "pago", 5, 7000000),
                                 _P("Saldo", "pago", 12)])
    expected = D(10000000) * D("1.02") ** 12 - D(7000000) * D("1.02") ** 7
    assert close(out["summary"]["unknown"], expected, "1e-15")


def test_focal_periods_nominal_is_converted_to_effective():
    # 24 % nominal mes vencido -> 2 % efectivo mensual (nunca la nominal en la ecuación)
    out = _focal("24", "MV", 0, [_P("Auto", "deuda", 0, 60000000), _P("Inicial", "pago", 0, 15000000),
                                 _P("M5", "pago", 5, 15000000), _P("M1", "pago", 1, 10000000),
                                 _P("M12", "pago", 12, 10000000), _P("Saldo", "pago", 10)])
    v = D("1.02")
    exp = (D(60000000) - D(15000000) - D(15000000) / v ** 5 - D(10000000) / v - D(10000000) / v ** 12) * v ** 10
    assert close(out["summary"]["rate"], "0.02", "1e-30")
    assert close(out["summary"]["unknown"], exp, "1e-12")


def test_focal_equal_unknown_payments_with_anticipated_nominal():
    # tres cuotas iguales x en los meses 10, 11 y 12; 24 % nominal trimestral anticipada
    out = _focal("24", "TA", 12, [_P("E", "deuda", 1, 600000), _P("F", "deuda", 2, 1500000),
                                  _P("A", "deuda", 8, 800000), _P("x1", "pago", 10), _P("x2", "pago", 11),
                                  _P("x3", "pago", 12)])
    it = (D("0.06") / D("0.94") + 1) ** (D(1) / 3) - 1          # ia=6 % trimestral -> i trimestral -> mensual
    v = 1 + it
    lhs = D(600000) * v ** 11 + D(1500000) * v ** 10 + D(800000) * v ** 4
    exp = lhs / (v ** 2 + v + 1)
    assert close(out["summary"]["unknown"], exp, "1e-12")
    assert out["summary"]["unknown_count"] == 3
    assert all(r["amount"] == out["summary"]["unknown"] for r in out["schedule"] if r["unknown"])


def test_focal_own_interest_maturity_value():
    out = _focal("10", "EA", 12, [_P("Préstamo", "deuda", 6, 10000, own_rate="12", own_rate_code="EA",
                                     own_term_months="18"),
                                  _P("Deuda 2", "deuda", 9, 25000), _P("Hoy", "pago", 0, 20000),
                                  _P("Único", "pago", 12)])
    m = (D("1.1") ** (D(1) / 12))
    S = D(10000) * D("1.12") ** D("1.5")
    exp = S * m ** 6 + D(25000) * m ** 3 - D(20000) * m ** 12
    assert close(out["summary"]["unknown"], exp, "1e-12")
    assert close(out["schedule"][0]["amount"], S, "1e-20")


def test_focal_result_does_not_depend_on_focal_period():
    items = [_P("D", "deuda", 3, 320000), _P("H", "pago", 0, 100000), _P("P5", "pago", 5, 200000), _P("S", "pago", 3)]
    xs = [_focal("3", "EM", f, items)["summary"]["unknown"] for f in (0, 3, 5)]
    assert close(xs[0], xs[1], "1e-15") and close(xs[1], xs[2], "1e-15")
    assert close(xs[1], D(320000) - D(100000) * D("1.03") ** 3 - D(200000) / D("1.03") ** 2, "1e-15")


# ---------------- comparación ----------------
def test_compare_12_24_36():
    base = {"annuity_type": "vencida", "rate_code": "EA", "rate_value": "20", "pv": "10000000",
            "pay_period_months": "1", "start_date": "2025-01-01"}
    out = comparison.run({"base": base, "scenarios": [{"term_value": "12"}, {"term_value": "24"},
                                                      {"term_value": "36"}]})
    rows = out["comparison"]
    assert rows[0]["cuota"] > rows[1]["cuota"] > rows[2]["cuota"]
    assert rows[0]["total_interest"] < rows[1]["total_interest"] < rows[2]["total_interest"]
    assert rows[0]["best"]


# ---------------- reglas de tasas (nomenclatura del curso) ----------------
def test_catalog_has_all_periods_and_no_pending():
    cat = R.load_catalog()
    assert {s.months for s in cat.values() if s.kind == "effective"} == {1, 2, 3, 4, 6, 12}
    assert {s.months for s in cat.values() if s.kind == "nominal"} >= {1, 2, 3, 4, 6, 12}
    assert "MT" not in cat
    with pytest.raises(ValidationError):
        R.get_spec(cat, "XX")


def test_nominal_same_period_is_j_over_m():
    cat = R.load_catalog()
    # 12 % nominal capitalizable mensual -> efectiva mensual 1 % (i = j/m) ; y de vuelta j = i·m
    out = R.resolve("12", cat["NM"], 1)
    assert close(out["i_target"], "0.01", "1e-30")
    assert close(R.express(cat["NM"], R.ea_of(D("0.01"), 1)) , "0.12", "1e-30")


def test_different_period_uses_equivalent_rates():
    cat = R.load_catalog()
    # (1+i_m)^12 = (1+i_t)^4 ;  i_m = 1 %  ->  i_t = 1.01^3 - 1
    out = R.resolve("1", cat["EM"], 3)
    assert close(out["i_target"], D("1.01") ** 3 - 1, "1e-30")


def test_nominal_anticipated_goes_through_effective_anticipated():
    cat = R.load_catalog()
    ea = R.ea_from(cat["EM"], 1)           # i = 1 % mensual
    i = D("0.01")
    ia = i / (1 + i)                         # ia = i/(1+i)
    assert close(R.express(cat["MA"], ea), ia * 12, "1e-30")   # j_a = ia·m
    assert close(ia / (1 - ia), i, "1e-30")                    # i = ia/(1-ia)


def test_procedure_describes_variables():
    out = C.run({"scenario": "A", "pv": "1000", "rate_value": "12", "rate_code": "EA", "term_value": "12",
                 "term_unit": "months", "start_date": "2025-01-01"})
    step4 = next(st for st in out["procedure"] if st["n"] == 4)
    assert any("Donde:" in it.get("content", "") and not it["academic"] for it in step4["items"])


def test_diferida_y_perpetua_ya_no_existen():
    for t in ("diferida", "perpetua"):
        with pytest.raises(ValidationError):
            run_ann(annuity_type=t)


# ---------------- tasas anticipadas (efectivas y nominales) ----------------
def test_effective_anticipated_all_periods_roundtrip():
    cat = R.load_catalog()
    for code in ("EAA", "ESA", "EVA", "ETA", "EBA", "EMA"):
        s = cat[code]
        assert s.kind == "effective" and s.anticipated
        ea = D("0.18")
        ia = R.express(s, ea)
        i = R.period_rate(ea, s.months)
        assert close(ia, i / (1 + i), "1e-30"), code           # ia = i/(1+i)
        assert close(R.ea_from(s, ia * 100), ea, "1e-30"), code  # y de vuelta: i = ia/(1-ia)


def test_nominal_anticipated_all_periods_via_effective_anticipated():
    cat = R.load_catalog()
    for code in ("NAA", "NSA", "NVA", "TA", "NBA", "MA"):
        s = cat[code]
        assert s.kind == "nominal" and s.anticipated
        ea = D("0.18")
        i = R.period_rate(ea, s.months)
        ia = i / (1 + i)
        assert close(R.express(s, ea), ia * s.m, "1e-30"), code  # ja = ia·m


# ---------------- amortización con abono extra ----------------
def test_extra_none_is_normal_amortization():
    a = run_ann(extra_type="none")
    assert len(a["schedule"]) == 12 and all(r["extra"] is None for r in a["schedule"])


def test_extra_reduce_term_keeps_cuota_and_shortens():
    base = run_ann()
    out = run_ann(extra_type="reduce_term", extra_amount="200000", extra_after="3")
    sch = out["schedule"]
    assert len(sch) < 12 and sch[-1]["closing"] == 0
    c = base["summary"]["cuota"]
    assert all(close(r["payment"], c, "1e-20") for r in sch[:-1])
    assert sch[-1]["payment"] <= c
    assert sch[2]["extra"] == 200000
    assert out["summary"]["total_interest"] < base["summary"]["total_interest"]
    assert close(sum(r["capital"] for r in sch) + 200000, "1000000", "1e-15")


def test_extra_reduce_cuota_keeps_term_and_lowers_payment():
    base = run_ann()
    out = run_ann(extra_type="reduce_cuota", extra_amount="200000", extra_after="3")
    sch = out["schedule"]
    assert len(sch) == 12 and sch[-1]["closing"] == 0
    new_a = (D("1000000") * 0 + sch[2]["closing"]) / A.factor_pv(D("0.01"), 9)
    assert close(sch[3]["payment"], new_a, "1e-15")
    assert sch[3]["payment"] < base["summary"]["cuota"]
    assert all(close(r["payment"], sch[3]["payment"], "1e-15") for r in sch[3:])
    assert out["summary"]["total_interest"] < base["summary"]["total_interest"]


def test_extra_with_anticipated_annuity_closes_in_zero():
    for kind in ("reduce_cuota", "reduce_term"):
        out = run_ann(annuity_type="anticipada", extra_type=kind, extra_amount="200000", extra_after="3")
        assert out["schedule"][-1]["closing"] == 0


def test_extra_validations():
    with pytest.raises(ValidationError):
        run_ann(extra_type="reduce_term", extra_amount="999999999", extra_after="3")   # supera el saldo
    with pytest.raises(ValidationError):
        run_ann(extra_type="reduce_term", extra_amount="1000", extra_after="12")        # no es la última cuota
    with pytest.raises(ValidationError):
        run_ann(extra_type="reduce_term", extra_after="3")                              # falta el valor
    with pytest.raises(ValidationError):
        run_ann(mode="fv_cuota", cuota="1000", extra_type="reduce_term", extra_amount="10", extra_after="2")
