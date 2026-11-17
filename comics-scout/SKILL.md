# Comics scout – daily procedure

Instructions for the scheduled Claude task. Everything runs in the cloud; never use a browser or the user's computer.

## Goal
Find every current listing for:
1. **Mighty Boys** – only **Přístav Země / Zatmění** (one book by Zack Kaplan) and **Trojka**, both normal and collector's (sběratelská) edition
2. **Tales from the Crypt** comics (any edition)
3. **Kolosální Conan** (Comics Centrum: vol. 1, z Cimerie, Král aquilonský, Kapitán pirátů, Mstitel, any newer volume)

Write ALL findings to a fresh dated file. Do **not** compare with earlier days.

## Steps

1. **Get the repo.** Attach `lsalat/claudeai` with push access (add_repo), clone it, and work in `comics-scout/` on branch `main`.

2. **Search all sites** (takes about 2 minutes – give the command a 10-minute timeout):
   `python3 scout.py --terms search-terms.txt > /tmp/results.json`
   - Sites: Bazoš, Sbazar, KomiksBazar (collector ads + antiquarian offers, which also include many **Aukro** listings), Trh knih, Knihobot, Reknihy, Restorio, Antikavion, Antikvariaty.cz, Arkham.
   - Each site pauses 2–6 s between requests and stops at its first error/block. Exit code 2 means at least one site stopped – check the `status` field per site and report it. Never retry a blocked site.

3. **Publisher shops** (WebFetch):
   - https://www.mightyboys.cz/ – only whether **Přístav Země / Zatmění** or **Trojka** is available again (reprint, new edition, last copies). Ignore other titles.
   - https://www.comicscentrum.cz/e-shop/kolosalni-knihy – price and availability of each Kolosální Conan volume; note any new volume.

4. **Build the daily file:**
   `python3 report.py /tmp/results.json history/listings-YYYY-MM-DD.txt` (today's date, Prague time).
   Then open the file and review it:
   - remove anything that is clearly not one of the wanted comics (the script removes known noise, but new noise can appear),
   - add a section "PUBLISHER SHOPS" with the findings from step 3,
   - mark suspiciously cheap listings with `CHECK:`.
   If a file for today already exists, overwrite it.

5. **Commit and push** straight to `main`:
   `git add comics-scout && git commit -m "Comics scout: listings YYYY-MM-DD" && git push origin main` (fetch/rebase first if the push is rejected).

6. **Update the Claude page** "Comics scout – latest findings"
   (slug `4debf014-8821-4d59-9a58-2fbf034acd4e`, https://claude.ai/artifact/Ad5jGHU2bTPriSMAjBxNow). Never create a new artifact.
   - Read it with `read_artifact` (gives the HTML and the live version).
   - Replace ONLY the JSON inside `<script id="scout-data" type="application/json"> ... </script>`; keep everything else unchanged.
   - JSON shape: `{"date": "YYYY-MM-DD", "note": "", "sites_checked": [...], "sites_failed": [...], "items": [{"cat": "Mighty Boys" | "Tales from the Crypt" | "Kolosální Conan", "title": "short title incl. edition", "price": number in Kč or null, "price_text": "price as shown", "site": "site name", "place": "location or short note", "url": "listing URL"}]}`
   - Include every listing from today's file, plus publisher-shop items (site = shop name, place = stock status). Leave `note` empty unless something important needs saying (e.g. a site could not be checked).
   - Publish the full updated HTML with `publish_version` (slug + `base_version` from `read_artifact`; omit title and icon). On a version conflict, read again and retry once.
   - If the scout itself failed, still update the page: keep the old items, set `date` to today and `note` to a one-line explanation of what failed.

7. **Report** with SendUserMessage (short):
   - number of listings per category and per site
   - the most interesting finds: cheapest offer per title, anything clearly below normal price (e.g. Král aquilonský under 3 200 Kč, Kolosální Conan vol. 1 under ~30 000 Kč, Přístav Země / Zatmění or Trojka near their original price (1 969 Kč / 528 Kč)), auctions ending soon
   - publisher news (new titles, stock changes)
   - any site that stopped or could not be checked
   - link to the new file on GitHub and to the Claude page

## Not covered
- **Aukro directly** – Cloudflare blocks cloud requests (partly covered through KomiksBazar).
- **ComicsDB Bazar** – blocks automated access ("Access Forbidden").
- **Facebook Marketplace** – excluded by the user.

## Rules
- Read only: never contact sellers, log in or buy anything.
- Never retry a blocked site.
- Keep this file in sync with the scheduled task's instructions (see `claude_scheduler.txt`).
