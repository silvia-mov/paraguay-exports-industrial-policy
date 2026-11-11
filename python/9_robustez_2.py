"""
* *********************************************************************
*
*       PRUEBAS DE ROBUSTEZ (2): placebo con IC, EF de producto,
*                 sectores, efectos de arrastre *
* *********************************************************************

Entrada:  $data_temp/DataforRegressions.parquet, GTA_cleaned_IP.dta y
          DTA_subsidies.dta (para adelantos y rezagos a nivel producto)
Salidas:  $tables/{PAIS}_robustez2_v{VUELTA}.csv, $figures/{PAIS}_evento_v{VUELTA}_*.png

Base: ec. (6) (ver 7_pais.py y 8_robustez.py).

1. Placebo con intervalo de confianza (Eggers, Tuñón y Dafoe 2024): el
   adelanto F1 (la IP del año siguiente) no debería tener efecto. Se informa
   su IC 95 % y si ese IC excluye un efecto del tamaño del estimado
   principal (prueba de equivalencia TOST de Hartman e Hidalgo 2018).
2. Efectos fijos de producto: importador + año + producto HS 6 dígitos, e
   importador × producto + año (como el paper).
3. Sectores: profundidad por grupo de sectores (agro primario, alimentos,
   otras manufacturas, electricidad) y la ec. (6) sin electricidad (ISIC 40;
   en Paraguay es la energía de Itaipú y Yacyretá, regida por tratados
   binacionales).
4. Arrastre y estudio de eventos (Liu, Wang y Xu 2022): adelantos F2, F1 y
   rezagos L1, L2 en una misma regresión (años 2014–2020, donde existen
   todos), con gráfico.
"""
import os
import re
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyfixest as pf
from scipy import stats

from config import DATA_TEMP, FIGURES, TABLES, VUELTA
from stata_utils import lincom
from pais import PAIS, acuerdo_referencia, cargar_muestra, socios_tratados_principales

warnings.filterwarnings("ignore")

UMBRAL = 1000
CL = {"CRV1": "IMP_CODE"}
FE = "IMP_CODE + year + ISIC3_2"

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


def fila_coef(prueba, spec, fit, nombres, **extra):
    fila = {"prueba": prueba, "spec": spec, "N": fit._N}
    q = stats.t.ppf(0.975, fit._df_t)
    partes = []
    for v in nombres:
        if v not in fit._coefnames:
            continue
        b, se, p = fit.coef()[v], fit.se()[v], fit.pvalue()[v]
        fila.update({f"b_{v}": b, f"se_{v}": se, f"p_{v}": p,
                     f"lo_{v}": b - q * se, f"hi_{v}": b + q * se})
        partes.append(f"{v}={b:.3f} ({se:.3f}, p={p:.3f}; IC {b - q * se:.2f} a {b + q * se:.2f})")
    fila.update(extra)
    filas.append(fila)
    print(f"[{prueba} | {spec}] N={fit._N:,}  " + "  ".join(partes)
          + "".join(f"  {k}={v}" for k, v in extra.items()))
    return fila


def acuerdo(fit, ip="IP", subs="IP_RTA_SUBS"):
    lc = lincom(fit, {ip: 1, subs: COB_REF})
    return {"acuerdo": round(lc["estimate"], 3), "acuerdo_p": round(lc["p"], 3),
            "acuerdo_IC": f"{lc['ci_low']:.2f} a {lc['ci_high']:.2f}"}


# ---- Adelantos y rezagos a nivel producto (igual que 7_pais.py) ------------
gta_ip = pd.read_stata(DATA_TEMP / "GTA_cleaned_IP.dta", columns=["IMP", "HS2012", "year"],
                       convert_categoricals=False).assign(IPx=1)
cob = pd.read_stata(DATA_TEMP / "DTA_subsidies.dta", convert_categoricals=False)
cob = cob.loc[cob["EXP"] == PAIS, ["IMP", "year", "SUBS_COVERAGE"]].rename(
    columns={"SUBS_COVERAGE": "COBx"})


def desfasar(d, k, nombre):
    """Agrega {nombre}_IP y {nombre}_IP_RTA_SUBS con el tratamiento del año t+k."""
    d = d.assign(_y=d["year"] + k)
    d = d.merge(gta_ip.rename(columns={"year": "_y"}), on=["IMP", "HS2012", "_y"], how="left")
    d = d.merge(cob.rename(columns={"year": "_y"}), on=["IMP", "_y"], how="left")
    d[f"{nombre}_IP"] = d["IPx"].fillna(0)
    d[f"{nombre}_IP_RTA_SUBS"] = d[f"{nombre}_IP"] * d["COBx"].fillna(0)
    return d.drop(columns=["_y", "IPx", "COBx"])


chk = desfasar(py, 0, "K0")
assert (chk["K0_IP"] == chk["IP"]).all() and np.allclose(chk["K0_IP_RTA_SUBS"], chk["IP_RTA_SUBS"])
din = py
for k, n in ((2, "F2"), (1, "F1"), (-1, "L1"), (-2, "L2")):
    din = desfasar(din, k, n)
din_con = din[din["EXPORTS"] > UMBRAL]
din_specs = {
    "Esp1 crecimiento, con umbral": ("EXP_GROWTH", din_con),
    "Esp2 crecimiento sin outliers, con umbral": ("EXP_GROWTH", sin_out(din_con)),
    "Esp3 ln, con umbral": ("ln_exp", din_con),
    "Esp4 crecimiento, sin umbral": ("EXP_GROWTH", din),
}

# ---- 1. Placebo F1 con intervalo de confianza y equivalencia ------------------
print("\n== 1. Placebo F1 con IC 95 % y prueba de equivalencia (TOST)")
for nombre, (y, d) in din_specs.items():
    d = d[d["year"] < 2022]  # 2022 no tiene t+1
    fit = pf.feols(f"{y} ~ IP + IP_RTA_SUBS + F1_IP + F1_IP_RTA_SUBS | {FE}", data=d,
                   vcov=CL, fixef_rm="none")
    b, se = fit.coef()["F1_IP_RTA_SUBS"], fit.se()["F1_IP_RTA_SUBS"]
    delta = abs(fit.coef()["IP_RTA_SUBS"])  # tamaño del efecto contemporáneo
    df = fit._df_t
    # TOST: H0 |F1| >= delta; se rechaza si ambos tests unilaterales rechazan.
    p_tost = max(stats.t.sf((b + delta) / se, df), stats.t.sf((delta - b) / se, df))
    lc = lincom(fit, {"F1_IP": 1, "F1_IP_RTA_SUBS": COB_REF})
    fila_coef("1 placebo F1", nombre, fit, ["IP_RTA_SUBS", "F1_IP_RTA_SUBS"],
              delta=round(delta, 3), p_equivalencia=round(p_tost, 3),
              F1_acuerdo=round(lc["estimate"], 3),
              F1_acuerdo_IC=f"{lc['ci_low']:.2f} a {lc['ci_high']:.2f}")

# ---- 2. Efectos fijos de producto ---------------------------------------------
print("\n== 2. Efectos fijos de producto")
for nombre, (y, d) in specs.items():
    d = d.dropna(subset=[y, "IP", "IP_RTA_SUBS"])
    for etiqueta, fe in (("base", FE), ("EF producto", "IMP_CODE + year + HS2012"),
                         ("EF importador×producto", "IMP_CODE^HS2012 + year")):
        # fixef_rm="singleton" en los EF finos: grupos de una sola obs no aportan.
        fit = pf.feols(f"{y} ~ IP + IP_RTA_SUBS | {fe}", data=d, vcov=CL,
                       fixef_rm="none" if etiqueta == "base" else "singleton")
        fila_coef(f"2 {etiqueta}", nombre, fit, ["IP", "IP_RTA_SUBS"], **acuerdo(fit))

# ---- 3. Sectores ---------------------------------------------------------------
print("\n== 3. Sectores")
grupos = {"agro primario (01-05)": lambda s: s <= 5,
          "alimentos (15-16)": lambda s: (s >= 15) & (s <= 16),
          "otras manufacturas (17-37)": lambda s: (s >= 17) & (s <= 37),
          "electricidad (40)": lambda s: s == 40}
for nombre, (y, d) in specs.items():
    d = d.dropna(subset=[y, "IP", "IP_RTA_SUBS", "ISIC3_2"]).copy()
    vars_ = []
    for i, (g, f) in enumerate(grupos.items()):
        m = f(d["ISIC3_2"]).astype(float)
        d[f"IP_g{i}"] = d["IP"] * m
        d[f"SUBS_g{i}"] = d["IP_RTA_SUBS"] * m
        if (d[f"SUBS_g{i}"] > 0).sum() > 0:
            vars_ += [f"IP_g{i}", f"SUBS_g{i}"]
        elif (d[f"IP_g{i}"] > 0).sum() > 0:
            vars_ += [f"IP_g{i}"]
    fit = pf.feols(f"{y} ~ {' + '.join(vars_)} | {FE}", data=d, vcov=CL, fixef_rm="none")
    for i, g in enumerate(grupos):
        if f"SUBS_g{i}" in fit._coefnames:
            n_sub = int((d[f"SUBS_g{i}"] > 0).sum())
            fila_coef("3 por sector", f"{nombre} | {g}", fit, [f"IP_g{i}", f"SUBS_g{i}"],
                      obs_SUBS=n_sub, **acuerdo(fit, f"IP_g{i}", f"SUBS_g{i}"))
    # Sin electricidad
    dd = d[d["ISIC3_2"] != 40]
    fit = pf.feols(f"{y} ~ IP + IP_RTA_SUBS | {FE}", data=dd, vcov=CL, fixef_rm="none")
    fila_coef("3 sin electricidad", nombre, fit, ["IP", "IP_RTA_SUBS"],
              obs_SUBS=int((dd["IP_RTA_SUBS"] > 0).sum()), **acuerdo(fit))

# ---- 4. Estudio de eventos: F2, F1, contemporáneo, L1, L2 ----------------------
print("\n== 4. Estudio de eventos (2014–2020)")
orden = [("F2", -2), ("F1", -1), ("", 0), ("L1", 1), ("L2", 2)]
for nombre, (y, d) in din_specs.items():
    d = d[(d["year"] >= 2014) & (d["year"] <= 2020)]
    xs = []
    for n, _ in orden:
        xs += [f"{n}_IP" if n else "IP", f"{n}_IP_RTA_SUBS" if n else "IP_RTA_SUBS"]
    fit = pf.feols(f"{y} ~ {' + '.join(xs)} | {FE}", data=d, vcov=CL, fixef_rm="none")
    puntos = []
    for n, k in orden:
        s = f"{n}_IP_RTA_SUBS" if n else "IP_RTA_SUBS"
        i = f"{n}_IP" if n else "IP"
        lc = lincom(fit, {i: 1, s: COB_REF})
        puntos.append((k, fit.coef()[s], fit.se()[s], lc["estimate"], lc["ci_low"], lc["ci_high"]))
        fila_coef("4 evento", f"{nombre} | k={k:+d}", fit, [i, s], **acuerdo(fit, i, s))
    R = np.array([[1.0 if c == r else 0.0 for c in fit._coefnames]
                  for r in ("F2_IP_RTA_SUBS", "F1_IP_RTA_SUBS")])
    pre = fit.wald_test(R=R)
    acum = lincom(fit, {"IP_RTA_SUBS": 1, "L1_IP_RTA_SUBS": 1, "L2_IP_RTA_SUBS": 1})
    filas.append({"prueba": "4 evento resumen", "spec": nombre, "N": fit._N,
                  "p_pretendencia_conjunta": float(pre["pvalue"]),
                  "acumulado_0_a_2": acum["estimate"], "acum_p": acum["p"],
                  "acum_IC": f"{acum['ci_low']:.2f} a {acum['ci_high']:.2f}"})
    print(f"   adelantos F2 y F1 conjuntos = 0: p={float(pre['pvalue']):.3f};"
          f"  acumulado t a t+2 = {acum['estimate']:.2f} (p={acum['p']:.3f})")
    # Gráfico: coeficiente de profundidad por año relativo, con IC 95 %
    q = stats.t.ppf(0.975, fit._df_t)
    k_, b_, se_ = zip(*[(p[0], p[1], p[2]) for p in puntos])
    fig, ax = plt.subplots(figsize=(6, 3.6))
    ax.axhline(0, color="#888", lw=0.8)
    ax.axvline(-0.5, color="#bbb", lw=0.8, ls="--")
    ax.errorbar(k_, b_, yerr=[q * s for s in se_], fmt="o", color="#1f4e79", capsize=4)
    ax.set_xticks(list(k_))
    ax.set_xticklabels(["t−2", "t−1", "t", "t+1", "t+2"])
    ax.set_xlabel("Año respecto de la medida de política industrial")
    ax.set_ylabel("Coef. de profundidad (IP_RTA_SUBS)")
    ax.set_title(f"{PAIS} — {nombre}", fontsize=10)
    fig.tight_layout()
    slug = re.sub(r"[^a-z0-9]+", "_", nombre.lower()).strip("_")
    fig.savefig(FIGURES / f"{PAIS}_evento_v{VUELTA}_{slug}.png", dpi=150)
    plt.close(fig)

salida = TABLES / f"{PAIS}_robustez2_v{VUELTA}.csv"
pd.DataFrame(filas).to_csv(salida, index=False)
print(f"\nGuardado {salida}")
