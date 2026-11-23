# FinMath Lab — Guía de uso

## 1. ¿Qué es y para qué sirve?

FinMath Lab es un simulador web de **matemáticas financieras** hecho en Python. Sirve para estudiar y verificar cálculos de:

- interés compuesto,
- conversión entre tasas de interés,
- anualidades (vencidas y anticipadas) y cuotas de crédito o ahorro,
- equivalencia de obligaciones en una fecha focal,
- comparación de varias simulaciones.

Para cada resultado muestra **el procedimiento matemático completo en 7 pasos**, con fórmulas, sustitución de valores y conclusión. Por eso sirve como herramienta de estudio y para comprobar ejercicios, además de simular créditos.

> Es una herramienta educativa. Los valores iniciales son ejemplos didácticos y no representan tasas comerciales de ninguna entidad.

## 2. Cómo ejecutarla

### Opción A — Ejecutable (sin instalar Python)

1. Haga doble clic en `FinMathLab.exe`, que está junto a `app.py`.
2. Se abre una ventana negra (la consola) y, tras unos segundos, el navegador con la aplicación.
3. Para cerrar la aplicación, cierre la ventana negra.

Notas:
- Si Windows SmartScreen avisa de "editor desconocido", elija *Más información → Ejecutar de todas formas*. El ejecutable no está firmado digitalmente.
- Las fórmulas y los gráficos se cargan desde internet (KaTeX y Chart.js). Los cálculos funcionan sin conexión.

### Opción B — Desde el código

```bash
pip install -r requirements.txt
python app.py          # abre http://127.0.0.1:5000
python -m pytest -q    # pruebas matemáticas (43)
```

### Regenerar el ejecutable

Ejecute `build_exe.bat`. Crea un entorno temporal e instala PyInstaller. Necesita Python 3.10.1 o superior (la 3.10.0 tiene un error que rompe PyInstaller).

## 3. Recorrido por la pantalla

- **Barra lateral:** cambia de módulo (Simulador de cuotas, Interés compuesto, Tasas de interés, Fechas focales, Comparar simulaciones, Guía de tasas).
- **Barra superior:** selector de **moneda** (COP por defecto), interruptor **Sencilla / Académica** y botones **Excel** y **PDF**.
- **Formulario (izquierda):** datos de entrada. Se recalcula solo cuando usted deja de escribir.
- **Resultados (derecha), con tres pestañas:**
  1. **Resultado:** tarjetas con las cifras y gráficos. La cifra calculada aparece destacada.
  2. **Procedimiento:** los 7 pasos matemáticos.
  3. **Tabla:** plan de pagos, tabla de crecimiento o traslado de valores, según el módulo.
- Cada tarjeta tiene un botón **Ver procedimiento** que lleva al paso donde se calculó.
- **Sencilla / Académica:** la vista sencilla oculta las fórmulas largas y deja lo esencial. La académica muestra todo.

### Los 7 pasos del procedimiento

En el paso 4 cada fórmula va acompañada de **la descripción de cada variable** ("Donde: …") y esa descripción se ve también en la vista sencilla.

1. Identificación de los datos.
2. Identificación de la tasa.
3. Conversión de tasas.
4. Identificación de la fórmula financiera.
5. Sustitución de valores.
6. Desarrollo matemático.
7. Resultado final.

## 4. Módulos

### 4.1 Simulador de cuotas

Calcula créditos y planes de ahorro con anualidades.

**Qué puede calcular** (campo *Cálculo*):

| Opción | Pregunta que responde |
|---|---|
| Cuota a partir de la deuda | ¿Cuánto pago por periodo para un crédito de PV? |
| Monto financiable a partir de la cuota | ¿Cuánto me prestan si puedo pagar tal cuota? |
| Cuota de ahorro para una meta | ¿Cuánto ahorro por periodo para llegar a un FV? |
| Valor futuro de mis aportes | ¿Cuánto tendré si aporto tal cuota? |
| Número de cuotas | ¿En cuánto tiempo pago una deuda con esta cuota? |

**Tipo de anualidad:** vencida (pago al final del periodo) o anticipada (pago al inicio). El plan de pagos es lo que antes se llamaba tabla de amortización: muestra cada cuota con su interés y su abono a capital.

**Fórmulas** (con i = tasa efectiva del periodo de pago, n = número de cuotas, A = cuota):

| Caso | Fórmula |
|---|---|
| Valor presente, vencida | PV = A · [1 − (1+i)^−n] / i |
| Valor presente, anticipada | PV = A · [1 − (1+i)^−n] / i · (1+i) |
| Valor futuro, vencida | FV = A · [(1+i)^n − 1] / i |
| Valor futuro, anticipada | FV = A · [(1+i)^n − 1] / i · (1+i) |
| Número de cuotas | n = −ln[1 − PV·i / A] / ln(1+i)  (anticipada: A·(1+i) en el denominador) |

**Datos principales:**
- **Monto / deuda (PV), Meta de ahorro (FV)** o **Cuota**, según lo que se calcule.
- **Tasa:** valor en % y su tipo (EA, NM, TV, …). Se convierte sola a la tasa del periodo de pago.
- **Periodicidad de pago:** mensual, bimestral, trimestral o semestral.
- **Plazo** en meses o años, o directamente el **número de cuotas**.
- **Fecha de nacimiento:** se convierte en edad, útil para créditos con seguro.
- **Fecha inicial** (y final opcional). Si no la indica, usa la de hoy y se lo avisa.
- **Seguro:** ninguno, % mensual sobre saldo, % mensual sobre el monto inicial, o valor fijo mensual.

**Amortización (cómo se paga el crédito):**

| Opción | Qué hace |
|---|---|
| **Normal** | Cuota fija hasta el final del plazo, sin pagos extra. |
| **Abono extra, reducir la cuota** | Con la cuota n.º *k* se paga además un abono extra a capital. El **plazo no cambia**, pero la cuota baja desde la cuota *k+1*: A' = S'·i / [1 − (1+i)^−(n−k)], con S' = saldo − abono. |
| **Abono extra, reducir el plazo** | El mismo abono, pero la **cuota se mantiene** y el crédito termina antes: n' = −ln[1 − S'·i/A] / ln(1+i); la última cuota paga el saldo que quede. |

Los dos tipos de abono ahorran intereses (la tarjeta "Intereses ahorrados" muestra cuánto). El plan de pagos marca la fila del abono y agrega la columna "Abono extra". Disponible al calcular la cuota o el monto financiable de un crédito.

**Resultados:** cuota, total pagado, intereses, capital amortizado, seguro, plan de pagos y gráficos.

Reglas que conviene conocer:
- El seguro "% sobre saldo" no se admite al calcular el monto financiable, porque la cuota total dejaría de ser constante.
- Las anualidades diferidas y las perpetuas no están incluidas.
- El abono extra debe pagarse con una cuota anterior a la última y ser menor que el saldo; si no, la aplicación lo rechaza.
- Si el plazo no es compatible con la periodicidad (por ejemplo 10 meses con pagos trimestrales), la aplicación lo rechaza y lo explica.

### 4.2 Interés compuesto

Cuatro escenarios con un mismo formulario:

| Escenario | Incógnita | Fórmula |
|---|---|---|
| A | Valor futuro | FV = PV·(1+i)ⁿ |
| B | Valor presente | PV = FV·(1+i)⁻ⁿ |
| C | Tasa de interés | i = (FV/PV)^(1/n) − 1 |
| D | Tiempo | n = ln(FV/PV) / ln(1+i) |

Variables: **FV** valor futuro, **PV** valor presente (capital inicial), **i** tasa efectiva del periodo, **n** número de periodos. Se puede indicar el periodo de capitalización y el plazo, o las fechas inicial y final. Devuelve la tabla de crecimiento y una gráfica.

### 4.3 Tasas de interés

Convierte una tasa de un tipo a otro: ingrese el valor, su tipo (EA, EM, NM, TV, …) y el periodo de cálculo. Muestra la EA equivalente, la tasa periódica usada, la fórmula de cada conversión y una tabla con la tasa expresada en todas las modalidades. El nombre completo de cada sigla se muestra siempre.

**Variables:** **i** tasa efectiva (o periódica), **j** tasa nominal, **m** número de periodos por año, **iₐ** tasa efectiva anticipada.

**Nombres y periodos.** La tasa **efectiva (periódica)** y la **nominal** (capitalizable, convertible o vencida) existen en periodo mensual, bimestral, trimestral, cuatrimestral, semestral y anual.

**Reglas de conversión**

- Efectiva ↔ nominal **del mismo periodo**: i = j / m  y  j = i · m.
- Cualquier otro cambio de periodo usa **tasas equivalentes**: (1+i₁)^n₁ = (1+i₂)^n₂, donde n es cuántas veces cabe el periodo en un año.
- Tasas anticipadas: i = iₐ / (1 − iₐ)  e  iₐ = i / (1 + i). **Solo** se pasa de efectiva a anticipada; una nominal nunca se convierte directamente a anticipada. Si se necesita una nominal anticipada, primero se pasa de efectiva a efectiva anticipada y luego jₐ = iₐ · m. Al revés, de nominal anticipada a efectiva: iₐ = jₐ / m y luego i = iₐ / (1 − iₐ). Las tasas anticipadas (efectivas y nominales) se pueden usar como dato de entrada y como resultado en la conversión.

### 4.4 Fechas focales

Traslada obligaciones y pagos a una fecha común para comparar o resolver una incógnita.

En una ecuación de valor la suma de activos es igual a la de pasivos, la de ingresos a la de egresos y la de deudas a la de pagos. Cada valor se traslada con V_F = V·(1+i)^t, donde **V_F** es el valor en la fecha focal, **V** el valor en su fecha, **i** la tasa **efectiva** y **t** la diferencia entre la fecha focal y la fecha del valor (en años). **Nunca se usa una tasa nominal**: siempre se convierte a efectiva.

1. Indique fecha inicial, fecha final, **fecha focal**, tasa y conteo de tiempo (365, 360 o 30/360).
2. Agregue las obligaciones: etiqueta, grupo (**deuda** o **pago**), fecha y monto.
3. Deje **un solo monto en blanco** si quiere que la aplicación lo calcule.

Resultado: línea de tiempo, ecuación de equivalencia (Σdeudas = Σpagos) y el valor de la incógnita o la diferencia entre ambos lados.

### 4.5 Comparar simulaciones

Compara créditos con los mismos datos base y distinto plazo (por ejemplo 12, 24 y 36 meses). Muestra la cuota, los intereses y el total pagado de cada uno, las diferencias entre ellos y cuál sale más económico, con un gráfico de barras.

### 4.6 Guía de tasas

Tabla de consulta (solo lectura) con las siglas disponibles, su nombre completo, tipo, periodo, número de periodos por año (m) y si son vencidas o anticipadas, junto con las reglas de conversión.

Siglas:

- Efectivas vencidas: EA, ES, EV (cuatrimestral), ET, EB, EM.
- Nominales vencidas (capitalizables): NA, NS, NV, NT, NB, NM, y TV, MV (trimestre y mes vencido).
- **Efectivas anticipadas:** EAA, ESA, EVA, ETA, EBA, EMA.
- **Nominales anticipadas:** NAA, NSA, NVA, TA (trimestre anticipado), NBA, MA (mes anticipado).

## 5. Exportar

Los botones **Excel** y **PDF** de la barra superior descargan el módulo activo: datos, resultados, procedimiento y tablas. El archivo se recalcula en el servidor con los mismos datos, así que coincide con la pantalla.

## 6. Precisión y validaciones

- Los cálculos usan aritmética decimal de 50 dígitos y **no redondean los pasos intermedios**. Solo se redondea al mostrar (el dinero se muestra con 2 decimales).
- Si falta un dato o hay una combinación imposible, aparece un aviso claro junto al campo y no se calcula nada con valores inventados.
- Tasa cero, plazos fraccionarios (con ajuste de la última cuota) y valores no válidos están contemplados.

## 7. Estructura del proyecto

```
app.py              Punto de entrada (servidor o ejecutable)
FinMathLab.exe      Ejecutable para Windows
build_exe.bat       Genera el ejecutable
finmath/            Lógica financiera (sin dependencia de la web)
web/                Interfaz: plantilla, CSS y JavaScript
exports/            Exportación a Excel y PDF
tests/              Pruebas matemáticas
docs/               Esta documentación
```

## 8. Problemas frecuentes

| Problema | Causa y solución |
|---|---|
| Las fórmulas se ven como código o no hay gráficos | No hay internet; KaTeX y Chart.js se cargan en línea. |
| La página no abre al ejecutar el .exe | Abra manualmente la dirección que muestra la ventana negra (normalmente http://127.0.0.1:5000). |
| El antivirus bloquea el .exe | Es un falso positivo habitual de los ejecutables creados con PyInstaller. Permítalo o ejecute desde el código. |
| "Operación matemática inválida" | Revise tasa, plazo y valores; por ejemplo, una tasa de −100 % o un plazo en cero. |
