# *********************************************************************
#
#       PART 1:  CLEANING THE CORE GTA DATABASE AND CREATING CSV WITH
#                SECTOR INFORMATION
#       (traducción de 2-DataPrepare_GTA_PT1.do)
#
# *********************************************************************
#
# Entradas: $data_raw/GTA-OCT-23.csv
#           $data_aux/Classification-economies-07.dta
# Salidas:  $data_temp/GTA_cleaned.dta
#           $data_temp/ProductsWide_GTA_IP.csv   (políticas industriales distorsivas)
#           $data_temp/ProductsWide_GTA_IMP.csv  (barreras a la importación distorsivas)
#
# Los caracteres no ASCII (é, ã, ü...) se escriben como \uXXXX para que el
# script funcione igual en cualquier configuración regional (Windows incluido).

if (!exists("rutas")) source(here::here("R", "config.R"))
source(here::here("R", "stata_utils.R"))

library(dplyr)
library(haven)

# insheet using "$data_raw\GTA-OCT-23.csv", clear
# drop v1   // the index variable
gta <- insheet(file.path(rutas$data_raw, "GTA-OCT-23.csv")) %>% select(-v1)


# *I. Label variables --------------------------------------------------------
etiquetas <- c(
  stateactid = "ID of announcement made by the government",
  interventionid = "ID of the intervention",
  stateacttitle = "Title of government announcement",
  announcementdate = "Date of announcement made by the government",
  gtaevaluation = "Direction of intervention",
  currentlyinforce = "=1 if the intervention is currently in force",
  inceptiondate = "The date the documented change is enforced",
  removaldate = "The date the documented change is withdrawn or fully replaced",
  implementingjurisdiction = "The jurisdiction(s) for which the described change is announced",
  implementationlevel = "Government level of implementing jurisdiction",
  eligiblefirms = "Subset of the firms affected by the change",
  interventiontype = "The content of each intervention",
  mastchapter = "UN MAST chapter (International Classification of NTMs)",
  affectedsectors = "CPC of affected sectors (ver. 2.1 3-digit lev.)",
  affectedproducts = "HS of affected products (ver. 2012 6-digit lev.)",
  affectedjurisdiction = "Jurisdictions whose commercial interests are affected"
)


# * II. Harmonize missing values ---------------------------------------------
# replace mastchapter="NA" if mastchapter=="Instrument unclear"
# replace interventiontype="NA" if interventiontype=="Instrument unclear"
gta <- gta %>%
  mutate(across(c(mastchapter, interventiontype),
                ~ if_else(.x == "Instrument unclear", "NA", .x)))


# *III. Encode ---------------------------------------------------------------
# label define yesno 0 "No" 1 "Yes"
# encode currentlyinforce, gen(temp) label(yesno) noextend
yesno <- c(No = 0, Yes = 1)
fuera <- setdiff(unique(gta$currentlyinforce), c(names(yesno), ""))
if (length(fuera) > 0) stop("encode noextend: currentlyinforce tiene valores ", toString(fuera))
gta$currentlyinforce <- unname(yesno[gta$currentlyinforce])   # "" -> NA

# Nombres de jurisdicciones de la GTA -> nombres del Banco Mundial.
# Se aplican EN ORDEN, como la secuencia de `replace` del original.
renombres <- list(
  c("Macedonia", "North Macedonia"),
  c("Faeroe Islands", "Faroe Islands"),
  c("British Virgin Islands", "Virgin Islands, British"),
  c("Micronesia", "Micronesia, Federated States of"),
  c("Saint-Barthélemy", "Saint Barthélemy"),
  c("Saint-Martin", "Saint Martin (French part)"),
  c("Svalbard and Jan Mayen Islands", "Svalbard and Jan Mayen"),
  c("Vatican", "Holy See (Vatican City State)"),
  c("Wallis and Futuna Islands", "Wallis and Futuna"),
  c("Saint Helena", "Saint Helena, Ascension and Tristan da Cunha"),
  c("Bahamas", "Bahamas, The"),
  c("Cape Verde", "Cabo Verde"),
  c("Chinese Taipei", "Taiwan, China"),
  c("Congo", "Congo, Rep."),
  c("DR Congo", "Congo, Dem. Rep."),
  c("Egypt", "Egypt, Arab Rep."),
  c("Gambia", "Gambia, The"),
  c("Hong Kong", "Hong Kong SAR, China"),
  c("Iran", "Iran, Islamic Rep."),
  c("Ivory Coast", "Cote d'Ivoire"),
  c("Kyrgyzstan", "Kyrgyz Republic"),
  c("Lao", "Lao PDR"),
  # OJO: en el CSV de la GTA las jurisdicciones vacías vienen como "NA";
  # esta línea las convierte en Micronesia (posible error del original,
  # se replica para obtener los mismos datos).
  c("NA", "Micronesia, Fed. Sts."),
  c("Republic of Korea", "Korea, Rep."),
  c("Republic of Moldova", "Moldova"),
  c("Republic of the Sudan", "Sudan"),
  c("Russia", "Russian Federation"),
  c("Saint Kitts and Nevis", "St. Kitts and Nevis"),
  c("Saint Lucia", "St. Lucia"),
  c("Saint Vincent and the Grenadines", "St. Vincent and the Grenadines"),
  c("Sao Tome and Principe", "São Tomé and Príncipe"),
  c("Slovakia", "Slovak Republic"),
  c("State of Palestine", "West Bank and Gaza"),
  c("Swaziland", "Eswatini"),
  c("Syria", "Syrian Arab Republic"),
  c("Turkey", "Türkiye"),
  c("US Virgin Islands", "Virgin Islands (U.S.)"),
  c("United States of America", "United States"),
  c("Venezuela", "Venezuela, RB"),
  c("Yemen", "Yemen, Rep.")
)
# (se omiten los replace que no cambian nada: "Anguilla"->"Anguilla", etc.)

# foreach var in implementingjurisdiction affectedjurisdiction { ... }
for (v in c("implementingjurisdiction", "affectedjurisdiction")) {
  x <- gsub("&", "and", gta[[v]], fixed = TRUE)   # subinstr(`var', "&", "and", .)
  for (r in renombres) {
    r <- utf8(r)
    x[x == r[1]] <- r[2]
  }
  gta[[v]] <- x
}

clas07 <- zap_labels(read_dta(file.path(rutas$data_aux, "Classification-economies-07.dta")))

# rename implementingjurisdiction Economy
# merge m:1 Economy using "$data_aux/Classification-economies-07.dta"
# drop if _merge!=3   // Anguilla, Falklands & Montserrat
# rename (Economy Code Incomegroup) (implementingjurisdiction ISO_impl incgroup_impl)
gta <- gta %>%
  rename(Economy = implementingjurisdiction) %>%
  stata_merge(clas07, by = "Economy", how = "m:1", keep = 3, gen = NULL) %>%
  rename(implementingjurisdiction = Economy, ISO_impl = Code, incgroup_impl = Incomegroup)

# rename affectedjurisdiction Economy
# merge m:1 Economy using "$data_aux\Classification-economies-07.dta"
# drop if _merge!=3 & Economy!="NA"
# (otras columnas de la clasificación ya están en la base: Stata conserva las
#  del master, es decir, las del país que implementa)
gta <- gta %>%
  rename(Economy = affectedjurisdiction) %>%
  stata_merge(clas07, by = "Economy", how = "m:1") %>%
  filter(`_merge` == 3 | Economy == "NA") %>%
  select(-`_merge`) %>%
  rename(affectedjurisdiction = Economy, ISO_aff = Code, incgroup_aff = Incomegroup)


# * IV. Duplicates drop -------------------------------------------------------
gta <- distinct(gta)


# * V. Create new ID variable -------------------------------------------------
# sort interventionid implementingjurisdiction affectedjurisdiction
# egen ID=group(interventionid implementingjurisdiction affectedjurisdiction)
# (1, 2, 3... en ese orden; las filas con algún valor vacío quedan sin ID)
gta <- arrange(gta, interventionid, implementingjurisdiction, affectedjurisdiction)
falta <- is.na(gta$interventionid) | is_missing_stata(gta$implementingjurisdiction) |
  is_missing_stata(gta$affectedjurisdiction)
gta$ID <- NA_integer_
gta$ID[!falta] <- vctrs::vec_group_id(
  gta[!falta, c("interventionid", "implementingjurisdiction", "affectedjurisdiction")])
# vec_group_id numera por orden de aparición; como la base ya está ordenada,
# coincide con la numeración de egen group()


# * VI. Create additional variables ------------------------------------------
# gen inception_year=substr(inceptiondate,1,4)
# destring inception_year, force replace   (force: lo no numérico -> missing)
# keep if inrange(inception_year, 2009, 2022)
gta <- gta %>%
  mutate(inception_year = suppressWarnings(as.numeric(substr(inceptiondate, 1, 4)))) %>%
  filter(between(inception_year, 2009, 2022))

# gen class_measure="" + replace ... if inlist(interventiontype, ...)
clases <- list(
  # Measures of commercial policy (Import barriers)
  Imp_barriers = c(
    "Anti-dumping", "Anti-subsidy", "Import ban", "Import licensing requirement",
    "Import monitoring", "Import quota", "Import tariff",
    "Import tariff quota", "Internal taxation of imports",
    "Import-related non-tariff measure, nes",
    "Local content incentive", "Local content requirement", "Local operations incentive",
    "Local operations requirement", "Local value added incentive",
    "Public procurement localisation", "Localisation, nes"),
  # Measures of commercial policy (Export barriers)
  Exp_barriers = c(
    "Export ban", "Export licensing requirement", "Export quota", "Export tariff quota",
    "Export tax", "Local supply requirement for exports",
    "Export-related non-tariff measure, nes"),
  # Measures of industrial policy (Subsidies + Export incentives)
  Ind_policy = c(
    "Capital injection and equity stakes (including bailouts)", "Financial grant",
    "In-kind grant", "Tax or social insurance relief", "Production subsidy",
    "Interest payment subsidy", "Loan guarantee", "Import incentive", "Price stabilisation",
    "State loan", "State aid, nes", "State aid, unspecified",
    "Trade finance", "Export subsidy", "Tax-based export incentive",
    "Financial assistance in foreign market", "Other export incentive")
)
gta$class_measure <- ""
for (clase in names(clases)) gta$class_measure[gta$interventiontype %in% clases[[clase]]] <- clase


# * VII. Subset ---------------------------------------------------------------
# drop if gtaevaluation=="Amber" / drop if class_measure==""
gta <- filter(gta, gtaevaluation != "Amber", class_measure != "")

# label drop _all   (currentlyinforce queda como 0/1 sin etiquetas)
# label define greenred 1 "Green" 2 "Red"
# encode gtaevaluation, label(greenred) noextend gen(greenred)
greenred <- c(Green = 1, Red = 2)
fuera <- setdiff(unique(gta$gtaevaluation), c(names(greenred), ""))
if (length(fuera) > 0) stop("encode noextend: gtaevaluation tiene valores ", toString(fuera))
gta$gtaevaluation <- unname(greenred[gta$gtaevaluation])

# sort class_measure gtaevaluation
# gen code_class=. + replace code_class=1..6 if class_measure==... & gtaevaluation==...
#   1 Exp_barriers verde   2 Exp_barriers roja
#   3 Imp_barriers verde   4 Imp_barriers roja   <- usadas como IMP_BARR
#   5 Ind_policy verde     6 Ind_policy roja     <- usadas como IP
base <- c(Exp_barriers = 0, Imp_barriers = 2, Ind_policy = 4)
gta <- gta %>%
  arrange(class_measure, gtaevaluation) %>%
  mutate(code_class = unname(base[class_measure]) + gtaevaluation)

# order ID interventionid ISO_impl ISO_aff gtaevaluation ... *_impl affectedjurisdiction *_aff
gta <- order_stata(gta, c(
  "ID", "interventionid", "ISO_impl", "ISO_aff", "gtaevaluation", "inceptiondate",
  "mastchapter", "interventiontype", "announcementdate", "currentlyinforce", "removaldate",
  "stateacttitle", "eligiblefirms", "affectedproducts", "affectedsectors",
  "implementationlevel", "stateactid", "implementingjurisdiction", "*_impl",
  "affectedjurisdiction", "*_aff"))

# label var ... / etiqueta de valores de gtaevaluation
for (v in intersect(names(etiquetas), names(gta))) attr(gta[[v]], "label") <- etiquetas[[v]]
gta$gtaevaluation <- labelled(gta$gtaevaluation, labels = greenred,
                              label = etiquetas[["gtaevaluation"]])

# compress / save "$data_temp/GTA_cleaned.dta", replace
write_dta(gta, file.path(rutas$data_temp, "GTA_cleaned.dta"))
message("GTA_cleaned: ", nrow(gta), " filas")


# *VII. Export IP and IMP measures --------------------------------------------
# keep if code_class==6 (IP distorsiva) / ==4 (medidas de importación distorsivas)
# keep ID interventionid affectedproducts
# export delimited using "$data_temp\ProductsWide_GTA_xx.csv", replace
# (estos CSV son la entrada de 3-Split Sectors-Products)
for (caso in list(list(6, "ProductsWide_GTA_IP.csv"), list(4, "ProductsWide_GTA_IMP.csv"))) {
  sub <- gta %>%
    filter(code_class == caso[[1]]) %>%
    select(ID, interventionid, affectedproducts) %>%
    zap_labels()
  write.csv(sub, file.path(rutas$data_temp, caso[[2]]), row.names = FALSE, na = "",
            fileEncoding = "UTF-8")
  message(caso[[2]], ": ", nrow(sub), " filas")
}
