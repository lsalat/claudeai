"""Comics scout – search several Czech sites and print all listings as JSON.

Usage:
  python3 scout.py --terms search-terms.txt              # all sites, all terms
  python3 scout.py --terms search-terms.txt --sites bazos,sbazar
  python3 scout.py "kolosální conan" "mighty boys"       # terms on the command line

Sites: bazos, sbazar, komiksbazar (classified ads + antiquarian offers),
antikvariaty, arkham.

Polite by design: each site is searched one term at a time with a random
2–6 s pause between requests; different sites run in parallel. A site stops
at its first error / block / CAPTCHA and is reported as such – it is never
retried. Listings found by several searches are listed once per site.
"""
import html
import json
import random
import re
import subprocess
import sys
import threading
import time
import urllib.parse

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
q = urllib.parse.quote_plus
qp = urllib.parse.quote


def clean(s):
    s = re.sub(r"<script.*?</script>", " ", s or "", flags=re.S)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", s)).split())


def fetch(url):
    r = subprocess.run(["curl", "-sS", "-L", "-m", "30", "-A", UA, "-w", "\n%{http_code}", url],
                       capture_output=True, text=True, errors="replace")
    body, _, code = r.stdout.rpartition("\n")
    # 404 = "nothing found" on some sites (e.g. Sbazar) – treat as an empty result, not a block
    blocked = code not in ("200", "404") or re.search(r"just a moment|cf-chl-|g-recaptcha\"|hcaptcha", body, re.I)
    return (None if blocked else body), (code or r.stderr.strip()[:120])


# ---------- site parsers: each returns a list of {title, price, place, date, url, note} ----------

def bazos(term):
    url = f"https://www.bazos.cz/search.php?hledat={q(term)}&rubriky=www&kitx=ano"
    body, code = fetch(url)
    if body is None:
        return None, code
    out = []
    for blk in body.split('<div class="inzeraty inzeratyflex">')[1:]:
        a = re.search(r'<h2 class="?nadpis"?><a href="([^"]+)">(.*?)</a>', blk, re.S)
        if not a:
            continue
        price = re.search(r'inzeratycena[^>]*>(.*?)</div>', blk, re.S)
        place = re.search(r'inzeratylok[^>]*>(.*?)</div>', blk, re.S)
        date = re.search(r'\[(\d+\.\d+\. \d{4})\]', blk)
        out.append({"title": clean(a.group(2)), "price": clean(price.group(1)) if price else "",
                    "place": re.sub(r"\s*\d{3}\s?\d{2}$", "", clean(place.group(1))) if place else "",
                    "date": date.group(1) if date else "", "url": urllib.parse.urljoin("https://www.bazos.cz", a.group(1))})
    return out, code


def sbazar(term):
    url = f"https://www.sbazar.cz/hledej/{qp(term)}"
    body, code = fetch(url)
    if body is None:
        return None, code
    out = []
    for m in re.finditer(r'<li data-offer-id="(\d+)">(.*?)</li>', body, re.S):
        a = re.search(r'href="(/inzerat/[^"]+)"', m.group(2))
        parts = [p for p in (clean(x) for x in re.split(r"<[^>]+>", m.group(2))) if p]
        if not a or not parts:
            continue
        price = next((p for p in parts if re.search(r"Kč|dohodou|zdarma", p, re.I)), "")
        place = next((p[2:] for p in parts if p.startswith("v ")), "")
        out.append({"title": parts[0], "price": price, "place": place, "date": "",
                    "url": "https://www.sbazar.cz" + a.group(1)})
    return out, code


def komiksbazar(term):
    out = []
    # classified ads from collectors
    body, code = fetch(f"https://www.komiksbazar.cz/inzeraty.aspx?search={q(term)}")
    if body is None:
        return None, code
    for m in re.finditer(r'ctrAdvertisementShort_(\d+)_hypTitle_\d+" class="[^"]*" href="([^"]+)">(.*?)</a>', body, re.S):
        n = m.group(1)
        price = re.search(rf'ctrAdvertisementShort_{n}_litPricePrimary_\d+"[^>]*>(.*?)</', body, re.S)
        typ = re.search(rf'ctrAdvertisementShort_{n}_litType_\d+"[^>]*>(.*?)</', body, re.S)
        out.append({"title": clean(m.group(3)), "price": clean(price.group(1)) if price else "", "place": "",
                    "date": "", "note": "bazar ad" + (f" ({clean(typ.group(1))})" if typ else ""),
                    "url": urllib.parse.urljoin("https://www.komiksbazar.cz/", m.group(2))})
    time.sleep(random.uniform(2, 6))
    # offers from antiquarian bookshops listed on KomiksBazar
    body, code = fetch(f"https://www.komiksbazar.cz/antikvariaty-vyhledavani.aspx?search={q(term)}")
    if body is None:
        return None, code
    for m in re.finditer(r'ctrAntiquesSearchShort_(\d+)_hypName_\d+" class="[^"]*" href="([^"]+)"[^>]*>(.*?)</a>', body, re.S):
        n = m.group(1)
        price = re.search(rf'ctrAntiquesSearchShort_{n}_labPrice1_\d+"[^>]*>(.*?)</', body, re.S)
        source = urllib.parse.urlparse(m.group(2)).netloc.replace("www.", "")
        note = "via Aukro (listed on KomiksBazar)" if "aukro" in source else f"antiquarian shop {source}"
        out.append({"title": re.sub(r"^\d+\.\s*", "", clean(m.group(3))), "price": clean(price.group(1)) if price else "",
                    "place": "", "date": "", "note": note, "url": m.group(2)})
    return out, code


def antikvariaty(term):
    url = ("https://www.antikvariaty.cz/index.php?action=ListBooks&display=search&search=fulltext"
           f"&fulltxt={q(term)}&rows=50&curr=1")
    body, code = fetch(url)
    if body is None:
        return None, code
    out = []
    for blk in re.split(r'<div zarazena="', body)[1:]:
        added = blk[:10]
        t = re.search(r'<h2 class="nazev">\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', blk, re.S)
        price = re.search(r'<strong class="cena">(.*?)</strong>', blk, re.S)
        shop = re.search(r'prodejna:\s*([^<\-]+)', blk)
        if not t:
            continue
        out.append({"title": clean(t.group(2)), "price": clean(price.group(1)).replace("Cena:", "").strip() if price else "",
                    "place": ("shop: " + shop.group(1).strip()) if shop else "", "date": added,
                    "url": urllib.parse.urljoin("https://www.antikvariaty.cz/", html.unescape(t.group(1)))})
    return out, code


def arkham(term):
    url = f"https://www.arkham.cz/vyhledavani/?string={q(term)}"
    body, code = fetch(url)
    if body is None:
        return None, code
    out = []
    for blk in body.split('<div class="product">')[1:]:
        a = re.search(r'<a href="([^"]+)" class="name"', blk)
        name = re.search(r'data-micro="name"[^>]*>(.*?)</span>', blk, re.S)
        price = re.search(r'productCardPrice"[^>]*>(.*?)</div>', blk, re.S)
        avail = re.search(r'<div class="availability">(.*?)</div>', blk, re.S)
        if not (a and name):
            continue
        out.append({"title": clean(name.group(1)), "price": clean(price.group(1)) if price else "",
                    "place": "", "date": "", "note": clean(avail.group(1)) if avail else "",
                    "url": urllib.parse.urljoin("https://www.arkham.cz", a.group(1))})
    return out, code


def trhknih(term):
    """Trh knih – one entry per book with the lowest current price; books without offers are skipped."""
    url = f"https://www.trhknih.cz/hledat?q={q(term)}"
    body, code = fetch(url)
    if body is None:
        return None, code
    out = []
    for blk in body.split('<div class="row serp-item">')[1:]:
        p = re.search(r'<div class="span6">\s*<p>(.*?)</p>', blk, re.S)
        a = re.search(r'<a href="(/kniha/[^"]+)">(.*?)</a>', blk, re.S)
        price = re.search(r'ask-count[^>]*>(.*?)</span>', blk, re.S)
        if not (p and a and price):
            continue
        lines = [clean(x) for x in re.split(r"<br\s*/?>", p.group(1))]
        title = " – ".join(x for x in lines[:2] if x and "Kč" not in x)
        year = re.search(r"<em>(\d{4})</em>", blk)
        out.append({"title": title, "price": "from " + clean(price.group(1)), "place": "",
                    "date": year.group(1) if year else "", "note": "lowest offer",
                    "url": "https://www.trhknih.cz" + a.group(1)})
    return out, code


RESTORIO_HASHID = "e08b0ecc3b5a2e10a31665511853935a"  # Restorio's public Doofinder search ID (from its website)


def restorio(term):
    """Restorio – second-hand bookshop; its search runs through Doofinder's JSON API."""
    url = f"https://eu1-search.doofinder.com/6/{RESTORIO_HASHID}/_search?query={q(term)}&rpp=50"
    r = subprocess.run(["curl", "-sS", "-m", "30", "-A", UA, "-H", "Origin: https://www.restorio.cz",
                        "-w", "\n%{http_code}", url], capture_output=True, text=True, errors="replace")
    body, _, code = r.stdout.rpartition("\n")
    if code != "200":
        return None, code or r.stderr.strip()[:120]
    out = []
    for it in json.loads(body).get("results", []):
        price = it.get("best_price") or it.get("price")
        if not price or it.get("fskladem") == "ne":  # catalogue entry without a copy for sale
            continue
        out.append({"title": clean(it.get("title", "")), "price": f"{price:.0f} Kč",
                    "place": "", "date": str(it.get("doo_rok") or ""), "note": "in stock",
                    "url": it.get("link", "")})
    return out, code


SITES = {"trhknih": trhknih, "restorio": restorio, "bazos": bazos, "sbazar": sbazar, "komiksbazar": komiksbazar,
         "antikvariaty": antikvariaty, "arkham": arkham}


def run_site(name, terms, results):
    seen, data, status = set(), {}, "ok"
    for i, term in enumerate(terms):
        if i:
            time.sleep(random.uniform(2, 6))
        try:
            items, code = SITES[name](term)
        except Exception as e:  # parser problem – report, don't crash the other sites
            items, code = None, f"error: {e}"
        if items is None:
            status = f"stopped at '{term}': {code}"
            break
        new = [it for it in items if it["url"] not in seen]
        seen.update(it["url"] for it in new)
        if new:
            data[term] = new
    results[name] = {"status": status, "count": len(seen), "results": data}


def main():
    args, sites = sys.argv[1:], list(SITES)
    if "--sites" in args:
        i = args.index("--sites")
        sites = [s.strip() for s in args[i + 1].split(",")]
        del args[i:i + 2]
    if len(args) >= 2 and args[0] == "--terms":
        with open(args[1], encoding="utf-8") as f:
            terms = [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]
    else:
        terms = args
    if not terms:
        sys.exit(__doc__)
    results, threads = {}, []
    for s in sites:
        t = threading.Thread(target=run_site, args=(s, terms, results))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    print(json.dumps({s: results[s] for s in sites}, ensure_ascii=False, indent=1))
    sys.exit(0 if all(r["status"] == "ok" for r in results.values()) else 2)


if __name__ == "__main__":
    main()
