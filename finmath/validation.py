"""Lectura y validación de datos de entrada. Nunca se inventan valores."""
from datetime import date
from decimal import Decimal, InvalidOperation

from .precision import D


class ValidationError(Exception):
    def __init__(self, errors, message=None):
        if isinstance(errors, str):
            errors = {"_": errors}
        self.errors = errors
        self.message = message or "; ".join(errors.values())
        super().__init__(self.message)


class NeedsInfo(ValidationError):
    """Falta información necesaria: se solicita al usuario en vez de suponerla."""


def blank(v):
    return v is None or (isinstance(v, str) and v.strip() == "")


class Reader:
    def __init__(self, data):
        self.data = data or {}
        self.errors = {}

    def has(self, key):
        return not blank(self.data.get(key))

    def dec(self, key, label, *, required=True, min=None, gt=None, max=None):
        raw = self.data.get(key)
        if blank(raw):
            if required:
                self.errors[key] = f"{label}: es obligatorio para este cálculo."
            return None
        try:
            v = D(raw)
            if not v.is_finite():
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            self.errors[key] = f"{label}: valor numérico inválido."
            return None
        if min is not None and v < D(min):
            self.errors[key] = f"{label}: no puede ser menor que {min}."
        elif gt is not None and v <= D(gt):
            self.errors[key] = f"{label}: debe ser mayor que {gt}."
        elif max is not None and v > D(max):
            self.errors[key] = f"{label}: no puede ser mayor que {max}."
        return v

    def integer(self, key, label, *, required=True, min=None, max=None):
        v = self.dec(key, label, required=required, min=min, max=max)
        if v is None:
            return None
        if v != v.to_integral_value():
            self.errors[key] = f"{label}: debe ser un número entero."
            return None
        return int(v)

    def date(self, key, label, *, required=True):
        raw = self.data.get(key)
        if blank(raw):
            if required:
                self.errors[key] = f"{label}: es obligatoria."
            return None
        try:
            return date.fromisoformat(str(raw)[:10])
        except ValueError:
            self.errors[key] = f"{label}: fecha inválida."
            return None

    def choice(self, key, label, options, default=None):
        raw = self.data.get(key)
        if blank(raw):
            if default is not None:
                return default
            self.errors[key] = f"{label}: seleccione una opción."
            return None
        if str(raw) not in [str(o) for o in options]:
            self.errors[key] = f"{label}: opción no válida."
            return None
        return str(raw)

    def text(self, key, default=""):
        raw = self.data.get(key)
        return default if blank(raw) else str(raw).strip()

    def done(self):
        if self.errors:
            raise ValidationError(self.errors)
