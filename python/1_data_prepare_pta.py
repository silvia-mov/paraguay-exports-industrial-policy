"""
* *********************************************************************
*
*       PART 1:  CLEANING THE CORE SUBSIDIES DATABASE
*       (traducción de 1-DataPrepare_PTA.do)
*
* *********************************************************************

Entrada:  $data_raw/DTA 2.0 - Vertical Content (v2).xlsx
          hojas "STATA" y "Bilateral Information"
Salida:   $data_temp/DTA_subsidies.dta
          (pares EXP-IMP-año 2012-2022 con un acuerdo comercial vigente y la
          cobertura de sus cláusulas sobre subsidios)
"""
import pandas as pd

from config import DATA_RAW, DATA_TEMP, VUELTA

DTA_FILE = DATA_RAW / "DTA 2.0 - Vertical Content (v2).xlsx"

# ----------------------------------------------------------------------
# 1. Índice de cobertura de subsidios por acuerdo (WBID)
# ----------------------------------------------------------------------

# import excel ..., sheet("STATA") firstrow allstring clear
# dtype=str equivale a allstring: todas las columnas se leen como texto
prov = pd.read_excel(DTA_FILE, sheet_name="STATA", dtype=str)

# keep if Area=="Subsidies"
prov = prov[prov["Area"] == "Subsidies"]

# gen question=real(substr(Coding, -2, .))
# Últimos 2 caracteres de Coding pasados a número; si no es número -> NaN
# (real() de Stata también devuelve missing en ese caso)
prov["question"] = pd.to_numeric(prov["Coding"].str[-2:].str.strip(), errors="coerce")

# tab question
print(prov["question"].value_counts(dropna=False).sort_index())

# keep if question>=13 & question<=25
# (NaN no cumple la condición, igual que en Stata)
prov = prov[prov["question"].between(13, 25)]

# reshape long agree_, i(Area Coding Provision) j(WBID)
# Las columnas agree_1, agree_2, ... pasan a filas; el sufijo es el WBID.
agree_cols = prov.columns[prov.columns.str.fullmatch(r"agree_\d+")]
long = prov.melt(
    id_vars=["Area", "Coding", "Provision", "question"],
    value_vars=agree_cols,
    var_name="WBID",
    value_name="agree_",
)
long["WBID"] = long["WBID"].str.removeprefix("agree_").astype(int)

# gen VALUE=real(agree_)
long["VALUE"] = pd.to_numeric(long["agree_"].str.strip(), errors="coerce")

# keep WBID question VALUE
# reshape wide VALUE, i(WBID) j(question)
# pivot (y no pivot_table) para que falle si (WBID, question) se repite,
# igual que reshape wide en Stata.
long["question"] = long["question"].astype(int)
subs = long.pivot(index="WBID", columns="question", values="VALUE")
subs.columns = [f"VALUE{q}" for q in subs.columns]

# drop VALUE16
subs = subs.drop(columns="VALUE16")

# egen SUBS_COVERAGE=rowtotal(VALUE*)
# rowtotal trata los missing como 0 (fila sin datos -> 0): sum(min_count=0)
value_cols = [c for c in subs.columns if c.startswith("VALUE")]
subs["SUBS_COVERAGE"] = subs[value_cols].sum(axis=1, min_count=0)

# replace SUBS_COVERAGE = SUBS_COVERAGE/12
# (12 = preguntas 13 a 25 sin la 16)
subs["SUBS_COVERAGE"] = subs["SUBS_COVERAGE"] / 12

# egen max_SUBS_COVERAGE=max(SUBS_COVERAGE)
# gen REL_SUBS_COVERAGE=SUBS_COVERAGE/max_SUBS_COVERAGE
subs["REL_SUBS_COVERAGE"] = subs["SUBS_COVERAGE"] / subs["SUBS_COVERAGE"].max()

# keep WBID SUBS_COVERAGE REL_SUBS_COVERAGE
# tempfile subsidies / save `subsidies'  -> basta con dejarlo en memoria
subs = subs.reset_index()[["WBID", "SUBS_COVERAGE", "REL_SUBS_COVERAGE"]]

# ----------------------------------------------------------------------
# 2. Panel bilateral de acuerdos (exportador-importador-año)
# ----------------------------------------------------------------------

# import excel ..., sheet("Bilateral Information") firstrow clear
bil = pd.read_excel(DTA_FILE, sheet_name="Bilateral Information")

# rename (iso1 iso2) (EXP IMP)
bil = bil.rename(columns={"iso1": "EXP", "iso2": "IMP"})

# keep if inrange(year, 2003, 2023)
# (inrange con year missing devuelve 0 -> también se eliminan los NaN)
bil = bil[bil["year"].between(2003, 2023)]

# merge m:1 WBID using `subsidies', keep(3) nogen
# keep(3) = solo los que hacen match -> how="inner"
# validate="m:1" falla si WBID se repite en subs, como en Stata
bil["WBID"] = bil["WBID"].astype(int)
dta = bil.merge(subs, on="WBID", how="inner", validate="m:1")

# keep EXP IMP year SUBS_COVERAGE REL_SUBS_COVERAGE
dta = dta[["EXP", "IMP", "year", "SUBS_COVERAGE", "REL_SUBS_COVERAGE"]].copy()

# gen rta=1
dta["rta"] = 1

# drop if year<=2011
# drop if year==2023
# -> quedan los años 2012-2022
dta = dta[(dta["year"] > 2011) & (dta["year"] != 2023)]

# Vuelta 1 (original):  sort EXP IMP year SUBS_COVERAGE
# Vuelta 2:             gsort EXP IMP year -SUBS_COVERAGE
# duplicates drop EXP IMP year, force
# Si un par de países tiene varios acuerdos el mismo año, se queda con la
# primera fila tras ordenar = el acuerdo con MENOR SUBS_COVERAGE (Vuelta 1)
# o con MAYOR SUBS_COVERAGE (Vuelta 2).
if VUELTA not in (1, 2):
    raise ValueError(f"VUELTA debe ser 1 o 2 (config.py), no {VUELTA!r}")
print(f"Vuelta {VUELTA}: acuerdo de {'MENOR' if VUELTA == 1 else 'MAYOR'} cobertura")
dta = (
    dta.sort_values(["EXP", "IMP", "year", "SUBS_COVERAGE"],
                    ascending=[True, True, True, VUELTA == 1], kind="stable")
    .drop_duplicates(subset=["EXP", "IMP", "year"], keep="first")
)

# drop if year==.
# (redundante: inrange ya eliminó los años missing; se deja por fidelidad)
dta = dta[dta["year"].notna()]
dta["year"] = dta["year"].astype(int)

# save "$data_temp\DTA_subsidies.dta", replace
# Se guarda en .dta para poder comparar con la salida de Stata.
dta = dta.reset_index(drop=True)
dta.to_stata(DATA_TEMP / "DTA_subsidies.dta", write_index=False, version=118)
print(f"DTA_subsidies.dta: {len(dta):,} filas")
