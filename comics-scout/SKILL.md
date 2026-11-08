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

2. **Bazoš.** Run `python3 bazos.py --terms search-terms.txt > /tmp/bazos.json`.
   - The script is polite (2–6 s pauses) and exits with code 2 at the first error or CAPTCHA. If that happens, do not retry – report it.

3. **Publisher shops** (WebFetch):
   - https://www.mightyboys.cz/ – titles, prices, pre-orders, "poslední kusy", sold out. If there is a new title, add `<title> mighty boys` to `search-terms.txt`.
   - https://www.comicscentrum.cz/e-shop/kolosalni-knihy – open each Kolosální Conan product page for price and availability; note any new volume.

4. **Aukro** – not automated (Cloudflare). Write one line: "Aukro: not checked (pending setup)".

5. **Filter.** Drop listings that are clearly not the wanted comics (e.g. search noise, unrelated items, non-comic Tales from the Crypt items). Keep "wanted"/"koupím" ads only in a separate note. Flag suspiciously cheap listings with `CHECK:`.

6. **Write the file** `history/listings-YYYY-MM-DD.txt` (today's date, Prague time). Use the same layout as earlier files: a header with date and sources, then sections 1) KOLOSÁLNÍ CONAN, 2) TALES FROM THE CRYPT, 3) MIGHTY BOYS, each split into "Publisher shop", "Bazoš", "Aukro". One line per listing: title | price | place | date | URL. If the file already exists for today, overwrite it.

7. **Commit and push** straight to `main`: `git add comics-scout && git commit -m "Comics scout: listings YYYY-MM-DD" && git push origin main`. Fetch/rebase first if the push is rejected.

8. **Report** with SendUserMessage (short):
   - number of listings per category
   - the most interesting finds (cheapest per title, anything clearly below normal price, e.g. Král aquilonský under 3 200 Kč, Kolosální Conan vol. 1 under ~30 000 Kč, sold-out Mighty Boys titles near original price)
   - publisher news (new titles, stock changes)
   - anything that could not be checked
   - link to the new file on GitHub

## Rules
- Read only: never contact sellers, log in or buy anything.
- Never retry a blocked site.
