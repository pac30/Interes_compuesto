"""Catálogo configurable de tasas, conversión y explicación paso a paso.

Modelo: cada tasa (RateSpec) tiene
  kind   : 'effective' | 'nominal'
  months : periodo de la tasa efectiva, o periodo de capitalización de la nominal
           (las nominales siempre se expresan como tasa anual)
  anticipated : True si los intereses se cobran al inicio del periodo
Toda conversión pasa por la tasa efectiva anual (EA) como pivote.
"""
import json
import os
import sys
from dataclasses import dataclass, asdict

from .precision import D, dpow
from .steps import N, P, T, Procedure
from .validation import ValidationError, NeedsInfo, Reader

# Empaquetado (.exe): el catálogo editable se guarda junto al ejecutable; en desarrollo, en config/.
_BASE_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.dirname(__file__))
CATALOG_PATH = os.path.join(_BASE_DIR, "config", "rate_catalog.json")
VALID_MONTHS = (1, 2, 3, 4, 6, 12)
PER_NAME = {1: "mensual", 2: "bimestral", 3: "trimestral", 4: "cuatrimestral", 6: "semestral", 12: "anual"}
CAP_NAME = {1: "mensualmente", 2: "bimestralmente", 3: "trimestralmente", 4: "cuatrimestralmente",
            6: "semestralmente", 12: "anualmente"}


@dataclass
class RateSpec:
    code: str
    name: str
    kind: str
    months: int
    anticipated: bool = False
    pending: bool = False
    note: str = ""

    @property
    def m(self):  # capitalizaciones por año (nominal)
        return 12 // self.months

    def description(self):
        ant = " anticipada" if self.anticipated else " vencida"
        if self.kind == "effective":
            return f"Tasa efectiva {PER_NAME[self.months]}{ant}"
        return f"Tasa nominal anual capitalizable {CAP_NAME[self.months]}{ant}"

    def to_dict(self):
        d = asdict(self)
        d["description"] = self.description()
        return d


DEFAULT_CATALOG = [
    RateSpec("EA", "Efectiva Anual", "effective", 12),
    RateSpec("EM", "Efectiva Mensual", "effective", 1),
    RateSpec("EB", "Efectiva Bimestral", "effective", 2),
    RateSpec("ET", "Efectiva Trimestral", "effective", 3),
    RateSpec("EV", "Efectiva Cuatrimestral", "effective", 4, note="Convención: V = cuatrimestre."),
    RateSpec("ES", "Efectiva Semestral", "effective", 6),
    RateSpec("NA", "Nominal Anual (capitalización anual)", "nominal", 12),
    RateSpec("NM", "Nominal Anual capitalizable Mensual", "nominal", 1),
    RateSpec("NB", "Nominal Anual capitalizable Bimestral", "nominal", 2),
    RateSpec("NT", "Nominal Anual capitalizable Trimestral", "nominal", 3),
    RateSpec("NS", "Nominal Anual capitalizable Semestral", "nominal", 6),
    RateSpec("TV", "Nominal Anual Trimestre Vencido", "nominal", 3, note="Convención: TV = trimestre vencido."),
    RateSpec("MV", "Nominal Anual Mes Vencido", "nominal", 1, note="Convención: MV = mes vencido."),
    RateSpec("TA", "Nominal Anual Trimestre Anticipado", "nominal", 3, anticipated=True),
    RateSpec("MA", "Nominal Anual Mes Anticipado", "nominal", 1, anticipated=True),
    RateSpec("MT", "Mensual/Trimestral (por configurar)", "nominal", 1, pending=True,
             note="Sigla ambigua: su significado depende del material académico. Configúrela en el catálogo."),
]


def default_catalog_list():
    return [asdict(s) for s in DEFAULT_CATALOG]


def parse_catalog(items):
    specs, errors, seen = [], {}, set()
    for k, it in enumerate(items or []):
        code = str(it.get("code", "")).strip().upper()
        pre = f"fila {k + 1}"
        if not code:
            errors[pre] = f"{pre}: la sigla es obligatoria."
            continue
        if code in seen:
            errors[code] = f"Sigla repetida: {code}."
            continue
        seen.add(code)
        kind = it.get("kind")
        try:
            months = int(it.get("months"))
        except (TypeError, ValueError):
            months = 0
        if kind not in ("effective", "nominal"):
            errors[code] = f"{code}: tipo inválido."
        elif months not in VALID_MONTHS:
            errors[code] = f"{code}: el periodo debe ser 1, 2, 3, 4, 6 o 12 meses."
        else:
            specs.append(RateSpec(code, str(it.get("name") or code), kind, months,
                                  bool(it.get("anticipated")), bool(it.get("pending")), str(it.get("note", ""))))
    if errors:
        raise ValidationError(errors)
    if not specs:
        raise ValidationError("El catálogo no puede quedar vacío.")
    return specs


def save_catalog(items):
    specs = parse_catalog(items)
    os.makedirs(os.path.dirname(CATALOG_PATH), exist_ok=True)
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump([asdict(s) for s in specs], f, ensure_ascii=False, indent=2)
    return specs


def reset_catalog():
    return save_catalog(default_catalog_list())


def load_catalog():
    if not os.path.exists(CATALOG_PATH):
        save_catalog(default_catalog_list())
    with open(CATALOG_PATH, encoding="utf-8") as f:
        items = json.load(f)
    return {s.code: s for s in parse_catalog(items)}


def get_spec(catalog, code):
    if code not in catalog:
        raise ValidationError({"rate_code": f"Tipo de tasa desconocido: {code}"})
    spec = catalog[code]
    if spec.pending:
        raise NeedsInfo({"rate_code": f"La sigla {code} está sin configurar. Defina su significado en el "
                                      f"Catálogo de tasas antes de usarla."})
    return spec


# ------------------------- matemática pura -------------------------

def native_effective(spec, v):
    """Devuelve (r, i): r = tasa periódica declarada, i = efectiva vencida del periodo nativo."""
    r = v / spec.m if spec.kind == "nominal" else v
    if spec.anticipated:
        if r >= 1:
            raise ValidationError({"rate_value": "Una tasa periódica anticipada debe ser menor al 100 %."})
        return r, r / (1 - r)
    return r, r


def ea_of(i, months):
    return dpow(1 + i, D(12) / months) - 1


def period_rate(ea, months):
    return dpow(1 + ea, D(months) / 12) - 1


def express(spec, ea):
    """Valor (fracción) de la tasa `spec` equivalente a la efectiva anual `ea`."""
    i = period_rate(ea, spec.months)
    r = i / (1 + i) if spec.anticipated else i
    return r * spec.m if spec.kind == "nominal" else r


def ea_from(spec, value_pct):
    _, i = native_effective(spec, D(value_pct) / 100)
    return ea_of(i, spec.months)


# ------------------------- explicación -------------------------

def explain_identification(proc, spec, v):
    proc.text(f"La tasa ingresada es **{spec.name} ({spec.code})**: {spec.description()}.")
    proc.math(f"{T(spec.code)} = {P(v)}")
    if spec.kind == "nominal":
        proc.text(f"Es una tasa **nominal**: se expresa como tasa anual y se capitaliza {CAP_NAME[spec.months]} "
                  f"({spec.m} vez/veces al año). Una tasa nominal **no** se puede usar directamente en las fórmulas; "
                  f"primero se convierte en tasa periódica y luego en efectiva.")
    elif spec.months == 12 and not spec.anticipated:
        proc.text("Es una tasa **efectiva anual**: es la tasa de referencia (pivote) para las conversiones.")
    else:
        proc.text(f"Es una tasa **efectiva {PER_NAME[spec.months]}**: se aplica directamente a periodos de "
                  f"{spec.months} mes(es); para otro periodo debe convertirse mediante la EA.")
    if spec.anticipated:
        proc.text("La tasa es **anticipada**: los intereses se cobran al inicio del periodo y deben convertirse "
                  "a vencida.")


def explain_conversion(proc, spec, v, target_months):
    r, i_nat = native_effective(spec, v)
    if spec.kind == "nominal":
        proc.text("Tasa periódica a partir de la nominal: $i_p = J / m$, con $m$ = capitalizaciones por año.")
        proc.math(f"i_p = \\dfrac{{J}}{{m}} = \\dfrac{{{N(v)}}}{{{spec.m}}} = {N(r, 12)}")
    if spec.anticipated:
        proc.text("Conversión de anticipada a vencida: $i = \\dfrac{i_a}{1-i_a}$.")
        proc.math(f"i = \\dfrac{{{N(r, 12)}}}{{1-{N(r, 12)}}} = {N(i_nat, 12)}")
    ea = ea_of(i_nat, spec.months)
    if spec.months != 12 or spec.kind == "nominal" or spec.anticipated:
        proc.text("Tasa efectiva anual (pivote): $EA = (1+i)^{12/p}-1$, con $p$ = meses del periodo.")
        proc.math(f"EA = (1+{N(i_nat, 12)})^{{12/{spec.months}}}-1 = {N(ea, 12)} = {P(ea, 10)}")
    else:
        proc.math(f"EA = {P(ea, 10)}")
    i_t = period_rate(ea, target_months)
    if target_months == 12:
        proc.text("El periodo de cálculo es anual: se usa la EA directamente.")
        proc.math(f"i = EA = {N(i_t, 12)} = {P(i_t, 10)}", result=True)
    else:
        proc.text(f"Tasa efectiva del periodo de cálculo ({target_months} mes(es)): $i = (1+EA)^{{p/12}}-1$.")
        proc.math(f"i = (1+{N(ea, 12)})^{{{target_months}/12}}-1 = {N(i_t, 12)} = {P(i_t, 10)}", result=True)
    return {"ea": ea, "i_native": i_nat, "i_target": i_t, "r_native": r}


def resolve(value_pct, spec, target_months, proc=None):
    """Convierte la tasa ingresada a la efectiva del periodo `target_months` (con pasos 2 y 3 opcionales)."""
    v = D(value_pct) / 100
    if proc is not None:
        proc.step(2, "Identificación de la tasa")
        explain_identification(proc, spec, v)
        proc.step(3, "Conversión de tasas")
        return {**explain_conversion(proc, spec, v, target_months), "value": v}
    r, i_nat = native_effective(spec, v)
    ea = ea_of(i_nat, spec.months)
    return {"ea": ea, "i_native": i_nat, "i_target": period_rate(ea, target_months), "r_native": r, "value": v}


# ------------------------- módulo de tasas (conversión múltiple) -------------------------

def conversion_latex(spec, ea):
    i = period_rate(ea, spec.months)
    lines = [f"i = (1+{N(ea, 12)})^{{{spec.months}/12}}-1 = {N(i, 12)}"]
    r = i
    if spec.anticipated:
        r = i / (1 + i)
        lines.append(f"i_a = \\dfrac{{i}}{{1+i}} = \\dfrac{{{N(i, 12)}}}{{1+{N(i, 12)}}} = {N(r, 12)}")
    if spec.kind == "nominal":
        lines.append(f"J = i \\cdot m = {N(r, 12)} \\cdot {spec.m} = {N(r * spec.m, 12)}")
    lines.append(f"{T(spec.code)} = {P(express(spec, ea), 10)}")
    return lines


def run(data):
    cat = load_catalog()
    rd = Reader(data)
    value = rd.dec("rate_value", "Tasa", min=0)
    code = rd.text("rate_code")
    if not code:
        rd.errors["rate_code"] = "Tipo de tasa: seleccione una opción."
    rd.done()
    spec = get_spec(cat, code)
    v = value / 100
    try:
        target_months = int(data.get("target_months") or 1)
    except ValueError:
        target_months = 0
    if target_months not in VALID_MONTHS:
        raise ValidationError({"target_months": "Periodo de cálculo no válido."})

    proc = Procedure()
    proc.step(1, "Identificación de los datos")
    proc.table([[T("tasa"), "Valor ingresado", P(v)], [T("tipo"), spec.name, T(spec.code)],
                [T("p"), "Periodo de cálculo (meses)", str(target_months)]])
    res = resolve(value, spec, target_months, proc)
    ea = res["ea"]
    proc.step(4, "Identificación de la fórmula financiera")
    proc.text("Para pasar de una modalidad a otra se usa la **equivalencia de tasas**: dos tasas son equivalentes "
              "si producen el mismo valor futuro al cabo de un año. Por eso toda conversión pasa por la EA:")
    proc.math("(1+i_1)^{n_1} = (1+i_2)^{n_2}")
    proc.text("Las nominales se obtienen con $J = i_p \\cdot m$ y las anticipadas con $i_a = i/(1+i)$.")
    proc.step(5, "Sustitución de valores")
    proc.text("Se sustituye la EA calculada en cada modalidad destino (ver cada conversión en el paso 6).")
    proc.step(6, "Desarrollo matemático")
    rows = []
    for c, s in cat.items():
        if s.pending:
            rows.append({"code": c, "name": s.name, "description": s.description(), "value": None,
                         "pending": True, "latex": [], "same": False})
            continue
        val = express(s, ea)
        rows.append({"code": c, "name": s.name, "description": s.description(), "value": val * 100,
                     "pending": False, "latex": conversion_latex(s, ea), "same": c == code})
    for r in rows:
        if r["pending"] or r["same"]:
            continue
        proc.text(f"**{r['name']} ({r['code']})** — {r['description']}")
        for ln in r["latex"][:-1]:
            proc.math(ln, academic=True)
        proc.math(r["latex"][-1])
    proc.step(7, "Resultado final")
    proc.math(f"{T(spec.code)} = {P(v)} \\;\\Longleftrightarrow\\; EA = {P(ea, 10)}", result=True)
    proc.text(f"La tasa efectiva que realmente se usa en un periodo de {target_months} mes(es) es "
              f"**{N(res['i_target'] * 100, 10)} %**.")
    warnings = ["Una tasa nominal nunca se convierte dividiendo o multiplicando directamente hacia una efectiva "
                "de otro periodo: se pasa por la tasa periódica y luego por la EA."]
    if any(r["pending"] for r in rows):
        warnings.append("Hay siglas del catálogo sin configurar (se omiten hasta que las defina).")
    cards = [
        {"key": "ea", "label": "Tasa efectiva anual (EA)", "value": ea * 100, "kind": "pct", "step": 3},
        {"key": "ip", "label": f"Tasa periódica utilizada ({target_months} m)", "value": res["i_target"] * 100,
         "kind": "pct", "step": 3},
        {"key": "native", "label": f"Tasa ingresada ({code})", "value": value, "kind": "pct", "step": 2},
    ]
    return {"module": "rates", "cards": cards, "rates": rows, "procedure": proc.to_list(), "warnings": warnings,
            "schedule": None, "chart": None}
