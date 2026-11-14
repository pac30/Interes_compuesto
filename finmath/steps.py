"""Constructor del procedimiento matemático (pasos 1 a 7) en notación LaTeX.

Cada ítem lleva `academic=True` si solo debe verse en la vista académica.
"""
from .precision import D

THIN = "\\,"


def N(x, dp=8, trim=True):
    s = f"{D(x):,.{dp}f}"
    if trim and "." in s:
        s = s.rstrip("0").rstrip(".")
    return s.replace(",", THIN)


def M(x, dp=2):
    return N(x, dp, trim=False)


def P(x, dp=8):
    return N(D(x) * 100, dp) + "\\%"


def T(s):
    s = str(s).replace("%", "\\%").replace("_", "\\_").replace("&", "\\&")
    return "\\text{" + s + "}"


class Procedure:
    def __init__(self):
        self.steps = []
        self._cur = None

    def step(self, n, title):
        self._cur = {"n": n, "title": title, "items": []}
        self.steps.append(self._cur)
        return self

    def text(self, t, academic=True):
        self._cur["items"].append({"kind": "text", "content": t, "academic": academic})

    def math(self, latex, academic=False, result=False):
        self._cur["items"].append({"kind": "math", "content": latex, "academic": academic, "result": result})

    def table(self, rows, academic=False):
        """rows: [variable, descripción, valor]"""
        self._cur["items"].append({"kind": "table", "rows": rows, "academic": academic})

    def to_list(self):
        return self.steps
