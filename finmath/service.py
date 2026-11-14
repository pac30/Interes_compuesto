"""Fachada: despacha módulos y serializa Decimal/date a JSON (cadenas, sin perder precisión)."""
from datetime import date
from decimal import Decimal

from . import annuities, compound, comparison, focal_dates, rates
from .validation import ValidationError

MODULES = {
    "rates": rates.run,
    "compound": compound.run,
    "annuity": annuities.run,
    "focal": focal_dates.run,
    "compare": comparison.run,
}


def jsonable(x):
    if isinstance(x, Decimal):
        return format(x, "f") if x.is_finite() else None
    if isinstance(x, date):
        return x.isoformat()
    if isinstance(x, dict):
        return {k: jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [jsonable(v) for v in x]
    return x


HERO_BY_MODE = {"cuota_pv": "cuota", "pv_cuota": "pv", "cuota_fv": "cuota", "fv_cuota": "fv", "n_pv_cuota": "n"}
HERO_BY_SCENARIO = {"A": "fv", "B": "pv", "C": "rate", "D": "n"}


def _mark_hero(module, result):
    """Marca la tarjeta principal (la magnitud calculada) para destacarla en la interfaz."""
    if module == "annuity":
        key = HERO_BY_MODE.get(result.get("mode"))
    elif module == "compound":
        key = HERO_BY_SCENARIO.get(result.get("scenario"))
    elif module == "focal":
        key = "x" if any(c["key"] == "x" for c in result["cards"]) else "diff"
    elif module == "compare":
        key = "best"
    else:
        key = "ea"
    for c in result.get("cards", []):
        c["hero"] = c["key"] == key
    return result


def run(module, data):
    if module not in MODULES:
        raise ValidationError({"_": f"Módulo desconocido: {module}"})
    return _mark_hero(module, MODULES[module](data or {}))


def run_json(module, data):
    return jsonable(run(module, data))
