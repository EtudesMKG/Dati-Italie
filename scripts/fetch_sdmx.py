"""Telechargement sequentiel (limite ISTAT ~5 req/min) des flux SDMX retenus -> raw/sdmx/*.csv"""
import os
import istat_sdmx as s

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "raw", "sdmx")
os.makedirs(OUT, exist_ok=True)

jobs = [("60_1004_DF_DCIS_MUSVIS_COM_1", "all", {}, "musei_comuni")]
for y in range(2012, 2024):
    jobs.append(("183_285_DF_DICA_ASIAULP_7", "A..LU+LUEMPDAA.0010+I+55+56.TOTAL",
                 {"startPeriod": y, "endPeriod": y}, f"asia_ul_{y}"))
jobs += [
    ("68_357_DF_DCCV_TURNOT_CAPI_3", "all", {}, "viaggi_notti_destinazione_tipo"),
    ("68_1221_DF_DCCV_VIAGGI_CAPI_2_7", "all", {}, "viaggi_lavoro"),
    ("68_1221_DF_DCCV_VIAGGI_CAPI_2_1", "all", {}, "viaggi_vacanze"),
]

for flow, key, p, name in jobs:
    path = os.path.join(OUT, name + ".csv")
    if os.path.exists(path):
        continue
    try:
        d = s.data(flow, key, **p)
        d.to_csv(path, index=False)
        print("OK", name, d.shape, flush=True)
    except Exception as e:
        print("ERR", name, str(e)[:300], flush=True)
