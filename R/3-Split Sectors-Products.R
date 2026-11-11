# *********************************************************************
#
#       PART 3:  SPLIT AFFECTED PRODUCTS (wide -> long)
#       (versión adaptada de 3-Split Sectors-Products.R; el original está
#        en stata/3-Split Sectors-Products.R)
#
# *********************************************************************
#
# En la Global Trade Alert cada intervención (ID) trae sus productos HS
# afectados en una sola celda: "870210, 870321, 870322, ...". Este paso crea
# una fila por cada par (ID, producto).
#
# Cambios respecto al original (el resultado es idéntico):
#   - usa rutas$data_temp en vez de depender de setwd()
#   - el bloque repetido para IP e IMP pasa a ser una función
#   - reemplaza reshape2::melt (paquete retirado) por tidyr/base
#
# Entrada: $data_temp/ProductsWide_GTA_IP.csv, ProductsWide_GTA_IMP.csv
# Salida:  $data_temp/ProductsLong_GTA_IP.dta, ProductsLong_GTA_IMP.dta

if (!exists("rutas")) source(here::here("R", "config.R"))

library(dplyr)
library(tidyr)
library(stringr)
library(haven)

# El original separa en 600 columnas (sector_1 ... sector_600): si una
# intervención lista más de 600 productos, el resto se pierde (separate()
# solo da un warning). Se replica; usa Inf para conservar todos.
max_products <- 600

split_products <- function(entrada, salida) {
  # read.csv(...); subset(select = c(ID, affectedproducts))
  products <- read.csv(file.path(rutas$data_temp, entrada), sep = ",") %>%
    select(ID, affectedproducts)

  # separate(affectedproducts, into = paste0("sector_", 1:600), sep = ",")
  # str_split da los mismos pedazos que separate (incluye "" en "a,,b")
  piezas <- str_split(products$affectedproducts, ",")
  n_cortados <- sum(lengths(piezas) > max_products)
  if (n_cortados > 0) {
    message("  Aviso: ", n_cortados, " intervenciones tienen más de ",
            max_products, " productos; se truncan como en el original.")
  }
  piezas <- lapply(piezas, head, n = max_products)

  long <- tibble(ID = products$ID, Product = piezas) %>%
    # melt(id.vars = "ID", variable.name = "Products_order", ...)
    unnest_longer(Product, indices_to = "Products_order") %>%
    # na.rm = TRUE
    filter(!is.na(Product)) %>%
    # melt apila columna por columna (todos los sector_1, luego sector_2...):
    # se reproduce ese orden ordenando por la posición dentro de la celda
    arrange(Products_order) %>%
    # str_trim(Product); select(-Products_order)
    mutate(Product = str_trim(Product)) %>%
    select(ID, Product)

  write_dta(long, file.path(rutas$data_temp, salida))
  message("  ", salida, ": ", nrow(long), " filas")
  invisible(long)
}

# Políticas industriales (IP) y barreras a la importación (IMP)
split_products("ProductsWide_GTA_IP.csv", "ProductsLong_GTA_IP.dta")
split_products("ProductsWide_GTA_IMP.csv", "ProductsLong_GTA_IMP.dta")
