-- =============================================================================
-- Grupos na prancheta (fase 13, item 13.1) -- 5/5: limpeza agendada.
--
-- Uma vez por dia, às 04:17 UTC, salas paradas há mais de 30 dias saem (com
-- as operações e os membros). Usa o pg_cron ("Supabase Cron"); a documentação
-- consultada em 2026-10-13 (supabase.com/docs/guides/cron/quickstart) mostra o
-- cron.schedule e não cita restrição de plano.
--
-- SE ESTA MIGRAÇÃO FALHAR (extensão indisponível no plano): as quatro
-- anteriores bastam para o grupo funcionar. Rode a limpeza à mão no SQL
-- Editor de vez em quando:
--     select grupos.limpa_salas_antigas();
-- (devolve quantas salas saíram). O cartão em notas/PENDENCIAS_PARA_O_PEDRO.md
-- diz o mesmo.
-- =============================================================================

create extension if not exists pg_cron;

select cron.schedule('grupos-limpa-salas-antigas', '17 4 * * *', $$select grupos.limpa_salas_antigas()$$);
