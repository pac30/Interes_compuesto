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
  rates.py          Catálogo configurable, conversión vía EA, pasos 2-3
  compound.py       Escenarios A (FV), B (PV), C (tasa), D (tiempo)
  annuities.py      Vencida, anticipada, diferida, perpetua; ahorro y crédito; seguros
  amortization.py   Tablas de amortización / acumulación
  focal_dates.py    Equivalencia en fecha focal, incógnita, línea de tiempo
  comparison.py     Comparación de simulaciones (12/24/36 meses, etc.)
  steps.py          Constructor del procedimiento (pasos 1-7, LaTeX)
  validation.py     Validación; pide los datos que faltan en vez de inventarlos
  service.py        Fachada + serialización JSON
web/          Flask (API JSON) + plantilla + CSS + JS por módulos (ES modules)
exports/      Excel (openpyxl) y PDF (reportlab), recalculados en el servidor
config/rate_catalog.json   Catálogo de siglas editable (también desde la interfaz)
tests/        pytest
```

## Convenciones (editables en el Catálogo de tasas)

* Tasa nominal: siempre anual, con periodo de capitalización; periódica = J/m.
* TV = nominal anual trimestre vencido; MV = nominal anual mes vencido; TA/MA = anticipadas.
* **MT** viene "por configurar": no se puede usar hasta definir su significado.
* Fechas focales: tiempo en años con base 365 (o 360 / 30/360), tasa convertida a EA.
* Diferida: periodos de gracia con intereses capitalizados; el plazo ingresado cuenta solo los pagos.
* Seguro: valor mensual (% sobre saldo, % sobre monto inicial o fijo); en periodos de varios meses se multiplica por los
  meses del periodo; no se cobra en gracia.
* Si no se indica fecha inicial se usa la de hoy (y se avisa).
