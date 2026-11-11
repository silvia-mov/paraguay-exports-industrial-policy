# Correcciones al código original

Al traducir y volver a correr el paquete de Barattieri, Mattoo y Taglioni (2024)
aparecieron tres comportamientos del código original que probablemente no son
intencionales. **Por defecto este repositorio los replica tal cual** (así los
resultados coinciden con el paper). Cada corrección se activa por separado con
una variable de entorno.

Las cifras de abajo salen de correr el paquete completo con los datos reales.

---

## 1. Acuerdos superpuestos: se queda el de menor cobertura

**Dónde:** paso 1, `1-DataPrepare_PTA.do`.

Un mismo par de países puede tener varios acuerdos vigentes el mismo año (por
ejemplo, Paraguay y Brasil están en ALADI y en Mercosur). El código ordena con
`sort ... SUBS_COVERAGE` y después hace `duplicates drop`, así que se queda con
el acuerdo de **menor** cobertura de disciplinas sobre subsidios.

- 107.708 pares de países-año; 16.231 tienen más de un acuerdo y en 11.137 las
  coberturas son distintas, así que la elección importa.
- Para Paraguay con Argentina, Brasil y Uruguay gana ALADI (cobertura 0) sobre
  Mercosur (cobertura 1/3). Con el código original, la profundidad del acuerdo
  **nunca** varía para Paraguay y su efecto no se puede estimar.

**Corrección:** `gsort EXP IMP year -SUBS_COVERAGE` (se queda con la mayor).
Activar con `TESIS_VUELTA=2` en Python, o `vuelta <- 2` en `R/config.R`.

**Efecto en el paper** (Tabla 3, columna 5): IP_RTA_SUBS pasa de 2,304 (0,575)
a 2,092 (0,553); IP pasa de −0,773 a −0,757. Las columnas sin IP_RTA_SUBS no cambian.

---

## 2. La lista de productos se corta en 2.045 caracteres

**Dónde:** paso 2, `2-DataPrepare_GTA_PT1.do` (`insheet`), que alimenta al paso 3.

`insheet` de Stata lee los textos como `str2045`: cualquier celda más larga se
corta. La columna `affectedproducts` de la Global Trade Alert es una lista de
códigos HS separados por comas, y en muchas medidas supera ese largo. Lo que
queda después del corte se pierde, y el último código queda a medias (por
ejemplo `85149`).

- Políticas industriales (IP): 1.599 medidas afectadas, 356.706 pares
  medida-producto perdidos (≈ 9 %).
- Barreras a las importaciones (IMP): 5.206 medidas afectadas, 7.660.588 pares
  perdidos (≈ 69 %).
- Explica por qué ninguna medida tiene más de 256 productos.

**Corrección:** leer el CSV sin límite de largo (y sin el tope de 600 productos
del paso 3). Activar con `TESIS_SIN_TRUNCAR=1` (solo Python).

---

## 3. El crecimiento no siempre es contra el año anterior

**Dónde:** paso 4, `4-DataPrepare_GTA_PT2.do`.

`EXP_GROWTH` se calcula con la **observación anterior** del mismo flujo
(`[_n-1]`), no con el año t−1. Si un producto no se exportó en algún año, el
"crecimiento" compara con dos, tres o más años atrás.

- 417.061 de 9.036.301 observaciones de la muestra de regresión (4,6 %) no
  comparan con t−1; en toda la base, el 9,35 % (brechas de 2 a 10 años).

**Corrección:** exigir que la observación anterior sea exactamente t−1 (si no,
el crecimiento queda vacío). Activar con `TESIS_T_MENOS_1=1` (solo Python).

---

## Otras observaciones (sin corrección)

- Los umbrales de exportación son distintos en dos pasos: el paso 4 borra los
  flujos menores a USD 500 mil (`EXPORTS<500`, BACI está en miles) y el paso 5
  se queda con los mayores a USD 1 millón (`EXPORTS>1000`, nota 3 del paper).
- En el paso 2 las jurisdicciones `"NA"` se convierten en "Micronesia, Fed. Sts.";
  probablemente `"NA"` era un valor faltante y no Micronesia.
- El archivo de la GTA mezcla UTF-8 con bytes Windows-1252 (por ejemplo,
  "Réunion" y "Saint-Barthélemy"); Stata compara bytes y esas filas se pierden en
  un merge. Python lo imita para dar los mismos resultados.
- `lincom` sí está en `5-Regressions.do`, pero dentro de `quietly{}`, así que no
  aparece en el log.
- Los peces de HS 0301xx–0302xx tienen sector ISIC "0", que no existe (probablemente debería ser 05).
