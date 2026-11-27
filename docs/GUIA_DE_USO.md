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
python -m pytest -q    # pruebas matemáticas (48)
```

### Regenerar el ejecutable

Ejecute `build_exe.bat`. Crea un entorno temporal e instala PyInstaller. Necesita Python 3.10.1 o superior (la 3.10.0 tiene un error que rompe PyInstaller).

## 3. Recorrido por la pantalla

- **Barra lateral:** cambia de módulo (Simulador de cuotas, Interés compuesto, Tasas de interés, Fechas focales (ecuaciones de valor), Comparar simulaciones, Guía de tasas).
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

### 4.4 Ecuaciones de valor y fechas focales

Resuelve ejercicios de ecuaciones de valor: saldos, pagos únicos, refinanciaciones y cuotas iguales que reemplazan un plan de pagos.

En una ecuación de valor la suma de activos es igual a la de pasivos, la de ingresos a la de egresos y la de deudas a la de pagos:

Σ deudas · (1+i)^t = Σ pagos · (1+i)^t

donde **i** es la tasa **efectiva** (nunca se usa la nominal: si el ejercicio da una nominal, la aplicación la convierte primero) y **t** es la fecha focal menos el momento de cada valor (positivo: se capitaliza; negativo: se descuenta).

**Cómo plantear un ejercicio**

1. **Medir el tiempo en:** *Periodos* (lo normal en clase: mes 0 = hoy, mes 5, …) o *Fechas del calendario* (días reales con base 365, 360 o 30/360).
2. En periodos, elija la duración de cada periodo (mes, trimestre, …) y el **periodo focal**. La tasa se convierte a la efectiva de ese periodo.
3. Escriba la tasa tal como la da el enunciado (por ejemplo 24 % TA = nominal trimestral anticipada).
4. Agregue cada valor en su lado:
   - **Deuda / depósito:** lo que se debe, lo que se compra o lo que se deposita.
   - **Pago / retiro:** lo que se paga o se retira, incluido el saldo que se busca.
5. Deje en blanco el valor que se quiere hallar. Si deja **varias filas en blanco, todas son el mismo valor x** (por ejemplo "tres cuotas iguales").
6. Si una deuda ya tiene intereses propios ("préstamo contratado a 18 meses al 12 %"), abra **Intereses propios** en esa fila y escriba su tasa y su plazo original en meses: primero se calcula su valor al vencimiento S = P(1+i)^n.

El resultado muestra el diagrama (línea de tiempo con cada valor y su traslado al foco), la ecuación con los datos, el despeje de x y la tabla de traslado.

**Ejercicios de ejemplo.** El selector "Cargar un ejercicio de ejemplo" trae seis ejercicios ya planteados:

| Ejercicio | Planteamiento | Resultado |
|---|---|---|
| 1. Depósito de $100.000 al 30 % anual, retiros de $20.000 (mes 1) y $30.000 (mes 3) | Foco mes 6, tasa EA | Saldo = $59.673,49 |
| 2. Sebastián: Q10.000 (préstamo a 18 meses al 12 %) y Q25.000; paga Q20.000 hoy | Foco mes 12, 10 % EA, interés compuesto | Pago único = Q16.034,34 |
| 3. Deuda de $320.000 en el periodo 3; $100.000 hoy y $200.000 en el periodo 5 | Foco periodo 3, 3 % efectivo | Saldo = $22.208,12 |
| 4. Empresa xyz: $10.000.000 al 2 % mensual, abono de $7.000.000 en el mes 5 | Foco mes 12 | Saldo = $4.641.618,27 |
| 5. Pablo Pérez: auto de $60.000.000 | 24 % nominal mes vencido (2 % mensual) | Saldo mes 10 = $16.730.923,35 |
| 6. Angelo Pulido: tres cuotas iguales en octubre, noviembre y diciembre | 24 % nominal trimestral anticipado | Cuota = $1.131.326,01 |

> Ejercicio 2: el enunciado parece de un libro que usa **interés simple**; con interés simple el pago sería Q16.015. La aplicación usa interés compuesto, que es lo que se ve en el curso.

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
