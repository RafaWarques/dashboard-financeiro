-- Lista compartilhada da família, acessada somente pelo servidor Streamlit.
-- Execute o arquivo inteiro no SQL Editor do mesmo projeto das despesas.
begin;

create table if not exists public.wishlist_itens (
    id uuid primary key default gen_random_uuid(),
    nome text not null check (length(trim(nome)) between 1 and 120),
    valor numeric(12, 2) not null check (valor > 0 and valor <= 9999999999.99),
    descricao text not null default '' check (length(descricao) <= 2000),
    responsavel text not null check (responsavel in ('Rafael', 'Nathalia')),
    status text not null default 'desejado' check (status in ('desejado', 'comprado')),
    foto_path text,
    criado_em timestamptz not null default now(),
    atualizado_em timestamptz not null default now(),
    comprado_em timestamptz,
    constraint wishlist_compra_status check (
        (status = 'desejado' and comprado_em is null)
        or (status = 'comprado' and comprado_em is not null)
    ),
    constraint wishlist_foto_path check (
        foto_path is null or foto_path ~ (
            '^' || id::text || '/[0-9a-f]{32}[.]jpg$'
        )
    )
);

create index if not exists wishlist_responsavel_status_idx
    on public.wishlist_itens (responsavel, status, criado_em desc);

create or replace function public.wishlist_atualizar_timestamp()
returns trigger
language plpgsql
set search_path = public
as $$
begin
    new.atualizado_em = now();
    return new;
end;
$$;

drop trigger if exists wishlist_timestamp on public.wishlist_itens;
create trigger wishlist_timestamp
    before update on public.wishlist_itens
    for each row execute function public.wishlist_atualizar_timestamp();

alter table public.wishlist_itens enable row level security;
-- Sem políticas abertas: a chave anon do app não acessa esta tabela.
revoke all on public.wishlist_itens from public, anon, authenticated;
grant select, insert, update, delete on public.wishlist_itens to service_role;
revoke all on function public.wishlist_atualizar_timestamp() from public;

-- O app valida e converte as fotos para JPEG antes de enviar ao Storage.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('wishlist-fotos', 'wishlist-fotos', false, 5242880, array['image/jpeg'])
on conflict (id) do update set
    public = false,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;

-- Acesso ao bucket pelo servidor usando service_role, sem políticas anon.
-- Nenhuma alteração nas políticas das despesas ou dos outros buckets.
commit;

notify pgrst, 'reload schema';
