# *********************************************************************
#
#       PART 1:  CLEANING THE CORE SUBSIDIES DATABASE
#       (traducción de 1-DataPrepare_PTA.do)
#
# *********************************************************************
#
# Entrada: $data_raw/DTA 2.0 - Vertical Content (v2).xlsx
#          hojas "STATA" y "Bilateral Information"
# Salida:  $data_temp/DTA_subsidies.dta
#          (pares EXP-IMP-año 2012-2022 con un acuerdo comercial vigente y la
#          cobertura de sus cláusulas sobre subsidios)

if (!exists("rutas")) source(here::here("R", "config.R"))

library(readxl)
library(dplyr)
library(tidyr)
library(stringr)
library(haven)

if (!vuelta %in% c(1, 2)) stop("vuelta debe ser 1 o 2 (config.R)")
message("Vuelta ", vuelta, ": acuerdo de ", if (vuelta == 1) "MENOR" else "MAYOR", " cobertura")

dta_file <- file.path(rutas$data_raw, "DTA 2.0 - Vertical Content (v2).xlsx")

# ----------------------------------------------------------------------
# 1. Índice de cobertura de subsidios por acuerdo (WBID)
# ----------------------------------------------------------------------

# import excel ..., sheet("STATA") firstrow allstring clear
# col_types = "text" equivale a allstring
prov <- read_excel(dta_file, sheet = "STATA", col_types = "text")

prov <- prov %>%
  # keep if Area=="Subsidies"
  filter(Area == "Subsidies") %>%
  # gen question=real(substr(Coding, -2, .))
  # Últimos 2 caracteres de Coding pasados a número; si no es número -> NA
  mutate(question = suppressWarnings(as.numeric(str_sub(Coding, -2, -1))))

# tab question
print(table(prov$question, useNA = "ifany"))

# keep if question>=13 & question<=25
# (filter() descarta los NA, igual que Stata en esta condición)
prov <- prov %>% filter(question >= 13, question <= 25)

# reshape long agree_, i(Area Coding Provision) j(WBID)
# Las columnas agree_1, agree_2, ... pasan a filas; el sufijo es el WBID.
long <- prov %>%
  select(Area, Coding, Provision, question, matches("^agree_\\d+$")) %>%
  pivot_longer(
    cols = matches("^agree_\\d+$"),
    names_to = "WBID",
    names_prefix = "agree_",
    names_transform = list(WBID = as.integer),
    values_to = "agree_"
  ) %>%
  # gen VALUE=real(agree_)
  mutate(VALUE = suppressWarnings(as.numeric(agree_))) %>%
  # keep WBID question VALUE
  select(WBID, question, VALUE)

# reshape wide VALUE, i(WBID) j(question)
# Stata da error si (WBID, question) se repite; aquí lo verificamos a mano
# porque pivot_wider solo daría un warning.
stopifnot(!anyDuplicated(long[c("WBID", "question")]))
subs <- long %>%
  arrange(question) %>%
  pivot_wider(names_from = question, values_from = VALUE,
              names_prefix = "VALUE") %>%
  # drop VALUE16
  select(-VALUE16) %>%
  # egen SUBS_COVERAGE=rowtotal(VALUE*)
  # rowtotal trata los missing como 0 -> rowSums(na.rm = TRUE)
  # replace SUBS_COVERAGE = SUBS_COVERAGE/12   (12 = preguntas 13-25 sin la 16)
  mutate(SUBS_COVERAGE = rowSums(across(starts_with("VALUE")), na.rm = TRUE) / 12) %>%
  # egen max_SUBS_COVERAGE=max(SUBS_COVERAGE)
  # gen REL_SUBS_COVERAGE=SUBS_COVERAGE/max_SUBS_COVERAGE
  mutate(REL_SUBS_COVERAGE = SUBS_COVERAGE / max(SUBS_COVERAGE, na.rm = TRUE)) %>%
  # keep WBID SUBS_COVERAGE REL_SUBS_COVERAGE
  # tempfile subsidies / save `subsidies'  -> basta con dejarlo en memoria
  select(WBID, SUBS_COVERAGE, REL_SUBS_COVERAGE)

# ----------------------------------------------------------------------
# 2. Panel bilateral de acuerdos (exportador-importador-año)
# ----------------------------------------------------------------------

# import excel ..., sheet("Bilateral Information") firstrow clear
bil <- read_excel(dta_file, sheet = "Bilateral Information")

dta_subsidies <- bil %>%
  # rename (iso1 iso2) (EXP IMP)
  rename(EXP = iso1, IMP = iso2) %>%
  # keep if inrange(year, 2003, 2023)   (los NA también se eliminan)
  filter(between(year, 2003, 2023)) %>%
  mutate(WBID = as.integer(WBID)) %>%
  # merge m:1 WBID using `subsidies', keep(3) nogen
  # keep(3) = solo los que hacen match -> inner_join
  # relationship = "many-to-one" falla si WBID se repite en subs, como en Stata
  inner_join(subs, by = "WBID", relationship = "many-to-one") %>%
  # keep EXP IMP year SUBS_COVERAGE REL_SUBS_COVERAGE
  select(EXP, IMP, year, SUBS_COVERAGE, REL_SUBS_COVERAGE) %>%
  # gen rta=1
  mutate(rta = 1) %>%
  # drop if year<=2011 / drop if year==2023  -> quedan 2012-2022
  filter(year > 2011, year != 2023) %>%
  # Vuelta 1 (original):  sort EXP IMP year SUBS_COVERAGE
  # Vuelta 2:             gsort EXP IMP year -SUBS_COVERAGE
  # duplicates drop EXP IMP year, force
  # Si un par de países tiene varios acuerdos el mismo año, se queda con la
  # primera fila tras ordenar = el acuerdo con MENOR SUBS_COVERAGE (Vuelta 1)
  # o con MAYOR SUBS_COVERAGE (Vuelta 2).
  # (arrange ordena texto en locale "C", igual que Stata)
  arrange(EXP, IMP, year, if (vuelta == 1) SUBS_COVERAGE else desc(SUBS_COVERAGE)) %>%
  distinct(EXP, IMP, year, .keep_all = TRUE) %>%
  # drop if year==.   (redundante: between() ya eliminó los NA)
  filter(!is.na(year))

# save "$data_temp\DTA_subsidies.dta", replace
# Se guarda en .dta para poder comparar con la salida de Stata.
write_dta(dta_subsidies, file.path(rutas$data_temp, "DTA_subsidies.dta"))
message("DTA_subsidies.dta: ", nrow(dta_subsidies), " filas")
