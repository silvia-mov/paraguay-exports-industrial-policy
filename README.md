# Políticas industriales de los socios comerciales y exportaciones de Paraguay (2012–2022)

Réplica en **Python** y **R** del paquete de reproducibilidad de
**Barattieri, Mattoo y Taglioni (2024)**, *Trade Effects of Industrial Policies:
Are Preferential Agreements a Shield?* (Banco Mundial, Policy Research Working
Paper 10806), con tres correcciones al código original y una extensión para
estimar el efecto en **un país exportador** (Paraguay en la tesis, pero sirve
para cualquier otro).

Trabajo Final de Grado en Economía, Universidad Nacional de Asunción (2026).

> 🇬🇧 *English summary at the end.*

---

## ¿Qué pregunta responde?

Cuando un socio comercial aplica una **política industrial** (subsidios,
préstamos estatales, incentivos fiscales…), ¿qué pasa con las exportaciones que
otros países le venden en ese producto? ¿Y protege un **acuerdo comercial
preferencial** con reglas sobre subsidios?

El paper original responde con datos de todo el mundo: una nueva medida en el
mercado de destino reduce el crecimiento de las exportaciones hacia ese mercado
en unos 0,28 puntos porcentuales, salvo que exportador e importador compartan un
acuerdo con disciplinas sobre subsidios (el "escudo").

## Datos

| Base | Qué aporta | Fuente |
|---|---|---|
| **BACI** (CEPII), HS 2012 | Comercio bilateral por producto (6 dígitos) | [cepii.fr](http://www.cepii.fr/CEPII/en/bdd_modele/bdd_modele_item.asp?id=37) |
| **Global Trade Alert** | Medidas de política industrial por país, producto y año | [globaltradealert.org](https://www.globaltradealert.org/data_extraction) |
| **Deep Trade Agreements 2.0** (Banco Mundial) | Cobertura de disciplinas sobre subsidios en cada acuerdo | [datatopics.worldbank.org/dta](https://datatopics.worldbank.org/dta/) |

Los datos **no** están en este repositorio (pesan varios GB y algunas licencias
no permiten redistribuirlos libremente). Cómo conseguirlos: [`docs/datos.md`](docs/datos.md).

## Estructura

```
├── python/                  ← traducción a Python (pasos 0–6)
│   ├── config.py            ← rutas y opciones
│   ├── stata_utils.py       ← merge, encode, insheet, lincom… con la lógica de Stata
│   ├── 0_master.py          ← corre todo en orden
│   ├── 1_…6_*.py            ← un script por do-file original
│   └── tests_make_synthetic_data.py ← datos falsos para probar que todo corre
├── R/                       ← la misma traducción en R
├── stata/                   ← do-files originales de los autores (referencia)
├── docs/
│   ├── datos.md             ← cómo descargar y ordenar los datos
│   └── correcciones.md      ← las 3 correcciones al código original
├── requirements.txt         ← paquetes de Python
└── LICENSE                  ← BSD-3 (la del código original)
```

## Los pasos

| # | Qué hace | Stata (original) | Python | R |
|---|---|---|---|---|
| 1 | Acuerdos comerciales y su cobertura de subsidios (DTA) | `1-DataPrepare_PTA.do` | `1_data_prepare_pta.py` | `1-DataPrepare_PTA.R` |
| 2 | Limpia las medidas de la Global Trade Alert | `2-DataPrepare_GTA_PT1.do` | `2_data_prepare_gta_pt1.py` | `2-DataPrepare_GTA_PT1.R` |
| 3 | Separa la lista de productos afectados por cada medida | `3-Split Sectors-Products.R` | `3_split_sectors_products.py` | `3-Split Sectors-Products.R` |
| 4 | Une comercio (BACI) + medidas + acuerdos → base de regresiones | `4-DataPrepare_GTA_PT2.do` | `4_data_prepare_gta_pt2.py` | `4-DataPrepare_GTA_PT2.R` |
| 5 | Regresiones con efectos fijos (Tablas 3–8 del paper) | `5-Regressions.do` | `5_regressions.py` | `5-Regressions.R` |
| 6 | Figuras del paper | `6-Figures.do` | `6_figures.py` | `6-Figures.R` |

Cada script de Python y R tiene, como comentario, la línea de Stata que traduce,
para poder compararlos de a uno.

## Cómo correrlo

### 1. Probar con datos sintéticos (2 minutos, sin descargar nada)

```bash
pip install -r requirements.txt
python python/tests_make_synthetic_data.py .
python python/0_master.py
```

Crea datos falsos en `1_Data/` y corre los 6 pasos. Las tablas quedan en
`5_Tables/` y las figuras en `4_Figures/`. Los números no significan nada:
solo sirve para comprobar que todo funciona.

### 2. Con los datos reales

1. Descarga los datos como explica [`docs/datos.md`](docs/datos.md) y ponlos en `1_Data/`.
2. Corre `python python/0_master.py` (o `Rscript R/0-master.R`, o abre `R/0-master.R` en RStudio).

⚠️ Con los datos reales la base tiene unos 15 millones de filas: se necesitan
**16 GB de RAM** y varias horas (la Tabla 8 es la más lenta).

### 3. Opciones (correcciones)

Por defecto el código hace **exactamente lo mismo que el original**. Las
correcciones se activan con variables de entorno, sin tocar el código:

| Variable | Valor | Qué cambia | Detalle |
|---|---|---|---|
| `TESIS_VUELTA` | `2` | Si un par de países tiene varios acuerdos el mismo año, usa el de **mayor** cobertura de subsidios (el original se queda con el menor) | [corrección 1](docs/correcciones.md#1-acuerdos-superpuestos-se-queda-el-de-menor-cobertura) |
| `TESIS_SIN_TRUNCAR` | `1` | No corta la lista de productos afectados en 2.045 caracteres | [corrección 2](docs/correcciones.md#2-la-lista-de-productos-se-corta-en-2045-caracteres) |
| `TESIS_T_MENOS_1` | `1` | El crecimiento de las exportaciones compara siempre con el año anterior (t−1) | [corrección 3](docs/correcciones.md#3-el-crecimiento-no-siempre-es-contra-el-año-anterior) |
| `TESIS_ROOT` | ruta | Carpeta donde están `1_Data/` y donde se guardan las salidas | — |

Ejemplo (Linux/Mac):

```bash
TESIS_VUELTA=2 TESIS_SIN_TRUNCAR=1 TESIS_T_MENOS_1=1 python python/0_master.py
```

En Windows (PowerShell): `$env:TESIS_VUELTA=2` antes de correr el script.

En R, por ahora solo existe la corrección 1 (`vuelta <- 2` en `R/config.R`).

## Validación

- **Stata**: con el código original, las Tablas 3 a 7 salen **idénticas** al paper
  (por ejemplo, Tabla 3, columna 1: IP = −0,283 (0,126); N = 8.474.619; R² = 0,244).
- **Python vs. Stata**: la base de regresiones de Python coincide con la de Stata en
  sus 23 variables (15.054.549 filas; N, media, desvío, mínimo y máximo), y la
  columna 5 de la Tabla 3 coincide al decimal.
- **Python vs. R**: con datos sintéticos, las 17 salidas intermedias y finales son
  idénticas.
- **Limitación**: `R/5-Regressions.R` (paquete `fixest`) no se pudo ejecutar en el
  entorno donde se tradujo; solo se verificó que los N coinciden. Los errores
  estándar de `pyfixest`/`fixest` pueden diferir de `reghdfe` en el tercer decimal.

## Créditos y cita

El método, los datos y el código original (carpeta `stata/`) son de:

> Barattieri, A., Mattoo, A. y Taglioni, D. (2024). *Trade Effects of Industrial
> Policies: Are Preferential Agreements a Shield?* Policy Research Working Paper
> 10806. Banco Mundial.
> [Documento](https://documents.worldbank.org/en/publication/documents-reports/documentdetail/099310406172411550) ·
> [Paquete de reproducibilidad RR_EAP_2024_161](https://reproducibility.worldbank.org/catalog/176)

Si usas este repositorio, cita el paper original. Este repositorio agrega la
traducción a Python y R, las correcciones y la extensión por país.

Licencia: BSD-3 (la misma del código original; ver [`LICENSE`](LICENSE)).

---

## 🇬🇧 English summary

Python and R translation of the World Bank reproducibility package for
Barattieri, Mattoo & Taglioni (2024), *Trade Effects of Industrial Policies: Are
Preferential Agreements a Shield?* (PRWP 10806), developed for an undergraduate
thesis in Economics on Paraguay's exports (2012–2022).

- **Same results**: with the original code, Tables 3–7 match the paper exactly;
  the Python pipeline reproduces Stata's regression dataset (23 variables, 15M rows)
  and Table 3, column 5.
- **Three optional fixes** to the original code (off by default; see
  [`docs/correcciones.md`](docs/correcciones.md)): overlapping agreements keep the
  *lowest* subsidy coverage; Stata's `insheet` truncates product lists at 2,045
  bytes; export growth is computed against the previous *observation*, not
  always t−1.
- **Quick test**: `pip install -r requirements.txt`,
  `python python/tests_make_synthetic_data.py .`, `python python/0_master.py`.
- Data (BACI, Global Trade Alert, Deep Trade Agreements 2.0) are not included;
  see [`docs/datos.md`](docs/datos.md).
