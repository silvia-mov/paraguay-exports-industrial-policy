"""Datos de la página web (docs/datos_pagina.js) a partir de los CSV de esta carpeta.

Uso (desde la raíz del repositorio):
    python resultados/datos_pagina.py

La página (docs/index.html) solo dibuja; todos los números salen de aquí.
"""
import json
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).resolve().parent
DESTINO = AQUI.parent / "docs" / "datos_pagina.js"

# Por qué se hizo cada prueba y qué mostró (resumen de docs/robustez.md)
PRUEBAS = {
    "Errores agrupados por importador (base)": (
        "Base", "Es la estimación principal: los errores se agrupan por país de destino, porque las exportaciones a un "
        "mismo país se parecen entre sí.", ""),
    "Bootstrap salvaje (9.999 repeticiones)": (
        "Bootstrap salvaje", "Solo tres socios (los del MERCOSUR) tienen reglas sobre subsidios en los datos. Con tan pocos, "
        "los errores habituales suelen salir demasiado chicos; el bootstrap recalcula el p-valor sin depender de eso.", ""),
    "Sorteo de socios placebo (1.999)": (
        "Sorteo de socios", "Si se le asignara el acuerdo a tres socios al azar, ¿qué tan seguido saldría un resultado tan "
        "grande como el real? Si es raro, el resultado no es casualidad.", ""),
    "Errores agrupados por importador y año": (
        "Por importador y año", "Hay golpes que afectan a todos los destinos el mismo año, como la pandemia de 2020. "
        "Esta prueba los tiene en cuenta.", ""),
    "Sin Brasil": (
        "Sin Brasil", "Brasil pesa entre el 50 % y el 80 % de la información. ¿El resultado es del MERCOSUR o solo de Brasil?", ""),
    "Efectos fijos de producto": (
        "Mismo producto", "Compara el mismo producto antes y después de la medida, en lugar de productos distintos entre sí.", ""),
    "Efectos fijos de importador por producto": (
        "Mismo destino y producto", "Lo mismo, pero para cada combinación de destino y producto: es lo que hace el estudio original.", ""),
    "Bootstrap del efecto neto del Mercosur": (
        "Efecto neto MERCOSUR", "Ésta no mide el escudo sino algo más: si con un socio del MERCOSUR las exportaciones "
        "llegan a subir. Se prueba con bootstrap, por los pocos socios.", ""),
}
RESULTADO = {
    ("Tasa de crecimiento", "Errores agrupados por importador (base)"): "Significativo: con más reglas sobre subsidios, la medida perjudica menos.",
    ("Tasa de crecimiento", "Bootstrap salvaje (9.999 repeticiones)"): "Sigue significativo al 5 %.",
    ("Tasa de crecimiento", "Sorteo de socios placebo (1.999)"): "El resultado real es raro bajo el azar: no es casualidad.",
    ("Tasa de crecimiento", "Errores agrupados por importador y año"): "Queda justo en el límite (5 %); significativo al 10 %.",
    ("Tasa de crecimiento", "Sin Brasil"): "Se mantiene sin Brasil, aunque más chico.",
    ("Tasa de crecimiento", "Efectos fijos de producto"): "Se hace más fuerte: no es un efecto de qué productos se exportan.",
    ("Tasa de crecimiento", "Efectos fijos de importador por producto"): "También se mantiene, como en el estudio original.",
    ("Tasa de crecimiento", "Bootstrap del efecto neto del Mercosur"): "No resiste: el MERCOSUR protege (el efecto neto no es negativo), pero no se puede afirmar que haga subir las exportaciones.",
    ("Logaritmo", "Errores agrupados por importador (base)"): "Significativo en la estimación base.",
    ("Logaritmo", "Bootstrap salvaje (9.999 repeticiones)"): "Pierde fuerza: significativo solo al 10 %.",
    ("Logaritmo", "Sorteo de socios placebo (1.999)"): "Raro bajo el azar.",
    ("Logaritmo", "Errores agrupados por importador y año"): "Se mantiene.",
    ("Logaritmo", "Sin Brasil"): "Se mantiene sin Brasil.",
    ("Logaritmo", "Efectos fijos de producto"): "Desaparece: en logaritmo, el resultado reflejaba qué productos se exportan a cada socio, no el efecto de las medidas.",
    ("Logaritmo", "Efectos fijos de importador por producto"): "Desaparece, por la misma razón.",
    ("Logaritmo", "Bootstrap del efecto neto del Mercosur"): "No resiste.",
}


def main():
    med = pd.read_csv(AQUI / "medidas_por_anio.csv")
    medidas = {"anios": med["Año"].tolist(),
               "paises": {c: med[c].tolist() for c in med.columns if c != "Año"}}

    ex = pd.read_csv(AQUI / "exportaciones_alcanzadas.csv").sort_values("Exportaciones alcanzadas (%)", ascending=False)
    exposicion = [{"p": r["País"], "v": float(r["Exportaciones alcanzadas (%)"]),
                   "a": float(r["Exportaciones alcanzadas (millones de USD)"]),
                   "t": float(r["Exportaciones totales (millones de USD)"]),
                   "prod": r["Producto principal alcanzado"] if isinstance(r["Producto principal alcanzado"], str) else ""}
                  for _, r in ex.iterrows()]

    ec6 = pd.read_csv(AQUI / "paraguay_ec6.csv").set_index("Especificación")
    especificaciones = {}
    for clave, fila, que, unidad, dec, paso in (
            ("crec", "Robustez: tasa de crecimiento", "el crecimiento de las exportaciones paraguayas de ese producto",
             "puntos porcentuales", 2, 10),
            ("log", "Principal: logaritmo (sin umbral)", "el valor exportado de ese producto (en logaritmo)",
             "unidades de logaritmo", 3, 0.5)):
        r = ec6.loc[fila]
        v1, v2, vm = r["se_IP"] ** 2, r["se_SUBS"] ** 2, r["Mercosur_se"] ** 2
        # Var(b1 + b2/3) = v1 + v2/9 + 2c/3  ->  covarianza c entre b1 y b2
        c = (vm - v1 - v2 / 9) * 1.5
        especificaciones[clave] = {"b1": r["b_IP"], "b2": r["b_SUBS"], "v1": v1, "v2": v2, "c": c,
                                   "que": que, "unidad": unidad, "dec": dec, "paso": paso}

    inf = pd.read_csv(AQUI / "paraguay_inferencia.csv")
    robustez = []
    for _, r in inf[inf["Especificación"].isin(["Tasa de crecimiento", "Logaritmo"])].iterrows():
        corto, duda, _ = PRUEBAS[r["Prueba"]]
        robustez.append({"e": r["Especificación"], "t": r["Prueba"], "corto": corto, "p": float(r["p"]),
                         "duda": duda, "res": RESULTADO[(r["Especificación"], r["Prueba"])]})

    g = pd.read_csv(AQUI / "gtap_por_sector.csv")
    s1 = g[g["Escenario"] == "S1"].set_index("Sector")
    s3 = g[g["Escenario"] == "S3"].set_index("Sector")
    gtap = [{"s": s, "sub": str(s1.loc[s, "Subsidiado"]) == "True", "s1": float(s1.loc[s, "Variación (%)"]),
             "s3": float(s3.loc[s, "Variación (%)"])} for s in s1.sort_values("Variación (%)").index]

    datos = {"medidas": medidas, "exposicion": exposicion, "especificaciones": especificaciones,
             "robustez": robustez, "gtap": gtap}
    DESTINO.write_text("// Generado por resultados/datos_pagina.py a partir de resultados/*.csv\nconst DATOS = "
                       + json.dumps(datos, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
    print("Listo:", DESTINO)


if __name__ == "__main__":
    main()
