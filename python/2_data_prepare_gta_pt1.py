"""
* *********************************************************************
*
*       PART 1:  CLEANING THE CORE GTA DATABASE AND CREATING CSV WITH
*                SECTOR INFORMATION
*       (traducción de 2-DataPrepare_GTA_PT1.do)
*
* *********************************************************************

Entradas: $data_raw/GTA-OCT-23.csv
          $data_aux/Classification-economies-07.dta
Salidas:  $data_temp/GTA_cleaned.dta
          $data_temp/ProductsWide_GTA_IP.csv   (políticas industriales distorsivas)
          $data_temp/ProductsWide_GTA_IMP.csv  (barreras a la importación distorsivas)
"""
import os

import pandas as pd

from config import DATA_AUX, DATA_RAW, DATA_TEMP
from stata_utils import insheet, merge, order, save_dta

# insheet using "$data_raw\GTA-OCT-23.csv", clear
# drop v1   // the index variable
# insheet corta todo texto en 2.045 bytes (límite str2045 de Stata): así se
# pierden productos en affectedproducts (ver stata_utils.insheet). Para la
# versión corregida, definir la variable de entorno TESIS_SIN_TRUNCAR=1.
SIN_TRUNCAR = os.environ.get("TESIS_SIN_TRUNCAR") == "1"
gta = insheet(DATA_RAW / "GTA-OCT-23.csv",
              max_bytes=None if SIN_TRUNCAR else 2045).drop(columns="v1")
print("insheet:", "SIN cortar textos (corregido)" if SIN_TRUNCAR else "corta en 2.045 bytes como Stata")


# *I. Label variables --------------------------------------------------------
LABELS = {
    "stateactid": "ID of announcement made by the government",
    "interventionid": "ID of the intervention",
    "stateacttitle": "Title of government announcement",
    "announcementdate": "Date of announcement made by the government",
    "gtaevaluation": "Direction of intervention",
    "currentlyinforce": "=1 if the intervention is currently in force",
    "inceptiondate": "The date the documented change is enforced",
    "removaldate": "The date the documented change is withdrawn or fully replaced",
    "implementingjurisdiction": "The jurisdiction(s) for which the described change is announced",
    "implementationlevel": "Government level of implementing jurisdiction",
    "eligiblefirms": "Subset of the firms affected by the change",
    "interventiontype": "The content of each intervention",
    "mastchapter": "UN MAST chapter (International Classification of NTMs)",
    "affectedsectors": "CPC of affected sectors (ver. 2.1 3-digit lev.)",
    "affectedproducts": "HS of affected products (ver. 2012 6-digit lev.)",
    "affectedjurisdiction": "Jurisdictions whose commercial interests are affected",
}


# * II. Harmonize missing values ---------------------------------------------
# replace mastchapter="NA" if mastchapter=="Instrument unclear"
# replace interventiontype="NA" if interventiontype=="Instrument unclear"
for v in ("mastchapter", "interventiontype"):
    gta.loc[gta[v] == "Instrument unclear", v] = "NA"


# *III. Encode ---------------------------------------------------------------
# label define yesno 0 "No" 1 "Yes"
# encode currentlyinforce, gen(temp) label(yesno) noextend
YESNO = {"No": 0, "Yes": 1}
fuera = set(gta["currentlyinforce"]) - set(YESNO) - {""}
if fuera:   # noextend: Stata da error con valores no definidos
    raise ValueError(f"encode noextend: currentlyinforce tiene valores {fuera}")
gta["currentlyinforce"] = gta["currentlyinforce"].map(YESNO)   # "" -> NaN

# Nombres de jurisdicciones de la GTA -> nombres del Banco Mundial.
# Se aplican EN ORDEN, como la secuencia de `replace` del original.
RENOMBRES = [
    ("Macedonia", "North Macedonia"),
    ("Faeroe Islands", "Faroe Islands"),
    ("British Virgin Islands", "Virgin Islands, British"),
    ("Micronesia", "Micronesia, Federated States of"),
    ("Saint-Barthélemy", "Saint Barthélemy"),
    ("Saint-Martin", "Saint Martin (French part)"),
    ("Svalbard and Jan Mayen Islands", "Svalbard and Jan Mayen"),
    ("Vatican", "Holy See (Vatican City State)"),
    ("Wallis and Futuna Islands", "Wallis and Futuna"),
    ("Saint Helena", "Saint Helena, Ascension and Tristan da Cunha"),
    ("Bahamas", "Bahamas, The"),
    ("Cape Verde", "Cabo Verde"),
    ("Chinese Taipei", "Taiwan, China"),
    ("Congo", "Congo, Rep."),
    ("DR Congo", "Congo, Dem. Rep."),
    ("Egypt", "Egypt, Arab Rep."),
    ("Gambia", "Gambia, The"),
    ("Hong Kong", "Hong Kong SAR, China"),
    ("Iran", "Iran, Islamic Rep."),
    ("Ivory Coast", "Cote d'Ivoire"),
    ("Kyrgyzstan", "Kyrgyz Republic"),
    ("Lao", "Lao PDR"),
    # OJO: en el CSV de la GTA las jurisdicciones vacías vienen como "NA";
    # esta línea las convierte en Micronesia (posible error del original,
    # se replica para obtener los mismos datos).
    ("NA", "Micronesia, Fed. Sts."),
    ("Republic of Korea", "Korea, Rep."),
    ("Republic of Moldova", "Moldova"),
    ("Republic of the Sudan", "Sudan"),
    ("Russia", "Russian Federation"),
    ("Saint Kitts and Nevis", "St. Kitts and Nevis"),
    ("Saint Lucia", "St. Lucia"),
    ("Saint Vincent and the Grenadines", "St. Vincent and the Grenadines"),
    ("Sao Tome and Principe", "São Tomé and Príncipe"),
    ("Slovakia", "Slovak Republic"),
    ("State of Palestine", "West Bank and Gaza"),
    ("Swaziland", "Eswatini"),
    ("Syria", "Syrian Arab Republic"),
    ("Turkey", "Türkiye"),
    ("US Virgin Islands", "Virgin Islands (U.S.)"),
    ("United States of America", "United States"),
    ("Venezuela", "Venezuela, RB"),
    ("Yemen", "Yemen, Rep."),
]
# (se omiten los replace que no cambian nada: "Anguilla"->"Anguilla", etc.)

# foreach var in implementingjurisdiction affectedjurisdiction { ... }
for v in ("implementingjurisdiction", "affectedjurisdiction"):
    # replace `var'=subinstr(`var', "&", "and",.)
    gta[v] = gta[v].str.replace("&", "and", regex=False)
    for viejo, nuevo in RENOMBRES:
        gta.loc[gta[v] == viejo, v] = nuevo

# rename implementingjurisdiction Economy
# merge m:1 Economy using "$data_aux/Classification-economies-07.dta"
# drop if _merge!=3   // Anguilla, Falklands & Montserrat
clas07 = pd.read_stata(DATA_AUX / "Classification-economies-07.dta", convert_categoricals=False)
gta = gta.rename(columns={"implementingjurisdiction": "Economy"})
gta = merge(gta, clas07, on="Economy", how="m:1", keep=(3,), gen=None)
# rename (Economy Code Incomegroup) (implementingjurisdiction ISO_impl incgroup_impl)
gta = gta.rename(columns={"Economy": "implementingjurisdiction", "Code": "ISO_impl",
                          "Incomegroup": "incgroup_impl"})

# rename affectedjurisdiction Economy
# merge m:1 Economy using "$data_aux\Classification-economies-07.dta"
# drop if _merge!=3 & Economy!="NA"
# (otras columnas de la clasificación ya están en la base: Stata conserva las
#  del master, es decir, las del país que implementa)
gta = gta.rename(columns={"affectedjurisdiction": "Economy"})
gta = merge(gta, clas07, on="Economy", how="m:1")
gta = gta[(gta["_merge"] == 3) | (gta["Economy"] == "NA")].drop(columns="_merge")
gta = gta.rename(columns={"Economy": "affectedjurisdiction", "Code": "ISO_aff",
                          "Incomegroup": "incgroup_aff"})


# * IV. Duplicates drop -------------------------------------------------------
gta = gta.drop_duplicates()


# * V. Create new ID variable -------------------------------------------------
# sort interventionid implementingjurisdiction affectedjurisdiction
# egen ID=group(interventionid implementingjurisdiction affectedjurisdiction)
# (1, 2, 3... en ese orden; las filas con algún valor vacío quedan sin ID)
claves = ["interventionid", "implementingjurisdiction", "affectedjurisdiction"]
gta = gta.sort_values(claves, kind="stable", na_position="last").reset_index(drop=True)
falta = gta[claves].isna().any(axis=1) | (gta[claves[1:]] == "").any(axis=1)
gta["ID"] = gta[~falta].groupby(claves, sort=True).ngroup() + 1
if gta["ID"].notna().all():
    gta["ID"] = gta["ID"].astype("int32")


# * VI. Create additional variables ------------------------------------------
# gen inception_year=substr(inceptiondate,1,4)
# destring inception_year, force replace   (force: lo no numérico -> missing)
# keep if inrange(inception_year, 2009, 2022)
gta["inception_year"] = pd.to_numeric(gta["inceptiondate"].astype(str).str[:4], errors="coerce")
gta = gta[gta["inception_year"].between(2009, 2022)].copy()

# gen class_measure="" + replace ... if inlist(interventiontype, ...)
CLASES = {
    # Measures of commercial policy (Import barriers)
    "Imp_barriers": [
        "Anti-dumping", "Anti-subsidy", "Import ban", "Import licensing requirement",
        "Import monitoring", "Import quota", "Import tariff",
        "Import tariff quota", "Internal taxation of imports",
        "Import-related non-tariff measure, nes",
        "Local content incentive", "Local content requirement", "Local operations incentive",
        "Local operations requirement", "Local value added incentive",
        "Public procurement localisation", "Localisation, nes"],
    # Measures of commercial policy (Export barriers)
    "Exp_barriers": [
        "Export ban", "Export licensing requirement", "Export quota", "Export tariff quota",
        "Export tax", "Local supply requirement for exports",
        "Export-related non-tariff measure, nes"],
    # Measures of industrial policy (Subsidies + Export incentives)
    "Ind_policy": [
        "Capital injection and equity stakes (including bailouts)", "Financial grant",
        "In-kind grant", "Tax or social insurance relief", "Production subsidy",
        "Interest payment subsidy", "Loan guarantee", "Import incentive", "Price stabilisation",
        "State loan", "State aid, nes", "State aid, unspecified",
        "Trade finance", "Export subsidy", "Tax-based export incentive",
        "Financial assistance in foreign market", "Other export incentive"],
}
gta["class_measure"] = ""
for clase, tipos in CLASES.items():
    gta.loc[gta["interventiontype"].isin(tipos), "class_measure"] = clase


# * VII. Subset ---------------------------------------------------------------
# drop if gtaevaluation=="Amber" / drop if class_measure==""
gta = gta[(gta["gtaevaluation"] != "Amber") & (gta["class_measure"] != "")]

# label drop _all   (currentlyinforce queda como 0/1 sin etiquetas)
# label define greenred 1 "Green" 2 "Red"
# encode gtaevaluation, label(greenred) noextend gen(greenred)
GREENRED = {"Green": 1, "Red": 2}
fuera = set(gta["gtaevaluation"]) - set(GREENRED) - {""}
if fuera:
    raise ValueError(f"encode noextend: gtaevaluation tiene valores {fuera}")
gta["gtaevaluation"] = gta["gtaevaluation"].map(GREENRED)

# sort class_measure gtaevaluation
gta = gta.sort_values(["class_measure", "gtaevaluation"], kind="stable").reset_index(drop=True)

# gen code_class=. + replace code_class=1..6 if class_measure==... & gtaevaluation==...
#   1 Exp_barriers verde   2 Exp_barriers roja
#   3 Imp_barriers verde   4 Imp_barriers roja   <- usadas como IMP_BARR
#   5 Ind_policy verde     6 Ind_policy roja     <- usadas como IP
base = {"Exp_barriers": 0, "Imp_barriers": 2, "Ind_policy": 4}
gta["code_class"] = gta["class_measure"].map(base) + gta["gtaevaluation"]

# order ID interventionid ISO_impl ISO_aff gtaevaluation ... *_impl affectedjurisdiction *_aff
gta = order(gta, [
    "ID", "interventionid", "ISO_impl", "ISO_aff", "gtaevaluation", "inceptiondate",
    "mastchapter", "interventiontype", "announcementdate", "currentlyinforce", "removaldate",
    "stateacttitle", "eligiblefirms", "affectedproducts", "affectedsectors",
    "implementationlevel", "stateactid", "implementingjurisdiction", "*_impl",
    "affectedjurisdiction", "*_aff"])

# compress / save "$data_temp/GTA_cleaned.dta", replace
save_dta(gta, DATA_TEMP / "GTA_cleaned.dta",
         value_labels={"gtaevaluation": {1: "Green", 2: "Red"}},
         variable_labels={k: v for k, v in LABELS.items() if k in gta.columns})
print(f"GTA_cleaned: {len(gta):,} filas")


# *VII. Export IP and IMP measures --------------------------------------------
# keep if code_class==6 (IP distorsiva) / ==4 (medidas de importación distorsivas)
# keep ID interventionid affectedproducts
# export delimited using "$data_temp\ProductsWide_GTA_xx.csv", replace
# (estos CSV son la entrada de 3-Split Sectors-Products)
for code, archivo in [(6, "ProductsWide_GTA_IP.csv"), (4, "ProductsWide_GTA_IMP.csv")]:
    sub = gta.loc[gta["code_class"] == code, ["ID", "interventionid", "affectedproducts"]]
    sub.to_csv(DATA_TEMP / archivo, index=False)
    print(f"{archivo}: {len(sub):,} filas")
