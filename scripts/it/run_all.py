"""Chaîne complète Italie (idempotente : les fichiers bruts déjà présents dans raw/ ne sont pas retéléchargés).
Usage : python3 scripts/it/run_all.py"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ETAPES = [
    # Bloc 1 - référentiel et contours
    "build_referentiel.py",
    # Bloc 2 - démographie, emploi, revenus, offre
    "build_demographie.py",
    "fetch_sdmx_it.py",          # ISTAT SDMX (ASIA par taille, institutions publiques) - lent : 1 requête / 15 s
    "build_emploi.py",
    "build_revenus.py",          # MEF IRPEF par commune 2012-...
    "build_pendolarismo.py",
    "fetch_offre.py",            # registres régionaux via CKAN dati.gov.it
    "build_offre.py",
    # Bloc 3 - accessibilité, environnement touristique
    "build_aeroports.py",        # Assaeroporti
    "build_lieux_culture.py",    # MiC SPARQL
    "build_unesco.py",           # Wikidata (non officiel)
    # Bloc 4 - demande
    "build_bdi_turismo.py",      # Banca d'Italia (tableaux pivot)
    "build_occupation.py",
    # Livrable
    "build_consolidated.py",
]
if __name__ == "__main__":
    for e in ETAPES:
        t = time.time()
        print(f"=== {e}", flush=True)
        r = subprocess.run([sys.executable, os.path.join(HERE, e)], cwd=HERE)
        print(f"=== {e} : code {r.returncode} en {round(time.time() - t)} s", flush=True)
        if r.returncode != 0:
            sys.exit(r.returncode)
