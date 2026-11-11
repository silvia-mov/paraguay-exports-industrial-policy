
   * ******************************************************************** *
   *                                                                      *
   *   ECUACIÓN (6) Y PRUEBAS DE ROBUSTEZ PARA UN PAÍS (por defecto PRY)  *
   *                                                                      *
   *   Confirmación en Stata de python/7_pais.py, 8_robustez.py,          *
   *   9_robustez_2.py y 10_extra.py                                      *
   *                                                                      *
   * ******************************************************************** *
   *
   * Datos: muestra del país exportador guardada por python/10_extra.py
   *   ({PAIS}_muestra_stata_v{VUELTA}.dta). La de la tesis se armó con
   *   TESIS_VUELTA=2 TESIS_SIN_TRUNCAR=1 TESIS_T_MENOS_1=1 (las 3 correcciones).
   * Para otro país: cambiar el nombre de la muestra y, en `local merc`, la
   * cobertura del acuerdo de referencia (la que imprime python/7_pais.py).
   *
   * Paquetes (instalar una sola vez si faltan; OJO: no reinstalar reghdfe
   * con ssc dentro de la carpeta ado del paquete del paper, porque reemplaza
   * las versiones que usaron los autores):
   *   ssc install boottest
   *   ssc install coefplot
   *   ssc install ppmlhdfe
   *   (reghdfe y ftools ya están instalados)

	version 19
	clear all
	set more off
	set varabbrev off

	* <<< CAMBIAR: carpeta donde está la muestra (la guarda python/10_extra.py en 5_Tables) >>>
	global pry "C:/ruta/a/5_Tables"
	* <<< ELEGIR LA VUELTA >>>
	global muestra "PRY_muestra_stata_v2"

	cd "$pry"
	capture log close
	log using "$pry/$muestra-robustez.log", text replace

	use "$pry/$muestra.dta", clear

	* Cobertura de subsidios del Mercosur (DTA): 4/12
	local merc = 4/12
	* Errores agrupados por importador; efectos fijos aditivos
	local fe   "IMP_CODE year ISIC3_2"
	local vce  "vce(cluster IMP_CODE)"
	* keepsingletons: mismo N que areg y que Python (no cambia los coeficientes)
	local opc  "keepsingletons"

	* Muestras (EXPORTS en miles de USD; umbral = USD 1 millón, nota 3 del paper)
	gen byte umbral  = EXPORTS > 1000
	gen byte sin_out = EXP_GROWTH > -200 & EXP_GROWTH < 200   // missing -> 0

	* Las 6 especificaciones (Esp1 a Esp6 de python/7_pais.py)
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


   * ---------------------------------------------------------------------
   * 1. Ecuación (6) y efecto Mercosur (lincom) + wild cluster bootstrap
   * ---------------------------------------------------------------------
	forvalues e = 1/6 {
		di as txt _n "===== Esp`e': `y`e'' if `c`e'' ====="
		reghdfe `y`e'' IP IP_RTA_SUBS if `c`e'', absorb(`fe') `vce' `opc'
		estimates store esp`e'
		* Efecto para un socio del Mercosur: IP + (1/3)*IP_RTA_SUBS
		lincom IP + `merc'*IP_RTA_SUBS
		* Wild cluster bootstrap (Roodman et al. 2019): coeficiente y efecto Mercosur.
		* boottest no funciona después de reghdfe con más de un efecto fijo absorbido,
		* así que se reestima la misma ecuación con areg (año y sector como dummies;
		* mismos coeficientes) solo para el bootstrap.
		quietly areg `y`e'' IP IP_RTA_SUBS i.year i.ISIC3_2 if `c`e'', absorb(IMP_CODE) vce(cluster IMP_CODE)
		boottest IP_RTA_SUBS, reps(9999) seed(20261018) nograph
		boottest {IP + `merc'*IP_RTA_SUBS = 0}, reps(9999) seed(20261018) nograph
	}
	* Tabla con las 6 especificaciones (estout ya está instalado)
	esttab esp1 esp2 esp3 esp4 esp5 esp6 using "$pry/$muestra-ec6.rtf", ///
		replace b(3) se(3) star(* 0.10 ** 0.05 *** 0.01) keep(IP IP_RTA_SUBS) ///
		stats(N r2_within, labels("N" "R2 within")) ///
		mtitles("Esp1" "Esp2" "Esp3 ln" "Esp4" "Esp5" "Esp6 ln")


   * ---------------------------------------------------------------------
   * 2. Prueba por sorteo (inferencia por aleatorización)
   *    Se asigna la cobertura del Mercosur (1/3) a 3 importadores al azar
   *    que no son del Mercosur y se compara el estadístico t (no el
   *    coeficiente; Lehmann y Romano 2022, §17.3).
   *    Tarda unos minutos por especificación.
   * ---------------------------------------------------------------------
	local sorteos 1999
	foreach e in 1 2 4 5 {
		di as txt _n "===== Sorteo Esp`e' ====="
		* importadores con alguna fila con IP = 1, fuera del Mercosur
		levelsof IMP if IP == 1 & `c`e'' & !missing(`y`e'') ///
			& !inlist(IMP, "ARG", "BRA", "URY"), local(pool) clean
		local npool : word count `pool'
		capture drop Z
		gen double Z = IP * cond(inlist(IMP, "ARG", "BRA", "URY"), `merc', 0)
		quietly reghdfe `y`e'' IP Z if `c`e'', absorb(`fe') `vce' `opc'
		local treal = _b[Z] / _se[Z]
		tempname sim
		postfile `sim' double t using "$pry/sorteo_esp`e'.dta", replace
		set seed 20261019
		forvalues r = 1/`sorteos' {
			local a = ceil(runiform() * `npool')
			local b = `a'
			while `b' == `a' {
				local b = ceil(runiform() * `npool')
			}
			local c = `a'
			while `c' == `a' | `c' == `b' {
				local c = ceil(runiform() * `npool')
			}
			local i1 : word `a' of `pool'
			local i2 : word `b' of `pool'
			local i3 : word `c' of `pool'
			quietly replace Z = IP * cond(inlist(IMP, "`i1'", "`i2'", "`i3'"), `merc', 0)
			capture quietly reghdfe `y`e'' IP Z if `c`e'', absorb(`fe') `vce' `opc'
			if !_rc post `sim' (_b[Z] / _se[Z])
		}
		postclose `sim'
		preserve
		use "$pry/sorteo_esp`e'.dta", clear
		quietly count if abs(t) >= abs(`treal') & !missing(t)
		local mayor = r(N)
		quietly count if !missing(t)
		di as res "Esp`e': t real = " %5.2f `treal' "  p sorteo = " ///
			%5.3f (1 + `mayor') / (1 + r(N)) "  (" r(N) " sorteos, " `npool' " importadores)"
		restore
		drop Z
	}


   * ---------------------------------------------------------------------
   * 3. Sacar un socio por vez (Brasil, Argentina, Uruguay)
   * ---------------------------------------------------------------------
	forvalues e = 1/6 {
		foreach fuera in ARG BRA URY {
			di as txt _n "===== Esp`e' sin `fuera' ====="
			quietly reghdfe `y`e'' IP IP_RTA_SUBS if `c`e'' & IMP != "`fuera'", ///
				absorb(`fe') `vce' `opc'
			lincom IP_RTA_SUBS
			lincom IP + `merc'*IP_RTA_SUBS
		}
	}


   * ---------------------------------------------------------------------
   * 4. Efectos fijos de producto (HS 6 dígitos) e importador × producto
   * ---------------------------------------------------------------------
	forvalues e = 1/6 {
		di as txt _n "===== Esp`e' con EF de producto ====="
		reghdfe `y`e'' IP IP_RTA_SUBS if `c`e'', absorb(IMP_CODE year HS2012) `vce'
		lincom IP + `merc'*IP_RTA_SUBS
		di as txt _n "===== Esp`e' con EF importador × producto ====="
		reghdfe `y`e'' IP IP_RTA_SUBS if `c`e'', absorb(IMP_CODE#HS2012 year) `vce'
		lincom IP + `merc'*IP_RTA_SUBS
	}


   * ---------------------------------------------------------------------
   * 5. Placebo F1 = prueba de exogeneidad estricta (Wooldridge 2010,
   *    §10.7.1) y estudio de eventos (adelantos t-2, t-1; rezagos t+1, t+2)
   * ---------------------------------------------------------------------
	foreach e in 1 2 3 4 {
		di as txt _n "===== Esp`e': placebo F1 ====="
		reghdfe `y`e'' IP IP_RTA_SUBS F1_IP F1_IP_RTA_SUBS if `c`e'' & year < 2022, ///
			absorb(`fe') `vce' `opc'

		di as txt _n "===== Esp`e': estudio de eventos 2014-2020 ====="
		reghdfe `y`e'' F2_IP F2_IP_RTA_SUBS F1_IP F1_IP_RTA_SUBS IP IP_RTA_SUBS ///
			L1_IP L1_IP_RTA_SUBS L2_IP L2_IP_RTA_SUBS ///
			if `c`e'' & inrange(year, 2014, 2020), absorb(`fe') `vce' `opc'
		test F2_IP_RTA_SUBS F1_IP_RTA_SUBS            // pre-tendencia conjunta
		lincom IP_RTA_SUBS + L1_IP_RTA_SUBS + L2_IP_RTA_SUBS   // acumulado t..t+2
		coefplot, keep(F2_IP_RTA_SUBS F1_IP_RTA_SUBS IP_RTA_SUBS L1_IP_RTA_SUBS L2_IP_RTA_SUBS) ///
			order(F2_IP_RTA_SUBS F1_IP_RTA_SUBS IP_RTA_SUBS L1_IP_RTA_SUBS L2_IP_RTA_SUBS) ///
			vertical yline(0) ciopts(recast(rcap)) ///
			coeflabels(F2_IP_RTA_SUBS = "t-2" F1_IP_RTA_SUBS = "t-1" IP_RTA_SUBS = "t" ///
				L1_IP_RTA_SUBS = "t+1" L2_IP_RTA_SUBS = "t+2") ///
			xtitle("Año respecto de la medida de política industrial") ///
			ytitle("Coef. de profundidad (IP_RTA_SUBS)") title("Paraguay - Esp`e'")
		graph export "$pry/$muestra-evento-esp`e'.png", replace width(1200)
	}


   * ---------------------------------------------------------------------
   * 6. Poisson con efectos fijos (PPML; Santos Silva y Tenreyro 2006)
   *    Efecto en %: 100*(exp(b)-1)
   * ---------------------------------------------------------------------
	foreach cond in "umbral" "1" {
		di as txt _n "===== PPML if `cond' ====="
		ppmlhdfe EXPORTS IP IP_RTA_SUBS if `cond', absorb(`fe') `vce'
		lincom IP + `merc'*IP_RTA_SUBS, eform
	}


   * ---------------------------------------------------------------------
   * 7. Errores agrupados en dos vías (importador y año)
   * ---------------------------------------------------------------------
	forvalues e = 1/6 {
		di as txt _n "===== Esp`e' cluster importador y año ====="
		reghdfe `y`e'' IP IP_RTA_SUBS if `c`e'', absorb(`fe') vce(cluster IMP_CODE year) `opc'
	}


   * ---------------------------------------------------------------------
   * 8. Por sector y sin electricidad (ISIC 40 = HS 271600, Itaipú/Yacyretá)
   * ---------------------------------------------------------------------
	gen byte grupo = .
	replace grupo = 1 if ISIC3_2 <= 5
	replace grupo = 2 if inrange(ISIC3_2, 15, 16)
	replace grupo = 3 if inrange(ISIC3_2, 17, 37)
	replace grupo = 4 if ISIC3_2 == 40
	replace grupo = 5 if missing(grupo) & !missing(ISIC3_2)   // resto (sin IP = 1)
	label define grupo 1 "Agro primario" 2 "Alimentos" 3 "Otras manufacturas" 4 "Electricidad" 5 "Otros"
	label values grupo grupo
	forvalues e = 1/6 {
		di as txt _n "===== Esp`e' por sector ====="
		reghdfe `y`e'' i.grupo#c.IP i.grupo#c.IP_RTA_SUBS if `c`e'', absorb(`fe') `vce' `opc'
		di as txt _n "===== Esp`e' sin electricidad ====="
		reghdfe `y`e'' IP IP_RTA_SUBS if `c`e'' & ISIC3_2 != 40, absorb(`fe') `vce' `opc'
		lincom IP + `merc'*IP_RTA_SUBS
	}

	log close
	* Fin
