"""
* *********************************************************************
*
*       Inferencia para el corte por tipo de subsidio
*
* *********************************************************************

Entrada:  $data_temp/DataforRegressions.parquet, GTA_cleaned.dta,
          ProductsLong_GTA_IP.dta
Salida:   $tables/{PAIS}_tipo_subsidio_inferencia_v{VUELTA}.csv

Complementa 12_tipo_subsidio.py para el tipo principal
("Tax-based export incentive", incentivo fiscal a la exportación) y el
grupo B (incentivos a la exportación), en las especificaciones de
crecimiento (Esp1, 2, 4, 5). Modelo:
    Y ~ IP_T + SUBS_T + IP_OTRA + SUBS_OTRA | IMP + año + ISIC3_2
1. Wild cluster bootstrap (Rademacher, cluster importador) de SUBS_T y del
   efecto neto IP_T + d·SUBS_T (reparametrizando Z = SUBS_T − d·IP_T,
   como en 7_pais.py).
2. Prueba por sorteo del TIPO. El sorteo de ternas de 8_robustez.py
   no se puede hacer aquí: en Paraguay, fuera del Mercosur solo 2–3
   importadores tienen filas con IP_T = 1 (no hay ternas). En su lugar se pregunta si el tipo T
   es especial: entre las filas con IP = 1 se reparte al azar la etiqueta
   "tipo T", manteniendo cuántas filas T tiene cada importador (sorteo
   estratificado por importador), y se reestima. Estadístico: t de SUBS_T.
   p bajo = el incentivo fiscal tiene un efecto distinto del de un grupo
   cualquiera de medidas del mismo tamaño.
3. Sacar un socio por vez (los dos socios con más observaciones tratadas;
   en Paraguay, BRA y ARG).

Variables de entorno: TESIS_BOOT_REPS (9999), TESIS_SORTEOS (1999).
"""
import os
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
KEYS = ["IMP", "HS2012", "year"]
REPS = int(os.environ.get("TESIS_BOOT_REPS", 9999))
SORTEOS = int(os.environ.get("TESIS_SORTEOS", 1999))
SEMILLA = 20261021
EXPORTACION = ["Export subsidy", "Tax-based export incentive", "Trade finance",
               "Other export incentive", "Financial assistance in foreign market"]
GRUPOS = {"Incentivo fiscal a la exportación": ["Tax-based export incentive"],
          "Grupo B: incentivos a la exportación": EXPORTACION}

# ---- Datos (igual que 12_tipo_subsidio.py) -----------------------------
gta = pd.read_stata(DATA_TEMP / "GTA_cleaned.dta",
                    columns=["ID", "ISO_impl", "inception_year", "code_class", "interventiontype"],
                    convert_categoricals=False)
gta = gta[gta["code_class"] == 6]
prod = pd.read_stata(DATA_TEMP / "ProductsLong_GTA_IP.dta", convert_categoricals=False)
tipos = gta.merge(prod, on="ID").rename(
    columns={"Product": "HS2012", "ISO_impl": "IMP", "inception_year": "year"})
tipos["HS2012"] = pd.to_numeric(tipos["HS2012"], errors="coerce")
tipos = tipos[KEYS + ["interventiontype"]].drop_duplicates()

cols = ["EXP", "IMP", "IMP_CODE", "year", "HS2012", "ISIC3_2", "EXPORTS",
        "EXP_GROWTH", "IP", "SUBS_COVERAGE", "IP_RTA_SUBS"]
py = cargar_muestra(cols)   # (se llama "py" por Paraguay, pero es el país elegido)
COB_REF, SOCIOS_REF = acuerdo_referencia(py, obligatorio=True)
py["IMP"] = py["IMP"].astype(str)
py["IMP_CODE"] = py["IMP_CODE"].astype(int)
print(f"Vuelta {VUELTA} | {PAIS} exportador: {len(py):,} filas | reps={REPS} sorteos={SORTEOS}")

sin_out = lambda d: d[(d["EXP_GROWTH"] > -200) & (d["EXP_GROWTH"] < 200)]
specs = {
    "Esp1 crecimiento, con umbral": lambda d: d[d["EXPORTS"] > UMBRAL],
    "Esp2 crecimiento sin outliers, con umbral": lambda d: sin_out(d[d["EXPORTS"] > UMBRAL]),
    "Esp4 crecimiento, sin umbral": lambda d: d,
    "Esp5 crecimiento sin outliers, sin umbral": sin_out,
}
FORM = "EXP_GROWTH ~ IP_T + SUBS_T + IP_OTRA + SUBS_OTRA | " + FE
filas = []

for grupo, lista in GRUPOS.items():
    celdas = tipos.loc[tipos["interventiontype"].isin(lista), KEYS].drop_duplicates().assign(IP_T=1)
    d0 = py.merge(celdas, on=KEYS, how="left")
    d0["IP_T"] = d0["IP_T"].fillna(0)
    d0["IP_OTRA"] = d0["IP"] - d0["IP_T"]
    d0["SUBS_T"] = d0["IP_T"] * d0["SUBS_COVERAGE"]
    d0["SUBS_OTRA"] = d0["IP_OTRA"] * d0["SUBS_COVERAGE"]
    print(f"\n=== {grupo}")
    for nombre, f in specs.items():
        d = f(d0).dropna(subset=["EXP_GROWTH", "ISIC3_2"]).copy()
        fit = pf.feols(FORM, data=d, vcov=CL, fixef_rm="none")
        if "SUBS_T" not in fit._coefnames:
            print(f"[{nombre}] SUBS_T no identificado (ninguna fila de este tipo con cobertura > 0)")
            continue
        b, se, p = fit.coef()["SUBS_T"], fit.se()["SUBS_T"], fit.pvalue()["SUBS_T"]
        lc = lincom(fit, {"IP_T": 1, "SUBS_T": COB_REF})
        r = {"grupo": grupo, "spec": nombre, "N": fit._N, "b_SUBS_T": b, "se_SUBS_T": se,
             "p_SUBS_T": p, "acuerdo": lc["estimate"], "acuerdo_p": lc["p"]}

        # 1. Wild cluster bootstrap
        r["p_boot_SUBS_T"] = float(fit.wildboottest(param="SUBS_T", reps=REPS,
                                                    seed=SEMILLA)["Pr(>|t|)"])
        dm = d.assign(Z=d["SUBS_T"] - COB_REF * d["IP_T"])
        fm = pf.feols(FORM.replace("SUBS_T ", "Z "), data=dm, vcov=CL, fixef_rm="none")
        assert np.isclose(fm.coef()["IP_T"], lc["estimate"])
        r["p_boot_acuerdo"] = float(fm.wildboottest(param="IP_T", reps=REPS,
                                                     seed=SEMILLA)["Pr(>|t|)"])

        # 2. Sorteo del tipo (estratificado por importador)
        rng = np.random.default_rng(SEMILLA)
        otros = sorted(set(d.loc[d["IP_T"] == 1, "IMP"]) - set(SOCIOS_REF))
        r["importadores_T_fuera_acuerdo"] = ",".join(otros)
        idx = {imp: g.index.to_numpy() for imp, g in d[d["IP"] == 1].groupby("IMP")}
        n_t = d.loc[d["IP"] == 1].groupby("IMP")["IP_T"].sum().astype(int).to_dict()
        ts = []
        for _ in range(SORTEOS):
            perm = pd.Series(0.0, index=d.index)
            for imp, ii in idx.items():
                if n_t[imp] > 0:
                    perm.loc[rng.choice(ii, n_t[imp], replace=False)] = 1.0
            dp = d.assign(IP_T=perm, IP_OTRA=d["IP"] - perm)
            dp["SUBS_T"] = dp["IP_T"] * dp["SUBS_COVERAGE"]
            dp["SUBS_OTRA"] = dp["IP_OTRA"] * dp["SUBS_COVERAGE"]
            ff = pf.feols(FORM, data=dp, vcov=CL, fixef_rm="none")
            if "SUBS_T" in ff._coefnames:
                ts.append(ff.tstat()["SUBS_T"])
        ts = np.array(ts)
        ts = ts[np.isfinite(ts)]
        t_real = fit.tstat()["SUBS_T"]
        r["t_real"] = t_real
        r["p_sorteo_tipo"] = (1 + np.sum(np.abs(ts) >= abs(t_real))) / (1 + len(ts))
        r["sorteos_validos"] = len(ts)

        # 3. Sin un socio
        for fuera in socios_tratados_principales(py):
            ff = pf.feols(FORM, data=d[d["IMP"] != fuera], vcov=CL, fixef_rm="none")
            if "SUBS_T" in ff._coefnames:
                lf = lincom(ff, {"IP_T": 1, "SUBS_T": COB_REF})
                r[f"sin{fuera}_SUBS_T"], r[f"sin{fuera}_p"] = ff.coef()["SUBS_T"], ff.pvalue()["SUBS_T"]
                r[f"sin{fuera}_acuerdo"], r[f"sin{fuera}_acuerdo_p"] = lf["estimate"], lf["p"]
        filas.append(r)
        print(f"[{nombre}] N={r['N']:,}  SUBS_T={b:.2f} ({se:.2f}) p={p:.3f}  "
              f"p_boot={r['p_boot_SUBS_T']:.3f}  p_sorteo_tipo={r['p_sorteo_tipo']:.3f} "
              f"({r['sorteos_validos']} sorteos; T fuera del Acuerdo: {r['importadores_T_fuera_acuerdo']})  | "
              f"Acuerdo={lc['estimate']:.2f} p={lc['p']:.3f} p_boot={r['p_boot_acuerdo']:.3f}")
        for fuera in socios_tratados_principales(py):
            if f"sin{fuera}_SUBS_T" in r:
                print(f"     sin {fuera}: SUBS_T={r[f'sin{fuera}_SUBS_T']:.2f} (p={r[f'sin{fuera}_p']:.3f})"
                      f"  Acuerdo={r[f'sin{fuera}_acuerdo']:.2f} (p={r[f'sin{fuera}_acuerdo_p']:.3f})")
            else:
                print(f"     sin {fuera}: SUBS_T no identificado")

TABLES.mkdir(parents=True, exist_ok=True)
pd.DataFrame(filas).to_csv(TABLES / f"{PAIS}_tipo_subsidio_inferencia_v{VUELTA}.csv", index=False)
print(f"\nGuardado {TABLES / f'{PAIS}_tipo_subsidio_inferencia_v{VUELTA}.csv'}")
