"""
* *********************************************************************
*
*       PART 3:  SPLIT AFFECTED PRODUCTS (wide -> long)
*       (traducción de 3-Split Sectors-Products.R)
*
* *********************************************************************

En la Global Trade Alert cada intervención (ID) trae sus productos HS
afectados en una sola celda: "870210, 870321, 870322, ...". Este paso crea
una fila por cada par (ID, producto).

Entrada:  $data_temp/ProductsWide_GTA_IP.csv    (políticas industriales)
          $data_temp/ProductsWide_GTA_IMP.csv   (barreras a la importación)
          (las genera 2-DataPrepare_GTA_PT1)
Salida:   $data_temp/ProductsLong_GTA_IP.dta
          $data_temp/ProductsLong_GTA_IMP.dta
"""
import os

import pandas as pd

from config import DATA_TEMP

# El script original separa en 600 columnas (sector_1 ... sector_600):
# si una intervención lista más de 600 productos, el resto se pierde
# (tidyr::separate solo emite un warning). Se replica para obtener los
# mismos datos; usa None para conservar todos los productos.
MAX_PRODUCTS = 600
# Versión corregida (sin tope): variable de entorno TESIS_SIN_TRUNCAR=1
# (junto con el insheet sin corte del paso 2).
if os.environ.get("TESIS_SIN_TRUNCAR") == "1":
    MAX_PRODUCTS = None


def split_products(entrada: str, salida: str) -> pd.DataFrame:
    # Products = read.csv(...); subset(select = c(ID, affectedproducts))
    # keep_default_na=False + na_values=["NA"] imita read.csv: solo "NA"
    # es missing; una celda vacía queda como texto "".
    products = pd.read_csv(
        DATA_TEMP / entrada,
        usecols=["ID", "affectedproducts"],
        dtype={"affectedproducts": str},
        keep_default_na=False,
        na_values=["NA"],
    )

    # separate(affectedproducts, into = paste0("sector_", 1:600), sep = ",")
    piezas = products["affectedproducts"].str.split(",")
    n = piezas.str.len()
    if MAX_PRODUCTS is not None:
        n_cortados = int((n > MAX_PRODUCTS).sum())
        if n_cortados:
            print(f"  Aviso: {n_cortados} intervenciones tienen más de "
                  f"{MAX_PRODUCTS} productos; se truncan como en el original.")
        piezas = piezas.str[:MAX_PRODUCTS]

    # melt(id.vars = "ID", variable.name = "Products_order",
    #      value.name = "Product", na.rm = TRUE)
    long = (
        products[["ID"]]
        .assign(Product=piezas)
        .explode("Product")
        .dropna(subset=["Product"])          # na.rm = TRUE
    )
    # melt apila columna por columna (todos los sector_1, luego sector_2, ...).
    # Se reproduce ese orden con la posición del producto dentro de la celda.
    long["Products_order"] = long.groupby(level=0).cumcount()
    long = long.sort_values("Products_order", kind="stable")

    # Products$Product <- str_trim(Products$Product)
    long["Product"] = long["Product"].str.strip()

    # select(-Products_order)
    long = long[["ID", "Product"]].reset_index(drop=True)

    # write_dta(Products, ...)
    long.to_stata(DATA_TEMP / salida, write_index=False, version=118)
    print(f"  {salida}: {len(long):,} filas")
    return long


# Políticas industriales (IP) y barreras a la importación (IMP)
split_products("ProductsWide_GTA_IP.csv", "ProductsLong_GTA_IP.dta")
split_products("ProductsWide_GTA_IMP.csv", "ProductsLong_GTA_IMP.dta")
