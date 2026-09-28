"""MEF - Dipartimento delle Finanze : Redditi e principali variabili IRPEF su base comunale (open data), toutes années."""
import glob
import io
import os
import re
import sys
import zipfile

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, NA, meta, save  # noqa: E402
from dl import get  # noqa: E402

URL = ("https://www1.finanze.gov.it/finanze/analisi_stat/public/v_4_0_0/contenuti/"
       "Redditi_e_principali_variabili_IRPEF_su_base_comunale_CSV_{y}.zip")
FR = [("Numero contribuenti", "nb_contribuables"), ("Reddito da fabbricati", "revenus_fonciers"),
      ("Reddito da lavoro dipendente e assimilati", "revenus_salaires"), ("Reddito da pensione", "pensions"),
      ("Reddito da lavoro autonomo", "revenus_travail_independant"),
      ("contabilita' ordinaria", "revenus_entrepreneur_compta_ordinaire"),
      ("contabilita' semplificata", "revenus_entrepreneur_compta_simplifiee"),
      ("Reddito da partecipazione", "revenus_participation"), ("Reddito imponibile addizionale", "revenu_imposable_addizionale"),
      ("Reddito imponibile", "revenu_imposable"), ("Imposta netta", "impot_net"), ("Trattamento spettante", "bonus_irpef"),
      ("Addizionale regionale", "addizionale_regionale"), ("Addizionale comunale", "addizionale_comunale"),
      ("minore o uguale a zero", "rc_inf_egal_0"), ("da 0 a 10000", "rc_0_10k"), ("da 10000 a 15000", "rc_10k_15k"),
      ("da 15000 a 26000", "rc_15k_26k"), ("da 26000 a 55000", "rc_26k_55k"), ("da 55000 a 75000", "rc_55k_75k"),
      ("da 75000 a 120000", "rc_75k_120k"), ("oltre 120000", "rc_sup_120k"), ("Reddito complessivo", "revenu_complessivo")]


def rename(c):
    for k, v in FR:
        if k in c:
            suf = "_nb" if c.endswith("Frequenza") else ("_eur" if "Ammontare" in c else "")
            return v + suf
    return {"Anno di imposta": "annee_imposition", "Codice catastale": "code_cadastral_belfiore",
            "Codice Istat Comune": "cod_istat", "Denominazione Comune": "commune_mef", "Sigla Provincia": "sigle_province",
            "Regione": "region", "Codice Istat Regione": "code_region"}.get(c.strip(), c.strip())


rows = []
for y in range(2012, 2031):
    try:
        p = get(URL.format(y=y), "mef_irpef")
    except Exception:
        continue
    z = zipfile.ZipFile(p)
    raw = z.read([n for n in z.namelist() if n.lower().endswith(".csv")][0])
    d = pd.read_csv(io.BytesIO(raw), sep=";", dtype=str, encoding="latin-1", index_col=False, **NA)
    d = d[[c for c in d.columns if c.strip()]]
    d.columns = [rename(c) for c in d.columns]
    d["cod_istat"] = d["cod_istat"].str.zfill(6)
    rows.append(d)
    print(y, d.shape, flush=True)
d = pd.concat(rows, ignore_index=True)
num = [c for c in d.columns if c.endswith(("_nb", "_eur")) or c == "nb_contribuables"]
for c in num:
    d[c] = pd.to_numeric(d[c].str.replace(",", ".", regex=False), errors="coerce")
# CALCUL (signalé) : revenu moyen brut annuel du travail salarié = montant / nombre de déclarants
d["CALCUL_revenu_moyen_salarie_eur"] = (d["revenus_salaires_eur"] / d["revenus_salaires_nb"]).round(0)
d["CALCUL_revenu_complessivo_moyen_eur"] = (d["revenu_complessivo_eur"] / d["revenu_complessivo_nb"]).round(0)
M = meta("MEF - Dipartimento delle Finanze, Dichiarazioni IRPEF - dati per comune (open data)",
         "https://www1.finanze.gov.it/finanze/analisi_stat/public/index.php?opendata=yes",
         f"années d'imposition {d.annee_imposition.min()}-{d.annee_imposition.max()}")
d["millesime"] = d["annee_imposition"]
save(d, "revenus_irpef_communes", M)
last = d[d.annee_imposition == d.annee_imposition.max()]
print("lignes", len(d), "| dernière année", d.annee_imposition.max(), "communes", last.cod_istat.nunique(),
      "| total revenu complessivo (Md€)", round(last.revenu_complessivo_eur.sum() / 1e9, 1))
