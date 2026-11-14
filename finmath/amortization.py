"""Tablas de amortización (créditos) y de acumulación (ahorros), sin redondear valores intermedios."""
from decimal import Decimal

from .dates import add_months
from .precision import ZERO, D

EPS = Decimal("1e-20")


def _clean(x):
    return ZERO if abs(x) < EPS else x


class Insurance:
    """Seguro: 'none' | 'pct_balance' (% mensual sobre saldo) | 'pct_initial' (% mensual sobre el monto)
    | 'fixed' (valor mensual fijo). Para periodos de p meses se multiplica por p."""

    def __init__(self, kind="none", value=ZERO, pv=ZERO, p=1):
        self.kind, self.value, self.pv, self.p = kind, D(value), D(pv), D(p)

    def amount(self, opening):
        if self.kind == "pct_balance":
            return opening * self.value / 100 * self.p
        if self.kind == "pct_initial":
            return self.pv * self.value / 100 * self.p
        if self.kind == "fixed":
            return self.value * self.p
        return ZERO


def loan_schedule(pv, i, n, cuota, due=False, defer=0, start=None, p=1, insurance=None, adjust_last=False):
    """Cronograma de un crédito.

    - defer: periodos de gracia con intereses capitalizados (periodo muerto).
    - due:   cuotas anticipadas (la primera cuota se paga al inicio del primer periodo de pago).
    - adjust_last: la última cuota paga exactamente el saldo (cuando n no es entero).
    """
    ins = insurance or Insurance()
    rows, bal, k = [], D(pv), 0
    for t in range(1, defer + 1):
        k += 1
        interest = bal * i
        rows.append({"n": k, "date": add_months(start, t * p) if start else None, "phase": "gracia",
                     "opening": bal, "interest": interest, "capital": -interest, "payment": ZERO,
                     "insurance": ZERO, "total": ZERO, "closing": bal + interest})
        bal += interest
    for j in range(1, n + 1):
        k += 1
        opening = bal
        interest = ZERO if (due and j == 1) else opening * i
        last = j == n
        pay = (opening + interest) if (adjust_last and last) else D(cuota)
        capital = pay - interest
        closing = _clean(opening - capital)
        offset = (defer + j - 1) if due else (defer + j)
        seg = ins.amount(opening)
        rows.append({"n": k, "date": add_months(start, offset * p) if start else None, "phase": "pago",
                     "opening": opening, "interest": interest, "capital": capital, "payment": pay,
                     "insurance": seg, "total": pay + seg, "closing": closing})
        bal = closing
    return rows


def savings_schedule(i, n, aporte, due=False, start=None, p=1):
    rows, bal = [], ZERO
    for j in range(1, n + 1):
        opening = bal
        if due:
            interest = (opening + aporte) * i
        else:
            interest = opening * i
        closing = opening + interest + aporte
        offset = (j - 1) if due else j
        rows.append({"n": j, "date": add_months(start, offset * p) if start else None, "phase": "aporte",
                     "opening": opening, "interest": interest, "capital": D(aporte), "payment": D(aporte),
                     "insurance": ZERO, "total": D(aporte), "closing": closing})
        bal = closing
    return rows
