"""Crea una versión en Excel de cada CSV que se ofrece para descargar en la página.

Uso:
    python python/csv_a_excel.py datos/a.csv datos/b.csv ...

Cada Excel queda al lado de su CSV, con el mismo nombre: hoja "Datos" (Calibri 10, encabezado fijo con filtro)
y hoja "Notas" (de qué archivo sale). Las columnas de códigos (NCM, posición, código...) quedan como texto,
para no perder los ceros a la izquierda.
"""
import re
import sys
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

TEXTO = re.compile(r"(?i)ncm|codigo|código|posicion|posición|producto|capitulo|capítulo|hs|nandina|sa6|cod_|_cod|partida|^id")
FUENTE = Font(name="Calibri", size=10)
NEGRITA = Font(name="Calibri", size=10, bold=True)
FONDO = PatternFill("solid", fgColor="B7D0CC")


def a_numero(col):
    if TEXTO.search(col.name):
        return col
    n = pd.to_numeric(col, errors="coerce")
    return n if n.notna().sum() == col.replace("", pd.NA).notna().sum() else col


def convertir(csv):
    csv = Path(csv)
    d = pd.read_csv(csv, dtype=str, keep_default_na=False, encoding="utf-8-sig", sep=None, engine="python")
    d = d.apply(a_numero)
    xlsx = csv.with_suffix(".xlsx")
    with pd.ExcelWriter(xlsx, engine="openpyxl") as w:
        d.to_excel(w, sheet_name="Datos", index=False)
        pd.DataFrame({"Notas": [f"Misma información que {csv.name}.",
                                "Generado con python/csv_a_excel.py. Las columnas de códigos están como texto."]}
                     ).to_excel(w, sheet_name="Notas", index=False)
    wb = load_workbook(xlsx)
    ws = wb["Datos"]
    for fila in ws.iter_rows():
        for c in fila:
            c.font = FUENTE
    for c in ws[1]:
        c.font, c.fill, c.alignment = NEGRITA, FONDO, Alignment(wrap_text=True, vertical="top")
    for i, col in enumerate(d.columns, start=1):
        largo = max([len(str(col))] + [len(str(v)) for v in d[col].head(500)])
        ws.column_dimensions[get_column_letter(i)].width = min(max(largo + 2, 8), 60)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for fila in wb["Notas"].iter_rows():
        for c in fila:
            c.font = FUENTE
    wb["Notas"].column_dimensions["A"].width = 90
    wb.save(xlsx)
    print(xlsx, len(d))


if __name__ == "__main__":
    for f in sys.argv[1:]:
        convertir(f)
