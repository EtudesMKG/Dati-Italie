"""MiC - Luoghi della cultura (DB Unico) via SPARQL dati.cultura.gov.it : nom, catégorie, adresse, commune, coordonnées."""
import json
import os
import re
import sys
import time
import unicodedata

import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, TODAY, meta, save  # noqa: E402

UA = {"User-Agent": "MKG-EtudeMarche-IT/1.0 (collecte open data officielle; contact etudes@mkg-group.com)",
      "Accept": "application/sparql-results+json"}
EP = "https://dati.cultura.gov.it/sparql"
Q = """PREFIX cis: <http://dati.beniculturali.it/cis/>
PREFIX l0: <https://w3id.org/italia/onto/l0/>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX geo: <http://www.w3.org/2003/01/geo/wgs84_pos#>
PREFIX clv: <https://w3id.org/italia/onto/CLV/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?s ?id ?nom ?type ?adresse ?cp ?ville ?prov ?reg ?lat ?lon WHERE {
  ?s dc:type ?type .
  FILTER(?type = "%s")
  OPTIONAL { ?s l0:identifier ?id }
  OPTIONAL { ?s cis:institutionalCISName ?nom }
  OPTIONAL { ?s geo:lat ?lat ; geo:long ?lon }
  OPTIONAL { ?s cis:hasSite ?site . ?site cis:siteAddress ?a .
             OPTIONAL { ?a clv:fullAddress ?adresse } OPTIONAL { ?a clv:postCode ?cp }
             OPTIONAL { ?a clv:hasCity ?ville } OPTIONAL { ?a clv:hasProvince ?prov } OPTIONAL { ?a clv:hasRegion ?reg } }
} ORDER BY ?s LIMIT 2000 OFFSET %d"""
raw_dir = os.path.join(ROOT, "raw", "mic_luoghi", TODAY)
os.makedirs(raw_dir, exist_ok=True)
TYPES = ["Museo, Galleria e/o raccolta", "Area Archeologica", "Parco Archeologico", "Monumento",
         "Chiesa o edificio di culto", "Villa o Palazzo di interesse storico o artistico", "Architettura Civile",
         "Architettura Fortificata", "Parco o Giardino di interesse storico o artistico"]
rows = []
for ti, T in enumerate(TYPES):
  off = 0
  while True:
    p = os.path.join(raw_dir, f"sparql_type{ti}_offset_{off}.json")
    if not os.path.exists(p):
        for essai in range(4):
            r = requests.get(EP, params={"query": Q % (T, off), "format": "json"}, headers=UA, timeout=600)
            if r.ok:
                break
            time.sleep(10 * (essai + 1))
        r.raise_for_status()
        open(p, "wb").write(r.content)
        time.sleep(1)
    b = json.load(open(p))["results"]["bindings"]
    rows += [{k: v["value"] for k, v in x.items()} for x in b]
    if len(b) < 2000:
        break
    off += 2000
d = pd.DataFrame(rows)
for c_ in ["nom", "adresse", "cp", "ville", "prov", "reg", "lat", "lon"]:
    if c_ not in d.columns:
        d[c_] = pd.NA
last = lambda s: s.fillna("").map(lambda u: re.sub(r"_", " ", u.rsplit("/", 1)[-1]))  # noqa: E731
d["commune_source"], d["province_source"], d["region_source"] = last(d["ville"]), last(d["prov"]), last(d["reg"])
d = d.drop(columns=["ville", "prov", "reg"]).drop_duplicates(["s", "type"])
# Catégories alignées sur l'appli française
CAT = [(r"Museo|Galleria|raccolta", "Musée"), (r"Area Archeologica|Parco Archeologico", "Site historique - archéologie"),
       (r"Monumento|Architettura|Villa o Palazzo|Chiesa|edificio di culto", "Site historique - monument"),
       (r"Parco o Giardino", "Parc / jardin historique"), (r"Archivio|Biblioteca", "Archive / bibliothèque"), (r"^Altro$", "Autre lieu culturel")]
d["categorie_fr"] = d["type"].map(lambda t: next((c for p, c in CAT if re.search(p, t)), "Autre"))
d = d[d["categorie_fr"] != "Autre"].copy()  # exclut les objets de collections (fossiles, minéraux...) mal typés


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


ref = pd.read_parquet(os.path.join(ROOT, "data", "it", "referentiel_communes.parquet"))
ref["kc"], ref["kp"] = ref.commune.map(norm), ref.province_uts.map(norm)
by2 = ref.set_index(ref.kc + "|" + ref.kp)["cod_istat"]
by1 = ref.drop_duplicates("kc", keep=False).set_index("kc")["cod_istat"]
byprov = ref.groupby("kp")[["kc", "cod_istat"]].apply(lambda x: list(zip(x.kc, x.cod_istat))).to_dict()


def match(c, p):
    k, kp = norm(c), norm(p)
    r = by2.get(k + "|" + kp) or by1.get(k)
    if r:
        return r
    # noms bilingues (ex. 'Bolzano Bozen', 'Merano Meran') : nom italien du référentiel en préfixe, même province
    kp1 = kp.split(" ")[0]
    cands = [cc for kpp, lst in byprov.items() if kpp.split(" ")[0] == kp1 for kc, cc in lst if k.startswith(kc + " ")]
    return cands[0] if len(cands) == 1 else ""


d["cod_istat"] = [match(c, p) for c, p in zip(d.commune_source, d.province_source)]
d = d.rename(columns={"id": "identifiant_mic", "nom": "nom", "type": "type_mic", "cp": "code_postal", "s": "uri"})
M = meta("MiC - Luoghi della cultura (DB Unico), Linked Open Data", "https://dati.cultura.gov.it/sparql", TODAY)
save(d, "lieux_culture_mic", M)
print(len(d), d.categorie_fr.value_counts().to_dict(), "| avec coord (source):", d.lat.notna().sum(),
      "| jointure cod_istat %:", round((d.cod_istat.fillna("") != "").mean() * 100, 1))
