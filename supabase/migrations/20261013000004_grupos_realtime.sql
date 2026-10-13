-- =============================================================================
-- Grupos na prancheta (fase 13, item 13.1) -- 4/5: Realtime.
--
-- Um canal PRIVADO por sala, com o tópico 'sala:<id da sala>':
--   * as operações chegam por Postgres Changes em public.operacoes (filtro
--     sala_id=eq.<id>), e o Realtime confere o RLS da tabela para cada
--     assinante a cada operação;
--   * quem está online vai por Presence; o cabeçote da líder, por Broadcast
--     (nada disso fica guardado: o Realtime apaga as mensagens dos canais);
--   * as mudanças de membros e da sala (permissão, expulsão, encerrar,
--     transferir) vão por Broadcast saído do banco (realtime.send), porque o
--     Postgres Changes não aplica RLS em DELETE e o expulso precisa saber.
-- A entrada no canal privado é autorizada pelo RLS de realtime.messages
-- (documentação do Supabase, "Realtime Authorization", consultada em
-- 2026-10-13): só membro entra. O RLS dessa tabela já vem ligado no Supabase
-- -- NÃO se escreve "alter table realtime.messages enable row level security"
-- aqui (a documentação avisa que falha com 42501 e aborta a migração).
-- No painel, Realtime > Settings > "Allow public access" precisa ficar
-- DESLIGADO (passo do cartão em notas/PENDENCIAS_PARA_O_PEDRO.md).
-- =============================================================================

-- As operações entram na publicação do Realtime (Postgres Changes).
alter publication supabase_realtime add table public.operacoes;

-- O tópico é 'sala:<uuid>'. Qualquer outro formato não é de sala nenhuma.
create or replace function grupos.sala_do_topico(p_topico text)
returns uuid
language sql immutable set search_path = ''
as $$
  select case when p_topico ~ '^sala:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
              then substr(p_topico, 6)::uuid end;
$$;
revoke all on function grupos.sala_do_topico(text) from public, anon;
grant execute on function grupos.sala_do_topico(text) to authenticated;

-- Receber (Presence e Broadcast do canal da sala): só membro.
create policy grupos_membro_le_o_canal on realtime.messages
  for select to authenticated
  using (realtime.messages.extension in ('broadcast', 'presence')
         and grupos.eh_membro(grupos.sala_do_topico((select realtime.topic()))));

-- Marcar presença: só membro.
create policy grupos_membro_marca_presenca on realtime.messages
  for insert to authenticated
  with check (realtime.messages.extension = 'presence'
              and grupos.eh_membro(grupos.sala_do_topico((select realtime.topic()))));

-- Transmitir (o cabeçote): só a líder.
create policy grupos_lider_transmite on realtime.messages
  for insert to authenticated
  with check (realtime.messages.extension = 'broadcast'
              and grupos.eh_lider(grupos.sala_do_topico((select realtime.topic()))));

-- ---------------------------------------------------------------------------
-- Avisos do banco para o canal da sala: quem entrou, saiu ou foi expulso, quem
-- pode desenhar, "todos podem desenhar", encerrar e transferir a liderança.
-- O cliente relê membros e sala (pelo RLS) ao receber; o expulso, que já não
-- lê nada, sabe pelo próprio aviso.
-- ---------------------------------------------------------------------------
create or replace function grupos.avisa_a_sala()
returns trigger
language plpgsql security definer set search_path = ''
as $$
declare
  v_sala uuid;
  v_aviso jsonb;
begin
  if tg_table_name = 'salas' then
    v_sala := new.id;
    v_aviso := jsonb_build_object('tabela', 'salas', 'lider', new.lider,
                                  'todos_podem_desenhar', new.todos_podem_desenhar, 'encerrada', new.encerrada);
  elsif tg_op = 'DELETE' then
    v_sala := old.sala_id;
    v_aviso := jsonb_build_object('tabela', 'membros', 'evento', tg_op, 'usuario', old.usuario);
  else
    v_sala := new.sala_id;
    v_aviso := jsonb_build_object('tabela', 'membros', 'evento', tg_op, 'usuario', new.usuario,
                                  'pode_desenhar', new.pode_desenhar);
  end if;
  perform realtime.send(v_aviso, 'mudou', 'sala:' || v_sala::text, true);
  return null;
end
$$;
revoke all on function grupos.avisa_a_sala() from public, anon, authenticated;

create trigger avisa_a_sala_membros after insert or update or delete on public.membros
  for each row execute function grupos.avisa_a_sala();
-- só as colunas que a tela mostra (ultima_atividade muda a cada minuto e não interessa)
create trigger avisa_a_sala_salas after update of todos_podem_desenhar, encerrada, lider on public.salas
  for each row
  when (old.todos_podem_desenhar is distinct from new.todos_podem_desenhar
        or old.encerrada is distinct from new.encerrada
        or old.lider is distinct from new.lider)
  execute function grupos.avisa_a_sala();
