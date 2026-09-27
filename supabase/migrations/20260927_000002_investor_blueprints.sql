-- AIR AGENTS LLC investor blueprint and KPI targets
-- Review and apply only to the explicitly selected durable Supabase project.
-- This migration is intentionally not applied by the repository.

begin;

create table public.investor_blueprints (
    id uuid primary key default gen_random_uuid(),
    title text not null check (char_length(title) between 1 and 160),
    as_of_date date not null,
    currency text not null default 'USD' check (currency ~ '^[A-Z]{3}$'),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table public.investor_kpis (
    id uuid primary key default gen_random_uuid(),
    blueprint_id uuid not null references public.investor_blueprints(id) on delete cascade,
    category text not null check (category in ('revenue', 'retention', 'growth', 'operations')),
    label text not null check (char_length(label) between 1 and 160),
    actual_value numeric not null check (actual_value between -1000000000000 and 1000000000000),
    target_value numeric not null check (target_value > 0 and target_value <= 1000000000000),
    unit text not null check (unit in ('currency', 'percent', 'count', 'ratio')),
    owner text check (owner is null or char_length(owner) <= 120),
    target_date date,
    description text check (description is null or char_length(description) <= 8000),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index investor_blueprints_as_of_date_idx
    on public.investor_blueprints (as_of_date desc);
create index investor_kpis_blueprint_category_target_idx
    on public.investor_kpis (blueprint_id, category, target_date);

create trigger investor_blueprints_set_updated_at before update on public.investor_blueprints
for each row execute function public.set_updated_at();
create trigger investor_kpis_set_updated_at before update on public.investor_kpis
for each row execute function public.set_updated_at();

alter table public.investor_blueprints enable row level security;
alter table public.investor_kpis enable row level security;

-- Viewer roles can consume the investor snapshot. Only administrators can
-- change source targets or accountable owners; the FastAPI layer also writes
-- the corresponding append-only audit event.
create policy "workspace investor blueprints select" on public.investor_blueprints
for select to authenticated using (public.air_agents_has_role('viewer'));
create policy "administrators investor blueprints insert" on public.investor_blueprints
for insert to authenticated with check (public.air_agents_has_role('admin'));
create policy "administrators investor blueprints update" on public.investor_blueprints
for update to authenticated using (public.air_agents_has_role('admin')) with check (public.air_agents_has_role('admin'));

create policy "workspace investor kpis select" on public.investor_kpis
for select to authenticated using (public.air_agents_has_role('viewer'));
create policy "administrators investor kpis insert" on public.investor_kpis
for insert to authenticated with check (public.air_agents_has_role('admin'));
create policy "administrators investor kpis update" on public.investor_kpis
for update to authenticated using (public.air_agents_has_role('admin')) with check (public.air_agents_has_role('admin'));

commit;
