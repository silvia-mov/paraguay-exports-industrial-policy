   * ******************************************************************** *
   *   WILD CLUSTER BOOTSTRAP DE LA ECUACIÓN (6)                          *
   *                                                                      *
   *   Complemento de 7_pais_robustez.do. boottest no funciona        *
   *   después de reghdfe con más de un efecto fijo absorbido, así que    *
   *   aquí se estima la MISMA ecuación con areg: absorbe el importador   *
   *   y pone año y sector como dummies. Los coeficientes son idénticos   *
   *   a los de reghdfe con keepsingletons.                               *
   * ******************************************************************** *
   * Requiere: boottest instalado; correr en la misma carpeta que el 7.

	version 19
	clear all
	set more off
	set varabbrev off

	* <<< CAMBIAR: carpeta donde está la muestra (la guarda python/10_extra.py en 5_Tables) >>>
	global pry "C:/ruta/a/5_Tables"
	global muestra "PRY_muestra_stata_v2"

	cd "$pry"
	capture log close
	log using "$pry/$muestra-boottest.log", text replace
	use "$pry/$muestra.dta", clear

	local merc = 4/12
	gen byte umbral  = EXPORTS > 1000
	gen byte sin_out = EXP_GROWTH > -200 & EXP_GROWTH < 200

	local y1 "EXP_GROWTH"
	local c1 "umbral"
	local y2 "EXP_GROWTH"
	local c2 "umbral & sin_out"
	local y3 "ln_exp"
	local c3 "umbral"
	local y4 "EXP_GROWTH"
	local c4 "1"
	local y5 "EXP_GROWTH"
	local c5 "sin_out"
	local y6 "ln_exp"
	local c6 "1"

	forvalues e = 1/6 {
		di as txt _n "===== Esp`e': `y`e'' if `c`e'' ====="
		areg `y`e'' IP IP_RTA_SUBS i.year i.ISIC3_2 if `c`e'', absorb(IMP_CODE) vce(cluster IMP_CODE)
		* Coeficiente de profundidad y efecto para un socio del Mercosur
		boottest IP_RTA_SUBS, reps(9999) seed(20261018) nograph
		boottest {IP + `merc'*IP_RTA_SUBS = 0}, reps(9999) seed(20261018) nograph
	}

	log close
