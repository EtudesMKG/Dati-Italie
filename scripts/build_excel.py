"""Compile les données brutes ISTAT en un classeur Excel unique.

Aucune valeur n'est estimée ni inventée : les chiffres sont repris tels que publiés par ISTAT.
Seules opérations : mise en forme (large/long), jointure sur le code commune ISTAT, et
sommes d'âges simples publiés par ISTAT (population totale 2014-2018, classes d'âge).
"""
import glob
import os
import re
from datetime import date

import pandas as pd

import demografia as dm
import istat_sdmx as s

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
RAW = os.path.join(ROOT, "raw")
OUT = os.path.join(ROOT, "output", "Dati_Italia_ISTAT_comuni.xlsx")


def num(v):
    """Convertit en nombre quand c'est un nombre ; sinon garde la marque ISTAT brute (*, -, ...)."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    t = str(v).strip()
    if t == "":
        return None
    try:
        f = float(t.replace(",", "."))
        return int(f) if f.is_integer() else f
    except ValueError:
        return t


def numcols(df, cols):
    for c in cols:
        df[c] = df[c].map(num)
    return df


# ---------------------------------------------------------------- référentiel communes
def referentiel():
    e = pd.read_excel(os.path.join(RAW, "ref", "Elenco-comuni-italiani.xlsx"), dtype=str)
    e = e.rename(columns=lambda c: c.strip())
    ref = pd.DataFrame({
        "Cod. ISTAT": e["Codice Comune formato alfanumerico"],
        "Commune": e["Denominazione in italiano"],
        "Province / UTS": e["Denominazione dell'Unità territoriale sovracomunale \n(valida a fini statistici)".strip()]
        if "Denominazione dell'Unità territoriale sovracomunale \n(valida a fini statistici)".strip() in e.columns
        else e[[c for c in e.columns if c.startswith("Denominazione dell'Unità territoriale")][0]],
        "Sigle": e["Sigla automobilistica"],
        "Région": e["Denominazione Regione"],
        "Répartition": e["Ripartizione geografica"],
        "Chef-lieu (1=oui)": e[[c for c in e.columns if c.startswith("Flag Comune capoluogo")][0]],
        # code ISTAT en vigueur 2017-2025 (recodification Sardaigne 2026) : clé utilisée par les sources statistiques
        "Cod. ISTAT 2017-2025": e[[c for c in e.columns if "dal 2017" in c][0]].str.zfill(6),
    })
    leg = pd.read_excel(os.path.join(RAW, "turismo", "DCSC_turistical_area_TB.xls"), "Legenda comuni", dtype=str)
    leg.columns = [c.strip() for c in leg.columns]
    leg = leg.rename(columns={
        "Cod_ISTAT": "Cod. ISTAT",
        "Comune litoraneo / Seaside municipality": "Commune littorale",
        "Comune costiero / Coastal municipality": "Commune côtière",
        "Grado di urbanizzazione / Degree of urbanisation": "Degré d'urbanisation",
        "Categoria turistica prevalente / Predominant tourism category": "Catégorie touristique prévalente",
        "Brand Turistico": "Brand touristique",
    })
    keep = ["Cod. ISTAT", "Commune littorale", "Commune côtière", "Degré d'urbanisation",
            "Catégorie touristique prévalente", "Brand touristique"]
    return _join(ref, leg[keep])


# ---------------------------------------------------------------- démographie
def demographie():
    ric = dm.ricostruzione()
    ric = ric[ric.anno < 2019]  # 2019+ : POSAS
    tot = ric[ric.sesso == "Totale"].pivot_table(index="cod", columns="anno", values="pop", aggfunc="sum")
    names = ric.drop_duplicates("cod").set_index("cod")["comune"]
    pos = dm.posas()
    wide = {}
    for y, d in pos.items():
        t = d[d["Età"] == 999].set_index("Codice comune")
        wide[y] = t["Totale"]
        names = pd.concat([names, t["Comune"]])
    names = names[~names.index.duplicated(keep="last")]
    pop = pd.DataFrame({f"Pop. 1/1/{y}": tot[y] for y in sorted(tot.columns)})
    pop = pop.join(pd.DataFrame({f"Pop. 1/1/{y}": v for y, v in sorted(wide.items())}), how="outer")
    last = max(pos)
    d = pos[last]
    t = d[d["Età"] == 999].set_index("Codice comune")
    ages = d[d["Età"] != 999]
    cls = lambda lo, hi: ages[(ages["Età"] >= lo) & (ages["Età"] <= hi)].groupby("Codice comune")["Totale"].sum()
    pop[f"Hommes 1/1/{last}"] = t["Totale maschi"]
    pop[f"Femmes 1/1/{last}"] = t["Totale femmine"]
    pop[f"0-14 ans 1/1/{last}"] = cls(0, 14)
    pop[f"15-64 ans 1/1/{last}"] = cls(15, 64)
    pop[f"65 ans et + 1/1/{last}"] = cls(65, 200)
    pop = pop.astype("Int64")
    pop.index.name = "Cod. ISTAT"
    pop.insert(0, "Commune (nom ISTAT)", names.reindex(pop.index))
    return pop.reset_index()


def bilan():
    rows = []
    for y, d in dm.bilancio().items():
        cols = [c for c in d.columns if c.endswith("- Totale") or c.startswith("Numero")]
        x = d[["Codice comune", "Comune"] + cols].copy()
        x.insert(0, "Année", y)
        rows.append(x)
    b = pd.concat(rows, ignore_index=True)
    b.columns = [c.replace(" - Totale", "") for c in b.columns]
    return b.rename(columns={"Codice comune": "Cod. ISTAT", "Comune": "Commune"})


# ---------------------------------------------------------------- entreprises / emploi (ASIA)
ATECO = {"0010": "Total activités", "I": "I - Hébergement et restauration", "55": "55 - Hébergement",
         "56": "56 - Restauration"}


def asia():
    fs = sorted(glob.glob(os.path.join(RAW, "sdmx", "asia_ul_*.csv")))
    d = pd.concat([pd.read_csv(f, dtype=str) for f in fs], ignore_index=True)
    d = d[d.REF_AREA.str.fullmatch(r"\d{6}", na=False)]
    d = d.drop_duplicates(["REF_AREA", "DATA_TYPE", "ECON_ACTIVITY_NACE_2007", "TIME_PERIOD"])
    d["col"] = d.ECON_ACTIVITY_NACE_2007.map(ATECO) + d.DATA_TYPE.map(
        {"LU": " - Unités locales", "LUEMPDAA": " - Actifs occupés (addetti, moy. annuelle)"})
    w = d.pivot_table(index=["REF_AREA", "TIME_PERIOD"], columns="col", values="OBS_VALUE", aggfunc="first")
    order = [a + b for a in ATECO.values() for b in (" - Unités locales", " - Actifs occupés (addetti, moy. annuelle)")]
    w = w.reindex(columns=[c for c in order if c in w.columns]).reset_index()
    for c in w.columns[2:]:
        w[c] = w[c].map(num)
    _, cls = s.structure("183_285_DF_DICA_ASIAULP_7")
    lab = cls.get("CL_ITTER107", {})
    w.insert(1, "Commune", w.REF_AREA.map(lab))
    return w.rename(columns={"REF_AREA": "Cod. ISTAT", "TIME_PERIOD": "Année"}).sort_values(["Cod. ISTAT", "Année"])


def _sdmx_wide(name, flow, colkey, labels=None, index=("REF_AREA", "TIME_PERIOD")):
    """CSV SDMX brut -> tableau large par commune (codes 6 chiffres), colonnes = libellés ISTAT."""
    p = os.path.join(RAW, "sdmx", name + ".csv")
    if not os.path.exists(p):
        return None
    d = pd.read_csv(p, dtype=str)
    d = d[d.REF_AREA.str.fullmatch(r"\d{6}", na=False)].copy()
    dims, cls = s.structure(flow)
    cl = {dim: cls.get(c, {}) for dim, _, c in dims}
    d["col"] = d.apply(colkey if callable(colkey) else (lambda r: cl[colkey].get(r[colkey], r[colkey])), axis=1)
    d["v"] = d.OBS_VALUE.map(num).astype(object)
    w = d.pivot_table(index=list(index), columns="col", values="v", aggfunc="first")
    if labels:
        w = w.reindex(columns=[c for c in labels if c in w.columns])
    w = w.reset_index()
    w.insert(1, "Commune", w.REF_AREA.map(cl["REF_AREA"]))
    return w.rename(columns={"REF_AREA": "Cod. ISTAT", "TIME_PERIOD": "Année"}).sort_values(["Cod. ISTAT", "Année"])


def occupes_recensement():
    """Recensement permanent : actifs occupés résidents 15+ (total / salariés / indépendants, par sexe)."""
    stat = {"99": "Actifs occupés", "9": "dont salariés (dipendenti)", "22": "dont indépendants"}
    sexe = {"T": "total", "M": "hommes", "F": "femmes"}
    order = [f"{v} - {x}" for x in sexe.values() for v in stat.values()]
    return _sdmx_wide("occupati_posizione_comuni", "DF_DCSS_EMPLP_1_COM",
                      lambda r: f"{stat[r.EMPLOYMENT_STATUS]} - {sexe[r.GENDER]}", order)


def occupes_secteur():
    lab = {"0010": "Total actifs occupés", "A": "A - Agriculture, sylviculture, pêche",
           "0011": "B-F - Industrie (y c. construction)", "0026": "G,I - Commerce, hôtels et restaurants",
           "0091": "H,J - Transport, entreposage, information et communication",
           "0092": "K-N - Finance, assurance, immobilier, activités spécialisées, services aux entreprises",
           "0093": "O-U - Autres activités (administration, enseignement, santé, autres services)"}
    return _sdmx_wide("occupati_settore_comuni", "DF_DCSS_EMPLP_2_COM",
                      lambda r: lab.get(r.BRANCH_ECON_ACT, r.BRANCH_ECON_ACT), list(lab.values()))


def condition_pro():
    """Recensement permanent : population 15+ par condition professionnelle, 2018-2024."""
    fs = sorted(glob.glob(os.path.join(RAW, "sdmx", "condizione_professionale_20*.csv")))
    if not fs:
        return None
    d = pd.concat([pd.read_csv(f, dtype=str) for f in fs], ignore_index=True)
    d = d.drop_duplicates(["REF_AREA", "CUR_ACT_STAT", "TIME_PERIOD"])
    d.to_csv(os.path.join(RAW, "sdmx", "condizione_professionale_all.csv"), index=False)
    lab = {"99": "Population 15 ans et +", "22": "Forces de travail (actifs)", "1": "Actifs occupés",
           "12": "Chômeurs (en recherche d'emploi)", "23": "Inactifs (hors forces de travail)"}
    return _sdmx_wide("condizione_professionale_all", "DF_DCSS_ISTR_LAV_PEN_2_TV_3",
                      lambda r: lab.get(r.CUR_ACT_STAT, r.CUR_ACT_STAT), list(lab.values()))


def asia_sections():
    lab = {"0010": "TOTAL toutes activités"}
    for k, v in [("A", "Agriculture"), ("B", "Extraction"), ("C", "Industrie manufacturière"), ("D", "Énergie"),
                 ("E", "Eau, déchets"), ("F", "Construction"), ("G", "Commerce"), ("H", "Transport, entreposage"),
                 ("I", "Hébergement, restauration"), ("J", "Information, communication"), ("K", "Finance, assurance"),
                 ("L", "Immobilier"), ("M", "Activités spécialisées, scientifiques, techniques"),
                 ("N", "Services administratifs et de soutien"), ("P", "Enseignement"), ("Q", "Santé, action sociale"),
                 ("R", "Arts, spectacles, loisirs"), ("S", "Autres services")]:
        lab[k] = f"{k} - {v}"
    mes = {"LU": "Établissements (unités locales)", "LUEMPDAA": "Actifs occupés (addetti)"}
    order = [f"{mes[m]} - {v}" for m in mes for v in lab.values()]
    return _sdmx_wide("asia_ul_sezioni_2023", "183_285_DF_DICA_ASIAULP_7",
                      lambda r: f"{mes[r.DATA_TYPE]} - {lab.get(r.ECON_ACTIVITY_NACE_2007, r.ECON_ACTIVITY_NACE_2007)}",
                      order)


def frame2017():
    """ISTAT Frame territoriale 2017 : établissements, actifs, SALARIÉS, CA, VA par commune (4 blocs ISTAT)."""
    f = os.path.join(RAW, "imprese", "dati_comunali_2017_DPCM_covid19.xlsx")
    blocs = {"Settori attivi_industria": "Industrie secteurs 'actifs'",
             "settori sospesi industria": "Industrie secteurs 'suspendus'",
             "settori attivi servizi": "Services secteurs 'actifs'",
             "settori sospesi servizi": "Services secteurs 'suspendus'"}
    mes = {"Unita_locali": "Établissements", "Numero Addetti": "Actifs occupés (addetti)",
           "Numero Dipendenti": "Salariés (dipendenti)", "Fatturato\n(valori in euro)": "Chiffre d'affaires (€)",
           "Valore_aggiunto\n(valori in euro)": "Valeur ajoutée (€)"}
    out = None
    for sh, b in blocs.items():
        d = pd.read_excel(f, sheet_name=sh, dtype=str).iloc[:, :10]
        d = d[d.codice_comune.str.fullmatch(r"\d{6}", na=False)]
        x = d[["codice_comune", "Denominazione_comune", "Denominazione_provincia", "Denominazione_regione"]].copy()
        for k, v in mes.items():
            x[f"{b} - {v}"] = d[k].map(num)
        out = x if out is None else out.merge(x, on=["codice_comune", "Denominazione_comune", "Denominazione_provincia",
                                                     "Denominazione_regione"], how="outer")
    return out.rename(columns={"codice_comune": "Cod. ISTAT", "Denominazione_comune": "Commune",
                               "Denominazione_provincia": "Province", "Denominazione_regione": "Région"})


# ---------------------------------------------------------------- tourisme
def tourisme_annuel():
    d = pd.read_excel(os.path.join(RAW, "turismo", "2_dati_comunali.xlsx"), sheet_name=0, header=None,
                      skiprows=6, dtype=str)
    d = d[d[0].str.fullmatch(r"\d{4}", na=False)].iloc[:, :26]
    base = ["Année", "Cod. Rég.", "Région", "Cod. Prov.", "Province", "Commune", "Cod. ISTAT", "Flags"]
    vals = []
    for m in ("Arrivées", "Nuitées"):
        for t in ("Total hébergements", "Hôtellerie (esercizi alberghieri)", "Extra-hôtelier"):
            for r in ("Résidents Italie", "Non-résidents (étrangers)", "Total"):
                vals.append(f"{m} - {t} - {r}")
    d.columns = base + vals
    d["Année"] = d["Année"].astype(int)
    return numcols(d, vals)


def tourisme_mensuel():
    d = pd.read_excel(os.path.join(RAW, "turismo", "2_dati_comunali.xlsx"), sheet_name=1, header=None,
                      skiprows=4, dtype=str)
    d = d[d[0].str.fullmatch(r"\d{4}", na=False)].iloc[:, :34]
    base = ["Année", "Cod. Rég.", "Région", "Cod. Prov.", "Province", "Commune", "Cod. ISTAT", "Flags"]
    vals = [f"Arrivées M{m:02d}" for m in range(1, 13)] + [f"Nuitées M{m:02d}" for m in range(1, 13)] + \
           ["Arrivées année", "Nuitées année"]
    d.columns = base + vals
    d["Année"] = d["Année"].astype(int)
    return numcols(d, vals)


def capacite(first_year=2014):
    f = glob.glob(os.path.join(RAW, "turismo", "Capacit*comunale*.xlsx"))[0]
    h = pd.read_excel(f, header=None, nrows=6, dtype=str)
    d = pd.read_excel(f, header=None, skiprows=6, dtype=str)
    d = d[d[0].str.fullmatch(r"\d{4}", na=False)]
    d = d[d[0].astype(int) >= first_year]
    grp = h.iloc[4].ffill()
    tot = h.iloc[2].ffill()
    mes = h.iloc[5]
    cols = ["Année", "Région", "Cod. Rég.", "Province", "Cod. Prov.", "Commune", "Code commune (prov.)", "Cod. ISTAT"]
    for i in range(8, d.shape[1]):
        g = str(tot[i]).strip() if pd.notna(tot[i]) else str(grp[i]).strip()
        cols.append(f"{g.split('/')[0].strip()} - {str(mes[i]).split('/')[0].strip()}")
    d.columns = cols
    d["Année"] = d["Année"].astype(int)
    return numcols(d, cols[8:])


def provenance():
    f = os.path.join(RAW, "turismo", "3_dati_provinciali_per_provenienza.xlsx")
    h = pd.read_excel(f, header=None, nrows=2, dtype=str)
    d = pd.read_excel(f, header=None, skiprows=2, dtype=str)
    d = d[d[0].str.fullmatch(r"\d{4}", na=False)]
    grp = h.iloc[0].ffill()
    cols = ["Année", "Cod. Rég.", "Région", "Cod. Prov.", "Province", "Code provenance", "Pays / région de résidence du client"]
    for i in range(7, d.shape[1]):
        cols.append(f"{str(grp[i]).split('/')[0].strip()} - {str(h.iloc[1][i]).split('/')[0].strip()}")
    d.columns = cols
    d["Année"] = d["Année"].astype(int)
    return numcols(d, cols[7:])


# ---------------------------------------------------------------- musées
def musees():
    d = pd.read_csv(os.path.join(RAW, "sdmx", "musei_comuni.csv"), dtype=str)
    d = d[d.REF_AREA.str.fullmatch(r"\d{6}", na=False)]
    d["v"] = d.OBS_VALUE.map(num).astype(object)
    d.loc[d.OBS_STATUS == "c", "v"] = "c (secret stat.)"
    d["col"] = d.DATA_TYPE.map({"INSTITUTES": "Musées et instituts similaires (nombre)",
                                "ADMISSIONS": "Visiteurs (nombre)"})
    w = d.pivot_table(index=["REF_AREA", "TIME_PERIOD"], columns="col", values="v", aggfunc="first").reset_index()
    _, cls = s.structure("60_1004_DF_DCIS_MUSVIS_COM_1")
    w.insert(1, "Commune", w.REF_AREA.map(cls.get("CL_ITTER107", {})))
    return w.rename(columns={"REF_AREA": "Cod. ISTAT", "TIME_PERIOD": "Année"}).sort_values(["Cod. ISTAT", "Année"])


# ---------------------------------------------------------------- voyages loisir / affaires
def voyages():
    out = {}
    for name, flow in [("viaggi_notti_destinazione_tipo", "68_357_DF_DCCV_TURNOT_CAPI_3"),
                       ("viaggi_lavoro", "68_1221_DF_DCCV_VIAGGI_CAPI_2_7"),
                       ("viaggi_vacanze", "68_1221_DF_DCCV_VIAGGI_CAPI_2_1")]:
        p = os.path.join(RAW, "sdmx", name + ".csv")
        if not os.path.exists(p):
            continue
        d = pd.read_csv(p, dtype=str)
        dims, cls = s.structure(flow)
        keep = []
        for dim, _, cl in dims:
            if dim == "FREQ" or dim not in d.columns:
                continue
            if d[dim].nunique() == 1 and d[dim].iloc[0] in ("ALL", "TOTAL", "9", "IT"):
                pass
            d[dim + " (libellé)"] = d[dim].map(cls.get(cl, {}))
            keep += [dim, dim + " (libellé)"]
        d["Valeur"] = d.OBS_VALUE.map(num)
        out[name] = d[keep + ["TIME_PERIOD", "Valeur", "OBS_STATUS"]].rename(columns={"TIME_PERIOD": "Période"})
    return out


# ---------------------------------------------------------------- synthèse
def _join(x, df):
    """Jointure sur le code actuel, à défaut sur le code 2017-2025 (communes recodifiées en 2026)."""
    df = df.drop_duplicates("Cod. ISTAT")
    a = x[["Cod. ISTAT"]].merge(df, on="Cod. ISTAT", how="left").set_index(x.index)
    b = x[["Cod. ISTAT 2017-2025"]].merge(df.rename(columns={"Cod. ISTAT": "Cod. ISTAT 2017-2025"}),
                                          on="Cod. ISTAT 2017-2025", how="left").set_index(x.index)
    cols = [c for c in df.columns if c != "Cod. ISTAT"]
    a[cols] = a[cols].astype(object).where(a[cols].notna(), b[cols].astype(object))
    return pd.concat([x, a[cols]], axis=1)


def synthese(ref, pop, asi, tann, cap, mus, occ=None, cpro=None):
    x = ref.copy()
    popcols = [c for c in pop.columns if c.startswith("Pop. 1/1/")]
    x = _join(x, pop[["Cod. ISTAT"] + popcols[-3:]])
    if cpro is not None:
        yp = cpro["Année"].max()
        c = cpro[cpro["Année"] == yp].drop(columns=["Commune", "Année"])
        c.columns = ["Cod. ISTAT"] + [f"Recensement : {k} ({yp})" for k in c.columns[1:]]
        x = _join(x, c)
    if occ is not None:
        yo = occ["Année"].max()
        o = occ[occ["Année"] == yo]
        oc = [c for c in o.columns if c.endswith("- total")]
        x = _join(x, o[["Cod. ISTAT"] + oc].rename(columns={c: f"Recensement : {c} ({yo})" for c in oc}))
    ya = asi["Année"].max()
    a = asi[asi["Année"] == ya].drop(columns=["Commune", "Année"])
    a.columns = ["Cod. ISTAT"] + [f"ASIA : {c} ({ya})" for c in a.columns[1:]]
    x = _join(x, a)
    for y in sorted(tann["Année"].unique())[-2:]:
        t = tann[tann["Année"] == y]
        cols = ["Arrivées - Total hébergements - Total", "Nuitées - Total hébergements - Total",
                "Arrivées - Hôtellerie (esercizi alberghieri) - Total",
                "Nuitées - Hôtellerie (esercizi alberghieri) - Total",
                "Arrivées - Total hébergements - Résidents Italie",
                "Arrivées - Total hébergements - Non-résidents (étrangers)"]
        t = t[["Cod. ISTAT"] + cols].rename(columns={c: f"{c} ({y})" for c in cols})
        x = _join(x, t)
    yc = cap["Année"].max()
    c = cap[cap["Année"] == yc]
    ccols = [k for k in c.columns if k.startswith("totale alberghi") or k.startswith("TOTALE")]
    c = c[["Cod. ISTAT"] + ccols].rename(columns={k: f"Capacité {k} ({yc})" for k in ccols})
    x = _join(x, c)
    ym = mus["Année"].max()
    m = mus[mus["Année"] == ym].drop(columns=["Commune", "Année"])
    m.columns = ["Cod. ISTAT"] + [f"{k} ({ym})" for k in m.columns[1:]]
    return _join(x, m)


# ---------------------------------------------------------------- écriture
def write(sheets, notes):
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with pd.ExcelWriter(OUT, engine="xlsxwriter", engine_kwargs={"options": {"strings_to_numbers": False}}) as xw:
        wb = xw.book
        hdr = wb.add_format({"bold": True, "text_wrap": True, "valign": "top", "bg_color": "#1F3864",
                             "font_color": "#FFFFFF", "border": 1, "font_size": 9})
        body = wb.add_format({"font_size": 9})
        numf = wb.add_format({"font_size": 9, "num_format": "#,##0"})
        title = wb.add_format({"bold": True, "font_size": 14})
        bold = wb.add_format({"bold": True, "font_size": 10, "text_wrap": True, "valign": "top"})
        wrap = wb.add_format({"font_size": 10, "text_wrap": True, "valign": "top"})
        ws = wb.add_worksheet("Lisez-moi")
        ws.set_column(0, 0, 34)
        ws.set_column(1, 1, 120)
        ws.write(0, 0, "Données communales Italie - source unique ISTAT", title)
        for i, (k, v) in enumerate(notes, start=2):
            ws.write(i, 0, k, bold)
            ws.write(i, 1, v, wrap)
        for name, df in sheets.items():
            df = df.copy()
            df.to_excel(xw, sheet_name=name, index=False, startrow=1, header=False)
            sh = xw.sheets[name]
            for j, c in enumerate(df.columns):
                sh.write(0, j, str(c), hdr)
                isnum = pd.api.types.is_numeric_dtype(df[c]) or df[c].map(lambda v: isinstance(v, (int, float))).mean() > 0.5
                width = 10 if isnum else min(max(10, int(df[c].astype(str).str.len().quantile(0.9)) + 2), 40)
                sh.set_column(j, j, width, numf if isnum and not str(c).startswith(("Cod", "Année", "Code")) else body)
            sh.set_row(0, 60)
            sh.freeze_panes(1, 2)
            sh.autofilter(0, 0, len(df), len(df.columns) - 1)
    print("écrit", OUT)


def main():
    ref = referentiel()
    pop = demographie()
    bil = bilan()
    asi = asia()
    tann = tourisme_annuel()
    tmen = tourisme_mensuel()
    cap = capacite()
    prov = provenance()
    mus = musees()
    voy = voyages()
    occ = occupes_recensement()
    occsec = occupes_secteur()
    cpro = condition_pro()
    asec = asia_sections()
    fr17 = frame2017()
    syn = synthese(ref, pop, asi, tann, cap, mus, occ, cpro)
    popy = [c for c in pop.columns if c.startswith("Pop. 1/1/")]
    sheets = {
        "Synthèse communes": syn,
        "Démographie": pop,
        "Bilan démographique": bil,
        "Actifs occupés 2021 (recens.)": occ,
        "Actifs par secteur 2021": occsec,
        "Actifs occupés 2018-2024": cpro,
        "Établissements par secteur 2023": asec,
        "Établ. & actifs 2012-2023 ASIA": asi,
        "Salariés-CA par commune 2017": fr17,
        "Tourisme annuel 2014-2025": tann,
        "Tourisme mensuel 2022-2025": tmen,
        "Capacité hébergement": cap,
        "Provenance clients (prov.)": prov,
        "Musées-Fréquentation": mus,
    }
    labels = {"viaggi_notti_destinazione_tipo": "Loisir-Affaires nuitées",
              "viaggi_lavoro": "Voyages d'affaires",
              "viaggi_vacanze": "Voyages de vacances"}
    for k, v in voy.items():
        sheets[labels[k]] = v
    sheets = {k: v for k, v in sheets.items() if v is not None}
    notes = [
        ("Source", "Exclusivement ISTAT (Istituto Nazionale di Statistica). Aucun chiffre estimé, calculé ou "
                   "complété par nous : valeurs reprises telles que publiées. Les marques ISTAT sont conservées "
                   "('*' ou 'c' = secret statistique, '-' = phénomène absent, colonne Flags = notes ISTAT (a)-(f))."),
        ("Date d'extraction", date.today().isoformat()),
        ("Périmètre", "Toutes les communes italiennes publiées par ISTAT. Clé de jointure : code commune ISTAT "
                      "à 6 chiffres (Cod. ISTAT). Les codes suivent les fusions/créations de communes de chaque année."),
        ("Synthèse communes", "Une ligne par commune existante (liste officielle ISTAT 'Elenco comuni italiani') + "
                              "classifications touristiques ISTAT + derniers millésimes de chaque onglet (simple "
                              "recopie, pas de calcul)."),
        ("Démographie", f"Population résidente au 1er janvier {popy[0][-4:]}-{popy[-1][-4:]}. 2014-2018 : "
                        "reconstruction intercensitaire ISTAT (demo.istat.it, somme des âges simples publiés). "
                        "2019-2026 : ISTAT POSAS (population par âge et sexe ; 2026 = estimation ISTAT). Classes d'âge "
                        "et sexe = sommes des âges simples ISTAT du dernier millésime."),
        ("Bilan démographique", "ISTAT demo.istat.it, bilan démographique par commune (naissances, décès, "
                                "migrations, ménages) 2019-2025, colonnes 'Totale'."),
        ("EMPLOI - lecture", "Deux mesures ISTAT complémentaires : (1) LIEU DE RÉSIDENCE : personnes de 15 ans et + "
                             "résidant dans la commune et ayant un emploi (recensement permanent) ; (2) LIEU DE TRAVAIL : "
                             "emplois localisés dans les établissements d'entreprises situés dans la commune (registre ASIA)."),
        ("Actifs occupés 2021 (recens.)", "ISTAT, Censimento permanente della popolazione 2021, flux DF_DCSS_EMPLP_1_COM : "
                                          "actifs occupés résidents 15+ par commune, dont salariés (dipendenti) et "
                                          "indépendants, par sexe. Dernier millésime communal publié. Décimales = "
                                          "valeurs ISTAT issues d'estimation (recensement par échantillon/registres)."),
        ("Actifs par secteur 2021", "Même recensement, flux DF_DCSS_EMPLP_2_COM : actifs occupés résidents par grand "
                                    "secteur d'activité (7 regroupements ISTAT)."),
        ("Actifs occupés 2018-2024", "Recensement permanent, flux DF_DCSS_ISTR_LAV_PEN_2_TV_3 : population résidente "
                                     "15+ par condition professionnelle, chaque année 2018-2024 : actifs occupés, chômeurs, "
                                     "forces de travail, inactifs. Série annuelle la plus récente sur l'emploi par commune."),
        ("Établissements par secteur 2023", "ISTAT, Registre ASIA unités locales 2023 (flux 183_285_DF_DICA_ASIAULP_7) : "
                                            "nombre d'établissements et d'actifs occupés (addetti = salariés + "
                                            "indépendants, moyenne annuelle) par commune, TOUTES sections Ateco (A-S)."),
        ("Établ. & actifs 2012-2023 ASIA", "Même registre, série 2012-2023 : total toutes activités + hébergement/"
                                           "restauration (I, 55, 56)."),
        ("Salariés-CA par commune 2017", "ISTAT, Registre étendu 'Frame territoriale' 2017 (publication ISTAT avril 2020 "
                                         "'Dati comunali su imprese, addetti e risultati economici', fichier "
                                         "dati_comunali_2017_DPCM_covid19.xlsx) : SEULE source ISTAT donnant par commune "
                                         "les SALARIÉS (dipendenti), les actifs, le chiffre d'affaires et la valeur ajoutée. "
                                         "ISTAT publie 4 blocs séparés (industrie/services x secteurs 'actifs'/'suspendus' "
                                         "lors du confinement de mars 2020) ; ils sont repris tels quels, non additionnés. "
                                         "Champ : industrie, construction, services marchands (hors agriculture, finance/"
                                         "assurance, administration publique). '*' = secret statistique (< 3 unités)."),
        ("Nombre d'entreprises", "ISTAT ne publie PAS le nombre d'entreprises (sièges sociaux) par commune : le registre "
                                 "ASIA-entreprises est diffusé au niveau provincial au plus fin. Au niveau communal, "
                                 "l'indicateur ISTAT est le nombre d'établissements (unités locales), qui compte chaque "
                                 "site d'activité d'une entreprise situé dans la commune."),
        ("Tourisme annuel 2014-2025", "ISTAT, Movimento dei clienti negli esercizi ricettivi - fichier 'Turismo - file già "
                                      "pronti' (esploradati.istat.it/databrowser/DWL/Servizi/DCSC_Occupancy_in_collective_"
                                      "accommodation.zip, version juillet 2026). Arrivées et nuitées par commune, hôtellerie / "
                                      "extra-hôtelier, résidents / non-résidents. ATTENTION (f) : à partir de 2025 l'extra-"
                                      "hôtelier inclut les locations privées non professionnelles (rupture de série). Communes "
                                      "absentes = données non diffusables (secret statistique)."),
        ("Tourisme mensuel 2022-2025", "Même fichier ISTAT, arrivées et nuitées mensuelles par commune (ISTAT ne diffuse pas "
                                       "de mensuel communal avant 2022)."),
        ("Capacité hébergement", "ISTAT, Capacità degli esercizi ricettivi - dati comunali (DWL/Servizi/DCSC Capacity of "
                                 "tourist accommodation municipal.zip), 2014-2025 : nombre d'établissements, lits, "
                                 "chambres, salles de bain par catégorie d'hôtel et type d'extra-hôtelier."),
        ("Répartition clientèle", "Au niveau COMMUNAL, ISTAT ne diffuse que la répartition résidents (Italiens) / "
                                  "non-résidents (étrangers) : colonnes de l'onglet 'Tourisme annuel'. La répartition par "
                                  "pays / région d'origine n'existe qu'au niveau PROVINCIAL : onglet 'Provenance clients "
                                  "(prov.)' (fichier ISTAT 3_dati_provinciali_per_provenienza, 2019-2025, par type "
                                  "d'hébergement)."),
        ("Loisir / Affaires", "ISTAT ne ventile PAS les arrivées/nuitées des hébergements par motif. La seule source ISTAT "
                              "est l'enquête 'Viaggi e vacanze' (voyages des résidents italiens) : niveau national / "
                              "grandes zones / régions de destination, jamais communal. Onglets 'Loisir-Affaires "
                              "nuitées' (68_357_DF_DCCV_TURNOT_CAPI_3), 'Voyages d'affaires' (68_1221_..._2_7) et "
                              "'Voyages de vacances' (68_1221_..._2_1), valeurs en milliers ou % selon DATA_TYPE."),
        ("Musées-Fréquentation", "ISTAT, Indagine sui musei e le istituzioni similari, flux SDMX 60_1004_DF_DCIS_MUSVIS_COM_1 : "
                                 "nombre de musées/monuments/aires archéologiques et de visiteurs par commune, années "
                                 "2011, 2015, 2017-2020 (derniers millésimes communaux publiés par ISTAT). "
                                 "'c' = donnée confidentielle (secret statistique). Aucune autre fréquentation de sites "
                                 "touristiques n'est publiée par ISTAT au niveau communal."),
        ("Codes communes", "ISTAT a recodifié en 2026 les communes de Sardaigne (nouvelles provinces). Les onglets de "
                           "données gardent le code publié par ISTAT pour chaque année ; la Synthèse relie les deux via "
                           "la colonne officielle 'Cod. ISTAT 2017-2025' de la liste ISTAT des communes. Les communes "
                           "nées d'une fusion récente n'ont pas de données antérieures à leur création."),
        ("Reproductibilité", "Scripts dans le dépôt : scripts/fetch_sdmx.py (API SDMX ISTAT), scripts/demografia.py, "
                             "scripts/build_excel.py. Fichiers bruts téléchargés dans raw/."),
    ]
    write(sheets, notes)


if __name__ == "__main__":
    main()
