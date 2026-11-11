"""
Utilidades comunes de la estimación por país (scripts 7 a 13).

El país exportador se elige con la variable de entorno TESIS_PAIS (código ISO3,
por defecto "PRY" = Paraguay), sin editar el código:

    TESIS_PAIS=URY python python/7_pais.py

ACUERDO DE REFERENCIA
El efecto neto de una medida para un socio con acuerdo es β1 + d·β2, donde d es
la cobertura de disciplinas sobre subsidios del acuerdo (SUBS_COVERAGE, de 0 a 1).
Para Paraguay el único acuerdo con cobertura > 0 y medidas en la muestra es el
Mercosur (d = 4/12 = 1/3; socios ARG, BRA, URY). Para otros países se detecta
solo: es la cobertura > 0 con más observaciones tratadas (IP_RTA_SUBS > 0), y
sus socios son los importadores con esa cobertura. Se puede fijar a mano con
TESIS_COB_REF (por ejemplo 0.25).

OJO: si el país no tiene ningún socio con IP_RTA_SUBS > 0, β2 no se puede
estimar (pasa con Paraguay en la Vuelta 1: ver docs/correcciones.md).
"""
import os

import numpy as np
import pandas as pd

from config import DATA_TEMP

PAIS = os.environ.get("TESIS_PAIS", "PRY").upper()


def cargar_muestra(cols, pais=PAIS):
    """Filas de DataforRegressions con `pais` como exportador (EXP == pais)."""
    if (DATA_TEMP / "DataforRegressions.parquet").exists():
        df = pd.read_parquet(DATA_TEMP / "DataforRegressions.parquet", columns=cols,
                             filters=[("EXP", "==", pais)])
    else:
        # La base completa pesa ~2,5 GB: se lee por partes.
        import pyreadstat
        partes = [
            chunk[chunk["EXP"] == pais]
            for chunk, _ in pyreadstat.read_file_in_chunks(
                pyreadstat.read_dta, str(DATA_TEMP / "DataforRegressions.dta"),
                chunksize=1_000_000, usecols=cols)
        ]
        df = pd.concat(partes, ignore_index=True)
    for c in ("EXP", "IMP"):
        if c in df.columns:
            df[c] = df[c].astype(str)
    if "IMP_CODE" in df.columns:
        df["IMP_CODE"] = df["IMP_CODE"].astype(int)
    if df.empty:
        raise SystemExit(f"No hay filas con EXP == '{pais}'. ¿El código ISO3 es correcto?")
    return df


def acuerdo_referencia(df, obligatorio=False):
    """(cobertura d, lista de socios) del acuerdo de referencia. Ver docstring del módulo.

    Con obligatorio=True corta el script si el país no tiene socios tratados.
    """
    tratados = df[(df["IP_RTA_SUBS"] > 0)]
    if os.environ.get("TESIS_COB_REF"):
        cob = float(os.environ["TESIS_COB_REF"])
    elif tratados.empty:
        print(f"AVISO: {PAIS} no tiene observaciones con IP_RTA_SUBS > 0; "
              "β2 y el efecto neto del acuerdo no se pueden estimar.")
        if obligatorio:
            raise SystemExit("Este script necesita al menos un socio con IP_RTA_SUBS > 0.")
        return np.nan, []
    else:
        # IP_RTA_SUBS = IP × SUBS_COVERAGE: entre las filas tratadas es la cobertura
        cob = float(tratados["IP_RTA_SUBS"].round(6).value_counts().idxmax())
    socios = sorted(df.loc[np.isclose(df["IP_RTA_SUBS"], cob, atol=1e-6), "IMP"].unique())
    print(f"Acuerdo de referencia: cobertura {cob:.3f}; socios con medidas: {', '.join(socios) or '—'}")
    return cob, socios


def socios_tratados_principales(df, n=2):
    """Los `n` socios con más observaciones con IP_RTA_SUBS > 0 (para "sacar un socio por vez")."""
    return df.loc[df["IP_RTA_SUBS"] > 0, "IMP"].value_counts().index[:n].tolist()
