# Comics scout

Daily search of Czech second-hand sites and shops for five kinds of comics:

1. **Mighty Boys** – only *Přístav Země / Zatmění* and *Trojka* (normal and collector's editions)
2. **Tales from the Crypt** – any edition
3. **Kolosální Conan** – the big Comics Centrum hardcovers: only **vol. 1** and any newer volume (vol. 2 z Cimerie, 3 Král aquilonský, 4 Kapitán pirátů and 5 Mstitel are excluded)
4. **Banda** – Czech edition of *The Boys* by Garth Ennis (Crew), all volumes
5. **Criminal** – Ed Brubaker & Sean Phillips, Czech edition only

## How it runs

A scheduled Claude task ("Comics scout daily (cloud)") runs every morning at 6:43 Prague time, fully in the cloud – no computer needs to be on. Each run:

1. Searches all sites below with `scout.py`, using the terms in `search-terms.txt`.
2. Does not check publisher shops (mightyboys.cz and comicscentrum.cz were removed from the scout).
3. Builds a fresh file `history/listings-YYYY-MM-DD.txt` with **all findings** (no comparison with earlier days) using `report.py` (kept in the run's workspace; the task uses GitHub read-only and pushes nothing).
4. Updates the Claude page **"Comics scout – latest findings"** (https://claude.ai/artifact/Ad5jGHU2bTPriSMAjBxNow) with the same findings and the run's timestamp (Prague time).
5. Sends an HTML report and a push notification, plus a Gmail e-mail "Comics scout – DD/MM/YYYY" with one line per book found (no table).

The full procedure the task follows is in `SKILL.md`.

## Sites

| Site | What it is | Status |
|---|---|---|
| Bazoš | General classifieds | ✅ searched |
| Sbazar | Seznam's classifieds | ✅ searched |
| KomiksBazar | Comics collectors' ads + offers from antiquarian shops (incl. many **Aukro** listings) | ✅ searched |
| Trh knih | Online antiquarian marketplace (shows the lowest current offer per book) | ✅ searched |
| Restorio | Second-hand bookshop (only copies in stock are reported) | ✅ searched via its Doofinder search |
| Knihobot | Second-hand bookshop (only copies in stock) | ✅ searched via its own JSON search |
| Reknihy | Second-hand bookshop (only copies in stock) | ✅ searched via its Luigi's Box search |
| Antikavion | Antiquarian bookshop (only books with a copy for sale) | ✅ searched |
| Antikvariaty.cz | Antiquarian bookshop catalogue | ✅ searched (rarely has these titles) |
| Arkham | Comics bookshop (new + second-hand) | ✅ searched |
| comicscentrum.cz | Publisher (Kolosální Conan) | ⏸ removed from the scout (2026-11-19) |
| mightyboys.cz | Publisher (Mighty Boys) | ⏸ removed from the scout (2026-11-19) |
| Aukro (directly) | Auctions | ❌ Cloudflare blocks cloud requests – partly covered via KomiksBazar |
| ComicsDB Bazar | Community bazaar | ❌ blocks automated access |
| Facebook Marketplace | – | excluded |

All searching is polite: one request per term per site, 2–6 s pauses, sites searched in parallel, and a site stops at its first error or block (never retried). Note: these sites' robots.txt files ask automated tools not to search; the owner of this repo chose to search them anyway at this low volume.

## Files

| File | What it is |
|---|---|
| `scout.py` | Searches all sites, prints JSON. Python 3 + `curl`, no other packages. |
| `report.py` | Turns the JSON into the readable daily file, removes known search noise. |
| `search-terms.txt` | One search term per line – add a title here to include it. |
| `SKILL.md` | Step-by-step instructions the daily task follows. |
| `claude_scheduler.txt` | The scheduled task's settings (schedule, notifications, full instructions). |
| `history/` | One text file per day with everything found. |

## Run it yourself

Linux / WSL / Raspberry Pi:
```bash
python3 scout.py --terms search-terms.txt > results.json
python3 report.py results.json history/listings-$(date +%F).txt
```

Windows 11 (PowerShell; Python 3 installed, `curl` is built in):
```powershell
py scout.py --terms search-terms.txt > results.json
py report.py results.json "history/listings-$(Get-Date -Format yyyy-MM-dd).txt"
```

Only some sites or terms: `python3 scout.py "kolosální conan" --sites bazos,sbazar`
