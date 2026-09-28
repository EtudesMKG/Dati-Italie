"""Utilitaires communs : lecture sûre ('None' = commune 001168), métadonnées, sauvegarde Parquet + CSV."""
import datetime
import os

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(ROOT, "data", "it")
# Ne jamais convertir 'None', 'NA', 'nan'... en vide : la commune 001168 s'appelle 'None'
NA = dict(keep_default_na=False, na_values=[""])
TODAY = datetime.date.today().isoformat()


def meta(source, url, millesime):
    return dict(source=source, url_source=url, date_extraction=TODAY, millesime=str(millesime))


def status_split(df, cols, marks=("(*)", "*", "c", "-", "..", "x")):
    """Valeur numérique dans la colonne, marque ISTAT de secret/absence dans <col>_statut."""
    for c in cols:
        s = df[c].astype(str).str.strip()
        df[c + "_statut"] = s.where(s.isin(marks), "")
        df[c] = pd.to_numeric(s.where(~s.isin(marks)).str.replace(",", ".", regex=False), errors="coerce")
    return df


def save(df, name, m, csv_only=False):
    os.makedirs(OUT, exist_ok=True)
    df = df.copy()
    for k, v in m.items():
        if k not in df.columns:
            df[k] = v
    if "cod_istat" in df.columns:
        c = df["cod_istat"].astype("string").str.strip()
        df["cod_istat"] = c.where(c.isna() | (c == ""), c.str.zfill(6)).replace("", pd.NA)
    df.to_csv(os.path.join(OUT, name + ".csv"), index=False, encoding="utf-8")
    if not csv_only:
        df.to_parquet(os.path.join(OUT, name + ".parquet"), index=False)
    return df
