-- AIR AGENTS LLC initial Supabase schema
-- Apply to the selected Supabase project only after review.
-- This migration creates durable operating records, role-based RLS controls,
-- append-only audit data, and GitHub webhook delivery idempotency.

begin;

create extension if not exists pgcrypto;

create type public.air_agents_role as enum ('viewer', 'operator', 'admin');

create table public.workspace_members (
    user_id uuid primary key references auth.users(id) on delete cascade,
    role public.air_agents_role not null default 'viewer',
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table public.leads (
    id uuid primary key default gen_random_uuid(),
    full_name text not null check (char_length(full_name) between 1 and 160),
    email text not null check (char_length(email) <= 320),
    phone text check (phone is null or char_length(phone) <= 40),
    company text check (company is null or char_length(company) <= 160),
    service_interest text not null check (service_interest in (
        'ai_growth_systems', 'partnered_operations', 'voice_agent_automation',
        'media_production', 'lending_coordination', 'creative_launchpad', 'other'
    )),
    message text check (message is null or char_length(message) <= 8000),
    source text not null default 'website' check (char_length(source) between 1 and 80),
    status text not null default 'new' check (status in ('new', 'qualified', 'nurturing', 'closed_won', 'closed_lost')),
    priority text not null default 'normal' check (priority in ('low', 'normal', 'high', 'urgent')),
    owner text check (owner is null or char_length(owner) <= 120),
    consent_to_contact boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table public.partners (
    id uuid primary key default gen_random_uuid(),
    name text not null check (char_length(name) between 1 and 160),
    category text not null check (category in ('vendor', 'lending_partner', 'creative_partner', 'technology', 'referral', 'other')),
    contact_name text check (contact_name is null or char_length(contact_name) <= 160),
    email text check (email is null or char_length(email) <= 320),
    phone text check (phone is null or char_length(phone) <= 40),
    status text not null default 'prospect' check (status in ('prospect', 'active', 'inactive', 'paused')),
    notes text check (notes is null or char_length(notes) <= 8000),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table public.tasks (
    id uuid primary key default gen_random_uuid(),
    title text not null check (char_length(title) between 1 and 160),
    description text check (description is null or char_length(description) <= 8000),
    status text not null default 'open' check (status in ('open', 'in_progress', 'blocked', 'completed')),
    priority text not null default 'normal' check (priority in ('low', 'normal', 'high', 'urgent')),
    assignee text check (assignee is null or char_length(assignee) <= 120),
    due_at timestamptz,
    related_type text check (related_type is null or related_type in ('lead', 'partner', 'lending_case', 'campaign_brief')),
    related_id uuid,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table public.lending_cases (
    id uuid primary key default gen_random_uuid(),
    business_name text not null check (char_length(business_name) between 1 and 160),
    contact_name text not null check (char_length(contact_name) between 1 and 160),
    email text not null check (char_length(email) <= 320),
    funding_goal text check (funding_goal is null or char_length(funding_goal) <= 1000),
    requested_amount bigint check (requested_amount is null or requested_amount between 0 and 100000000),
    readiness_status text not null default 'intake' check (readiness_status in (
        'intake', 'documents_requested', 'package_ready', 'partner_follow_up', 'closed', 'not_proceeding'
    )),
    documents_status text not null default 'not_requested' check (documents_status in ('not_requested', 'requested', 'partial', 'complete')),
    authorized_partner_contact boolean not null default false,
    notes text check (notes is null or char_length(notes) <= 8000),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table public.campaign_briefs (
    id uuid primary key default gen_random_uuid(),
    title text not null check (char_length(title) between 1 and 160),
    objective text not null check (char_length(objective) between 1 and 8000),
    audience text not null check (char_length(audience) between 1 and 8000),
    primary_message text not null check (char_length(primary_message) between 1 and 8000),
    channels jsonb not null default '[]'::jsonb check (jsonb_typeof(channels) = 'array'),
    visual_direction text check (visual_direction is null or char_length(visual_direction) <= 8000),
    call_to_action text check (call_to_action is null or char_length(call_to_action) <= 500),
    status text not null default 'draft' check (status in ('draft', 'review', 'approved', 'in_production', 'complete', 'archived')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table public.audit_events (
    id uuid primary key default gen_random_uuid(),
    actor_user_id uuid references auth.users(id) on delete set null,
    actor_role text not null check (actor_role in ('public', 'viewer', 'operator', 'admin', 'system')),
    action text not null check (char_length(action) between 1 and 120),
    entity_type text not null check (char_length(entity_type) between 1 and 120),
    entity_id text not null check (char_length(entity_id) between 1 and 128),
    created_at timestamptz not null default now(),
    metadata jsonb not null default '{}'::jsonb check (jsonb_typeof(metadata) = 'object')
);

create table public.github_webhook_deliveries (
    delivery_id text primary key check (char_length(delivery_id) between 1 and 128),
    event_name text not null check (char_length(event_name) between 1 and 120),
    action text check (action is null or char_length(action) <= 120),
    repository_full_name text check (repository_full_name is null or char_length(repository_full_name) <= 512),
    installation_id text check (installation_id is null or char_length(installation_id) <= 64),
    payload_sha256 text not null check (payload_sha256 ~ '^[a-f0-9]{64}$'),
    status text not null default 'received' check (status in ('received', 'queued', 'processed', 'failed', 'ignored')),
    received_at timestamptz not null default now(),
    processed_at timestamptz,
    metadata jsonb not null default '{}'::jsonb check (jsonb_typeof(metadata) = 'object')
);

create index leads_status_created_idx on public.leads (status, created_at desc);
create index leads_email_idx on public.leads (email);
create index partners_status_idx on public.partners (status);
create index tasks_status_due_idx on public.tasks (status, due_at);
create index lending_cases_status_idx on public.lending_cases (readiness_status);
create index campaign_briefs_status_idx on public.campaign_briefs (status);
create index audit_events_created_idx on public.audit_events (created_at desc);
create index github_webhook_deliveries_received_idx on public.github_webhook_deliveries (received_at desc);
create index github_webhook_deliveries_repository_idx on public.github_webhook_deliveries (repository_full_name, received_at desc);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = public
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

create trigger workspace_members_set_updated_at before update on public.workspace_members
for each row execute function public.set_updated_at();
create trigger leads_set_updated_at before update on public.leads
for each row execute function public.set_updated_at();
create trigger partners_set_updated_at before update on public.partners
for each row execute function public.set_updated_at();
create trigger tasks_set_updated_at before update on public.tasks
for each row execute function public.set_updated_at();
create trigger lending_cases_set_updated_at before update on public.lending_cases
for each row execute function public.set_updated_at();
create trigger campaign_briefs_set_updated_at before update on public.campaign_briefs
for each row execute function public.set_updated_at();

create or replace function public.air_agents_has_role(minimum_role public.air_agents_role)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
    select coalesce((
        select member.role >= minimum_role
        from public.workspace_members as member
        where member.user_id = auth.uid() and member.is_active
        limit 1
    ), false);
$$;

revoke all on function public.air_agents_has_role(public.air_agents_role) from public;
grant execute on function public.air_agents_has_role(public.air_agents_role) to authenticated;

alter table public.workspace_members enable row level security;
alter table public.leads enable row level security;
alter table public.partners enable row level security;
alter table public.tasks enable row level security;
alter table public.lending_cases enable row level security;
alter table public.campaign_briefs enable row level security;
alter table public.audit_events enable row level security;
alter table public.github_webhook_deliveries enable row level security;

-- Workspace users can inspect their membership; administrators can inspect all membership records.
create policy "workspace members read permitted memberships" on public.workspace_members
for select to authenticated
using (user_id = auth.uid() or public.air_agents_has_role('admin'));

-- Browser clients never receive a direct anonymous table policy. Public form intake
-- flows through the validated FastAPI endpoint using a server-side database credential.
create policy "workspace leads select" on public.leads
for select to authenticated using (public.air_agents_has_role('viewer'));
create policy "workspace leads insert" on public.leads
for insert to authenticated with check (public.air_agents_has_role('operator'));
create policy "workspace leads update" on public.leads
for update to authenticated using (public.air_agents_has_role('operator')) with check (public.air_agents_has_role('operator'));

create policy "workspace partners select" on public.partners
for select to authenticated using (public.air_agents_has_role('viewer'));
create policy "workspace partners insert" on public.partners
for insert to authenticated with check (public.air_agents_has_role('operator'));
create policy "workspace partners update" on public.partners
for update to authenticated using (public.air_agents_has_role('operator')) with check (public.air_agents_has_role('operator'));

create policy "workspace tasks select" on public.tasks
for select to authenticated using (public.air_agents_has_role('viewer'));
create policy "workspace tasks insert" on public.tasks
for insert to authenticated with check (public.air_agents_has_role('operator'));
create policy "workspace tasks update" on public.tasks
for update to authenticated using (public.air_agents_has_role('operator')) with check (public.air_agents_has_role('operator'));

create policy "workspace lending cases select" on public.lending_cases
for select to authenticated using (public.air_agents_has_role('viewer'));
create policy "workspace lending cases insert" on public.lending_cases
for insert to authenticated with check (public.air_agents_has_role('operator'));
create policy "workspace lending cases update" on public.lending_cases
for update to authenticated using (public.air_agents_has_role('operator')) with check (public.air_agents_has_role('operator'));

create policy "workspace campaign briefs select" on public.campaign_briefs
for select to authenticated using (public.air_agents_has_role('viewer'));
create policy "workspace campaign briefs insert" on public.campaign_briefs
for insert to authenticated with check (public.air_agents_has_role('operator'));
create policy "workspace campaign briefs update" on public.campaign_briefs
for update to authenticated using (public.air_agents_has_role('operator')) with check (public.air_agents_has_role('operator'));

create policy "administrators read audit events" on public.audit_events
for select to authenticated using (public.air_agents_has_role('admin'));

create policy "administrators read webhook delivery receipts" on public.github_webhook_deliveries
for select to authenticated using (public.air_agents_has_role('admin'));

commit;
