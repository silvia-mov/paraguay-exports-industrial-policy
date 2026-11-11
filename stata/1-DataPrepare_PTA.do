
   * *********************************************************************
   *
   *       PART 1:  CLEANING THE CORE SUBSIDIES DATABASE
   *
   *
   * *********************************************************************	   
   
   
	import excel "$data_raw/DTA 2.0 - Vertical Content (v2).xlsx", sheet("STATA") firstrow allstring clear
	keep if Area=="Subsidies"

	gen question=real(substr( Coding, -2,.))
	tab question
	keep if question>=13 & question<=25
	reshape long agree_, i( Area Coding Provision) j(WBID)
	gen VALUE=real(agree_)
	keep WBID question VALUE
	reshape wide VALUE, i( WBID) j( question)
	drop VALUE16
	egen SUBS_COVERAGE=rowtotal(VALUE*)
	replace SUBS_COVERAGE =SUBS_COVERAGE/12
	egen max_SUBS_COVERAGE=max(SUBS_COVERAGE)
	gen REL_SUBS_COVERAGE=SUBS_COVERAGE/max_SUBS_COVERAGE
	keep WBID SUBS_COVERAGE REL_SUBS_COVERAGE
	tempfile subsidies
	save `subsidies'
	
	import excel "$data_raw\DTA 2.0 - Vertical Content (v2).xlsx", sheet("Bilateral Information") firstrow clear
	rename (iso1 iso2) (EXP IMP)
	keep if inrange( year, 2003,2023)
	merge m:1 WBID using `subsidies', keep(3) nogen
	keep EXP IMP year SUBS_COVERAGE REL_SUBS_COVERAGE
	gen rta=1
	drop if year<=2011
	drop if year==2023
	sort EXP IMP year SUBS_COVERAGE
	duplicates drop EXP IMP year, force
	drop if year==.

	save "$data_temp\DTA_subsidies.dta", replace	

	