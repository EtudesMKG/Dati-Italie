"""ISTAT POSAS (demo.istat.it) : population au 1er janvier par âge simple et sexe -> tranches FR (0-19/20-64/65+) et ISTAT."""
import glob
import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, NA, meta, save  # noqa: E402

out = []
for f in sorted(glob.glob(os.path.join(ROOT, "raw", "demo", "POSAS_*_it_Comuni.csv"))):
    y = int(re.search(r"POSAS_(\d{4})", f).group(1))
    d = pd.read_csv(f, sep=";", skiprows=1, dtype=str, encoding="utf-8-sig", **NA)
    d = d[d["Codice comune"].str.fullmatch(r"\d{6}", na=False)].copy()
    d["age"] = pd.to_numeric(d["Età"])
    for c in ["Totale maschi", "Totale femmine", "Totale"]:
        d[c] = pd.to_numeric(d[c])
    a = d[d.age != 999]
    tot = d[d.age == 999].set_index("Codice comune")
    g = lambda lo, hi, col="Totale": a[(a.age >= lo) & (a.age <= hi)].groupby("Codice comune")[col].sum()  # noqa: E731
    t = pd.DataFrame({
        "commune": tot["Comune"], "pop_totale": tot["Totale"], "pop_hommes": tot["Totale maschi"],
        "pop_femmes": tot["Totale femmine"],
        "pop_0_19": g(0, 19), "pop_20_64": g(20, 64), "pop_65_plus": g(65, 200),
        "pop_0_14": g(0, 14), "pop_15_64": g(15, 64), "pop_75_plus": g(75, 200),
    }).reset_index().rename(columns={"Codice comune": "cod_istat"})
    t.insert(1, "annee_1er_janvier", y)
    t["controle_somme_ages"] = (t.pop_0_19 + t.pop_20_64 + t.pop_65_plus == t.pop_totale)
    out.append(t)
d = pd.concat(out, ignore_index=True)
M = meta("ISTAT - Popolazione residente per età e sesso (POSAS), demo.istat.it", "https://demo.istat.it/app/?i=POS&l=it",
         "1er janvier 2019-2026 (2026 = estimation)")
d["millesime"] = d["annee_1er_janvier"]
save(d, "demographie_tranches_communes", M)
print(d.groupby("annee_1er_janvier").pop_totale.sum().to_dict(), "| contrôles KO:", (~d.controle_somme_ages).sum())
