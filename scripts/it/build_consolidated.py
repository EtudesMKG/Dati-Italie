"""Classeur consolidé data/it/Italie_donnees_consolidees.xlsx : un onglet par module de l'appli + Lisez-moi + Contrôles.
Réutilise les tables data/it/*.parquet et les lecteurs ISTAT existants (scripts/build_excel.py)."""
import glob
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
from common import ROOT, NA, OUT, TODAY  # noqa: E402
import build_excel as bx  # noqa: E402

P = lambda n: pd.read_parquet(os.path.join(OUT, n + ".parquet"))  # noqa: E731
ref = P("referentiel_communes")
NOM = ref.set_index("cod_istat")["commune"]


def fix(df, code="cod_istat"):
    """Restaure le nom 'None' (commune 001168) si un lecteur l'a transformé en vide ; cod_istat en texte."""
    df = df.copy()
    for c in df.columns:
        if c.lower().startswith(("cod_istat", "cod. istat")):
            df[c] = df[c].astype("string")
    for cc, nc in [("Cod. ISTAT", "Commune"), ("Cod. ISTAT", "Commune (nom ISTAT)"), ("cod_istat", "commune")]:
        if cc in df.columns and nc in df.columns:
            m = (df[cc] == "001168") & df[nc].isna()
            df.loc[m, nc] = "None"
    return df


def meta_cols(df, src, url, mill):
    df = df.copy()
    for k, v in dict(source=src, url_source=url, date_extraction=TODAY, millesime=mill).items():
        if k not in df.columns:
            df[k] = v
    return df


ISTAT_T = "https://esploradati.istat.it/databrowser/#/it/dw/categories/IT1,Z0700SER,1.0/SER_TOURISM"
S, notes = {}, []


def add(name, df, source, url, mill, niveau, limites):
    S[name] = fix(df)
    notes.append((name, source, url, mill, niveau, limites, len(df)))


# ---------- 0. Synthèse par commune (reprise de l'ancien classeur, derniers millésimes)
_occ, _cpro, _pent, _pss = bx.occupes_recensement(), bx.condition_pro(), bx.prov_entreprises(), bx.prov_salaries_secteur()
_fl, _cc = bx.forze_lavoro_prov(), bx.camcom_imprese()
_syn = bx.synthese(bx.referentiel(), bx.demographie(), bx.asia(), bx.tourisme_annuel(), bx.capacite(2019), bx.musees(),
                   _occ, _cpro, _pent, _pss, _fl, _cc)
S_first = ("Synthèse communes", _syn)
# ---------- 1. Référentiel
add("Référentiel communes", ref, "ISTAT Elenco comuni + Confini 01/01/2026 + Altimetria + Corone urbane",
    "https://www.istat.it/classificazione/codici-dei-comuni-delle-province-e-delle-regioni/", "01/01/2026", "commune",
    "Centroïde = point intérieur du polygone ISTAT (reprojeté EPSG:32632->4326). Castegnero Nanto (024129) : contour = union "
    "des anciennes communes 024027+024071 (fusion postérieure au 01/01/2026). Variations commune par commune non "
    "téléchargeables (SITUAS = application web) : codes historiques via colonnes 2017-2025/2010-2016 + table Sardaigne.")
# ---------- 2. Démographie
add("Démographie tranches", P("demographie_tranches_communes").drop(columns=["controle_somme_ages"]),
    "ISTAT POSAS (demo.istat.it)", "https://demo.istat.it/app/?i=POS&l=it", "1er janvier 2019-2026", "commune",
    "Tranches FR 0-19/20-64/65+ et ISTAT 0-14/15-64 = sommes des âges simples publiés. 2026 = estimation ISTAT.")
add("Démographie série 2014-2026", bx.demographie(), "ISTAT reconstruction 2002-2018 + POSAS 2019-2026",
    "https://demo.istat.it/", "2014-2026", "commune", "Pop. 2014-2018 = somme des âges simples de la reconstruction ISTAT.")
add("Bilan démographique", bx.bilan(), "ISTAT demo.istat.it (P2)", "https://demo.istat.it/", "2019-2025", "commune", "")
# ---------- 3. Emploi, entreprises, revenus
add("Établissements par taille", P("emploi_asia_taille_communes"), "ISTAT ASIA unità locali (183_285_DF_DICA_ASIAULP_7)",
    "https://esploradati.istat.it/SDMXWS/rest/data/183_285_DF_DICA_ASIAULP_7", "2012-2023", "commune (lieu de travail)",
    "Équivalent de la liste nominative FR : nombre d'établissements 50-249 et 250+ par commune (pas de noms). ASIA exclut "
    "agriculture, administration publique et non profit.")
add("ASIA hôtellerie 2012-2023", bx.asia(), "ISTAT ASIA unità locali (total, I, 55, 56)",
    "https://esploradati.istat.it/SDMXWS/rest/data/183_285_DF_DICA_ASIAULP_7", "2012-2023", "commune", "")
add("Établissements par secteur", bx.asia_sections(), "ISTAT ASIA unità locali par section Ateco",
    "https://esploradati.istat.it/SDMXWS/rest/data/183_285_DF_DICA_ASIAULP_7", "2023", "commune", "")
add("Institutions publiques UL", P("institutions_publiques_ul_communes"),
    "ISTAT Censimento permanente istituzioni pubbliche (741_1099_DF_DICA_IPSTRULCOM_1)",
    "https://esploradati.istat.it/SDMXWS/rest/data/741_1099_DF_DICA_IPSTRULCOM_1", "2011, 2015, 2017, 2020", "commune",
    "Seul le NOMBRE d'unités locales est diffusé par commune ; le personnel n'est pas diffusé à ce niveau.")
add("Actifs résidents 2018-2024", bx.condition_pro(), "ISTAT Censimento permanente (DF_DCSS_ISTR_LAV_PEN_2_TV_3)",
    "https://esploradati.istat.it/", "2018-2024 (sans 2020)", "commune (résidence)", "")
add("Actifs 2021 salariés-indép.", bx.occupes_recensement(), "ISTAT Censimento permanente (DF_DCSS_EMPLP_1_COM)",
    "https://esploradati.istat.it/", "2021", "commune (résidence)", "Décimales = estimations ISTAT.")
irp = P("revenus_irpef_communes")
add("Revenus IRPEF", irp, "MEF - Dipartimento delle Finanze, IRPEF dati per comune",
    "https://www1.finanze.gov.it/finanze/analisi_stat/public/index.php?opendata=yes", "années d'imposition 2012-2024", "commune (résidence du contribuable)",
    "Colonnes CALCUL_* = montant / fréquence (revenu moyen), calcul signalé. Proxy des salaires, pas un salaire horaire.")
add("PROV Entreprises 2012-2024", bx.prov_entreprises(), "ISTAT ASIA imprese (183_277_DF_DICA_ASIAUE1P_4)",
    "https://esploradati.istat.it/", "2012-2024", "province", "Nombre d'entreprises (sièges) non diffusé par commune.")
add("PROV Entreprises taille", bx.prov_taille(), "ISTAT ASIA imprese (183_277_DF_DICA_ASIAUE1P_5)",
    "https://esploradati.istat.it/", "2012-2024", "province", "Classes 0-9, 10-49, 50-249, 250+ actifs ; dont artisanales.")
add("PROV Entreprises forme jur.", bx.prov_forme_juridique(), "ISTAT ASIA imprese (183_277_DF_DICA_ASIAUE1P_4)",
    "https://esploradati.istat.it/", "2012-2024", "province", "")
add("PROV Salariés qualification", bx.prov_salaries_qualif(), "ISTAT ASIA occupazione (183_332_DF_DICA_ASIAULOCCP_3)",
    "https://esploradati.istat.it/", "2012-2017", "province", "Dirigeants, cadres, employés, ouvriers, apprentis.")
add("PROV Entreprises CCIAA", bx.camcom_imprese(), "NON ISTAT : CCIAA Marche / InfoCamere (open data)",
    "https://opendata.marche.camcom.it/data/Stock-Imprese-Attive-Italia-2009-2025.json", "2009-03 à 2025-03",
    "province (anciennes limites pour BA, FG et Sardaigne)", "Registre administratif : non comparable à ISTAT-ASIA.")
add("Salariés-CA communes 2017", bx.frame2017(), "ISTAT Frame territoriale 2017 (dati_comunali_2017_DPCM_covid19.xlsx)",
    "https://www.istat.it/notizia/dati-comunali-su-imprese-addetti-e-risultati-economici-delle-imprese-incluse-in-settori-attivi-e-sospesi-secondo-i-decreti-governativi-approvati-a-marzo-per-l/",
    "2017", "commune", "Seule source ISTAT donnant les salariés, CA et VA par commune ; 4 blocs non additionnés.")
add("Actifs par secteur 2021", bx.occupes_secteur(), "ISTAT Censimento permanente (DF_DCSS_EMPLP_2_COM)",
    "https://esploradati.istat.it/", "2021", "commune (résidence)", "")
add("PROV Salariés 2012-2017", bx.prov_salaries_secteur(), "ISTAT ASIA occupazione (183_332_DF_DICA_ASIAULOCCP_4)",
    "https://esploradati.istat.it/", "2012-2017", "province", "")
add("PROV Marché travail 2023", bx.forze_lavoro_prov(), "ISTAT Forze di lavoro - Dati provinciali 2023",
    "https://www.istat.it/comunicato-stampa/il-mercato-del-lavoro-iv-trimestre-2023/", "2023", "province", "En milliers.")
for nom_, f_, src_ in [("Grandes communes travail", "lavoro/Anni-2018-2023-Dati-grandi-comuni-offerta-di-lavoro.xlsx",
                        "ISTAT Forze di lavoro - grandi comuni 2018-2023 (en milliers)"),
                       ("ASIA tableaux Italie 2022", "lavoro/tavole-diffusione-2022.xlsx", "ISTAT Registro imprese attive 2022"),
                       ("ASIA tableaux Italie 2023", "imprese/Tavole/tavole-diffusione-2023.xlsx", "ISTAT Registro imprese attive 2023")]:
    rs = bx.raw_stack(os.path.join(ROOT, "raw", f_))
    rs.columns = [f"col_{i}" for i in range(rs.shape[1])]
    add(nom_, rs, src_, "https://www.istat.it/", "voir source", "grande commune / Italie / région",
        "Tableaux ISTAT mis en forme, repris tels quels (feuilles empilées).")
add("Navettes 2011 (synthèse)", P("pendolarisme_synthese_communes_2011"), "ISTAT Matrice del pendolarismo 2011",
    "https://www.istat.it/storage/cartografia/matrici_pendolarismo/matrici_pendolarismo_2011.zip", "2011",
    "commune (codes 2011)", "Dernier millésime publié. Matrice origine-destination complète : data/it/pendolarisme_od_2011.")
# ---------- 4. Offre hôtelière
add("Offre nominative", P("offre_hebergement_nominative"), "Registres régionaux/communaux open data (CKAN dati.gov.it)",
    "https://www.dati.gov.it/opendata/api/3/action/package_search?q=strutture%20ricettive", "voir colonne date_maj_source",
    "établissement", "Couverture partielle : voir onglet 'Offre couverture' et RAPPORT_LACUNES.md.")
add("Offre couverture", P("offre_couverture_regions"), "Calcul de couverture", "", TODAY, "région", "")
add("Capacité hébergement", bx.capacite(2019), "ISTAT Capacità degli esercizi ricettivi - dati comunali", ISTAT_T,
    "2019-2025", "commune", "Nombre d'établissements, lits, chambres par étoiles.")
# ---------- 5. Demande
add("Tourisme annuel", bx.tourisme_annuel(), "ISTAT Movimento dei clienti - dati comunali", ISTAT_T, "2014-2025", "commune",
    "Flag (f) : à partir de 2025 l'extra-hôtelier inclut les locations privées (rupture).")
add("Tourisme mensuel", bx.tourisme_mensuel(), "ISTAT Movimento dei clienti - dati comunali mensili", ISTAT_T, "2022-2025",
    "commune", "")
add("Taux utilisation lits hôtels", P("hotels_taux_utilisation_lits_communes"), "CALCUL sur données ISTAT", ISTAT_T,
    "2014-2025", "commune", "CALCUL = nuitées hôtelières / (lits hôteliers x jours). Vide si nuitées sous secret (*).")
add("Provenance clients (prov.)", bx.provenance(), "ISTAT - dati provinciali per provenienza", ISTAT_T, "2019-2025",
    "province", "Pays / région de résidence des clients.")
add("Étrangers motif (BdI)", P("bdi_voyageurs_etrangers_province_motif"),
    "Banca d'Italia - Indagine sul turismo internazionale (tableaux pivot)",
    "https://www.bancaditalia.it/statistiche/tematiche/rapporti-estero/turismo-internazionale/distribuzione-microdati/tabelle-pivot/index.html",
    "2017-2025", "province visitée",
    "Voyageurs/nuitées en milliers, dépenses en millions d'euros. Agrégation des facteurs d'extrapolation BdI (méthode du tableau pivot). Part affaires = motif_agrege.")
for k, v in bx.voyages().items():
    add({"viaggi_notti_destinazione_tipo": "ISTAT nuitées loisir-affaires", "viaggi_lavoro": "ISTAT voyages d'affaires",
         "viaggi_vacanze": "ISTAT voyages de vacances"}[k], v, "ISTAT Viaggi e vacanze (résidents italiens)",
        "https://esploradati.istat.it/", "2014-2025", "national / grandes zones",
        "Voyages des résidents italiens ; valeurs en milliers ou % selon DATA_TYPE.")
# ---------- 6. Accessibilité
add("Aéroports trafic", P("aeroports_trafic_assaeroporti"), "Assaeroporti - statistiche mensili",
    "https://assaeroporti.com/statistiche/", "2012-01 à 2026-07", "aéroport",
    "Tables mois / cumul janvier-mois ; passagers nationaux, internationaux, UE. Coordonnées OSM non récupérées (Overpass bloqué).")
# ---------- 7. Environnement touristique
add("Lieux culture MiC", P("lieux_culture_mic"), "MiC - Luoghi della cultura (LOD)", "https://dati.cultura.gov.it/sparql",
    TODAY, "lieu", "Catégories alignées sur l'appli FR. Coordonnées quand publiées par le MiC.")
add("Musées fréquentation ISTAT", bx.musees(), "ISTAT Indagine musei (60_1004_DF_DCIS_MUSVIS_COM_1)",
    "https://esploradati.istat.it/", "2011, 2015, 2017-2020", "commune", "'c' = secret statistique.")
add("Sites UNESCO", P("sites_unesco_wikidata"), "Wikidata P757 (NON OFFICIEL)", "https://query.wikidata.org/", TODAY,
    "site", "whc.unesco.org bloque les robots (Cloudflare) : à valider avec la liste officielle UNESCO.")

S = {S_first[0]: fix(S_first[1]), **S}
notes.insert(0, (S_first[0], "Reprise des derniers millésimes de chaque thème (ISTAT ; colonnes PROVINCE : valeurs provinciales)",
                 "voir onglets sources", "dernier millésime", "commune", "Colonnes 'PROVINCE :' = valeur de la province.", len(_syn)))
# ---------- Lacunes (contenu de RAPPORT_LACUNES.md, intégré au classeur)
import re as _re
_rows, _sec = [], ""
for _l in open(os.path.join(HERE, "rapport_lacunes.md"), encoding="utf-8"):
    _l = _l.rstrip("\n")
    if _l.startswith("#"):
        _sec = _l.lstrip("# ").strip()
        continue
    if _l.startswith("|") and not _re.match(r"^\|[-| ]+\|$", _l):
        _cells = [c.strip() for c in _l.strip("|").split("|")]
        _rows.append([_sec] + _cells)
    elif _l.strip():
        _rows.append([_sec, _l.strip()])
_w = max(len(r) for r in _rows)
lac = pd.DataFrame([r + [""] * (_w - len(r)) for r in _rows], columns=["module"] + [f"col_{i}" for i in range(1, _w)])
S["Lacunes"] = lac
notes.append(("Lacunes", "Rapport de couverture et de lacunes", "", TODAY, "tous", "Ce qui manque, ce qui est bloqué, ce qui est payant.", len(lac)))
# ---------- Contrôles
C = []
C.append(("Nombre de communes (référentiel 01/01/2026)", len(ref), 7894, len(ref) == 7894))
C.append(("Commune 001168 nommée 'None'", NOM.get("001168"), "None", NOM.get("001168") == "None"))
dem = P("demographie_tranches_communes")
p25 = int(dem[dem.annee_1er_janvier == 2025].pop_totale.sum())
bil = bx.bilan()
b24 = int(pd.to_numeric(bil[bil["Année"] == 2024]["Popolazione censita al 31 dicembre"], errors="coerce").sum())
C.append(("Population 01/01/2025 (POSAS) vs bilan ISTAT au 31/12/2024", p25, b24, p25 == b24))
ser = pd.read_excel(os.path.join(ROOT, "raw", "turismo", "1_serie_storica.xlsx"), header=None, dtype=str, **NA)
nat = ser[ser[0].astype(str).str.startswith("2024")].iloc[0]
nat_n = float(nat[12]) * 1000  # nuitées totales Italie 2024 (milliers) - colonne Totale/Totale
ta = bx.tourisme_annuel()
com_n = pd.to_numeric(ta[ta["Année"] == 2024]["Nuitées - Total hébergements - Total"], errors="coerce").sum()
C.append(("Nuitées 2024 : somme des communes publiées vs série nationale ISTAT", int(com_n), int(nat_n),
          f"écart {round((com_n / nat_n - 1) * 100, 2)} % (communes sous secret exclues)"))
codes = set(ref.cod_istat) | set(ref.cod_istat_2017_2025.dropna()) | set(ref.cod_istat_avant_2026_sardaigne.dropna())
for name, df in S.items():
    col = next((c for c in df.columns if c.lower() in ("cod_istat", "cod. istat")), None)
    if col is None:
        continue
    ycol = next((c for c in df.columns if c in ("annee", "Année", "annee_1er_janvier", "annee_imposition")), None)
    if ycol is not None:
        df = df[df[ycol].astype(str) == df[ycol].astype(str).max()]
    v = df[col].dropna().astype(str)
    v = v[v != ""]
    if len(v):
        rate = round(v.isin(codes).mean() * 100, 2)
        C.append((f"Part des lignes jointes au référentiel (dernier millésime) : {name}", rate, "> 99 %", rate > 99))
ctrl = pd.DataFrame(C, columns=["controle", "valeur", "reference", "resultat"])
S["Contrôles"] = ctrl

# ---------- Écriture
path = os.path.join(ROOT, "Italie_donnees_consolidees.xlsx")
lis = pd.DataFrame(notes, columns=["onglet", "source", "url", "millesime", "niveau_geographique", "limites", "lignes"])
with pd.ExcelWriter(path, engine="xlsxwriter", engine_kwargs={"options": {"strings_to_urls": False}}) as xw:
    wb = xw.book
    hdr = wb.add_format({"bold": True, "bg_color": "#1F3864", "font_color": "white", "text_wrap": True, "valign": "top", "font_size": 9})
    wrap = wb.add_format({"text_wrap": True, "valign": "top", "font_size": 9})
    lis.to_excel(xw, sheet_name="Lisez-moi", index=False, startrow=3)
    ws = xw.sheets["Lisez-moi"]
    ws.write(0, 0, "Italie - données consolidées pour l'outil d'étude de marché hôtelière", wb.add_format({"bold": True, "font_size": 14}))
    ws.write(1, 0, f"Extraction du {TODAY}. Clé de jointure : cod_istat (texte, 6 chiffres). Aucune valeur estimée ; "
                   "colonnes CALCUL_* = calculs signalés. Marques de secret ISTAT conservées (colonnes *_statut ou valeurs '(*)'/'c').", wrap)
    for j, c in enumerate(lis.columns):
        ws.write(3, j, c, hdr)
    ws.set_column(0, 0, 28, wrap); ws.set_column(1, 1, 45, wrap); ws.set_column(2, 2, 40, wrap)
    ws.set_column(3, 4, 18, wrap); ws.set_column(5, 5, 80, wrap)
    for name, df in S.items():
        df = df.drop(columns=[c for c in ("url_source", "source", "date_extraction") if c in df.columns])  # dans le Lisez-moi
        df.to_excel(xw, sheet_name=name[:31], index=False)
        sh = xw.sheets[name[:31]]
        for j, c in enumerate(df.columns):
            sh.write(0, j, str(c), hdr)
        sh.set_row(0, 45)
        sh.set_column(0, len(df.columns) - 1, 14)
        sh.freeze_panes(1, 1)
        sh.autofilter(0, 0, len(df), len(df.columns) - 1)
print("écrit", path, round(os.path.getsize(path) / 1e6, 1), "Mo")
print(ctrl.to_string())

# Recompression maximale (limite GitHub 100 Mio par fichier)
import zipfile  # noqa: E402
_tmp = path + ".tmp"
with zipfile.ZipFile(path) as zi, zipfile.ZipFile(_tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zo:
    for it in zi.infolist():
        zo.writestr(it.filename, zi.read(it.filename))
os.replace(_tmp, path)
print("recompressé :", round(os.path.getsize(path) / 2**20, 1), "Mio")
