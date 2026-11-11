# if needed, set the WD to the reproducibility package path
# setwd("C:/...../RR_EAP_2024_161-v01/Reproducibility package") 

# Install packages if needed
#install.packages("tidyr")
#install.packages("reshape2")
#install.packages("haven")
#install.packages("stringr")
#install.packages("dplyr")

library(tidyr)
library(reshape2)
library(haven)
library(stringr)
library(dplyr)


################################################################################
Products = read.csv("1_Data/Temp/ProductsWide_GTA_IP.csv", sep = ',')

Products <- subset(Products, select = c(ID, affectedproducts))


Products <- separate(Products, col = affectedproducts, into = paste0("sector_", 1:600), sep = ",")

# Reshape the data from wide to long format
Products <- melt(
  data = Products,
  id.vars = "ID",
  variable.name = "Products_order",
  value.name = "Product",
  na.rm = TRUE
)

Products$Product <- str_trim(Products$Product)
Products <- select(Products, -Products_order)

write_dta(Products,  "1_Data/Temp/ProductsLong_GTA_IP.dta")

rm(Products)





################################################################################
Products = read.csv("1_Data/Temp/ProductsWide_GTA_IMP.csv", sep = ',')

Products <- subset(Products, select = c(ID, affectedproducts))


Products <- separate(Products, col = affectedproducts, into = paste0("sector_", 1:600), sep = ",")

# Reshape the data from wide to long format
Products <- melt(
  data = Products,
  id.vars = "ID",
  variable.name = "Products_order",
  value.name = "Product",
  na.rm = TRUE
)

Products$Product <- str_trim(Products$Product)
Products <- select(Products, -Products_order)

write_dta(Products,  "1_Data/Temp/ProductsLong_GTA_IMP.dta")


rm(Products)


