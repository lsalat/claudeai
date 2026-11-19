#!/usr/bin/env python3
"""
Price-candle chart for the comics scout (PNG, for the daily e-mail).

One row per book, price on a log axis. Each row has:
  - a BLUE candle for the latest run (wick = lowest–highest asking price,
    body = middle 50 % of listings, white line = median, n = listings),
  - a GREY candle for ALL earlier runs together (same meaning, past prices;
    each listing counted once per distinct price),
  - a red dashed tick at the book's alert limit (scout_alert_limits).

Data comes from Supabase (tables scout_listings + scout_alert_limits), which
supabase_push.py fills every run – so run this AFTER supabase_push.py.

Usage:
  python3 chart.py out.png                       # read Supabase (SUPABASE_URL + SUPABASE_SECRET_KEY)
  python3 chart.py out.png --run run.json        # fallback: latest run from the scout-data JSON
                                                 #   (used if Supabase is not reachable; no grey history then)
  python3 chart.py out.png --data data.json      # offline/test: {"listings":[{run_ts,cat,book,site,price}],
                                                 #   "limits":{book:max_price}}
Exit code 0 = chart written, 1 = no data. Prints one line: "Chart ready – …" or "Chart not made – …".
Never prints secrets.
"""
import json, os, sys, urllib.request
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CAT_ORDER = ["Kolosální Conan", "Mighty Boys", "Banda", "Criminal", "Tales from the Crypt"]
BLUE, GREY, RED = "#2a78d6", "#b4b2a9", "#e34948"
INK, SEC, MUT, GRID = "#0b0b0b", "#52514e", "#898781", "#e1e0d9"


def sb_get(base, key, path):
    headers = {"apikey": key, "Accept": "application/json"}
    if key.startswith("eyJ"):
        headers["Authorization"] = "Bearer " + key
    out, start, step = [], 0, 1000
    while True:
        h = dict(headers, Range=f"{start}-{start + step - 1}")
        req = urllib.request.Request(f"{base.rstrip('/')}/rest/v1/{path}", headers=h)
        with urllib.request.urlopen(req, timeout=60) as r:
            page = json.load(r)
        out += page
        if len(page) < step:
            return out
        start += step


def load_supabase():
    base, key = os.environ.get("SUPABASE_URL", ""), os.environ.get("SUPABASE_SECRET_KEY", "")
    if not base or not key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SECRET_KEY not set")
    listings = sb_get(base, key, "scout_listings?select=run_ts,url_key,cat,book,site,price&order=run_ts")
    limits = {r["book"]: r["max_price"] for r in sb_get(base, key, "scout_alert_limits?select=book,max_price")}
    return listings, limits


def load_run(path):
    from supabase_push import rows_from
    run = json.load(open(path, encoding="utf-8"))
    run_row, listings = rows_from(run)
    return listings, {}


def q(vals, t):
    s = sorted(vals)
    i = (len(s) - 1) * t
    lo, hi = int(i), min(int(i) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (i - lo)


def fmt(v):
    return f"{round(v):,}".replace(",", " ") + " Kč"


def build(listings, limits, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FixedLocator, NullLocator, FuncFormatter

    rows = [l for l in listings if l.get("price") not in (None, "") and l.get("book")]
    if not rows:
        return None
    for l in rows:
        l["price"] = float(l["price"])
    runs = sorted({str(l["run_ts"]) for l in rows})
    latest = runs[-1]
    cur, past, cat_of, seen = defaultdict(list), defaultdict(list), {}, set()
    for l in rows:
        cat_of[l["book"]] = l.get("cat") or "Other"
        if str(l["run_ts"]) == latest:
            cur[l["book"]].append(l["price"])
            continue
        # earlier runs: count each listing once per distinct price, so an ad seen on many days is not over-weighted
        k = (l.get("url_key") or id(l), l["price"])
        if k not in seen:
            seen.add(k)
            past[l["book"]].append(l["price"])
    books = sorted(set(cur) | set(past),
                   key=lambda b: (CAT_ORDER.index(cat_of[b]) if cat_of[b] in CAT_ORDER else 99, b.lower()))

    allp = [l["price"] for l in rows] + [float(v) for v in limits.values() if v]
    lo = 10 ** (__import__("math").floor(__import__("math").log10(min(allp) * 0.8) * 2) / 2)
    hi = max(allp) * 1.6

    rh = 0.62
    fig_h = 1.3 + 0.42 * len(books)
    plt.rcParams["font.family"] = "DejaVu Sans"
    fig, ax = plt.subplots(figsize=(10, fig_h), dpi=150)
    fig.subplots_adjust(left=0.30, right=0.97, top=1 - 0.75 / fig_h, bottom=0.55 / fig_h)
    ax.set_xscale("log")
    ax.set_xlim(lo, hi)
    ax.set_ylim(len(books) - 0.4, -0.6)
    ticks = [t for t in (200, 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000, 200000) if lo <= t <= hi]
    ax.xaxis.set_major_locator(FixedLocator(ticks))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v/1000:g}k" if v >= 1000 else f"{v:g}"))
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(axis="x", colors=MUT, labelsize=8, length=0)
    ax.tick_params(axis="y", length=0)
    ax.set_yticks(range(len(books)))
    ax.set_yticklabels(books, fontsize=8.5, color=SEC)
    ax.set_xlabel("Asking price (Kč, log scale)", color=MUT, fontsize=8)

    def candle(y, vals, color, h):
        mn, mx, q1, q3, md = min(vals), max(vals), q(vals, .25), q(vals, .75), q(vals, .5)
        ax.plot([mn, mx], [y, y], color=color, lw=1.4, solid_capstyle="round", zorder=3)
        if q3 / q1 < 1.02:
            ax.add_patch(plt.Rectangle((q1 / 1.015, y - h / 2), q3 * 1.015 - q1 / 1.015, h, color=color, zorder=4, lw=0))
        else:
            ax.add_patch(plt.Rectangle((q1, y - h / 2), q3 - q1, h, color=color, zorder=4, lw=0))
        if len(vals) > 1:
            ax.plot([md, md], [y - h / 2, y + h / 2], color="white", lw=1.6, zorder=5)
        ax.text(mx * 1.06, y, f"n={len(vals)}", va="center", fontsize=7, color=SEC if color == BLUE else MUT, zorder=6)

    prev = None
    for i, b in enumerate(books):
        c = cat_of[b]
        if c != prev and i > 0:
            ax.axhline(i - 0.5, color=MUT, lw=0.5, ls=(0, (2, 3)))
        if c != prev:
            ax.text(-0.43, i - 0.28, c.upper(), transform=ax.get_yaxis_transform(), fontsize=6.5, color=MUT, ha="left")
        prev = c
        if past.get(b):
            candle(i - 0.15, past[b], GREY, rh * 0.32)
        if cur.get(b):
            candle(i + (0.12 if past.get(b) else 0), cur[b], BLUE, rh * 0.4)
        lim = limits.get(b)
        if lim:
            ax.plot([float(lim)] * 2, [i - 0.42, i + 0.42], color=RED, lw=1.6, ls=(0, (3, 2)), zorder=6)

    n_past = len(runs) - 1
    date = latest[:10]
    fig.text(0.015, 1 - 0.22 / fig_h, f"Comics scout – price candles – {date}", fontsize=11, color=INK, weight="bold", va="top")
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    handles = [Patch(color=BLUE, label=f"Latest run ({date})"),
               Patch(color=GREY, label=f"Earlier runs ({n_past}, {runs[0][:10]} – {runs[-2][:10]})" if n_past else "Earlier runs (none yet)"),
               Line2D([], [], color=RED, ls=(0, (3, 2)), lw=1.6, label="Alert limit")]
    fig.legend(handles=handles, loc="upper right", bbox_to_anchor=(0.97, 1 - 0.12 / fig_h), ncol=3, frameon=False, fontsize=7.5,
               labelcolor=SEC, handlelength=1.4)
    fig.text(0.015, 0.012, "Wick = lowest–highest asking price · body = middle 50 % of listings · white line = median · listings without a price not shown",
             fontsize=6.5, color=MUT)
    fig.savefig(out, facecolor="white")
    return len(books), sum(len(v) for v in cur.values()), n_past


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    out = sys.argv[1]
    args = sys.argv[2:]
    try:
        if "--data" in args:
            d = json.load(open(args[args.index("--data") + 1], encoding="utf-8"))
            listings, limits = d["listings"], d.get("limits", {})
            src = "test data"
        else:
            try:
                listings, limits = load_supabase()
                src = "Supabase"
            except Exception as e:
                if "--run" not in args:
                    raise
                listings, limits = load_run(args[args.index("--run") + 1])
                src = f"today's run only (Supabase unavailable: {type(e).__name__})"
        res = build(listings, limits, out)
    except Exception as e:
        print(f"Chart not made – {type(e).__name__}: {str(e)[:200]}"); sys.exit(1)
    if not res:
        print("Chart not made – no priced listings."); sys.exit(1)
    books, n_cur, n_past = res
    print(f"Chart ready – {out}: {books} books, {n_cur} listings in the latest run, {n_past} earlier runs in grey ({src}).")


if __name__ == "__main__":
    main()
