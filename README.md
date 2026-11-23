# FinMath Lab · Simulador de matemáticas financieras (Python)

Simulador web educativo: interés compuesto, conversión de tasas, anualidades/cuotas, fechas focales, comparación de
escenarios, tabla de amortización y procedimiento matemático paso a paso (KaTeX).

## Ejecutar

```bash
pip install -r requirements.txt
python app.py          # http://127.0.0.1:5000
python -m pytest -q    # pruebas matemáticas
```

Sin Python: doble clic en `FinMathLab.exe` (se regenera con `build_exe.bat`). Guía completa en `docs/` (Word y Markdown).

> KaTeX y Chart.js se cargan desde cdnjs, por lo que la interfaz necesita internet. Los cálculos no.

## Arquitectura

```
finmath/      Lógica financiera pura (sin Flask ni HTML). Decimal con 50 dígitos; no se redondean intermedios.
  rates.py          Catálogo fijo de tasas, conversión (i=j/m, tasas equivalentes, anticipadas), pasos 2-3
  compound.py       Escenarios A (FV), B (PV), C (tasa), D (tiempo)
  annuities.py      Vencida y anticipada; ahorro y crédito (plan de pagos); seguros
  amortization.py   Plan de pagos / tabla de acumulación
  focal_dates.py    Equivalencia en fecha focal, incógnita, línea de tiempo
  comparison.py     Comparación de simulaciones (12/24/36 meses, etc.)
  steps.py          Constructor del procedimiento (pasos 1-7, LaTeX)
  validation.py     Validación; pide los datos que faltan en vez de inventarlos
  service.py        Fachada + serialización JSON
web/          Flask (API JSON) + plantilla + CSS + JS por módulos (ES modules)
exports/      Excel (openpyxl) y PDF (reportlab), recalculados en el servidor
tests/        pytest
```

## Convenciones

* Nomenclatura: **i** efectiva (periódica), **j** nominal, **m** periodos por año, **iₐ** efectiva anticipada.
* Efectiva ↔ nominal del mismo periodo: i = j/m, j = i·m. Otro cambio de periodo: tasas equivalentes (1+i₁)^n₁ = (1+i₂)^n₂.
* Anticipadas: i = iₐ/(1−iₐ), iₐ = i/(1+i). Una nominal nunca pasa directo a anticipada: primero i → iₐ y luego jₐ = iₐ·m.
* Ecuaciones de valor / fechas focales: nunca tasa nominal, siempre efectiva; tiempo en años con base 365 (o 360 / 30/360).
* Anualidades: vencida y anticipada (sin diferidas ni perpetuas). El plan de pagos reemplaza a la "amortización".
* Amortización: normal, o con abono extra a capital que **reduce la cuota** (mismo plazo) o **reduce el plazo** (misma cuota).
* Seguro: valor mensual (% sobre saldo, % sobre monto inicial o fijo); en periodos de varios meses se multiplica por los
  meses del periodo.
* Si no se indica fecha inicial se usa la de hoy (y se avisa).
