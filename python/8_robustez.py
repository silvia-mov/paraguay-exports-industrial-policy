"""
* *********************************************************************
*
*       PRUEBAS DE ROBUSTEZ (1): inferencia, socios, PPML y diagnósticos
*
* *********************************************************************

Entrada:  $data_temp/DataforRegressions.parquet (o .dta), muestra EXP == PAIS
Salidas:  $tables/{PAIS}_robustez_v{VUELTA}.csv y detalle en pantalla

Se parte de la ec. (6) (ver 7_pais.py):
    Y ~ IP + IP_RTA_SUBS | importador + año + sector ISIC3 2 díg.,
    errores agrupados por importador.

1. Prueba por sorteo (inferencia por aleatorización; Hagemann 2019; Conley y
   Taber 2011): la cobertura del acuerdo de referencia (para Paraguay, el
   Mercosur: 1/3) se asigna a tantos importadores como socios tiene el acuerdo
   (Paraguay: 3), elegidos al azar entre los que no son socios, y se reestima. Se
   compara el estadístico t (no el coeficiente: grupos de distinto tamaño y
   varianza, Lehmann y Romano 2022, §17.3).
2. Sacar un socio del acuerdo por vez (Paraguay: sin Brasil, sin Argentina, sin Uruguay).
3. Poisson con efectos fijos (PPML; Santos Silva y Tenreyro 2006) para el
   nivel de exportaciones en dólares.
4. Diagnósticos: Breusch-Pagan de Koenker y Jarque-Bera en las
   ecs. (2)-(4); en la ec. (6): R² within, test F de los efectos de
   importador, Hausman robusto (Mundlak) y test de Wooldridge de
   correlación serial (panel importador × producto).
5. Errores agrupados por importador y año (dos vías).

Variable de entorno TESIS_SORTEOS: número de sorteos (por defecto 1999).
"""
import os
import re
import warnings

import numpy as np
import pandas as pd
import pyfixest as pf
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.diagnostic import het_breuschpagan

from config import DATA_TEMP, TABLES, VUELTA
from stata_utils import lincom
from pais import PAIS, acuerdo_referencia, cargar_muestra, socios_tratados_principales

warnings.filterwarnings("ignore")

UMBRAL = 1000          # keep if EXPORTS>1000 (USD 1 millón)
SORTEOS = int(os.environ.get("TESIS_SORTEOS", 1999))
SEMILLA = 20261019

cols = ["EXP", "IMP", "IMP_CODE", "year", "HS2012", "ISIC3_2", "EXPORTS", "ln_exp",
        "EXP_GROWTH", "IP", "SUBS_COVERAGE", "IP_RTA_SUBS"]
py = cargar_muestra(cols)   # (se llama "py" por Paraguay, pero es el país elegido)
COB_REF, SOCIOS_REF = acuerdo_referencia(py, obligatorio=True)
print(f"Vuelta {VUELTA} | {PAIS} exportador: {len(py):,} filas")

FE = "IMP_CODE + year + ISIC3_2"
CL = {"CRV1": "IMP_CODE"}
con = py[py["EXPORTS"] > UMBRAL]
sin = py
sin_out = lambda d: d[(d["EXP_GROWTH"] > -200) & (d["EXP_GROWTH"] < 200)]
specs = {
    "Esp1 crecimiento, con umbral": ("EXP_GROWTH", con),
    "Esp2 crecimiento sin outliers, con umbral": ("EXP_GROWTH", sin_out(con)),
    "Esp3 ln, con umbral": ("ln_exp", con),
    "Esp4 crecimiento, sin umbral": ("EXP_GROWTH", sin),
    "Esp5 crecimiento sin outliers, sin umbral": ("EXP_GROWTH", sin_out(sin)),
    "Esp6 ln, sin umbral": ("ln_exp", sin),
}
filas = []


def muestra(d, y):
    return d.dropna(subset=[y, "IP", "IP_RTA_SUBS", "IMP_CODE", "year", "ISIC3_2"])


def resumen(prueba, spec, fit, **extra):
    fila = {"prueba": prueba, "spec": spec, "N": fit._N}
    for v in ("IP", "IP_RTA_SUBS"):
        if v in fit._coefnames:
            fila[f"b_{v}"], fila[f"se_{v}"] = fit.coef()[v], fit.se()[v]
            fila[f"p_{v}"] = fit.pvalue()[v]
    if {"IP", "IP_RTA_SUBS"} <= set(fit._coefnames):
        lc = lincom(fit, {"IP": 1, "IP_RTA_SUBS": COB_REF})
        fila.update(acuerdo_b=lc["estimate"], acuerdo_se=lc["se"], acuerdo_p=lc["p"])
    fila.update(extra)
    filas.append(fila)
    txt = "  ".join(f"{v}={fila[f'b_{v}']:.3f} ({fila[f'se_{v}']:.3f}, p={fila[f'p_{v}']:.3f})"
                    for v in ("IP", "IP_RTA_SUBS") if f"b_{v}" in fila)
    if "acuerdo_b" in fila:
        txt += f"  Acuerdo={fila['acuerdo_b']:.3f} (p={fila['acuerdo_p']:.3f})"
    print(f"[{prueba} | {spec}] N={fila['N']:,}  {txt}"
          + "".join(f"  {k}={v:.3f}" if isinstance(v, float) else f"  {k}={v}"
                    for k, v in extra.items()))
    return fila


# ---- 1. Prueba por sorteo ----------------------------------------------------
# Se reemplaza la cobertura de TODOS los socios por 0 y se asigna la cobertura
# del acuerdo de referencia a un grupo de importadores del mismo tamaño que el
# real (Paraguay: ARG, BRA, URY con 1/3; la cobertura de Israel, 0,25, no
# tiene filas con IP = 1 y no afecta). Solo entran al sorteo
# importadores con al menos una fila con IP = 1 en la muestra (si no, la
# variable placebo sería siempre 0).
print("\n== 1. Prueba por sorteo (estadístico t de IP_RTA_SUBS)")
rng = np.random.default_rng(SEMILLA)
for nombre, (y, d) in specs.items():
    d = muestra(d, y).copy()
    con_ip = d.loc[d["IP"] == 1, "IMP"].unique()
    pool = np.array(sorted(set(con_ip) - set(SOCIOS_REF)))
    formula = f"{y} ~ IP + Z | {FE}"

    def t_terna(terna):
        d["Z"] = d["IP"] * np.where(d["IMP"].isin(terna), COB_REF, 0.0)
        f = pf.feols(formula, data=d, vcov=CL, fixef_rm="none")
        return f.coef()["Z"], f.tstat()["Z"]

    b_real, t_real = t_terna(SOCIOS_REF)
    # Chequeo: con el grupo real se reproduce el coeficiente de IP_RTA_SUBS
    # si el acuerdo de referencia es el único con cobertura > 0 y no cambia en
    # el tiempo (caso de Paraguay). Si no, el sorteo es una aproximación.
    ref = pf.feols(f"{y} ~ IP + IP_RTA_SUBS | {FE}", data=d, vcov=CL, fixef_rm="none")
    if not np.isclose(b_real, ref.coef()["IP_RTA_SUBS"], rtol=1e-6):
        print("   AVISO: hay otras coberturas > 0; el sorteo usa solo el acuerdo de referencia.")
    # Ternas distintas entre sí (sorteo sin repetir ternas)
    ternas = set()
    from math import comb
    k = len(SOCIOS_REF)
    while len(ternas) < min(SORTEOS, comb(len(pool), k)):
        ternas.add(tuple(sorted(rng.choice(pool, k, replace=False))))
    ts = np.array([t_terna(list(t))[1] for t in sorted(ternas)])
    ts = ts[np.isfinite(ts)]
    p_sorteo = (1 + np.sum(np.abs(ts) >= abs(t_real))) / (1 + len(ts))
    rango = int(np.sum(ts >= t_real)) + 1
    fila = {"prueba": "1 sorteo", "spec": nombre, "N": len(d),
            "b_IP_RTA_SUBS": b_real, "t_real": t_real,
            "p_sorteo": p_sorteo, "sorteos_validos": len(ts), "pool": len(pool),
            "puesto_real": rango}
    filas.append(fila)
    print(f"[sorteo | {nombre}] N={len(d):,}  IP_RTA_SUBS={b_real:.3f}"
          f"  t real={t_real:.2f}  p sorteo={p_sorteo:.3f}  (puesto {rango} de"
          f" {len(ts) + 1}; {len(pool)} importadores en el sorteo)")

# ---- 2. Sacar un socio por vez -------------------------------------------------
print("\n== 2. Sacar un socio por vez")
for nombre, (y, d) in specs.items():
    for fuera in [None] + SOCIOS_REF:
        dd = d if fuera is None else d[d["IMP"] != fuera]
        dd = muestra(dd, y)
        fit = pf.feols(f"{y} ~ IP + IP_RTA_SUBS | {FE}", data=dd, vcov=CL, fixef_rm="none")
        resumen("2 sin " + (fuera or "nadie"), nombre, fit,
                obs_SUBS=int((dd["IP_RTA_SUBS"] > 0).sum()))

# ---- 3. Poisson con efectos fijos (PPML) ---------------------------------------
# Y = EXPORTS en miles de USD. Efecto en %: 100*(exp(b)-1).
print("\n== 3. Poisson (PPML)")
for etiqueta, d in (("con umbral", con), ("sin umbral", sin)):
    d = muestra(d, "EXPORTS")
    f2 = pf.fepois("EXPORTS ~ IP", data=d, vcov="hetero")
    resumen("3 PPML ec.(2) sin EF", etiqueta, f2)
    f6 = pf.fepois(f"EXPORTS ~ IP + IP_RTA_SUBS | {FE}", data=d, vcov=CL)
    fila = resumen("3 PPML ec.(6)", etiqueta, f6)
    print(f"   en %: IP {100 * np.expm1(fila['b_IP']):.1f} %;"
          f" Acuerdo {100 * np.expm1(fila['acuerdo_b']):.1f} %")

# ---- 4. Diagnósticos ----------------------------------------------------------
print("\n== 4. Diagnósticos")
for etiqueta, d in (("con umbral", con), ("sin umbral", sin)):
    for ec, y, xs in (("(2)", "EXPORTS", ["IP"]), ("(3)", "ln_exp", ["IP"]),
                      ("(4)", "ln_exp", ["IP", "IP_RTA_SUBS"])):
        dd = d.dropna(subset=[y] + xs)
        X = sm.add_constant(dd[xs].astype(float))
        r = sm.OLS(dd[y].astype(float), X).fit()
        bp = het_breuschpagan(r.resid, X, robust=True)   # versión de Koenker
        jb = stats.jarque_bera(r.resid)
        filas.append({"prueba": "4 pruebas MCO", "spec": f"ec.{ec} {etiqueta}",
                      "N": int(r.nobs), "BP_Koenker": bp[0], "p_BP": bp[1],
                      "JB": jb.statistic, "p_JB": jb.pvalue,
                      "asimetria": stats.skew(r.resid), "curtosis": stats.kurtosis(r.resid, fisher=False)})
        print(f"[ec.{ec} {etiqueta}] N={int(r.nobs):,}  BP Koenker={bp[0]:.1f} (p={bp[1]:.3g})"
              f"  Jarque-Bera={jb.statistic:.0f} (p={jb.pvalue:.3g})")

for nombre, (y, d) in specs.items():
    d = muestra(d, y).copy()
    fit = pf.feols(f"{y} ~ IP + IP_RTA_SUBS | {FE}", data=d, vcov=CL, fixef_rm="none")
    r2w = fit._r2_within
    # Test F de los efectos de importador (MCO con dummies, errores clásicos).
    full = sm.OLS.from_formula(f"{y} ~ IP + IP_RTA_SUBS + C(IMP_CODE) + C(year) + C(ISIC3_2)", d).fit()
    rest = sm.OLS.from_formula(f"{y} ~ IP + IP_RTA_SUBS + C(year) + C(ISIC3_2)", d).fit()
    F, pF, _ = full.compare_f_test(rest)
    # Hausman robusto (Mundlak): MCO agrupado + promedios por importador de IP
    # e IP_RTA_SUBS; si esos promedios son conjuntamente 0, EA sería válido.
    d["m_IP"] = d.groupby("IMP_CODE")["IP"].transform("mean")
    d["m_SUBS"] = d.groupby("IMP_CODE")["IP_RTA_SUBS"].transform("mean")
    mund = pf.feols(f"{y} ~ IP + IP_RTA_SUBS + m_IP + m_SUBS | year + ISIC3_2", data=d,
                    vcov=CL, fixef_rm="none")
    w = mund.wald_test(R=np.array([[0, 0, 1, 0], [0, 0, 0, 1]]))
    # Wooldridge (2010) / Drukker (2003): panel = importador × producto; en
    # primeras diferencias, los residuos deben tener correlación −0,5.
    p = d.sort_values(["IMP_CODE", "HS2012", "year"]).copy()
    g = p.groupby(["IMP_CODE", "HS2012"])
    consec = g["year"].diff() == 1
    for v in (y, "IP", "IP_RTA_SUBS"):
        p["d_" + v] = g[v].diff().where(consec)
    p["d_year"] = p["year"].astype(str)
    dif = p.dropna(subset=["d_" + y, "d_IP", "d_IP_RTA_SUBS"])
    rd = sm.OLS.from_formula(f"d_{y} ~ d_IP + d_IP_RTA_SUBS + C(d_year)", dif).fit()
    dif = dif.assign(e=rd.resid)
    dif["e_l"] = dif.groupby(["IMP_CODE", "HS2012"])["e"].shift().where(
        dif.groupby(["IMP_CODE", "HS2012"])["year"].diff() == 1)
    dw = dif.dropna(subset=["e_l"])
    dw = dw.assign(panel=dw["IMP_CODE"].astype(str) + "_" + dw["HS2012"].astype(str))
    rw = sm.OLS(dw["e"], sm.add_constant(dw["e_l"])).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(dw["panel"])[0]})
    t_w = (rw.params["e_l"] + 0.5) / rw.bse["e_l"]
    p_w = 2 * stats.norm.sf(abs(t_w))
    filas.append({"prueba": "4 pruebas ec.(6)", "spec": nombre, "N": fit._N,
                  "R2_within": r2w, "F_importador": F, "p_F": pF,
                  "Hausman_Mundlak": float(w["statistic"]), "p_Hausman": float(w["pvalue"]),
                  "rho_Wooldridge": rw.params["e_l"], "p_Wooldridge": p_w, "N_Wooldridge": int(rw.nobs)})
    print(f"[ec.(6) {nombre}] R² within={r2w:.3f}  F importador={F:.2f} (p={pF:.3g})"
          f"  Hausman-Mundlak={float(w['statistic']):.2f} (p={float(w['pvalue']):.3g})"
          f"  Wooldridge: rho={rw.params['e_l']:.3f} vs −0,5 (p={p_w:.3g}; N={int(rw.nobs):,})")

# ---- 5. Errores agrupados por importador y año ---------------------------------
print("\n== 5. Errores agrupados en dos vías (importador y año)")
for nombre, (y, d) in specs.items():
    d = muestra(d, y)
    fit = pf.feols(f"{y} ~ IP + IP_RTA_SUBS | {FE}", data=d,
                   vcov={"CRV1": "IMP_CODE+year"}, fixef_rm="none")
    resumen("5 cluster IMP+año", nombre, fit)

salida = TABLES / f"{PAIS}_robustez_v{VUELTA}.csv"
pd.DataFrame(filas).to_csv(salida, index=False)
print(f"\nGuardado {salida}")
