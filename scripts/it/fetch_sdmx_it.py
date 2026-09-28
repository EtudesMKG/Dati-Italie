"""Flux ISTAT SDMX complémentaires (communes) -> raw/istat_sdmx/<date>/*.csv
- ASIA unités locales par classe de taille (0-9, 10-49, 50-249, 250+) par commune
- Institutions publiques / non profit / agriculture : test sur Florence (048017) puis extraction complète si niveau communal
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import istat_sdmx as s  # noqa: E402
from dl import ROOT, TODAY  # noqa: E402

OUT = os.path.join(ROOT, "raw", "istat_sdmx", TODAY)
os.makedirs(OUT, exist_ok=True)


def key(flow, **fix):
    dims, _ = s.structure(flow)
    return ".".join(fix.get(d, "") for d, _, _ in sorted(dims, key=lambda x: int(x[1])))


def save(name, flow, k, **p):
    path = os.path.join(OUT, name + ".csv")
    if os.path.exists(path):
        return
    try:
        d = s.data(flow, k, **p)
        d.to_csv(path, index=False)
        print("OK", name, d.shape, flush=True)
    except Exception as e:
        print("ERR", name, str(e)[:250], flush=True)


# 1) ASIA UL par classe de taille, toutes communes, par blocs d'années
# (une classe par requête : ISTAT renvoie une erreur 500 sur les requêtes multi-classes au niveau communal)
for cl in ["W_GE250", "W50_249", "W10_49", "W0_9"]:
    save(f"asia_ul_taille_{cl}", "183_285_DF_DICA_ASIAULP_7",
         key("183_285_DF_DICA_ASIAULP_7", FREQ="A", DATA_TYPE="LU+LUEMPDAA", ECON_ACTIVITY_NACE_2007="0010",
             PERS_EMPL_SIZE_CLASS=cl))

# 2) Flux institutions / agriculture : test communal puis extraction complète
for name, flow in [("istituzioni_pubbliche_ul_comuni", "741_1099_DF_DICA_IPSTRULCOM_1"),
                   ("nonprofit_sintesi", "740_1091_DF_DICA_N03G_1"),
                   ("nonprofit_risorse_umane", "741_1096_DF_DICA_IPSTRIPNP_1"),
                   ("agricoltura_manodopera", "102_974_DF_DCSP_SPA_14"),
                   ("agricoltura_aziende_superfici", "102_974_DF_DCSP_SPA_6")]:
    dims, _ = s.structure(flow)
    test = key(flow, FREQ="A", REF_AREA="048017")
    try:
        t = s.data(flow, test)
        print("TEST communal OK", name, t.shape, flush=True)
        save(name, flow, key(flow, FREQ="A"))
    except Exception as e:
        print("TEST communal ÉCHEC", name, str(e)[:150], flush=True)
