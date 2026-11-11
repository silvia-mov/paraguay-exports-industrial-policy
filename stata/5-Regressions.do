 * *********************************************************************
   *
   *       PART 3:  Run the analysis 
   *
   *
   * *********************************************************************	   
   
**# TABLE 1------
	* No data needed
**# TABLE 2------
	* No data needed

use  "$data_temp/DataforRegressions", clear 

 keep if EXPORTS>1000
**# TABLE 3------
local n 3

quietly { 
	
reghdfe EXP_GROWTH IP, a(EXP_CODE#IMP_CODE#year  EXP_CODE#year#HS2012 IMP_CODE#year#ISIC3_2 HS2012#IMP_CODE) cluster(EXP_CODE#IMP_CODE)
estimates store m1

reghdfe EXP_GROWTH IP IP_RTA , a(EXP_CODE#IMP_CODE#year  EXP_CODE#year#HS2012 IMP_CODE#year#ISIC3_2  HS2012#IMP_CODE) cluster(EXP_CODE#IMP_CODE)
estimates store m2
lincom IP + IP_RTA

reghdfe EXP_GROWTH IP IMP_BARR , a(EXP_CODE#IMP_CODE#year  EXP_CODE#year#HS2012 IMP_CODE#year#ISIC3_2  HS2012#IMP_CODE) cluster(EXP_CODE#IMP_CODE)
estimates store m3

reghdfe EXP_GROWTH IP IMP_BARR IP_RTA IMP_BARR_RTA  , a(EXP_CODE#IMP_CODE#year  EXP_CODE#year#HS2012 IMP_CODE#year#ISIC3_2  HS2012#IMP_CODE) cluster(EXP_CODE#IMP_CODE)
estimates store m4

reghdfe EXP_GROWTH IP IP_RTA_SUBS   , a(EXP_CODE#IMP_CODE#year  EXP_CODE#year#HS2012 IMP_CODE#year#ISIC3_2 HS2012#IMP_CODE) cluster(EXP_CODE#IMP_CODE)
estimates store m5
lincom IP + 0.5*IP_RTA_SUBS 

reghdfe EXP_GROWTH IP IMP_BARR IMP_BARR_RTA IP_RTA_SUBS  ,a(EXP_CODE#IMP_CODE#year  EXP_CODE#year#HS2012 IMP_CODE#year#ISIC3_2  HS2012#IMP_CODE) cluster(EXP_CODE#IMP_CODE)
estimates store m6
}
estout m*, k( IP IMP_BARR IP_RTA  IMP_BARR IMP_BARR_RTA IP_RTA_SUBS  )  cells(b(star fmt(%9.3f)) se(par)) stats(r2 N, fmt(%9.3f %9.0g) labels(R-squared)) legend collabels(none) varlabels(_cons Constant) starlevels( * 0.10 ** 0.05 *** 0.01)

estout m* using "$tables/BMT_Tab_`n'.tex", k( IP IMP_BARR IP_RTA  IMP_BARR IMP_BARR_RTA IP_RTA_SUBS  ) style(tex) cells(b(star fmt(%9.3f)) se(par)) stats(r2 N, fmt(%9.3f %9.0g) labels(R-squared)) legend collabels(none) varlabels(_cons Constant) starlevels( * 0.10 ** 0.05 *** 0.01) replace

est clear
*restore



**# TABLE 4 More stringent
local n 4

quietly { 


reghdfe EXP_GROWTH IP_RTA , a(EXP_CODE#IMP_CODE#year  EXP_CODE#year#HS2012 IMP_CODE#year#HS2012 EXP_CODE#IMP_CODE#HS2012) cluster(EXP_CODE#IMP_CODE)
estimates store m1

reghdfe EXP_GROWTH  IP_RTA IMP_BARR_RTA  , a(EXP_CODE#IMP_CODE#year  EXP_CODE#year#HS2012 IMP_CODE#year#HS2012 EXP_CODE#IMP_CODE#HS2012) cluster(EXP_CODE#IMP_CODE)
estimates store m2

reghdfe EXP_GROWTH  IP_RTA_SUBS , a(EXP_CODE#IMP_CODE#year  EXP_CODE#year#HS2012 IMP_CODE#year#HS2012 EXP_CODE#IMP_CODE#HS2012) cluster(EXP_CODE#IMP_CODE)
estimates store m3

reghdfe EXP_GROWTH  IP_RTA IMP_BARR_RTA  IP_RTA_SUBS , a(EXP_CODE#IMP_CODE#year  EXP_CODE#year#HS2012 IMP_CODE#year#HS2012 EXP_CODE#IMP_CODE#HS2012) cluster(EXP_CODE#IMP_CODE)
estimates store m4
}
estout m*, k( IP_RTA IMP_BARR_RTA IP_RTA_SUBS )  cells(b(star fmt(%9.3f)) se(par)) stats(r2 N, fmt(%9.3f %9.0g) labels(R-squared)) legend collabels(none) varlabels(_cons Constant) starlevels( * 0.10 ** 0.05 *** 0.01)

estout m* using "$tables/BMT_Tab_`n'.tex", k( IP_RTA IMP_BARR_RTA IP_RTA_SUBS ) style(tex) cells(b(star fmt(%9.3f)) se(par)) stats(r2 N, fmt(%9.3f %9.0g) labels(R-squared)) legend collabels(none) varlabels(_cons Constant) starlevels( * 0.10 ** 0.05 *** 0.01) replace
est clear

**# TABLE 5 No outliers
local n 5

quietly { 



reghdfe EXP_GROWTH IP if EXP_GROWTH>-200 & EXP_GROWTH<200, a(EXP_CODE#IMP_CODE#year  EXP_CODE#year#HS2012 IMP_CODE#year#ISIC3_2 HS2012#IMP_CODE) cluster(EXP_CODE#IMP_CODE)
estimates store m1

reghdfe EXP_GROWTH IP IP_RTA  if EXP_GROWTH>-200 & EXP_GROWTH<200, a(EXP_CODE#IMP_CODE#year  EXP_CODE#year#HS2012 IMP_CODE#year#ISIC3_2  HS2012#IMP_CODE) cluster(EXP_CODE#IMP_CODE)
estimates store m2
lincom IP + IP_RTA

reghdfe EXP_GROWTH IP IMP_BARR  if EXP_GROWTH>-200 & EXP_GROWTH<200, a(EXP_CODE#IMP_CODE#year  EXP_CODE#year#HS2012 IMP_CODE#year#ISIC3_2  HS2012#IMP_CODE) cluster(EXP_CODE#IMP_CODE)
estimates store m3

reghdfe EXP_GROWTH IP IMP_BARR IP_RTA IMP_BARR_RTA   if EXP_GROWTH>-200 & EXP_GROWTH<200, a(EXP_CODE#IMP_CODE#year  EXP_CODE#year#HS2012 IMP_CODE#year#ISIC3_2  HS2012#IMP_CODE) cluster(EXP_CODE#IMP_CODE)
estimates store m4

reghdfe EXP_GROWTH IP IP_RTA_SUBS   if EXP_GROWTH>-200 & EXP_GROWTH<200, a(EXP_CODE#IMP_CODE#year  EXP_CODE#year#HS2012 IMP_CODE#year#ISIC3_2 HS2012#IMP_CODE) cluster(EXP_CODE#IMP_CODE)
estimates store m5
lincom IP + 0.5*IP_RTA_SUBS 

reghdfe EXP_GROWTH IP IMP_BARR IMP_BARR_RTA IP_RTA_SUBS   if EXP_GROWTH>-200 & EXP_GROWTH<200 ,a(EXP_CODE#IMP_CODE#year  EXP_CODE#year#HS2012 IMP_CODE#year#ISIC3_2  HS2012#IMP_CODE) cluster(EXP_CODE#IMP_CODE)
estimates store m6
}

estout m*, k( IP IMP_BARR IP_RTA  IMP_BARR IMP_BARR_RTA IP_RTA_SUBS  )  cells(b(star fmt(%9.3f)) se(par)) stats(r2 N, fmt(%9.3f %9.0g) labels(R-squared)) legend collabels(none) varlabels(_cons Constant) starlevels( * 0.10 ** 0.05 *** 0.01)

estout m* using "$tables/BMT_Tab_`n'.tex", k( IP IMP_BARR IP_RTA  IMP_BARR IMP_BARR_RTA IP_RTA_SUBS  ) style(tex) cells(b(star fmt(%9.3f)) se(par)) stats(r2 N, fmt(%9.3f %9.0g) labels(R-squared)) legend collabels(none) varlabels(_cons Constant) starlevels( * 0.10 ** 0.05 *** 0.01) replace

est clear



**# TABLE 6 Levels
local n 6

quietly{
replace ln_exp=ln_exp*100
reghdfe ln_exp IP, a(EXP_CODE#IMP_CODE#year  EXP_CODE#year#HS2012 IMP_CODE#year#ISIC3_2 HS2012#IMP_CODE) cluster(EXP_CODE#IMP_CODE)
estimates store m1

reghdfe ln_exp IP IP_RTA , a(EXP_CODE#IMP_CODE#year  EXP_CODE#year#HS2012 IMP_CODE#year#ISIC3_2  HS2012#IMP_CODE) cluster(EXP_CODE#IMP_CODE)
estimates store m2
lincom IP + IP_RTA

reghdfe ln_exp IP IMP_BARR , a(EXP_CODE#IMP_CODE#year  EXP_CODE#year#HS2012 IMP_CODE#year#ISIC3_2  HS2012#IMP_CODE) cluster(EXP_CODE#IMP_CODE)
estimates store m3

reghdfe ln_exp IP IMP_BARR IP_RTA IMP_BARR_RTA  , a(EXP_CODE#IMP_CODE#year  EXP_CODE#year#HS2012 IMP_CODE#year#ISIC3_2  HS2012#IMP_CODE) cluster(EXP_CODE#IMP_CODE)
estimates store m4

reghdfe ln_exp IP IP_RTA_SUBS   , a(EXP_CODE#IMP_CODE#year  EXP_CODE#year#HS2012 IMP_CODE#year#ISIC3_2 HS2012#IMP_CODE) cluster(EXP_CODE#IMP_CODE)
estimates store m5
lincom IP + 0.5*IP_RTA_SUBS 

reghdfe ln_exp IP IMP_BARR IMP_BARR_RTA IP_RTA_SUBS  ,a(EXP_CODE#IMP_CODE#year  EXP_CODE#year#HS2012 IMP_CODE#year#ISIC3_2  HS2012#IMP_CODE) cluster(EXP_CODE#IMP_CODE)
estimates store m6
}
estout m*, k( IP IMP_BARR IP_RTA  IMP_BARR IMP_BARR_RTA IP_RTA_SUBS  )  cells(b(star fmt(%9.3f)) se(par)) stats(r2 N, fmt(%9.3f %9.0g) labels(R-squared)) legend collabels(none) varlabels(_cons Constant) starlevels( * 0.10 ** 0.05 *** 0.01)

estout m* using "$tables/BMT_Tab_`n'.tex", k( IP IMP_BARR IP_RTA  IMP_BARR IMP_BARR_RTA IP_RTA_SUBS  ) style(tex) cells(b(star fmt(%9.3f)) se(par)) stats(r2 N, fmt(%9.3f %9.0g) labels(R-squared)) legend collabels(none) varlabels(_cons Constant) starlevels( * 0.10 ** 0.05 *** 0.01) replace

est clear



**#  TABLE 7 Heterogeneity across regions
local n 7

* Define the list of country codes to be considered as "Advanced" using a local macro

    replace region = "Advanced Economies" if incomegroup == "High income"



label define region 1 "Advanced Economies" 2 "East Asia & Pacific" 3 "Europe & Central Asia" 4 "Latin America & Caribbean" 5 "Middle East & North Africa" 6 "South Asia" 7 "Sub-Saharan Africa"
encode region, gen(region_code) label(region) noextend


quietly{

reghdfe EXP_GROWTH region_code#c.IP region_code#c.IP_RTA , a(EXP_CODE#IMP_CODE#year  EXP_CODE#year#HS2012 IMP_CODE#year#ISIC3_2 HS2012#IMP_CODE) cluster(EXP_CODE#IMP_CODE)
estimates store m2
}


estout m2,   cells(b(star fmt(%9.3f)) se(par)) stats(r2 N, fmt(%9.3f %9.0g) labels(R-squared)) legend collabels(none) varlabels(_cons Constant) starlevels( * 0.10 ** 0.05 *** 0.01)
estout m2 using "$tables/BMT_Tab_`n'.tex",  style(tex) cells(b(star fmt(%9.3f)) se(par)) stats(r2 N, fmt(%9.3f %9.0g) labels(R-squared)) legend collabels(none) varlabels(_cons Constant) starlevels( * 0.10 ** 0.05 *** 0.01) replace
est clear

**#  TABLE 8 Heterogeneity across sectors
local n 8
quietly{

reghdfe EXP_GROWTH ISIC3_2#c.IP ISIC3_2#c.IP_RTA, a(EXP_CODE#IMP_CODE#year  EXP_CODE#year#HS2012 IMP_CODE#year#ISIC3_2 HS2012#IMP_CODE) cluster(EXP_CODE#IMP_CODE)
estimates store m1
}

estout m1 using "$tables/BMT_Tab_`n'.tex",   cells(b(star fmt(%9.3f)) se(par)) stats(r2 N, fmt(%9.3f %9.0g) labels(R-squared)) legend collabels(none) varlabels(_cons Constant) starlevels( * 0.10 ** 0.05 *** 0.01) replace
estout m1,  style(tex) cells(b(star fmt(%9.3f)) se(par)) stats(r2 N, fmt(%9.3f %9.0g) labels(R-squared)) legend collabels(none) varlabels(_cons Constant) starlevels( * 0.10 ** 0.05 *** 0.01)
est clear


