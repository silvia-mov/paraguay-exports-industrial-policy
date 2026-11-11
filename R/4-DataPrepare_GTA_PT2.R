# *********************************************************************
#
#       PART 2:  MERGING THE GTA WITH SECTORS IN LONG FORMAT,
#                TRADE FLOWS AND PTA DATA
#       (traducción de 4-DataPrepare_GTA_PT2.do)
#
# *********************************************************************
#
# Entradas: $data_temp/GTA_cleaned.dta                 (de 2-DataPrepare_GTA_PT1)
#           $data_temp/ProductsLong_GTA_IP.dta / _IMP.dta (de 3-Split Sectors)
#           $data_temp/DTA_subsidies.dta               (de 1-DataPrepare_PTA)
#           $data_raw/BACI_HS12_Y2012..2022_V202401.csv
#           $data_aux/BACI_ISO_Codes.dta, HS2012_ISIC3.dta,
#                     Classification-economies-21.dta
# Salidas:  $data_temp/GTA_cleaned_IP.dta, GTA_cleaned_IMP.dta,
#           BACI_measures.dta, DataforRegressions.dta

if (!exists("rutas")) source(here::here("R", "config.R"))
source(here::here("R", "stata_utils.R"))

library(dplyr)
library(haven)
library(data.table)   # solo fread(), para leer BACI rápido

years <- 2012:2022

# drop if EXPORTS<500. En BACI `v` está en MILES de USD -> 500 = USD 500 mil
# (la nota 3 del paper habla de USD 1 millón; aquí se replica el código).
min_exports <- 500

# EXP_GROWTH en el original compara con la OBSERVACIÓN anterior del flujo,
# no necesariamente con el año t-1 (si falta un año, compara con t-2...).
# FALSE replica el original; TRUE exige que la anterior sea exactamente t-1.
strict_t_minus_1 <- FALSE

hs_label <- "HS of affected products (ver. 2012 6-digit lev.)"


# *IX. Merge with measure in long format ---------------------------------------
gta_long <- function(clase, products_file, flag) {
  # use "$data_temp/GTA_cleaned.dta", clear
  # keep ID ISO_impl affectedproducts inception_year code_class interventionid
  # (zap_labels: se trabaja con los códigos numéricos, como en Stata)
  gta <- read_dta(file.path(rutas$data_temp, "GTA_cleaned.dta"),
                  col_select = c(ID, ISO_impl, affectedproducts, inception_year,
                                 code_class, interventionid)) %>%
    zap_labels() %>%
    # keep if code_class==6 (IP distorsiva) / ==4 (medidas de importación)
    filter(code_class == clase)

  # merge 1:m ID using "$data_temp/ProductsLong_GTA_xx.dta"
  products <- zap_labels(read_dta(file.path(rutas$data_temp, products_file)))
  df <- stata_merge(gta, products, by = "ID", how = "1:m")

  df <- df %>%
    # rename Product HS2012
    rename(HS2012 = Product) %>%
    # drop if _merge==1   // Measures that do not have a specific sector
    # drop _merge
    # (las filas _merge==2 se conservan, como en el original)
    filter(`_merge` != 1) %>%
    select(-`_merge`) %>%
    # destring HS2012, replace
    mutate(HS2012 = destring(HS2012)) %>%
    # duplicates drop ISO_impl HS2012 inception_year, force
    # Una medida por país-producto-año; queda la primera en el orden actual
    # (ordenado por ID), es decir, la intervención con menor ID.
    distinct(ISO_impl, HS2012, inception_year, .keep_all = TRUE) %>%
    # drop ID affectedproducts / rename ISO_impl IMP / rename inception_year year
    select(-ID, -affectedproducts) %>%
    rename(IMP = ISO_impl, year = inception_year) %>%
    # gen IP=1  /  gen IMP_BARR=1
    mutate(!!flag := 1) %>%
    # sort year IMP HS
    arrange(year, IMP, HS2012)

  attr(df$HS2012, "label") <- hs_label   # label var HS2012 "..."
  df
}

gta_ip <- gta_long(6, "ProductsLong_GTA_IP.dta", "IP")
write_dta(gta_ip, file.path(rutas$data_temp, "GTA_cleaned_IP.dta"))

gta_imp <- gta_long(4, "ProductsLong_GTA_IMP.dta", "IMP_BARR")
write_dta(gta_imp, file.path(rutas$data_temp, "GTA_cleaned_IMP.dta"))
message("GTA_cleaned_IP: ", nrow(gta_ip), " filas | GTA_cleaned_IMP: ",
        nrow(gta_imp), " filas")


# -------------------------------------------------------------------------------
# BACI measures
# -------------------------------------------------------------------------------
# *I. Create a combined dataset of all years
#   import delimited ... / forvalues i=2013/2022 { ... append }
# Para ahorrar memoria (BACI tiene >100 millones de filas) se lee solo lo que
# se usa (q se elimina después) y se aplica `drop if EXPORTS<500` año por año.
# Es equivalente al original: los merges con keep(3) y ese drop solo eliminan
# filas, así que el orden en que se aplican no cambia el resultado.
read_baci <- function(year) {
  df <- fread(file.path(rutas$data_raw, sprintf("BACI_HS12_Y%d_V202401.csv", year)),
              select = c("t", "i", "j", "k", "v"))
  # drop if EXPORTS<500   (en Stata missing<500 es falso: los NA se quedan)
  df[is.na(v) | v >= min_exports]
}
baci <- as_tibble(rbindlist(lapply(years, read_baci)))

# merge m:1 i using "$data_aux/BACI_ISO_Codes.dta", keep(3) nogen   // i is exp
# drop IMP
# merge m:1 j using "$data_aux/BACI_ISO_Codes.dta", keep(3) nogen   // j is imp
# El archivo de códigos trae i, j, EXP e IMP (copias del código y del ISO3).
# En el primer merge solo sirve EXP (por eso se borra IMP); en el segundo,
# IMP. Las demás columnas repetidas conservan el valor del master.
iso <- zap_labels(read_dta(file.path(rutas$data_aux, "BACI_ISO_Codes.dta")))
baci <- stata_merge(baci, iso, by = "i", how = "m:1", keep = 3, gen = NULL) %>%
  select(-IMP)
baci <- stata_merge(baci, iso, by = "j", how = "m:1", keep = 3, gen = NULL) %>%
  # rename t year / rename k HS2012 / rename v EXPORTS / drop q
  rename(year = t, HS2012 = k, EXPORTS = v)

# save "$data_temp/BACI_measures.dta", replace
write_dta(baci, file.path(rutas$data_temp, "BACI_measures.dta"))
message("BACI_measures: ", nrow(baci), " filas")


# -------------------------------------------------------------------------------
# Combine BACI, GTA and subsidies dataset
# -------------------------------------------------------------------------------
# use "$data_temp/BACI_measures.dta"   -> seguimos con `baci` en memoria
keys <- c("IMP", "HS2012", "year")

# merge m:1 IMP HS2012 year using "$data_temp/GTA_cleaned_IP.dta"
# drop if _merge==2   // IP measures but no trade flows
# replace IP=0 if IP==.
df <- stata_merge(baci, gta_ip, by = keys, how = "m:1") %>%
  filter(`_merge` != 2) %>%
  select(-`_merge`) %>%
  mutate(IP = coalesce(IP, 0))

# merge m:1 IMP HS2012 year using "$data_temp/GTA_cleaned_IMP.dta", replace update
# drop if _merge==2 / replace IMP_BARR=0 if IMP_BARR==.
# (update/replace solo afectan a interventionid y code_class, que están en
#  ambas bases y se eliminan en el keep siguiente)
df <- stata_merge(df, gta_imp, by = keys, how = "m:1", update = TRUE, replace = TRUE) %>%
  filter(`_merge` != 2) %>%
  select(-`_merge`) %>%
  mutate(IMP_BARR = coalesce(IMP_BARR, 0)) %>%
  # keep year EXP IMP EXPORTS IP HS2012 IMP_BARR
  select(year, EXP, IMP, EXPORTS, IP, HS2012, IMP_BARR) %>%
  # encode EXP, gen(EXP_CODE) / encode IMP, gen(IMP_CODE)
  mutate(EXP_CODE = encode(EXP), IMP_CODE = encode(IMP))

# ***FTA VARIABLES FROM DTA / SUBS COVERAGE
# merge m:1 EXP IMP year using "$data_temp/DTA_subsidies.dta"
# drop if _merge==2 / replace rta=0 if rta==.
dta <- zap_labels(read_dta(file.path(rutas$data_temp, "DTA_subsidies.dta")))
df <- stata_merge(df, dta, by = c("EXP", "IMP", "year"), how = "m:1") %>%
  filter(`_merge` != 2) %>%
  select(-`_merge`) %>%
  mutate(
    rta = coalesce(rta, 0),
    # gen IP_RTA=IP*(rta) / gen IMP_BARR_RTA=IMP_BARR*(rta)
    IP_RTA = IP * rta,
    IMP_BARR_RTA = IMP_BARR * rta,
    # replace SUBS_COVERAGE=0 if SUBS_COVERAGE==. (y REL_SUBS_COVERAGE)
    SUBS_COVERAGE = coalesce(SUBS_COVERAGE, 0),
    REL_SUBS_COVERAGE = coalesce(REL_SUBS_COVERAGE, 0),
    # gen IP_RTA_SUBS=IP*SUBS_COVERAGE / gen IP_RTA_REL_SUBS=IP*REL_SUBS_COVERAGE
    IP_RTA_SUBS = IP * SUBS_COVERAGE,
    IP_RTA_REL_SUBS = IP * REL_SUBS_COVERAGE
  )

# -------------------------------------------------------------------------------
# ***DEPENDENT VARIABLES
# sort EXP IMP HS2012 year
# gen ln_exp=ln(EXPORTS)
# bysort EXP IMP HS2012: gen EXP_GROWTH=100*(ln(EXPORTS)-ln(EXPORTS[_n-1]))
# [_n-1] dentro del grupo = fila anterior si pertenece al mismo flujo.
# (Versión vectorizada con lag(): mucho más rápida que group_by() en 10M+ filas)
df <- df %>%
  arrange(EXP, IMP, HS2012, year) %>%
  mutate(
    ln_exp = ln_stata(EXPORTS),
    same_flow = EXP == lag(EXP) & IMP == lag(IMP) & HS2012 == lag(HS2012) &
      (!strict_t_minus_1 | year - lag(year) == 1),
    EXP_GROWTH = if_else(coalesce(same_flow, FALSE), 100 * (ln_exp - lag(ln_exp)), NA_real_)
  ) %>%
  select(-same_flow)

# -------------------------------------------------------------------------------
# ***ADDITIONAL VARIABLES
# *** ISIC REV3
# merge m:1 HS2012 using "$data_aux/HS2012_ISIC3.dta" / drop if _merge==2
isic <- zap_labels(read_dta(file.path(rutas$data_aux, "HS2012_ISIC3.dta")))
df <- stata_merge(df, isic, by = "HS2012", how = "m:1") %>%
  filter(`_merge` != 2) %>%
  select(-`_merge`)

# *** REGIONS & INCOME
# rename EXP Economy
# merge m:1 Economy using "$data_aux/Classification-economies-21.dta"
# rename Economy EXP
# OJO: aquí el original NO elimina _merge ni las filas _merge==2, así que
# DataforRegressions incluye economías de la clasificación sin comercio
# (con EXP_GROWTH vacío; las regresiones las descartan solas).
clas <- read_dta(file.path(rutas$data_aux, "Classification-economies-21.dta"))
df <- df %>%
  rename(Economy = EXP) %>%
  stata_merge(clas, by = "Economy", how = "m:1") %>%
  rename(EXP = Economy) %>%
  mutate(`_merge` = haven::labelled(`_merge`, labels = merge_labels))

# -------------------------------------------------------------------------------
# *** SAVE
# save "$data_temp/DataforRegressions", replace
write_dta(df, file.path(rutas$data_temp, "DataforRegressions.dta"))
message("DataforRegressions: ", nrow(df), " filas, ", ncol(df), " columnas")
