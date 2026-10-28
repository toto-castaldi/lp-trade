# Dischi in vendita

Vetrina online di una collezione di LP in vinile in vendita: 118 dischi, ciascuno con foto di copertina fronte e retro, artista, titolo e anno.

**Sito:** https://toto-castaldi.github.io/lp-trade/

## Funzionalità

- Griglia delle copertine, ottimizzata anche per smartphone
- Scheda di dettaglio per ogni disco con foto fronte/retro
- Ricerca per artista o titolo
- Ordinamento per artista o per anno
- Download dell'elenco completo in PDF
- Area riservata (protetta da password) con quotazioni, valore complessivo, ordinamento per prezzo e riferimenti Discogs

## Come funziona l'area riservata

Il sito è statico e pubblico, ma le quotazioni non sono mai pubblicate in chiaro: vengono cifrate con AES-256-GCM (chiave derivata dalla password con PBKDF2-SHA256) nel file `prices.enc.json` e decifrate direttamente nel browser solo inserendo la password corretta.

## Sviluppo

Requisiti: Python 3 con `cryptography`, `reportlab` e `Pillow`.

```sh
python3 build.py              # genera records.js, prices.enc.json e dischi.pdf
python3 -m http.server 8000   # anteprima su http://localhost:8000
```

- `data/catalog.tsv` — catalogo dei dischi (foto, artista, titolo, anno)
- `photos/` — foto delle copertine (`thumbs/` per la griglia)
- `discogs.py` — raccoglie dati di mercato dall'API pubblica di Discogs
- `index.html` — l'intero sito, senza dipendenze esterne a parte i font

Le quotazioni in chiaro e la password restano solo in locale (vedi `.gitignore`).
