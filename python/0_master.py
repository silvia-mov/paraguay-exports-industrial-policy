"""
* ******************************************************************** *
*                IP TRADE EFFECTS AND PTA                              *
*                Master script (traducción de 0-master.do)             *
* ******************************************************************** *

Uso (desde la raíz del proyecto):
    python python/0_master.py

Ejecuta, en orden, todos los scripts que limpian los datos y producen
tablas y figuras. Con el diccionario RUN puedes apagar pasos (útil porque
el pipeline completo tarda horas).
"""
import logging
import runpy
import sys
import time
from pathlib import Path

# Hace importable config.py desde los scripts que ejecutamos con runpy
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import CODE, LOG_FILES  # noqa: E402

# ----------------------------------------------------------------------
# PART 0: STANDARDIZE SETTINGS
#   clear all / macro drop _all -> cada ejecución de Python parte limpia
#   set more off / set linesize 80 -> no aplican
#   set varabbrev on -> sin equivalente (en pandas los nombres van completos)
#   sysdir set PLUS ".../ado" + ssc install -> dependencias en requirements.txt:
#       pip install -r requirements.txt
#   (reghdfe -> pyfixest, estout -> pyfixest.etable, unique -> nunique())
# ----------------------------------------------------------------------

# log using "$log_files/reppackage161_1", replace
# Escribe a la consola y al archivo a la vez. mode="w" equivale a "replace".
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILES / "reppackage161_1.log", mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("master")

# ----------------------------------------------------------------------
# PART 1: RUN ALL THE CODES NEEDED TO CLEAN THE DATA & PRODUCE OUTPUT
# True = se ejecuta. Equivale a comentar/descomentar líneas `do ...`.
# ----------------------------------------------------------------------
RUN = {
    # 1. CLEAN DATA
    "1_data_prepare_pta.py": True,            # do "1-DataPrepare_PTA.do"
    "2_data_prepare_gta_pt1.py": True,        # do "2-DataPrepare_GTA_PT1.do"
    "3_split_sectors_products.py": True,      # "3-Split Sectors-Products.R" (en Stata era manual)
    "4_data_prepare_gta_pt2.py": True,        # do "4-DataPrepare_GTA_PT2.do"
    # 2. RUN REGRESSIONS & PRODUCE TABLES
    "5_regressions.py": True,                 # do "5-Regressions.do"
    # 3. PRODUCE FIGURES
    "6_figures.py": True,                     # do "6-Figures.do"
}


def main() -> None:
    t_total = time.perf_counter()
    for script, run in RUN.items():
        if not run:
            log.info("Omitido: %s", script)
            continue
        path = CODE / script
        if not path.exists():
            raise FileNotFoundError(f"No existe {path} (¿ya fue traducido?)")
        log.info("Ejecutando: %s", script)
        t0 = time.perf_counter()
        # equivale a `do "archivo.do"`: corre el script como si fuera __main__
        runpy.run_path(str(path), run_name="__main__")
        log.info("Terminado: %s (%.1f min)", script, (time.perf_counter() - t0) / 60)
    log.info("Pipeline completo en %.1f min", (time.perf_counter() - t_total) / 60)


if __name__ == "__main__":
    main()
