"""
* *********************************************************************
*
*       ROBUSTEZ POR TIPO DE SUBSIDIO
*
* *********************************************************************

Entrada:  $data_temp/DataforRegressions.parquet, GTA_cleaned.dta,
          ProductsLong_GTA_IP.dta
Salida:   $tables/{PAIS}_tipo_subsidio_v{VUELTA}.csv

Base: ec. (6) (ver 7_pais.py). La IP del paper junta 17
tipos de intervención GTA (Ind_policy roja). Aquí se separa la IP en:
    IP_T    = 1 si al menos una medida del tipo (o grupo) T cubre el
              importador-producto-año
    IP_OTRA = IP == 1 y no IP_T  (cubierta solo por otros tipos)
y se estima
    Y ~ IP_T + IP_T×COB + IP_OTRA + IP_OTRA×COB | importador + año + ISIC3_2
con COB = SUBS_COVERAGE (profundidad). Así el grupo de comparación sigue
siendo el de productos sin ninguna IP, como en la ec. (6).

Tipos/grupos (con obs. tratadas suficientes en socios con COB > 0):
  - Incentivo fiscal a la exportación ("Tax-based export incentive")
  - Préstamo estatal ("State loan")
  - Financiamiento al comercio ("Trade finance")
  - Grupo A, apoyo interno (donaciones, préstamos, garantías, alivio
    fiscal, subsidio a la producción, etc.)
  - Grupo B, incentivos a la exportación
"""
import warnings

import pandas as pd
import pyfixest as pf

from config import DATA_TEMP, TABLES, VUELTA
from stata_utils import lincom
from pais import PAIS, acuerdo_referencia, cargar_muestra, socios_tratados_principales

warnings.filterwarnings("ignore")

UMBRAL = 1000
CL = {"CRV1": "IMP_CODE"}
FE = "IMP_CODE + year + ISIC3_2"
KEYS = ["IMP", "HS2012", "year"]

EXPORTACION = ["Export subsidy", "Tax-based export incentive", "Trade finance",
               "Other export incentive", "Financial assistance in foreign market"]
GRUPOS = {
    "Incentivo fiscal a la exportación": ["Tax-based export incentive"],
    "Préstamo estatal": ["State loan"],
    "Financiamiento al comercio": ["Trade finance"],
    "Grupo A: apoyo interno": None,          # todo lo que no es exportación
    "Grupo B: incentivos a la exportación": EXPORTACION,
}

# ---- Tipos de cada importador-producto-año con IP (como 4-DataPrepare) --------
gta = pd.read_stata(DATA_TEMP / "GTA_cleaned.dta",
                    columns=["ID", "ISO_impl", "inception_year", "code_class", "interventiontype"],
                    convert_categoricals=False)
gta = gta[gta["code_class"] == 6]
prod = pd.read_stata(DATA_TEMP / "ProductsLong_GTA_IP.dta", convert_categoricals=False)
tipos = gta.merge(prod, on="ID").rename(
    columns={"Product": "HS2012", "ISO_impl": "IMP", "inception_year": "year"})
tipos["HS2012"] = pd.to_numeric(tipos["HS2012"], errors="coerce")
tipos = tipos[KEYS + ["interventiontype"]].drop_duplicates()

cols = ["EXP", "IMP", "IMP_CODE", "year", "HS2012", "ISIC3_2", "EXPORTS", "ln_exp",
        "EXP_GROWTH", "IP", "SUBS_COVERAGE", "IP_RTA_SUBS"]
py = cargar_muestra(cols)   # (se llama "py" por Paraguay, pero es el país elegido)
COB_REF, SOCIOS_REF = acuerdo_referencia(py, obligatorio=True)
py["IMP"] = py["IMP"].astype(str)
py["IMP_CODE"] = py["IMP_CODE"].astype(int)
tipos = tipos.merge(py.loc[py["IP"] == 1, KEYS], on=KEYS)  # solo celdas del país con IP
print(f"Vuelta {VUELTA} | {PAIS} exportador: {len(py):,} filas; con IP: {int(py['IP'].sum()):,}")
sin_tipo = py[py["IP"] == 1].merge(tipos[KEYS].drop_duplicates(), on=KEYS, how="left",
                                   indicator=True)
assert (sin_tipo["_merge"] == "both").all(), "hay obs con IP=1 sin tipo GTA"

con = py[py["EXPORTS"] > UMBRAL]
sin_out = lambda d: d[(d["EXP_GROWTH"] > -200) & (d["EXP_GROWTH"] < 200)]
specs = {
    "Esp1 crecimiento, con umbral": ("EXP_GROWTH", lambda d: d[d["EXPORTS"] > UMBRAL]),
    "Esp2 crecimiento sin outliers, con umbral": ("EXP_GROWTH", lambda d: sin_out(d[d["EXPORTS"] > UMBRAL])),
    "Esp3 ln, con umbral": ("ln_exp", lambda d: d[d["EXPORTS"] > UMBRAL]),
    "Esp4 crecimiento, sin umbral": ("EXP_GROWTH", lambda d: d),
    "Esp5 crecimiento sin outliers, sin umbral": ("EXP_GROWTH", sin_out),
    "Esp6 ln, sin umbral": ("ln_exp", lambda d: d),
}
filas = []

for grupo, lista in GRUPOS.items():
    if lista is None:
        sel = ~tipos["interventiontype"].isin(EXPORTACION)
    else:
        sel = tipos["interventiontype"].isin(lista)
    celdas = tipos.loc[sel, KEYS].drop_duplicates().assign(IP_T=1)
    d0 = py.merge(celdas, on=KEYS, how="left")
    d0["IP_T"] = d0["IP_T"].fillna(0)
    d0["IP_OTRA"] = d0["IP"] - d0["IP_T"]
    d0["SUBS_T"] = d0["IP_T"] * d0["SUBS_COVERAGE"]
    d0["SUBS_OTRA"] = d0["IP_OTRA"] * d0["SUBS_COVERAGE"]
    tr = d0[(d0["SUBS_T"] > 0) & (d0["EXPORTS"] > UMBRAL) & d0["EXP_GROWTH"].notna()]
    print(f"\n== {grupo}: obs. IP_T=1 {int(d0['IP_T'].sum()):,}; con COB>0 (con umbral, "
          f"growth no missing) {len(tr):,} {tr['IMP'].value_counts().to_dict()}")
    for nombre, (y, f) in specs.items():
        d = f(d0).dropna(subset=[y])
        fit = pf.feols(f"{y} ~ IP_T + SUBS_T + IP_OTRA + SUBS_OTRA | {FE}", data=d,
                       vcov=CL, fixef_rm="none")
        r = {"grupo": grupo, "spec": nombre, "N": fit._N,
             "n_T_COB>0": int((d["SUBS_T"] > 0).sum())}
        for v in ("IP_T", "SUBS_T", "IP_OTRA", "SUBS_OTRA"):
            ok = v in fit._coefnames
            r.update({f"b_{v}": fit.coef()[v] if ok else float("nan"),
                      f"se_{v}": fit.se()[v] if ok else float("nan"),
                      f"p_{v}": fit.pvalue()[v] if ok else float("nan")})
        if "SUBS_T" in fit._coefnames:
            lc = lincom(fit, {"IP_T": 1, "SUBS_T": COB_REF})
            r.update({"acuerdo_T": round(lc["estimate"], 3), "acuerdo_T_p": round(lc["p"], 3)})
        filas.append(r)
        print(f"[{nombre}] N={fit._N:,} T con COB>0={r['n_T_COB>0']}  "
              f"IP_T={r['b_IP_T']:.3f} ({r['se_IP_T']:.3f}, p={r['p_IP_T']:.3f})  "
              f"SUBS_T={r['b_SUBS_T']:.3f} ({r['se_SUBS_T']:.3f}, p={r['p_SUBS_T']:.3f})  "
              f"Acuerdo_T={r.get('acuerdo_T')} (p={r.get('acuerdo_T_p')})  | "
              f"IP_OTRA={r['b_IP_OTRA']:.3f} (p={r['p_IP_OTRA']:.3f})  "
              f"SUBS_OTRA={r['b_SUBS_OTRA']:.3f} (p={r['p_SUBS_OTRA']:.3f})")

TABLES.mkdir(parents=True, exist_ok=True)
pd.DataFrame(filas).to_csv(TABLES / f"{PAIS}_tipo_subsidio_v{VUELTA}.csv", index=False)
print(f"\nGuardado {TABLES / f'{PAIS}_tipo_subsidio_v{VUELTA}.csv'}")
