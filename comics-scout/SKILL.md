# Comics scout – daily procedure

Instructions for the scheduled Claude task. Everything runs in the cloud; never use a browser or the user's computer.

## Goal
Find every current listing for (5 categories):
1. **Mighty Boys** – only **Přístav Země / Zatmění** (one book by Zack Kaplan) and **Trojka**, both normal and collector's (sběratelská) edition
2. **Tales from the Crypt** comics (any edition)
3. **Kolosální Conan** (Comics Centrum) – only **vol. 1** and any newer volume (6+). **Excluded:** vol. 2 z Cimerie, vol. 3 Král aquilonský, vol. 4 Kapitán pirátů, vol. 5 Mstitel. `report.py` drops these automatically; mixed bundle ads are kept.
4. **Banda** – Czech edition of *The Boys* by Garth Ennis (publisher Crew), every volume (Karty jsou rozdaný, Nakládačka, …). English *The Boys* editions are out of scope.
5. **Criminal** – comic by Ed Brubaker & Sean Phillips, **Czech edition only** (Criminal deluxe edice 1–2, Každý je zločinec, Noční rozhodnutí, Poslední z nevinných, …). English editions are out of scope. "Criminal" is a common word: on bazaar sites a listing counts only if it also mentions Brubaker, Phillips or komiks/comics; on book catalogues (Trh knih, Knihobot, Antikavion, …) a title starting with "Criminal" is enough. `report.py` applies this.

**Sold-out items are out of scope:** anything marked "Vyprodáno", "Momentálně nedostupné", "Není skladem", "sold out" or "out of stock" is dropped everywhere (`report.py` does this).

Write ALL findings to a fresh dated file. Do **not** compare with earlier days.

## Steps

1. **Get the repo.** Call the add_repo tool (`mcp__claude-code-remote__add_repo`) with owner `lsalat`, repo `claudeai`, access `push`. If that tool is not in your tool list, first load it with ToolSearch, query `select:mcp__claude-code-remote__add_repo`. Clone exactly as add_repo instructs and work in `comics-scout/` on branch `main`.
   Do not use a personal GitHub token or `GH_TOKEN`: Claude's cloud only lets you reach repos attached through add_repo. If add_repo refuses (for example "link your GitHub account"), do not retry; report that GitHub must be reconnected in claude.ai Settings → Connectors.

2. **Search all sites** (takes about 2 minutes – give the command a 10-minute timeout):
   `python3 scout.py --terms search-terms.txt > /tmp/results.json`
   - Sites: Bazoš, Sbazar, KomiksBazar (collector ads + antiquarian offers, which also include many **Aukro** listings), Trh knih, Knihobot, Reknihy, Restorio, Antikavion, Antikvariaty.cz, Arkham.
   - Each site pauses 2–6 s between requests and stops at its first error/block. Exit code 2 means at least one site stopped – check the `status` field per site and report it. Never retry a blocked site.

3. **Publisher shops** – none. mightyboys.cz and comicscentrum.cz are **not** checked (removed from the scout on 2026-11-19).

4. **Build the daily file:**
   `python3 report.py /tmp/results.json history/listings-YYYY-MM-DD.txt` (today's date, Prague time).
   Then open the file and review it:
   - remove anything that is clearly not one of the wanted comics (the script removes known noise, but new noise can appear),
   - remove any excluded Conan volume the script missed (z Cimerie, Král aquilonský, Kapitán pirátů, Mstitel, vol. 2–5),
   - mark suspiciously cheap listings with `CHECK:`.
   If a file for today already exists, overwrite it.

5. **Commit and push** straight to `main`:
   `git add comics-scout && git commit -m "Comics scout: listings YYYY-MM-DD" && git push origin main` (fetch/rebase first if the push is rejected).

6. **Update the Claude page** "Comics scout – latest findings"
   (slug `4debf014-8821-4d59-9a58-2fbf034acd4e`, https://claude.ai/artifact/Ad5jGHU2bTPriSMAjBxNow). Never create a new artifact.
   - Read it with `read_artifact` (gives the HTML and the live version).
   - Replace ONLY the JSON inside `<script id="scout-data" type="application/json"> ... </script>`; keep everything else unchanged.
   - JSON shape: `{"date": "YYYY-MM-DD", "timestamp": "YYYY-MM-DD HH:MM" (Prague time, `TZ=Europe/Prague date '+%Y-%m-%d %H:%M'`), "note": "", "sites_checked": [...], "sites_failed": [...], "items": [{"cat": "Mighty Boys" | "Tales from the Crypt" | "Kolosální Conan" | "Banda" | "Criminal", "title": "short title incl. edition", "price": number in Kč or null, "price_text": "price as shown", "site": "site name", "place": "location or short note", "url": "listing URL"}]}`
   - Include every listing from today's file. Leave `note` empty unless something important needs saying (e.g. a site could not be checked).
   - Publish the full updated HTML with `publish_version` (slug + `base_version` from `read_artifact`; omit title and icon). On a version conflict, read again and retry once.
   - If the scout itself failed, still update the page: keep the old items, set `date` and `timestamp` to now and `note` to a one-line explanation of what failed.
   - **History database:** after publishing, save the run with one `db_write` call (slug `4debf014-8821-4d59-9a58-2fbf034acd4e`): `{"op":"set","path":"runs/YYYY-MM-DD_HH-MM","data":<the same JSON as the scout-data block>}`. Never change or delete older `runs/` documents. Skip it if the scout failed.

7. **Report – in Conan comic style.** Send the report twice: with SendUserMessage (Markdown) and with PushNotification (this one becomes the push banner and the e-mail, so it must be sent every run, inside `<routine_summary>` tags). Same facts in both.
   - **Style:** a short sword-and-sorcery comic issue. Cover headline in capitals with ⚔️ (e.g. `⚔️ COMICS SCOUT – THE HUNT OF 19 NOVEMBER ⚔️`), narrator caption boxes in an old-chronicle voice (in Markdown use `>` blockquotes; in the e-mail use lines framed like `【 … 】`), one "panel" per category with a bold/CAPS heading and a 💰 loot list, sound effects for highlights (`KRAKK!` for a bargain, `TICK-TOCK…` for an auction ending soon, `SKREEE!` for a blocked site), and a closing `NEXT ISSUE: …` line. Write the narration yourself – never quote Robert E. Howard or any comic.
   - **The facts stay exact and complete:** number of listings per category and per site; the most interesting finds – cheapest offer per title, anything clearly below normal price (e.g. Kolosální Conan vol. 1 under ~30 000 Kč, Přístav Země / Zatmění or Trojka near their original price (1 969 Kč / 528 Kč), Banda or Criminal volumes under their shop price), auctions ending soon – with price, site and URL; any site that stopped or could not be checked; links to the new file on GitHub and to the Claude page.
   - The first sentence of the PushNotification is a plain, informative banner (e.g. `⚔️ 18 finds today – Kolosální Conan vol. 1 from 37 000 Kč on Bazoš!`). Keep the e-mail under ~300 words, plain text (no Markdown tables).

## History database
The page's code (Latest run + History tabs) is kept in `page/index.html` in this folder.
Every run is stored as one document `runs/YYYY-MM-DD_HH-MM` in the Claude page's own database (one snapshot of all findings + which sites were checked/failed). The page's **History** tab builds one row per listing from these snapshots: first seen, last seen, price changes, and status – *active*, *gone* (missing although its site was checked successfully; likely sold) or *not checked* (its site failed since). Nothing is ever deleted. The History tab has a **Download CSV** button for backup/Excel. Capacity: ~7 KB per run, 25 000 documents / 100 MB per database – decades of daily runs; the page loads the newest 1 000 runs.

## Supabase + Grafana (long-term history)
After the Claude page and its history are updated, the run uploads the same data to a free Supabase Postgres database with `python3 comics-scout/supabase_push.py <run.json>` (secrets `SUPABASE_URL`, `SUPABASE_SECRET_KEY` from the environment; never print them). Grafana Cloud reads that database (read-only user `grafana_reader`) and shows the dashboard in `grafana/dashboard.json`: price trends per book, offers per run, bargains vs. limits, latest listings and full history, plus a price alert. Supabase keeps all data (no 14-day limit). Setup steps: `grafana/SETUP.md`. A failed upload never stops the run; it is reported as "Supabase not updated – …".

## Price-candle chart
After the Supabase upload the run draws a PNG chart: `python3 chart.py /tmp/comics-scout-chart-YYYY-MM-DD.png --run /tmp/scout-run.json` (needs matplotlib; install once with `pip install --break-system-packages matplotlib` if missing).
- One row per book (grouped by category), price on a log axis.
- **Blue candle = today's run**, **grey candle = all earlier runs together** (each earlier listing counted once per distinct price), red dashed tick = alert limit from `scout_alert_limits`.
- Wick = lowest–highest asking price, body = middle 50 % of listings, white line = median, `n` = number of listings. Listings without a price are left out.
- History comes from Supabase (`SUPABASE_URL`, `SUPABASE_SECRET_KEY`; never printed). If Supabase is unreachable, `--run` draws today's run only.
- Offline test: `python3 chart.py out.png --data data.json` with `{"listings":[{run_ts,url_key,cat,book,site,price}],"limits":{book:max_price}}`.
- The 8 Nov and 17 Nov findings were backfilled into Supabase from `history/` on 2026-11-19 (run note "backfilled from …").

## Daily e-mail
Two e-mails arrive every run:
1. **Gmail with the chart** – sent with the Gmail connector's `send_message` only (never read, search or change mail) from ladislav.salat@gmail.com to **ladislav.salat@seznam.cz**, subject `⚔️ Comics scout – YYYY-MM-DD – N finds`, plain-text body = the same text as the PushNotification, chart PNG attached as `comics-scout-chart-YYYY-MM-DD.png` (attached by file reference `sha256:<hash>:<path>`, not base64). Sent once, never retried; a failure is reported as "Chart e-mail not sent – …". The Gmail connector must be attached to the scheduled task (task settings → connectors).
2. **Claude's own automatic summary e-mail** (from the scheduled task's PushNotification): plain text, one line per book (offers, cheapest price, site, link), sites that could not be checked and a link to the Claude page. It can be switched off in the task's notification settings if the Gmail one is enough.
Details: `claude_scheduler.txt`, steps 4–6.

## Not covered
- **Aukro directly** – Cloudflare blocks cloud requests (partly covered through KomiksBazar).
- **ComicsDB Bazar** – blocks automated access ("Access Forbidden").
- **Facebook Marketplace** – excluded by the user.

## Rules
- Read only: never contact sellers, log in or buy anything.
- Never retry a blocked site.
- Keep this file in sync with the scheduled task's instructions (see `claude_scheduler.txt`).
