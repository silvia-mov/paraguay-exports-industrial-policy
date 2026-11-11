
   * ******************************************************************** *
   * ******************************************************************** *
   *                                                                      *
   *                IP TRADE EFFECTS AND PTA 			 						  *
   *                                                                      *
   * ******************************************************************** *
   * ******************************************************************** *
		clear all

	* PART 0:  STANDARDIZE SETTINGS & PREPARING FOLDER PATH GLOBALS
	
	 
	 
		set linesize 80
		set more off
		macro drop _all
		set more off		
		
		global root ""  // Change the root to the desired folder of the replicator

		cd "$root"
		
		sysdir set PLUS "${root}/2_Do_files/ado"
		set varabbrev on

		global data_raw 	"1_Data/Raw_data"
		global data_temp 	"1_Data/Temp"
		global data_aux 	"1_Data/Auxiliary"
		global do_files  	"2_Do_files"
		global log_files  	"3_Log_files"
		global figures 		"4_Figures"	
		global tables 		"5_Tables"	
		
		
		 log using "$log_files/reppackage161_1", replace
		
		**RUN THESE COMMANDS IF NOT ALREADY INSTALLED:
		*ssc install reghdfe, replace
		*ssc install estout, replace
		*ssc install unique, replace
		*ssc install ftools, replace
	
		
   * PART 1:  RUN ALL THE CODES NEEDED TO CLEAN THE DATA & PRODUCE OUTOUT TABLES AND FIGURES
		
	*1 CLEAN DATA-

//quietly {
		do "$do_files/1-DataPrepare_PTA.do"
		do "$do_files/2-DataPrepare_GTA_PT1.do"
		
		log close
		** Here you should run the code "1-Split Sectors-Products.R"
		** Then, you can continue cleaning the database 
			 log using "$log_files/reppackage161_1", replace

		
		do "$do_files/4-DataPrepare_GTA_PT2.do"
		

	*2 RUN REGRESSIONS	& PRODUCE TABLES
		do "$do_files/5-Regressions.do"
		
	*3. PRODUCE FIGURES
		do "$do_files/6-Figures.do"
		log close
//}	
