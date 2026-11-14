# FinMath Lab — Guía de uso

## 1. ¿Qué es y para qué sirve?

FinMath Lab es un simulador web de **matemáticas financieras** hecho en Python. Sirve para estudiar y verificar cálculos de:

- interés compuesto,
- conversión entre tasas de interés,
- anualidades y cuotas de crédito o ahorro,
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
- El catálogo de tasas se guarda en la carpeta `config` junto al ejecutable.

### Opción B — Desde el código

```bash
pip install -r requirements.txt
python app.py          # abre http://127.0.0.1:5000
python -m pytest -q    # pruebas matemáticas (36)
```

### Regenerar el ejecutable

Ejecute `build_exe.bat`. Crea un entorno temporal e instala PyInstaller. Necesita Python 3.10.1 o superior (la 3.10.0 tiene un error que rompe PyInstaller).

## 3. Recorrido por la pantalla

- **Barra lateral:** cambia de módulo (Simulador de cuotas, Interés compuesto, Tasas de interés, Fechas focales, Comparar simulaciones, Catálogo de tasas).
- **Barra superior:** selector de **moneda** (COP por defecto), interruptor **Sencilla / Académica** y botones **Excel** y **PDF**.
- **Formulario (izquierda):** datos de entrada. Se recalcula solo cuando usted deja de escribir.
- **Resultados (derecha), con tres pestañas:**
  1. **Resultado:** tarjetas con las cifras y gráficos. La cifra calculada aparece destacada.
  2. **Procedimiento:** los 7 pasos matemáticos.
  3. **Tabla:** plan de pagos / amortización, tabla de crecimiento o traslado de valores, según el módulo.
- Cada tarjeta tiene un botón **Ver procedimiento** que lleva al paso donde se calculó.
- **Sencilla / Académica:** la vista sencilla oculta las fórmulas largas y deja lo esencial. La académica muestra todo.

### Los 7 pasos del procedimiento

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

**Tipo de anualidad:** vencida (pago al final del periodo), anticipada (al inicio), diferida (con periodos de gracia) y perpetua (sin fin).

**Datos principales:**
- **Monto / deuda (PV), Meta de ahorro (FV)** o **Cuota**, según lo que se calcule.
- **Tasa:** valor en % y su tipo (EA, NM, TV, …). Se convierte sola a la tasa del periodo de pago.
- **Periodicidad de pago:** mensual, bimestral, trimestral o semestral.
- **Plazo** en meses o años, o directamente el **número de cuotas**.
- **Fecha de nacimiento:** se convierte en edad, útil para créditos con seguro.
- **Fecha inicial** (y final opcional). Si no la indica, usa la de hoy y se lo avisa.
- **Seguro:** ninguno, % mensual sobre saldo, % mensual sobre el monto inicial, o valor fijo mensual.

**Resultados:** cuota, total pagado, intereses, capital amortizado, seguro, plan de pagos y gráficos.

Reglas que conviene conocer:
- En la anualidad diferida, los intereses de la gracia se capitalizan y el plazo cuenta solo los pagos.
- El seguro no se cobra durante la gracia.
- El seguro "% sobre saldo" no se admite al calcular el monto financiable, porque la cuota total dejaría de ser constante.
- Si el plazo no es compatible con la periodicidad (por ejemplo 10 meses con pagos trimestrales), la aplicación lo rechaza y lo explica.

### 4.2 Interés compuesto

Cuatro escenarios con un mismo formulario:

| Escenario | Incógnita | Fórmula |
|---|---|---|
| A | Valor futuro | FV = PV·(1+i)ⁿ |
| B | Valor presente | PV = FV·(1+i)⁻ⁿ |
| C | Tasa de interés | i = (FV/PV)^(1/n) − 1 |
| D | Tiempo | n = ln(FV/PV) / ln(1+i) |

Se puede indicar el periodo de capitalización y el plazo, o las fechas inicial y final. Devuelve la tabla de crecimiento y una gráfica.

### 4.3 Tasas de interés

Convierte una tasa de un tipo a otro: ingrese el valor, su tipo (EA, EM, NM, TV, …) y el periodo de cálculo. Muestra la EA equivalente, la tasa periódica usada, la fórmula de cada conversión y una tabla con la tasa expresada en todas las modalidades. El nombre completo de cada sigla se muestra siempre.

Regla general: toda conversión pasa por la **EA** (tasa efectiva anual). La tasa nominal es siempre anual y su tasa periódica es J/m. La tasa anticipada se pasa a vencida con i = ia/(1−ia).

### 4.4 Fechas focales

Traslada obligaciones y pagos a una fecha común para comparar o resolver una incógnita.

1. Indique fecha inicial, fecha final, **fecha focal**, tasa y conteo de tiempo (365, 360 o 30/360).
2. Agregue las obligaciones: etiqueta, grupo (**deuda** o **pago**), fecha y monto.
3. Deje **un solo monto en blanco** si quiere que la aplicación lo calcule.

Cada valor se traslada con V_F = V·(1+EA)^t, con t en años. Resultado: línea de tiempo, ecuación de equivalencia (Σdeudas = Σpagos) y el valor de la incógnita o la diferencia entre ambos lados.

### 4.5 Comparar simulaciones

Compara créditos con los mismos datos base y distinto plazo (por ejemplo 12, 24 y 36 meses). Muestra la cuota, los intereses y el total pagado de cada uno, las diferencias entre ellos y cuál sale más económico, con un gráfico de barras.

### 4.6 Catálogo de tasas

Aquí se definen las siglas disponibles. Cada una tiene: sigla, nombre, tipo (efectiva o nominal), meses de capitalización y si es anticipada.

- Puede editar, agregar o eliminar siglas, y restablecer las de fábrica.
- **MT** viene "por configurar" porque su significado depende de su material de estudio. No se puede usar hasta definirla. Si la usa antes, la aplicación se lo pide en vez de adivinar.
- Los cambios se guardan en `config/rate_catalog.json` y las simulaciones abiertas se recalculan solas.

Siglas incluidas: EA, EM, EB, ET, ES, EV, NA, NM, NB, NT, NS, TV, MV, TA, MA y MT.

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
config/             Catálogo de tasas editable
tests/              Pruebas matemáticas
docs/               Esta documentación
```

## 8. Problemas frecuentes

| Problema | Causa y solución |
|---|---|
| Las fórmulas se ven como código o no hay gráficos | No hay internet; KaTeX y Chart.js se cargan en línea. |
| "La sigla MT está sin configurar" | Defina su significado en el Catálogo de tasas. |
| La página no abre al ejecutar el .exe | Abra manualmente la dirección que muestra la ventana negra (normalmente http://127.0.0.1:5000). |
| El antivirus bloquea el .exe | Es un falso positivo habitual de los ejecutables creados con PyInstaller. Permítalo o ejecute desde el código. |
| "Operación matemática inválida" | Revise tasa, plazo y valores; por ejemplo, una tasa de −100 % o un plazo en cero. |
