
   * *********************************************************************
   *
   *       PART 2:  MERGING THE GTA WITH SECTORS IN LONG FORMAT, TRADE FLOWS AND PTA DATA 
   *
   *
   * *********************************************************************	   

	
	
	// Only continue after running "Split Sectors-Products.R"
	// The present code is a continuation of "1-DataPrepare_GTA_PT1.do"

	
	
*IX. Merge with measure in long fortmat ----------------------------------------------------------


use "$data_temp/GTA_cleaned.dta", clear 
	keep ID ISO_impl affectedproducts inception_year code_class interventionid	
	***ONLY KEEP DISTORSIVE IP
	keep if code_class==6
	merge 1:m ID using "$data_temp/ProductsLong_GTA_IP.dta"
	rename Product HS2012
	label var HS2012 "HS of affected products (ver. 2012 6-digit lev.)
	drop if _merge==1 // Measures that do not have a specific sector
	drop _merge
	destring HS2012, replace
	duplicates drop ISO_impl HS2012 inception_year, force // We only keep one measure in each sector per perpetrator-year
	drop ID affectedproducts
	rename ISO_impl IMP
	rename inception_year year
	gen IP=1
	sort year IMP HS
	save "$data_temp/GTA_cleaned_IP.dta", replace

use "$data_temp/GTA_cleaned.dta", clear 
	keep ID ISO_impl affectedproducts inception_year code_class interventionid
	***ONLY KEEP DISTORSIVE Import measures
	keep if code_class==4
	merge 1:m ID using "$data_temp/ProductsLong_GTA_IMP.dta"
	rename Product HS2012
	label var HS2012 "HS of affected products (ver. 2012 6-digit lev.)
	drop if _merge==1 // Measures that do not have a specific sector
	drop _merge
	destring HS2012, replace
	duplicates drop ISO_impl HS2012 inception_year, force // We only keep one measure in each sector per perpetrator-year
	drop ID affectedproducts
	rename ISO_impl IMP
	rename inception_year year
	gen IMP_BARR=1
	sort year IMP HS
	save "$data_temp/GTA_cleaned_IMP.dta", replace

*-------------------------------------------------------------------------------
* BACI measures---------------------------------------------------------
*-------------------------------------------------------------------------------

*I. Create a combineddataset of all years

clear all

	import delimited "$data_raw/BACI_HS12_Y2012_V202401.csv", clear
	tempfile BACI 
	save `BACI'

	forvalues i=2013/2022{
	import delimited "$data_raw/BACI_HS12_Y`i'_V202401.csv", clear
	append using `BACI'
	save `BACI', replace
	}

	
	merge m:1 i using "$data_aux/BACI_ISO_Codes.dta", keep(3) nogen // i is exp
	drop  IMP
	merge m:1 j using "$data_aux/BACI_ISO_Codes.dta" , keep(3) nogen // j is imp 

	rename t year
	rename k HS2012
	rename v EXPORTS
	drop q
	
	drop if EXPORTS<500


	save "$data_temp/BACI_measures.dta", replace


*-------------------------------------------------------------------------------
* Combine BACI, GTA and subsidies dataset---------------------------------------
*-------------------------------------------------------------------------------

	use "$data_temp/BACI_measures.dta", replace

	merge m:1 IMP HS2012 year using "$data_temp/GTA_cleaned_IP.dta"
	drop if _merge==2 // Remove pairs where there are IP measures but no trade flows
	drop _merge
	replace IP=0 if IP==. // Trade flows that do not have an IP measure
	
	merge m:1 IMP HS2012 year using "$data_temp/GTA_cleaned_IMP.dta", replace update
	drop if _merge==2 // Remove pairs where there are IP measures but no trade flows
	drop _merge
	replace IMP_BARR=0 if IMP_BARR==.
	keep year EXP IMP EXPORTS IP HS2012 IMP_BARR

	encode EXP, gen(EXP_CODE)
	encode IMP, gen(IMP_CODE)

***FTA VARIABLES FROM DTA
***SUBS COVERAGE
	merge m:1 EXP IMP year using "$data_temp/DTA_subsidies.dta"
	drop if _merge==2
	drop _merge
	replace rta=0 if rta==.

	gen IP_RTA=IP*(rta)
	gen IMP_BARR_RTA=IMP_BARR*(rta)

	replace SUBS_COVERAGE=0 if SUBS_COVERAGE==.
	replace REL_SUBS_COVERAGE=0 if REL_SUBS_COVERAGE==.
	gen IP_RTA_SUBS=IP*SUBS_COVERAGE
	gen IP_RTA_REL_SUBS=IP*REL_SUBS_COVERAGE
	
	
	
*-------------------------------------------------------------------------------
***DEPENDENT VARIBLES
	sort EXP IMP HS2012 year
	gen ln_exp=ln(EXPORTS)
	bysort  EXP IMP HS2012: gen EXP_GROWTH=100*(ln(EXPORTS)-ln(EXPORTS[_n-1]))

*-------------------------------------------------------------------------------
***ADDTIONAL VARIBLES

	*** ISIC REV3
	merge m:1 HS2012 using "$data_aux/HS2012_ISIC3.dta"
	drop if _merge==2
	drop _merge

	*** REGIONS & INCOME
	rename EXP Economy
	merge m:1  Economy using "$data_aux/Classification-economies-21.dta"
	rename  Economy EXP
	
	
	
*-------------------------------------------------------------------------------
*** SAVE 

	save "$data_temp/DataforRegressions", replace