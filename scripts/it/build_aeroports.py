"""Assaeroporti : trafic mensuel et cumulé par aéroport (mouvements, passagers nationaux/internationaux/UE, fret)."""
import os
import re
import sys

import pandas as pd
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import meta, save  # noqa: E402
from dl import get  # noqa: E402

URL = "https://assaeroporti.com/statistiche/?selectedYear={y}&month={m}"


def num(x):
    x = str(x).strip().replace(".", "").replace(",", ".")
    try:
        return float(x)
    except ValueError:
        return None


rows = []
for y in range(2012, 2027):
    for m in range(1, 13):
        if (y, m) > (2026, 7):
            break
        try:
            p = get(URL.format(y=y, m=m), "assaeroporti", f"statistiche_{y}_{m:02d}.html")
        except Exception as e:
            print("ERR", y, m, e)
            continue
        s = BeautifulSoup(open(p, encoding="utf-8", errors="ignore").read(), "lxml")
        for t in s.find_all("table"):
            tr = [[c.get_text(" ", strip=True) for c in r.find_all(["td", "th"])] for r in t.find_all("tr")]
            if len(tr) < 3:
                continue
            titre = tr[0][0] if len(tr[0]) == 1 else "TOTALI " + ("MESE" if "MESE" in str(tr) else "")
            hdr, body = (tr[1], tr[2:]) if len(tr[0]) == 1 else (tr[0], tr[1:])
            per = re.search(r"(\w+ - )?(\w+) (\d{4})", titre)
            for r in body:
                if len(r) != len(hdr) or not r[0].isdigit() and r[0] != "":
                    if not (r and r[1:2] and "Totale" in " ".join(r[:2])):
                        continue
                rec = {"annee": y, "mois": m, "tableau": re.sub(r"\s+", " ", titre).strip(),
                       "aeroport": re.sub(r"\s*\(.*?\)\s*", " ", r[1]).strip(), "note_source": " ".join(re.findall(r"\(.*?\)", r[1]))}
                for i, h in enumerate(hdr[2:], start=2):
                    k = h if h != "%" else hdr[i - 1] + " - variation % vs année précédente"
                    rec[k] = num(r[i])
                rows.append(rec)
d = pd.DataFrame(rows)
M = meta("Assaeroporti - Dati di traffico (statistiche mensili per aeroporto)", "https://assaeroporti.com/statistiche/",
         "2012-01 à 2026-07")
d["millesime"] = d["annee"].astype(str) + "-" + d["mois"].astype(str).str.zfill(2)
save(d, "aeroports_trafic_assaeroporti", M)
print(d.shape, d.tableau.value_counts().head(10).to_dict())
