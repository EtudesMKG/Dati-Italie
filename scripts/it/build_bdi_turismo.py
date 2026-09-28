"""Banca d'Italia - Indagine sul turismo internazionale, tableaux pivot (micro-données pondérées) :
voyageurs étrangers en Italie par province visitée, motif (dont affaires), hébergement principal.
Agrégation = somme des facteurs d'extrapolation BdI (même opération que le tableau croisé publié)."""
import glob
import os
import re
import sys
import zipfile
from collections import defaultdict
from xml.etree.ElementTree import iterparse

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, meta, save  # noqa: E402

KEYS = ["ANNO", "PROVINCIA_VISITATA", "DESCR_PROV", "DESCR_REG", "DESCR_MOTIVO_AGGR", "DESCR_MOTIVO_VIAG", "DESCR_ALLOGGIO"]
VALS = ["FP_VIAG", "FPD_VIAG", "FPD_NOTTI", "FPD_SPESA_FMI"]
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def parse(zpath):
    xl = zipfile.ZipFile(zpath)
    inner = [n for n in xl.namelist() if n.lower().endswith((".xlsx", ".xls"))][0]
    if not inner.endswith(".xlsx"):
        return None
    tmp = os.path.join(os.path.dirname(zpath), inner)
    if not os.path.exists(tmp):
        xl.extract(inner, os.path.dirname(zpath))
    z = zipfile.ZipFile(tmp)
    dfn = z.read("xl/pivotCache/pivotCacheDefinition1.xml").decode("utf-8")
    fields, shared = [], []
    for m in re.finditer(r'<cacheField name="([^"]+)"[^>]*>(.*?)</cacheField>|<cacheField name="([^"]+)"[^>]*/>', dfn, re.S):
        name = m.group(1) or m.group(3)
        fields.append(name)
        shared.append(re.findall(r'<[smnb] v="([^"]*)"', m.group(2) or ""))
    idx = {f: i for i, f in enumerate(fields)}
    agg = defaultdict(lambda: [0.0] * len(VALS))
    with z.open("xl/pivotCache/pivotCacheRecords1.xml") as fh:
        for ev, el in iterparse(fh):
            if el.tag != NS + "r":
                continue
            cells = list(el)
            val = []
            for i, c in enumerate(cells):
                v = c.get("v")
                if c.tag == NS + "x":
                    v = shared[i][int(v)] if v is not None and int(v) < len(shared[i]) else ""
                val.append(v)
            k = tuple(val[idx[f]] if f in idx else "" for f in KEYS)
            a = agg[k]
            for j, f in enumerate(VALS):
                if f in idx:
                    try:
                        a[j] += float(val[idx[f]] or 0)
                    except ValueError:
                        pass
            el.clear()
    return pd.DataFrame([list(k) + v for k, v in agg.items()], columns=KEYS + VALS)


out = []
for z in sorted(glob.glob(os.path.join(ROOT, "raw", "bancaditalia", "*", "PIVOT_STRANIERI_*.zip"))):
    if not re.search(r"(2017_2019|2020|2021_2025)", z):
        continue
    d = parse(z)
    if d is not None:
        out.append(d)
        print(os.path.basename(z), d.shape, flush=True)
d = pd.concat(out, ignore_index=True)
d = d.rename(columns={"ANNO": "annee", "PROVINCIA_VISITATA": "code_province_bdi", "DESCR_PROV": "province_visitee",
                      "DESCR_REG": "region_visitee", "DESCR_MOTIVO_AGGR": "motif_agrege", "DESCR_MOTIVO_VIAG": "motif_detaille",
                      "DESCR_ALLOGGIO": "hebergement_principal", "FP_VIAG": "voyageurs_FP_VIAG_milliers",
                      "FPD_VIAG": "voyageurs_FPD_VIAG_milliers", "FPD_NOTTI": "nuitees_milliers", "FPD_SPESA_FMI": "depenses_millions_eur"})
M = meta("Banca d'Italia - Indagine sul turismo internazionale (tabelle pivot, viaggiatori stranieri)",
         "https://www.bancaditalia.it/statistiche/tematiche/rapporti-estero/turismo-internazionale/distribuzione-microdati/tabelle-pivot/index.html",
         "2017-2025")
d["millesime"] = d["annee"]
save(d, "bdi_voyageurs_etrangers_province_motif", M)
t = d.groupby(["annee", "motif_agrege"])["nuitees_milliers"].sum().unstack()
print(t.round(0))
