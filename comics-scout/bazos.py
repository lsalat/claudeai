"""Search Bazoš.cz for comics and print the listings as JSON.

Usage:
  python3 bazos.py --terms search-terms.txt        # all terms from the file
  python3 bazos.py "kolosální conan" "mighty boys"  # terms on the command line

Polite by design: one request per search term, a random 2–6 s pause between
requests, and it stops at the first error or CAPTCHA (exit code 2).
Listings found by several searches are listed once.
"""
import html
import json
import random
import re
import subprocess
import sys
import time
import urllib.parse

BASE = "https://www.bazos.cz"


def load_terms(argv):
    if len(argv) >= 2 and argv[0] == "--terms":
        with open(argv[1], encoding="utf-8") as f:
            return [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]
    return argv


def clean(s):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", s or "")).split())


def fetch(term):
    url = f"{BASE}/search.php?hledat={urllib.parse.quote_plus(term)}&rubriky=www&kitx=ano"
    r = subprocess.run(
        ["curl", "-sS", "-m", "25", "-A", "Mozilla/5.0", "-w", "\n%{http_code}", url],
        capture_output=True, text=True,
    )
    body, _, code = r.stdout.rpartition("\n")
    return code, body, r.stderr.strip()


def parse(body):
    items = []
    for blk in body.split('<div class="inzeraty inzeratyflex">')[1:]:
        a = re.search(r'<h2 class="?nadpis"?><a href="([^"]+)">(.*?)</a>', blk, re.S)
        if not a:
            continue
        price = re.search(r'inzeratycena[^>]*>(.*?)</div>', blk, re.S)
        place = re.search(r'inzeratylok[^>]*>(.*?)</div>', blk, re.S)
        date = re.search(r'\[(\d+\.\d+\. \d{4})\]', blk)
        items.append({
            "title": clean(a.group(2)),
            "price": clean(price.group(1)) if price else "",
            "place": re.sub(r"\s*\d{3}\s?\d{2}$", "", clean(place.group(1))) if place else "",
            "date": date.group(1) if date else "",
            "url": urllib.parse.urljoin(BASE, a.group(1)),
        })
    return items


def main():
    terms = load_terms(sys.argv[1:])
    if not terms:
        sys.exit(__doc__)
    results, seen, status = {}, set(), "ok"
    for i, term in enumerate(terms):
        if i:
            time.sleep(random.uniform(2, 6))
        code, body, err = fetch(term)
        if code != "200" or re.search(r"captcha", body, re.I):
            status = f"stopped at '{term}': HTTP {code or err}"
            break
        new = [it for it in parse(body) if it["url"] not in seen]
        seen.update(it["url"] for it in new)
        results[term] = new
    print(json.dumps({"status": status, "results": results}, ensure_ascii=False, indent=1))
    sys.exit(0 if status == "ok" else 2)


if __name__ == "__main__":
    main()
