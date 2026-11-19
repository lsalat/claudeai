#!/usr/bin/env python3
"""
Upload one comics-scout run to Supabase (long-term history for Grafana).

Usage:
  python3 supabase_push.py run.json            # upload (needs SUPABASE_URL + SUPABASE_SECRET_KEY)
  python3 supabase_push.py run.json --dry-run  # show what would be uploaded
  python3 supabase_push.py run.json --sql      # print INSERT statements (for seeding in the SQL editor)

run.json = the same JSON object the run puts in the Claude page's scout-data block:
  {"date","timestamp":"YYYY-MM-DD HH:MM" (Prague time),"note","sites_checked","sites_failed","items":[...]}

Only the Python standard library is used. Exit code 0 = uploaded, 2 = config missing, 1 = upload failed.
"""
import json, os, re, sys, unicodedata, urllib.request, urllib.error
from datetime import datetime
from zoneinfo import ZoneInfo

SOLD_OUT = re.compile(r"vyprod|nedostupn|není skladem|neni skladem|sold out|out of stock", re.I)


def plain(t):
    return "".join(c for c in unicodedata.normalize("NFKD", str(t or "").lower()) if not unicodedata.combining(c))


def url_key(u):
    """Same normalisation as the Claude page: host without www + path without trailing slash + query, lower case."""
    m = re.match(r"^[a-z]+://([^/?#]+)([^?#]*)(\?[^#]*)?", str(u or "").strip(), re.I)
    if not m:
        return str(u or "").lower()
    host = m.group(1).lower()
    host = host[4:] if host.startswith("www.") else host
    return (host + m.group(2).rstrip("/") + (m.group(3) or "")).lower()


def book(cat, title):
    """One clean book name per listing – used for grouping in Grafana."""
    t = plain(title)
    if cat == "Criminal":
        if "kazdy je zlocinec" in t or re.search(r"criminal\s*1\b", t):
            return "Criminal 1: Každý je zločinec"
        if "nocni rozhodnuti" in t or re.search(r"criminal\s*[-–:]?\s*3\b", t):
            return "Criminal 3: Noční rozhodnutí"
        if "posledni z nevinnych" in t:
            return "Criminal: Poslední z nevinných"
        if re.search(r"deluxe edice\s*[-–]?\s*2|deluxe edice 2|edice - 2", t):
            return "Criminal – deluxe edice 2"
        if "deluxe" in t:
            return "Criminal – deluxe edice 1"
        return "Criminal – other / volume not stated"
    if cat == "Banda":
        if any(w in t for w in ("druha", "nakladacka")) or re.search(r"banda\D{0,12}2\b", t):
            return "Banda 2: Nakládačka"
        if any(w in t for w in ("prvni", "karty jsou rozdany")) or re.search(r"banda\D{0,12}1\b", t):
            return "Banda 1: Karty jsou rozdaný"
        m = re.search(r"banda\D{0,12}(\d+)\b", t)
        return f"Banda {m.group(1)}" if m else "Banda – other"
    if cat == "Kolosální Conan":
        if any(w in t for w in ("lovci", "temny elf", "komiksy", "bundle", "atd")):
            return "Kolosální Conan – bundle ads"
        m = re.search(r"kolosalni conan\s*(\d+)", t)
        if m and int(m.group(1)) >= 6:
            return f"Kolosální Conan vol. {m.group(1)}"
        return "Kolosální Conan vol. 1"
    if cat == "Mighty Boys":
        se = bool(re.search(r"sberatel|limit|\bse\b", t))
        if "agent strachu" in t:
            return "Agent strachu + Přístav Země (CHECK)"
        if "trojka" in t:
            return "Trojka – collector's" if se else "Trojka – normal / not stated"
        return "Přístav Země / Zatmění – collector's" if se else "Přístav Země / Zatmění – normal / not stated"
    if cat == "Tales from the Crypt":
        return "Tales from the Crypt"
    return "Other"


def rows_from(run):
    ts = datetime.strptime(run["timestamp"], "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo("Europe/Prague")).isoformat()
    seen, listings = set(), []
    for i in run.get("items") or []:
        if not i or not i.get("url"):
            continue
        if SOLD_OUT.search(" ".join(str(i.get(k) or "") for k in ("title", "price_text", "place"))):
            continue
        k = url_key(i["url"])
        if k in seen:
            continue
        seen.add(k)
        price = i.get("price")
        listings.append({
            "run_ts": ts, "url_key": k, "url": i["url"], "cat": i.get("cat"), "book": book(i.get("cat"), i.get("title")),
            "title": i.get("title"), "site": i.get("site"), "place": i.get("place") or "",
            "price": price if isinstance(price, (int, float)) else None, "price_text": i.get("price_text") or "",
        })
    run_row = {"run_ts": ts, "run_date": run.get("date") or run["timestamp"][:10], "note": run.get("note") or "",
               "sites_checked": run.get("sites_checked") or [], "sites_failed": run.get("sites_failed") or [],
               "item_count": len(listings)}
    return run_row, listings


def sql_literal(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, list):
        return "array[" + ",".join(sql_literal(x) for x in v) + "]::text[]" if v else "'{}'::text[]"
    return "'" + str(v).replace("'", "''") + "'"


def to_sql(run_row, listings):
    out = ["-- seed: run " + run_row["run_ts"]]
    cols = list(run_row)
    out.append(f"insert into public.scout_runs ({','.join(cols)}) values ({','.join(sql_literal(run_row[c]) for c in cols)}) on conflict (run_ts) do nothing;")
    if listings:
        cols = list(listings[0])
        vals = ",\n".join("(" + ",".join(sql_literal(r[c]) for c in cols) + ")" for r in listings)
        out.append(f"insert into public.scout_listings ({','.join(cols)}) values\n{vals}\non conflict (run_ts, url_key) do nothing;")
    return "\n".join(out)


def post(base, key, table, payload, conflict):
    url = f"{base.rstrip('/')}/rest/v1/{table}?on_conflict={conflict}"
    headers = {"apikey": key, "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates,return=minimal"}
    if key.startswith("eyJ"):  # legacy service_role JWT
        headers["Authorization"] = "Bearer " + key
    req = urllib.request.Request(url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    run = json.load(open(sys.argv[1], encoding="utf-8"))
    run_row, listings = rows_from(run)
    if "--sql" in sys.argv:
        print(to_sql(run_row, listings)); return
    if "--dry-run" in sys.argv:
        print(json.dumps({"run": run_row, "listings": listings}, ensure_ascii=False, indent=1))
        print(f"\n{len(listings)} listings, books: {sorted({l['book'] for l in listings})}", file=sys.stderr); return
    base, key = os.environ.get("SUPABASE_URL", ""), os.environ.get("SUPABASE_SECRET_KEY", "")
    if not base or not key:
        print("Supabase not updated – SUPABASE_URL / SUPABASE_SECRET_KEY not set in the environment."); sys.exit(2)
    try:
        post(base, key, "scout_runs", [run_row], "run_ts")
        if listings:
            post(base, key, "scout_listings", listings, "run_ts,url_key")
    except urllib.error.HTTPError as e:
        print(f"Supabase not updated – HTTP {e.code}: {e.read()[:300].decode('utf-8', 'replace')}"); sys.exit(1)
    except Exception as e:
        print(f"Supabase not updated – {type(e).__name__}: {e}"); sys.exit(1)
    print(f"Supabase updated – run {run_row['run_ts']}, {len(listings)} listings.")


if __name__ == "__main__":
    main()
