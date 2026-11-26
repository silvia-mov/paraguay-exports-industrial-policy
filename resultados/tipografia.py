"""Tipografía de los gráficos: Source Sans 3 para todo el texto y Fraunces para los títulos.

Basta con importarlo después de matplotlib (import tipografia). Registra las fuentes de la carpeta fuentes_graficos/
de la raíz del repositorio (licencia OFL) y hace que los títulos (texto en negrita de 13 puntos o más) usen Fraunces.
"""
from pathlib import Path

import matplotlib
from matplotlib import font_manager
from matplotlib.axes import Axes
from matplotlib.figure import Figure

CARPETA = next(p / "fuentes_graficos" for p in Path(__file__).resolve().parents if (p / "fuentes_graficos").is_dir())
for f in sorted(CARPETA.glob("*.ttf")):
    font_manager.fontManager.addfont(str(f))
matplotlib.rcParams["font.family"] = ["Source Sans 3", "DejaVu Sans"]   # DejaVu solo para símbolos que falten
matplotlib.rcParams["font.sans-serif"] = ["Source Sans 3", "DejaVu Sans"]
TITULO = "Fraunces"


def _titulo(kw):
    fs = kw.get("fontsize", kw.get("size"))
    w = kw.get("fontweight", kw.get("weight"))
    if w in ("bold", "semibold", 600, 700) and isinstance(fs, (int, float)) and fs >= 13:
        kw.pop("weight", None)
        kw.update(fontfamily=TITULO, fontweight="semibold")
    return kw


def _envolver(cls, nombre):
    orig = getattr(cls, nombre)

    def nuevo(self, *a, **kw):
        return orig(self, *a, **_titulo(kw))
    setattr(cls, nombre, nuevo)


for _c, _n in ((Figure, "text"), (Figure, "suptitle"), (Axes, "set_title")):
    _envolver(_c, _n)
