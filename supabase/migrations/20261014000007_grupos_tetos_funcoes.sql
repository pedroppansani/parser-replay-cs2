-- =============================================================================
-- Grupos na prancheta (fase 16b, revisão de segurança: B-2, L-1, L-2, L-3, L-5) -- 7/7: funções e gatilhos.
--
-- Troca (create or replace) funções das migrações 3 e 4 e cria as novas. Todo limite é constante nomeada no
-- começo da função, com a origem:
--   MAX_OPS_POR_SALA = 5.000 e MAX_BYTES_POR_SALA = 2 MB  (o maior entre 5.000 / 2 MB e 4x o maior round real;
--       o maior round do corpus, aberto pela "Abrir round na prancheta", tem 68 operações e 88.835 bytes de
--       jsonb em 1.152 rounds -- 4x = 272 operações e 355.340 bytes --, então valem 5.000 e 2 MB; medição em
--       supabase/medicao/maior_round_na_prancheta.json, script scripts/mede_round_na_prancheta.py)
--   MAX_OPS_POR_MINUTO = 300 e MAX_OPS_POR_HORA = 3.000 por autor  (proposta da revisão, B-2)
--   MAX_SALAS_ATIVAS = 200  (200 salas x 2 MB = 400 MB, abaixo dos 500 MB do plano grátis; B-2)
--   MAX_CHAMADAS_POR_MINUTO = 30 de entrar_na_sala por conta  (B-2)
--   SALTO_DE_LAMPORT = 1.000 acima do maior da sala  (L-2)
-- Cada teto devolve um código próprio, que a tela traduz: sala_no_limite, autor_no_limite, servidor_cheio e,
-- em entrar_na_sala, o motivo muitas_chamadas.
--
-- A LISTA DE TIPOS de operação (L-3) vive em grupos.tipos_de_operacao() e é a mesma de OPERACOES em
-- dashboard/web/tactics.js e metrics/tactics.py (tests/test_grupos_migracoes.py compara as três). OPERAÇÃO NOVA
-- DA PRANCHETA EXIGE MIGRAÇÃO NOVA que troque esta função; sem isso o servidor recusa a operação.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Os tipos que o servidor aceita (L-3).
-- ---------------------------------------------------------------------------
create or replace function grupos.tipos_de_operacao()
returns text[]
language sql immutable set search_path = ''
as $$
  select array[
    'renomeia', 'cria_passo', 'renomeia_passo', 'remove_passo',
    'cria_peca', 'move_peca', 'remove_peca',
    'cria_granada', 'move_granada', 'remove_granada',
    'gira_peca', 'tira_peca',
    'cria_traco', 'remove_traco',
    'define_duracao', 'define_vida',
    'anula', 'reativa',
    'cria_caminho', 'move_ponto', 'remove_ponto', 'define_funcao', 'planta_bomba', 'nota_de_evento',
    'desenha_granada', 'define_area_desenho'
  ]::text[];
$$;
revoke all on function grupos.tipos_de_operacao() from public, anon, authenticated;

-- ---------------------------------------------------------------------------
-- A forma mínima de UMA operação (a mesma para o gatilho da tabela e para o estado inicial de cria_sala):
-- id, tipo (da lista), autor, em (texto) e seq (número inteiro de até 15 dígitos).
-- ---------------------------------------------------------------------------
create or replace function grupos.valida_operacao(p_op jsonb)
returns void
language plpgsql immutable set search_path = ''
as $$
begin
  if coalesce(jsonb_typeof(p_op), '') <> 'object'
     or coalesce(jsonb_typeof(p_op -> 'id'), '') <> 'string'
     or coalesce(jsonb_typeof(p_op -> 'tipo'), '') <> 'string'
     or coalesce(jsonb_typeof(p_op -> 'autor'), '') <> 'string'
     or coalesce(jsonb_typeof(p_op -> 'em'), '') <> 'string'
     or coalesce(jsonb_typeof(p_op -> 'seq'), '') <> 'number' then
    raise exception 'operacao_invalida' using errcode = '22023';
  end if;
  if (p_op ->> 'id') !~ '^[0-9A-Za-z_-]{1,64}$'
     or not ((p_op ->> 'tipo') = any (grupos.tipos_de_operacao()))
     or char_length(p_op ->> 'autor') not between 1 and 64
     or char_length(p_op ->> 'em') > 64
     or (p_op ->> 'seq') !~ '^[0-9]{1,15}$' then
    raise exception 'operacao_invalida' using errcode = '22023';
  end if;
end
$$;
revoke all on function grupos.valida_operacao(jsonb) from public, anon, authenticated;

-- ---------------------------------------------------------------------------
-- Criar sala (insert direto): o teto global de salas ativas (B-2) entra aqui; o resto é como na migração 3.
-- ---------------------------------------------------------------------------
create or replace function grupos.antes_de_criar_sala()
returns trigger
language plpgsql security definer set search_path = ''
as $$
declare
  c_max_salas_por_hora constant int := 5;
  c_max_salas_ativas constant int := 200;
  c_atividade_que_conta constant interval := interval '30 days';
  v_n int;
begin
  select count(*) into v_n from public.salas s
   where s.lider = new.lider and s.criada_em > now() - interval '1 hour';
  if v_n >= c_max_salas_por_hora then
    raise exception 'muitas_salas' using errcode = 'P0001',
      hint = 'no máximo 5 grupos por hora por pessoa';
  end if;
  -- duas criações ao mesmo tempo não passam juntas do teto
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('grupos.salas_ativas', 11));
  select count(*) into v_n from public.salas s where s.ultima_atividade > now() - c_atividade_que_conta;
  if v_n >= c_max_salas_ativas then
    raise exception 'servidor_cheio' using errcode = 'P0001',
      hint = 'o servidor de grupos está com 200 salas ativas';
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

-- ---------------------------------------------------------------------------
-- cria_sala(mapa, nick, estado_inicial): cria a sala e entra nela como líder, com o estado inicial da tática
-- numa linha só. estado_inicial = {"cabecalho": {...}, "operacoes": [...]}. Tudo ou nada: qualquer erro
-- desfaz a criação (a função levanta a exceção; o cliente traduz).
-- ---------------------------------------------------------------------------
create or replace function public.cria_sala(p_mapa text, p_nick text, p_estado_inicial jsonb)
returns jsonb
language plpgsql volatile security definer set search_path = ''
as $$
declare
  c_max_ops_por_sala constant int := 5000;
  c_max_bytes_por_sala constant bigint := 2097152;
  c_max_bytes_da_operacao constant int := 8192;
  c_max_bytes_do_cabecalho constant int := 8192;
  v_uid uuid := auth.uid();
  v_nick text := btrim(coalesce(p_nick, ''));
  v_cab jsonb;
  v_ops jsonb;
  v_op jsonb;
  v_n int;
  v_bytes bigint := 0;
  v_b int;
  v_maior bigint := 0;
  v_ids text[] := '{}';
  v_sala public.salas%rowtype;
begin
  if v_uid is null then
    raise exception 'sem_login' using errcode = '42501';
  end if;
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(v_uid::text, 7));
  if coalesce(p_mapa, '') !~ '^de_[a-z0-9_]{1,30}$' then
    raise exception 'mapa_invalido' using errcode = '22023';
  end if;
  if char_length(v_nick) not between 1 and 24 or v_nick !~ '^[A-Za-z0-9À-ÖØ-öø-ÿ _.-]+$' then
    raise exception 'nick_invalido' using errcode = '22023';
  end if;
  if coalesce(jsonb_typeof(p_estado_inicial), '') <> 'object'
     or coalesce(jsonb_typeof(p_estado_inicial -> 'cabecalho'), '') <> 'object'
     or coalesce(jsonb_typeof(p_estado_inicial -> 'operacoes'), '') <> 'array' then
    raise exception 'estado_invalido' using errcode = '22023';
  end if;
  v_cab := p_estado_inicial -> 'cabecalho';
  v_ops := p_estado_inicial -> 'operacoes';
  if octet_length(v_cab::text) > c_max_bytes_do_cabecalho then
    raise exception 'operacao_ate_8kb' using errcode = '23514', hint = 'o cabeçalho passa de 8 KB';
  end if;
  v_n := jsonb_array_length(v_ops);
  if v_n > c_max_ops_por_sala then
    raise exception 'sala_no_limite' using errcode = 'P0001', hint = 'no máximo 5.000 operações por sala';
  end if;
  for v_op in select e.value from jsonb_array_elements(v_ops) as e loop
    perform grupos.valida_operacao(v_op);
    v_b := octet_length(v_op::text);
    if v_b > c_max_bytes_da_operacao then
      raise exception 'operacao_ate_8kb' using errcode = '23514';
    end if;
    v_bytes := v_bytes + v_b;
    if v_bytes > c_max_bytes_por_sala then
      raise exception 'sala_no_limite' using errcode = 'P0001', hint = 'no máximo 2 MB por sala';
    end if;
    if (v_op ->> 'seq')::bigint < 1 then
      raise exception 'operacao_invalida' using errcode = '22023';
    end if;
    v_maior := greatest(v_maior, (v_op ->> 'seq')::bigint);
    v_ids := v_ids || (v_op ->> 'id');
  end loop;
  if (select count(distinct i) from unnest(v_ids) as i) <> v_n then
    raise exception 'operacao_invalida' using errcode = '22023', hint = 'ids repetidos';
  end if;
  -- o gatilho antes_de_criar_sala dá o código e confere os tetos de salas (por hora e ativas)
  insert into public.salas (lider, mapa, cabecalho, operacoes_iniciais, ids_iniciais, lamport_inicial, total_ops, total_bytes)
  values (v_uid, p_mapa, v_cab, v_ops, v_ids, v_maior, v_n, v_bytes)
  returning * into v_sala;
  insert into public.membros (sala_id, usuario, nick, pode_desenhar) values (v_sala.id, v_uid, v_nick, false);
  return jsonb_build_object(
    'ok', true, 'sala_id', v_sala.id, 'codigo', v_sala.codigo, 'mapa', v_sala.mapa,
    'cabecalho', v_sala.cabecalho, 'lider', v_sala.lider,
    'todos_podem_desenhar', v_sala.todos_podem_desenhar, 'encerrada', v_sala.encerrada);
end
$$;
revoke all on function public.cria_sala(text, text, jsonb) from public, anon;
grant execute on function public.cria_sala(text, text, jsonb) to authenticated;

-- ---------------------------------------------------------------------------
-- entrar_na_sala(codigo, nick): como na migração 3, mais:
--   L-1  trava consultiva por conta no começo: chamadas paralelas da mesma conta não passam juntas do limite
--   B-2  no máximo 30 chamadas por minuto por conta (uma linha por conta em grupos.chamadas) e a chamada CERTA
--        não grava nada em grupos.tentativas (só o código errado grava)
--   estado inicial: devolve operacoes_iniciais, a primeira parte do log
-- ---------------------------------------------------------------------------
create or replace function public.entrar_na_sala(p_codigo text, p_nick text)
returns jsonb
language plpgsql volatile security definer set search_path = ''
as $$
declare
  c_max_membros constant int := 10;
  c_max_erros_de_codigo constant int := 5;
  c_janela_dos_erros constant interval := interval '10 minutes';
  c_max_chamadas_por_minuto constant int := 30;
  c_janela_das_chamadas constant interval := interval '1 minute';
  v_uid uuid := auth.uid();
  v_codigo text := upper(btrim(coalesce(p_codigo, '')));
  v_nick text := btrim(coalesce(p_nick, ''));
  v_sala public.salas%rowtype;
  v_erros int;
  v_total int;
  v_chamadas int;
begin
  if v_uid is null then
    return jsonb_build_object('ok', false, 'motivo', 'sem_login');
  end if;
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(v_uid::text, 7));
  insert into grupos.chamadas as c (usuario, inicio, n) values (v_uid, now(), 1)
  on conflict (usuario) do update
    set inicio = case when c.inicio < now() - c_janela_das_chamadas then now() else c.inicio end,
        n = case when c.inicio < now() - c_janela_das_chamadas then 1
                 else least(c.n + 1, c_max_chamadas_por_minuto + 1) end
  returning c.n into v_chamadas;
  if v_chamadas > c_max_chamadas_por_minuto then
    return jsonb_build_object('ok', false, 'motivo', 'muitas_chamadas');
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
    'todos_podem_desenhar', v_sala.todos_podem_desenhar, 'encerrada', v_sala.encerrada,
    'operacoes_iniciais', v_sala.operacoes_iniciais);
end
$$;
revoke all on function public.entrar_na_sala(text, text) from public, anon;
grant execute on function public.entrar_na_sala(text, text) to authenticated;

-- ---------------------------------------------------------------------------
-- Operações: forma mínima (L-3), salto de Lamport (L-2), ritmo por autor em três janelas e o total da sala (B-2).
-- A permissão em si é a política operacoes_insere_quem_desenha (RLS).
-- ---------------------------------------------------------------------------
create or replace function grupos.antes_de_inserir_operacao()
returns trigger
language plpgsql security definer set search_path = ''
as $$
declare
  c_max_ops_por_segundo constant int := 20;
  c_max_ops_por_minuto constant int := 300;
  c_max_ops_por_hora constant int := 3000;
  c_max_ops_por_sala constant int := 5000;
  c_max_bytes_por_sala constant bigint := 2097152;
  c_salto_de_lamport constant bigint := 1000;
  v_seg int;
  v_min int;
  v_hora int;
  v_bytes int;
  v_maior bigint;
  v_inicial bigint;
  v_ids text[];
begin
  if new.autor is distinct from auth.uid() then
    raise exception 'operacao_de_outro_autor' using errcode = '42501';
  end if;
  -- a forma mínima de uma operação da prancheta (metrics/tactics.py): id, tipo da lista, autor, em e seq;
  -- o seq é o lamport da linha
  perform grupos.valida_operacao(new.op);
  if (new.op ->> 'seq')::bigint <> new.lamport then
    raise exception 'operacao_invalida' using errcode = '22023';
  end if;
  -- L-2: um escritor não leva o relógio de todos para um número que trava a sala
  select s.lamport_inicial, s.ids_iniciais into v_inicial, v_ids from public.salas s where s.id = new.sala_id;
  select coalesce(max(o.lamport), 0) into v_maior from public.operacoes o where o.sala_id = new.sala_id;
  if new.lamport > greatest(v_maior, coalesce(v_inicial, 0)) + c_salto_de_lamport then
    raise exception 'operacao_invalida' using errcode = '22023', hint = 'salto de Lamport acima de 1.000';
  end if;
  -- o id de uma operação do estado inicial não se repete (o índice único de operacoes não as enxerga)
  if (new.op ->> 'id') = any (coalesce(v_ids, '{}')) then
    raise exception 'duplicate key value violates unique constraint' using errcode = '23505';
  end if;
  -- ritmo por autor (em todas as salas): 20 por segundo, 300 por minuto e 3.000 por hora. A trava consultiva
  -- por autor serializa duas transações dele ao mesmo tempo, para as duas não passarem juntas da conta.
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(new.autor::text, 13));
  select count(*) filter (where o.criada_em > now() - interval '1 second'),
         count(*) filter (where o.criada_em > now() - interval '1 minute'),
         count(*)
    into v_seg, v_min, v_hora
    from public.operacoes o
   where o.autor = new.autor and o.criada_em > now() - interval '1 hour';
  if v_seg >= c_max_ops_por_segundo then
    raise exception 'ritmo' using errcode = 'P0001', hint = 'no máximo 20 operações por segundo';
  end if;
  if v_min >= c_max_ops_por_minuto then
    raise exception 'autor_no_limite' using errcode = 'P0001', hint = 'no máximo 300 operações por minuto';
  end if;
  if v_hora >= c_max_ops_por_hora then
    raise exception 'autor_no_limite' using errcode = 'P0001', hint = 'no máximo 3.000 operações por hora';
  end if;
  new.criada_em := now();
  -- o total da sala (estado inicial incluído) e a atividade, no mesmo update
  v_bytes := octet_length(new.op::text);
  update public.salas s
     set total_ops = s.total_ops + 1,
         total_bytes = s.total_bytes + v_bytes,
         ultima_atividade = case when s.ultima_atividade < now() - interval '1 minute' then now() else s.ultima_atividade end
   where s.id = new.sala_id
     and s.total_ops < c_max_ops_por_sala
     and s.total_bytes + v_bytes <= c_max_bytes_por_sala;
  if not found and exists (select 1 from public.salas s where s.id = new.sala_id) then
    raise exception 'sala_no_limite' using errcode = 'P0001', hint = 'no máximo 5.000 operações ou 2 MB por sala';
  end if;
  return new;
end
$$;

-- ---------------------------------------------------------------------------
-- Limpeza (a agendada na migração 5 chama esta): como na migração 3, mais as chamadas antigas e, L-5, os
-- usuários anônimos órfãos com mais de 2 dias (sem sala, sem grupo e sem operação: apagar quem escreveu apagaria,
-- em cascata, o histórico de uma sala que continua viva). O cliente refaz o login anônimo sozinho.
-- ---------------------------------------------------------------------------
create or replace function grupos.limpa_salas_antigas()
returns integer
language plpgsql security definer set search_path = ''
as $$
declare
  c_dias_parada constant interval := interval '30 days';
  c_idade_do_anonimo constant interval := interval '2 days';
  v_n int;
begin
  delete from public.salas s where s.ultima_atividade < now() - c_dias_parada;
  get diagnostics v_n = row_count;
  delete from grupos.tentativas t where t.em < now() - interval '1 day';
  delete from grupos.chamadas c where c.inicio < now() - interval '1 day';
  delete from auth.users u
   where u.is_anonymous and u.created_at < now() - c_idade_do_anonimo
     and not exists (select 1 from public.membros m where m.usuario = u.id)
     and not exists (select 1 from public.salas s where s.lider = u.id)
     and not exists (select 1 from public.operacoes o where o.autor = u.id);
  return v_n;
end
$$;
revoke all on function grupos.limpa_salas_antigas() from public, anon, authenticated;

revoke all on function grupos.antes_de_criar_sala(), grupos.antes_de_inserir_operacao() from public, anon, authenticated;
