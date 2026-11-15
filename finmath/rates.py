"""Catálogo de tasas, conversión y explicación paso a paso.

Nomenclatura (fija, definida por el curso):
  i   tasa efectiva (o periódica)            j   tasa nominal (capitalizable, convertible o vencida)
  m   número de periodos (capitalizaciones) por año
  ia  tasa efectiva anticipada

Reglas:
  * Efectiva <-> nominal del MISMO periodo:   i = j/m   y   j = i·m.
  * Cualquier otro cambio de periodo usa tasas equivalentes:  (1+i1)^n1 = (1+i2)^n2,
    con n = cuántas veces cabe el periodo en un año.
  * Anticipadas: solo se pasa de efectiva a efectiva anticipada (ia = i/(1+i)) y viceversa (i = ia/(1-ia)).
    Nunca se convierte una nominal directamente a anticipada: primero i -> ia y luego j_a = ia·m.
Internamente toda conversión pasa por la tasa efectiva anual (EA), que es el caso n = 1 de la equivalencia.
"""
from dataclasses import dataclass, asdict

from .precision import D, dpow
from .steps import N, P, T, Procedure
from .validation import ValidationError, Reader

VALID_MONTHS = (1, 2, 3, 4, 6, 12)
PER_NAME = {1: "mensual", 2: "bimestral", 3: "trimestral", 4: "cuatrimestral", 6: "semestral", 12: "anual"}
CAP_NAME = {1: "mensualmente", 2: "bimestralmente", 3: "trimestralmente", 4: "cuatrimestralmente",
            6: "semestralmente", 12: "anualmente"}


@dataclass(frozen=True)
class RateSpec:
    code: str
    name: str
    kind: str            # 'effective' | 'nominal'
    months: int          # periodo de la efectiva o de capitalización de la nominal
    anticipated: bool = False
    note: str = ""

    @property
    def m(self):  # periodos (capitalizaciones) por año
        return 12 // self.months

    def description(self):
        ant = " anticipada" if self.anticipated else " vencida"
        if self.kind == "effective":
            return f"Tasa efectiva (periódica) {PER_NAME[self.months]}{ant}"
        return f"Tasa nominal anual capitalizable (convertible) {CAP_NAME[self.months]}{ant}"

    def to_dict(self):
        d = asdict(self)
        d["description"] = self.description()
        d["m"] = self.m
        return d


CATALOG = [
    RateSpec("EA", "Efectiva Anual", "effective", 12),
    RateSpec("ES", "Efectiva Semestral", "effective", 6),
    RateSpec("EV", "Efectiva Cuatrimestral", "effective", 4),
    RateSpec("ET", "Efectiva Trimestral", "effective", 3),
    RateSpec("EB", "Efectiva Bimestral", "effective", 2),
    RateSpec("EM", "Efectiva Mensual", "effective", 1),
    RateSpec("NA", "Nominal Anual (capitalización anual)", "nominal", 12),
    RateSpec("NS", "Nominal Anual capitalizable Semestral", "nominal", 6),
    RateSpec("NV", "Nominal Anual capitalizable Cuatrimestral", "nominal", 4),
    RateSpec("NT", "Nominal Anual capitalizable Trimestral", "nominal", 3),
    RateSpec("NB", "Nominal Anual capitalizable Bimestral", "nominal", 2),
    RateSpec("NM", "Nominal Anual capitalizable Mensual", "nominal", 1),
    RateSpec("TV", "Nominal Anual Trimestre Vencido", "nominal", 3),
    RateSpec("MV", "Nominal Anual Mes Vencido", "nominal", 1),
    RateSpec("TA", "Nominal Anual Trimestre Anticipado", "nominal", 3, anticipated=True),
    RateSpec("MA", "Nominal Anual Mes Anticipado", "nominal", 1, anticipated=True),
]


def load_catalog():
    return {s.code: s for s in CATALOG}


def get_spec(catalog, code):
    if code not in catalog:
        raise ValidationError({"rate_code": f"Tipo de tasa desconocido: {code}"})
    return catalog[code]


# ------------------------- matemática pura -------------------------

def native_effective(spec, v):
    """Devuelve (r, i): r = tasa periódica declarada (j/m si es nominal), i = efectiva vencida del periodo nativo."""
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
    proc.text(f"La tasa ingresada es **{spec.name} ({spec.code})**: {spec.description()}.", academic=False)
    proc.math(f"{T(spec.code)} = {P(v)}")
    if spec.kind == "nominal":
        proc.text(f"Es una tasa **nominal** ($j$): se expresa como tasa anual y se capitaliza {CAP_NAME[spec.months]} "
                  f"($m = {spec.m}$ periodos por año). Una tasa nominal **nunca** se usa directamente en las "
                  f"fórmulas de valor: primero se convierte en tasa efectiva.", academic=False)
    elif spec.months == 12 and not spec.anticipated:
        proc.text("Es una tasa **efectiva anual**: es la tasa de referencia para las conversiones.", academic=False)
    else:
        proc.text(f"Es una tasa **efectiva** ($i$) **{PER_NAME[spec.months]}**: se aplica directamente a periodos de "
                  f"{spec.months} mes(es); para otro periodo debe convertirse con tasas equivalentes.", academic=False)
    if spec.anticipated:
        proc.text("La tasa es **anticipada** ($i_a$): los intereses se cobran al inicio del periodo y deben "
                  "convertirse a vencida antes de usarla.", academic=False)
    proc.where([("i", "tasa efectiva (periódica)"), ("j", "tasa nominal"),
                ("m", "número de periodos por año"), ("i_a", "tasa efectiva anticipada")])


def explain_conversion(proc, spec, v, target_months):
    r, i_nat = native_effective(spec, v)
    # 1) nominal -> efectiva del MISMO periodo:  i = j/m
    if spec.kind == "nominal":
        sym = "i_a" if spec.anticipated else "i"
        proc.text(f"Nominal a efectiva del mismo periodo (única conversión directa permitida): ${sym} = \\dfrac{{j}}{{m}}$.",
                  academic=False)
        proc.math(f"{sym} = \\dfrac{{j}}{{m}} = \\dfrac{{{N(v)}}}{{{spec.m}}} = {N(r, 12)} = {P(r, 10)}")
    # 2) anticipada -> vencida: i = ia/(1-ia)
    if spec.anticipated:
        proc.text("Efectiva anticipada a efectiva vencida: $i = \\dfrac{i_a}{1-i_a}$.", academic=False)
        proc.math(f"i = \\dfrac{{{N(r, 12)}}}{{1-{N(r, 12)}}} = {N(i_nat, 12)} = {P(i_nat, 10)}")
    # 3) cambio de periodo: tasas equivalentes
    ea = ea_of(i_nat, spec.months)
    n_nat, n_t = 12 // spec.months, 12 // target_months
    if spec.months == target_months:
        proc.text(f"El periodo de la tasa coincide con el periodo de cálculo ({target_months} mes(es)): "
                  f"no hace falta convertir.", academic=False)
        i_t = i_nat
        proc.math(f"i = {N(i_t, 12)} = {P(i_t, 10)}", result=True)
    else:
        proc.text("El periodo es distinto: se usan **tasas equivalentes** $(1+i_1)^{n_1} = (1+i_2)^{n_2}$, donde "
                  "$n$ es cuántas veces cabe el periodo en un año ($n = 12/\\text{meses del periodo}$).",
                  academic=False)
        i_t = period_rate(ea, target_months)
        proc.math(f"(1+{N(i_nat, 12)})^{{{n_nat}}} = (1+i_2)^{{{n_t}}}")
        proc.math(f"i_2 = (1+{N(i_nat, 12)})^{{{n_nat}/{n_t}}}-1 = {N(i_t, 12)} = {P(i_t, 10)}", result=True)
    proc.math(f"EA = (1+{N(i_nat, 12)})^{{{n_nat}}}-1 = {N(ea, 12)} = {P(ea, 10)}", academic=True)
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
    """Del valor efectivo anual a la modalidad `spec`: equivalencia -> (anticipada) -> (nominal)."""
    i = period_rate(ea, spec.months)
    n = 12 // spec.months
    lines = []
    if spec.months == 12:
        lines.append(f"i = EA = {N(ea, 12)}")
    else:
        lines.append(f"(1+{N(ea, 12)})^{{1}} = (1+i)^{{{n}}} \\Rightarrow i = (1+{N(ea, 12)})^{{1/{n}}}-1 = {N(i, 12)}")
    r = i
    if spec.anticipated:
        r = i / (1 + i)
        lines.append(f"i_a = \\dfrac{{i}}{{1+i}} = \\dfrac{{{N(i, 12)}}}{{1+{N(i, 12)}}} = {N(r, 12)}")
    if spec.kind == "nominal":
        sym = "i_a" if spec.anticipated else "i"
        lines.append(f"j = {sym} \\cdot m = {N(r, 12)} \\cdot {spec.m} = {N(r * spec.m, 12)}")
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
    proc.text("Se usan tres fórmulas, cada una en su caso:", academic=False)
    proc.math("i = \\dfrac{j}{m} \\qquad j = i \\cdot m")
    proc.where([("i", "tasa efectiva (periódica)"), ("j", "tasa nominal"), ("m", "número de periodos por año")])
    proc.text("Esta pareja **solo** sirve entre una efectiva y una nominal **del mismo periodo**. Para cualquier otro "
              "cambio de periodo se usan **tasas equivalentes**:", academic=False)
    proc.math("(1+i_1)^{n_1} = (1+i_2)^{n_2}")
    proc.where([("i_1,\\,i_2", "tasas efectivas de los dos periodos"),
                ("n_1,\\,n_2", "cuántas veces cabe cada periodo en un año")])
    proc.text("Tasas anticipadas: **solo** se pasa de efectiva a efectiva anticipada, nunca de una nominal "
              "directamente a anticipada. Si se necesita una nominal anticipada, primero $i \\to i_a$ y luego "
              "$j_a = i_a \\cdot m$.", academic=False)
    proc.math("i = \\dfrac{i_a}{1-i_a} \\qquad i_a = \\dfrac{i}{1+i}")
    proc.where([("i", "tasa efectiva vencida"), ("i_a", "tasa efectiva anticipada")])
    proc.step(5, "Sustitución de valores")
    proc.text("Se sustituye la EA calculada en cada modalidad destino (ver cada conversión en el paso 6).")
    proc.step(6, "Desarrollo matemático")
    rows = []
    for c, s in cat.items():
        val = express(s, ea)
        rows.append({"code": c, "name": s.name, "description": s.description(), "value": val * 100,
                     "latex": conversion_latex(s, ea), "same": c == code})
    for r in rows:
        if r["same"]:
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
                "de otro periodo: solo $i = j/m$ y $j = i\\cdot m$ del mismo periodo; en otro caso, tasas equivalentes."]
    cards = [
        {"key": "ea", "label": "Tasa efectiva anual (EA)", "value": ea * 100, "kind": "pct", "step": 3},
        {"key": "ip", "label": f"Tasa periódica utilizada ({target_months} m)", "value": res["i_target"] * 100,
         "kind": "pct", "step": 3},
        {"key": "native", "label": f"Tasa ingresada ({code})", "value": value, "kind": "pct", "step": 2},
    ]
    return {"module": "rates", "cards": cards, "rates": rows, "procedure": proc.to_list(), "warnings": warnings,
            "schedule": None, "chart": None}
