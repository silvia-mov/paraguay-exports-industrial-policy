"""
* *********************************************************************
*
*       EXTRA: número efectivo de grupos, intervalos de 3 años y
*                 exportación de la muestra para Stata
*
* *********************************************************************

Entrada:  $data_temp/DataforRegressions.parquet, GTA_cleaned_IP.dta,
          DTA_subsidies.dta
Salidas:  $tables/{PAIS}_extra_v{VUELTA}.csv
          $tables/{PAIS}_muestra_stata_v{VUELTA}.dta  (muestra del país con
          adelantos y rezagos, para stata/7_pais_robustez.do y 14_tablas.py)

1. Número efectivo de grupos (Carter, Schnepel y Steigerwald 2017; comando
   `clusteff` de Stata): G* = G / (1 + Γ), con Γ la variación relativa de la
   contribución de cada grupo (importador) a la varianza del coeficiente de
   IP_RTA_SUBS, suponiendo correlación perfecta dentro del grupo (ρ = 1).
   Se calcula sobre los regresores ya "limpios" de los efectos fijos
   (teorema de Frisch-Waugh-Lovell).
2. Crecimiento en intervalos de 3 años (Cheng y Wall 2005): 100·Δln
   EXPORTS entre t−3 y t, con t = 2015, 2018, 2021 (y 2016, 2019, 2022);
   tratamiento = alguna medida de IP en t−2, t−1 o t (a nivel producto).
3. Muestra del país en .dta (para Stata y para 14_tablas.py).
"""
import warnings

import numpy as np
import pandas as pd
import pyfixest as pf

from config import DATA_TEMP, TABLES, VUELTA
from stata_utils import lincom
from pais import PAIS, acuerdo_referencia, cargar_muestra, socios_tratados_principales

warnings.filterwarnings("ignore")

UMBRAL = 1000
CL = {"CRV1": "IMP_CODE"}
FE = "IMP_CODE + year + ISIC3_2"
SEMILLA = 20261019

cols = ["EXP", "IMP", "IMP_CODE", "year", "HS2012", "ISIC3_2", "EXPORTS", "ln_exp",
        "EXP_GROWTH", "IP", "SUBS_COVERAGE", "IP_RTA_SUBS"]
py = cargar_muestra(cols)   # (se llama "py" por Paraguay, pero es el país elegido)
COB_REF, SOCIOS_REF = acuerdo_referencia(py, obligatorio=True)
py["IMP"] = py["IMP"].astype(str)
py["IMP_CODE"] = py["IMP_CODE"].astype(int)
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
filas = []

# ---- 1. Número efectivo de grupos ------------------------------------------------
print("\n== 1. Número efectivo de grupos (Carter, Schnepel y Steigerwald 2017)")


def residualizar(d, cols_x):
    """Residuos de cada columna sobre los efectos fijos (dummies de IMP, año, ISIC)."""
    D = pd.get_dummies(d[["IMP_CODE", "year", "ISIC3_2"]].astype(str), drop_first=True)
    D.insert(0, "const", 1.0)
    D = D.to_numpy(dtype=float)
    X = d[cols_x].to_numpy(dtype=float)
    b, *_ = np.linalg.lstsq(D, X, rcond=None)
    return X - D @ b


for nombre, (y, d) in specs.items():
    d = d.dropna(subset=[y, "IP", "IP_RTA_SUBS", "ISIC3_2"]).reset_index(drop=True)
    Xt = residualizar(d, ["IP", "IP_RTA_SUBS"])
    A = np.linalg.solve(Xt.T @ Xt, Xt.T)       # fila k: pesos de cada obs. en β_k
    w = pd.Series(A[1], index=d.index)          # β de IP_RTA_SUBS
    s = w.groupby(d["IMP"]).sum()
    gam = s ** 2                                # contribución del grupo (ρ = 1)
    G = len(gam)
    Gamma = ((gam - gam.mean()) ** 2).mean() / gam.mean() ** 2
    G_ef = G / (1 + Gamma)
    peso = (gam / gam.sum()).sort_values(ascending=False)
    top = ", ".join(f"{k} {100 * v:.0f} %" for k, v in peso.head(4).items())
    filas.append({"prueba": "1 G efectivo", "spec": nombre, "N": len(d), "G": G,
                  "G_efectivo": G_ef, "pesos": top})
    print(f"[{nombre}] G={G}  G efectivo={G_ef:.1f}  (peso en la varianza de β2: {top})")

# ---- 2. Intervalos de 3 años ---------------------------------------------------
print("\n== 2. Crecimiento en intervalos de 3 años (Cheng y Wall 2005)")
gta_ip = pd.read_stata(DATA_TEMP / "GTA_cleaned_IP.dta", columns=["IMP", "HS2012", "year"],
                       convert_categoricals=False).drop_duplicates()
cob = pd.read_stata(DATA_TEMP / "DTA_subsidies.dta", convert_categoricals=False)
cob = cob.loc[cob["EXP"] == PAIS, ["IMP", "year", "SUBS_COVERAGE"]].rename(
    columns={"SUBS_COVERAGE": "COB"})
isic = py[["HS2012", "ISIC3_2"]].dropna().drop_duplicates("HS2012")
base = py[["IMP", "IMP_CODE", "HS2012", "year", "EXPORTS"]]

for finales in ((2015, 2018, 2021), (2016, 2019, 2022)):
    partes = []
    for t in finales:
        a = base[base["year"] == t].merge(
            base.loc[base["year"] == t - 3, ["IMP", "HS2012", "EXPORTS"]].rename(
                columns={"EXPORTS": "EXP_base"}), on=["IMP", "HS2012"], how="inner")
        ventana = gta_ip[gta_ip["year"].between(t - 2, t)][["IMP", "HS2012"]].drop_duplicates()
        a = a.merge(ventana.assign(IPw=1.0), on=["IMP", "HS2012"], how="left")
        a = a.merge(cob[cob["year"] == t][["IMP", "COB"]], on="IMP", how="left")
        a["IPw"] = a["IPw"].fillna(0.0)
        a["SUBSw"] = a["IPw"] * a["COB"].fillna(0.0)
        partes.append(a)
    p3 = pd.concat(partes, ignore_index=True).merge(isic, on="HS2012", how="left")
    p3["G3"] = 100 * (np.log(p3["EXPORTS"]) - np.log(p3["EXP_base"]))
    etiqueta = "/".join(str(t) for t in finales)
    for umbral, dd in (("sin umbral", p3), ("base > USD 1 millón", p3[p3["EXP_base"] > UMBRAL])):
        dd = dd.dropna(subset=["G3", "ISIC3_2"])
        fit = pf.feols(f"G3 ~ IPw + SUBSw | {FE}", data=dd, vcov=CL, fixef_rm="none")
        lc = lincom(fit, {"IPw": 1, "SUBSw": COB_REF})
        wb = fit.wildboottest(param="SUBSw", reps=9999, seed=SEMILLA)
        fila = {"prueba": "2 intervalos 3 años", "spec": f"{etiqueta}, {umbral}", "N": fit._N,
                "b_IP": fit.coef()["IPw"], "se_IP": fit.se()["IPw"], "p_IP": fit.pvalue()["IPw"],
                "b_SUBS": fit.coef()["SUBSw"], "se_SUBS": fit.se()["SUBSw"],
                "p_SUBS": fit.pvalue()["SUBSw"], "p_boot_SUBS": float(wb["Pr(>|t|)"]),
                "acuerdo": lc["estimate"], "acuerdo_p": lc["p"],
                "obs_SUBS": int((dd["SUBSw"] > 0).sum())}
        filas.append(fila)
        print(f"[{etiqueta}, {umbral}] N={fit._N:,}  IP={fila['b_IP']:.2f} ({fila['se_IP']:.2f},"
              f" p={fila['p_IP']:.3f})  IP_RTA_SUBS={fila['b_SUBS']:.2f} ({fila['se_SUBS']:.2f},"
              f" p={fila['p_SUBS']:.3f}; boot {fila['p_boot_SUBS']:.3f})"
              f"  Acuerdo={lc['estimate']:.2f} (p={lc['p']:.3f})  obs SUBS>0={fila['obs_SUBS']}")

pd.DataFrame(filas).to_csv(TABLES / f"{PAIS}_extra_v{VUELTA}.csv", index=False)

# ---- 3. Muestra del país (Stata y 14_tablas.py) -------------------------------------------
gta_k = gta_ip.assign(IPx=1.0)
m = py.copy()
for k, n in ((2, "F2"), (1, "F1"), (-1, "L1"), (-2, "L2")):
    m = m.assign(_y=m["year"] + k)
    m = m.merge(gta_k.rename(columns={"year": "_y"}), on=["IMP", "HS2012", "_y"], how="left")
    m = m.merge(cob.rename(columns={"year": "_y", "COB": "COBx"}), on=["IMP", "_y"], how="left")
    m[f"{n}_IP"] = m["IPx"].fillna(0.0)
    m[f"{n}_IP_RTA_SUBS"] = m[f"{n}_IP"] * m["COBx"].fillna(0.0)
    m = m.drop(columns=["_y", "IPx", "COBx"])
m = m.drop(columns=["EXP"]).sort_values(["IMP", "HS2012", "year"]).reset_index(drop=True)
for c in m.columns:
    if c != "IMP":
        m[c] = m[c].astype(float)
etiquetas = {
    "IMP": "Importador (ISO3)", "IMP_CODE": "Importador (código numérico)",
    "HS2012": "Producto HS 2012, 6 dígitos", "ISIC3_2": "Sector ISIC rev.3, 2 dígitos",
    "EXPORTS": f"Exportaciones de {PAIS}, miles de USD (BACI)", "ln_exp": "ln(EXPORTS)",
    "EXP_GROWTH": "100*Δln EXPORTS (según la vuelta)", "IP": "Política industrial del socio (t)",
    "SUBS_COVERAGE": "Cobertura de subsidios del acuerdo (DTA)", "IP_RTA_SUBS": "IP × cobertura",
}
for n in ("F2", "F1", "L1", "L2"):
    etiquetas[f"{n}_IP"] = f"IP en {n}"
    etiquetas[f"{n}_IP_RTA_SUBS"] = f"IP × cobertura en {n}"
salida = TABLES / f"{PAIS}_muestra_stata_v{VUELTA}.dta"
m.to_stata(salida, write_index=False, version=118, variable_labels=etiquetas)
print(f"\nGuardado {salida} ({len(m):,} filas) y {TABLES / f'{PAIS}_extra_v{VUELTA}.csv'}")
