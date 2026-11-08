# Comics scout

Daily search of Czech second-hand sites and publisher shops for three kinds of comics:

1. **Mighty Boys** – every title from the Czech publisher Mighty Boys (normal and collector's editions)
2. **Tales from the Crypt** – any edition
3. **Kolosální Conan** – the big Comics Centrum hardcovers (vol. 1, z Cimerie, Král aquilonský, Kapitán pirátů, Mstitel, …)

## How it runs

A scheduled Claude task ("Comics scout daily (cloud)") runs every morning at 6:43 Prague time, fully in the cloud – no computer needs to be on. Each run:

1. Searches **Bazoš** with `bazos.py` using the terms in `search-terms.txt`.
2. Checks the publisher shops **mightyboys.cz** and **comicscentrum.cz** for prices, stock and new titles.
3. Writes **all findings** to a fresh file `history/listings-YYYY-MM-DD.txt` (no comparison with earlier days) and commits it to `main`.
4. Sends a short push summary.

The full procedure the task follows is in `SKILL.md`.

## Sites and their limits

| Site | Status |
|---|---|
| Bazoš | Searched directly from the cloud. Polite: one request per term, 2–6 s pauses, stops at the first error/CAPTCHA. |
| mightyboys.cz, comicscentrum.cz | Read directly. |
| Aukro | **Not automated yet.** Its Cloudflare check blocks cloud requests. Options: Aukro email alerts ("Hlídací pes") read via Gmail, Apify scraper, or a small job on a home Raspberry Pi / Synology. |

## Files

| File | What it is |
|---|---|
| `bazos.py` | Bazoš search script (Python 3, needs `curl`). Prints JSON. |
| `search-terms.txt` | One search term per line – add a title here to include it. |
| `SKILL.md` | Step-by-step instructions the daily task follows. |
| `history/` | One text file per day with everything found. |

## Run it yourself

Linux / WSL / Raspberry Pi:
```bash
python3 bazos.py --terms search-terms.txt > results.json
```

Windows 11 (PowerShell; Python 3 installed, `curl` is built in):
```powershell
py bazos.py --terms search-terms.txt > results.json
```

Or search for single terms: `python3 bazos.py "kolosální conan" "mighty boys"`
