"""Emploi au lieu de travail par commune :
- ISTAT ASIA unités locales : établissements et actifs par classe de taille (0-9, 10-49, 50-249, 250+), 2012-2023
- ISTAT Censimento permanente istituzioni pubbliche : unités locales par commune (2011, 2015, 2017, 2020)
Le personnel des institutions publiques, les non profit et l'agriculture ne sont pas diffusés par commune (voir lacunes)."""
import glob
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common import ROOT, NA, meta, save, status_split  # noqa: E402

R = os.path.join(ROOT, "raw")
CL = {"W0_9": "0-9", "W10_49": "10-49", "W50_249": "50-249", "W_GE250": "250+"}
MES = {"LU": "etablissements", "LUEMPDAA": "actifs_addetti"}
parts = [pd.read_csv(f, dtype=str, **NA) for f in glob.glob(os.path.join(R, "istat_sdmx", "*", "asia_ul_taille_*.csv"))]
tot = pd.concat([pd.read_csv(f, dtype=str, **NA) for f in glob.glob(os.path.join(R, "sdmx", "asia_ul_20*.csv"))])
tot = tot[(tot.ECON_ACTIVITY_NACE_2007 == "0010")]
tot["PERS_EMPL_SIZE_CLASS"] = "TOTAL"
d = pd.concat(parts + [tot], ignore_index=True)
d = d[d.REF_AREA.str.fullmatch(r"\d{6}", na=False)].drop_duplicates(["REF_AREA", "DATA_TYPE", "PERS_EMPL_SIZE_CLASS", "TIME_PERIOD"])
d["col"] = d.DATA_TYPE.map(MES) + "_" + d.PERS_EMPL_SIZE_CLASS.map({**CL, "TOTAL": "total"})
w = d.pivot_table(index=["REF_AREA", "TIME_PERIOD"], columns="col", values="OBS_VALUE", aggfunc="first").reset_index()
order = [f"{m}_{c}" for m in MES.values() for c in ["total", "0-9", "10-49", "50-249", "250+"]]
w = w[["REF_AREA", "TIME_PERIOD"] + [c for c in order if c in w.columns]]
w = status_split(w, [c for c in order if c in w.columns])
w = w.rename(columns={"REF_AREA": "cod_istat", "TIME_PERIOD": "annee"})
w["millesime"] = w["annee"]
M = meta("ISTAT - Registro ASIA unità locali (flux SDMX 183_285_DF_DICA_ASIAULP_7), par classe d'actifs",
         "https://esploradati.istat.it/SDMXWS/rest/data/183_285_DF_DICA_ASIAULP_7", "2012-2023")
save(w, "emploi_asia_taille_communes", M)
print("ASIA taille:", w.shape, "| communes 2023:", (w.annee == "2023").sum(),
      "| établ. 250+ 2023:", int(w.loc[w.annee == "2023", "etablissements_250+"].sum()))

ip = pd.read_csv(glob.glob(os.path.join(R, "istat_sdmx", "*", "istituzioni_pubbliche_ul_comuni.csv"))[0], dtype=str, **NA)
ip = ip[ip.REF_AREA.str.fullmatch(r"\d{6}", na=False)]
FORM = {"TOT": "total", "2430": "commune", "2500": "sante_publique", "2420": "province", "2410": "region",
        "2620": "universite", "27": "ente_pubblico_non_economico", "X30": "organes_constitutionnels_etat",
        "X2440_2450": "communaute_montagne_union_communes"}
ip = ip[ip.LEGAL_FORM.isin(FORM)]
ip["col"] = "ul_institutions_publiques_" + ip.LEGAL_FORM.map(FORM)
wi = ip.pivot_table(index=["REF_AREA", "TIME_PERIOD"], columns="col", values="OBS_VALUE", aggfunc="first").reset_index()
wi = status_split(wi, [c for c in wi.columns if c.startswith("ul_")])
wi = wi.rename(columns={"REF_AREA": "cod_istat", "TIME_PERIOD": "annee"})
wi["millesime"] = wi["annee"]
M2 = meta("ISTAT - Censimento permanente delle istituzioni pubbliche (flux 741_1099_DF_DICA_IPSTRULCOM_1)",
          "https://esploradati.istat.it/SDMXWS/rest/data/741_1099_DF_DICA_IPSTRULCOM_1", "2011, 2015, 2017, 2020")
save(wi, "institutions_publiques_ul_communes", M2)
print("Institutions publiques:", wi.shape, wi.annee.value_counts().to_dict())
