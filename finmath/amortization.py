"""Plan de pagos (créditos) y tabla de acumulación (ahorros), sin redondear valores intermedios."""
from decimal import Decimal

from .dates import add_months
from .precision import ZERO, D, dpow

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


def _annuity_factor(i, n):
    """a_{n|i} de una anualidad vencida (n puede ser 0 solo si no hay cuotas pendientes)."""
    return D(n) if i == 0 else (1 - dpow(1 + i, -D(n))) / i


def loan_schedule(pv, i, n, cuota, due=False, start=None, p=1, insurance=None, adjust_last=False, extra=None):
    """Plan de pagos de un crédito.

    - due:   cuotas anticipadas (la primera cuota se paga al inicio del primer periodo de pago).
    - adjust_last: la última cuota paga exactamente el saldo (cuando n no es entero).
    - extra: (tipo, valor, k) abono extraordinario a capital que se paga junto con la cuota k.
        tipo 'reduce_cuota': el plazo no cambia; la cuota se recalcula con el saldo restante.
        tipo 'reduce_term' : la cuota no cambia; se acorta el plazo (la última cuota paga el saldo).
    """
    ins = insurance or Insurance()
    kind, extra_amt, extra_k = extra if extra else (None, ZERO, 0)
    rows, bal = [], D(pv)
    pay_amt, n_end, j, shortened = D(cuota), n, 0, False
    while j < n_end:
        j += 1
        opening = bal
        interest = ZERO if (due and j == 1) else opening * i
        if shortened:  # plazo reducido: se paga la cuota hasta que alcance el saldo
            last = opening + interest <= pay_amt * (1 + D("1e-30"))
            pay = (opening + interest) if last else pay_amt
            if not last:
                n_end = j + 1
        else:
            last = j == n_end
            pay = (opening + interest) if (adjust_last and last) else pay_amt
        capital = pay - interest
        closing = _clean(opening - capital)
        row_extra = None
        if kind and j == extra_k:
            row_extra = D(extra_amt)
            closing = _clean(closing - row_extra)
            if kind == "reduce_cuota":
                pay_amt = closing / _annuity_factor(i, n - j)
            else:
                shortened = True
                n_end = j + 1  # se sigue mientras quede saldo
        offset = (j - 1) if due else j
        seg = ins.amount(opening)
        rows.append({"n": j, "date": add_months(start, offset * p) if start else None, "phase": "pago",
                     "opening": opening, "interest": interest, "capital": capital, "payment": pay,
                     "extra": row_extra, "insurance": seg, "total": pay + seg, "closing": closing})
        bal = closing
        if shortened and closing == 0:
            break
        if j > 5000:
            break
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
