#!/usr/bin/env python3
"""Genera i file del sito a partire da data/.

- records.js: dati pubblici (artista, titolo, anno, foto). Nessun prezzo.
- prices.enc.json: quotazioni e dati Discogs cifrati con AES-GCM; la chiave è
  derivata (PBKDF2-SHA256) dalla password in .prices-password, che non va
  committata. index.html li decifra nel browser quando si inserisce la password.
"""
import base64
import csv
import glob
import json
import os
import secrets
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

ROOT = Path(__file__).parent
DATA = ROOT / "data"
PASSWORD_FILE = ROOT / ".prices-password"
PBKDF2_ITERATIONS = 310_000


def password():
    if not PASSWORD_FILE.exists():
        PASSWORD_FILE.write_text(secrets.token_urlsafe(12) + "\n")
        os.chmod(PASSWORD_FILE, 0o600)
        print(f"Creata nuova password in {PASSWORD_FILE}")
    return PASSWORD_FILE.read_text().strip()


def encrypt(payload, pw):
    salt, iv = os.urandom(16), os.urandom(12)
    key = PBKDF2HMAC(algorithm=SHA256(), length=32, salt=salt,
                     iterations=PBKDF2_ITERATIONS).derive(pw.encode())
    ct = AESGCM(key).encrypt(iv, json.dumps(payload, ensure_ascii=False).encode(), None)
    b64 = lambda b: base64.b64encode(b).decode()
    return {"iterations": PBKDF2_ITERATIONS, "salt": b64(salt), "iv": b64(iv), "data": b64(ct)}


def main():
    quotes = {}
    for f in sorted(glob.glob(str(DATA / "quotes_*.json"))):
        for q in json.loads(Path(f).read_text()):
            quotes[str(q["front"])] = q

    discogs_path = DATA / "discogs.json"
    discogs = json.loads(discogs_path.read_text()) if discogs_path.exists() else {}

    records, prices = [], {}
    with open(DATA / "catalog.tsv", newline="") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            q = quotes.get(row["front"], {})
            releases = discogs.get(row["front"], {}).get("releases", [])
            records.append({
                "id": row["front"],
                "artist": q.get("artist") or row["artist"],
                "title": q.get("title") or row["title"],
                "year": int(q.get("year") or row["year"]),
                "front": f"IMG_{row['front']}.jpg",
                "back": f"IMG_{row['back']}.jpg",
            })
            prices[row["front"]] = {
                "price_min": q.get("price_min"),
                "price_max": q.get("price_max"),
                "price": q.get("price_suggested"),
                "source": q.get("source"),
                "source_url": q.get("source_url"),
                "note": q.get("note"),
                "discogs": [
                    {k: r[k] for k in ("title", "year", "country", "catno", "label",
                                       "have", "want", "num_for_sale", "lowest_eur", "url")}
                    for r in releases
                ],
            }

    (ROOT / "records.js").write_text(
        "window.RECORDS = " + json.dumps(records, ensure_ascii=False, indent=1) + ";\n")
    (ROOT / "prices.enc.json").write_text(json.dumps(encrypt(prices, password())))
    priced = sum(1 for p in prices.values() if p["price"] is not None)
    print(f"{len(records)} dischi, {priced} con quotazione (cifrate in prices.enc.json)")


if __name__ == "__main__":
    main()
