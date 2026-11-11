# Configuración común (equivale a la PARTE 0 de 0-master.do: los `global`).
# La carga el master y también cada script, para que puedas correr un
# script solo en RStudio sin pasar por el master:
#   if (!exists("rutas")) source(here::here("R", "config.R"))

# global root ""
# here::here() detecta la raíz del proyecto (donde está el .Rproj o .git),
# así no hay que editar la ruta a mano en cada computador.
root <- here::here()

# Vuelta de la réplica (afecta solo al paso 1, acuerdos superpuestos):
#   1 = código original: si un par de países tiene varios acuerdos el mismo
#       año, se queda el de MENOR cobertura de subsidios (sort + duplicates drop)
#   2 = variante corregida: se queda el de MAYOR cobertura (gsort -SUBS_COVERAGE)
vuelta <- 1

# global data_raw / data_temp / data_aux / do_files / log_files / figures / tables
rutas <- list(
  data_raw  = file.path(root, "1_Data", "Raw_data"),
  data_temp = file.path(root, "1_Data", "Temp"),
  data_aux  = file.path(root, "1_Data", "Auxiliary"),
  code      = file.path(root, "R"),            # equivale a $do_files
  log_files = file.path(root, "3_Log_files"),
  figures   = file.path(root, "4_Figures"),
  tables    = file.path(root, "5_Tables")
)

# Crea las carpetas de salida si no existen
for (d in rutas[c("data_temp", "log_files", "figures", "tables")]) {
  dir.create(d, recursive = TRUE, showWarnings = FALSE)
}
rm(d)
