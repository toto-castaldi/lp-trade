# lp-trade

Sito statico (GitHub Pages) che mostra una collezione di LP in vendita: copertina fronte/retro, artista, titolo, anno. Nessun framework né build JS: `index.html` + file generati.

## Regola fondamentale: i prezzi sono privati

Il repository e il sito sono **pubblici**. Prezzi, totale, note di quotazione e dati Discogs devono essere visibili solo al proprietario.

- I prezzi esistono in chiaro solo in file ignorati da git: `data/quotes_*.json`, `data/discogs.json`.
- `build.py` li cifra in `prices.enc.json` (AES-256-GCM, chiave PBKDF2-SHA256 dalla password in `.prices-password`, anch'esso ignorato).
- `index.html` decifra nel browser con Web Crypto dopo l'inserimento della password ("Area riservata").
- Non scrivere mai prezzi, password o dati di quotazione in `records.js`, `data/catalog.tsv`, `index.html`, commit message, README o in questo file. Prima di ogni commit verifica `git status --ignored` e che `records.js` non contenga campi di prezzo.

## Struttura

- `data/catalog.tsv` — catalogo pubblico (fonte di verità): `front`, `back` (numeri foto IMG_xxxx), `artist`, `title`, `year`.
- `data/quotes_*.json` — (privato) quotazioni per disco, chiave `front`: `price_min`, `price_max`, `price_suggested`, `source`, `source_url`, `note`; possono correggere `artist`/`title`/`year`.
- `data/discogs.json` — (privato) output di `discogs.py`: stampe trovate con copie in vendita, prezzo minimo, have/want.
- `photos/IMG_xxxx.jpg` — foto 1200px; `photos/thumbs/` — 500px per la griglia.
- `records.js` — generato, dati pubblici (`window.RECORDS`).
- `prices.enc.json` — generato, dati privati cifrati.

## Comandi

```sh
python3 build.py              # rigenera records.js e prices.enc.json (richiede il pacchetto `cryptography`)
python3 discogs.py            # interroga l'API pubblica Discogs (~25 req/min, riprende da dove si era fermato)
python3 -m http.server 8000   # anteprima locale su http://localhost:8000
```

Dopo aver modificato `data/` rilancia sempre `build.py` e committa `records.js` e `prices.enc.json`.

## Aggiungere dischi

1. Foto originali HEIC dall'iPhone: convertire con `pillow-heif` (ImageMagick fallisce su alcune HEIC con depth map), ridimensionare a 1200px in `photos/` e 500px in `photos/thumbs/`.
2. Aggiungere la riga in `data/catalog.tsv`.
3. Aggiungere la quotazione in un `data/quotes_*.json` ed eventualmente rilanciare `discogs.py`.
4. `python3 build.py`.

## Note

- Testi dell'interfaccia in italiano.
- I dischi sono per lo più stampe italiane; il valore dipende molto dalla stampa (prima edizione vs ristampa), quindi le quotazioni sono indicative.
- La ricerca Discogs per la musica classica spesso trova incisioni diverse: va verificata a mano.
