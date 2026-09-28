"""ISTAT - Matrice del pendolarismo 2011 (dernier millésime publié) : flux domicile-travail/études entre communes.
Enregistrements de type S (totaux par strate) ; les codes communes sont ceux de 2011."""
import glob
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, meta, save  # noqa: E402

f = glob.glob(os.path.join(ROOT, "raw", "istat_pendolarismo", "*", "*", "matrix_pendo2011_*.txt"))[0]
rows = []
with open(f, encoding="latin-1") as fh:
    for line in fh:
        t = line.split()
        if t[0] != "S":
            continue
        # S, tipo_res, prov_res, com_res, sesso, motivo, luogo, prov_dest, com_dest, stato_est, ..., numero
        rows.append((t[2] + t[3], t[5], t[6], t[7] + t[8], t[9], float(t[-1]) if t[-1] not in ("ND",) else None))
d = pd.DataFrame(rows, columns=["cod_istat_residence_2011", "motif", "lieu", "cod_istat_destination_2011", "etat_etranger", "n"])
d["motif"] = d.motif.map({"1": "etudes", "2": "travail"})
d.loc[d.lieu == "3", "cod_istat_destination_2011"] = "ETRANGER"
od = d.groupby(["cod_istat_residence_2011", "cod_istat_destination_2011", "motif"])["n"].sum().unstack(fill_value=0).reset_index()
od.columns.name = None
M = meta("ISTAT - Matrice del pendolarismo 2011 (Censimento 2011)",
         "https://www.istat.it/storage/cartografia/matrici_pendolarismo/matrici_pendolarismo_2011.zip", "2011")
save(od, "pendolarisme_od_2011", M)
tr = d[d.motif == "travail"]
res = tr.groupby("cod_istat_residence_2011")["n"].sum()
same = tr[tr.lieu == "1"].groupby("cod_istat_residence_2011")["n"].sum()
inflow = tr[tr.lieu == "2"].groupby("cod_istat_destination_2011")["n"].sum()
synth = pd.DataFrame({"actifs_residents_navetteurs_travail": res, "travaillant_dans_leur_commune": same,
                      "entrants_travail_autres_communes": inflow}).fillna(0).reset_index().rename(columns={"index": "cod_istat_2011"})
save(synth, "pendolarisme_synthese_communes_2011", M)
print("OD:", od.shape, "| total travail:", int(tr.n.sum()), "| total études:", int(d[d.motif == 'etudes'].n.sum()))
