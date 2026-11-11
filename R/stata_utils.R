# Funciones que replican comandos de Stata cuyo comportamiento no tiene un
# equivalente exacto en dplyr. Se usan en varios scripts del pipeline:
#   source(here::here("R", "stata_utils.R"))

library(dplyr)

# Etiquetas de la variable _merge que crea Stata
merge_labels <- c("Master only (1)" = 1, "Using only (2)" = 2, "Matched (3)" = 3,
                  "Missing updated (4)" = 4, "Nonmissing conflict (5)" = 5)

# Missing al estilo Stata: NA en números y "" (o NA) en texto
is_missing_stata <- function(x) {
  if (is.character(x)) is.na(x) | x == "" else is.na(x)
}

# Equivale a `merge {how} on using using, keep(...) [update replace] [nogen]`
#  - how: "1:1", "m:1" o "1:m" (falla si las llaves no son únicas, como Stata)
#  - Si una variable (no llave) está en ambas bases, se conserva la del
#    master; en las filas "using only" se usa la del using. Con update se
#    rellenan los missing del master (_merge=4); con replace además los
#    valores no missing del using reemplazan a los del master (_merge=5).
#  - keep: códigos de _merge a conservar. gen = NULL equivale a nogen.
#  - El resultado queda ordenado por las llaves, como en Stata.
stata_merge <- function(master, using, by, how, keep = 1:5, gen = "_merge",
                        update = FALSE, replace = FALSE) {
  if (replace && !update) stop("replace requiere update (igual que en Stata)")
  relationship <- c("1:1" = "one-to-one", "m:1" = "many-to-one",
                    "1:m" = "one-to-many")[[how]]
  # Valida unicidad de las llaves como Stata (dplyr solo avisaría)
  if (how %in% c("1:1", "m:1") && anyDuplicated(using[by]))
    stop("variables ", paste(by, collapse = " "), " no identifican el using")
  if (how %in% c("1:1", "1:m") && anyDuplicated(master[by]))
    stop("variables ", paste(by, collapse = " "), " no identifican el master")

  # Stata compara llaves numéricas por valor aunque el tipo difiera
  for (k in by) {
    if (is.numeric(master[[k]]) && is.numeric(using[[k]]) &&
        !identical(class(master[[k]]), class(using[[k]]))) {
      master[[k]] <- as.double(master[[k]])
      using[[k]]  <- as.double(using[[k]])
    }
  }

  common <- setdiff(intersect(names(master), names(using)), by)
  master$.in_master <- TRUE
  using$.in_using <- TRUE
  out <- full_join(master, using, by = by, suffix = c("", "__using"),
                   relationship = relationship, na_matches = "na")
  code <- ifelse(is.na(out$.in_using), 1L, ifelse(is.na(out$.in_master), 2L, 3L))

  filled <- conflict <- rep(FALSE, nrow(out))
  for (c in common) {
    u <- out[[paste0(c, "__using")]]
    m <- out[[c]]
    m[code == 2L] <- u[code == 2L]   # filas solo del using
    if (update) {
      m_miss <- is_missing_stata(m)
      u_ok <- !is_missing_stata(u)
      fill <- code == 3L & m_miss & u_ok
      diff <- code == 3L & !m_miss & u_ok & (m != u)
      diff[is.na(diff)] <- FALSE
      m[fill] <- u[fill]
      if (replace) m[diff] <- u[diff]
      filled <- filled | fill
      conflict <- conflict | diff
    }
    out[[c]] <- m
    out[[paste0(c, "__using")]] <- NULL
  }
  if (update) {
    code[code == 3L & filled] <- 4L
    code[code == 3L & conflict] <- 5L
  }
  out$.in_master <- NULL
  out$.in_using <- NULL

  quedan <- code %in% keep
  out <- out[quedan, , drop = FALSE]
  if (!is.null(gen)) out[[gen]] <- code[quedan]
  arrange(out, across(all_of(by)))   # arrange es estable y deja NA al final
}

# `destring x, replace`: texto -> número; "" pasa a NA.
# Si hay caracteres no numéricos Stata no convierte (y los merges
# siguientes fallarían); aquí se lanza un error explícito.
destring <- function(x) {
  if (is.numeric(x)) return(x)
  x <- trimws(x)
  x[x == ""] <- NA
  num <- suppressWarnings(as.numeric(x))
  malos <- !is.na(x) & is.na(num)
  if (any(malos)) stop("destring: valores no numéricos, p. ej. '", x[malos][1], "'")
  num
}

# `encode x, gen(x_code)`: códigos 1..n en orden alfabético (locale "C",
# como Stata) con etiquetas de valor
encode <- function(x) {
  x[x == ""] <- NA
  niveles <- sort(unique(x[!is.na(x)]), method = "radix")
  haven::labelled(match(x, niveles), labels = setNames(seq_along(niveles), niveles))
}

# `ln()` de Stata: NA (no -Inf) cuando x <= 0
ln_stata <- function(x) {
  out <- rep(NA_real_, length(x))
  ok <- !is.na(x) & x > 0
  out[ok] <- log(x[ok])
  out
}


# ----------------------------------------------------------------------
# Regresiones: singletons, lincom y tablas al estilo estout
# ----------------------------------------------------------------------

# reghdfe elimina los singletons de forma ITERATIVA (quitar uno puede crear
# otro). fixest::feols(fixef.rm = "singleton") lo hace en una sola pasada,
# así que se hace aquí a mano para que N coincida con Stata.
# fe: texto con los efectos fijos, p. ej. "A^B^C + D^E"
drop_singletons <- function(data, fe) {
  grupos <- lapply(trimws(strsplit(fe, "+", fixed = TRUE)[[1]]), function(term) {
    vctrs::vec_group_id(data[trimws(strsplit(term, "^", fixed = TRUE)[[1]])])
  })
  keep <- rep(TRUE, nrow(data))
  repeat {
    cambio <- FALSE
    for (id in grupos) {
      n_por_grupo <- tabulate(id[keep], nbins = max(id))
      single <- keep & n_por_grupo[id] == 1L
      if (any(single)) {
        keep[single] <- FALSE
        cambio <- TRUE
      }
    }
    if (!cambio) break
  }
  data[keep, , drop = FALSE]
}

# `lincom IP + 0.5*IP_RTA_SUBS` -> lincom(fit, c(IP = 1, IP_RTA_SUBS = 0.5))
# t con los mismos grados de libertad que reghdfe con cluster (G-1)
lincom <- function(fit, pesos) {
  b <- coef(fit)
  r <- setNames(rep(0, length(b)), names(b))
  r[names(pesos)] <- pesos
  est <- sum(r * b)
  se <- sqrt(drop(t(r) %*% vcov(fit) %*% r))
  df <- fixest::degrees_freedom(fit, "t")
  q <- qt(0.975, df)
  tval <- est / se
  data.frame(estimate = est, se = se, t = tval, p = 2 * pt(-abs(tval), df),
             ci_low = est - q * se, ci_high = est + q * se, df = df)
}

stars <- function(p) ifelse(p < 0.01, "***", ifelse(p < 0.05, "**", ifelse(p < 0.10, "*", "")))

# `estout m*, k(...) cells(b(star fmt(%9.3f)) se(par)) stats(r2 N)`
# Imprime la tabla y, si se da `path`, la guarda en .tex y .csv.
# keep: filas a mostrar en ese orden (NULL = todos); rename: nombres a mostrar.
estout <- function(models, keep = NULL, rename = NULL, path = NULL) {
  if (is.null(keep)) keep <- unique(unlist(lapply(models, function(m) names(coef(m)))))
  nombre <- function(v) if (!is.null(rename) && v %in% names(rename)) rename[[v]] else v
  filas <- list()
  for (v in keep) {
    b <- s <- character(length(models))
    for (k in seq_along(models)) {
      m <- models[[k]]
      if (v %in% names(coef(m))) {
        b[k] <- sprintf("%.3f%s", coef(m)[[v]], stars(fixest::pvalue(m)[[v]]))
        s[k] <- sprintf("(%.3f)", fixest::se(m)[[v]])
      }
    }
    filas[[nombre(v)]] <- b
    filas[[paste(nombre(v), "(se)")]] <- s
  }
  filas[["R-squared"]] <- sapply(models, function(m) sprintf("%.3f", fixest::r2(m, "r2")))
  filas[["N"]] <- sapply(models, function(m) sprintf("%d", nobs(m)))
  tabla <- do.call(rbind, filas)
  colnames(tabla) <- names(models)
  print(noquote(tabla))
  cat("* p<0.10, ** p<0.05, *** p<0.01\n")

  if (!is.null(path)) {
    write.csv(tabla, paste0(path, ".csv"))
    tex <- function(x) gsub("&", "\\&", gsub("_", "\\_", x, fixed = TRUE), fixed = TRUE)
    lineas <- c(sprintf("\\begin{tabular}{l*{%d}{c}}", length(models)), "\\hline",
                paste(c("", tex(names(models))), collapse = " & ") |> paste("\\\\"), "\\hline")
    for (i in seq_len(nrow(tabla))) {
      fila <- rownames(tabla)[i]
      if (fila == "R-squared") lineas <- c(lineas, "\\hline")
      etiqueta <- if (endsWith(fila, " (se)")) "" else tex(fila)
      lineas <- c(lineas, paste(paste(c(etiqueta, tabla[i, ]), collapse = " & "), "\\\\"))
    }
    lineas <- c(lineas, "\\hline",
                sprintf("\\multicolumn{%d}{l}{\\footnotesize * p$<$0.10, ** p$<$0.05, *** p$<$0.01}\\\\",
                        length(models) + 1),
                "\\end{tabular}")
    writeLines(lineas, paste0(path, ".tex"))
  }
  invisible(tabla)
}


# ----------------------------------------------------------------------
# Importar como Stata
# ----------------------------------------------------------------------

# `insheet using archivo.csv, clear`
#  - Nombres como Stata: sin espacios ni signos y en minúsculas; una columna
#    sin nombre (el índice que agrega R al exportar) se llama v1, v2...
#  - Tipos como Stata: una columna es numérica solo si TODOS sus valores no
#    vacíos son números; si no, queda como texto (con "NA" y "" literales).
insheet <- function(path) {
  df <- read.csv(path, colClasses = "character", na.strings = character(0),
                 check.names = FALSE, fileEncoding = "UTF-8")
  n <- gsub("[^a-z0-9_]", "", tolower(names(df)))
  vacios <- n == "" | startsWith(n, "unnamed")
  n[vacios] <- paste0("v", which(vacios))
  names(df) <- n
  for (c in names(df)) {
    txt <- trimws(df[[c]])
    num <- suppressWarnings(as.numeric(ifelse(txt == "", NA, txt)))
    if (sum(!is.na(num)) == sum(txt != "")) df[[c]] <- num
  }
  tibble::as_tibble(df)
}

# `order varlist`: estas columnas primero (acepta comodines *x), el resto después
order_stata <- function(df, primero) {
  cols <- character(0)
  for (patron in primero) {
    regex <- paste0("^", gsub("*", ".*", gsub(".", "\\.", patron, fixed = TRUE), fixed = TRUE), "$")
    cols <- union(cols, grep(regex, names(df), value = TRUE))
  }
  df[c(cols, setdiff(names(df), cols))]
}

# Marca un texto escrito con \uXXXX como UTF-8. Sin esto, en sesiones con
# locale "C" (p. ej. Rscript en un servidor) "Türkiye" no es == al
# mismo texto leído de un .dta y el merge falla en silencio.
utf8 <- function(x) {
  Encoding(x) <- "UTF-8"
  x
}
