"""Gráficos del README a partir de los CSV de esta carpeta.

Uso (desde la raíz del repositorio):
    python resultados/figuras.py

Genera cada gráfico en dos versiones (tema claro y oscuro de GitHub) en docs/img/.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
IMG = AQUI.parent / "docs" / "img"
IMG.mkdir(parents=True, exist_ok=True)

TEMAS = {
    "light": dict(texto="#0b0b0b", texto2="#52514e", grilla="#e4e3df", eje="#c3c2b7",
                  s1="#2a78d6", s2="#eb6834", neutro="#a3a29b"),
    "dark": dict(texto="#f0efec", texto2="#c3c2b7", grilla="#33332f", eje="#52514e",
                 s1="#3987e5", s2="#d95926", neutro="#6f6e68"),
}


def coma(x, _pos=None):
    """Formato con coma decimal y signo menos tipográfico."""
    txt = f"{x:g}".replace("-", "−").replace(".", ",")
    return txt


def estilo(ax, t, grilla="x"):
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(t["eje"])
    ax.tick_params(colors=t["texto2"], labelsize=10, length=0)
    ax.grid(axis=grilla, color=t["grilla"], linewidth=0.8)
    ax.set_axisbelow(True)


def titulo(fig, t, texto, sub):
    fig.text(0.01, 0.98, texto, ha="left", va="top", fontsize=14, fontweight="bold", color=t["texto"])
    fig.text(0.01, 0.915, sub, ha="left", va="top", fontsize=10.5, color=t["texto2"])


def guardar(fig, nombre, modo):
    fig.savefig(IMG / f"{nombre}_{modo}.png", dpi=200, transparent=True)
    plt.close(fig)


# ---------------------------------------------------------------- 1. Medidas por año
med = pd.read_csv(AQUI / "medidas_por_anio.csv")
for modo, t in TEMAS.items():
    fig, ax = plt.subplots(figsize=(8, 3.8))
    fig.subplots_adjust(left=0.07, right=0.98, top=0.78, bottom=0.12)
    colores = [t["s1"] if a >= 2020 else t["neutro"] for a in med["Año"]]
    ax.bar(med["Año"], med["Total"], color=colores, width=0.7)
    for a, v in zip(med["Año"], med["Total"]):
        if a >= 2020:
            ax.text(a, v + 25, f"{v:,}".replace(",", "."), ha="center", va="bottom",
                    fontsize=9.5, color=t["texto"])
    estilo(ax, t, grilla="y")
    ax.set_xticks(med["Año"])
    titulo(fig, t, "Medidas de política industrial de los 12 principales socios de Paraguay",
           "Cantidad de medidas nuevas por año (Global Trade Alert, 2012–2022). "
           "Total: 11.104; desde 2020, el salto.")
    guardar(fig, "medidas_por_anio", modo)

# ---------------------------------------------------------------- 2. Efecto principal
ec6 = pd.read_csv(AQUI / "paraguay_ec6.csv").set_index("Especificación")
paneles = [
    ("Tasa de crecimiento (puntos porcentuales)", [
        ("Robustez: tasa de crecimiento", "Crecimiento"),
        ("Robustez: crecimiento sin valores atípicos", "Sin valores atípicos"),
        ("Robustez: crecimiento con umbral de USD 1 millón", "Flujos > USD 1 millón"),
    ]),
    ("Logaritmo de las exportaciones", [
        ("Principal: logaritmo (sin umbral)", "Logaritmo"),
        ("Robustez: logaritmo sin valores atípicos", "Sin valores atípicos"),
        ("Robustez: logaritmo con umbral de USD 1 millón", "Flujos > USD 1 millón"),
    ]),
]
for modo, t in TEMAS.items():
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.4))
    fig.subplots_adjust(left=0.17, right=0.98, top=0.72, bottom=0.12, wspace=0.55)
    for ax, (nombre_panel, filas) in zip(axes, paneles):
        for i, (clave, etiqueta) in enumerate(filas):
            r = ec6.loc[clave]
            y = len(filas) - 1 - i
            for dy, b, se, c in ((0.15, r["b_IP"], r["se_IP"], t["s1"]),
                                 (-0.15, r["Mercosur_b"], r["Mercosur_se"], t["s2"])):
                ax.plot([b - 1.96 * se, b + 1.96 * se], [y + dy] * 2, color=c, linewidth=2,
                        solid_capstyle="round")
                ax.plot(b, y + dy, "o", color=c, markersize=8,
                        markeredgecolor="none")
        ax.axvline(0, color=t["texto2"], linewidth=1)
        ax.set_yticks(range(len(filas)))
        ax.set_yticklabels([e for _, e in reversed(filas)], color=t["texto"])
        ax.set_ylim(-0.6, len(filas) - 0.4)
        ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(coma))
        ax.set_title(nombre_panel, fontsize=11, color=t["texto"], loc="left", pad=8)
        estilo(ax, t)
    titulo(fig, t, "Efecto de una medida del socio sobre las exportaciones de Paraguay",
           "Coeficientes e intervalos de confianza del 95 % (errores agrupados por importador).")
    fig.text(0.17, 0.83, "●  Socio sin disciplinas sobre subsidios (β₁)", color=t["s1"], fontsize=10.5)
    fig.text(0.58, 0.83, "●  Socio del Mercosur (β₁ + β₂/3)", color=t["s2"], fontsize=10.5)
    guardar(fig, "efecto_principal", modo)

# ---------------------------------------------------------------- 3. Robustez: p-valores
inf = pd.read_csv(AQUI / "paraguay_inferencia.csv")
pruebas = [
    ("Errores agrupados por importador (base)", "Base: errores agrupados por importador"),
    ("Bootstrap salvaje (9.999 repeticiones)", "Bootstrap salvaje"),
    ("Sorteo de socios placebo (1.999)", "Sorteo de socios placebo"),
    ("Errores agrupados por importador y año", "Agrupados por importador y año"),
    ("Sin Brasil", "Sin Brasil"),
    ("Efectos fijos de producto", "EF de producto"),
    ("Efectos fijos de importador por producto", "EF de importador × producto"),
]
for modo, t in TEMAS.items():
    fig, ax = plt.subplots(figsize=(9, 4.8))
    fig.subplots_adjust(left=0.33, right=0.97, top=0.76, bottom=0.12)
    for serie, dy, c in (("Tasa de crecimiento", 0.14, t["s1"]), ("Logaritmo", -0.14, t["s2"])):
        sub = inf[inf["Especificación"] == serie].set_index("Prueba")
        for i, (clave, _) in enumerate(pruebas):
            y = len(pruebas) - 1 - i
            p = max(sub.loc[clave, "p"], 1e-6)
            ax.plot(p, y + dy, "o", color=c, markersize=8, markeredgecolor="none")
    for umbral, txt, ha in ((0.05, "5 % ", "right"), (0.10, " 10 %", "left")):
        ax.axvline(umbral, color=t["texto2"], linewidth=1, linestyle=(0, (3, 3)))
        ax.text(umbral, len(pruebas) - 0.45, txt, ha=ha, va="bottom", fontsize=9,
                color=t["texto2"])
    ax.set_xscale("log")
    ax.set_xlim(5e-7, 1.2)
    ax.set_xticks([1e-6, 1e-4, 1e-2, 0.05, 0.1, 0.5, 1])
    ax.set_xticklabels(["0,000001", "0,0001", "0,01", "0,05", "0,1", "0,5", "1"])
    ax.set_yticks(range(len(pruebas)))
    ax.set_yticklabels([e for _, e in reversed(pruebas)], color=t["texto"])
    ax.set_ylim(-0.6, len(pruebas) - 0.2)
    ax.set_xlabel("p-valor de β₂ (escala logarítmica; a la izquierda de la línea = significativo)",
                  color=t["texto2"], fontsize=10)
    estilo(ax, t)
    titulo(fig, t, "¿Resiste el efecto de la profundidad del acuerdo (β₂)?",
           "p-valor del coeficiente de IP_RTA_SUBS en cada prueba de robustez.")
    fig.text(0.33, 0.83, "●  Tasa de crecimiento", color=t["s1"], fontsize=10.5)
    fig.text(0.62, 0.83, "●  Logaritmo", color=t["s2"], fontsize=10.5)
    guardar(fig, "robustez_pvalores", modo)

# ---------------------------------------------------------------- 4. GTAP
gt = pd.read_csv(AQUI / "gtap_por_sector.csv")
s1 = gt[gt["Escenario"] == "S1"].set_index("Sector")
s3 = gt[gt["Escenario"] == "S3"].set_index("Sector")
orden = s1.sort_values("Variación (%)").index.tolist()
for modo, t in TEMAS.items():
    fig, ax = plt.subplots(figsize=(9, 4.8))
    fig.subplots_adjust(left=0.27, right=0.97, top=0.76, bottom=0.1)
    y = np.arange(len(orden))
    ax.barh(y + 0.19, s1.loc[orden, "Variación (%)"], height=0.36, color=t["s1"])
    ax.barh(y - 0.19, s3.loc[orden, "Variación (%)"], height=0.36, color=t["s2"])
    ax.axvline(0, color=t["texto2"], linewidth=1)
    etiquetas = [f"{s} *" if str(s1.loc[s, "Subsidiado"]) == "True" else s for s in orden]
    ax.set_yticks(y)
    ax.set_yticklabels(etiquetas, color=t["texto"])
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(coma))
    ax.set_xlabel("Variación de las exportaciones de Paraguay a Brasil (%)", color=t["texto2"],
                  fontsize=10)
    estilo(ax, t)
    titulo(fig, t, "Simulación GTAP: subsidio de Brasil a 4 sectores (*)",
           "Los sectores subsidiados caen; recortar el subsidio en 1/3 amortigua la caída en ~25 %.")
    fig.text(0.27, 0.83, "■  S1: subsidio del 10 %", color=t["s1"], fontsize=10.5)
    fig.text(0.55, 0.83, "■  S3: subsidio recortado en 1/3", color=t["s2"], fontsize=10.5)
    guardar(fig, "gtap", modo)

print("Listo:", sorted(p.name for p in IMG.glob("*.png")))
