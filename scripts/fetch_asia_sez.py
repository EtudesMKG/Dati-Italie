"""ASIA unités locales 2023 par section Ateco, par lots (requête unique trop lourde pour ISTAT)."""
import os
import pandas as pd
import istat_sdmx as s

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "raw", "sdmx", "asia_ul_sezioni_2023.csv")
LOTS = ["A+B+C+D", "E+F+G+H", "J+K+L+M", "N+P", "Q+R+S"]  # 0010 et I déjà dans asia_ul_*.csv
parts = []
for lot in LOTS:
    d = s.data("183_285_DF_DICA_ASIAULP_7", f"A..LU+LUEMPDAA.{lot}.TOTAL", startPeriod=2023, endPeriod=2023)
    parts.append(d[d.TIME_PERIOD == "2023"])
    print("OK", lot, d.shape, flush=True)
old = pd.concat([pd.read_csv(os.path.join(os.path.dirname(OUT), "asia_ul_2023.csv"), dtype=str)])
parts.append(old[(old.TIME_PERIOD == "2023") & old.ECON_ACTIVITY_NACE_2007.isin(["0010", "I"])])
pd.concat(parts, ignore_index=True).to_csv(OUT, index=False)
print("écrit", OUT, flush=True)
