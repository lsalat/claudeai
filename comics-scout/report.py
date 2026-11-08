"""Turn scout.py JSON output into the daily findings file.

Usage: python3 report.py results.json history/listings-YYYY-MM-DD.txt
"""
import json, re, sys, datetime
src, dst = sys.argv[1], sys.argv[2]
d = json.load(open(src, encoding="utf-8"))
MB = ["agent strachu","cesta kostí","cesta na mars","dopis 44","jizvy","kletba","matka","osm miliard","ostrov miliardář","ozvěny","pan rosnička","poslední detektiv","pošťák","pouto smrti","přístav země","sara","šestiprsťák","sestiprstak","svědectví","temná věda","trojka","tulák","verdikt davu","vesmír na tripu","vyvrhel","zpěv neznáma","gideon falls","ďábelská komedie","think tank","desátek","mighty boys"]
def cat(title):
    t = title.lower()
    if "kolosáln" in t or "kolosaln" in t: return "conan"
    if "crypt" in t: return "crypt"
    if any(k in t for k in MB): return "mb"
    return None
NOISE = ["hell boys","hot boys","star wars","agent jfk","stmívání","garfield","xb-1","fantasy & science","harley","americký upír","comicsy v angličtině","conan doyl"]
NAMES = {"bazos":"Bazoš","sbazar":"Sbazar","komiksbazar":"KomiksBazar","antikvariaty":"Antikvariaty.cz","arkham":"Arkham (shop)"}
rows = {"conan":{}, "crypt":{}, "mb":{}}; wanted = []; aukro = {"conan":[], "crypt":[], "mb":[]}
for site, v in d.items():
    for term, items in v["results"].items():
        for it in items:
            t = it["title"]; tl = t.lower()
            if any(n in tl for n in NOISE): continue
            c = cat(t)
            if site == "arkham" and c is None: continue
            if c is None: continue
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
 "Sites searched: Bazoš, Sbazar, KomiksBazar (ads + antiquarian offers incl. Aukro), Antikvariaty.cz, Arkham.",
 "Not checked: Aukro directly (Cloudflare), ComicsDB Bazar (blocks automated access), Facebook (excluded).",
 "Search noise removed. Prices as listed; Aukro prices may be current auction bids.", ""]
titles = {"conan":"1) KOLOSÁLNÍ CONAN (Comics Centrum)", "crypt":"2) TALES FROM THE CRYPT", "mb":"3) MIGHTY BOYS"}
for c in ["conan","crypt","mb"]:
    out += ["-"*45, titles[c], "-"*45]
    any_ = False
    for site in ["Bazoš","Sbazar","KomiksBazar","Antikvariaty.cz","Arkham (shop)"]:
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
