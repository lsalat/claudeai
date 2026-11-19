"""Turn scout.py JSON output into the daily findings file.

Usage: python3 report.py results.json history/listings-YYYY-MM-DD.txt
"""
import json, re, sys, datetime
src, dst = sys.argv[1], sys.argv[2]
d = json.load(open(src, encoding="utf-8"))
def has(t, *words):
    return any(w in t for w in words)

def cat(title, site="", url=""):
    t = title.lower()
    # Mighty Boys books carry ISBNs starting 978-80-907931 (seen in shop URLs)
    if "978809079" in url and has(t, "přístav", "pristav", "zatmění", "zatmeni", "trojka"): return "mb"
    if "trojka" in t and "gillen" in t: return "mb"   # Trojka by Kieron Gillen = the Mighty Boys book
    if has(t, "kolosáln", "kolosaln"): return "conan"
    # Banda = Czech edition of The Boys (Garth Ennis, Crew); "banda" alone is a common word
    if "banda" in t and not has(t, "muertova", "ztracená banda", "banda lvů") and (
        has(t, "the boys", "theboys", "ennis", "karty jsou rozdan", "komiks", "crew")
        or (site == "arkham" and re.match(r"banda\b", t))):
        return "banda"
    # Criminal by Ed Brubaker & Sean Phillips – Czech edition only, and the title must also name the authors or say it is a comic
    # Book catalogues (searched by author too) often list it without the author, e.g. "Criminal – deluxe edice"
    BOOKSHOPS = ("trhknih", "knihobot", "reknihy", "restorio", "antikavion", "antikvariaty", "arkham")
    if (has(t, "criminal", "kriminál", "kriminal") and has(t, "brubaker", "phillips", "komiks", "comics", "comic")
            or (site in BOOKSHOPS and re.match(r"criminal\b", t))) \
            and not has(t, "volume", "vol.", "deluxe edition", "coward", "lawless", "the dead and the dying", "bad night",
                        "the sinners", "last of the innocent", "wrong place", "bad weekend", "cruel summer", "image comics",
                        "marvel", "icon", "english", "anglick", "my heroes", "kriminální", "kriminalni", "kriminalist"):
        return "criminal"
    if has(t, "tales from the crypt", "crypt-keeper", "crypt keeper", "příběhy z krypty"): return "crypt"
    # Mighty Boys – only Přístav Země / Zatmění and Trojka
    if has(t, "přístav země", "pristav zeme"): return "mb"
    if has(t, "zatmění", "zatmeni") and has(t, "kaplan", "mighty", "přístav", "pristav"): return "mb"
    if "trojka" in t and (has(t, "mighty", "komiks", "sběratel", "sberatel") or (site == "arkham" and t.strip() == "trojka")):
        return "mb"
    return None
import unicodedata
def _plain(t):
    return "".join(ch for ch in unicodedata.normalize("NFKD", t.lower()) if not unicodedata.combining(ch))
# Kolosální Conan volumes the user does not want: 2 = z Cimerie, 3 = Král aquilonský, 4 = Kapitán pirátů, 5 = Mstitel.
# Keep vol. 1, newer volumes and mixed bundle ads.
def excluded_conan(title):
    t = _plain(title)
    if any(w in t for w in ("lovci monster", "temny elf", "komiksy")):  # mixed bundle ads stay
        return False
    if any(w in t for w in ("cimer", "cimmer", "aquilon", "pirat", "mstitel")):
        return True
    return bool(re.search(r"kolosalni\s+conan\s*(?:c\.|vol\.?|kniha)?\s*[2-5]\b", t))
SOLD_OUT = re.compile(r"vyprod|nedostupn|není skladem|neni skladem|sold out|out of stock", re.I)
NOISE = ["hell boys","hot boys","star wars","agent jfk","stmívání","garfield","xb-1","fantasy & science","harley","americký upír","comicsy v angličtině","conan doyl","pobřežní piráti","na stopě","crypto"]
NAMES = {"trhknih":"Trh knih","knihobot":"Knihobot","reknihy":"Reknihy","restorio":"Restorio","antikavion":"Antikavion","bazos":"Bazoš","sbazar":"Sbazar","komiksbazar":"KomiksBazar","antikvariaty":"Antikvariaty.cz","arkham":"Arkham (shop)"}
rows = {"conan":{}, "crypt":{}, "mb":{}, "banda":{}, "criminal":{}}; wanted = []; aukro = {"conan":[], "crypt":[], "mb":[], "banda":[], "criminal":[]}
for site, v in d.items():
    for term, items in v["results"].items():
        for it in items:
            t = it["title"]; tl = t.lower()
            if any(n in tl for n in NOISE): continue
            c = cat(t, site, it.get("url",""))
            if site == "arkham" and c is None: continue
            if c is None: continue
            # Out of scope: sold-out / unavailable shop items ("Vyprodáno", "Momentálně nedostupné", "Není skladem", "sold out")
            if SOLD_OUT.search(" ".join(str(it.get(k,"")) for k in ("title","price","place","note","date"))): continue
            if c == "conan" and excluded_conan(t): continue
            if "Poptávka" in it.get("note","") or tl.startswith(("koupím","koupim","sháním","hledám")):
                wanted.append((NAMES[site], it)); continue
            if "via Aukro" in it.get("note",""):
                aukro[c].append(it); continue
            rows[c].setdefault(NAMES[site], []).append(it)
def line(it, site=None):
    extra = " | ".join(x for x in [it.get("place",""), it.get("date",""), it.get("note","") if "bazar ad" not in it.get("note","") else ""] if x)
    return f"  {it['title'][:58]:<58} | {it['price']:<12} | {extra:<28} | {it['url']}"
today = re.search(r"(\d{4}-\d{2}-\d{2})", dst).group(1)
out = [f"COMICS SCOUT – ALL FINDINGS – {today}", "="*45,
 "Sites searched: Bazoš, Sbazar, KomiksBazar (ads + antiquarian offers incl. Aukro), Trh knih, Knihobot, Reknihy, Restorio, Antikavion, Antikvariaty.cz, Arkham.",
 "Not checked: Aukro directly (Cloudflare), ComicsDB Bazar (blocks bots), Facebook (excluded).",
 "Search noise removed. Prices as listed; Aukro prices may be current auction bids.", ""]
titles = {"conan":"1) KOLOSÁLNÍ CONAN (Comics Centrum)", "crypt":"2) TALES FROM THE CRYPT", "mb":"3) MIGHTY BOYS (Přístav Země / Zatmění, Trojka)", "banda":"4) BANDA (The Boys, Garth Ennis – Czech edition)", "criminal":"5) CRIMINAL (Ed Brubaker & Sean Phillips – Czech edition)"}
for c in ["conan","crypt","mb","banda","criminal"]:
    out += ["-"*45, titles[c], "-"*45]
    any_ = False
    for site in ["Bazoš","Sbazar","KomiksBazar","Trh knih","Knihobot","Reknihy","Restorio","Antikavion","Antikvariaty.cz","Arkham (shop)"]:
        items = rows[c].get(site, [])
        if not items: continue
        any_ = True
        items = sorted(items, key=lambda i: int(re.sub(r"\D","",i["price"]) or 10**9))
        out.append(f"{site} ({len(items)})")
        out += [line(i) for i in items]; out.append("")
    if aukro[c]:
        any_ = True
        items = sorted(aukro[c], key=lambda i: int(re.sub(r"\D","",i["price"]) or 10**9))
        out.append(f"Aukro – found via KomiksBazar ({len(items)})")
        out += [line({**i, "note": ""}) for i in items]; out.append("")
    if not any_: out += ["  Nothing found on any site.", ""]
if wanted:
    out += ["-"*45, "WANTED ADS (people looking to BUY these – possible buyers if you sell)", "-"*45]
    out += [f"  [{s}] {i['title'][:60]} | {i['url']}" for s,i in wanted]
open(dst, "w", encoding="utf-8").write("\n".join(out) + "\n")
print(f"wrote {dst}: " + ", ".join(f"{titles[c].split(' ',1)[1].split(' (')[0]}: {sum(len(v) for v in rows[c].values()) + len(aukro[c])}" for c in rows) + f", wanted ads: {len(wanted)}")
