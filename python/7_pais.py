"""
* *********************************************************************
*
*       ESTIMACIÓN PARA UN PAÍS EXPORTADOR (extensión; no está en el paper)
*
* *********************************************************************

Entrada:  $data_temp/DataforRegressions.parquet o .dta (paso 4; la vuelta
          depende de cómo se armó DTA_subsidies en el paso 1)
Salidas:  $tables/{PAIS}_resultados_v{VUELTA}.csv (una fila por especificación)
          y el detalle en pantalla

País: variable de entorno TESIS_PAIS (ISO3; por defecto PRY = Paraguay).
Muestra: ese país como exportador (EXP == PAIS).

Especificaciones:
  (2) MCO      EXPORTS ~ IP
  (3) MCO      ln(EXPORTS) ~ IP
  (4) MCO      ln(EXPORTS) ~ IP + IP_RTA_SUBS
  (6) EF       Y ~ IP + IP_RTA_SUBS | importador + año + sector ISIC3 2 díg.,
               cluster por importador. Y = ln(EXPORTS) o EXP_GROWTH; con y sin
               el umbral EXPORTS>1000; sin outliers = |EXP_GROWTH|<200 (Tabla 5
               del paper). Las 6 variantes se llaman Esp1 a Esp6.

Para cada especificación con IP_RTA_SUBS se informa además:
  - efecto neto para un socio del acuerdo de referencia = lincom IP + d*IP_RTA_SUBS
    (d = cobertura del acuerdo; para Paraguay, Mercosur: d = 4/12. El coeficiente
    de IP_RTA_SUBS es por UNA unidad de cobertura, que ningún acuerdo alcanza).
    Ver pais.py.
  - p-valor de IP_RTA_SUBS y del efecto neto con wild cluster bootstrap
    (Rademacher, 9.999 repeticiones; TESIS_BOOT_REPS para cambiarlo)
  - cuántas observaciones tienen IP_RTA_SUBS > 0 y de qué socios vienen
"""
import os
import re
import warnings

import numpy as np
import pandas as pd
import pyfixest as pf

from config import DATA_TEMP, TABLES, VUELTA
from stata_utils import lincom
from pais import PAIS, acuerdo_referencia, cargar_muestra

warnings.filterwarnings("ignore", message=".*singleton.*")

UMBRAL = 1000          # keep if EXPORTS>1000 (USD 1 millón; el paso 4 ya quitó <500)
REPS = int(os.environ.get("TESIS_BOOT_REPS", 9999))

cols = ["EXP", "IMP", "IMP_CODE", "year", "HS2012", "ISIC3_2", "EXPORTS", "ln_exp",
        "EXP_GROWTH", "IP", "IP_RTA", "rta", "SUBS_COVERAGE", "IP_RTA_SUBS"]
py = cargar_muestra(cols)   # (se llama "py" por Paraguay, pero es el país elegido)
COB_REF, SOCIOS_REF = acuerdo_referencia(py)
HAY_SUBS = bool((py["IP_RTA_SUBS"] > 0).any())
print(f"Vuelta {VUELTA} | {PAIS} exportador: {len(py):,} filas "
      f"({(py['EXPORTS'] > UMBRAL).sum():,} con EXPORTS>{UMBRAL})")
print("Socios con IP_RTA_SUBS>0:",
      py.loc[py["IP_RTA_SUBS"] > 0, "IMP"].value_counts().to_dict())

filas = []


def estimar(nombre, formula, datos, vcov, fe=False):
    if not HAY_SUBS:   # sin socios tratados, IP_RTA_SUBS es siempre 0: se omite
        formula = re.sub(r"\s*\+\s*(F1_|L1_|L2_)?IP_RTA_SUBS", "", formula)
    # muestra explícita: sin faltantes en las variables usadas
    usadas = [c for c in cols if re.search(rf"\b{c}\b", formula)]
    datos = datos.dropna(subset=usadas)
    fit = pf.feols(formula, data=datos, vcov=vcov, fixef_rm="none")
    assert fit._N == len(datos)
    fila = {"spec": nombre, "formula": formula, "N": fit._N}
    for v in ("IP", "IP_RTA_SUBS"):
        if v in fit._coefnames:
            fila[f"b_{v}"] = fit.coef()[v]
            fila[f"se_{v}"] = fit.se()[v]
            fila[f"p_{v}"] = fit.pvalue()[v]
    if "IP_RTA_SUBS" in fit._coefnames:
        fila["n_IP_RTA_SUBS>0"] = int((datos["IP_RTA_SUBS"] > 0).sum())
        lc = lincom(fit, {"IP": 1, "IP_RTA_SUBS": COB_REF})
        fila.update({"acuerdo_b": lc["estimate"], "acuerdo_se": lc["se"],
                     "acuerdo_p": lc["p"]})
        if fe:
            fila["clusters"] = int(datos["IMP_CODE"].nunique())
            wb = fit.wildboottest(param="IP_RTA_SUBS", reps=REPS, seed=20261018)
            fila["p_boot_IP_RTA_SUBS"] = float(wb["Pr(>|t|)"])
            # Bootstrap del efecto neto: con Z = IP_RTA_SUBS - d*IP, el
            # coeficiente de IP en "Y ~ IP + Z" es IP + d*IP_RTA_SUBS.
            rep = datos.assign(Z_ACUERDO=datos["IP_RTA_SUBS"] - COB_REF * datos["IP"])
            fit_m = pf.feols(formula.replace("IP_RTA_SUBS", "Z_ACUERDO"), data=rep,
                             vcov=vcov, fixef_rm="none")
            assert np.isclose(fit_m.coef()["IP"], fila["acuerdo_b"])
            wb = fit_m.wildboottest(param="IP", reps=REPS, seed=20261018)
            fila["p_boot_acuerdo"] = float(wb["Pr(>|t|)"])
    filas.append(fila)
    print(f"\n[{nombre}] N={fila['N']:,}  " + "  ".join(
        f"{v}={fila[f'b_{v}']:.3f} ({fila[f'se_{v}']:.3f}, p={fila[f'p_{v}']:.3f})"
        for v in ("IP", "IP_RTA_SUBS") if f"b_{v}" in fila))
    if "acuerdo_b" in fila:
        extra = (f", p_boot IP_RTA_SUBS={fila['p_boot_IP_RTA_SUBS']:.3f}"
                 f", p_boot efecto neto={fila['p_boot_acuerdo']:.3f}"
                 f", clusters={fila['clusters']}") \
            if fe else ""
        print(f"   efecto neto acuerdo (IP + {COB_REF:.3f}*IP_RTA_SUBS) = {fila['acuerdo_b']:.3f} "
              f"({fila['acuerdo_se']:.3f}, p={fila['acuerdo_p']:.3f}); "
              f"obs con IP_RTA_SUBS>0 = {fila['n_IP_RTA_SUBS>0']}{extra}")
    return fit


con = py[py["EXPORTS"] > UMBRAL]
sin = py

# ---- Ecuaciones (2) a (4): MCO simple, errores estándar habituales -----------
for etiqueta, d in (("con umbral", con), ("sin umbral", sin)):
    estimar(f"(2) MCO niveles, {etiqueta}", "EXPORTS ~ IP", d, "iid")
    estimar(f"(3) MCO ln, {etiqueta}", "ln_exp ~ IP", d, "iid")
    estimar(f"(4) MCO ln + profundidad, {etiqueta}", "ln_exp ~ IP + IP_RTA_SUBS", d, "iid")

# ---- Ecuación (6): efectos fijos importador + año + sector, cluster importador -
FE = "IMP_CODE + year + ISIC3_2"
CL = {"CRV1": "IMP_CODE"}
sin_out = lambda d: d[(d["EXP_GROWTH"] > -200) & (d["EXP_GROWTH"] < 200)]
specs = [
    ("Esp1 crecimiento, con umbral", "EXP_GROWTH", con),
    ("Esp2 crecimiento sin outliers, con umbral", "EXP_GROWTH", sin_out(con)),
    ("Esp3 ln, con umbral", "ln_exp", con),
    ("Esp4 crecimiento, sin umbral", "EXP_GROWTH", sin),
    ("Esp5 crecimiento sin outliers, sin umbral", "EXP_GROWTH", sin_out(sin)),
    ("Esp6 ln, sin umbral", "ln_exp", sin),
]
for nombre, y, d in specs:
    estimar(f"(6) {nombre}", f"{y} ~ IP + IP_RTA_SUBS | {FE}", d, CL, fe=True)

# ---- Placebo (adelanto) y rezagos, construidos a nivel PRODUCTO ---------------
# IP de t+1 o t-1 se toma de la base de medidas (GTA_cleaned_IP: importador,
# producto, año), no de las filas con comercio, para no perder los años sin
# exportaciones ni mezclar productos (armarlos con un collapse a importador-año
# mezclaría productos distintos).
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


# Chequeo: con k=0 se reconstruye exactamente IP e IP_RTA_SUBS de la base
chk = desfasar(py, 0, "K0")
assert (chk["K0_IP"] == chk["IP"]).all() and np.allclose(chk["K0_IP_RTA_SUBS"], chk["IP_RTA_SUBS"])
din = desfasar(desfasar(desfasar(py, 1, "F1"), -1, "L1"), -2, "L2")
cols += ["F1_IP", "F1_IP_RTA_SUBS", "L1_IP", "L1_IP_RTA_SUBS", "L2_IP", "L2_IP_RTA_SUBS"]
din_con = din[(din["EXPORTS"] > UMBRAL) & (din["year"] < 2022)]   # 2022 no tiene t+1
def mostrar(fit, prefijos):
    for v in fit._coefnames:
        if v.startswith(prefijos):
            print(f"   {v} = {fit.coef()[v]:.3f} ({fit.se()[v]:.3f}, p={fit.pvalue()[v]:.3f})")


for y in ("ln_exp", "EXP_GROWTH"):
    fit = estimar(f"Placebo F1, {y}, con umbral",
                  f"{y} ~ IP + IP_RTA_SUBS + F1_IP + F1_IP_RTA_SUBS | {FE}", din_con, CL)
    mostrar(fit, ("F1_",))
    din_lag = din[(din["EXPORTS"] > UMBRAL) & (din["year"] >= 2014)]  # t-2 >= 2012
    fit = estimar(f"Rezagos L1 L2, {y}, con umbral",
                  f"{y} ~ IP + IP_RTA_SUBS + L1_IP + L1_IP_RTA_SUBS + L2_IP + L2_IP_RTA_SUBS"
                  f" | {FE}", din_lag, CL)
    mostrar(fit, ("L1_", "L2_"))
    if HAY_SUBS:
        acum = lincom(fit, {"IP_RTA_SUBS": 1, "L1_IP_RTA_SUBS": 1})
        print(f"   acumulado IP_RTA_SUBS + L1 = {acum['estimate']:.3f} "
              f"({acum['se']:.3f}, p={acum['p']:.3f})")

out = pd.DataFrame(filas)
out.insert(0, "vuelta", VUELTA)
out.insert(0, "pais", PAIS)
out.to_csv(TABLES / f"{PAIS}_resultados_v{VUELTA}.csv", index=False)
print(f"\nGuardado {TABLES / f'{PAIS}_resultados_v{VUELTA}.csv'}")
