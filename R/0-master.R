# ******************************************************************** #
#                IP TRADE EFFECTS AND PTA                              #
#                Master script (traducción de 0-master.do)             #
# ******************************************************************** #
#
# Uso: abre el proyecto .Rproj en RStudio y ejecuta este archivo
#      (Ctrl + Shift + S), o desde la terminal: Rscript R/0-master.R

# ----------------------------------------------------------------------
# PART 0: STANDARDIZE SETTINGS & PREPARING FOLDER PATH GLOBALS
# ----------------------------------------------------------------------

# clear all / macro drop _all
rm(list = ls())

# set more off / set linesize 80
options(width = 80, scipen = 999)

# sysdir set PLUS ".../ado" + ssc install reghdfe estout unique ftools
# -> En R las versiones se fijan con renv (renv::restore() las instala).
#    reghdfe -> fixest::feols | estout -> fixest::etable / modelsummary
#    unique  -> dplyr::n_distinct
paquetes <- c("here", "haven", "readxl", "data.table", "dplyr", "tidyr",
              "stringr", "fixest", "modelsummary", "ggplot2")
faltan <- paquetes[!paquetes %in% rownames(installed.packages())]
if (length(faltan) > 0) install.packages(faltan)

# set varabbrev on -> sin equivalente (en R los nombres van completos)

# global root "" + global data_raw ... (rutas en R/config.R)
source(here::here("R", "config.R"))

# log using "$log_files/reppackage161_1", replace
# sink(split = TRUE) escribe a la consola y al archivo a la vez.
log_con <- file(file.path(rutas$log_files, "reppackage161_1_R.log"), open = "wt")
sink(log_con, split = TRUE)
sink(log_con, type = "message")   # también guarda warnings y errores

# ----------------------------------------------------------------------
# PART 1: RUN ALL THE CODES NEEDED TO CLEAN THE DATA & PRODUCE OUTPUT
# TRUE = se ejecuta. Equivale a comentar/descomentar líneas `do ...`.
# ----------------------------------------------------------------------
run <- c(
  # 1. CLEAN DATA
  "1-DataPrepare_PTA.R"          = TRUE,  # do "1-DataPrepare_PTA.do"
  "2-DataPrepare_GTA_PT1.R"      = TRUE,  # do "2-DataPrepare_GTA_PT1.do"
  "3-Split Sectors-Products.R"   = TRUE,  # script R original (en Stata era manual)
  "4-DataPrepare_GTA_PT2.R"      = TRUE,  # do "4-DataPrepare_GTA_PT2.do"
  # 2. RUN REGRESSIONS & PRODUCE TABLES
  "5-Regressions.R"              = TRUE,  # do "5-Regressions.do"
  # 3. PRODUCE FIGURES
  "6-Figures.R"                  = TRUE   # do "6-Figures.do"
)

# tryCatch(finally = ...) garantiza que el log se cierre aunque un script falle
tryCatch({
  t_total <- Sys.time()
  for (script in names(run)) {
    if (!run[[script]]) {
      message("Omitido: ", script)
      next
    }
    ruta <- file.path(rutas$code, script)
    if (!file.exists(ruta)) stop("No existe ", ruta, " (¿ya fue traducido?)")
    message(format(Sys.time(), "%H:%M:%S"), " | Ejecutando: ", script)
    t0 <- Sys.time()
    # equivale a `do "archivo.do"`; local = globalenv() para que vea `rutas`
    source(ruta, local = globalenv(), echo = FALSE)
    message("Terminado: ", script, " (",
            round(difftime(Sys.time(), t0, units = "mins"), 1), " min)")
  }
  message("Pipeline completo en ",
          round(difftime(Sys.time(), t_total, units = "mins"), 1), " min")
}, finally = {
  sink(type = "message")
  sink()
  close(log_con)  # log close
})
