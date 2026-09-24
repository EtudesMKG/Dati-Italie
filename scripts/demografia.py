"""Population communale ISTAT (demo.istat.it) : fichiers bruts -> tableaux."""
import glob, os, re
import pandas as pd

RAW = os.path.join(os.path.dirname(__file__), "..", "raw", "demo")


def _read(f):
    return pd.read_csv(f, sep=";", skiprows=1, dtype={"Codice comune": str}, encoding="utf-8-sig",
                       decimal=",", skipfooter=0, engine="python", on_bad_lines="skip")


def posas():
    """Population au 1er janvier par sexe et classes d'âge (2019-2026)."""
    out = {}
    for f in sorted(glob.glob(os.path.join(RAW, "POSAS_*_it_Comuni.csv"))):
        y = int(re.search(r"POSAS_(\d{4})", f).group(1))
        d = _read(f)
        d = d[d["Codice comune"].str.fullmatch(r"\d{6}", na=False)]
        d["Età"] = pd.to_numeric(d["Età"])
        out[y] = d[["Codice comune", "Comune", "Età", "Totale maschi", "Totale femmine", "Totale"]]
    return out


def ricostruzione():
    """Population reconstruite au 1er janvier 2014-2018 (toutes nationalités), total/M/F."""
    rows = []
    for f in glob.glob(os.path.join(RAW, "ric", "*.csv")):
        year = sesso = None
        tutte = False
        for line in open(f, encoding="utf-8-sig", errors="replace"):
            line = line.rstrip("\n\r")
            m = re.match(r'"(.*?) - Anno: (\d{4})', line)
            if m:
                tutte = m.group(1) == "Tutte le cittadinanze"
                year = int(m.group(2))
                continue
            if line.startswith("Codice comune;Comune;"):
                sesso = line.split(";")[2]
                continue
            if not tutte or year is None or year < 2014:
                continue
            p = line.split(";")
            if len(p) > 3 and re.fullmatch(r"\d{6}", p[0]):
                rows.append((p[0], p[1], year, sesso, sum(int(x) for x in p[2:] if x.strip())))
    d = pd.DataFrame(rows, columns=["cod", "comune", "anno", "sesso", "pop"])
    return d


def bilancio():
    out = {}
    for f in sorted(glob.glob(os.path.join(RAW, "P2_*_it_Comuni.csv"))):
        y = int(re.search(r"P2_(\d{4})", f).group(1))
        d = _read(f)
        out[y] = d[d["Codice comune"].str.fullmatch(r"\d{6}", na=False)]
    return out
