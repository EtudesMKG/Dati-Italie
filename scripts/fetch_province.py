"""Entreprises et salariés par PROVINCE (ISTAT ASIA, SDMX) -> raw/sdmx/prov_*.csv
Le nombre d'entreprises (sièges) et de salariés n'est pas diffusé par commune : niveau provincial."""
import os
import istat_sdmx as s

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "raw", "sdmx")
SECTIONS = "0010+B+C+D+E+F+G+H+I+J+K+L+M+N+P+Q+R+S+55+56"


def key(flow, **fix):
    dims, _ = s.structure(flow)
    return ".".join(fix.get(d, "") for d, _, _ in sorted(dims, key=lambda x: int(x[1])))


jobs = []
# 1) Entreprises actives + actifs occupés, par secteur et présence de salariés, 2012-2024
# (une requête par secteur : ISTAT coupe les requêtes multi-secteurs)
for sec in SECTIONS.split("+"):
    jobs.append(("183_277_DF_DICA_ASIAUE1P_4",
                 dict(FREQ="A", DATA_TYPE="AENTN+AENTEMPDAA", ECON_ACTIVITY_NACE_2007=sec,
                      PERS_EMPL_SIZE_CLASS="TOTAL", LEGAL_FORM="TOT", Y_ENTER_WITH_EMPLOYEES="9+1+0", Y_CRAFTMEN="9"),
                 {}, f"prov_imprese_settore_{'TOTAL' if sec == '0010' else sec}"))
# 2) Entreprises par forme juridique (tous secteurs), 2012-2024
jobs.append(("183_277_DF_DICA_ASIAUE1P_4",
             dict(FREQ="A", DATA_TYPE="AENTN+AENTEMPDAA", ECON_ACTIVITY_NACE_2007="0010", PERS_EMPL_SIZE_CLASS="TOTAL",
                  Y_ENTER_WITH_EMPLOYEES="9", Y_CRAFTMEN="9"), {}, "prov_imprese_forma_giuridica"))
# 3) Entreprises par classe de taille (tous secteurs)
jobs.append(("183_277_DF_DICA_ASIAUE1P_5",
             dict(FREQ="A", DATA_TYPE="AENTN+AENTEMPDAA", ECON_ACTIVITY_NACE_2007="0010", LEGAL_FORM="TOT",
                  PERS_EMPL_SIZE_CLASS="TOTAL+W0_9+W10_49+W50_249+W_GE250"), {}, "prov_imprese_classe_addetti"))
# 4) Salariés (dipendenti) des unités locales par qualification, 2012-2017
jobs.append(("183_332_DF_DICA_ASIAULOCCP_3",
             dict(FREQ="A", DATA_TYPE="LUEMPYAA", ECON_ACTIVITY_NACE_2007="0010", PERS_EMPL_SIZE_CLASS="TOTAL",
                  SEX="9", AGE="Y_GE15", COUNTRY_BIRTH="WORLD"), {}, "prov_dipendenti_qualifica"))
# 5) Salariés (dipendenti) des unités locales par secteur et sexe, 2012-2017
for sec in SECTIONS.split("+"):
    jobs.append(("183_332_DF_DICA_ASIAULOCCP_4",
                 dict(FREQ="A", DATA_TYPE="LUEMPYAA", ECON_ACTIVITY_NACE_2007=sec, PERS_EMPL_SIZE_CLASS="TOTAL",
                      AGE="Y_GE15", COUNTRY_BIRTH="WORLD", PROF_STATUS="99"), {},
                 f"prov_dipendenti_settore_{'TOTAL' if sec == '0010' else sec}"))

for flow, fix, p, name in jobs:
    path = os.path.join(OUT, name + ".csv")
    if os.path.exists(path):
        continue
    try:
        d = s.data(flow, key(flow, **fix), **p)
        d.to_csv(path, index=False)
        print("OK", name, d.shape, flush=True)
    except Exception as e:
        print("ERR", name, str(e)[:300], flush=True)
