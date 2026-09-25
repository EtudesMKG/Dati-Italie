"""Emploi par commune (ISTAT SDMX) : recensement permanent + ASIA toutes sections -> raw/sdmx/*.csv"""
import os
import istat_sdmx as s

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "raw", "sdmx")
os.makedirs(OUT, exist_ok=True)


def key(flow, **fix):
    """Clé SDMX : dimensions fixées par nom, les autres vides (= toutes)."""
    dims, _ = s.structure(flow)
    return ".".join(fix.get(d, "") for d, _, _ in sorted(dims, key=lambda x: int(x[1])))


SECTIONS = "0010+A+B+C+D+E+F+G+H+I+J+K+L+M+N+P+Q+R+S"
jobs = [
    # Occupés résidents par position (total / salariés / indépendants), recensement permanent
    ("DF_DCSS_EMPLP_1_COM", dict(FREQ="A"), {}, "occupati_posizione_comuni"),
    # Occupés résidents par secteur d'activité
    ("DF_DCSS_EMPLP_2_COM", dict(FREQ="A", GENDER="T"), {}, "occupati_settore_comuni"),
    # Population 15+ par condition professionnelle (occupés, chômeurs, inactifs)
] + [
    ("DF_DCSS_ISTR_LAV_PEN_2_TV_3", dict(FREQ="A", INDICATOR="RESPOP_AV", GENDER="T", AGE_NOCLASS="Y_GE15",
                                         CITIZENSHIP="TOTAL", EDU_ATTAIN="ALL", CUR_ACT_STAT="1+12+22+23+99",
                                         LOC_DEST="ALL", REAS_COMMUTING="ALL"),
     {"startPeriod": y, "endPeriod": y}, f"condizione_professionale_{y}") for y in range(2018, 2025)
] + [
    # ASIA unités locales et actifs, toutes sections Ateco, dernier millésime
    ("183_285_DF_DICA_ASIAULP_7", dict(FREQ="A", DATA_TYPE="LU+LUEMPDAA", ECON_ACTIVITY_NACE_2007=SECTIONS,
                                       PERS_EMPL_SIZE_CLASS="TOTAL"), {"startPeriod": 2023}, "asia_ul_sezioni_2023"),
]

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
