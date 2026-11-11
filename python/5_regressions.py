"""
* *********************************************************************
*
*       PART 3:  Run the analysis
*       (traducción de 5-Regressions.do)
*
* *********************************************************************

Entrada:  $data_temp/DataforRegressions.dta   (de 4-DataPrepare_GTA_PT2)
Salidas:  $tables/BMT_Tab_3..8.tex / .csv
          $tables/lincom.csv   (combinaciones de coeficientes para la Figura 3)

reghdfe -> pyfixest.feols. Equivalencias verificadas:
  - a(A#B#C)            -> efecto fijo combinado "A^B^C"
  - cluster(A#B)        -> vcov={"CRV1": "pair"} con pair = grupo A-B
  - singletons          -> pyfixest los elimina de forma iterativa (fixef_rm="singleton"),
                           igual que reghdfe, así que N coincide
  - region_code#c.IP    -> i(region_code, IP)  (una pendiente por región, sin base)
  - t con G-1 grados de libertad, igual que reghdfe con cluster
  Los coeficientes son idénticos a los de reghdfe. Los errores estándar pueden
  diferir en el 3er decimal: reghdfe descuenta parte de los efectos fijos
  redundantes al calcular los grados de libertad y pyfixest no.
"""
import warnings

import pandas as pd
import pyfixest as pf

from config import DATA_TEMP, TABLES
from stata_utils import estout, lincom

warnings.filterwarnings("ignore", message=".*singleton.*")

# a(EXP_CODE#IMP_CODE#year EXP_CODE#year#HS2012 IMP_CODE#year#ISIC3_2 HS2012#IMP_CODE)
FE_BASE = ("EXP_CODE^IMP_CODE^year + EXP_CODE^year^HS2012"
           " + IMP_CODE^year^ISIC3_2 + HS2012^IMP_CODE")
# Tabla 4: a(EXP_CODE#IMP_CODE#year EXP_CODE#year#HS2012 IMP_CODE#year#HS2012 EXP_CODE#IMP_CODE#HS2012)
FE_STRICT = ("EXP_CODE^IMP_CODE^year + EXP_CODE^year^HS2012"
             " + IMP_CODE^year^HS2012 + EXP_CODE^IMP_CODE^HS2012")
# cluster(EXP_CODE#IMP_CODE)
VCOV = {"CRV1": "pair"}

# Orden de filas que produce estout al juntar los coeficientes de m1..m6
KEEP_BASE = ["IP", "IP_RTA", "IMP_BARR", "IMP_BARR_RTA", "IP_RTA_SUBS"]
KEEP_STRICT = ["IP_RTA", "IMP_BARR_RTA", "IP_RTA_SUBS"]

lincoms = []   # resultados de lincom (en el original quedan ocultos por `quietly`)


def reghdfe(y: str, x: str, data: pd.DataFrame, fe: str = FE_BASE):
    """reghdfe y x, a(fe) cluster(EXP_CODE#IMP_CODE)"""
    return pf.feols(f"{y} ~ {x} | {fe}", data=data, vcov=VCOV)


def guardar_lincom(tabla: int, modelo: str, fit, pesos: dict[str, float]) -> None:
    expr = " + ".join(f"{w:g}*{v}" if w != 1 else v for v, w in pesos.items())
    res = lincom(fit, pesos)
    print(f"  lincom {expr} ({modelo}): {res['estimate']:.3f} (se {res['se']:.3f}, p={res['p']:.3f})")
    lincoms.append({"tabla": tabla, "modelo": modelo, "lincom": expr, **res})


# **# TABLE 1 / TABLE 2 -> no usan datos

# use "$data_temp/DataforRegressions", clear
cols = ["EXP_GROWTH", "ln_exp", "EXPORTS", "IP", "IP_RTA", "IMP_BARR", "IMP_BARR_RTA",
        "IP_RTA_SUBS", "EXP_CODE", "IMP_CODE", "year", "HS2012", "ISIC3_2",
        "region", "incomegroup"]
df = pd.read_stata(DATA_TEMP / "DataforRegressions.dta", columns=cols,
                   convert_categoricals=False)

# keep if EXPORTS>1000
# (En Stata missing>1000 es verdadero: las filas sin EXPORTS -economías sin
#  comercio- se quedan, aunque luego no entran a ninguna regresión.
#  EXPORTS está en miles de USD: aquí se aplica el umbral de USD 1 millón
#  que menciona la nota 3 del paper.)
df = df[(df["EXPORTS"] > 1000) | df["EXPORTS"].isna()].reset_index(drop=True)

# Variable de cluster EXP_CODE#IMP_CODE
df["pair"] = df.groupby(["EXP_CODE", "IMP_CODE"], dropna=False).ngroup()


# **# TABLE 3 ------------------------------------------------------------------
def tabla_base(n: int, y: str, data: pd.DataFrame) -> None:
    """Tablas 3, 5 y 6: mismas 6 especificaciones, cambia y/muestra."""
    print(f"\n===== TABLE {n} =====")
    m = {}
    m["m1"] = reghdfe(y, "IP", data)
    m["m2"] = reghdfe(y, "IP + IP_RTA", data)
    # Las 4 barras de la Figura 3 (no está en el original: los autores la
    # armaron a mano con estos números de la Tabla 3)
    guardar_lincom(n, "m1", m["m1"], {"IP": 1})
    guardar_lincom(n, "m2", m["m2"], {"IP": 1})
    guardar_lincom(n, "m2", m["m2"], {"IP": 1, "IP_RTA": 1})
    m["m3"] = reghdfe(y, "IP + IMP_BARR", data)
    m["m4"] = reghdfe(y, "IP + IMP_BARR + IP_RTA + IMP_BARR_RTA", data)
    m["m5"] = reghdfe(y, "IP + IP_RTA_SUBS", data)
    guardar_lincom(n, "m5", m["m5"], {"IP": 1, "IP_RTA_SUBS": 0.5})
    m["m6"] = reghdfe(y, "IP + IMP_BARR + IMP_BARR_RTA + IP_RTA_SUBS", data)
    # estout m* [using "$tables/BMT_Tab_`n'.tex"], k(...) ...
    estout(m, keep=KEEP_BASE, path=TABLES / f"BMT_Tab_{n}")


tabla_base(3, "EXP_GROWTH", df)


# **# TABLE 4 More stringent ---------------------------------------------------
print("\n===== TABLE 4 =====")
m = {
    "m1": reghdfe("EXP_GROWTH", "IP_RTA", df, FE_STRICT),
    "m2": reghdfe("EXP_GROWTH", "IP_RTA + IMP_BARR_RTA", df, FE_STRICT),
    "m3": reghdfe("EXP_GROWTH", "IP_RTA_SUBS", df, FE_STRICT),
    "m4": reghdfe("EXP_GROWTH", "IP_RTA + IMP_BARR_RTA + IP_RTA_SUBS", df, FE_STRICT),
}
estout(m, keep=KEEP_STRICT, path=TABLES / "BMT_Tab_4")


# **# TABLE 5 No outliers --------------------------------------------------------
# ... if EXP_GROWTH>-200 & EXP_GROWTH<200
tabla_base(5, "EXP_GROWTH", df[(df["EXP_GROWTH"] > -200) & (df["EXP_GROWTH"] < 200)])


# **# TABLE 6 Levels -------------------------------------------------------------
# replace ln_exp=ln_exp*100
df["ln_exp"] = df["ln_exp"] * 100
tabla_base(6, "ln_exp", df)


# **# TABLE 7 Heterogeneity across regions ---------------------------------------
print("\n===== TABLE 7 =====")
# replace region = "Advanced Economies" if incomegroup == "High income"
df.loc[df["incomegroup"] == "High income", "region"] = "Advanced Economies"

# label define region 1 "Advanced Economies" 2 "East Asia & Pacific" ...
# encode region, gen(region_code) label(region) noextend
REGIONS = {1: "Advanced Economies", 2: "East Asia & Pacific",
           3: "Europe & Central Asia", 4: "Latin America & Caribbean",
           5: "Middle East & North Africa", 6: "South Asia", 7: "Sub-Saharan Africa"}
codigo = {v: k for k, v in REGIONS.items()}
region = df["region"].fillna("")
fuera = set(region[region != ""]) - set(codigo)
if fuera:   # noextend: Stata da error si aparece una región no definida
    raise ValueError(f"encode noextend: regiones sin código {sorted(fuera)}")
df["region_code"] = region.map(codigo)   # "" -> NaN

# reghdfe EXP_GROWTH region_code#c.IP region_code#c.IP_RTA, a(...) cluster(...)
# OJO: region es la del EXPORTADOR (se unió por EXP en el paso 4).
# Las filas sin región se excluyen, como hace Stata con un factor en missing.
d7 = df[df["region_code"].notna()].copy()
d7["region_code"] = d7["region_code"].astype(int)
m7 = reghdfe("EXP_GROWTH", "i(region_code, IP) + i(region_code, IP_RTA)", d7)
nombres7 = {f"region_code::{k}:{v}": f"{REGIONS[k]} x {v}"
            for k in REGIONS for v in ("IP", "IP_RTA")}
estout({"m2": m7}, rename=nombres7, path=TABLES / "BMT_Tab_7")


# **# TABLE 8 Heterogeneity across sectors -------------------------------------
print("\n===== TABLE 8 =====")
# reghdfe EXP_GROWTH ISIC3_2#c.IP ISIC3_2#c.IP_RTA, a(...) cluster(...)
d8 = df[df["ISIC3_2"].notna() & (df["ISIC3_2"].astype(str) != "")].copy()
if pd.api.types.is_numeric_dtype(d8["ISIC3_2"]):
    d8["ISIC3_2"] = d8["ISIC3_2"].astype(int)
m8 = reghdfe("EXP_GROWTH", "i(ISIC3_2, IP) + i(ISIC3_2, IP_RTA)", d8)
# (en el original el .tex de esta tabla se escribe sin style(tex): las dos
#  líneas estout están invertidas. Aquí se guarda en LaTeX válido.)
nombres8 = {f"ISIC3_2::{k}:{v}": f"ISIC {k} x {v}"
            for k in d8["ISIC3_2"].unique() for v in ("IP", "IP_RTA")}
estout({"m1": m8}, rename=nombres8, path=TABLES / "BMT_Tab_8")

# Resultados de lincom (para la Figura 3)
pd.DataFrame(lincoms).to_csv(TABLES / "lincom.csv", index=False)
