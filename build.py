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


def build_pdf(records, out):
    """Lista pubblica dei dischi (copertina, artista, titolo, anno). Mai prezzi."""
    import io
    from datetime import date

    from PIL import Image as PILImage
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    font, bold = "Helvetica", "Helvetica-Bold"
    dejavu = Path("/usr/share/fonts/truetype/dejavu")
    if (dejavu / "DejaVuSans.ttf").exists():
        pdfmetrics.registerFont(TTFont("DejaVu", str(dejavu / "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(dejavu / "DejaVuSans-Bold.ttf")))
        font, bold = "DejaVu", "DejaVu-Bold"

    ink, muted, line = colors.HexColor("#1e1a16"), colors.HexColor("#6f655a"), colors.HexColor("#e2d8c8")
    h1 = ParagraphStyle("h1", fontName=bold, fontSize=22, leading=26, textColor=ink)
    sub = ParagraphStyle("sub", fontName=font, fontSize=10, leading=14, textColor=muted)
    artist = ParagraphStyle("artist", fontName=font, fontSize=8, leading=10, textColor=muted)
    title = ParagraphStyle("title", fontName=bold, fontSize=10.5, leading=13, textColor=ink)
    cell = ParagraphStyle("cell", fontName=font, fontSize=10, leading=13, textColor=ink)

    def cover(name):
        im = PILImage.open(ROOT / "photos" / "thumbs" / name).convert("RGB")
        side = min(im.size)  # ritaglio quadrato centrato, come nella griglia del sito
        left, top = (im.width - side) // 2, (im.height - side) // 2
        im = im.crop((left, top, left + side, top + side)).resize((160, 160))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=72)
        buf.seek(0)
        return Image(buf, width=16 * mm, height=16 * mm)

    esc = lambda s: str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    ordered = sorted(records, key=lambda r: (r["artist"].casefold(), r["year"]))
    rows = [[Paragraph("<b>#</b>", sub), "", Paragraph("<b>Artista / Titolo</b>", sub), Paragraph("<b>Anno</b>", sub)]]
    for i, r in enumerate(ordered, 1):
        rows.append([
            Paragraph(str(i), sub),
            cover(r["front"]),
            [Paragraph(esc(r["artist"]).upper(), artist), Paragraph(esc(r["title"]), title)],
            Paragraph(str(r["year"]), cell),
        ])

    table = Table(rows, colWidths=[10 * mm, 20 * mm, 128 * mm, 16 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, line),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
    ]))

    def footer(canvas, doc):
        canvas.setFont(font, 8)
        canvas.setFillColor(muted)
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Pagina {doc.page}")

    doc = SimpleDocTemplate(str(out), pagesize=A4, title="Dischi in vendita",
                            leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm)
    doc.build([
        Paragraph("Dischi in vendita", h1),
        Paragraph(f"{len(records)} LP · elenco aggiornato al {date.today():%d/%m/%Y}", sub),
        Spacer(1, 6 * mm),
        table,
    ], onFirstPage=footer, onLaterPages=footer)


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
    build_pdf(records, ROOT / "dischi.pdf")
    priced = sum(1 for p in prices.values() if p["price"] is not None)
    print(f"{len(records)} dischi, {priced} con quotazione (cifrate in prices.enc.json)")


if __name__ == "__main__":
    main()
