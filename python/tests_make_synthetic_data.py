"""Datos SINTÉTICOS (no reales) para probar el pipeline completo (pasos 1-6).

Uso: python python/tests_make_synthetic_data.py <carpeta_raiz>
OJO: escribe en <carpeta_raiz>/1_Data; no lo uses sobre tus datos reales.

Datos sintéticos coherentes para correr todo el pipeline (pasos 1-6)."""
import sys, numpy as np, pandas as pd
from pathlib import Path
root = Path(sys.argv[1]); rng = np.random.default_rng(7)
RAW, AUX = root/"1_Data/Raw_data", root/"1_Data/Auxiliary"
if any(RAW.glob("*")) or any(AUX.glob("*")):
    sys.exit(f"Ya hay archivos en {RAW} o {AUX}: no se sobrescriben (¿son tus datos reales?).")
RAW.mkdir(parents=True, exist_ok=True); AUX.mkdir(parents=True, exist_ok=True)
# (ISO3, código BACI, nombre BM, nombre GTA, ingreso 2021, región, ln gdp)
P = [("USA",842,"United States","United States of America","High income","North America",11.1),
     ("CHN",156,"China","China","Upper middle income","East Asia & Pacific",9.8),
     ("DEU",276,"Germany","Germany","High income","Europe & Central Asia",10.9),
     ("KOR",410,"Korea, Rep.","Republic of Korea","High income","East Asia & Pacific",10.7),
     ("TUR",792,"Türkiye","Turkey","Upper middle income","Europe & Central Asia",10.4),
     ("BRA",76,"Brazil","Brazil","Upper middle income","Latin America & Caribbean",9.6),
     ("IND",699,"India","India","Lower middle income","South Asia",8.9),
     ("MEX",484,"Mexico","Mexico","Upper middle income","Latin America & Caribbean",9.9),
     ("FSM",583,"Micronesia, Fed. Sts.","Micronesia","Lower middle income","East Asia & Pacific",8.2)]
HS = [870210+i for i in range(8)] + [848610+i*10 for i in range(6)] + [300410+i for i in range(6)]
ISIC = {h: (34 if h < 848000 else 29 if h < 860000 else 24) for h in HS}
# --- Clasificaciones / auxiliares
pd.DataFrame({"Economy":[p[2] for p in P]+["Anguilla"],"Code":[p[0] for p in P]+["AIA"],
              "Incomegroup":["High income" if p[4]=="High income" else "Developing" for p in P]+["High income"],
              "Region":[p[5] for p in P]+["LAC"]}).to_stata(AUX/"Classification-economies-07.dta",write_index=False,version=118)
pd.DataFrame({"Economy":[p[0] for p in P],"Jurisdiction":[p[2] for p in P],"region":[p[5] for p in P],
              "incomegroup":[p[4] for p in P]}).to_stata(AUX/"Classification-economies-21.dta",write_index=False,version=118)
pd.DataFrame({"Economy":[p[0] for p in P],"gdp_pc":[np.exp(p[6]) for p in P],"ln_gdp_pc":[p[6] for p in P]}).to_stata(AUX/"GDP-21.dta",write_index=False,version=118)
iso = pd.DataFrame({"country_code":[p[1] for p in P],"country_iso3":[p[0] for p in P]})
iso["i"]=iso.country_code; iso["j"]=iso.country_code; iso["IMP"]=iso.country_iso3; iso["EXP"]=iso.country_iso3
iso.to_stata(AUX/"BACI_ISO_Codes.dta",write_index=False,version=118)
pd.DataFrame({"HS2012":HS,"ISIC3_2":[ISIC[h] for h in HS]}).to_stata(AUX/"HS2012_ISIC3.dta",write_index=False,version=118)
# --- GTA (como lo exporta R: primera columna = índice sin nombre)
tipos = ["Financial grant","State loan","Import tariff","Anti-dumping","Export ban","Production subsidy",
         "Instrument unclear","Local content requirement","Export tax","Some other type"]
mast = {"Financial grant":"L: Subsidies (excl. export subsidies)","State loan":"L: Subsidies (excl. export subsidies)",
        "Import tariff":"Tariff measures","Anti-dumping":"D: Contingent trade-protective measures","Export ban":"P: Export-related measures",
        "Production subsidy":"L: Subsidies (excl. export subsidies)","Instrument unclear":"Instrument unclear",
        "Local content requirement":"I: Trade-related investment measures","Export tax":"P: Export-related measures","Some other type":"M: Government procurement restrictions"}
filas = []
for iid in range(1, 401):
    impl = P[rng.integers(0,8)][3] if rng.random() > 0.03 else rng.choice(["Anguilla","NA"])
    tipo = rng.choice(tipos); y = int(rng.integers(2008, 2024))
    prods = ", ".join(map(str, sorted(rng.choice(HS, size=rng.integers(1, 15), replace=False))))
    if rng.random() < 0.05: prods = "NA"
    afectados = rng.choice([p[3] for p in P] + ["NA", "Antigua & Barbuda"], size=rng.integers(1, 4), replace=False)
    for aff in afectados:
        filas.append({"State Act ID": iid//3, "Intervention ID": iid, "State Act Title": f"Measure {iid} " + "x"*rng.integers(0,300),
            "Announcement Date": f"{y}-01-15", "GTA Evaluation": rng.choice(["Red","Green","Amber"], p=[.6,.3,.1]),
            "Currently in force": rng.choice(["Yes","No"]), "Inception Date": f"{y}-03-01" if rng.random()>.03 else "NA",
            "Removal Date": "NA", "Implementing Jurisdiction": impl, "Implementation Level": "National",
            "Eligible Firms": "all", "Intervention Type": tipo, "MAST chapter": mast[tipo],
            "Affected Sectors": "NA", "Affected Products": prods, "Affected Jurisdiction": aff})
gta = pd.DataFrame(filas); gta = pd.concat([gta, gta.iloc[:5]], ignore_index=True)   # duplicados exactos
gta.index = gta.index + 1; gta.to_csv(RAW/"GTA-OCT-23.csv", index_label="")
# --- BACI
for y in range(2012, 2023):
    rows = [(y, a[1], b[1], h, float(rng.lognormal(7.2, 1.0)), "NA") for a in P for b in P if a != b for h in HS if rng.random() < .85]
    pd.DataFrame(rows, columns=list("tijkvq")).to_csv(RAW/f"BACI_HS12_Y{y}_V202401.csv", index=False)
# --- DTA (paso 1)
prov = [{"Area":"Subsidies","Coding":f"SUB_{q:02d}","Provision":f"p{q}", **{f"agree_{w}": str(int(rng.random()<.5)) for w in range(1,6)}} for q in range(10,27)]
pares = [(a[0], b[0], w) for w, (a, b) in enumerate([(P[0],P[7]),(P[7],P[0]),(P[2],P[4]),(P[4],P[2]),(P[3],P[0]),(P[0],P[3]),(P[5],P[7]),(P[7],P[5])], start=1) if w<=5 or True]
bil = pd.DataFrame([{"WBID": (w-1)%5+1, "iso1": e, "iso2": m, "year": y} for e, m, w in pares for y in range(2010, 2024)])
with pd.ExcelWriter(RAW/"DTA 2.0 - Vertical Content (v2).xlsx") as w:
    pd.DataFrame(prov).to_excel(w, sheet_name="STATA", index=False); bil.to_excel(w, sheet_name="Bilateral Information", index=False)
# --- NIPO y Census (figuras)
nipo = [{"Entry ID": k, "Jurisdiction": P[k % 8][3], "Initial assessment (change relative to status quo)": "Distortive",
         "Size of subsidy (USD million)": float(rng.integers(1, 900)), "Implementation date": pd.Timestamp(2023, int(rng.integers(1,13)), 1)}
        for k in range(1, 120) if rng.random() < (0.3 + 0.07*(k % 8))]
pd.DataFrame(nipo).to_excel(RAW/"GTA_NIPO.xlsx", sheet_name="GTA NIPO - December 2023", index=False)
out = []
for pais, base, tr in [("World Total",2e11,.002),("China",4e10,-.004),("ASEAN - Association of Southeast Asian Nations",2e10,.008),("Mexico",3e10,.007),("Canada",2.5e10,.003),("USMCA - U.S.-Mexico-Canada Agreement",5.5e10,.005)]:
    for k, p in enumerate(pd.period_range("2017-01", "2024-02", freq="M")):
        out.append({"Time": p.strftime("%b-%y"), "Country": pais, "Customs Value (Gen) ($US)": f"{base*np.exp(tr*k)*(1+.04*rng.normal()):,.0f}", "Rate Provision": "All"})
pd.DataFrame(out).to_csv(RAW/"Standard Report - Imports.csv", index=False)
print("datos sintéticos listos en", root/"1_Data")
