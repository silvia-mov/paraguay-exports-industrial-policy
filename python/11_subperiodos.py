"""
* *********************************************************************
*
*       SUBPERÍODOS: 2012–2019 vs 2020–2022
*
* *********************************************************************

Entrada:  $data_temp/DataforRegressions.parquet
Salida:   $tables/{PAIS}_subperiodos_v{VUELTA}.csv

Base: ec. (6) (ver 7_pais.py). Idea de Evenett et al.
(2025, GTA): desde 2020 (pandemia y luego la ola de política industrial)
cambian el número y el tipo de medidas, así que el efecto podría no ser
el mismo en todo el período.

1. Conteos por subperíodo: obs., obs. con IP=1 y con IP_RTA_SUBS>0 (por socio).
2. Regresión por separado en cada subperíodo (mismos EF y cluster).
3. Regresión conjunta con interacciones IP×POST e IP_RTA_SUBS×POST
   (POST = 1 si year >= 2020): la prueba de que el efecto cambió es la
   t de la interacción. Efecto neto del acuerdo de referencia
   (IP + d·SUBS; Paraguay-Mercosur: d = 1/3) en cada subperíodo.
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
CORTE = 2020

cols = ["EXP", "IMP", "IMP_CODE", "year", "ISIC3_2", "EXPORTS", "ln_exp",
        "EXP_GROWTH", "IP", "IP_RTA_SUBS"]
py = cargar_muestra(cols)   # (se llama "py" por Paraguay, pero es el país elegido)
COB_REF, SOCIOS_REF = acuerdo_referencia(py, obligatorio=True)
py["IMP"] = py["IMP"].astype(str)
py["IMP_CODE"] = py["IMP_CODE"].astype(int)
py["POST"] = (py["year"] >= CORTE).astype(int)
py["IP_POST"] = py["IP"] * py["POST"]
py["SUBS_POST"] = py["IP_RTA_SUBS"] * py["POST"]
print(f"Vuelta {VUELTA} | {PAIS} exportador: {len(py):,} filas")

con = py[py["EXPORTS"] > UMBRAL]
sin_out = lambda d: d[(d["EXP_GROWTH"] > -200) & (d["EXP_GROWTH"] < 200)]
specs = {
    "Esp1 crecimiento, con umbral": ("EXP_GROWTH", con),
    "Esp2 crecimiento sin outliers, con umbral": ("EXP_GROWTH", sin_out(con)),
    "Esp3 ln, con umbral": ("ln_exp", con),
    "Esp4 crecimiento, sin umbral": ("EXP_GROWTH", py),
    "Esp5 crecimiento sin outliers, sin umbral": ("EXP_GROWTH", sin_out(py)),
    "Esp6 ln, sin umbral": ("ln_exp", py),
}
PERIODOS = {"2012-2019": lambda d: d[d["year"] < CORTE],
            "2020-2022": lambda d: d[d["year"] >= CORTE]}
filas = []


def coef(fit, v):
    if v not in fit._coefnames:
        return float("nan"), float("nan"), float("nan")
    return fit.coef()[v], fit.se()[v], fit.pvalue()[v]


def merco(fit, terms):
    lc = lincom(fit, terms)
    return round(lc["estimate"], 3), round(lc["p"], 3)


# ---- 1. Conteos ---------------------------------------------------------------
print("\n== 1. Conteos por subperíodo (con umbral / sin umbral; growth no missing)")
for etiqueta, d in (("con umbral", con), ("sin umbral", py)):
    d = d.dropna(subset=["EXP_GROWTH"])
    for per, f in PERIODOS.items():
        s = f(d)
        tr = s[s["IP_RTA_SUBS"] > 0]
        print(f"  {etiqueta:10s} {per}: N={len(s):,}  IP=1: {int(s['IP'].sum()):,}  "
              f"SUBS>0: {len(tr):,} {tr['IMP'].value_counts().to_dict()}")

# ---- 2. Por separado ------------------------------------------------------------
print("\n== 2. Ec. (6) por subperíodo")
for nombre, (y, d) in specs.items():
    d = d.dropna(subset=[y, "IP", "IP_RTA_SUBS"])
    for per, f in PERIODOS.items():
        s = f(d)
        fit = pf.feols(f"{y} ~ IP + IP_RTA_SUBS | {FE}", data=s, vcov=CL, fixef_rm="none")
        b1, se1, p1 = coef(fit, "IP")
        b2, se2, p2 = coef(fit, "IP_RTA_SUBS")
        m, mp = merco(fit, {"IP": 1, "IP_RTA_SUBS": COB_REF}) if b2 == b2 else (float("nan"),) * 2
        n_tr = int((s["IP_RTA_SUBS"] > 0).sum())
        filas.append({"prueba": "por separado", "spec": nombre, "periodo": per, "N": fit._N,
                      "n_SUBS>0": n_tr, "b_IP": b1, "se_IP": se1, "p_IP": p1,
                      "b_SUBS": b2, "se_SUBS": se2, "p_SUBS": p2,
                      "acuerdo": m, "acuerdo_p": mp})
        print(f"[{nombre} | {per}] N={fit._N:,} SUBS>0={n_tr}  IP={b1:.3f} ({se1:.3f}, p={p1:.3f})  "
              f"SUBS={b2:.3f} ({se2:.3f}, p={p2:.3f})  Acuerdo={m} (p={mp})")

# ---- 3. Conjunta con interacciones ---------------------------------------------
print("\n== 3. Conjunta con IP×POST e IP_RTA_SUBS×POST")
for nombre, (y, d) in specs.items():
    d = d.dropna(subset=[y, "IP", "IP_RTA_SUBS"])
    fit = pf.feols(f"{y} ~ IP + IP_RTA_SUBS + IP_POST + SUBS_POST | {FE}", data=d,
                   vcov=CL, fixef_rm="none")
    r = {"prueba": "interacciones", "spec": nombre, "periodo": "2012-2022", "N": fit._N}
    for v in ("IP", "IP_RTA_SUBS", "IP_POST", "SUBS_POST"):
        b, se, p = coef(fit, v)
        r.update({f"b_{v}": b, f"se_{v}": se, f"p_{v}": p})
    r["acuerdo_pre"], r["acuerdo_pre_p"] = merco(fit, {"IP": 1, "IP_RTA_SUBS": COB_REF})
    r["acuerdo_post"], r["acuerdo_post_p"] = merco(
        fit, {"IP": 1, "IP_RTA_SUBS": COB_REF, "IP_POST": 1, "SUBS_POST": COB_REF})
    r["SUBS_post_total"], r["SUBS_post_total_p"] = merco(fit, {"IP_RTA_SUBS": 1, "SUBS_POST": 1})
    filas.append(r)
    print(f"[{nombre}] N={fit._N:,}  "
          + "  ".join(f"{v}={r['b_'+v]:.3f} ({r['se_'+v]:.3f}, p={r['p_'+v]:.3f})"
                      for v in ("IP", "IP_RTA_SUBS", "IP_POST", "SUBS_POST"))
          + f"  | SUBS 2020-22={r['SUBS_post_total']} (p={r['SUBS_post_total_p']})"
          + f"  Acuerdo pre={r['acuerdo_pre']} (p={r['acuerdo_pre_p']})"
          + f" post={r['acuerdo_post']} (p={r['acuerdo_post_p']})")

TABLES.mkdir(parents=True, exist_ok=True)
pd.DataFrame(filas).to_csv(TABLES / f"{PAIS}_subperiodos_v{VUELTA}.csv", index=False)
print(f"\nGuardado {TABLES / f'{PAIS}_subperiodos_v{VUELTA}.csv'}")
