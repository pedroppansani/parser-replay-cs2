-- =============================================================================
-- Grupos na prancheta (fase 13, item 13.1) -- 3/5: funções e gatilhos.
--
-- Toda função `security definer` tem `search_path` vazio e nomes qualificados
-- (um objeto com o mesmo nome em outro schema não a sequestra).
-- Os limites são constantes nomeadas no começo de cada função, com a origem:
--   MAX_MEMBROS = 10                 (pedido da fase 13, item 13.1)
--   MAX_OPS_POR_SEGUNDO = 20         (proposta da fase 13: nenhum cliente inunda a sala)
--   MAX_ERROS_DE_CODIGO = 5 em 10 min (limite contra adivinhar o código; 13.7)
--   MAX_SALAS_POR_HORA = 5           (ninguém cria salas em série; 13.7)
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Código da sala: 8 caracteres de ABCDEFGHJKMNPQRSTUVWXYZ23456789 (31, sem
-- 0/O e 1/I/L), sorteados de gen_random_uuid() (gerador forte do Postgres),
-- com rejeição dos bytes >= 248 para não enviesar o resto da divisão por 31.
-- ---------------------------------------------------------------------------
create or replace function grupos.gera_codigo()
returns text
language plpgsql volatile set search_path = ''
as $$
declare
  c_alfabeto constant text := 'ABCDEFGHJKMNPQRSTUVWXYZ23456789';
  v_codigo text;
  v_bytes bytea;
  v_b int;
begin
  loop
    v_codigo := '';
    while char_length(v_codigo) < 8 loop
      v_bytes := pg_catalog.uuid_send(pg_catalog.gen_random_uuid());
      -- bytes 0 a 5 do uuid v4 são todos aleatórios (versão e variante ficam nos bytes 6 e 8)
      for i in 0..5 loop
        v_b := pg_catalog.get_byte(v_bytes, i);
        if v_b < 248 and char_length(v_codigo) < 8 then
          v_codigo := v_codigo || substr(c_alfabeto, v_b % 31 + 1, 1);
        end if;
      end loop;
    end loop;
    exit when not exists (select 1 from public.salas s where s.codigo = v_codigo);
  end loop;
  return v_codigo;
end
$$;
revoke all on function grupos.gera_codigo() from public, anon, authenticated;

-- ---------------------------------------------------------------------------
-- Criar sala: o insert direto (política salas_insere_lider) passa por aqui.
-- O código e os padrões são do servidor; ninguém escolhe.
-- ---------------------------------------------------------------------------
create or replace function grupos.antes_de_criar_sala()
returns trigger
language plpgsql security definer set search_path = ''
as $$
declare
  c_max_salas_por_hora constant int := 5;
  v_n int;
begin
  select count(*) into v_n from public.salas s
   where s.lider = new.lider and s.criada_em > now() - interval '1 hour';
  if v_n >= c_max_salas_por_hora then
    raise exception 'muitas_salas' using errcode = 'P0001',
      hint = 'no máximo 5 grupos por hora por pessoa';
  end if;
  new.id := pg_catalog.gen_random_uuid();
  new.codigo := grupos.gera_codigo();
  new.todos_podem_desenhar := false;
  new.encerrada := false;
  new.criada_em := now();
  new.ultima_atividade := now();
  return new;
end
$$;
create trigger antes_de_criar_sala before insert on public.salas
  for each row execute function grupos.antes_de_criar_sala();

-- Sala encerrada é definitiva: vira só leitura, e nada nela muda mais.
create or replace function grupos.antes_de_mudar_sala()
returns trigger
language plpgsql security definer set search_path = ''
as $$
begin
  if old.encerrada and (new.encerrada is distinct from old.encerrada
                        or new.todos_podem_desenhar is distinct from old.todos_podem_desenhar
                        or new.lider is distinct from old.lider) then
    raise exception 'sala_encerrada' using errcode = 'P0001';
  end if;
  if new.id is distinct from old.id or new.codigo is distinct from old.codigo or new.mapa is distinct from old.mapa
     or new.cabecalho is distinct from old.cabecalho or new.criada_em is distinct from old.criada_em then
    raise exception 'coluna_imutavel' using errcode = 'P0001';
  end if;
  return new;
end
$$;
create trigger antes_de_mudar_sala before update on public.salas
  for each row execute function grupos.antes_de_mudar_sala();

-- ---------------------------------------------------------------------------
-- entrar_na_sala(codigo, nick): a ÚNICA porta de entrada em membros.
-- Devolve {ok, motivo} em vez de erro: a tentativa errada precisa ficar
-- gravada (um erro desfaria o registro e o limite de tentativas não contaria).
-- ---------------------------------------------------------------------------
create or replace function public.entrar_na_sala(p_codigo text, p_nick text)
returns jsonb
language plpgsql volatile security definer set search_path = ''
as $$
declare
  c_max_membros constant int := 10;
  c_max_erros_de_codigo constant int := 5;
  c_janela_dos_erros constant interval := interval '10 minutes';
  v_uid uuid := auth.uid();
  v_codigo text := upper(btrim(coalesce(p_codigo, '')));
  v_nick text := btrim(coalesce(p_nick, ''));
  v_sala public.salas%rowtype;
  v_erros int;
  v_total int;
begin
  if v_uid is null then
    return jsonb_build_object('ok', false, 'motivo', 'sem_login');
  end if;
  select count(*) into v_erros from grupos.tentativas t
   where t.usuario = v_uid and not t.acertou and t.em > now() - c_janela_dos_erros;
  if v_erros >= c_max_erros_de_codigo then
    return jsonb_build_object('ok', false, 'motivo', 'muitas_tentativas');
  end if;
  -- a linha da sala fica travada até o fim: duas entradas ao mesmo tempo não
  -- passam juntas do limite de membros
  select * into v_sala from public.salas s where s.codigo = v_codigo for update;
  if not found then
    insert into grupos.tentativas (usuario, acertou) values (v_uid, false);
    return jsonb_build_object('ok', false, 'motivo', 'nao_existe');
  end if;
  insert into grupos.tentativas (usuario, acertou) values (v_uid, true);
  -- quem já é membro (recarregou a página) volta sem passar pelas regras de entrada
  if not exists (select 1 from public.membros m where m.sala_id = v_sala.id and m.usuario = v_uid) then
    if v_sala.encerrada then
      return jsonb_build_object('ok', false, 'motivo', 'encerrada');
    end if;
    if exists (select 1 from grupos.expulsos e where e.sala_id = v_sala.id and e.usuario = v_uid) then
      return jsonb_build_object('ok', false, 'motivo', 'expulso');
    end if;
    if char_length(v_nick) not between 1 and 24 or v_nick !~ '^[A-Za-z0-9À-ÖØ-öø-ÿ _.-]+$' then
      return jsonb_build_object('ok', false, 'motivo', 'nick_invalido');
    end if;
    if exists (select 1 from public.membros m where m.sala_id = v_sala.id and lower(m.nick) = lower(v_nick)) then
      return jsonb_build_object('ok', false, 'motivo', 'nick_em_uso');
    end if;
    select count(*) into v_total from public.membros m where m.sala_id = v_sala.id;
    if v_total >= c_max_membros then
      return jsonb_build_object('ok', false, 'motivo', 'sala_cheia');
    end if;
    insert into public.membros (sala_id, usuario, nick, pode_desenhar)
    values (v_sala.id, v_uid, v_nick, v_sala.todos_podem_desenhar);
    update public.salas s set ultima_atividade = now() where s.id = v_sala.id;
  end if;
  return jsonb_build_object(
    'ok', true, 'sala_id', v_sala.id, 'codigo', v_sala.codigo, 'mapa', v_sala.mapa,
    'cabecalho', v_sala.cabecalho, 'lider', v_sala.lider,
    'todos_podem_desenhar', v_sala.todos_podem_desenhar, 'encerrada', v_sala.encerrada);
end
$$;
revoke all on function public.entrar_na_sala(text, text) from public, anon;
grant execute on function public.entrar_na_sala(text, text) to authenticated;

-- ---------------------------------------------------------------------------
-- Operações: forma mínima, ritmo e atividade da sala.
-- A permissão em si é a política operacoes_insere_quem_desenha (RLS).
-- ---------------------------------------------------------------------------
create or replace function grupos.antes_de_inserir_operacao()
returns trigger
language plpgsql security definer set search_path = ''
as $$
declare
  c_max_ops_por_segundo constant int := 20;
  v_n int;
begin
  if new.autor is distinct from auth.uid() then
    raise exception 'operacao_de_outro_autor' using errcode = '42501';
  end if;
  -- a forma mínima de uma operação da prancheta (metrics/tactics.py): id, tipo,
  -- autor e seq; o seq é o lamport da linha
  if coalesce(jsonb_typeof(new.op -> 'id'), '') <> 'string'
     or coalesce(jsonb_typeof(new.op -> 'tipo'), '') <> 'string'
     or coalesce(jsonb_typeof(new.op -> 'autor'), '') <> 'string'
     or coalesce(jsonb_typeof(new.op -> 'seq'), '') <> 'number' then
    raise exception 'operacao_invalida' using errcode = '22023';
  end if;
  if (new.op ->> 'id') !~ '^[0-9A-Za-z_-]{1,64}$'
     or (new.op ->> 'tipo') !~ '^[a-z0-9_]{1,32}$'
     or char_length(new.op ->> 'autor') not between 1 and 64
     or (new.op ->> 'seq') !~ '^[0-9]{1,15}$' then
    raise exception 'operacao_invalida' using errcode = '22023';
  end if;
  if (new.op ->> 'seq')::bigint <> new.lamport then
    raise exception 'operacao_invalida' using errcode = '22023';
  end if;
  -- ritmo: no máximo c_max_ops_por_segundo por autor no último segundo (em
  -- todas as salas). A trava consultiva por autor serializa duas transações
  -- dele ao mesmo tempo, para as duas não passarem juntas da conta.
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(new.autor::text, 13));
  select count(*) into v_n from public.operacoes o
   where o.autor = new.autor and o.criada_em > now() - interval '1 second';
  if v_n >= c_max_ops_por_segundo then
    raise exception 'ritmo' using errcode = 'P0001', hint = 'no máximo 20 operações por segundo';
  end if;
  new.criada_em := now();
  update public.salas s set ultima_atividade = now()
   where s.id = new.sala_id and s.ultima_atividade < now() - interval '1 minute';
  return new;
end
$$;
create trigger antes_de_inserir_operacao before insert on public.operacoes
  for each row execute function grupos.antes_de_inserir_operacao();

-- ---------------------------------------------------------------------------
-- Expulsão: quem a líder tira não volta pela mesma conta.
-- ---------------------------------------------------------------------------
create or replace function grupos.depois_de_sair()
returns trigger
language plpgsql security definer set search_path = ''
as $$
begin
  -- apagado por OUTRA pessoa (a líder): expulsão. Pela própria pessoa: saiu.
  -- A sala apagada (a limpeza de 30 dias, em cascata): nada.
  if auth.uid() is not null and auth.uid() <> old.usuario
     and exists (select 1 from public.salas s where s.id = old.sala_id) then
    insert into grupos.expulsos (sala_id, usuario) values (old.sala_id, old.usuario)
    on conflict do nothing;
  end if;
  return null;
end
$$;
create trigger depois_de_sair after delete on public.membros
  for each row execute function grupos.depois_de_sair();

-- ---------------------------------------------------------------------------
-- Limpeza: salas paradas há mais de 30 dias saem, com as operações e os
-- membros (on delete cascade). Agendada na migração 5 (pg_cron); sem ela,
-- roda à mão no SQL Editor:  select grupos.limpa_salas_antigas();
-- ---------------------------------------------------------------------------
create or replace function grupos.limpa_salas_antigas()
returns integer
language plpgsql security definer set search_path = ''
as $$
declare
  c_dias_parada constant interval := interval '30 days';
  v_n int;
begin
  delete from public.salas s where s.ultima_atividade < now() - c_dias_parada;
  get diagnostics v_n = row_count;
  delete from grupos.tentativas t where t.em < now() - interval '1 day';
  return v_n;
end
$$;
revoke all on function grupos.limpa_salas_antigas() from public, anon, authenticated;

revoke all on function grupos.antes_de_criar_sala(), grupos.antes_de_mudar_sala(),
  grupos.antes_de_inserir_operacao(), grupos.depois_de_sair() from public, anon, authenticated;
