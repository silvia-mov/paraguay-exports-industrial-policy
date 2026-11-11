# Cómo conseguir los datos

El código espera esta estructura en la raíz del repositorio (o en la carpeta que
indiques con `TESIS_ROOT`):

```
1_Data/
├── Raw_data/
│   ├── BACI_HS12_Y2012_V202401.csv … BACI_HS12_Y2022_V202401.csv
│   ├── GTA-OCT-23.csv
│   ├── GTA_NIPO.xlsx
│   ├── DTA 2.0 - Vertical Content (v2).xlsx
│   └── Standard Report - Imports.csv
├── Auxiliary/
│   ├── BACI_ISO_Codes.dta
│   ├── Classification-economies-07.dta
│   ├── Classification-economies-21.dta
│   ├── GDP-21.dta
│   └── HS2012_ISIC3.dta
└── Temp/            ← se llena solo
```

## Opción recomendada: el paquete del Banco Mundial

Todos estos archivos vienen dentro del paquete de reproducibilidad original, con
las mismas versiones que usaron los autores:

1. Entra en <https://reproducibility.worldbank.org/catalog/176>.
2. Descarga **RR_EAP_2024_161-v01** ("Get reproducibility package").
3. Descomprime y copia su carpeta `1_Data/` en la raíz de este repositorio.

Así los resultados coinciden con los del paper.

## Opción alternativa: fuentes originales

Útil si quieres actualizar los años o las versiones (los resultados ya no serán
idénticos al paper):

| Archivo | Fuente | Licencia |
|---|---|---|
| `BACI_HS12_Y*_V202401.csv` | [BACI, CEPII](http://www.cepii.fr/CEPII/en/bdd_modele/bdd_modele_item.asp?id=37), nomenclatura HS 2012 | Etalab 2.0 |
| `GTA-OCT-23.csv` | [Global Trade Alert](https://www.globaltradealert.org/data_extraction), "2008 to latest" | CC BY-NC 4.0 |
| `DTA 2.0 - Vertical Content (v2).xlsx` | [Deep Trade Agreements, Banco Mundial](https://datatopics.worldbank.org/dta/) | CC BY-NC 4.0 |
| `Auxiliary/*`, `GTA_NIPO.xlsx`, `Standard Report - Imports.csv` | Paquete original (clasificaciones de países, PIB, correspondencia HS–ISIC) | — |

Si cambias los nombres de los archivos (por ejemplo, otra versión de BACI),
ajústalos en los pasos 2 y 4.

## Requisitos de máquina

- Unos **16 GB de RAM** para el paso 4 y las regresiones (la base final tiene
  ~15 millones de filas × 23 columnas).
- El paquete original tarda unas 15 horas en Stata; en Python el cuello de
  botella es la Tabla 8.
