# Comics scout – daily procedure

Instructions for the scheduled Claude task. Everything runs in the cloud; never use a browser or the user's computer.

## Goal
Find every current listing for:
1. **Mighty Boys** comics (all titles, běžná + sběratelská verze)
2. **Tales from the Crypt** comics (any edition)
3. **Kolosální Conan** (Comics Centrum: vol. 1, z Cimerie, Král aquilonský, Kapitán pirátů, Mstitel, any newer volume)

Write ALL findings to a fresh dated file. Do **not** compare with earlier days.

## Steps

1. **Get the repo.** Attach `lsalat/claudeai` with push access (add_repo), clone it, and work in `comics-scout/` on branch `main`.

2. **Search all sites** (takes about 8 minutes – give the command a 15-minute timeout):
   `python3 scout.py --terms search-terms.txt > /tmp/results.json`
   - Sites: Bazoš, Sbazar, KomiksBazar (collector ads + antiquarian offers, which also include many **Aukro** listings), Antikvariaty.cz, Arkham.
   - Each site pauses 2–6 s between requests and stops at its first error/block. Exit code 2 means at least one site stopped – check the `status` field per site and report it. Never retry a blocked site.

3. **Publisher shops** (WebFetch):
   - https://www.mightyboys.cz/ – new titles, prices, pre-orders, "poslední kusy". If there is a new title, add a line `<title> mighty boys` to `search-terms.txt` (it is used from the next run).
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

6. **Report** with SendUserMessage (short):
   - number of listings per category and per site
   - the most interesting finds: cheapest offer per title, anything clearly below normal price (e.g. Král aquilonský under 3 200 Kč, Kolosální Conan vol. 1 under ~30 000 Kč, sold-out Mighty Boys titles near their original price), auctions ending soon
   - publisher news (new titles, stock changes)
   - any site that stopped or could not be checked
   - link to the new file on GitHub

## Not covered
- **Aukro directly** – Cloudflare blocks cloud requests (partly covered through KomiksBazar).
- **ComicsDB Bazar** – blocks automated access ("Access Forbidden").
- **Facebook Marketplace** – excluded by the user.

## Rules
- Read only: never contact sellers, log in or buy anything.
- Never retry a blocked site.
