# *********************************************************************
#
#       FIGURES  (traducción de 6-Figures.do)
#
# *********************************************************************
#
# Entradas: $data_raw/GTA_NIPO.xlsx, $data_raw/Standard Report - Imports.csv
#           $data_aux/Classification-economies-21.dta, GDP-21.dta
#           $data_temp/GTA_cleaned.dta  (de 2-DataPrepare_GTA_PT1)
#           $tables/lincom.csv          (de 5-Regressions, para la Figura 3)
# Salidas:  $figures/BMT_Fig_n.pdf / .png / .jpg  y  BMT_Fig_n_data.csv
#           (el .csv es la "vista de tabla" con los datos de cada gráfico)
#
# graph save (.gph) no tiene equivalente: el .csv permite rehacer el gráfico.
# Colores: paleta categórica validada (apta para daltonismo) + tipos de línea
# distintos por serie, como en el original, para no depender solo del color.

if (!exists("rutas")) source(here::here("R", "config.R"))
source(here::here("R", "stata_utils.R"))

library(dplyr)
library(tidyr)
library(haven)
library(readxl)
library(ggplot2)

# ----------------------------------------------------------------------
# Estilo común
# ----------------------------------------------------------------------
series <- c("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300")
ink <- "#0b0b0b"; ink_2 <- "#52514e"; grid_col <- "#e4e3df"
tema <- theme_minimal(base_size = 11) +
  theme(panel.grid.major = element_line(colour = grid_col, linewidth = 0.4),
        panel.grid.minor = element_blank(),
        axis.line = element_line(colour = ink_2, linewidth = 0.4),
        axis.text = element_text(colour = ink_2),
        axis.title = element_text(colour = ink),
        plot.title = element_text(hjust = 0.5),
        legend.position = "bottom", legend.title = element_blank())
anos_45 <- theme(axis.text.x = element_text(angle = 45, hjust = 1))   # angle(45)

# graph save / graph export .pdf .jpg .png (+ datos en .csv)
guardar <- function(p, nombre, datos, width = 9, height = 5.5) {
  for (ext in c("pdf", "png", "jpg")) {
    ggsave(file.path(rutas$figures, paste0("BMT_Fig_", nombre, ".", ext)), p,
           width = width, height = height, dpi = 200, bg = "white")
  }
  write.csv(datos, file.path(rutas$figures, paste0("BMT_Fig_", nombre, "_data.csv")),
            row.names = FALSE)
  message("Figura ", nombre, " guardada")
}

# Nombres de variable como los crea Stata al importar:
# `import excel, firstrow` quita espacios y signos; `import delimited`
# además los pasa a minúsculas.
stata_names <- function(df, lower = FALSE) {
  n <- gsub("[^A-Za-z0-9_]", "", names(df))
  names(df) <- if (lower) tolower(n) else n
  df
}
# Columna cuyo nombre empieza con `nombre` (Stata puede truncar nombres largos)
col <- function(df, nombre) {
  c <- names(df)[startsWith(names(df), nombre)]
  if (length(c) != 1) stop("No hay una única columna que empiece con '", nombre, "'")
  c
}


# **# FIGURE 1 -------------------------------------------------------------------
# New Ind policies and GDP per capita
figura_1 <- function() {
  # import excel "$data_raw/GTA_NIPO.xlsx", sheet("GTA NIPO - December 2023") firstrow clear
  nipo <- stata_names(read_excel(file.path(rutas$data_raw, "GTA_NIPO.xlsx"),
                                 sheet = "GTA NIPO - December 2023"))
  nipo <- nipo %>%
    rename(assessment = all_of(col(nipo, "Initialassessmentchangerelat")),
           size_usd = all_of(col(nipo, "SizeofsubsidyUSDmillion")),
           EntryID = all_of(col(nipo, "EntryID"))) %>%
    mutate(size_usd = as.numeric(size_usd)) %>%
    # keep if Initialassessmentchangerelat=="Distortive"
    filter(assessment == "Distortive") %>%
    # gsort -SizeofsubsidyUSDmillion   (missing al final)
    # replace SizeofsubsidyUSDmillion = 622.560 in 1
    # (typo confirmado por los autores: 622 millones, no miles de millones)
    arrange(desc(size_usd)) %>%
    mutate(size_usd = replace(size_usd, 1, 622.560),
           # gen year=year(Implementationdate) / keep if year==2023
           year = as.integer(format(as.Date(Implementationdate), "%Y"))) %>%
    filter(year == 2023) %>%
    # replace Jurisdiction="..." if Jurisdiction=="..."  (nombres del Banco Mundial)
    mutate(Jurisdiction = recode(Jurisdiction,
      "United States of America" = "United States", "Egypt" = "Egypt, Arab Rep.",
      "Hong Kong" = "Hong Kong SAR, China", "Russia" = "Russian Federation",
      "Turkey" = utf8("T\u00fcrkiye"), "Republic of Korea" = "Korea, Rep."))

  # merge m:1 Jurisdiction using Classification-economies-21 / drop if _merge==2
  clas <- zap_labels(read_dta(file.path(rutas$data_aux, "Classification-economies-21.dta")))
  nipo <- stata_merge(nipo, clas, by = "Jurisdiction", how = "m:1")
  message("  Jurisdicciones sin clasificación (tab ... if _merge==1): ",
          paste(sort(unique(nipo$Jurisdiction[nipo$`_merge` == 1])), collapse = ", "))

  pais <- nipo %>%
    filter(`_merge` != 2) %>%
    # bysort Jurisdiction: egen IP_measure_country=count(EntryID)
    # bysort Jurisdiction: egen IP_USD_country=sum(SizeofsubsidyUSDmillion)
    group_by(Jurisdiction) %>%
    mutate(IP_measure_country = sum(!is.na(EntryID)),
           IP_USD_country = sum(size_usd, na.rm = TRUE)) %>%
    ungroup() %>%
    mutate(log_IP_measure_country = ln_stata(IP_measure_country),
           log_IP_USD_country = ln_stata(IP_USD_country)) %>%
    # keep Economy log_... income(group) IP_measure_country IP_USD_country
    select(Economy, log_IP_measure_country, log_IP_USD_country, incomegroup,
           IP_measure_country, IP_USD_country) %>%
    # duplicates drop Economy, force
    distinct(Economy, .keep_all = TRUE)

  # merge 1:1 Economy using "$data_aux/GDP-21.dta", keep(3) nogen
  gdp <- zap_labels(read_dta(file.path(rutas$data_aux, "GDP-21.dta")))
  pais <- stata_merge(pais, gdp, by = "Economy", how = "1:1", keep = 3, gen = NULL)

  # twoway (scatter ... if incomegroup=="High income") (scatter ... if !="High income")
  #        (lfit ...) if log_IP_measure_country!=0
  # OJO: el `if` excluye a los países con UNA sola medida (ln(1)=0).
  d <- pais %>%
    filter(log_IP_measure_country != 0, !is.na(ln_gdp_pc)) %>%
    mutate(grupo = if_else(incomegroup %in% "High income", "High Income", "EMDE"),
           grupo = factor(grupo, levels = c("High Income", "EMDE")))
  p <- ggplot(d, aes(ln_gdp_pc, log_IP_measure_country)) +
    geom_smooth(aes(linetype = "Fitted values"), method = "lm", formula = y ~ x,
                se = FALSE, colour = ink, linewidth = 0.7) +            # lfit
    geom_point(aes(colour = grupo), size = 2.5) +
    geom_text(aes(label = Economy), size = 2.5, colour = ink_2,         # mlabel(Economy)
              hjust = -0.2, vjust = -0.4) +
    scale_colour_manual(values = series[1:2]) +
    labs(title = "New Industrial Policies: Measures vs. Development, 2023 (source: NIPO)",
         x = "GDP per Capita in 2021 (in logs)", y = "Number of measures 2023 (in logs)",
         linetype = NULL) +
    tema + theme(legend.position = "top")
  guardar(p, "1", pais, height = 6)
}


# **# FIGURE 2 -------------------------------------------------------------------
# Exports to the US, selected markets
figura_2 <- function() {
  # import delimited "$data_raw/Standard Report - Imports.csv", clear / drop rateprovision
  imp <- stata_names(read.csv(file.path(rutas$data_raw, "Standard Report - Imports.csv"),
                              check.names = FALSE), lower = TRUE)
  imp$rateprovision <- NULL
  valor <- col(imp, "customsvalue")
  imp[[valor]] <- as.numeric(gsub(",", "", imp[[valor]]))   # números con separador de miles

  # year = real("20" + substr(time, 5, 2)); month según las 3 primeras letras
  # date_m = ym(year, month); drop if date_m==.
  imp <- imp %>%
    mutate(year = suppressWarnings(as.integer(paste0("20", substr(time, 5, 6)))),
           month = match(substr(time, 1, 3), month.abb)) %>%
    filter(!is.na(year), !is.na(month)) %>%
    mutate(date_m = as.Date(sprintf("%d-%02d-01", year, month)),
           # replace country="Total" / "USMCA" / "ASEAN" if ...
           country = recode(country, "World Total" = "Total",
                            "USMCA - U.S.-Mexico-Canada Agreement" = "USMCA",
                            "ASEAN - Association of Southeast Asian Nations" = "ASEAN")) %>%
    # rename customsvaluegenus EXP_0
    rename(EXP_0 = all_of(valor)) %>%
    # sort country date_m
    # bysort country: gen EXP_0_A = EXP_0 + EXP_0[_n-1] + ... + EXP_0[_n-11]
    arrange(country, date_m) %>%
    group_by(country) %>%
    mutate(EXP_0_A = Reduce(`+`, lapply(0:11, function(k) lag(EXP_0, k))),
           # by country: gen obs=_n
           obs = row_number(),
           # by country: gen EXP_0_A_index = 100*(EXP_0_A/EXP_0_A[18])  (obs 18 = 2018m6)
           EXP_0_A_index = 100 * EXP_0_A / if (n() >= 18) EXP_0_A[18] else NA_real_) %>%
    ungroup()

  # keep ... / reshape wide EXP_0_A_index, i(date_m) j(country) string / keep if obs>12
  wide <- imp %>%
    filter(obs > 12) %>%
    select(date_m, country, EXP_0_A_index) %>%
    pivot_wider(names_from = country, values_from = EXP_0_A_index,
                names_prefix = "EXP_0_A_index")

  largo <- imp %>% filter(obs > 12, country %in% c("ASEAN", "China", "Mexico", "Total"))
  p <- ggplot(largo, aes(date_m, EXP_0_A_index, colour = country, linetype = country)) +
    # xline(702) xline(722) xline(751) -> 2018m7, 2020m3, 2022m8
    geom_vline(xintercept = as.Date(c("2018-07-01", "2020-03-01", "2022-08-01")),
               colour = ink, linewidth = 0.4) +
    geom_line(linewidth = 0.9) +
    scale_colour_manual(values = series[1:4]) +
    scale_linetype_manual(values = c("solid", "solid", "dashed", "dotdash")) +
    labs(title = "Total Export to US, by Origin (2018m6=100)", x = NULL,
         y = "Index (2018m6=100) of 12-months trailing sum") +
    tema
  guardar(p, "2", mutate(wide, date_m = format(date_m, "%Y-%m")))
}


# **# FIGURE 3 -------------------------------------------------------------------
# Baseline results. No está en el do-file (los autores la armaron a mano con la
# Tabla 3). Se genera aquí con los resultados que guarda 5-Regressions.
figura_3 <- function() {
  lc <- read.csv(file.path(rutas$tables, "lincom.csv")) %>% filter(tabla == 3)
  filas <- data.frame(
    modelo = c("m1", "m2", "m2", "m5"),
    lincom = c("IP", "IP", "IP + IP_RTA", "IP + 0.5*IP_RTA_SUBS"),
    efecto = c("Average effect", "Non-member of PTA", "Member of PTA",
               "Member of deep PTA (PTA Depth = 0.5)"))
  d <- inner_join(filas, lc, by = c("modelo", "lincom")) %>%
    mutate(efecto = factor(efecto, levels = filas$efecto))
  p <- ggplot(d, aes(efecto, estimate)) +
    geom_col(fill = series[1], width = 0.55) +
    geom_errorbar(aes(ymin = ci_low, ymax = ci_high), width = 0.12, colour = ink) +
    geom_hline(yintercept = 0, colour = ink) +
    scale_x_discrete(labels = function(x) gsub(" \\(", "\n(", x)) +
    labs(title = "Effect of a new industrial policy on export growth (%)",
         x = NULL, y = "Coefficient and 95% CI") +
    tema + theme(panel.grid.major.x = element_blank())
  guardar(p, "3", d, width = 8, height = 5)
}


# **# FIGURES 5 y 6 --------------------------------------------------------------
# unique(interventionid), by(por + ISO_impl) gen(number_interventions)
# collapse (sum) number_interventions, by(por)
# `unique ..., by() gen()` deja el número de intervenciones distintas en UNA
# fila por grupo; collapse (sum) luego suma esos conteos sobre los países.
contar_intervenciones <- function(gta, por) {
  gta %>%
    group_by(across(all_of(c(por, "ISO_impl")))) %>%
    summarise(number_interventions = n_distinct(interventionid), .groups = "drop") %>%
    group_by(across(all_of(por))) %>%
    summarise(number_interventions = sum(number_interventions), .groups = "drop")
}

figura_5 <- function(gta) {
  d <- contar_intervenciones(gta, c("gtaevaluation", "inception_year"))
  p <- ggplot(filter(d, gtaevaluation == 2),   # 2 = restrictivas (rojo GTA)
              aes(inception_year, number_interventions)) +
    geom_line(colour = series[1], linetype = "dashed", linewidth = 0.9) +
    scale_x_continuous(breaks = 2009:2022) +
    labs(x = "Year", y = "Number of restrictive measures") +
    tema + anos_45
  guardar(p, "5", d, width = 8, height = 5)
}

figura_6 <- function(gta) {
  d <- contar_intervenciones(gta, c("gtaevaluation", "inception_year", "class_measure"))
  clases <- c(Exp_barriers = "Export barriers", Imp_barriers = "Import barriers",
              Ind_policy = "Industrial policy")
  g <- d %>%
    filter(gtaevaluation == 2, class_measure %in% names(clases)) %>%
    mutate(clase = factor(clases[class_measure], levels = clases))
  p <- ggplot(g, aes(inception_year, number_interventions, colour = clase, linetype = clase)) +
    geom_line(linewidth = 0.9) +
    scale_colour_manual(values = series[1:3]) +
    scale_linetype_manual(values = c("solid", "longdash", "dashed")) +
    scale_x_continuous(breaks = 2009:2022) +
    labs(x = "Year", y = "Number of measures") +
    tema + anos_45
  guardar(p, "6", d, width = 8, height = 5)
}


# **# FIGURE 7 -------------------------------------------------------------------
mast <- c(D = "Contingent trade-protective", I = "Trade-related investment",
          M = "Government procurement",
          E = "Non-automatic import licensing, quotas, prohibitions",
          L = "Subsidies", P = "Export-related")

figura_7 <- function(gta) {
  por <- c("MAST_code", "gtaevaluation", "inception_year")
  d <- gta %>%
    mutate(ch = coalesce(mastchapter, ""),
           # gen MAST_code=substr(mastchapter,1,1) + reemplazos
           MAST_code = case_when(
             ch %in% c("Instrument unclear", "") ~ "NS",
             ch %in% c("Capital control measures", "Tariff measures") ~ "TAR",
             ch == "FDI measures" ~ "FDI",
             ch == "Migration measures" ~ "MIG",
             TRUE ~ substr(ch, 1, 1))) %>%
    # unique(interventionid), by(...) gen(...) + collapse (sum)
    group_by(across(all_of(por))) %>%
    summarise(number_interventions = n_distinct(interventionid), .groups = "drop") %>%
    # fillin MAST_code gtaevaluation inception_year / replace ...=0 if _fillin==1
    complete(MAST_code, gtaevaluation, inception_year,
             fill = list(number_interventions = 0)) %>%
    # egen num_code_year=std(number_interventions), by(gtaevaluation) -> num_sd
    # (no se grafica, pero queda en los datos como en el original)
    group_by(gtaevaluation) %>%
    mutate(num_sd = (number_interventions - mean(number_interventions)) / sd(number_interventions)) %>%
    ungroup() %>%
    # replace MA=subinstr(MA," ","_",.) / drop if inception_year==2008
    mutate(MAST_code = gsub(" ", "_", MAST_code)) %>%
    filter(!(inception_year %in% 2008)) %>%
    # sort ...; bys ...: gen n1 = n - n[1]; replace n1 = n - n[2] if n1==.
    # -> diferencia respecto del primer año (2009): "Index [2009=0]"
    arrange(gtaevaluation, MAST_code, inception_year) %>%
    group_by(gtaevaluation, MAST_code) %>%
    mutate(number_interventions = coalesce(number_interventions - first(number_interventions),
                                           number_interventions - nth(number_interventions, 2))) %>%
    ungroup()

  # reshape wide num*, i(gtaevaluation inception_year) j(MAST_code) string
  wide <- d %>%
    pivot_wider(id_cols = c(gtaevaluation, inception_year), names_from = MAST_code,
                values_from = c(number_interventions, num_sd), names_sep = "")

  for (caso in list(list(2, "A", "restrictive", 2), list(1, "B", "liberalizing", 1))) {
    g <- d %>%
      filter(gtaevaluation == caso[[1]], MAST_code %in% names(mast)) %>%
      mutate(codigo = factor(mast[MAST_code], levels = mast))
    p <- ggplot(g, aes(inception_year, number_interventions, colour = codigo, linetype = codigo)) +
      geom_vline(xintercept = c(2015, 2019, 2022), colour = ink, linewidth = 0.4) +
      geom_hline(yintercept = 0, colour = ink, linewidth = 0.4) +
      geom_line(linewidth = 0.9) +
      scale_colour_manual(values = series) +
      scale_linetype_manual(values = c("dashed", "longdash", "dotdash", "dotted", "dashed", "twodash")) +
      scale_x_continuous(breaks = seq(2009, 2022, caso[[4]])) +
      labs(x = "Year", y = paste0("Index [2009=0] of ", caso[[3]], " measures")) +
      guides(colour = guide_legend(ncol = 2), linetype = guide_legend(ncol = 2)) +
      tema + anos_45
    guardar(p, paste0("7", caso[[2]]),
            filter(wide, gtaevaluation == caso[[1]]) %>% arrange(inception_year), height = 6)
  }
}


# ----------------------------------------------------------------------
# Cada figura usa datos distintos: si falta un archivo se avisa y se sigue.
correr <- function(f, ...) {
  tryCatch(f(...), error = function(e) {
    if (grepl("does not exist|cannot open|No such file", conditionMessage(e)))
      message("  Omitida: ", conditionMessage(e))
    else stop(e)
  })
}
correr(figura_1)
correr(figura_2)
correr(figura_3)
gta_file <- file.path(rutas$data_temp, "GTA_cleaned.dta")
if (file.exists(gta_file)) {
  gta <- zap_labels(read_dta(gta_file))
  correr(figura_5, gta)
  correr(figura_6, gta)
  correr(figura_7, gta)
} else {
  message("  Omitidas figuras 5-7: falta ", gta_file)
}
