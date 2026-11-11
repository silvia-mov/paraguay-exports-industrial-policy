"""
* *********************************************************************
*
*       FIGURES  (traducción de 6-Figures.do)
*
* *********************************************************************

Entradas: $data_raw/GTA_NIPO.xlsx, $data_raw/Standard Report - Imports.csv
          $data_aux/Classification-economies-21.dta, GDP-21.dta
          $data_temp/GTA_cleaned.dta  (de 2-DataPrepare_GTA_PT1)
          $tables/lincom.csv          (de 5-Regressions, para la Figura 3)
Salidas:  $figures/BMT_Fig_n.pdf / .png / .jpg  y  BMT_Fig_n_data.csv
          (el .csv es la "vista de tabla" con los datos de cada gráfico)

graph save (.gph) no tiene equivalente: el .csv permite rehacer el gráfico.
Colores: paleta categórica validada (apta para daltonismo) + tipos de línea
distintos por serie, como en el original, para no depender solo del color.
"""
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config import DATA_AUX, DATA_RAW, DATA_TEMP, FIGURES, TABLES
from stata_utils import merge

# ----------------------------------------------------------------------
# Estilo común
# ----------------------------------------------------------------------
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
INK, INK_2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": INK_2, "axes.labelcolor": INK,
    "xtick.color": INK_2, "ytick.color": INK_2, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.8, "legend.frameon": False, "lines.linewidth": 2,
})


def guardar(fig, nombre: str, datos: pd.DataFrame) -> None:
    """graph save / graph export .pdf .jpg .png (+ datos en .csv)"""
    for ext in ("pdf", "png", "jpg"):
        fig.savefig(FIGURES / f"BMT_Fig_{nombre}.{ext}", dpi=200, bbox_inches="tight")
    datos.to_csv(FIGURES / f"BMT_Fig_{nombre}_data.csv", index=False)
    plt.close(fig)
    print(f"Figura {nombre} guardada")


def rotar(ax) -> None:
    """xlabel(..., angle(45)): etiquetas rotadas y alineadas con su marca."""
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")


def stata_names(df: pd.DataFrame, lower: bool = False) -> pd.DataFrame:
    """Nombres de variable como los crea Stata al importar:
    `import excel, firstrow` quita espacios y signos;
    `import delimited` además los pasa a minúsculas."""
    nuevos = [re.sub(r"[^A-Za-z0-9_]", "", str(c)) for c in df.columns]
    return df.set_axis([c.lower() for c in nuevos] if lower else nuevos, axis=1)


def col(df: pd.DataFrame, nombre: str) -> str:
    """Columna cuyo nombre empieza con `nombre` (Stata puede truncar nombres
    largos, p. ej. Initialassessmentchangerelat)."""
    c = [x for x in df.columns if x.startswith(nombre)]
    if len(c) != 1:
        raise KeyError(f"No hay una única columna que empiece con {nombre!r}: {c}")
    return c[0]


# **# FIGURE 1 -------------------------------------------------------------------
# New Ind policies and GDP per capita
def figura_1() -> None:
    # import excel "$data_raw/GTA_NIPO.xlsx", sheet("GTA NIPO - December 2023") firstrow clear
    nipo = stata_names(pd.read_excel(DATA_RAW / "GTA_NIPO.xlsx",
                                     sheet_name="GTA NIPO - December 2023"))
    nipo = nipo.rename(columns={col(nipo, "Initialassessmentchangerelat"): "assessment",
                                col(nipo, "SizeofsubsidyUSDmillion"): "size_usd"})
    nipo["size_usd"] = pd.to_numeric(nipo["size_usd"], errors="coerce").astype("float64")
    # keep if Initialassessmentchangerelat=="Distortive"
    nipo = nipo[nipo["assessment"] == "Distortive"].copy()

    # gsort -SizeofsubsidyUSDmillion
    # replace SizeofsubsidyUSDmillion = 622.560 in 1
    # (typo confirmado por los autores: 622 millones, no miles de millones.
    #  gsort deja los missing al final, así que la fila 1 es el máximo.)
    nipo = nipo.sort_values("size_usd", ascending=False, na_position="last", kind="stable")
    nipo.iloc[0, nipo.columns.get_loc("size_usd")] = 622.560

    # gen year=year(Implementationdate) / keep if year==2023
    nipo["year"] = pd.to_datetime(nipo["Implementationdate"], errors="coerce").dt.year
    nipo = nipo[nipo["year"] == 2023]

    # replace Jurisdiction="..." if Jurisdiction=="..."  (nombres del Banco Mundial)
    nipo["Jurisdiction"] = nipo["Jurisdiction"].replace({
        "United States of America": "United States", "Egypt": "Egypt, Arab Rep.",
        "Hong Kong": "Hong Kong SAR, China", "Russia": "Russian Federation",
        "Turkey": "Türkiye", "Republic of Korea": "Korea, Rep."})

    # merge m:1 Jurisdiction using Classification-economies-21 / drop if _merge==2
    clas = pd.read_stata(DATA_AUX / "Classification-economies-21.dta", convert_categoricals=False)
    nipo = merge(nipo, clas, on="Jurisdiction", how="m:1")
    sin_match = sorted(nipo.loc[nipo["_merge"] == 1, "Jurisdiction"].dropna().unique())
    print("  Jurisdicciones sin clasificación (tab ... if _merge==1):", sin_match)
    nipo = nipo[nipo["_merge"] != 2]

    # bysort Jurisdiction: egen IP_measure_country=count(EntryID)
    # bysort Jurisdiction: egen IP_USD_country=sum(SizeofsubsidyUSDmillion)
    g = nipo.groupby("Jurisdiction", dropna=False)
    nipo["IP_measure_country"] = g[col(nipo, "EntryID")].transform("count")
    nipo["IP_USD_country"] = g["size_usd"].transform("sum")
    nipo["log_IP_measure_country"] = np.log(nipo["IP_measure_country"].where(nipo["IP_measure_country"] > 0))
    nipo["log_IP_USD_country"] = np.log(nipo["IP_USD_country"].where(nipo["IP_USD_country"] > 0))

    # keep Economy log_IP_measure_country log_IP_USD_country income(group) IP_measure_country IP_USD_country
    # duplicates drop Economy, force
    pais = nipo[["Economy", "log_IP_measure_country", "log_IP_USD_country", "incomegroup",
                 "IP_measure_country", "IP_USD_country"]].drop_duplicates("Economy")

    # merge 1:1 Economy using "$data_aux/GDP-21.dta", keep(3) nogen
    gdp = pd.read_stata(DATA_AUX / "GDP-21.dta", convert_categoricals=False)
    pais = merge(pais, gdp, on="Economy", how="1:1", keep=(3,), gen=None)

    # twoway (scatter ... if incomegroup=="High income") (scatter ... if incomegroup!="High income")
    #        (lfit ...) if log_IP_measure_country!=0
    # OJO: el `if` excluye a los países con UNA sola medida (ln(1)=0).
    d = pais[pais["log_IP_measure_country"] != 0].dropna(subset=["log_IP_measure_country", "ln_gdp_pc"])
    alto = d["incomegroup"] == "High income"
    fig, ax = plt.subplots(figsize=(9, 6))
    for mask, etiqueta, color in [(alto, "High Income", SERIES[0]), (~alto, "EMDE", SERIES[1])]:
        ax.scatter(d.loc[mask, "ln_gdp_pc"], d.loc[mask, "log_IP_measure_country"],
                   s=36, color=color, edgecolor="white", linewidth=1, label=etiqueta, zorder=3)
    for _, r in d.iterrows():   # mlabel(Economy)
        ax.annotate(r["Economy"], (r["ln_gdp_pc"], r["log_IP_measure_country"]),
                    xytext=(3, 3), textcoords="offset points", fontsize=7, color=INK_2)
    # lfit: recta MCO de y sobre x en la misma muestra
    b, a = np.polyfit(d["ln_gdp_pc"], d["log_IP_measure_country"], 1)
    xs = np.linspace(d["ln_gdp_pc"].min(), d["ln_gdp_pc"].max(), 50)
    ax.plot(xs, a + b * xs, color=INK, linewidth=1.5, label="Fitted values", zorder=2)
    ax.set(xlabel="GDP per Capita in 2021 (in logs)", ylabel="Number of measures 2023 (in logs)")
    # title(..., pos(12)) + legend(pos(12) rows(1)): título arriba y leyenda debajo
    fig.suptitle("New Industrial Policies: Measures vs. Development, 2023 (source: NIPO)", y=0.98)
    ax.legend(loc="lower center", ncol=3, bbox_to_anchor=(0.5, 1.0))
    fig.subplots_adjust(top=0.87)
    guardar(fig, "1", pais)


# **# FIGURE 2 -------------------------------------------------------------------
# Exports to the US, selected markets
MESES = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}


def figura_2() -> None:
    # import delimited "$data_raw/Standard Report - Imports.csv", clear / drop rateprovision
    imp = stata_names(pd.read_csv(DATA_RAW / "Standard Report - Imports.csv", thousands=","),
                      lower=True)
    imp = imp.drop(columns="rateprovision", errors="ignore")

    # year = real("20" + substr(time, 5, 2)); month según las 3 primeras letras
    # date_m = ym(year, month); drop if date_m==.
    # (month=0 si no es un mes válido -> ym() da missing -> se elimina)
    t = imp["time"].astype(str)
    year = pd.to_numeric("20" + t.str[4:6], errors="coerce")
    month = t.str[:3].map(MESES)
    imp = imp[year.notna() & month.notna()].copy()
    imp["date_m"] = pd.PeriodIndex.from_fields(year=year[imp.index].astype(int),
                                               month=month[imp.index].astype(int), freq="M")

    # replace country="Total" / "USMCA" / "ASEAN" if ...
    imp["country"] = imp["country"].replace({
        "World Total": "Total",
        "USMCA - U.S.-Mexico-Canada Agreement": "USMCA",
        "ASEAN - Association of Southeast Asian Nations": "ASEAN"})
    # rename customsvaluegenus EXP_0
    imp = imp.rename(columns={col(imp, "customsvalue"): "EXP_0"})

    # sort country date_m
    # bysort country: gen EXP_0_A = EXP_0 + EXP_0[_n-1] + ... + EXP_0[_n-11]
    # (suma móvil de 12 observaciones; missing en las 11 primeras de cada país)
    imp = imp.sort_values(["country", "date_m"], kind="stable").reset_index(drop=True)
    g = imp.groupby("country")["EXP_0"]
    imp["EXP_0_A"] = sum(g.shift(k) for k in range(12))
    # by country: gen obs=_n
    imp["obs"] = imp.groupby("country").cumcount() + 1
    # by country: gen EXP_0_A_index = 100*(EXP_0_A/EXP_0_A[18])   (obs 18 = 2018m6)
    base = imp.groupby("country")["EXP_0_A"].transform(lambda s: s.iloc[17] if len(s) >= 18 else np.nan)
    imp["EXP_0_A_index"] = 100 * imp["EXP_0_A"] / base

    # keep country date_m EXP_0_A_index obs / reshape wide ... / keep if obs>12
    wide = (imp[imp["obs"] > 12]
            .pivot(index="date_m", columns="country", values="EXP_0_A_index")
            .add_prefix("EXP_0_A_index").reset_index())

    fig, ax = plt.subplots(figsize=(9, 5.5))
    x = wide["date_m"].dt.to_timestamp()
    for pais, color, estilo in [("ASEAN", SERIES[0], "-"), ("China", SERIES[1], "-"),
                                ("Mexico", SERIES[2], "--"), ("Total", SERIES[3], "-.")]:
        ax.plot(x, wide[f"EXP_0_A_index{pais}"], color=color, linestyle=estilo, label=pais)
    # xline(702) xline(722) xline(751) -> 2018m7, 2020m3, 2022m8
    for fecha in ("2018-07", "2020-03", "2022-08"):
        ax.axvline(pd.Timestamp(fecha), color=INK, linewidth=1)
    ax.set(title="Total Export to US, by Origin (2018m6=100)", xlabel="",
           ylabel="Index (2018m6=100) of 12-months trailing sum")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=4)
    wide["date_m"] = wide["date_m"].astype(str)
    guardar(fig, "2", wide)


# **# FIGURE 3 -------------------------------------------------------------------
# Baseline results. No está en el do-file (los autores la armaron a mano con la
# Tabla 3). Se genera aquí con los resultados que guarda 5-Regressions.
def figura_3() -> None:
    lc = pd.read_csv(TABLES / "lincom.csv")
    lc = lc[lc["tabla"] == 3]
    filas = [("m1", "IP", "Average effect"),
             ("m2", "IP", "Non-member of PTA"),
             ("m2", "IP + IP_RTA", "Member of PTA"),
             ("m5", "IP + 0.5*IP_RTA_SUBS", "Member of deep PTA\n(PTA Depth = 0.5)")]
    d = pd.concat([lc[(lc["modelo"] == m) & (lc["lincom"] == e)].assign(efecto=n)
                   for m, e, n in filas], ignore_index=True)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(d["efecto"], d["estimate"], color=SERIES[0], width=0.55, zorder=2)
    ax.errorbar(d["efecto"], d["estimate"], yerr=[d["estimate"] - d["ci_low"], d["ci_high"] - d["estimate"]],
                fmt="none", ecolor=INK, capsize=5, linewidth=1.2, zorder=3)
    ax.axhline(0, color=INK, linewidth=1)
    ax.grid(axis="x", visible=False)
    ax.set(title="Effect of a new industrial policy on export growth (%)",
           ylabel="Coefficient and 95% CI")
    guardar(fig, "3", d.drop(columns=["efecto"]).assign(efecto=d["efecto"].str.replace("\n", " ")))


# **# FIGURES 5 y 6 --------------------------------------------------------------
def contar_intervenciones(gta: pd.DataFrame, por: list[str]) -> pd.DataFrame:
    """unique(interventionid), by(por + ISO_impl) gen(number_interventions)
    collapse (sum) number_interventions, by(por)

    `unique ..., by() gen()` deja el número de intervenciones distintas en UNA
    fila por grupo; collapse (sum) luego suma esos conteos sobre los países.
    """
    n = (gta.groupby(por + ["ISO_impl"], dropna=False)["interventionid"]
         .nunique(dropna=False).rename("number_interventions").reset_index())
    return n.groupby(por, dropna=False)["number_interventions"].sum().reset_index()


def figura_5(gta: pd.DataFrame) -> None:
    d = contar_intervenciones(gta, ["gtaevaluation", "inception_year"])
    r = d[d["gtaevaluation"] == 2].sort_values("inception_year")   # 2 = restrictivas (rojo GTA)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(r["inception_year"], r["number_interventions"], color=SERIES[0], linestyle=(0, (3, 2)))
    ax.set(ylabel="Number of restrictive measures", xlabel="Year",
           xticks=range(2009, 2023))
    rotar(ax)
    guardar(fig, "5", d)


def figura_6(gta: pd.DataFrame) -> None:
    d = contar_intervenciones(gta, ["gtaevaluation", "inception_year", "class_measure"])
    fig, ax = plt.subplots(figsize=(8, 5))
    for clase, etiqueta, color, estilo in [
            ("Exp_barriers", "Export barriers", SERIES[0], "-"),
            ("Imp_barriers", "Import barriers", SERIES[1], "--"),
            ("Ind_policy", "Industrial policy", SERIES[2], (0, (3, 2)))]:
        r = d[(d["gtaevaluation"] == 2) & (d["class_measure"] == clase)].sort_values("inception_year")
        ax.plot(r["inception_year"], r["number_interventions"], color=color, linestyle=estilo, label=etiqueta)
    ax.set(ylabel="Number of measures", xlabel="Year", xticks=range(2009, 2023))
    rotar(ax)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=3)
    guardar(fig, "6", d)


# **# FIGURE 7 -------------------------------------------------------------------
MAST = [("D", "Contingent trade-protective", SERIES[0], (0, (3, 2))),
        ("I", "Trade-related investment", SERIES[1], "--"),
        ("M", "Government procurement", SERIES[2], "-."),
        ("E", "Non-automatic import licensing, quotas, prohibitions", SERIES[3], ":"),
        ("L", "Subsidies", SERIES[4], (0, (3, 2))),
        ("P", "Export-related", SERIES[5], (0, (8, 3)))]


def figura_7(gta: pd.DataFrame) -> None:
    gta = gta.copy()
    ch = gta["mastchapter"].fillna("")
    # gen MAST_code=substr(mastchapter,1,1) + reemplazos
    gta["MAST_code"] = ch.str[:1]
    gta.loc[ch.isin(["Instrument unclear", ""]), "MAST_code"] = "NS"
    gta.loc[ch.isin(["Capital control measures", "Tariff measures"]), "MAST_code"] = "TAR"
    gta.loc[ch == "FDI measures", "MAST_code"] = "FDI"
    gta.loc[ch == "Migration measures", "MAST_code"] = "MIG"

    por = ["MAST_code", "gtaevaluation", "inception_year"]
    # unique(interventionid), by(...) gen(...) + collapse (sum)
    d = (gta.groupby(por, dropna=False)["interventionid"].nunique(dropna=False)
         .rename("number_interventions").reset_index())

    # fillin MAST_code gtaevaluation inception_year / replace number_interventions=0 if _fillin==1
    completo = pd.MultiIndex.from_product([d[c].unique() for c in por], names=por).to_frame(index=False)
    d = completo.merge(d, on=por, how="left")
    d["number_interventions"] = d["number_interventions"].fillna(0)

    # egen num_code_year=std(number_interventions), by(gtaevaluation) -> num_sd
    # (no se grafica, pero queda en los datos como en el original)
    g = d.groupby("gtaevaluation", dropna=False)["number_interventions"]
    d["num_sd"] = (d["number_interventions"] - g.transform("mean")) / g.transform("std")

    # replace MA=subinstr(MA," ","_",.) / drop if inception_year==2008
    d["MAST_code"] = d["MAST_code"].str.replace(" ", "_")
    d = d[d["inception_year"] != 2008]

    # sort gtaevaluation MAST_code inception_year
    # bys ...: gen n1 = n - n[1]; replace n1 = n - n[2] if n1==.
    # -> diferencia respecto del primer año (2009): "Index [2009=0]"
    d = d.sort_values(["gtaevaluation", "MAST_code", "inception_year"], kind="stable", na_position="last")
    gg = d.groupby(["gtaevaluation", "MAST_code"], dropna=False)["number_interventions"]
    n1 = d["number_interventions"] - gg.transform("first")
    n2 = d["number_interventions"] - gg.transform(lambda s: s.iloc[1] if len(s) > 1 else np.nan)
    d["number_interventions"] = n1.fillna(n2)

    # reshape wide num*, i(gtaevaluation inception_year) j(MAST_code) string
    wide = d.pivot(index=["gtaevaluation", "inception_year"], columns="MAST_code",
                   values=["number_interventions", "num_sd"])
    wide.columns = [f"{v}{c}" for v, c in wide.columns]
    wide = wide.reset_index()

    for evaluacion, sufijo, ytitulo, paso in [(2, "A", "restrictive", 2), (1, "B", "liberalizing", 1)]:
        w = wide[wide["gtaevaluation"] == evaluacion].sort_values("inception_year")
        fig, ax = plt.subplots(figsize=(9, 6))
        for code, etiqueta, color, estilo in MAST:
            if f"number_interventions{code}" not in w:   # Stata daría error aquí
                print(f"  Aviso: no hay medidas del capítulo MAST {code}; se omite esa línea")
                continue
            ax.plot(w["inception_year"], w[f"number_interventions{code}"], color=color,
                    linestyle=estilo, label=etiqueta)
        for x in (2015, 2019, 2022):
            ax.axvline(x, color=INK, linewidth=1)
        ax.axhline(0, color=INK, linewidth=1)
        ax.set(ylabel=f"Index [2009=0] of {ytitulo} measures", xlabel="Year",
               xticks=range(2009, 2023, paso))
        rotar(ax)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=2, fontsize=8)
        guardar(fig, f"7{sufijo}", w)


# ----------------------------------------------------------------------
# Cada figura usa datos distintos: si falta un archivo se avisa y se sigue.
def correr(funcion, *args) -> None:
    try:
        funcion(*args)
    except FileNotFoundError as e:
        print(f"  Omitida {funcion.__name__}: falta {e.filename}")


correr(figura_1)
correr(figura_2)
correr(figura_3)
gta_file = DATA_TEMP / "GTA_cleaned.dta"
if gta_file.exists():
    gta = pd.read_stata(gta_file, convert_categoricals=False)
    correr(figura_5, gta)
    correr(figura_6, gta)
    correr(figura_7, gta)
else:
    print(f"  Omitidas figuras 5-7: falta {gta_file}")
