# Revisão de segurança: grupos na prancheta (fase 13, item 13.7)

Para o agente `seguranca`. O Pedro leva este arquivo até ele. **`GRUPOS_ATIVOS` só vira `True` depois do
veredito LIBERADO** e da confirmação do Pedro; até lá o botão não aparece no site publicado
(`scripts/grupos_config.py`). Decisão de projeto: [47](../decisoes/47-grupos-na-prancheta.md).

## 1. O que é

Uma pessoa cria um grupo (uma sala) a partir de uma tática da prancheta e vira a líder. Os outros entram
por link ou código e veem a tática ao vivo. A líder escolhe quem pode alterar a tática. O servidor é o
Supabase (plano gratuito): Postgres, Realtime e login anônimo. **As permissões são do servidor (Row Level
Security)**; a tela só espelha.

A sala só transporta as operações do log da prancheta (decisões 32 e 35). Nenhuma operação muda de
significado; o servidor não interpreta peça, granada nem passo.

Arquivos: `supabase/migrations/` (sete migrações: 1 a 5 da fase 13; 6 e 7 da fase 16b, os tetos de uso), `dashboard/web/sala.js` (cliente; `SalaSupabase` e
`SalaFalsa`), `dashboard/web/grupo.js` (a aba e a ligação com a prancheta), `scripts/grupos_config.py`
(configuração e chave), `dashboard/web/vendor/supabase-js-2.117.2.js` (+ `.sha256`).

## 2. O que fica guardado, por quanto tempo e quem lê

| Dado | Onde | Quem lê | Quanto tempo |
|---|---|---|---|
| Usuário anônimo (uuid, sem e-mail, sem senha) | `auth.users` (Supabase Auth) | ninguém pela API | a limpeza diária apaga o anônimo com mais de 2 dias que não é membro, líder nem autor de operação em sala nenhuma (L-5) |
| Sala: código, líder (uuid), mapa, cabeçalho da tática (id, calibração, origem do round), **o estado inicial da tática (as operações que ela já tinha ao virar grupo, numa linha só, até 2 MB)**, os totais de operações e bytes, "todos podem desenhar", encerrada, datas | `public.salas` | membros da sala (e a líder) | apagada com 30 dias sem atividade |
| Membro: sala, uuid, **nick** (1 a 24 caracteres), pode desenhar, data de entrada | `public.membros` | membros da mesma sala | sai ao sair, ao ser expulso, ou com a sala |
| Operações da tática (o log; até 8 KB cada) | `public.operacoes` | membros da sala | com a sala; ninguém atualiza nem apaga antes |
| Tentativas de entrar com código ERRADO (uuid, horário; a chamada certa não grava nada) | `grupos.tentativas` | ninguém pela API | 1 dia (limpeza) |
| Chamadas de `entrar_na_sala` por conta (uma linha por conta: início da janela de 1 minuto e quantas) | `grupos.chamadas` | ninguém pela API | 1 dia (limpeza) |
| Expulsos (sala, uuid) | `grupos.expulsos` | ninguém pela API | com a sala |
| Presença (quem está online) e o cabeçote da líder | Realtime (Presence e Broadcast) | membros conectados ao canal | não fica guardado |

A tela diz, perto do botão: "O servidor guarda só o nick que você escolher, quem está em cada grupo e as
alterações da tática. O login é anônimo: sem e-mail, sem senha. Grupo parado há 30 dias é apagado."

## 3. O que a chave pública permite e o que não permite

A URL do projeto e a chave **publishable** (ou a anon antiga) vão para o build: são públicas por desenho.
Com elas, qualquer pessoa pode:

- criar um usuário anônimo (limite do Supabase: 30 por hora por IP);
- como usuário anônimo (papel `authenticated`), fazer exatamente o que as políticas abaixo deixam: criar
  sala (no máximo 5 por hora), entrar com código e nick, ler o que é da sala onde é membro, escrever
  operação onde pode desenhar, e as ações de líder na sala onde é líder.

Não permite: ler nada de sala onde não é membro; inserir membro sem passar por `entrar_na_sala`; mudar a
própria permissão; atualizar ou apagar operação; ler as tabelas do schema `grupos`; rodar a limpeza.
O papel `anon` (sem login) não tem privilégio nenhum nas tabelas.

A chave **secreta** do Supabase (`sb_secret_…`, e a antiga do papel de serviço) **não é usada em lugar
nenhum**: nem no repositório, nem no build, nem no CI, nem em log. `scripts/grupos_config.py` recusa no
build uma chave que não seja pública, e `tests/test_grupos_config.py::test_nenhuma_chave_secreta_no_repositorio_nem_no_docs`
varre todos os arquivos do repositório e do `docs/` atrás da palavra do papel de serviço, de `sb_secret_`
e de qualquer JWT cujo papel não seja `anon`.

## 4. O SQL das políticas e da função `entrar_na_sala`

Copiado das migrações (é o que roda). RLS ligado e privilégios:

```sql
alter table public.salas      enable row level security;
alter table public.membros    enable row level security;
alter table public.operacoes  enable row level security;
alter table grupos.tentativas enable row level security;
alter table grupos.expulsos   enable row level security;

-- Privilégios: o Supabase dá tudo a anon/authenticated nas tabelas de public
-- por padrão. Aqui começa do zero e devolve só o que as políticas usam --
-- inclusive por COLUNA no update (a líder muda só estas colunas).
revoke all on public.salas, public.membros, public.operacoes from anon, authenticated;
revoke all on all tables in schema grupos from anon, authenticated, public;
revoke all on schema grupos from anon, authenticated, public;
grant usage on schema grupos to authenticated;   -- as políticas chamam funções daqui

grant select on public.salas to authenticated;
grant insert (lider, mapa, cabecalho) on public.salas to authenticated;
grant update (todos_podem_desenhar, encerrada, lider) on public.salas to authenticated;

grant select on public.membros to authenticated;
grant update (pode_desenhar) on public.membros to authenticated;
grant delete on public.membros to authenticated;
-- sem insert em membros: entra-se pela função

grant select on public.operacoes to authenticated;
grant insert (sala_id, autor, lamport, op) on public.operacoes to authenticated;
grant usage on sequence public.operacoes_id_seq to authenticated;
-- sem update nem delete em operacoes: o log é imutável
```

As políticas (migração 2, inteira):

```sql
-- =============================================================================
-- Grupos na prancheta (fase 13, item 13.1) -- 2/5: políticas (RLS).
--
-- As permissões são garantidas AQUI, no servidor; a tela só as espelha.
-- As funções auxiliares são `security definer` para consultar membros e salas
-- sem cair de novo no RLS (política que lê a própria tabela recursa), com
-- `search_path` vazio (todo nome qualificado) e `stable`.
-- =============================================================================

-- A pessoa logada é membro da sala?
create or replace function grupos.eh_membro(p_sala uuid)
returns boolean
language sql stable security definer set search_path = ''
as $$
  select exists (select 1 from public.membros m where m.sala_id = p_sala and m.usuario = auth.uid());
$$;

-- A pessoa logada é a líder da sala?
create or replace function grupos.eh_lider(p_sala uuid)
returns boolean
language sql stable security definer set search_path = ''
as $$
  select exists (select 1 from public.salas s where s.id = p_sala and s.lider = auth.uid());
$$;

-- A pessoa logada pode alterar a tática da sala agora? A sala não está
-- encerrada E (é a líder, OU é membro com pode_desenhar, OU é membro e a sala
-- tem "todos podem desenhar").
create or replace function grupos.pode_desenhar(p_sala uuid)
returns boolean
language sql stable security definer set search_path = ''
as $$
  select exists (
    select 1 from public.salas s
     where s.id = p_sala and not s.encerrada
       and (s.lider = auth.uid()
            or exists (select 1 from public.membros m
                        where m.sala_id = s.id and m.usuario = auth.uid()
                          and (m.pode_desenhar or s.todos_podem_desenhar))));
$$;

revoke all on function grupos.eh_membro(uuid), grupos.eh_lider(uuid), grupos.pode_desenhar(uuid) from public, anon;
grant execute on function grupos.eh_membro(uuid), grupos.eh_lider(uuid), grupos.pode_desenhar(uuid) to authenticated;

-- ---------------------------------------------------------------------------
-- salas
-- ---------------------------------------------------------------------------
-- lê só quem é membro (a líder também enxerga a sala que acabou de criar,
-- antes de entrar nela como membro)
create policy salas_le_membro on public.salas
  for select to authenticated
  using (grupos.eh_membro(id) or lider = (select auth.uid()));

-- insere só com lider = a própria pessoa (o código e os padrões são do gatilho)
create policy salas_insere_lider on public.salas
  for insert to authenticated
  with check (lider = (select auth.uid()));

-- atualiza só a líder (as colunas permitidas estão no grant da migração 1:
-- todos_podem_desenhar, encerrada e lider). Na transferência, a linha nova
-- precisa apontar para alguém que é membro da sala.
create policy salas_atualiza_lider on public.salas
  for update to authenticated
  using (lider = (select auth.uid()))
  with check (exists (select 1 from public.membros m where m.sala_id = salas.id and m.usuario = salas.lider));

-- ninguém apaga sala pela API (a limpeza de 30 dias roda como dona do banco)

-- ---------------------------------------------------------------------------
-- membros
-- ---------------------------------------------------------------------------
-- lê só quem é membro da mesma sala
create policy membros_le_membro on public.membros
  for select to authenticated
  using (grupos.eh_membro(sala_id));

-- pode_desenhar só a líder muda (a coluna é a única com grant de update)
create policy membros_atualiza_lider on public.membros
  for update to authenticated
  using (grupos.eh_lider(sala_id))
  with check (grupos.eh_lider(sala_id));

-- apagar: a líder expulsa (outra pessoa) ou a própria pessoa sai. A líder não
-- sai sem antes transferir a liderança ou encerrar o grupo.
create policy membros_apaga on public.membros
  for delete to authenticated
  using ((grupos.eh_lider(sala_id) and usuario <> (select auth.uid()))
         or (usuario = (select auth.uid()) and not grupos.eh_lider(sala_id)));

-- sem política de insert: entra-se só por public.entrar_na_sala (migração 3)

-- ---------------------------------------------------------------------------
-- operacoes
-- ---------------------------------------------------------------------------
-- lê só quem é membro
create policy operacoes_le_membro on public.operacoes
  for select to authenticated
  using (grupos.eh_membro(sala_id));

-- insere só a própria operação, com a sala aberta e permissão de desenhar
create policy operacoes_insere_quem_desenha on public.operacoes
  for insert to authenticated
  with check (autor = (select auth.uid()) and grupos.pode_desenhar(sala_id));

-- sem política de update nem de delete: o log é imutável
```

A função `entrar_na_sala` (migração 3), a única porta de entrada em `membros`:

```sql
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
```

O gatilho das operações (forma mínima, ritmo de 20 por segundo e atividade da sala):

```sql
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
```

O Realtime: o canal é privado, tópico `sala:<id>`, e a entrada é autorizada pelo RLS de
`realtime.messages` (no painel, "Allow public access" desligado: passo 4 do cartão 10 em
`notas/PENDENCIAS_PARA_O_PEDRO.md`). As operações chegam por Postgres Changes em `public.operacoes`, com o
RLS de leitura conferido pelo Realtime para cada assinante.

```sql
create or replace function grupos.sala_do_topico(p_topico text)
returns uuid
language sql immutable set search_path = ''
as $$
  select case when p_topico ~ '^sala:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
              then substr(p_topico, 6)::uuid end;
$$;

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
```

Os demais gatilhos (código gerado no servidor, sala encerrada definitiva, expulsão registrada, aviso ao
canal e limpeza) estão em `supabase/migrations/20261013000003_grupos_funcoes.sql` e
`20261013000004_grupos_realtime.sql`. Toda função `security definer` tem `search_path = ''` e nomes
qualificados (teste `tests/test_grupos_migracoes.py::test_security_definer_sempre_com_search_path_fixo`).

## 4.1 O SQL dos tetos de uso (fase 16b: migrações 6 e 7)

A revisão de 2026-10-13 deu BLOQUEADO (relatório fora do repositório, `Base-Seguranca/projetos/parser-cs2-grupos.md`).
Esta fase fecha B-2 e os itens L-1, L-2, L-3 e L-5 **sem editar as migrações 1 a 5**: a 6 acrescenta colunas e
uma tabela, a 7 troca (`create or replace`) as funções da migração 3 e cria as novas. O log da sala passa a ser
o **estado inicial** (`salas.operacoes_iniciais`, uma linha) **seguido** das linhas de `operacoes`; nenhuma
operação muda de significado (decisão 47).

Colunas e tabela (migração 6):

```sql
alter table public.salas
  -- as operações da tática no momento de criar o grupo (forma validada no servidor, cada uma com até 8 KB)
  add column operacoes_iniciais jsonb not null default '[]'::jsonb
    constraint salas_operacoes_iniciais_e_lista check (jsonb_typeof(operacoes_iniciais) = 'array'),
  -- os ids dessas operações: uma operação nova com o mesmo id repetiria a do estado inicial (o índice único de
  -- `operacoes` não as enxerga) e a sala deixaria de abrir para quem entra
  add column ids_iniciais text[] not null default '{}',
  -- o maior número de ordem (seq) do estado inicial: o salto de Lamport (L-2) conta a partir dele
  add column lamport_inicial bigint not null default 0,
  -- o total da sala (inclui o estado inicial): o teto por sala (B-2) é conferido no gatilho da operação
  add column total_ops int not null default 0,
  add column total_bytes bigint not null default 0;

-- chamadas de entrar_na_sala por conta: UMA linha por conta (a janela de 1 minuto recomeça na primeira chamada
-- depois dela); as chamadas CERTAS não gravam mais nada em `tentativas` (B-2 d: o loop de chamadas certas
-- enchia o banco)
create table grupos.chamadas (
  usuario uuid primary key,
  inicio  timestamptz not null default now(),
  n       int not null default 0
);
alter table grupos.chamadas enable row level security;
revoke all on grupos.chamadas from anon, authenticated, public;
```

Funções (migração 7, copiadas):

```sql
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
```

## 5. Ameaças, defesa e teste

Os testes são de três níveis: **A** = parte A da fase 13, na suíte e no CI (`SalaFalsa`, que aplica as
mesmas regras no navegador); **P** = `supabase/tests/politicas_no_pglite.mjs`, as migrações aplicadas num
Postgres 17 de verdade (PGlite) com um calço do Supabase, mais de 120 casos, chamado por
`tests/test_grupos_migracoes.py::test_politicas_rodam_num_postgres_de_verdade` quando o Node e o PGlite
estão instalados; **B** = parte B, `tests/test_grupos_integracao.py`, contra o projeto real (pula sem
configuração; roda depois do cartão 10).

| Ameaça | Defesa | Teste |
|---|---|---|
| Quem não é membro lendo a sala (operações, membros, sala, canal) | Políticas `*_le_membro` com `grupos.eh_membro`; canal privado com `grupos_membro_le_o_canal` | P "não membro não lê salas/membros/operacoes", "não membro não lê o canal"; B1 |
| Membro desenhando sem permissão, inclusive chamando a API direto | `operacoes_insere_quem_desenha`: `autor = auth.uid()` e `grupos.pode_desenhar` (líder, `pode_desenhar` ou "todos podem desenhar", e sala aberta) | A `test_sem_permissao_a_alteracao_e_recusada_desfeita_e_a_dica_diz_o_motivo`; P "membro sem permissão não insere", "ninguém insere em nome de outro autor"; B2 |
| Escalar a própria permissão (pode_desenhar, todos podem, liderança, entrar como membro sem a função) | `grant update (pode_desenhar)` só passa pela política da líder; `salas_atualiza_lider`; sem grant de insert em membros | P "membro não muda o próprio pode_desenhar", "membro não liga todos podem desenhar", "ninguém insere membro direto", "não transfere para quem não é membro"; B3, B9 |
| Inundar a sala | Gatilho de ritmo: 20 operações por segundo por autor (trava consultiva por autor); 5 salas por hora por pessoa; o cliente manda em lotes dentro do ritmo | P "o ritmo aceita 20 e recusa o excesso", "no máximo 5 salas por hora"; A `test_cair_perder_50_operacoes_e_voltar_sem_duplicar` (lotes); B7 |
| Operação gigante | `check (octet_length(op::text) <= 8192)` (8 KB); o cliente mede igual antes de enviar e não manda | P "operação acima de 8 KB é recusada"; B6 |
| Log adulterado depois de gravado | Sem grant nem política de update/delete em `operacoes`; `unique (sala_id, autor, lamport)` e id único da operação | P "ninguém atualiza/apaga operação (nem a líder)", "a mesma operação duas vezes é recusada"; `test_log_imutavel_sem_update_nem_delete_em_operacoes`; B5 |
| Injeção no nick | No banco: check de 1 a 24 caracteres só com letras, números, espaço, `_ . -`; na tela: todo nick passa por `MapCore.esc()` e a dica usa `textContent` | P "nick com < > é recusado"; A `test_nick_e_dado_nunca_marcacao` (com o check do servidor desligado, a tela mostra o texto literal e não cria elemento) |
| Adivinhar o código da sala | 8 caracteres de 31 (sem 0/O, 1/I/L): 31^8 = 852.891.037.441 códigos, gerados no servidor com `gen_random_uuid()`; `entrar_na_sala` trava a pessoa depois de 5 códigos errados em 10 minutos (a tentativa errada é gravada; a função devolve o motivo em vez de erro, para o registro não ser desfeito) | P "5 códigos errados travam a entrada por 10 min" |
| Código de uma sala de OUTRO mapa digitado na página errada | Nenhuma função nova: `entrar_na_sala` já devolve o `mapa` (só a quem acertou o código, o mesmo que já recebia o cabeçalho) e entra a pessoa como membro; a página, se o mapa for outro, navega para `prancheta_<mapa>.html#sala=CODIGO&nick=NICK` (o mapa só vira endereço se casar com `^de_[a-z0-9_]{1,30}$`, o check de `salas.mapa`). Na página certa a entrada se repete e é idempotente: quem já é membro volta sem recontar nick nem o limite de 10. Código errado continua não revelando nada e contando como tentativa errada. O nick vai na URL só nesse salto e a página o tira da barra | `tests/test_grupos_mapas.py` |
| Expulso voltando | `grupos.expulsos` preenchido por gatilho quando a líder apaga o membro; `entrar_na_sala` recusa | A `test_todos_podem_desenhar_libera_todos_e_expulsar_tira_o_acesso_na_hora`; P "o expulso não volta pela mesma conta"; B8 |
| Sala encerrada sendo alterada | `pode_desenhar` exige sala aberta; gatilho torna o encerramento definitivo; ninguém entra | P "sala encerrada não aceita operação", "encerrar é definitivo", "ninguém entra em sala encerrada"; A `test_a_lider_cria_pela_aba_e_controla_o_grupo`; B4 |
| Vazamento de chave | Só a chave pública vai para o build; o build recusa chave secreta; o teste varre repositório e `docs/`; o `.env` está no `.gitignore`; no CI são variáveis do repositório, não código | `tests/test_grupos_config.py` (`test_o_build_recusa_chave_que_nao_e_publica`, `test_nenhuma_chave_secreta_no_repositorio_nem_no_docs`, `test_env_e_node_modules_fora_do_git`) |
| Código de terceiro trocado (supabase-js) | Versão exata, baixada uma vez do registro do npm (shasum do tarball conferido), sha256 gravado ao lado e conferido em todo build; servido do próprio site, nunca de CDN; carregado só ao criar ou entrar | `test_supabase_js_confere_com_o_sha256_gravado`, `test_criar_grupo_carrega_o_supabase_js_so_na_hora_e_fora_do_ar_avisa` |
| Membro transmitindo cabeçote falso | `grupos_lider_transmite`: só a líder insere Broadcast no canal | P "membro não transmite o cabeçote"; A `test_so_a_lider_transmite_o_cabecote` |
| Esgotar banco, Realtime e MAU com uma conta só (B-2) | Total por sala (5.000 operações / 2 MB, estado inicial incluído, `sala_no_limite`); segundo teto por autor (300 operações por minuto e 3.000 por hora, `autor_no_limite`); teto global de 200 salas ativas (`servidor_cheio`); `entrar_na_sala` limitada a 30 chamadas por minuto por conta (`muitas_chamadas`) e sem gravar a chamada certa. Cada teto tem a sua frase na tela | P "a sala aceita exatamente 5.000 operações", "a 5.001ª operação é recusada", "cria_sala aceita exatamente 2 MB", "2 MB mais 1 byte", "o autor chega a 300 operações em 1 minuto", "a 301ª...", "a 3.001ª...", "a sala 201 ativa é recusada", "chamadas certas de entrar_na_sala não gravam em tentativas", "a 31ª volta muitas_chamadas"; A `tests/test_grupos_tetos_browser.py` (`test_teto_da_sala...`, `test_teto_por_autor...`, `test_teto_global...`, `test_teto_de_chamadas...`); `tests/test_grupos_migracoes.py::test_os_tetos_vem_da_medicao_do_maior_round_real` |
| Criar grupo de uma tática grande demorava minutos com os tetos novos | O estado inicial sobe numa linha só, em `cria_sala(mapa, nick, estado_inicial)`, validado no servidor; depois dele, só as operações novas | A `test_criar_sobe_o_estado_inicial_numa_linha_so...`, `test_criar_grupo_do_maior_round_real_leva_ate_10_segundos_em_fast_4g`; P os `cria_sala recusa: ...` |
| Chamadas paralelas da mesma conta passando juntas do limite de erros (L-1) | `pg_advisory_xact_lock` por conta no começo de `entrar_na_sala` | P "L-1: 30 chamadas com código errado da mesma conta gravam no máximo 5 erros" (no PGlite as chamadas são sequenciais: o paralelo de verdade é a B18) |
| Escritor que leva o Lamport de todos para um número que trava a sala (L-2) | Gatilho: `lamport <= maior da sala (estado inicial incluído) + 1.000` | P "L-2: salto de 1.001...recusado", "salto de exatamente 1.000 é aceito"; A `test_l2_salto_de_lamport_acima_de_1000_e_recusado` |
| Operação sem `em` ou de tipo qualquer que impede a sala de abrir para quem entra (L-3) | `grupos.valida_operacao`: `em` texto, tipo na lista fechada; operação nova com o id de uma do estado inicial é recusada | P "L-3: ..."; `test_a_lista_de_tipos_do_servidor_e_a_do_javascript_e_a_do_python`; A `test_l3_...` |
| Anônimos órfãos acumulando em `auth.users` (L-5) | A limpeza diária apaga o anônimo com mais de 2 dias sem sala, grupo nem operação; o cliente confere a sessão guardada (`getUser`) e refaz o login anônimo sozinho | P "L-5: ..."; A `test_l5_com_a_sessao_apagada_no_servidor_o_proximo_entrar_refaz_o_login_sozinho`, `test_l5_supabase_js_confere_a_sessao_guardada_e_refaz_o_login` |
| Página sem grupo vazando pedido de rede | Nada de rede até "Criar grupo" ou "Entrar" | A `test_sem_grupo_aberto_nenhum_pedido_de_rede_a_mais_e_o_supabase_js_fica_fora`, `test_o_link_da_sala_abre_a_aba_com_o_codigo` |

## 6. O que NÃO é coberto

- **Quem tem o link entra.** O link (ou o código) é o convite. Não há lista de convidados nem aprovação
  da líder. A líder pode expulsar, e o expulso não volta pela mesma conta anônima, mas pode criar outra
  conta anônima (limite de 30 por hora por IP) e entrar de novo com o código. Contra isso, a líder
  encerra o grupo e cria outro.
- **O autor escrito dentro da operação** (`op.autor`, o nick) não é conferido contra o nick do membro: o
  autor real é a coluna `autor` (uuid), conferida pelo RLS. Quem pode desenhar pode escrever outro nick
  dentro da operação e, com isso, desfazer operação de outra pessoa (o desfazer vale para operação do
  mesmo `op.autor`). Isso não dá poder novo: quem pode desenhar já pode apagar qualquer peça. A tela
  usa sempre o próprio nick, e os nicks são únicos na sala (sem diferença de caixa).
- **O tipo da operação** é conferido contra uma lista fechada (L-3, fase 16b: `grupos.tipos_de_operacao()`,
  as 26 operações de `OPERACOES` em `tactics.js` e `metrics/tactics.py`, com um teste que compara as três).
  **Operação nova da prancheta exige migração nova** que troque essa função; sem ela o servidor recusa a
  operação (`operacao_invalida`). O servidor continua sem interpretar a tática: só confere a forma mínima
  (id, tipo da lista, autor, `em` em texto, `seq`).
- **Expulsão e Realtime:** o Realtime guarda a autorização do canal até o JWT expirar ou ser renovado
  (documentação "Realtime Authorization"). As operações (Postgres Changes) param na hora, porque o RLS é
  conferido a cada mensagem; a presença e o cabeçote da líder podem continuar chegando ao expulso até o
  token renovar (1 hora, no padrão do Supabase). A tela do expulso sai do canal sozinha ao receber o
  aviso.
- **Os avisos do banco ao canal** (`realtime.send`) dizem a quem está na sala o uuid de quem entrou,
  saiu ou mudou de permissão. É dado da própria sala.
- **CAPTCHA no login anônimo:** a documentação do Supabase recomenda; não está ligado.
- **Uma operação muito grande de uma tática de round** (o caminho de um jogador com mais de ~8 KB, 3 dos
  1.152 rounds do corpus medidos no texto do jsonb) impede essa tática de virar grupo; a tela diz por quê.
- **Projeto pausado por inatividade** (plano gratuito): a tela mostra "Grupo indisponível agora"; os
  dados voltam quando o Pedro retoma o projeto.
- **A parte B ainda não rodou** (depende do projeto real). As políticas foram exercitadas no PGlite com
  um calço do Supabase; o Realtime, o login anônimo, o pg_cron e a origem `file://` só se conferem lá.

## 7. Os números

10 membros por sala; 20 operações por segundo por autor; 8 KB por operação; 30 dias sem atividade até a
limpeza; 5 códigos errados em 10 minutos travam a entrada; 5 salas por hora por pessoa; código de 8
caracteres de 31. Fase 16b (B-2, L-2): **5.000 operações e 2 MB por sala** (o estado inicial conta; o teto é o
maior entre 5.000 operações / 2 MB e 4 vezes o maior round real: o maior round do corpus, medido nos 1.152 rounds
abertos pela "Abrir round na prancheta", tem 68 operações e 88.835 bytes de jsonb, 4 vezes dá 272 e 355.340;
`supabase/medicao/maior_round_na_prancheta.json`, `scripts/mede_round_na_prancheta.py`); **300 operações por
minuto e 3.000 operações por hora por autor**; **200 salas ativas** no servidor (200 x 2 MB = 400 MB, abaixo
dos 500 MB do plano grátis); **30 chamadas por minuto** de `entrar_na_sala` por conta; salto de Lamport de no
máximo **1.000** acima do maior da sala. O mesmo número está no banco, no cliente (`sala.js`) e aqui (teste
`tests/test_grupos_migracoes.py::test_limites_iguais_no_banco_no_cliente_e_no_documento`).
