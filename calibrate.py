#!/usr/bin/env python3
"""Ricalibra i prezzi suggeriti sui dati di mercato Discogs (data/discogs.json).

Scrive data/calibrated.json (privato, ignorato da git), che build.py applica
sopra le stime di data/quotes_*.json. I dischi senza dati Discogs mantengono
la stima originale.

Regola:
- base = copia meno cara oggi in vendita tra le stampe abbinate al disco
  (di solito in condizioni peggiori di una VG/VG+, quindi va maggiorata);
- moltiplicatore in base alla concorrenza (copie in vendita);
- +20% se il disco è molto cercato (want/have > 0.6);
- prezzo minimo 5 €.
"""
import glob
import json
from pathlib import Path

DATA = Path(__file__).parent / "data"
FLOOR = 5


def supply_factor(n):
    if n >= 80:
        return 1.6
    if n >= 30:
        return 1.8
    if n >= 10:
        return 2.0
    return 2.4


def nice(x):
    """Arrotonda a cifre da cartellino: interi sotto i 20 €, multipli di 5 sopra."""
    return int(round(x)) if x < 20 else int(5 * round(x / 5))


def main():
    quotes = {str(x["front"]): x for f in glob.glob(str(DATA / "quotes_*.json"))
              for x in json.loads(Path(f).read_text())}
    discogs = json.loads((DATA / "discogs.json").read_text())

    calibrated = {}
    for front, q in quotes.items():
        releases = [r for r in discogs.get(front, {}).get("releases", []) if r.get("lowest_eur")]
        if not releases:
            continue
        low = min(r["lowest_eur"] for r in releases)
        high = max(r["lowest_eur"] for r in releases)
        n = sum(r.get("num_for_sale") or 0 for r in releases)
        top = max(releases, key=lambda r: r.get("have") or 0)
        demand = (top.get("want") or 0) / max(top.get("have") or 1, 1)

        factor = supply_factor(n) * (1.2 if demand > 0.6 else 1)
        price = max(FLOOR, nice(low * factor))
        pmin = max(3, round(low * 1.2))
        pmax = max(price + 2, nice(high * 2.5))
        calibrated[front] = {
            "price_suggested": price,
            "price_min": min(pmin, price),
            "price_max": pmax,
            "previous": q.get("price_suggested"),
            "basis": (f"Discogs: {n} copie in vendita, la meno cara € {low:g}"
                      + (", disco molto cercato" if demand > 0.6 else "")),
        }

    (DATA / "calibrated.json").write_text(json.dumps(calibrated, ensure_ascii=False, indent=1))
    old = sum(q.get("price_suggested") or 0 for q in quotes.values())
    new = sum(calibrated.get(k, {}).get("price_suggested", q.get("price_suggested") or 0)
              for k, q in quotes.items())
    print(f"ricalibrati {len(calibrated)}/{len(quotes)} dischi · totale € {old} -> € {new}")


if __name__ == "__main__":
    main()
