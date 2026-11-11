"""
* *********************************************************************
*
*       TABLAS FINALES DEL PAÍS (las del README y de resultados/)
*
* *********************************************************************

Junta en un solo lugar los resultados del país elegido (TESIS_PAIS, por
defecto PRY). Recalcula desde la muestra las ecuaciones (2)-(4) con sus
diagnósticos, la ecuación (6) en sus 6 variantes, el test de Wooldridge, el
placebo, los rezagos y la estimación por sector; toma la inferencia adicional
(bootstrap, sorteo, cluster doble, sacar un socio, PPML, EF de producto) de las
salidas de los scripts 7 a 9.

Correr antes, con las mismas variables de entorno:
    7_pais.py, 8_robustez.py, 9_robustez_2.py y 10_extra.py (que guarda la muestra).

Entrada:  $tables/{PAIS}_muestra_stata_v{VUELTA}.dta   (de 10_extra.py)
          $tables/{PAIS}_resultados_v{VUELTA}.csv      (de 7_pais.py)
          $tables/{PAIS}_robustez_v{VUELTA}.csv        (de 8_robustez.py)
          $tables/{PAIS}_robustez2_v{VUELTA}.csv       (de 9_robustez_2.py)
Salida:   $tables/{PAIS}_tablas_v{VUELTA}/*.csv  (mismo formato que resultados/)

Los resultados de la tesis (resultados/paraguay_*.csv) se obtuvieron con
    TESIS_VUELTA=2 TESIS_SIN_TRUNCAR=1 TESIS_T_MENOS_1=1
"""
import warnings

import numpy as np
import pandas as pd
import pyfixest as pf
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.diagnostic import het_breuschpagan, het_white
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.stattools import durbin_watson

from config import TABLES, VUELTA
from pais import PAIS, acuerdo_referencia, socios_tratados_principales

warnings.filterwarnings("ignore")

FE, CL = "IMP_CODE + year + ISIC3_2", {"CRV1": "IMP_CODE"}
SALIDA = TABLES / f"{PAIS}_tablas_v{VUELTA}"
SALIDA.mkdir(parents=True, exist_ok=True)
ent = lambda n: TABLES / f"{PAIS}_{n}_v{VUELTA}"

py = pd.read_stata(ent("muestra_stata").with_suffix(".dta"))
py["IMP_CODE"] = py["IMP_CODE"].astype(int)
COB, SOCIOS = acuerdo_referencia(py)
if np.isnan(COB):
    raise SystemExit("Sin socios tratados (IP_RTA_SUBS > 0) no hay β2 que tabular.")
UMB = py[py.EXPORTS > 1000]
sin_out = lambda d: d[d.EXP_GROWTH.isna() | (d.EXP_GROWTH.abs() < 200)]
print(f"Vuelta {VUELTA} | {PAIS}: {len(py):,} observaciones")

# ---------- Descriptiva ---------------------------------------------------------------------------------
desc = py[["EXPORTS", "ln_exp", "EXP_GROWTH", "IP", "IP_RTA_SUBS"]].describe().T[
    ["count", "mean", "std", "min", "50%", "max"]]

# ---------- Ecuaciones (2)-(4): MCO, errores estándar habituales, diagnósticos -------------------------
t24 = []
for ec, y, xs in (("(2)", "EXPORTS", ["IP"]), ("(3)", "ln_exp", ["IP"]), ("(4)", "ln_exp", ["IP", "IP_RTA_SUBS"])):
    d = py.dropna(subset=[y] + xs)
    X = sm.add_constant(d[xs].astype(float))
    r = sm.OLS(d[y].astype(float), X).fit()
    bp = het_breuschpagan(r.resid, X, robust=True)      # Breusch-Pagan, versión de Koenker
    wh = het_white(r.resid, X)                           # con IP binaria coincide con Breusch-Pagan
    jb = stats.jarque_bera(r.resid)
    fila = {"Ecuación": ec, "Variable dependiente": y, "N": int(r.nobs), "R2": r.rsquared,
            "R2_ajustado": r.rsquared_adj, "F": r.fvalue, "p_F": r.f_pvalue,
            "BP_Koenker": bp[0], "p_BP": bp[1], "White": wh[0], "p_White": wh[1],
            "Jarque_Bera": jb.statistic, "p_JB": jb.pvalue, "Durbin_Watson": durbin_watson(r.resid),
            "VIF_max": max(variance_inflation_factor(X.values, i) for i in range(1, X.shape[1]))}
    for v in ["const"] + xs:
        fila[f"b_{v}"], fila[f"se_{v}"], fila[f"p_{v}"] = r.params[v], r.bse[v], r.pvalues[v]
    t24.append(fila)
t24 = pd.DataFrame(t24)


# ---------- Ecuación (6) --------------------------------------------------------------------------------
def ec6(y, d, extra=""):
    v = [y, "IP", "IP_RTA_SUBS"] + [c for c in ["F1_IP", "F1_IP_RTA_SUBS", "L1_IP", "L1_IP_RTA_SUBS",
                                               "L2_IP", "L2_IP_RTA_SUBS"] if c in extra]
    d = d.dropna(subset=v)
    f = pf.feols(f"{y} ~ IP + IP_RTA_SUBS{extra} | {FE}", data=d, vcov=CL, fixef_rm="none")
    return f, d


def fila6(nombre, f, d):
    c, s, p = f.coef(), f.se(), f.pvalue()
    names = list(f._coefnames)
    L = np.zeros(len(names)); L[names.index("IP")] = 1; L[names.index("IP_RTA_SUBS")] = COB
    mb = float(L @ c.values); ms = float(np.sqrt(L @ f._vcov @ L))
    G = d.IMP_CODE.nunique()
    return {"Especificación": nombre, "N": f._N, "b_IP": c["IP"], "se_IP": s["IP"], "p_IP": p["IP"],
            "b_SUBS": c["IP_RTA_SUBS"], "se_SUBS": s["IP_RTA_SUBS"], "p_SUBS": p["IP_RTA_SUBS"],
            "Acuerdo_b": mb, "Acuerdo_se": ms, "Acuerdo_p": 2 * stats.t.sf(abs(mb / ms), G - 1),
            "R2": f._r2, "R2_within": f._r2_within, "importadores": G,
            "obs_SUBS>0": int((d.IP_RTA_SUBS > 0).sum())}


SPECS = [("Logaritmo (sin umbral)", "ln_exp", py),
         ("Tasa de crecimiento", "EXP_GROWTH", py),
         ("Crecimiento sin valores atípicos", "EXP_GROWTH", sin_out(py)),
         ("Logaritmo sin valores atípicos", "ln_exp", sin_out(py)),
         ("Logaritmo con umbral de USD 1 millón", "ln_exp", UMB),
         ("Crecimiento con umbral de USD 1 millón", "EXP_GROWTH", UMB)]
t6 = pd.DataFrame([fila6(n, *ec6(y, d)) for n, y, d in SPECS])


# Wooldridge (panel importador × producto): en primeras diferencias, correlación de residuos = −0,5
def wooldridge(y, d):
    p = d.dropna(subset=[y]).sort_values(["IMP_CODE", "HS2012", "year"]).copy()
    g = p.groupby(["IMP_CODE", "HS2012"]); cons = g["year"].diff() == 1
    for v in (y, "IP", "IP_RTA_SUBS"):
        p["d_" + v] = g[v].diff().where(cons)
    p["d_year"] = p["year"].astype(int).astype(str)
    dif = p.dropna(subset=["d_" + y, "d_IP", "d_IP_RTA_SUBS"])
    rd = sm.OLS.from_formula(f"d_{y} ~ d_IP + d_IP_RTA_SUBS + C(d_year)", dif).fit()
    dif = dif.assign(e=rd.resid)
    gg = dif.groupby(["IMP_CODE", "HS2012"])
    dif["e_l"] = gg["e"].shift().where(gg["year"].diff() == 1)
    w = dif.dropna(subset=["e_l"])
    rw = sm.OLS(w["e"], sm.add_constant(w["e_l"])).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(w.IMP_CODE.astype(str) + "_" + w.HS2012.astype(str))[0]})
    t = (rw.params["e_l"] + 0.5) / rw.bse["e_l"]
    return rw.params["e_l"], 2 * stats.norm.sf(abs(t)), int(rw.nobs)


panel = pd.DataFrame([("Logaritmo", *wooldridge("ln_exp", py)),
                      ("Tasa de crecimiento", *wooldridge("EXP_GROWTH", py))],
                     columns=["Especificación", "rho", "p (H0: rho = -0,5)", "N"])
# Prueba F de los efectos fijos de importador y Hausman-Mundlak: de 8_robustez.py
rob = pd.read_csv(ent("robustez").with_suffix(".csv"))
_r = rob[rob.prueba.astype(str).str.startswith("4 pruebas ec")].set_index("spec")
for i, sp in ((0, "Esp6 ln, sin umbral"), (1, "Esp4 crecimiento, sin umbral")):
    for c in ("F_importador", "p_F", "Hausman_Mundlak", "p_Hausman"):
        panel.loc[i, c] = _r.loc[sp, c]

# ---------- Placebo (adelanto de un año) y rezagos ------------------------------------------------------
t_pl = []
for nom, y in (("Logaritmo", "ln_exp"), ("Tasa de crecimiento", "EXP_GROWTH")):
    f, _ = ec6(y, py[py.year < 2022], " + F1_IP + F1_IP_RTA_SUBS")
    t_pl.append({"Especificación": nom, "Prueba": "Placebo: adelanto de un año (t+1)", "N": f._N,
                 "b_contemporáneo": f.coef()["IP_RTA_SUBS"], "p_contemporáneo": f.pvalue()["IP_RTA_SUBS"],
                 "b_prueba": f.coef()["F1_IP_RTA_SUBS"], "se_prueba": f.se()["F1_IP_RTA_SUBS"],
                 "p_prueba": f.pvalue()["F1_IP_RTA_SUBS"]})
    f, _ = ec6(y, py[py.year >= 2014], " + L1_IP + L1_IP_RTA_SUBS + L2_IP + L2_IP_RTA_SUBS")
    for L in ("L1", "L2"):
        t_pl.append({"Especificación": nom, "Prueba": f"Rezago {L[1]} año(s)", "N": f._N,
                     "b_contemporáneo": f.coef()["IP_RTA_SUBS"], "p_contemporáneo": f.pvalue()["IP_RTA_SUBS"],
                     "b_prueba": f.coef()[f"{L}_IP_RTA_SUBS"], "se_prueba": f.se()[f"{L}_IP_RTA_SUBS"],
                     "p_prueba": f.pvalue()[f"{L}_IP_RTA_SUBS"]})
t_pl = pd.DataFrame(t_pl)

# ---------- Por sector -----------------------------------------------------------------------------------
GR = {"Agricultura y otros primarios (CIIU 01-14)": lambda s: s < 15,
      "Alimentos, bebidas y tabaco (CIIU 15-16)": lambda s: s.between(15, 16),
      "Otras manufacturas (CIIU 17-37)": lambda s: s.between(17, 37)}
t_sec = []
for nom, y in (("Logaritmo", "ln_exp"), ("Tasa de crecimiento", "EXP_GROWTH")):
    for g, cond in GR.items():
        d = py[cond(py.ISIC3_2.astype(float))]
        if not (d.IP_RTA_SUBS > 0).any():
            continue
        r = fila6(g, *ec6(y, d)); r["Especificación"] = nom; r["Grupo"] = g
        t_sec.append(r)
t_sec = pd.DataFrame(t_sec)[["Especificación", "Grupo", "N", "obs_SUBS>0", "b_IP", "p_IP", "b_SUBS",
                             "p_SUBS", "Acuerdo_b", "Acuerdo_p"]]

# ---------- Inferencia adicional (de las salidas de los scripts 7 a 9) ----------------------------------
rob2 = pd.read_csv(ent("robustez2").with_suffix(".csv"))
res = pd.read_csv(ent("resultados").with_suffix(".csv"))
principal = socios_tratados_principales(py, 1)[0]
E = {"Logaritmo": "Esp6 ln, sin umbral", "Tasa de crecimiento": "Esp4 crecimiento, sin umbral"}


def g(df, prueba, spec, col):
    s = df[(df.prueba.astype(str).str.startswith(prueba)) & (df.spec == spec)][col]
    return float(s.iloc[0]) if len(s) else np.nan


t_inf = []
for nom, sp in E.items():
    rr = res[res.spec.str.startswith("(6) " + sp.split(",")[0])].iloc[0]
    t_inf += [
        {"Especificación": nom, "Prueba": "Errores agrupados por importador (base)", "b_SUBS": rr.b_IP_RTA_SUBS, "p": rr.p_IP_RTA_SUBS},
        {"Especificación": nom, "Prueba": "Bootstrap salvaje (9.999 repeticiones)", "b_SUBS": rr.b_IP_RTA_SUBS, "p": rr.p_boot_IP_RTA_SUBS},
        {"Especificación": nom, "Prueba": "Sorteo de socios placebo", "b_SUBS": g(rob, "1 sorteo", sp, "b_IP_RTA_SUBS"), "p": g(rob, "1 sorteo", sp, "p_sorteo")},
        {"Especificación": nom, "Prueba": "Errores agrupados por importador y año", "b_SUBS": g(rob, "5", sp, "b_IP_RTA_SUBS"), "p": g(rob, "5", sp, "p_IP_RTA_SUBS")},
        {"Especificación": nom, "Prueba": f"Sin {principal}", "b_SUBS": g(rob, f"2 sin {principal}", sp, "b_IP_RTA_SUBS"), "p": g(rob, f"2 sin {principal}", sp, "p_IP_RTA_SUBS")},
        {"Especificación": nom, "Prueba": "Efectos fijos de producto", "b_SUBS": g(rob2, "2 EF producto", sp, "b_IP_RTA_SUBS"), "p": g(rob2, "2 EF producto", sp, "p_IP_RTA_SUBS")},
        {"Especificación": nom, "Prueba": "Efectos fijos de importador por producto", "b_SUBS": g(rob2, "2 EF imp", sp, "b_IP_RTA_SUBS"), "p": g(rob2, "2 EF imp", sp, "p_IP_RTA_SUBS")},
        {"Especificación": nom, "Prueba": "Bootstrap del efecto neto del acuerdo", "b_SUBS": rr.acuerdo_b, "p": rr.p_boot_acuerdo},
    ]
t_inf.append({"Especificación": "Niveles (Poisson)", "Prueba": "PPML con los mismos efectos fijos",
              "b_SUBS": g(rob, "3 PPML ec.(6)", "sin umbral", "b_IP_RTA_SUBS"),
              "p": g(rob, "3 PPML ec.(6)", "sin umbral", "p_IP_RTA_SUBS")})
t_inf = pd.DataFrame(t_inf)

# ---------- Guardar ---------------------------------------------------------------------------------------
for nombre, t, idx in (("descriptiva", desc, True), ("ec2_4_mco", t24, False), ("ec6", t6, False),
                       ("pruebas_panel", panel, False), ("placebo_rezagos", t_pl, False),
                       ("por_sector", t_sec, False), ("inferencia", t_inf, False)):
    t.to_csv(SALIDA / f"{PAIS.lower()}_{nombre}.csv", index=idx, float_format="%.6g")
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
for t in (t24, t6, panel, t_pl, t_sec, t_inf):
    print(t.round(4).to_string(), "\n")
print(f"Guardado en {SALIDA}")
