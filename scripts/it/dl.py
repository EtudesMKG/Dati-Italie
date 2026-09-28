"""Téléchargement brut avec cache raw/<source>/<date>/ , 1 requête/s/domaine, User-Agent explicite."""
import os, sys, time, datetime, requests
from urllib.parse import urlparse
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
UA = {"User-Agent": "MKG-EtudeMarche-IT/1.0 (collecte open data officielle; contact etudes@mkg-group.com)"}
_last = {}
TODAY = datetime.date.today().isoformat()


def get(url, source, name=None, date=None, timeout=600):
    name = name or os.path.basename(urlparse(url).path) or "index.html"
    for d in sorted(os.listdir(os.path.join(ROOT, "raw", source))) if os.path.isdir(os.path.join(ROOT, "raw", source)) else []:
        p = os.path.join(ROOT, "raw", source, d, name)
        if os.path.exists(p) and os.path.getsize(p) > 0:
            return p
    out = os.path.join(ROOT, "raw", source, date or TODAY)
    os.makedirs(out, exist_ok=True)
    h = urlparse(url).netloc
    w = 1.0 - (time.time() - _last.get(h, 0))
    if w > 0:
        time.sleep(w)
    _last[h] = time.time()
    r = requests.get(url, headers=UA, timeout=timeout)
    r.raise_for_status()
    p = os.path.join(out, name)
    open(p, "wb").write(r.content)
    return p


if __name__ == "__main__":
    src = sys.argv[1]
    for u in sys.argv[2:]:
        try:
            print("OK", get(u, src), flush=True)
        except Exception as e:
            print("ERR", u, str(e)[:150], flush=True)
