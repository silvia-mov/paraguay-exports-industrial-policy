

   * *********************************************************************
   *
   *       PART 1:  CLEANING THE CORE GTA DATABASE AND CREATING CSV WITH SECTOR INFORMATION
   *
   *
   * *********************************************************************	   

	   
	insheet using  "$data_raw\GTA-OCT-23.csv", clear 							// Use the original data
	drop v1 																	// the index variable 
	

*I. Label variables 

	label var stateactid  					"ID of announcement made by the government"
	label var interventionid 				"ID of the intervention"
	label var stateacttitle 				"Title of government announcement"
	label var announcementdate  			"Date of announcement made by the government"
	label var gtaevaluation     			"Direction of intervention"
	label var currentlyinforce 				"=1 if the intervention is currently in force"
	label var inceptiondate					"The date the documented change is enforced"
	label var removaldate					"The date the documented change is withdrawn or fully replaced"
	label var implementingjurisdiction 		"The jurisdiction(s) for which the described change is announced"
	label var implementationlevel 			"Government level of implementing jurisdiction"
	label var eligiblefirms					"Subset of the firms affected by the change"
	label var interventiontype				"The content of each intervention"
	label var mastchapter					"UN MAST chapter (International Classification of NTMs)"
	label var affectedsectors				"CPC of affected sectors (ver. 2.1 3-digit lev.)"
	label var affectedproducts				"HS of affected products (ver. 2012 6-digit lev.)"
	label var affectedjurisdiction  		"Jurisdictions whose commercial interests are affected"
	
	
	
* II. Harmonize missing values 
	replace mastchapter="NA" 		if  mastchapter=="Instrument unclear"
	replace interventiontype="NA" 	if  interventiontype=="Instrument unclear"
	
	
*III. Encode 
	label define yesno 0 "No" 1 "Yes"
	encode currentlyinforce, gen(temp) label(yesno) noextend
	drop currentlyinforce
	rename temp currentlyinforce
	
	foreach var in implementingjurisdiction affectedjurisdiction{
		replace `var'=subinstr(`var', "&", "and",.)
		replace `var'= "North Macedonia" if `var'=="Macedonia"
		replace `var'= "Faroe Islands" if `var'=="Faeroe Islands"
		replace `var'= "North Macedonia" if `var'=="Macedonia"
		replace `var'= "Faroe Islands" if `var'=="Faeroe Islands"
		replace `var'= "Faroe Islands" if `var'=="Faeroe Islands"
		replace `var'= "Virgin Islands, British" if `var'=="British Virgin Islands"
		replace `var'= "Micronesia, Federated States of" if `var'=="Micronesia"
		replace `var'= "Saint Barthélemy" if `var'=="Saint-Barthélemy"
		replace `var'= "Saint Martin (French part)" if `var'=="Saint-Martin"
		replace `var'= "Svalbard and Jan Mayen" if `var'=="Svalbard and Jan Mayen Islands"
		replace `var'= "Holy See (Vatican City State)" if `var'=="Vatican"	
		replace `var'= "Wallis and Futuna" if `var'=="Wallis and Futuna Islands"
		replace `var'= "Saint Helena, Ascension and Tristan da Cunha" if `var'=="Saint Helena"	
		replace `var' = "Anguilla" if `var' == "Anguilla"
		replace `var' = "Bahamas, The" if `var' == "Bahamas"
		replace `var' = "Cabo Verde" if `var' == "Cape Verde"
		replace `var' = "Taiwan, China" if `var' == "Chinese Taipei"
		replace `var' = "Congo, Rep." if `var' == "Congo"
		replace `var' = "Congo, Dem. Rep." if `var' == "DR Congo"
		replace `var' = "Egypt, Arab Rep." if `var' == "Egypt"
		replace `var' = "Falkland Islands" if `var' == "Falkland Islands"
		replace `var' = "Gambia, The" if `var' == "Gambia"
		replace `var' = "Hong Kong SAR, China" if `var' == "Hong Kong"
		replace `var' = "Iran, Islamic Rep." if `var' == "Iran"
		replace `var' = "Cote d'Ivoire" if `var' == "Ivory Coast"
		replace `var' = "Kyrgyz Republic" if `var' == "Kyrgyzstan"
		replace `var' = "Lao PDR" if `var' == "Lao"
		replace `var' = "Montserrat" if `var' == "Montserrat"
		replace `var' = "Micronesia, Fed. Sts." if `var' == "NA"
		replace `var' = "Korea, Rep." if `var' == "Republic of Korea"
		replace `var' = "Moldova" if `var' == "Republic of Moldova"
		replace `var' = "Sudan" if `var' == "Republic of the Sudan"
		replace `var' = "Russian Federation" if `var' == "Russia"
		replace `var' = "St. Kitts and Nevis" if `var' == "Saint Kitts and Nevis"
		replace `var' = "St. Lucia" if `var' == "Saint Lucia"
		replace `var' = "St. Vincent and the Grenadines" if `var' == "Saint Vincent and the Grenadines"
		replace `var' = "São Tomé and Príncipe" if `var' == "Sao Tome and Principe"
		replace `var' = "Slovak Republic" if `var' == "Slovakia"
		replace `var' = "West Bank and Gaza" if `var' == "State of Palestine"
		replace `var' = "Eswatini" if `var' == "Swaziland"
		replace `var' = "Syrian Arab Republic" if `var' == "Syria"
		replace `var' = "Türkiye" if `var' == "Turkey"
		replace `var' = "Virgin Islands (U.S.)" if `var' == "US Virgin Islands"
		replace `var' = "United States" if `var' == "United States of America"
		replace `var' = "Venezuela, RB" if `var' == "Venezuela"
		replace `var' = "Yemen, Rep." if `var' == "Yemen"
	}
	
	rename implementingjurisdiction Economy
	merge m:1 Economy using "$data_aux/Classification-economies-07.dta"
	drop if _merge!=3  // Anguilla, Falklands & Monsterrat
	drop _merge 
	rename (Economy Code Incomegroup) (implementingjurisdiction ISO_impl incgroup_impl)
	
	rename affectedjurisdiction Economy
	merge m:1 Economy using "$data_aux\Classification-economies-07.dta"
	drop if _merge!=3 & Economy!="NA"
	drop _merge 
	rename (Economy Code Incomegroup) (affectedjurisdiction ISO_aff incgroup_aff)
	
	
* IV. Duplicates drop 
	duplicates drop
	
* V. Create new ID variable
	sort interventionid implementingjurisdiction affectedjurisdiction
	egen ID=group(interventionid implementingjurisdiction affectedjurisdiction)	

	
* VI. 	Create additional variables

	gen inception_year=substr(inceptiondate,1,4)
	destring inception_year, force replace
	keep if inrange(inception_year, 2009,2022)
	
	
	gen class_measure=""
	
	* Measures of commercial policy (Import barriers)
	replace class_measure="Imp_barriers" if inlist(interventiontype, "Anti-dumping", "Anti-subsidy", "Import ban", "Import licensing requirement", "Import monitoring", "Import quota", "Import tariff")
	replace class_measure="Imp_barriers" if inlist(interventiontype, "Import tariff quota", "Internal taxation of imports", "Import-related non-tariff measure, nes")
	    replace class_measure="Imp_barriers" if inlist(interventiontype, "Local content incentive", "Local content requirement", "Local operations incentive", "Local operations requirement", "Local value added incentive", "Public procurement localisation", "Localisation, nes")
	


	* Measures of commercial policy (Export barriers)
	replace class_measure="Exp_barriers" if inlist(interventiontype, "Export ban", "Export licensing requirement", "Export quota", "Export tariff quota", "Export tax")
	replace class_measure="Exp_barriers" if inlist(interventiontype, "Local supply requirement for exports", "Export-related non-tariff measure, nes")

	* Measures of industrial policy (Subsidies+ Export incentives)
	replace class_measure="Ind_policy" if inlist(interventiontype, "Capital injection and equity stakes (including bailouts)", "Financial grant", "In-kind grant", "Tax or social insurance relief", "Production subsidy")
	replace class_measure="Ind_policy" if inlist(interventiontype, "Interest payment subsidy", "Loan guarantee", "Import incentive", "Price stabilisation")
	replace class_measure="Ind_policy" if inlist(interventiontype, "State loan","State aid, nes", "State aid, unspecified")
	replace class_measure="Ind_policy" if inlist(interventiontype, "Trade finance", "Export subsidy", "Tax-based export incentive", "Financial assistance in foreign market", "Other export incentive")

	

* VII. Subset 

	drop if  gtaevaluation=="Amber"	
	drop if  class_measure==""

	label drop _all

	label define greenred 1 "Green" 2 "Red"
	encode gtaevaluation, label(greenred) noextend gen(greenred)
	drop gtaevaluation
	rename greenred gtaevaluation 

	sort class_measure gtaevaluation 			
	
	gen code_class=.
	replace code_class=1 if class_measure=="Exp_barriers" & gtaevaluation==1
	replace code_class=2 if class_measure=="Exp_barriers" & gtaevaluation==2
	replace code_class=3 if class_measure=="Imp_barriers" & gtaevaluation==1
	replace code_class=4 if class_measure=="Imp_barriers" & gtaevaluation==2
	replace code_class=5 if class_measure=="Ind_policy" & gtaevaluation==1
	replace code_class=6 if class_measure=="Ind_policy" & gtaevaluation==2


	order ID interventionid ISO_impl ISO_aff gtaevaluation inceptiondate mastchapter interventiontype announcementdate currentlyinforce removaldate  stateacttitle eligiblefirms affectedproducts affectedsectors implementationlevel stateactid interventionid implementingjurisdiction *_impl affectedjurisdiction *_aff
	
	compress	

	save "$data_temp/GTA_cleaned.dta", replace 

*VII. Export IP and IMP measures---------------------------------------------------------

use "$data_temp/GTA_cleaned.dta", clear 
	keep ID ISO_impl affectedproducts inception_year code_class interventionid
	***ONLY KEEP DISTORSIVE IP
	keep if code_class==6
	keep ID interventionid affectedproducts	
	export delimited using "$data_temp\ProductsWide_GTA_IP.csv", replace
	// The file "ProductsWide_GTA_IP.csv" will be used to produce the sector variable in R.  

use "$data_temp/GTA_cleaned.dta", clear 
	keep ID ISO_impl affectedproducts inception_year code_class interventionid
	***ONLY KEEP DISTORSIVE Import measures
	keep if code_class==4
	keep ID interventionid affectedproducts	
	export delimited using "$data_temp\ProductsWide_GTA_IMP.csv", replace
	// The file "ProductsWide_GTA_IMP.csv" will be used to produce the sector variable in R.  

	// Refer to the code >>> "Split Sectors-Products.R"
	// DO NOT RUN THE REST OF THE CODE BEFORE RUNNING "Split Sectors-Products.R"
	// This code will create the files  ProductsLong_GTA_IMP.dta &  ProductsLong_GTA_IP.dta that are needed in the next step



