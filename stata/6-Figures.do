
**# FIGURE 1 -------------------------------------------------------------------
* New Ind policies and GDP mer capita
*-------------------------------------------------------------------------------
***DATA PREPARATION
local n 1

import excel "$data_raw/GTA_NIPO.xlsx", sheet("GTA NIPO - December 2023") firstrow clear
keep if Initialassessmentchangerelat=="Distortive"
gsort -SizeofsubsidyUSDmillion
***CONFIRMED A TYPO  IN THE CURRENT LARGEST DOLLAR MOUNT (UK) checked with GTA website: 622 millions not billions!
replace SizeofsubsidyUSDmillion = 622.560 in 1

gen date_m=mofd( Implementationdate )
format date_m %tm
tab date_m
gen year=year( Implementationdate )
tab year
br if year==2024
keep if year==2023
replace Jurisdiction="United States" if  Jurisdiction=="United States of America"
replace Jurisdiction="Egypt, Arab Rep." if  Jurisdiction=="Egypt"
replace Jurisdiction="Hong Kong SAR, China" if  Jurisdiction=="Hong Kong"
replace Jurisdiction="Russian Federation" if  Jurisdiction=="Russia"
replace Jurisdiction="Türkiye" if  Jurisdiction=="Turkey"
replace Jurisdiction="Korea, Rep." if  Jurisdiction=="Republic of Korea"
merge m:1 Jurisdiction using "$data_aux/Classification-economies-21.dta"
tab Jurisdiction if _merge==1
drop if _merge==2

bysort Jurisdiction: egen IP_measure_country=count(EntryID)
bysort Jurisdiction: egen IP_USD_country=sum( SizeofsubsidyUSDmillion)
gen log_IP_measure_country=ln(IP_measure_country)
gen log_IP_USD_country=ln( IP_USD_country)

keep Economy log_IP_measure_country log_IP_USD_country income IP_measure_country IP_USD_country
duplicates drop Economy , force

merge 1:1 Economy using "$data_aux/GDP-21.dta", keep (3) nogen

***EXPORT
twoway(scatter log_IP_measure_country ln_gdp_pc if incomegroup=="High income", mlabel(Economy) legend(label(1 "High Income")) )(scatter log_IP_measure_country ln_gdp_pc if incomegroup!="High income" , mlabel(Economy) legend(label(2 "EMDE")))(lfit log_IP_measure_country ln_gdp_pc, lc(black)) if log_IP_measure_country!=0, title("New Industrial Policies: Measures vs. Development, 2023 (source: NIPO)", size(medium) pos(12)) xtitle("GDP per Capita in 2021 (in logs)", height(10)) ytitle("Number of measures 2023 (in logs)", height(10)) legend(pos(12) rows(1))

	graph save 	 "$figures/BMT_Fig_`n'.gph", replace
	graph export "$figures/BMT_Fig_`n'.pdf", replace as(pdf)
	graph export "$figures/BMT_Fig_`n'.jpg",  replace as(jpg) name("Graph") 
	graph export "$figures/BMT_Fig_`n'.png",  replace as(png) name("Graph") 



**# FIGURE 2 -------------------------------------------------------------------
* Exports to the US, selected markets
*-------------------------------------------------------------------------------
local n 2 

import delimited "$data_raw/Standard Report - Imports.csv", clear 

drop rateprovision

gen time2="20"
gen time3=substr(time, 5, 2)
gen time4= time2+ time3
gen month_name=substr(time,1,3)
gen month=0
replace month=1 if month_name=="Jan"
replace month=2 if month_name=="Feb"
replace month=3 if month_name=="Mar"
replace month=4 if month_name=="Apr"
replace month=5 if month_name=="May"
replace month=6 if month_name=="Jun"
replace month=7 if month_name=="Jul"
replace month=8 if month_name=="Aug"
replace month=9 if month_name=="Sep"
replace month=10 if month_name=="Oct"
replace month=11 if month_name=="Nov"
replace month=12 if month_name=="Dec"
tab month
gen year=real(time4)
gen date_m=ym(year, month)
format date %tm
drop if date_m==.

drop month_name time4 time3 time2 time 

replace country="Total" if country=="World Total"
replace country="USMCA" if country=="USMCA - U.S.-Mexico-Canada Agreement"
replace country="ASEAN" if country=="ASEAN - Association of Southeast Asian Nations"

rename customsvaluegenus EXP_0
*reshape wide EXP_,  i(date_m) j(country) string

sort country date_m
bysort country: gen EXP_0_A=EXP_0+EXP_0[_n-1]+EXP_0[_n-2]+EXP_0[_n-3]+EXP_0[_n-4]+EXP_0[_n-5]+EXP_0[_n-6]+EXP_0[_n-7]+EXP_0[_n-8]+EXP_0[_n-9]+EXP_0[_n-10]+EXP_0[_n-11]
by country: gen obs=_n
tab obs

by country: gen EXP_0_A_index=100*(EXP_0_A/EXP_0_A[18])

keep country date_m EXP_0_A_index obs
reshape wide EXP_0_A_index, i(date_m) j(country) string
keep if obs>12
twoway(line EXP_0_A_indexASEAN date_m,lw(medthick)  )(line EXP_0_A_indexChina date_m , lw(medthick) )(line EXP_0_A_indexMexico date_m, lw(medthick) lp(dash) )(line EXP_0_A_indexTotal date_m ,lw(medthick) lp(dash_dot)) ,  graphregion(color(white)) plotregion(color(white)) legend( label(1 "ASEAN") label(2 "China") label(3 "Mexico") label(4 "Total")) title("Total Export to US, by Origin (2018m6=100)", height(-20)) xtitle("") ytitle("Index (2018m6=100) of 12-months trailing sum") xline(702,lc(black)) xline(722,lc(black)) xline(751,lc(black)) legend(position(6) rows(1))

	graph save 	 "$figures/BMT_Fig_`n'.gph", replace
	graph export "$figures/BMT_Fig_`n'.pdf", replace as(pdf)
	graph export "$figures/BMT_Fig_`n'.jpg",  replace as(jpg) name("Graph") 
	graph export "$figures/BMT_Fig_`n'.png",  replace as(png) name("Graph") 

**# FIGURE 3 -------------------------------------------------------------------
* Baseline results (figure made by authors from coefficientes shown in table 3)
*-------------------------------------------------------------------------------

**# FIGURE  4-------------------------------------------------------------------
* GTA chapters (figure taken from the GTA handbook)
*-------------------------------------------------------------------------------

**# FIGURE 5 -------------------------------------------------------------------
* Breakdown in industrial policies, import and export restrictions
*-------------------------------------------------------------------------------

local n 5
	use "$data_temp\GTA_cleaned", clear
	unique(interventionid), by (gtaevaluation inception_year ISO_impl) gen(number_interventions)
	collapse (sum) number_interventions, by(gtaevaluation inception_year)

	
	twoway (line  number_interventions inception_year if  gtaevaluation==2, color(red) lpattern(shortdash) lwidth(0.5)), ytitle("Number of restricitve measures", height(10)) ///
	xlabel(2009(1)2022, angle(45)) xtitle("Year", height(10)) /// year
	legend(off) 	

	graph save 	 "$figures/BMT_Fig_`n'.gph", replace
	graph export "$figures/BMT_Fig_`n'.pdf", replace as(pdf)
	graph export "$figures/BMT_Fig_`n'.jpg",  replace as(jpg) name("Graph") 
	graph export "$figures/BMT_Fig_`n'.png",  replace as(png) name("Graph") 
		
		
		
**# FIGURE 6 -------------------------------------------------------------------
* Breakdown in industrial policies, import and export restrictions
*-------------------------------------------------------------------------------
local n 6
	use "$data_temp\GTA_cleaned", clear
	unique(interventionid), by (gtaevaluation inception_year class_measure ISO_impl) gen(number_interventions)
	collapse (sum) number_interventions, by(gtaevaluation inception_year class_measure)


	twoway (line  number_interventions inception_year if  gtaevaluation==2 & class_measure=="Exp_barriers", color(red) lpattern(solid) lwidth(0.5)) ///
	(line  number_interventions inception_year if  gtaevaluation==2 & class_measure=="Imp_barriers", color(navy) lpattern(dash) lwidth(0.5)) ///
	(line  number_interventions inception_year if  gtaevaluation==2 & class_measure=="Ind_policy", color(green) lpattern(shortdash) lwidth(0.5)), ///
 ytitle("Number of measures", height(10)) ///
	xlabel(2009(1)2022, angle(45)) xtitle("Year") /// year
	legend(order (1 "Export barriers" 2 "Import barriers" 3 "Industrial policy") ///
	region(lstyle(none)) pos(6) rows(1)) 
	

	graph save 	 "$figures/BMT_Fig_`n'.gph", replace
	graph export "$figures/BMT_Fig_`n'.pdf", replace as(pdf)
	graph export "$figures/BMT_Fig_`n'.jpg",  replace as(jpg) name("Graph") 
	graph export "$figures/BMT_Fig_`n'.png",  replace as(png) name("Graph") 
		

**# FIGURE 7 -------------------------------------------------------------------
* Breakdown in industrial policies, import and export restrictions
*-------------------------------------------------------------------------------


local n 7

	use "$data_temp\GTA_cleaned", clear
	
	gen MAST_code=substr(mastchapter,1,1)
	
	replace MAST_code="NS" if mastchapter=="Instrument unclear"
	replace MAST_code="NS" if mastchapter==""

	replace MAST_code="TAR" if mastchapter=="Capital control measures"
	replace MAST_code="FDI" if mastchapter=="FDI measures"
	replace MAST_code="MIG" if mastchapter=="Migration measures"
	replace MAST_code="TAR" if mastchapter=="Tariff measures"
	
	unique(interventionid), by (MAST_code gtaevaluation inception_year) gen(number_interventions)
	collapse (sum) (number_interventions), by (MAST_code gtaevaluation inception_year) 
	fillin MAST_code gtaevaluation inception_year
	replace number_interventions=0 if _fillin==1
	drop _fillin
	egen num_code_year=std(number_interventions), by (gtaevaluation)


	replace MA=subinstr(MA, " ", "_",.)
	rename num_code_year num_sd
*rename number_interventions num
	drop if inception_year==2008
		
	sort gtaevaluation MAST_code  inception_year
	bys gtaevaluation MAST_code : gen number_interventions1=number_interventions-number_interventions[1]
	bys gtaevaluation MAST_code : replace number_interventions1=number_interventions-number_interventions[2] if number_interventions1==.
		drop number_interventions
		rename number_interventions1 number_interventions

	sort gtaevaluation MAST_code  inception_year

	reshape wide num*, i(gtaevaluation inception_year) j(MAST_code) string

preserve 
keep if gtaevaluation==2

	
	twoway ///
	(line  number_interventionsD inception_year, lpattern(shortdash) lcolor(orange)) || ///
	(line number_interventionsI inception_year, lpattern(dash) lcolor(purple)) || ///
	(line  number_interventionsM inception_year, lpattern(longdash_dot) lcolor(navy) lwidth(0.5)) ///
	(line  number_interventionsE inception_year, lpattern(dot) lcolor(green) lwidth(1)) ///
	(line  number_interventionsL inception_year, lpattern(shortdash) lcolor(red) lwidth(0.5)) ///
	(line  number_interventionsP inception_year, lpattern(longdash) lcolor(midblue) lwidth(0.5)), ///
	 xline(2015, lcolor(black) lpattern(solid)) xline(2019, lcolor(black) lpattern(solid)) xline(2022, lcolor(black) lpattern(solid)) yline(0, lpattern(solid)) ///
	graphregion(color(white))  ///
	ytitle("Index [2009=0] of restrictive measures", height(10) size(medsmall)) ///
	xlabel(2009(2)2022, angle(45)) xtitle("Year") /// year
	legend(order (1 "Contingent trade-protective " 2 "Trade-related investment" 3 "Government procurement" 4 "Non-automatic import licensing, quotas, prohibitions" 5 "Subsidies" 6 "Export-related") region(lstyle(none)) pos(6) rows(3) size(small)) 
	
	graph save 	 "$figures/BMT_Fig_`n'A.gph", replace
	graph export "$figures/BMT_Fig_`n'A.pdf", replace as(pdf)
	graph export "$figures/BMT_Fig_`n'A.jpg",  replace as(jpg) name("Graph") 
	graph export "$figures/BMT_Fig_`n'A.png",  replace as(png) name("Graph") 
restore



preserve 
keep if gtaevaluation==1

	
	twoway ///
	(line  number_interventionsD inception_year, lpattern(shortdash) lcolor(orange)) || ///
	(line number_interventionsI inception_year, lpattern(dash) lcolor(purple)) || ///
	(line  number_interventionsM inception_year, lpattern(longdash_dot) lcolor(navy) lwidth(0.5)) ///
	(line  number_interventionsE inception_year, lpattern(dot) lcolor(green) lwidth(1)) ///
	(line  number_interventionsL inception_year, lpattern(shortdash) lcolor(red) lwidth(0.5)) ///
	(line  number_interventionsP inception_year, lpattern(longdash) lcolor(midblue) lwidth(0.5)), ///
	 xline(2015, lcolor(black) lpattern(solid)) xline(2019, lcolor(black) lpattern(solid)) xline(2022, lcolor(black) lpattern(solid)) yline(0, lpattern(solid)) ///
	graphregion(color(white))  ///
	ytitle("Index [2009=0] of liberalizing measures", height(10) size(medsmall)) ///
	xlabel(2009(1)2022, angle(45)) xtitle("Year") /// year
	legend(order (1 "Contingent trade-protective " 2 "Trade-related investment" 3 "Government procurement" 4 "Non-automatic import licensing, quotas, prohibitions" 5 "Subsidies" 6 "Export-related") region(lstyle(none)) pos(6) rows(3) size(small)) 
	
	
	graph save 	 "$figures/BMT_Fig_`n'B.gph", replace
	graph export "$figures/BMT_Fig_`n'B.pdf", replace as(pdf)
	graph export "$figures/BMT_Fig_`n'B.jpg",  replace as(jpg) name("Graph") 
	graph export "$figures/BMT_Fig_`n'B.png",  replace as(png) name("Graph") 
restore

