"""Petit client SDMX pour l'API ISTAT (esploradati.istat.it)."""
import io, re, time, os, hashlib
import requests
import pandas as pd

BASE = "https://esploradati.istat.it/SDMXWS/rest"
CACHE = os.environ.get("ISTAT_CACHE", os.path.join(os.path.dirname(__file__), "..", "cache"))
os.makedirs(CACHE, exist_ok=True)
S = requests.Session()
_LAST = 0.0


def _get(url, accept=None, timeout=900, tries=4):
    key = hashlib.md5((url + str(accept)).encode()).hexdigest()
    p = os.path.join(CACHE, key)
    if os.path.exists(p):
        return open(p, "rb").read()
    last = None
    global _LAST
    for i in range(tries):
        wait = 15 - (time.time() - _LAST)
        if wait > 0:
            time.sleep(wait)  # ISTAT: max ~5 requetes/minute
        _LAST = time.time()
        try:
            r = S.get(url, headers={"Accept": accept} if accept else {}, timeout=timeout)
            if r.status_code == 200:
                open(p, "wb").write(r.content)
                return r.content
            if r.status_code == 404:
                raise FileNotFoundError(f"404 {url}: {r.text[:300]}")
            last = f"HTTP {r.status_code}: {r.text[:300]}"
        except (requests.RequestException,) as e:
            last = repr(e)
        time.sleep(5 * (2 ** i))
    raise RuntimeError(f"echec {url}: {last}")


def structure(flow):
    """Dimensions du DSD + codelists (id -> {code: libelle it})."""
    x = _get(f"{BASE}/dataflow/IT1/{flow}/latest?references=all&detail=full").decode("utf-8")
    dims = re.findall(r'<structure:Dimension id="([^"]+)"[^>]*position="(\d+)".*?<Ref id="(CL_[^"]+)"', x, re.S)
    cls = {}
    for m in re.finditer(r'<structure:Codelist id="([^"]+)".*?</structure:Codelist>', x, re.S):
        codes = {}
        for c in re.finditer(r'<structure:Code id="([^"]+)"[^>]*>(.*?)</structure:Code>', m.group(0), re.S):
            it = re.search(r'<common:Name xml:lang="it">([^<]*)', c.group(2))
            en = re.search(r'<common:Name xml:lang="en">([^<]*)', c.group(2))
            codes[c.group(1)] = (it or en).group(1) if (it or en) else ""
        cls[m.group(1)] = codes
    return dims, cls


def available(flow):
    """Valeurs effectivement présentes par dimension."""
    x = _get(f"{BASE}/availableconstraint/{flow}").decode("utf-8")
    out = {}
    for m in re.finditer(r'<common:KeyValue id="([^"]+)">(.*?)</common:KeyValue>', x, re.S):
        out[m.group(1)] = re.findall(r"<common:Value>([^<]*)</common:Value>", m.group(2))
    return out


def data(flow, key="all", **params):
    q = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{BASE}/data/{flow}/{key}" + (f"?{q}" if q else "")
    raw = _get(url, accept="application/vnd.sdmx.data+csv;version=1.0.0")
    return pd.read_csv(io.BytesIO(raw), dtype=str)
