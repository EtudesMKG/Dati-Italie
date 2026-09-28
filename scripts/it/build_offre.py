"""Offre d'hébergement nominative : registres open data régionaux/communaux (via CKAN dati.gov.it) -> table unifiée
+ tableau de couverture. Aucune valeur complétée : champs absents de la source = vides."""
import glob
import json
import os
import re
import sys
import unicodedata

import geopandas as gpd
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, NA, TODAY, save  # noqa: E402

RAW = os.path.join(ROOT, "raw")
man = {m["fichier"].split("/")[-1]: m for m in json.load(open(os.path.join(RAW, "offre_manifest", "manifest.json")))}


def rd(pattern):
    f = sorted(glob.glob(os.path.join(RAW, pattern)))[-1]
    for enc in ("utf-8-sig", "latin-1"):
        for sep in (";", ",", "\t"):
            try:
                t = pd.read_csv(f, sep=sep, encoding=enc, dtype=str, on_bad_lines="warn", **NA)
                if t.shape[1] > 3:
                    return t, man.get(os.path.basename(f), {})
            except Exception:
                pass
    raise ValueError(f)


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def stars(s):
    m = re.search(r"(\d)\s*(stell|stars|\*)", str(s).lower())
    return m.group(1) if m else ""


def xy(geom, epsg):
    g = gpd.GeoSeries.from_wkt(geom.fillna("POINT EMPTY"), crs=epsg).to_crs(4326)
    return g.y.round(6).where(~g.is_empty), g.x.round(6).where(~g.is_empty)


ref = pd.read_parquet(os.path.join(ROOT, "data", "it", "referentiel_communes.parquet"))
ref["k"] = ref["commune"].map(norm) + "|" + ref["sigle_province"]
ref["k2"] = ref["commune"].map(norm)
uniq = ref.drop_duplicates("k2", keep=False).set_index("k2")["cod_istat"]
bykey = ref.set_index("k")["cod_istat"]
SIG = dict(zip(ref["province_uts"].map(norm), ref["sigle_province"]))
SIG.update({"bolzano": "BZ", "reggio emilia": "RE", "monza e brianza": "MB"})


def cod(commune, prov=None):
    k2 = norm(commune)
    if prov is not None:
        sg = prov if len(str(prov)) == 2 else SIG.get(norm(prov), "")
        c = bykey.get(k2 + "|" + str(sg).upper())
        if c:
            return c
    return uniq.get(k2, "")


cols = ["region_source", "source", "url_source", "date_maj_source", "nom", "categorie", "type", "etoiles", "chambres",
        "lits", "adresse", "cap", "commune_source", "province_source", "cod_istat", "lat", "lon", "cin", "remarque"]
parts = []

v, m = rd("offre_regione_veneto/*/*.csv")
parts.append(pd.DataFrame({
    "region_source": "Veneto", "source": "Regione Veneto - Elenco strutture ricettive turistiche", "url_source": m.get("url"),
    "date_maj_source": m.get("maj"), "nom": v.DENOMINAZIONE, "categorie": v.TIPOLOGIA_SECONDARIA, "type": v.TIPOLOGIA,
    "etoiles": v.CLASSIFICAZIONE.map(stars), "chambres": v.CAMERE, "lits": v.POSTI_LETTO,
    "adresse": (v.INDIRIZZO.fillna("") + " " + v.NUMERO_CIVICO.fillna("")).str.strip(), "cap": v.CAP,
    "commune_source": v.COMUNE, "province_source": v.PROVINCIA,
    "cod_istat": [cod(c, p) for c, p in zip(v.COMUNE, v.PROVINCIA)], "cin": v.CODICE_CIN, "remarque": ""}))

c, m = rd("offre_regione_campania/*/*.csv")
parts.append(pd.DataFrame({
    "region_source": "Campania", "source": "Regione Campania - Elenco strutture ricettive al 30/04/2024", "url_source": m.get("url"),
    "date_maj_source": "2024-04-30", "nom": c.Denominazione, "categorie": c.Tipologia,
    "type": (c.Sottotipo.fillna("") + " " + c.Categoria.fillna("")).str.strip(),
    "etoiles": c.Classificazione.map(stars), "chambres": c["Numero camere"], "lits": c["Numero posti letto"],
    "adresse": (c.Indirizzo.fillna("") + " " + c["N. Civico"].fillna("")).str.strip(), "cap": c.CAP,
    "commune_source": c.Comune, "province_source": c.Provincia,
    "cod_istat": [cod(a, b) for a, b in zip(c.Comune, c.Provincia)], "cin": "", "remarque": "code CUSR: " + c["Codice Unico CUSR"]}))

lo, m = rd("offre_regione_lombardia/*/*.csv")
la, ln = xy(lo.the_geom, 4326)
parts.append(pd.DataFrame({
    "region_source": "Lombardia (province Monza-Brianza seulement)", "source": "Provincia Monza Brianza - Strutture ricettive",
    "url_source": m.get("url"), "date_maj_source": m.get("maj"), "nom": lo.NOME, "categorie": lo.CATEGORIA,
    "type": lo.CLASSIFICA, "etoiles": lo.CLASSIFICA.map(stars), "chambres": "", "lits": "", "adresse": lo.INDIRIZZO,
    "cap": lo.CAP, "commune_source": lo.COMUNE, "province_source": lo.PROVINCIA,
    "cod_istat": lo.ISTAT.fillna("").str.zfill(6).where(lo.ISTAT.notna(), [cod(a, "MB") for a in lo.COMUNE]),
    "lat": la, "lon": ln, "cin": "", "remarque": ""}))

e, m = rd("offre_regione_emilia_romagna/*/*.csv")
e = e[e.ATTIVA.str.upper() == "SI"]
la, ln = xy(e.SHAPE, 3003)
parts.append(pd.DataFrame({
    "region_source": "Emilia-Romagna (commune de Bologna seulement)", "source": "Comune di Bologna - Strutture ricettive (actives)",
    "url_source": m.get("url"), "date_maj_source": e.DATA_ULTIMO_AGGIORNAMENTO, "nom": "", "categorie": e.CATEGORIA,
    "type": e.TIPOLOGIA, "etoiles": "", "chambres": e.NRCAMERE, "lits": e.NRLETTI,
    "adresse": (e.DENOMINAZIONE_VIA.fillna("") + " " + e.CIVICO.fillna("")).str.strip(), "cap": "",
    "commune_source": "Bologna", "province_source": "BO", "cod_istat": "037006", "lat": la, "lon": ln, "cin": "",
    "remarque": "nom non publié par la source"}))

lz, m = rd("offre_regione_lazio/*/*.csv")
parts.append(pd.DataFrame({
    "region_source": "Lazio (hôtels 5 étoiles de Roma seulement)", "source": "Roma Capitale / Regione Lazio - Strutture ricettive a 5 stelle",
    "url_source": m.get("url"), "date_maj_source": m.get("maj"), "nom": lz.INSEGNA, "categorie": lz.TIPOLOGIA,
    "type": lz.CATEGORIA, "etoiles": lz.CATEGORIA.map(stars), "chambres": lz.CAMERE, "lits": "", "adresse": lz.INDIRIZZO,
    "cap": "", "commune_source": "Roma", "province_source": "RM", "cod_istat": "058091", "cin": "",
    "remarque": lz.MUNICIPIO}))

fv, m = rd("offre_regione_friuli_venezia_giulia/*/*Sociale.csv")
parts.append(pd.DataFrame({
    "region_source": "Friuli-Venezia Giulia (structures à caractère social seulement)",
    "source": "Regione FVG - Strutture ricettive a carattere sociale", "url_source": m.get("url"), "date_maj_source": m.get("maj"),
    "nom": fv.DENOMINAZIONE, "categorie": "struttura ricettiva a carattere sociale", "type": "", "etoiles": "",
    "chambres": "", "lits": "", "adresse": "", "cap": "", "commune_source": fv.COMUNE, "province_source": fv.PROVINCIA,
    "cod_istat": [cod(a, b) for a, b in zip(fv.COMUNE, fv.PROVINCIA)], "cin": "", "remarque": ""}))

f = sorted(glob.glob(os.path.join(RAW, "offre_regione_toscana/*/*")))[-1]
t = gpd.read_file(f)
t = t.set_crs(3003, allow_override=True).to_crs(4326)
parts.append(pd.DataFrame({
    "region_source": "Toscana (commune de Firenze seulement)", "source": "Comune di Firenze - Strutture ricettive (GeoJSON)",
    "url_source": man.get(os.path.basename(f), {}).get("url"), "date_maj_source": man.get(os.path.basename(f), {}).get("maj"),
    "nom": "", "categorie": t.tipologiaattivita, "type": "", "etoiles": "", "chambres": "", "lits": "", "adresse": "",
    "cap": "", "commune_source": "Firenze", "province_source": "FI", "cod_istat": "048017",
    "lat": t.geometry.y.round(6), "lon": t.geometry.x.round(6), "cin": "",
    "remarque": "nom non publié par la source ; coordonnées converties EPSG:3003 -> 4326"}))

off = pd.concat([p.reindex(columns=cols) for p in parts], ignore_index=True)
off["cod_istat"] = off["cod_istat"].fillna("").astype(str).replace({"000000": ""})
for c_ in ["nom", "chambres", "lits", "etoiles", "cin", "adresse", "cap", "type", "remarque"]:
    off[c_] = off[c_].replace("", pd.NA)
off["date_extraction"] = TODAY
off["millesime"] = off["date_maj_source"]
save(off, "offre_hebergement_nominative", {})
cov = off.groupby("region_source").agg(etablissements=("source", "size"), avec_cod_istat=("cod_istat", lambda s: (s != "").sum()),
                                       avec_nom=("nom", lambda s: s.notna().sum()), avec_coord=("lat", lambda s: s.notna().sum()),
                                       avec_chambres=("chambres", lambda s: s.notna().sum()),
                                       date_maj=("date_maj_source", "max")).reset_index()
cov["part_jointe_cod_istat_%"] = (cov.avec_cod_istat / cov.etablissements * 100).round(1)
save(cov, "offre_couverture_regions", {"date_extraction": TODAY})
print(cov.to_string())
