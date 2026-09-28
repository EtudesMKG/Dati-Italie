"""Bloc 1 : référentiel des communes + contours simplifiés (GeoJSON EPSG:4326) + centroïdes.
Sources : ISTAT Elenco comuni italiani, table Sardaigne 2026, Altimetria, Corone urbane, Confini 01/01/2026 (généralisés).
"""
import glob
import os
import sys

import geopandas as gpd
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, NA, meta, save  # noqa: E402

RAW = os.path.join(ROOT, "raw")


def f(pattern):
    return sorted(glob.glob(os.path.join(RAW, pattern)))[-1]


def referentiel():
    e = pd.read_excel(f("istat_codici/*/Elenco-comuni-italiani.xlsx"), dtype=str, **NA)
    e.columns = [c.replace("\n", " ").strip() for c in e.columns]
    col = lambda s: [c for c in e.columns if c.startswith(s)][0]  # noqa: E731
    r = pd.DataFrame({
        "cod_istat": e["Codice Comune formato alfanumerico"],
        "commune": e["Denominazione in italiano"],
        "commune_autre_langue": e["Denominazione altra lingua"],
        "code_uts": e[col("Codice dell'Unità territoriale sovracomunale")],
        "province_uts": e[col("Denominazione dell'Unità territoriale sovracomunale")],
        "sigle_province": e["Sigla automobilistica"],
        "code_region": e["Codice Regione"],
        "region": e["Denominazione Regione"],
        "repartition": e["Ripartizione geografica"],
        "chef_lieu": e[col("Flag Comune capoluogo")],
        "code_cadastral_belfiore": e["Codice Catastale del Comune"],
        "cod_istat_2017_2025": e[col("Codice Comune numerico con 107 Province (dal 2017")].str.zfill(6),
        "cod_istat_2010_2016": e[col("Codice Comune numerico con 110 Province")].str.zfill(6),
        "nuts3_2024": e[col("Codice NUTS3 2024")],
    })
    # Sardaigne : code précédent officiel
    sd = pd.read_csv(f("istat_codici/*/sardegna/*/*.csv"), sep=";", encoding="latin-1", dtype=str, skiprows=1, **NA)
    sd.columns = [c.replace("\n", " ").strip() for c in sd.columns]
    sd = sd.rename(columns={"Codice Comune": "cod_istat", "Codice Comune precedente": "cod_istat_avant_2026_sardaigne"})
    r = r.merge(sd[["cod_istat", "cod_istat_avant_2026_sardaigne"]], on="cod_istat", how="left")
    # Altimétrie / superficie (ISTAT, 31/12/2021, codes de l'époque)
    a = pd.read_excel(f("istat_codici/*/Altimetria_Comuni*.xlsx"), sheet_name=0, skiprows=1, dtype=str, **NA)
    a["cod"] = a["PRO_COM"].str.zfill(6)
    a = a.rename(columns={"AREA_KMQ": "superficie_km2", "ALT MIN": "altitude_min_m", "ALT MAX": "altitude_max_m",
                          "ALT CENTR MUN": "altitude_centre_m"})[["cod", "superficie_km2", "altitude_min_m",
                                                                  "altitude_max_m", "altitude_centre_m"]]
    r = r.merge(a.rename(columns={"cod": "cod_istat"}), on="cod_istat", how="left")
    miss = r["superficie_km2"].isna()
    alt = r.loc[miss, ["cod_istat_2017_2025"]].merge(a, left_on="cod_istat_2017_2025", right_on="cod", how="left")
    for c in ["superficie_km2", "altitude_min_m", "altitude_max_m", "altitude_centre_m"]:
        r.loc[miss, c] = alt[c].values
    # Couronnes urbaines au 01/01/2026
    cu = pd.read_excel(f("istat_codici/*/Corone-urbane*.xlsx"), sheet_name="Comuni_01-01-2026", dtype=str, **NA)
    r = r.merge(cu[["PRO_COM_T", "CORONA_N", "CORONA_T"]].rename(
        columns={"PRO_COM_T": "cod_istat", "CORONA_N": "couronne_urbaine_n", "CORONA_T": "couronne_urbaine"}),
        on="cod_istat", how="left")
    return r


def contours(ref):
    shp = f("istat_confini/*/Com01012026_g/Com01012026_g_WGS84.shp")
    g = gpd.read_file(shp, encoding="utf-8")
    g["cod_istat"] = g["PRO_COM_T"].astype(str).str.zfill(6)
    # Fusions postérieures aux contours du 01/01/2026 : union géométrique des anciennes communes (signalée)
    FUSIONS = {"024129": ["024027", "024071"]}  # Castegnero Nanto = Castegnero + Nanto
    g["contour_statut"] = "officiel ISTAT 01/01/2026"
    for new, olds in FUSIONS.items():
        m = g["cod_istat"].isin(olds)
        g.loc[m, "cod_istat"] = new
        g.loc[m, "contour_statut"] = "union des contours ISTAT 2026 de " + "+".join(olds) + " (fusion postérieure)"
    g = g.dissolve(by="cod_istat", as_index=False, aggfunc={"contour_statut": "first"})
    g["superficie_km2_contour_2026"] = (g.geometry.area / 1e6).round(4)
    cent = g.copy()
    cent["geometry"] = g.geometry.representative_point()  # point garanti à l'intérieur (calcul en EPSG:32632)
    cent = cent.to_crs(4326)
    c = pd.DataFrame({"cod_istat": cent["cod_istat"], "lat": cent.geometry.y.round(6), "lon": cent.geometry.x.round(6),
                      "superficie_km2_contour_2026": g["superficie_km2_contour_2026"], "contour_statut": g["contour_statut"]})
    web = g[["cod_istat", "contour_statut", "geometry"]].copy()
    web["geometry"] = web.geometry.simplify(150, preserve_topology=True)  # tolérance 150 m (EPSG:32632)
    web = web.to_crs(4326).merge(ref[["cod_istat", "commune", "sigle_province", "region"]], on="cod_istat", how="left")
    out = os.path.join(ROOT, "data", "it")
    os.makedirs(out, exist_ok=True)
    web.to_file(os.path.join(out, "communes_it.geojson"), driver="GeoJSON", COORDINATE_PRECISION=5)
    for lvl, pat in [("provinces", "ProvCM01012026_g/*.shp"), ("regions", "Reg01012026_g/*.shp")]:
        p = gpd.read_file(f("istat_confini/*/" + pat), encoding="utf-8")
        p["geometry"] = p.geometry.simplify(300, preserve_topology=True)
        p.to_crs(4326).to_file(os.path.join(out, f"{lvl}_it.geojson"), driver="GeoJSON", COORDINATE_PRECISION=5)
    return c


if __name__ == "__main__":
    ref = referentiel()
    cen = contours(ref)
    ref = ref.merge(cen, on="cod_istat", how="left")
    M = meta("ISTAT - Elenco comuni italiani; Confini unità amministrative 01/01/2026; Altimetria; Corone urbane",
             "https://www.istat.it/classificazione/codici-dei-comuni-delle-province-e-delle-regioni/", "2026")
    save(ref, "referentiel_communes", M)
    save(cen, "communes_it_centroides", M, csv_only=True)
    print("communes:", len(ref), "| 001168 =", ref.loc[ref.cod_istat == "001168", "commune"].tolist(),
          "| sans centroïde:", ref["lat"].isna().sum(), "| sans superficie:", ref["superficie_km2"].isna().sum())
