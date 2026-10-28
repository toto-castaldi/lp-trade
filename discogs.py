#!/usr/bin/env python3
"""Interroga l'API pubblica Discogs per ogni disco di data/catalog.tsv.

Per ogni disco cerca le stampe in vinile (prima italiane, poi qualsiasi paese)
e legge le statistiche del marketplace (copie in vendita, prezzo minimo in EUR).
Risultato in data/discogs.json. Senza token il limite è ~25 richieste/minuto.
"""
import csv
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

DATA = Path(__file__).parent / "data"
API = "https://api.discogs.com"
UA = "lp-trade/1.0 +https://github.com/"
PAUSE = 2.6  # secondi tra le richieste, per stare sotto il rate limit
MAX_RELEASES = 3


def get(path, **params):
    url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
    for attempt in range(5):
        time.sleep(PAUSE)
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(30)
                continue
            if e.code == 404:
                return None
            raise
    return None


def clean_title(title):
    title = re.sub(r"\(.*?\)", "", title)
    return title.split(" – ")[0].strip()


def search(row):
    artist = row["artist"].split(" – ")[0].strip()
    title = clean_title(row["title"])
    attempts = []
    if artist == "Artisti vari":
        attempts.append({"q": title, "country": "Italy"})
        attempts.append({"q": title})
    else:
        attempts.append({"artist": artist, "release_title": title, "country": "Italy"})
        attempts.append({"artist": artist, "release_title": title})
        attempts.append({"q": f"{artist} {title}"})
    for params in attempts:
        res = get("/database/search", type="release", format="Vinyl", per_page=10, **params)
        results = (res or {}).get("results") or []
        if results:
            return results, params
    return [], None


def main():
    out_path = DATA / "discogs.json"
    done = json.loads(out_path.read_text()) if out_path.exists() else {}
    with open(DATA / "catalog.tsv", newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))

    for i, row in enumerate(rows, 1):
        if row["front"] in done:
            continue
        results, params = search(row)
        # Le stampe più "possedute" sono quelle più probabili per una copia comune
        results.sort(key=lambda r: -(r.get("community") or {}).get("have", 0))
        releases = []
        for r in results[:MAX_RELEASES]:
            stats = get(f"/marketplace/stats/{r['id']}", curr_abbr="EUR") or {}
            lowest = (stats.get("lowest_price") or {}).get("value")
            releases.append({
                "id": r["id"],
                "title": r.get("title"),
                "year": r.get("year"),
                "country": r.get("country"),
                "catno": r.get("catno"),
                "label": (r.get("label") or [None])[0],
                "have": (r.get("community") or {}).get("have"),
                "want": (r.get("community") or {}).get("want"),
                "num_for_sale": stats.get("num_for_sale"),
                "lowest_eur": round(lowest, 2) if lowest is not None else None,
                "url": f"https://www.discogs.com/release/{r['id']}",
            })
        done[row["front"]] = {"query": params, "releases": releases}
        out_path.write_text(json.dumps(done, ensure_ascii=False, indent=1))
        best = releases[0] if releases else {}
        print(f"[{i}/{len(rows)}] {row['artist']} – {row['title']}: "
              f"{best.get('title')} ({best.get('country')}) min €{best.get('lowest_eur')} "
              f"in vendita {best.get('num_for_sale')}", flush=True)


if __name__ == "__main__":
    main()
