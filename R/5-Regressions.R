# *********************************************************************
#
#       PART 3:  Run the analysis
#       (traducción de 5-Regressions.do)
#
# *********************************************************************
#
# Entrada: $data_temp/DataforRegressions.dta   (de 4-DataPrepare_GTA_PT2)
# Salidas: $tables/BMT_Tab_3..8.tex / .csv
#          $tables/lincom.csv   (combinaciones de coeficientes para la Figura 3)
#
# reghdfe -> fixest::feols. Equivalencias:
#   - a(A#B#C)          -> efecto fijo combinado A^B^C
#   - cluster(A#B)      -> cluster = ~A^B
#   - singletons        -> drop_singletons() los quita de forma iterativa, como
#                          reghdfe (fixest solo hace una pasada)
#   - region_code#c.IP  -> i(region_code, IP)  (una pendiente por región, sin base)
#   - ssc por defecto de fixest: no cuenta los efectos fijos anidados en el
#     cluster y usa t con G-1 grados de libertad, como reghdfe
#   Los coeficientes son idénticos a los de reghdfe. Los errores estándar pueden
#   diferir en el 3er decimal por cómo se cuentan los efectos fijos redundantes.

if (!exists("rutas")) source(here::here("R", "config.R"))
source(here::here("R", "stata_utils.R"))

library(dplyr)
library(haven)
library(fixest)

# a(EXP_CODE#IMP_CODE#year EXP_CODE#year#HS2012 IMP_CODE#year#ISIC3_2 HS2012#IMP_CODE)
fe_base <- paste("EXP_CODE^IMP_CODE^year + EXP_CODE^year^HS2012",
                 "+ IMP_CODE^year^ISIC3_2 + HS2012^IMP_CODE")
# Tabla 4: a(... IMP_CODE#year#HS2012 EXP_CODE#IMP_CODE#HS2012)
fe_strict <- paste("EXP_CODE^IMP_CODE^year + EXP_CODE^year^HS2012",
                   "+ IMP_CODE^year^HS2012 + EXP_CODE^IMP_CODE^HS2012")

# Orden de filas que produce estout al juntar los coeficientes de m1..m6
keep_base <- c("IP", "IP_RTA", "IMP_BARR", "IMP_BARR_RTA", "IP_RTA_SUBS")
keep_strict <- c("IP_RTA", "IMP_BARR_RTA", "IP_RTA_SUBS")

# reghdfe y x, a(fe) cluster(EXP_CODE#IMP_CODE)
reghdfe <- function(y, x, data, fe = fe_base) {
  fml <- as.formula(paste(y, "~", x, "|", fe))
  # muestra de estimación: sin missing en ninguna variable del modelo
  muestra <- data[complete.cases(data[all.vars(fml)]), ]
  muestra <- drop_singletons(muestra, fe)
  feols(fml, data = muestra, cluster = ~EXP_CODE^IMP_CODE)
}

lincoms <- list()   # resultados de lincom (en el original quedan ocultos por `quietly`)
guardar_lincom <- function(tabla, modelo, fit, pesos) {
  expr <- paste(ifelse(pesos == 1, names(pesos), paste0(pesos, "*", names(pesos))),
                collapse = " + ")
  res <- lincom(fit, pesos)
  message(sprintf("  lincom %s (%s): %.3f (se %.3f, p=%.3f)", expr, modelo,
                  res$estimate, res$se, res$p))
  lincoms[[length(lincoms) + 1]] <<- data.frame(tabla = tabla, modelo = modelo,
                                                lincom = expr, res)
}

# **# TABLE 1 / TABLE 2 -> no usan datos

# use "$data_temp/DataforRegressions", clear
df <- read_dta(file.path(rutas$data_temp, "DataforRegressions.dta"),
               col_select = c(EXP_GROWTH, ln_exp, EXPORTS, IP, IP_RTA, IMP_BARR,
                              IMP_BARR_RTA, IP_RTA_SUBS, EXP_CODE, IMP_CODE, year,
                              HS2012, ISIC3_2, region, incomegroup)) %>%
  zap_labels() %>%
  # keep if EXPORTS>1000
  # (En Stata missing>1000 es verdadero: las filas sin EXPORTS -economías sin
  #  comercio- se quedan, aunque luego no entran a ninguna regresión.
  #  EXPORTS está en miles de USD: es el umbral de USD 1 millón de la nota 3.)
  filter(EXPORTS > 1000 | is.na(EXPORTS))


# **# TABLE 3 ------------------------------------------------------------------
# Tablas 3, 5 y 6: mismas 6 especificaciones, cambia y/muestra
tabla_base <- function(n, y, data) {
  message("\n===== TABLE ", n, " =====")
  m <- list()
  m$m1 <- reghdfe(y, "IP", data)
  m$m2 <- reghdfe(y, "IP + IP_RTA", data)
  # Las 4 barras de la Figura 3 (no está en el original: los autores la
  # armaron a mano con estos números de la Tabla 3)
  guardar_lincom(n, "m1", m$m1, c(IP = 1))
  guardar_lincom(n, "m2", m$m2, c(IP = 1))
  guardar_lincom(n, "m2", m$m2, c(IP = 1, IP_RTA = 1))
  m$m3 <- reghdfe(y, "IP + IMP_BARR", data)
  m$m4 <- reghdfe(y, "IP + IMP_BARR + IP_RTA + IMP_BARR_RTA", data)
  m$m5 <- reghdfe(y, "IP + IP_RTA_SUBS", data)
  guardar_lincom(n, "m5", m$m5, c(IP = 1, IP_RTA_SUBS = 0.5))
  m$m6 <- reghdfe(y, "IP + IMP_BARR + IMP_BARR_RTA + IP_RTA_SUBS", data)
  # estout m* [using "$tables/BMT_Tab_`n'.tex"], k(...) ...
  estout(m, keep = keep_base, path = file.path(rutas$tables, paste0("BMT_Tab_", n)))
}

tabla_base(3, "EXP_GROWTH", df)


# **# TABLE 4 More stringent ---------------------------------------------------
message("\n===== TABLE 4 =====")
m <- list(
  m1 = reghdfe("EXP_GROWTH", "IP_RTA", df, fe_strict),
  m2 = reghdfe("EXP_GROWTH", "IP_RTA + IMP_BARR_RTA", df, fe_strict),
  m3 = reghdfe("EXP_GROWTH", "IP_RTA_SUBS", df, fe_strict),
  m4 = reghdfe("EXP_GROWTH", "IP_RTA + IMP_BARR_RTA + IP_RTA_SUBS", df, fe_strict)
)
estout(m, keep = keep_strict, path = file.path(rutas$tables, "BMT_Tab_4"))


# **# TABLE 5 No outliers --------------------------------------------------------
# ... if EXP_GROWTH>-200 & EXP_GROWTH<200
tabla_base(5, "EXP_GROWTH", filter(df, EXP_GROWTH > -200, EXP_GROWTH < 200))


# **# TABLE 6 Levels -------------------------------------------------------------
# replace ln_exp=ln_exp*100
df <- mutate(df, ln_exp = ln_exp * 100)
tabla_base(6, "ln_exp", df)


# **# TABLE 7 Heterogeneity across regions ---------------------------------------
message("\n===== TABLE 7 =====")
# replace region = "Advanced Economies" if incomegroup == "High income"
df <- mutate(df, region = if_else(incomegroup %in% "High income", "Advanced Economies", region))

# label define region 1 "Advanced Economies" 2 "East Asia & Pacific" ...
# encode region, gen(region_code) label(region) noextend
regiones <- c("Advanced Economies", "East Asia & Pacific", "Europe & Central Asia",
              "Latin America & Caribbean", "Middle East & North Africa", "South Asia",
              "Sub-Saharan Africa")
region <- ifelse(is.na(df$region), "", df$region)
fuera <- setdiff(unique(region[region != ""]), regiones)
if (length(fuera) > 0)   # noextend: Stata da error si aparece una región no definida
  stop("encode noextend: regiones sin código: ", paste(fuera, collapse = ", "))
df$region_code <- match(region, regiones)   # "" -> NA

# reghdfe EXP_GROWTH region_code#c.IP region_code#c.IP_RTA, a(...) cluster(...)
# OJO: region es la del EXPORTADOR (se unió por EXP en el paso 4).
# Las filas sin región se excluyen (complete.cases en reghdfe()), como hace
# Stata con un factor en missing.
m7 <- reghdfe("EXP_GROWTH", "i(region_code, IP) + i(region_code, IP_RTA)", df)
nombres7 <- unlist(lapply(c("IP", "IP_RTA"), function(v)
  setNames(paste(regiones, "x", v), paste0("region_code::", seq_along(regiones), ":", v))))
estout(list(m2 = m7), rename = nombres7, path = file.path(rutas$tables, "BMT_Tab_7"))


# **# TABLE 8 Heterogeneity across sectors -------------------------------------
message("\n===== TABLE 8 =====")
# reghdfe EXP_GROWTH ISIC3_2#c.IP ISIC3_2#c.IP_RTA, a(...) cluster(...)
d8 <- filter(df, !is.na(ISIC3_2), as.character(ISIC3_2) != "")
m8 <- reghdfe("EXP_GROWTH", "i(ISIC3_2, IP) + i(ISIC3_2, IP_RTA)", d8)
isic <- sort(unique(d8$ISIC3_2))
nombres8 <- unlist(lapply(c("IP", "IP_RTA"), function(v)
  setNames(paste("ISIC", isic, "x", v), paste0("ISIC3_2::", isic, ":", v))))
# (en el original el .tex de esta tabla se escribe sin style(tex): las dos
#  líneas estout están invertidas. Aquí se guarda en LaTeX válido.)
estout(list(m1 = m8), rename = nombres8, path = file.path(rutas$tables, "BMT_Tab_8"))

# Resultados de lincom (para la Figura 3)
write.csv(do.call(rbind, lincoms), file.path(rutas$tables, "lincom.csv"), row.names = FALSE)
