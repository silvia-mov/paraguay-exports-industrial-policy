"""
Configuración común del proyecto (equivale a la PARTE 0 de 0-master.do).

Cada script del pipeline hace `from config import *` para usar las mismas
rutas, igual que los do-files usan los `global` definidos en el master.
"""
import os
from pathlib import Path

# ----------------------------------------------------------------------
# global root ""   // Change the root to the desired folder of the replicator
#
# En lugar de editar la ruta a mano, se detecta sola: es la carpeta que
# contiene a /python. Si tus datos están en otro lugar, cámbiala aquí,
# p. ej.: ROOT = Path(r"C:/Users/<usuario>/Documents/RR_EAP_2024_161")
# ----------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
# Alternativa sin editar este archivo: definir la variable de entorno
# TESIS_ROOT con la carpeta que contiene 1_Data, 3_Log_files, etc.
if os.environ.get("TESIS_ROOT"):
    ROOT = Path(os.environ["TESIS_ROOT"])

# ----------------------------------------------------------------------
# Vuelta de la réplica (afecta solo al paso 1, acuerdos superpuestos):
#   1 = código original: si un par de países tiene varios acuerdos el mismo
#       año, se queda el de MENOR cobertura de subsidios (sort + duplicates drop)
#   2 = variante corregida: se queda el de MAYOR cobertura (gsort -SUBS_COVERAGE)
# ----------------------------------------------------------------------
VUELTA = int(os.environ.get("TESIS_VUELTA", 1))

# global data_raw / data_temp / data_aux / do_files / log_files / figures / tables
DATA_RAW = ROOT / "1_Data" / "Raw_data"
DATA_TEMP = ROOT / "1_Data" / "Temp"
DATA_AUX = ROOT / "1_Data" / "Auxiliary"
CODE = ROOT / "python"            # equivale a $do_files
LOG_FILES = ROOT / "3_Log_files"
FIGURES = ROOT / "4_Figures"
TABLES = ROOT / "5_Tables"

# Stata crea los archivos en carpetas que ya deben existir; aquí las
# creamos si faltan (las de salida, no las de datos de entrada).
for _d in (DATA_TEMP, LOG_FILES, FIGURES, TABLES):
    _d.mkdir(parents=True, exist_ok=True)
