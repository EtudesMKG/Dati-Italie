"""Taux d'utilisation des lits hôteliers par commune (CALCUL, signalé) = nuitées hôtelières / (lits hôteliers x jours de l'année).
Sources ISTAT : Movimento dei clienti (dati comunali) et Capacità degli esercizi ricettivi (dati comunali)."""
import calendar
import glob
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common import ROOT, meta, save  # noqa: E402
import build_excel as bx  # noqa: E402  (lecteurs des fichiers ISTAT tourisme déjà en place)

t = bx.tourisme_annuel()
c = bx.capacite(2014)
t = t[["Année", "Cod. ISTAT", "Commune", "Nuitées - Hôtellerie (esercizi alberghieri) - Total", "Flags"]]
c = c[["Année", "Cod. ISTAT", "totale alberghi - Letti", "totale alberghi - Camere", "totale alberghi - Numero"]]
d = t.merge(c, on=["Année", "Cod. ISTAT"], how="left")
d.columns = ["annee", "cod_istat", "commune", "nuitees_hotels", "flags_istat", "lits_hotels", "chambres_hotels", "hotels"]
for col in ["nuitees_hotels", "lits_hotels", "chambres_hotels", "hotels"]:
    d[col + "_statut"] = d[col].map(lambda v: v if isinstance(v, str) else "")
    d[col] = pd.to_numeric(d[col], errors="coerce")
jours = d.annee.map(lambda y: 366 if calendar.isleap(int(y)) else 365)
d["CALCUL_taux_utilisation_lits_hotels_pct"] = (d.nuitees_hotels / (d.lits_hotels * jours) * 100).round(1)
d.loc[(d.lits_hotels <= 0) | d.lits_hotels.isna(), "CALCUL_taux_utilisation_lits_hotels_pct"] = pd.NA
M = meta("CALCUL à partir d'ISTAT Movimento dei clienti (comunali) et Capacità degli esercizi ricettivi (comunali)",
         "https://esploradati.istat.it/databrowser/#/it/dw/categories/IT1,Z0700SER,1.0/SER_TOURISM", "2014-2025")
d["millesime"] = d["annee"]
save(d, "hotels_taux_utilisation_lits_communes", M)
x = d[d.annee == 2024]
print(d.shape, "| 2024 communes avec taux:", x["CALCUL_taux_utilisation_lits_hotels_pct"].notna().sum(),
      "| Italie 2024 (nuitées/lits):", round(x.nuitees_hotels.sum() / (x.lits_hotels.sum() * 366) * 100, 1), "%")
