"""Offre hébergement nominative : BDSR Ministero del Turismo + registres régionaux open data (via CKAN dati.gov.it)."""
import json, os, re
from dl import get, ROOT
rows = json.load(open(get("https://www.dati.gov.it/opendata/api/3/action/package_search?q=strutture%20ricettive&rows=1000",
                          "dati_gov_ckan", "package_search_strutture_ricettive.json")))["result"]["results"]
WANT = [  # (organisation, motif titre)
    ("Ministero del Turismo", r"^Banca Dati Strutture Ricettive"),
    ("Regione Piemonte", r"^Strutture ricettive Open Data$"),
    ("Regione Puglia", r"Elenco delle Strutture Ricettive e delle Locazioni"),
    ("Regione Emilia Romagna", r"^Strutture ricettive$"),
    ("Regione Lombardia", r"^strutture_ricettive$"),
    ("Regione Campania", r"Elenco Strutture Ricettive al 30/04/2024"),
    ("Regione Calabria", r"^Strutture ricettive$"),
    ("Regione Lazio", r"Strutture ricettive a 5 stelle"),
    ("Regione Marche", r"^strutture ricettive 2026$"),
    ("Regione Toscana", r"^Strutture ricettive$"),
    ("Regione Veneto", r"."),
    ("Regione Friuli Venezia-Giulia", r"."),
    ("Provincia Autonoma di Trento", r"(?i)strutture|esercizi|elenco"),
    ("Regione Siciliana", r"."),
    ("Regione Umbria", r"."),
]
man = []
for pk in rows:
    org = (pk.get("organization") or {}).get("title", "")
    for o, pat in WANT:
        if org == o and re.search(pat, pk["title"]):
            res = [r for r in pk.get("resources", []) if (r.get("format") or "").upper() in ("CSV", "GEOJSON", "JSON", "XLSX")]
            res.sort(key=lambda r: ["CSV", "XLSX", "GEOJSON", "JSON"].index((r.get("format") or "").upper()))
            for r in (res if o == "Ministero del Turismo" else res[:1]):
                if o == "Ministero del Turismo" and (r.get("format") or "").upper() != "CSV":
                    continue
                name = re.sub(r"\W+", "_", f"{org}_{pk['title']}")[:90] + "." + (r.get("format") or "csv").lower()
                try:
                    p = get(r["url"], "offre_" + re.sub(r"\W+", "_", org.lower())[:30], name)
                    man.append(dict(org=org, titre=pk["title"], url=r["url"], fichier=os.path.relpath(p, ROOT),
                                    maj=pk.get("metadata_modified", "")[:10], format=r.get("format"), taille=os.path.getsize(p)))
                    print("OK", org, "|", pk["title"][:60], "|", os.path.getsize(p), flush=True)
                except Exception as e:
                    print("ERR", org, pk["title"][:60], str(e)[:120], flush=True)
os.makedirs(os.path.join(ROOT, "raw", "offre_manifest"), exist_ok=True)
json.dump(man, open(os.path.join(ROOT, "raw", "offre_manifest", "manifest.json"), "w"), ensure_ascii=False, indent=1)
