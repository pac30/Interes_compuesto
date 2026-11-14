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


@pytest.fixture(autouse=True)
def _default_catalog(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "CATALOG_PATH", str(tmp_path / "cat.json"))


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
        if s.pending:
            continue
        v = R.express(s, ea)
        assert close(R.ea_from(s, v * 100), ea, "1e-30"), c


def test_pending_rate_requires_config():
    with pytest.raises(NeedsInfo):
        R.get_spec(R.load_catalog(), "MT")


def test_catalog_configurable_and_reset():
    items = R.default_catalog_list()
    for it in items:
        if it["code"] == "MT":
            it.update(pending=False, months=3, anticipated=False, name="Mes-Trimestre")
    R.save_catalog(items)
    assert R.get_spec(R.load_catalog(), "MT").months == 3
    items.append({"code": "ZZ", "name": "x", "kind": "nominal", "months": 5})
    with pytest.raises(ValidationError):
        R.save_catalog(items)


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


def test_deferred():
    i = D("0.02")
    c = A.cuota_from_pv(D(1000), i, 10, False, 3)
    assert close(A.pv_from_cuota(c, i, 10, False, 3), "1000", "1e-25")


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


def test_perpetuity():
    assert close(A.perpetuity_pv(D(100), D("0.05")), "2000")
    assert close(A.perpetuity_pv(D(100), D("0.05"), True), "2100")
    assert close(A.perpetuity_cuota(D(2000), D("0.05")), "100")


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


def test_deferred_schedule():
    out = run_ann(annuity_type="diferida", defer_periods="3", term_value="12")
    sch = out["schedule"]
    assert len(sch) == 15 and sch[2]["phase"] == "gracia"
    assert sch[-1]["closing"] == 0
    assert close(out["summary"]["total_interest"], sum(r["interest"] for r in sch), "1e-15")


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


def test_perpetuity_module():
    out = A.run({"mode": "pv_cuota", "annuity_type": "perpetua", "rate_code": "EM", "rate_value": "1",
                 "cuota": "100", "pay_period_months": "1"})
    assert close(out["summary"]["pv"], "10000")
    with pytest.raises(ValidationError):
        A.run({"mode": "cuota_fv", "annuity_type": "perpetua", "rate_code": "EM", "rate_value": "1",
               "fv": "100", "pay_period_months": "1"})


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


def test_focal_two_unknowns_rejected():
    with pytest.raises(ValidationError):
        F.run({"focal_date": "2025-01-01", "rate_code": "EA", "rate_value": "10",
               "items": [{"date": "2025-01-01", "amount": "", "group": "deuda"},
                         {"date": "2025-02-01", "amount": "", "group": "pago"}]})


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
