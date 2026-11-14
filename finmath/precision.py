"""Aritmética de alta precisión: nunca se redondean valores intermedios."""
import decimal
from decimal import Decimal

PREC = 50
decimal.DefaultContext.prec = PREC   # hilos nuevos (Flask)
decimal.getcontext().prec = PREC     # hilo actual

ZERO = Decimal(0)
ONE = Decimal(1)


def D(x) -> Decimal:
    if isinstance(x, Decimal):
        return x
    if isinstance(x, float):
        return Decimal(repr(x))
    return Decimal(str(x).strip().replace(",", "."))


def dpow(base, exp) -> Decimal:
    return D(base) ** D(exp)


def dln(x) -> Decimal:
    return D(x).ln()
