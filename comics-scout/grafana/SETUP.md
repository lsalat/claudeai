# Comics scout → Supabase → Grafana Cloud (setup, once)

How it works: every daily scout run uploads its findings to a free **Supabase** Postgres database
(`supabase_push.py`). **Grafana Cloud** (free) reads that database and shows the dashboard and alerts.
Supabase keeps the data with no time limit, so Grafana's 14-day limit does not matter (Grafana only displays it).

Files in this folder:
- `setup.sql` – tables, views, read-only Grafana user, alert limits (run once)
- `seed-2026-11-19.sql` – the first run (19/11/2026 14:59), so the dashboard starts with data
- `dashboard.json` – the Grafana dashboard to import

## 1. Supabase (5 min)
1. Sign up at https://supabase.com (free, no card) → **New project**. Region: **Central EU (Frankfurt)**. Save the database password somewhere safe.
2. Open **SQL Editor** → New query → paste the whole `setup.sql`.
   Replace `CHANGE_ME_GRAFANA_PASSWORD` with a new strong password (this is for Grafana, not the DB password) → **Run**.
3. New query → paste `seed-2026-11-19.sql` → **Run**.
4. **Project Settings → API Keys**: copy the **Project URL** (`https://xxxx.supabase.co`) and a **Secret key** (`sb_secret_…`; or the legacy `service_role` key).

## 2. Claude (2 min)
1. In the cloud environment used by the scheduled task, add two **environment secrets** (the same place as GH_TOKEN before):
   - `SUPABASE_URL` = the Project URL
   - `SUPABASE_SECRET_KEY` = the secret key
   Never paste the key into a chat or the task text.
2. claude.ai → **Settings → Capabilities** → allowed domains: add **`supabase.co`**.

## 3. Grafana Cloud (5 min)
1. Sign up at https://grafana.com (free) and open your stack.
2. **Connections → Data sources → Add → PostgreSQL**:
   - Name: `Comics scout`
   - Host: in Supabase click **Connect** (top bar) → **Session pooler** → copy host and port, e.g. `aws-0-eu-central-1.pooler.supabase.com:5432`
   - Database: `postgres`
   - User: `grafana_reader.<project-ref>` (project-ref = the `xxxx` from the Project URL)
   - Password: the Grafana password you put in `setup.sql`
   - TLS/SSL mode: **require**
   - **Save & test** → should say "Database Connection OK".
3. **Dashboards → New → Import** → upload `dashboard.json` → choose the `Comics scout` data source → **Import**.

## 4. Price alert (optional, 3 min)
**Alerting → Alert rules → New alert rule**:
- Query (data source `Comics scout`, Code mode, Format **Table**):
  `SELECT book AS metric, min_price AS value FROM scout.bargains`
- Expressions: **Reduce** (Last) → **Threshold**: IS ABOVE `0`
- Evaluate every `1h`, pending period `0s`; folder/group: `Comics scout`
- Contact point: your e-mail. Name: `Comics scout – bargain`.
You get one alert per book whose cheapest offer is at or below its limit.
**Change the limits** any time in Supabase → Table Editor → `scout_alert_limits` (`max_price`, empty = no alert).

## What you see
- **Cheapest price per book** over time, **offers per category** per run
- **Bargains now** (at/below your limit), **Latest run** table, **History** of every listing
  (active / gone = likely sold / not checked), all with links to the ads.

## Notes
- If the upload fails (secrets missing, Supabase paused, network), the daily run still finishes and reports "Supabase not updated".
- Supabase pauses free projects after 7 days without activity; the daily upload keeps it active. A paused project can be resumed from the Supabase dashboard with all data.
