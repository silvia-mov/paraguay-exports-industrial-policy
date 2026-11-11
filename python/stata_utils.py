"""
Funciones que replican comandos de Stata cuyo comportamiento no tiene un
equivalente exacto en pandas. Se usan en varios scripts del pipeline.
"""
import re
from collections.abc import Iterable, Sequence
from pathlib import Path

import numpy as np
import pandas as pd

# Etiquetas de la variable _merge que crea Stata
MERGE_LABELS = {
    1: "Master only (1)",
    2: "Using only (2)",
    3: "Matched (3)",
    4: "Missing updated (4)",
    5: "Nonmissing conflict (5)",
}


def _is_missing(s: pd.Series) -> pd.Series:
    """Missing al estilo Stata: NaN en números y "" (o NaN) en texto."""
    if pd.api.types.is_numeric_dtype(s):
        return s.isna()
    return s.isna() | (s.astype("string") == "")


def merge(
    master: pd.DataFrame,
    using: pd.DataFrame,
    on: str | Sequence[str],
    how: str,
    keep: Iterable[int] = (1, 2, 3, 4, 5),
    gen: str | None = "_merge",
    update: bool = False,
    replace: bool = False,
) -> pd.DataFrame:
    """Equivale a `merge {how} on using using, keep(...) [update replace] [nogen]`.

    - how: "1:1", "m:1" o "1:m". Falla si las llaves no son únicas donde
      corresponde, igual que Stata.
    - Si una variable (que no es llave) está en ambas bases, se conserva la
      del master; en las filas "using only" se usa la del using.
      Con update se rellenan los missing del master con el using (_merge=4);
      con replace, además, los valores no missing del using reemplazan a los
      del master (_merge=5).
    - keep: códigos de _merge que se conservan (1=master, 2=using, 3=match).
    - gen=None equivale a `nogen`.
    - El resultado queda ordenado por las llaves, como en Stata.
    """
    on = [on] if isinstance(on, str) else list(on)
    if replace and not update:
        raise ValueError("replace requiere update (igual que en Stata)")

    # Stata compara llaves numéricas por valor aunque el tipo sea distinto
    # (byte/int/long/double); pandas es más estricto, así que se igualan.
    # (copias livianas: solo se reemplazan columnas llave; con 15 millones de
    #  filas una copia completa agota la memoria)
    master, using = master.copy(deep=False), using.copy(deep=False)
    for k in on:
        a, b = master[k], using[k]
        if (pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(b)
                and a.dtype != b.dtype):
            master[k], using[k] = a.astype("float64"), b.astype("float64")
        elif isinstance(a.dtype, pd.CategoricalDtype) or isinstance(b.dtype, pd.CategoricalDtype):
            # llaves de texto guardadas como categorías (para ahorrar memoria):
            # mismas categorías en ambas bases, en orden alfabético
            cats = sorted(set(a.dropna().unique()) | set(b.dropna().unique()))
            tipo = pd.CategoricalDtype(cats)
            master[k], using[k] = a.astype(tipo), b.astype(tipo)

    common = [c for c in using.columns if c in master.columns and c not in on]
    out = master.merge(
        using, on=on, how="outer", validate=how, indicator="_m",
        suffixes=("", "__using"), sort=False,
    )
    code = out.pop("_m").map({"left_only": 1, "right_only": 2, "both": 3}).astype("int8")

    conflict = pd.Series(False, index=out.index)
    filled = pd.Series(False, index=out.index)
    for c in common:
        u = out.pop(c + "__using")
        m = out[c]
        # filas solo del using: todas sus variables vienen del using
        m = m.mask(code == 2, u)
        if update:
            matched = code == 3
            m_miss, u_ok = _is_missing(m), ~_is_missing(u)
            fill = matched & m_miss & u_ok
            diff = matched & ~m_miss & u_ok & (m != u)
            m = m.mask(fill, u)
            if replace:
                m = m.mask(diff, u)
            filled |= fill
            conflict |= diff
        out[c] = m
    if update:
        code = code.mask((code == 3) & filled, 4).mask((code == 3) & conflict, 5)

    out = out[code.isin(list(keep))]
    code = code[out.index]
    if gen:
        out[gen] = code
    return out.sort_values(on, kind="stable", na_position="last").reset_index(drop=True)


def destring(s: pd.Series) -> pd.Series:
    """`destring x, replace`: texto -> número; "" pasa a missing.

    Si hay caracteres no numéricos Stata no convierte la variable (y los
    merges siguientes fallarían); aquí se lanza un error explícito.
    """
    if pd.api.types.is_numeric_dtype(s):
        return s
    txt = s.astype("string").str.strip().replace("", pd.NA)
    return pd.to_numeric(txt, errors="raise").astype("float64")


def encode(s: pd.Series) -> tuple[pd.Series, dict[int, str]]:
    """`encode x, gen(x_code)`: códigos 1..n en orden alfabético + etiquetas."""
    if isinstance(s.dtype, pd.CategoricalDtype):
        # categorías: se codifica sobre las categorías (sin crear millones de textos)
        presentes = s.cat.remove_unused_categories()
        niveles = sorted(c for c in presentes.cat.categories if c != "")
        mapa = {v: i for i, v in enumerate(niveles, start=1)}
        codigos = pd.Series(presentes.cat.categories.map(lambda c: mapa.get(c, np.nan))
                            .to_numpy(dtype="float64")[presentes.cat.codes.to_numpy()],
                            index=s.index)
        codigos[presentes.cat.codes.to_numpy() < 0] = np.nan
    else:
        miss = _is_missing(s)
        niveles = sorted(s[~miss].unique())
        mapa = {v: i for i, v in enumerate(niveles, start=1)}
        codigos = s.map(mapa).where(~miss).astype("float64")
    if not codigos.isna().any():
        codigos = codigos.astype("int32")
    return codigos, {i: v for v, i in mapa.items()}


def ln(x: pd.Series) -> pd.Series:
    """`ln()` de Stata: missing (no -inf) cuando x <= 0."""
    return np.log(x.where(x > 0))


def value_labels_of(path: Path) -> dict[str, dict[int, str]]:
    """Etiquetas de valor de un .dta: {variable: {código: texto}}.

    pandas puede leerlas como categorías, pero al guardar renumera los
    códigos; para conservarlos como Stata se lee con
    convert_categoricals=False y se pasan estas etiquetas a save_dta().
    """
    import pyreadstat

    _, meta = pyreadstat.read_dta(str(path), metadataonly=True)
    return {var: {int(k): v for k, v in labs.items()}
            for var, labs in meta.variable_value_labels.items()}


def save_dta(df: pd.DataFrame, path: Path, value_labels=None, variable_labels=None) -> None:
    """`save path, replace` (formato Stata 14+, como el original)."""
    df = df.copy(deep=False)   # copia liviana: solo se reemplazan columnas de texto
    largos = []
    for c in df.columns:
        # categorías de texto (ahorro de memoria) -> texto, como en Stata
        # (sin crear millones de copias de cada texto: con 15 millones de
        #  filas eso agotaba la memoria)
        if isinstance(df[c].dtype, pd.CategoricalDtype) and not pd.api.types.is_numeric_dtype(
                df[c].cat.categories):
            col = df[c]
            if "" not in col.cat.categories:
                col = col.cat.add_categories("")
            df[c] = col.fillna("").astype(object)
        # en Stata el texto faltante es "", no NaN
        if not pd.api.types.is_numeric_dtype(df[c]) and not isinstance(df[c].dtype, pd.CategoricalDtype):
            col = df[c].astype(object)
            df[c] = col.where(col.notna(), "")
            # textos de más de 244 caracteres van como strL (p. ej. affectedproducts)
            if df[c].str.len().max() > 244:
                largos.append(c)
    df.to_stata(path, write_index=False, version=118, convert_strl=largos,
                value_labels=value_labels, variable_labels=variable_labels)


def save_dta_grande(df: pd.DataFrame, path: Path, value_labels=None) -> None:
    """`save path, replace` para bases muy grandes (p. ej. DataforRegressions).

    pandas.to_stata hace varias copias internas y con 15 millones de filas
    agota 15 GB de memoria; pyreadstat escribe en C y usa ~6 GB.
    Los textos faltantes se escriben como "" (como en Stata).
    """
    import pyreadstat

    for c in df.columns:
        if isinstance(df[c].dtype, pd.CategoricalDtype) or (
                not pd.api.types.is_numeric_dtype(df[c])):
            col = df[c].astype(object)
            df[c] = col.where(col.notna(), "")
    pyreadstat.write_dta(df, str(path), version=15,
                         variable_value_labels=value_labels or None)


def insheet(path: Path, max_bytes: int | None = 2045) -> pd.DataFrame:
    """`insheet using archivo.csv, clear`.

    - Nombres como Stata: sin espacios ni signos y en minúsculas; una columna
      sin nombre (el índice que agrega R al exportar) se llama v1, v2...
    - Tipos como Stata: una columna es numérica solo si TODOS sus valores no
      vacíos son números; si no, queda como texto (con "NA" y "" literales).
    - Bytes como Stata: GTA-OCT-23.csv mezcla UTF-8 con bytes de Windows-1252
      (p. ej. "Saint-Barthélemy" y "Réunion" en 85 filas). Stata los guarda tal
      cual y compara byte a byte, así que esos textos NO coinciden con los
      escritos en UTF-8 en el do-file. Aquí cada byte inválido se escribe
      escapado (p. ej. "Saint-Barth\\xe9lemy"): el texto sigue siendo único y
      tampoco coincide con el del do-file, igual que en Stata.
    - Largo como Stata: `insheet` guarda texto como str# y el máximo es
      str2045, así que CORTA en silencio todo texto de más de 2.045 bytes.
      En GTA-OCT-23.csv eso corta affectedproducts en 1.599 medidas de
      política industrial y 5.206 de barreras a la importación (el último
      código queda a medias). max_bytes=None conserva el texto completo.
    """
    df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8",
                     encoding_errors="backslashreplace")
    if max_bytes is not None:
        for c in df.columns:
            largo = df[c].str.len() > max_bytes // 4   # candidatos (barato)
            if largo.any():
                df.loc[largo, c] = df.loc[largo, c].map(
                    lambda x: x.encode("utf-8")[:max_bytes].decode("utf-8", "ignore"))
    nombres = []
    for i, c in enumerate(df.columns, start=1):
        n = re.sub(r"[^a-z0-9_]", "", str(c).lower())
        nombres.append(f"v{i}" if n == "" or n.startswith("unnamed") else n)
    df.columns = nombres
    for c in df.columns:
        txt = df[c].str.strip()
        num = pd.to_numeric(txt.replace("", np.nan), errors="coerce")
        if num.notna().sum() == (txt != "").sum():
            df[c] = num
    return df


def order(df: pd.DataFrame, primero: list[str]) -> pd.DataFrame:
    """`order varlist`: estas columnas primero (acepta comodines *x), el resto
    después en su orden actual."""
    cols = []
    for patron in primero:
        regex = "^" + re.escape(patron).replace(r"\*", ".*") + "$"
        cols += [c for c in df.columns if re.match(regex, c) and c not in cols]
    return df[cols + [c for c in df.columns if c not in cols]]


# ----------------------------------------------------------------------
# Regresiones: lincom y tablas al estilo estout
# ----------------------------------------------------------------------
def lincom(fit, pesos: dict[str, float]) -> dict[str, float]:
    """`lincom IP + 0.5*IP_RTA_SUBS` -> lincom(fit, {"IP": 1, "IP_RTA_SUBS": 0.5}).

    Usa la matriz de varianzas del modelo (cluster) y una t con los mismos
    grados de libertad que reghdfe (G-1).
    """
    from scipy import stats

    nombres = list(fit._coefnames)
    r = np.array([pesos.get(n, 0.0) for n in nombres])
    est = float(r @ fit.coef().to_numpy())
    se = float(np.sqrt(r @ fit._vcov @ r))
    df = float(fit._df_t)
    t = est / se
    q = stats.t.ppf(0.975, df)
    return {"estimate": est, "se": se, "t": t, "p": 2 * stats.t.sf(abs(t), df),
            "ci_low": est - q * se, "ci_high": est + q * se, "df": df}


def _stars(p: float) -> str:
    # starlevels(* 0.10 ** 0.05 *** 0.01)
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""


def estout(models: dict, keep: list[str] | None = None, rename: dict[str, str] | None = None,
           path: Path | None = None) -> pd.DataFrame:
    """`estout m*, k(...) cells(b(star fmt(%9.3f)) se(par)) stats(r2 N)`.

    Devuelve la tabla como DataFrame, la imprime y, si se da `path`, la guarda
    en .tex (tabular de LaTeX) y en .csv.
    keep: filas a mostrar, en ese orden (None = todos los coeficientes).
    rename: nombres a mostrar para los coeficientes.
    """
    rename = rename or {}
    if keep is None:
        keep = list(dict.fromkeys(c for m in models.values() for c in m._coefnames))
    filas = {}
    for var in keep:
        b, s = [], []
        for m in models.values():
            if var in m._coefnames:
                b.append(f"{m.coef()[var]:.3f}{_stars(m.pvalue()[var])}")
                s.append(f"({m.se()[var]:.3f})")
            else:
                b.append("")
                s.append("")
        filas[rename.get(var, var)] = b
        filas[f"{rename.get(var, var)} (se)"] = s
    filas["R-squared"] = [f"{m._r2:.3f}" for m in models.values()]
    filas["N"] = [f"{m._N:d}" for m in models.values()]
    tabla = pd.DataFrame(filas, index=list(models)).T
    print(tabla.to_string())
    print("* p<0.10, ** p<0.05, *** p<0.01")

    if path is not None:
        tabla.to_csv(Path(path).with_suffix(".csv"))
        tex = lambda x: str(x).replace("_", r"\_").replace("&", r"\&")
        lineas = [r"\begin{tabular}{l*{%d}{c}}" % len(models), r"\hline",
                  " & ".join([""] + [tex(m) for m in models]) + r" \\", r"\hline"]
        for nombre, fila in tabla.iterrows():
            etiqueta = "" if nombre.endswith(" (se)") else tex(nombre)
            if nombre == "R-squared":
                lineas.append(r"\hline")
            lineas.append(" & ".join([etiqueta] + list(fila)) + r" \\")
        lineas += [r"\hline",
                   r"\multicolumn{%d}{l}{\footnotesize * p$<$0.10, ** p$<$0.05, *** p$<$0.01}\\" % (len(models) + 1),
                   r"\end{tabular}"]
        Path(path).with_suffix(".tex").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return tabla
