"""Sites UNESCO en Italie via Wikidata (P757 = identifiant Patrimoine mondial). whc.unesco.org bloque les robots (Cloudflare) :
source NON OFFICIELLE, à valider avec la liste UNESCO."""
import json
import os
import sys

import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, TODAY, meta, save  # noqa: E402

Q = """SELECT ?item ?itemLabel ?whc ?coord ?adminLabel ?istat WHERE {
  ?item wdt:P757 ?whc ; wdt:P17 wd:Q38 .
  OPTIONAL { ?item wdt:P625 ?coord }
  OPTIONAL { ?item wdt:P131 ?admin . OPTIONAL { ?admin wdt:P635 ?istat } }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "it,fr,en". }
}"""
p = os.path.join(ROOT, "raw", "wikidata_unesco", TODAY)
os.makedirs(p, exist_ok=True)
f = os.path.join(p, "unesco_it.json")
if not os.path.exists(f):
    r = requests.get("https://query.wikidata.org/sparql", params={"query": Q, "format": "json"},
                     headers={"User-Agent": "MKG-EtudeMarche-IT/1.0 (contact etudes@mkg-group.com)"}, timeout=300)
    r.raise_for_status()
    open(f, "wb").write(r.content)
b = json.load(open(f))["results"]["bindings"]
d = pd.DataFrame([{k: v["value"] for k, v in x.items()} for x in b])
d[["lon", "lat"]] = d["coord"].str.extract(r"Point\(([-\d.]+) ([-\d.]+)\)").astype(float)
d = d.rename(columns={"itemLabel": "nom", "whc": "id_unesco", "adminLabel": "entite_administrative", "istat": "cod_istat",
                      "item": "wikidata"}).drop(columns=["coord"])
# rattachement à la commune par point-dans-polygone (contours ISTAT 2026) ; cod_istat Wikidata conservé à part
import geopandas as gpd  # noqa: E402
com = gpd.read_file(os.path.join(ROOT, "data", "it", "communes_it.geojson"))[["cod_istat", "geometry"]]
pts = gpd.GeoDataFrame(d, geometry=gpd.points_from_xy(d.lon, d.lat), crs=4326)
j = gpd.sjoin(pts, com.rename(columns={"cod_istat": "cod_istat_geo"}), how="left", predicate="within")
d["cod_istat_wikidata_entite"] = d["cod_istat"]
d["cod_istat"] = j["cod_istat_geo"].values
M = meta("Wikidata (P757 identifiant Patrimoine mondial UNESCO) - source non officielle", "https://query.wikidata.org/", TODAY)
save(d, "sites_unesco_wikidata", M)
print(len(d), "lignes |", d.id_unesco.nunique(), "biens/composantes UNESCO distincts | avec coord:", d.lat.notna().sum())
