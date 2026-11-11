"""
* *********************************************************************
*
*       PART 2:  MERGING THE GTA WITH SECTORS IN LONG FORMAT,
*                TRADE FLOWS AND PTA DATA
*       (traducción de 4-DataPrepare_GTA_PT2.do)
*
* *********************************************************************

Entradas: $data_temp/GTA_cleaned.dta                (de 2-DataPrepare_GTA_PT1)
          $data_temp/ProductsLong_GTA_IP.dta / _IMP.dta (de 3-Split Sectors)
          $data_temp/DTA_subsidies.dta              (de 1-DataPrepare_PTA)
          $data_raw/BACI_HS12_Y2012..2022_V202401.csv
          $data_aux/BACI_ISO_Codes.dta, HS2012_ISIC3.dta,
                    Classification-economies-21.dta
Salidas:  $data_temp/GTA_cleaned_IP.dta, GTA_cleaned_IMP.dta,
          BACI_measures.dta, DataforRegressions.dta
"""
import os

import numpy as np
import pandas as pd

from config import DATA_AUX, DATA_RAW, DATA_TEMP
from stata_utils import (MERGE_LABELS, destring, encode, ln, merge, save_dta,
                         save_dta_grande, value_labels_of)

YEARS = range(2012, 2023)

# drop if EXPORTS<500. En BACI `v` está en MILES de USD -> 500 = USD 500 mil
# (la nota 3 del paper habla de USD 1 millón; aquí se replica el código).
MIN_EXPORTS = 500

# EXP_GROWTH en el original compara con la OBSERVACIÓN anterior del flujo,
# no necesariamente con el año t-1 (si falta un año, compara con t-2...).
# False replica el original; True exige que la anterior sea exactamente t-1.
STRICT_T_MINUS_1 = False
# Sin editar el código: variable de entorno TESIS_T_MENOS_1=1
if os.environ.get("TESIS_T_MENOS_1") == "1":
    STRICT_T_MINUS_1 = True
# Corridas de robustez: TESIS_SOLO_PARQUET=1 no escribe el .dta grande (3 GB)
SOLO_PARQUET = os.environ.get("TESIS_SOLO_PARQUET") == "1"

HS_LABEL = {"HS2012": "HS of affected products (ver. 2012 6-digit lev.)"}


# *IX. Merge with measure in long format ---------------------------------------
def gta_long(code_class: int, products_file: str, flag: str) -> pd.DataFrame:
    # use "$data_temp/GTA_cleaned.dta", clear
    # keep ID ISO_impl affectedproducts inception_year code_class interventionid
    # (convert_categoricals=False: se leen los códigos numéricos, no las
    #  etiquetas, para poder comparar code_class==6 como en Stata)
    gta = pd.read_stata(
        DATA_TEMP / "GTA_cleaned.dta",
        columns=["ID", "ISO_impl", "affectedproducts", "inception_year",
                 "code_class", "interventionid"],
        convert_categoricals=False,
    )
    # keep if code_class==6 (IP distorsiva) / ==4 (medidas de importación)
    gta = gta[gta["code_class"] == code_class]
    # affectedproducts se borra más abajo sin usarse; se quita ya para no
    # copiar el texto largo en cada fila del merge (sin cortar a 2045 bytes
    # no entra en memoria). No cambia el resultado.
    gta = gta.drop(columns="affectedproducts")

    # merge 1:m ID using "$data_temp/ProductsLong_GTA_xx.dta"
    products = pd.read_stata(DATA_TEMP / products_file, convert_categoricals=False)
    df = merge(gta, products, on="ID", how="1:m")

    # rename Product HS2012
    df = df.rename(columns={"Product": "HS2012"})
    # drop if _merge==1   // Measures that do not have a specific sector
    # drop _merge
    # (las filas _merge==2 -productos cuyo ID no está en el master- se
    #  conservan, como en el original; tienen IMP y año vacíos)
    df = df[df["_merge"] != 1].drop(columns="_merge")
    # destring HS2012, replace
    df["HS2012"] = destring(df["HS2012"])
    # duplicates drop ISO_impl HS2012 inception_year, force
    # Una medida por país-producto-año. Queda la primera en el orden actual
    # (ordenado por ID), es decir, la intervención con menor ID.
    df = df.drop_duplicates(["ISO_impl", "HS2012", "inception_year"], keep="first")
    # drop ID affectedproducts
    # rename ISO_impl IMP / rename inception_year year
    df = df.drop(columns=["ID"]).rename(
        columns={"ISO_impl": "IMP", "inception_year": "year"})
    # gen IP=1  /  gen IMP_BARR=1
    df[flag] = 1
    # sort year IMP HS
    return df.sort_values(["year", "IMP", "HS2012"], kind="stable").reset_index(drop=True)


gta_ip = gta_long(6, "ProductsLong_GTA_IP.dta", "IP")
save_dta(gta_ip, DATA_TEMP / "GTA_cleaned_IP.dta", variable_labels=HS_LABEL)

gta_imp = gta_long(4, "ProductsLong_GTA_IMP.dta", "IMP_BARR")
save_dta(gta_imp, DATA_TEMP / "GTA_cleaned_IMP.dta", variable_labels=HS_LABEL)
print(f"GTA_cleaned_IP: {len(gta_ip):,} filas | GTA_cleaned_IMP: {len(gta_imp):,} filas")


# -------------------------------------------------------------------------------
# BACI measures
# -------------------------------------------------------------------------------
# *I. Create a combined dataset of all years
#   import delimited ... / forvalues i=2013/2022 { ... append }
# Para ahorrar memoria (BACI tiene >100 millones de filas) se lee solo lo que
# se usa (q se elimina después) y se aplica `drop if EXPORTS<500` año por año.
# Es equivalente al original: los merges con keep(3) y ese drop solo eliminan
# filas, así que el orden en que se aplican no cambia el resultado.
def read_baci(year: int) -> pd.DataFrame:
    df = pd.read_csv(
        DATA_RAW / f"BACI_HS12_Y{year}_V202401.csv",
        usecols=["t", "i", "j", "k", "v"],
        dtype={"t": "int16", "i": "int16", "j": "int16", "k": "int32", "v": "float64"},
    )
    # drop if EXPORTS<500   (en Stata missing<500 es falso: los NaN se quedan)
    return df[~(df["v"] < MIN_EXPORTS)]


baci = pd.concat([read_baci(y) for y in YEARS], ignore_index=True)

# merge m:1 i using "$data_aux/BACI_ISO_Codes.dta", keep(3) nogen   // i is exp
# drop IMP
# merge m:1 j using "$data_aux/BACI_ISO_Codes.dta", keep(3) nogen   // j is imp
# El archivo de códigos trae i, j, EXP e IMP (copias del código y del ISO3).
# En el primer merge solo sirve EXP (por eso se borra IMP); en el segundo,
# IMP. Las demás columnas repetidas conservan el valor del master.
iso = pd.read_stata(DATA_AUX / "BACI_ISO_Codes.dta", convert_categoricals=False)
baci = merge(baci, iso, on="i", how="m:1", keep=(3,), gen=None)
baci = baci.drop(columns="IMP")
baci = merge(baci, iso, on="j", how="m:1", keep=(3,), gen=None)
# Ahorro de memoria (no cambia los datos): los ISO3 como categorías
for c in ("EXP", "IMP"):
    baci[c] = baci[c].astype(pd.CategoricalDtype(sorted(baci[c].dropna().unique())))

# rename t year / rename k HS2012 / rename v EXPORTS / drop q
baci = baci.rename(columns={"t": "year", "k": "HS2012", "v": "EXPORTS"})

# save "$data_temp/BACI_measures.dta", replace
save_dta(baci, DATA_TEMP / "BACI_measures.dta")
print(f"BACI_measures: {len(baci):,} filas")


def merge_izq(master, using, on):
    """`merge m:1 on using ...` seguido de `drop if _merge==2` (y drop _merge).

    Da lo mismo que merge(..., how="m:1") + quitar _merge==2, pero con un
    cruce por la izquierda: el cruce completo (outer) duplica en memoria las
    15 millones de filas. Las variables del using que el original actualiza
    (update replace) y después borra con `keep` no se traen. Orden final
    igual que Stata: por las llaves.
    """
    master, using = _llaves_iguales(master, using, on)
    out = master.merge(using, on=on, how="left", validate="m:1", sort=False)
    return out.sort_values(on, kind="stable").reset_index(drop=True)


def _llaves_iguales(master, using, on):
    """Llaves de texto guardadas como categorías: mismas categorías en ambas."""
    master, using = master.copy(deep=False), using.copy(deep=False)
    for k in on:
        if isinstance(master[k].dtype, pd.CategoricalDtype) or isinstance(using[k].dtype, pd.CategoricalDtype):
            cats = sorted(set(master[k].dropna().unique()) | set(using[k].dropna().unique()))
            tipo = pd.CategoricalDtype(cats)
            master[k], using[k] = master[k].astype(tipo), using[k].astype(tipo)
    return master, using


# -------------------------------------------------------------------------------
# Combine BACI, GTA and subsidies dataset
# -------------------------------------------------------------------------------
# use "$data_temp/BACI_measures.dta"   -> seguimos con `baci` en memoria
keys = ["IMP", "HS2012", "year"]

# merge m:1 IMP HS2012 year using "$data_temp/GTA_cleaned_IP.dta"
# drop if _merge==2   // IP measures but no trade flows
# replace IP=0 if IP==.
df = merge_izq(baci, gta_ip[keys + ["IP"]], keys)
del baci
df["IP"] = df["IP"].fillna(0)

# merge m:1 IMP HS2012 year using "$data_temp/GTA_cleaned_IMP.dta", replace update
# drop if _merge==2 / replace IMP_BARR=0 if IMP_BARR==.
# (update/replace solo afectan a interventionid y code_class, que están en
#  ambas bases y se eliminan en el keep siguiente)
df = merge_izq(df, gta_imp[keys + ["IMP_BARR"]], keys)
df["IMP_BARR"] = df["IMP_BARR"].fillna(0)

# keep year EXP IMP EXPORTS IP HS2012 IMP_BARR
df = df[["year", "EXP", "IMP", "EXPORTS", "IP", "HS2012", "IMP_BARR"]]

# encode EXP, gen(EXP_CODE) / encode IMP, gen(IMP_CODE)
df["EXP_CODE"], exp_labels = encode(df["EXP"])
df["IMP_CODE"], imp_labels = encode(df["IMP"])

# ***FTA VARIABLES FROM DTA / SUBS COVERAGE
# merge m:1 EXP IMP year using "$data_temp/DTA_subsidies.dta"
# drop if _merge==2 / replace rta=0 if rta==.
dta = pd.read_stata(DATA_TEMP / "DTA_subsidies.dta", convert_categoricals=False)
df = merge_izq(df, dta, ["EXP", "IMP", "year"])
df["rta"] = df["rta"].fillna(0)

# gen IP_RTA=IP*(rta) / gen IMP_BARR_RTA=IMP_BARR*(rta)
df["IP_RTA"] = df["IP"] * df["rta"]
df["IMP_BARR_RTA"] = df["IMP_BARR"] * df["rta"]

# replace SUBS_COVERAGE=0 if SUBS_COVERAGE==. (y REL_SUBS_COVERAGE)
# gen IP_RTA_SUBS=IP*SUBS_COVERAGE / gen IP_RTA_REL_SUBS=IP*REL_SUBS_COVERAGE
df["SUBS_COVERAGE"] = df["SUBS_COVERAGE"].fillna(0)
df["REL_SUBS_COVERAGE"] = df["REL_SUBS_COVERAGE"].fillna(0)
df["IP_RTA_SUBS"] = df["IP"] * df["SUBS_COVERAGE"]
df["IP_RTA_REL_SUBS"] = df["IP"] * df["REL_SUBS_COVERAGE"]

# -------------------------------------------------------------------------------
# ***DEPENDENT VARIABLES
# sort EXP IMP HS2012 year
# gen ln_exp=ln(EXPORTS)
# bysort EXP IMP HS2012: gen EXP_GROWTH=100*(ln(EXPORTS)-ln(EXPORTS[_n-1]))
flow = ["EXP", "IMP", "HS2012"]
df = df.sort_values(flow + ["year"], kind="stable").reset_index(drop=True)
df["ln_exp"] = ln(df["EXPORTS"])
# [_n-1] dentro del grupo = fila anterior si pertenece al mismo flujo.
# (Versión vectorizada: mucho más rápida que groupby().shift() en 10M+ filas)
prev = df[flow + ["year", "ln_exp"]].shift(1)
same_flow = (df[flow] == prev[flow]).all(axis=1)
if STRICT_T_MINUS_1:
    same_flow &= df["year"] - prev["year"] == 1
df["EXP_GROWTH"] = (100 * (df["ln_exp"] - prev["ln_exp"])).where(same_flow)
del prev

# -------------------------------------------------------------------------------
# ***ADDITIONAL VARIABLES
# *** ISIC REV3
# merge m:1 HS2012 using "$data_aux/HS2012_ISIC3.dta" / drop if _merge==2
isic = pd.read_stata(DATA_AUX / "HS2012_ISIC3.dta", convert_categoricals=False)
df = merge_izq(df, isic, ["HS2012"])

# *** REGIONS & INCOME
# rename EXP Economy
# merge m:1 Economy using "$data_aux/Classification-economies-21.dta"
# rename Economy EXP
# OJO: aquí el original NO elimina _merge ni las filas _merge==2, así que
# DataforRegressions incluye economías de la clasificación sin comercio
# (con EXP_GROWTH vacío; las regresiones las descartan solas).
clas_file = DATA_AUX / "Classification-economies-21.dta"
clas = pd.read_stata(clas_file, convert_categoricals=False)
clas_labels = value_labels_of(clas_file)   # p. ej. códigos de ingreso
df = df.rename(columns={"EXP": "Economy"})
# (cruce por la izquierda + filas solo de la clasificación, con su _merge)
df, clas_k = _llaves_iguales(df, clas, ["Economy"])
df = df.merge(clas_k, on="Economy", how="left", validate="m:1", indicator="_m")
df["_merge"] = np.where(df.pop("_m") == "both", 3, 1).astype("int8")
solo_using = clas_k[~clas_k["Economy"].isin(df["Economy"].unique())].assign(_merge=np.int8(2))
df = pd.concat([df, solo_using], ignore_index=True)
df = df.sort_values("Economy", kind="stable").reset_index(drop=True)
df = df.rename(columns={"Economy": "EXP"})

# -------------------------------------------------------------------------------
# *** SAVE
# save "$data_temp/DataforRegressions", replace
# Primero una copia .parquet (no existe en el original): mucho más rápida y
# liviana de leer desde Python/R para las regresiones.
try:
    df.to_parquet(DATA_TEMP / "DataforRegressions.parquet", index=False)
except ImportError:
    pass
if not SOLO_PARQUET:
    save_dta_grande(
        df,
        DATA_TEMP / "DataforRegressions.dta",
        value_labels={**clas_labels, "EXP_CODE": exp_labels, "IMP_CODE": imp_labels,
                      "_merge": MERGE_LABELS},
    )
print(f"DataforRegressions: {len(df):,} filas, {df.shape[1]} columnas")
