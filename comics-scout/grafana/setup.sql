-- =====================================================================
-- Comics scout – Supabase setup (run ONCE in Supabase → SQL Editor)
-- Before running: replace CHANGE_ME_GRAFANA_PASSWORD below with a strong
-- password of your own (Grafana uses it to read the data).
-- Safe to run again: everything uses "if not exists" / "or replace".
-- =====================================================================

-- 1) Raw data, written by the daily scout run (through the Supabase REST API)
create table if not exists public.scout_runs (
  run_ts        timestamptz primary key,          -- time of the run (Prague time, stored with zone)
  run_date      date        not null,
  note          text        not null default '',
  sites_checked text[]      not null default '{}',
  sites_failed  text[]      not null default '{}',
  item_count    integer     not null default 0,
  inserted_at   timestamptz not null default now()
);

create table if not exists public.scout_listings (
  run_ts     timestamptz not null references public.scout_runs(run_ts) on delete cascade,
  url_key    text not null,                      -- normalised link = identity of a listing
  url        text not null,
  cat        text not null,                      -- Mighty Boys / Tales from the Crypt / Kolosální Conan / Banda / Criminal
  book       text not null,                      -- clean book name, e.g. "Banda 2: Nakládačka"
  title      text not null,
  site       text not null,
  place      text not null default '',
  price      numeric,                            -- Kč, null = price in text / by agreement
  price_text text not null default '',
  primary key (run_ts, url_key)
);
create index if not exists scout_listings_url_key_idx on public.scout_listings (url_key);
create index if not exists scout_listings_book_idx    on public.scout_listings (book, run_ts);

-- Price limits for Grafana alerts (edit these rows any time in Table Editor)
create table if not exists public.scout_alert_limits (
  book      text primary key,
  max_price numeric,                             -- alert when the cheapest offer is at or below this; null = no alert
  note      text not null default ''
);
insert into public.scout_alert_limits (book, max_price, note) values
  ('Kolosální Conan vol. 1',                       30000, 'bargain level used by the scout'),
  ('Přístav Země / Zatmění – collector''s',         2500, 'original price 1 969 Kč'),
  ('Přístav Země / Zatmění – normal / not stated',  2500, 'original price 1 969 Kč'),
  ('Trojka – collector''s',                          800, 'original price 528 Kč'),
  ('Trojka – normal / not stated',                   800, 'original price 528 Kč'),
  ('Banda 1: Karty jsou rozdaný',                   null, 'set your limit'),
  ('Banda 2: Nakládačka',                           null, 'set your limit'),
  ('Criminal 1: Každý je zločinec',                 null, 'set your limit'),
  ('Criminal 3: Noční rozhodnutí',                  null, 'set your limit'),
  ('Criminal – deluxe edice 1',                     null, 'set your limit'),
  ('Criminal – deluxe edice 2',                     null, 'set your limit'),
  ('Criminal: Poslední z nevinných',                null, 'set your limit'),
  ('Tales from the Crypt',                          null, 'set your limit')
on conflict (book) do nothing;

-- Lock the tables: nobody can read/write them through the public API keys.
-- The scout writes with the SECRET key (bypasses this); Grafana reads with its own role below.
alter table public.scout_runs         enable row level security;
alter table public.scout_listings     enable row level security;
alter table public.scout_alert_limits enable row level security;

-- 2) Read-only role for Grafana
do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'grafana_reader') then
    create role grafana_reader login password 'CHANGE_ME_GRAFANA_PASSWORD';
  end if;
end $$;

drop policy if exists grafana_read on public.scout_runs;
drop policy if exists grafana_read on public.scout_listings;
drop policy if exists grafana_read on public.scout_alert_limits;
create policy grafana_read on public.scout_runs         for select to grafana_reader using (true);
create policy grafana_read on public.scout_listings     for select to grafana_reader using (true);
create policy grafana_read on public.scout_alert_limits for select to grafana_reader using (true);

-- 3) Views for Grafana, in their own schema (not exposed by the Supabase API)
create schema if not exists scout;

-- site name -> short key ("Aukro (via KomiksBazar)" -> komiksbazar, "Arkham (partial)" -> arkham)
create or replace function scout.site_key(s text) returns text language sql immutable as $$
  select case when lower(coalesce(s,'')) like '%komiksbazar%' then 'komiksbazar'
              else split_part(btrim(regexp_replace(lower(coalesce(s,'')), '\(.*?\)', ' ', 'g')), ' ', 1) end
$$;

-- sites that were checked fully in each run (not failed, not "partial")
create or replace view scout.run_ok_sites with (security_invoker = true) as
select r.run_ts, scout.site_key(s) as site_key
from public.scout_runs r, unnest(r.sites_checked) s
where s !~* 'partial'
  and scout.site_key(s) <> all (array(select scout.site_key(f) from unnest(r.sites_failed) f));

-- cheapest price and number of offers per book per run (price trends, offer counts)
create or replace view scout.book_prices with (security_invoker = true) as
select run_ts, cat, book, min(price) as min_price, count(*) as offers
from public.scout_listings
group by run_ts, cat, book;

-- listings of the latest run
create or replace view scout.latest_listings with (security_invoker = true) as
select l.*
from public.scout_listings l
where l.run_ts = (select max(run_ts) from public.scout_runs);

-- one row per listing ever seen: first/last seen, prices, status
create or replace view scout.listing_history with (security_invoker = true) as
with agg as (
  select url_key,
         min(run_ts) as first_seen,
         max(run_ts) as last_seen,
         count(*)    as times_seen,
         (array_agg(price order by run_ts) filter (where price is not null))[1] as first_price,
         count(distinct price_text) - 1 as price_changes
  from public.scout_listings group by url_key
), last_row as (
  select distinct on (url_key) * from public.scout_listings order by url_key, run_ts desc
)
select l.url_key, l.cat, l.book, l.title, l.site, l.place, l.url,
       a.first_seen, a.last_seen, a.times_seen,
       a.first_price, l.price as price_now, l.price_text as price_now_text,
       case when l.price is not null and a.first_price is not null then l.price - a.first_price end as price_change,
       a.price_changes,
       case
         when a.last_seen = (select max(run_ts) from public.scout_runs) then 'active'
         when exists (select 1 from scout.run_ok_sites o
                      where o.run_ts > a.last_seen and o.site_key = scout.site_key(l.site)) then 'gone'
         else 'not checked'
       end as status,
       (select min(o.run_ts) from scout.run_ok_sites o
         where o.run_ts > a.last_seen and o.site_key = scout.site_key(l.site)) as gone_since
from agg a join last_row l using (url_key);

-- bargains right now: books whose cheapest offer in the latest run is at or below its limit (for alerts)
create or replace view scout.bargains with (security_invoker = true) as
select b.book, b.cat, b.min_price, lim.max_price, b.offers, b.run_ts
from scout.book_prices b
join public.scout_alert_limits lim on lim.book = b.book and lim.max_price is not null
where b.run_ts = (select max(run_ts) from public.scout_runs)
  and b.min_price is not null and b.min_price <= lim.max_price;

grant usage on schema scout to grafana_reader;
grant select on all tables in schema scout to grafana_reader;
grant execute on function scout.site_key(text) to grafana_reader;
grant usage on schema public to grafana_reader;
grant select on public.scout_runs, public.scout_listings, public.scout_alert_limits to grafana_reader;
