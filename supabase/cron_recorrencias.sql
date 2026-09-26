-- Opcional: execute este arquivo uma vez no SQL Editor do Supabase para que as
-- cobranças sejam geradas diariamente, mesmo quando ninguém abrir o aplicativo.
create extension if not exists pg_cron with schema extensions;

do $$
begin
    if not exists (
        select 1 from cron.job where jobname = 'sincronizar-despesas-recorrentes'
    ) then
        perform cron.schedule(
            'sincronizar-despesas-recorrentes',
            '5 3 * * *',
            'select public.sincronizar_despesas_recorrentes(current_date);'
        );
    end if;
end;
$$;
