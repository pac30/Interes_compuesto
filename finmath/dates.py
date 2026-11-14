"""Utilidades de fechas."""
import math
from datetime import date, timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta

from .precision import D


def add_months(d: date, months) -> date:
    months = D(months)
    whole = int(months.to_integral_value(rounding="ROUND_FLOOR"))
    frac = months - whole
    out = d + relativedelta(months=whole)
    if frac:
        out += timedelta(days=int(round(float(frac) * 30)))
    return out


def months_between(start: date, end: date) -> Decimal:
    """Meses completos entre las fechas más fracción de días / 30."""
    if end < start:
        return D(0)
    rd = relativedelta(end, start)
    return D(rd.years * 12 + rd.months) + D(rd.days) / 30


def age_on(birth: date, ref: date) -> int:
    return ref.year - birth.year - ((ref.month, ref.day) < (birth.month, birth.day))


def days360(a: date, b: date) -> int:
    """Convención 30/360 (US/NASD)."""
    d1, d2 = min(a.day, 30), b.day
    if d2 == 31 and d1 >= 30:
        d2 = 30
    return (b.year - a.year) * 360 + (b.month - a.month) * 30 + (d2 - d1)


def year_fraction(a: date, b: date, basis: str) -> Decimal:
    """Años entre a y b (negativo si b < a) según la base: 365, 360 o 30/360."""
    if basis == "30/360":
        return D(days360(a, b)) / 360
    base = 365 if basis == "365" else 360
    return D((b - a).days) / base
