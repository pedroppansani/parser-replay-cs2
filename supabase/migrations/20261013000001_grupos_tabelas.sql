-- =============================================================================
-- Grupos na prancheta (fase 13, item 13.1) -- 1/5: tabelas.
--
-- A sala só TRANSPORTA as operações que a prancheta já tem (decisões 32 e 35):
-- o servidor guarda o log, nunca o estado. O que fica guardado é o mínimo:
-- o nick que a pessoa escolheu, a participação na sala e as operações da
-- tática. Nada de e-mail, senha ou dado pessoal (o login é anônimo).
--
-- Tudo o que muda no banco passa por estas migrações (supabase/migrations/).
-- Os números (10 membros, 20 operações por segundo, 8 KB, 30 dias) estão
-- repetidos em dashboard/web/sala.js e em notas/seguranca/grupos.md; há teste
-- conferindo que os três dizem o mesmo (tests/test_grupos_config.py).
-- =============================================================================

-- O schema das funções auxiliares das políticas. Ele NÃO é exposto pela API
-- (o PostgREST expõe só `public` e `graphql_public`): as funções daqui não
-- viram RPC.
create schema if not exists grupos;

-- ---------------------------------------------------------------------------
-- salas: uma por grupo. O código é gerado NO SERVIDOR (gatilho na migração 3),
-- 8 caracteres de um alfabeto de 31 sem ambíguos (sem 0/O e 1/I/L):
-- 31^8 = 852.891.037.441 códigos possíveis.
-- ---------------------------------------------------------------------------
create table public.salas (
  id                   uuid primary key default gen_random_uuid(),
  codigo               text not null unique
                       check (codigo ~ '^[ABCDEFGHJKMNPQRSTUVWXYZ23456789]{8}$'),
  lider                uuid not null references auth.users (id) on delete cascade,
  mapa                 text not null check (mapa ~ '^de_[a-z0-9_]{1,30}$'),
  -- o cabeçalho do documento da tática (id, calibração do radar, origem do
  -- round...): o que não é operação e quem entra precisa para montar a mesma
  -- tática. Mesmo limite de tamanho de uma operação.
  cabecalho            jsonb not null
                       check (jsonb_typeof(cabecalho) = 'object' and octet_length(cabecalho::text) <= 8192),
  todos_podem_desenhar boolean not null default false,
  encerrada            boolean not null default false,
  criada_em            timestamptz not null default now(),
  ultima_atividade     timestamptz not null default now()
);
create index salas_ultima_atividade on public.salas (ultima_atividade);
create index salas_lider_criada_em on public.salas (lider, criada_em);

-- ---------------------------------------------------------------------------
-- membros: quem está na sala. Entra-se SÓ pela função entrar_na_sala.
-- O nick: de 1 a 24 caracteres, letras (com acento), números, espaço, _ . -
-- -- nada de < > & " ' (a tela passa todo nick pelo esc() também).
-- ---------------------------------------------------------------------------
create table public.membros (
  sala_id       uuid not null references public.salas (id) on delete cascade,
  usuario       uuid not null references auth.users (id) on delete cascade,
  nick          text not null
                check (char_length(nick) between 1 and 24
                       and nick = btrim(nick)
                       and nick ~ '^[A-Za-z0-9À-ÖØ-öø-ÿ _.-]+$'),
  pode_desenhar boolean not null default false,
  entrou_em     timestamptz not null default now(),
  primary key (sala_id, usuario)
);
-- dois membros com o mesmo nick na mesma sala confundiriam o "X moveu Y" e o
-- autor das operações (desfazer vale só sobre operação do MESMO autor)
create unique index membros_nick_unico on public.membros (sala_id, lower(nick));
create index membros_usuario on public.membros (usuario);

-- ---------------------------------------------------------------------------
-- operacoes: o log, imutável (ninguém atualiza nem apaga; desfazer é uma
-- operação anula/reativa, como já é na prancheta).
-- `lamport` é o número de ordem (`seq`) da própria operação; o par
-- (autor, lamport) é único na sala, e o id da operação também.
-- ---------------------------------------------------------------------------
create table public.operacoes (
  id        bigserial primary key,
  sala_id   uuid not null references public.salas (id) on delete cascade,
  autor     uuid not null default auth.uid() references auth.users (id) on delete cascade,
  lamport   bigint not null check (lamport > 0),
  op        jsonb not null,
  criada_em timestamptz not null default now(),
  unique (sala_id, autor, lamport),
  -- 8 KB medidos no texto do jsonb (o que o Postgres devolve). O cliente confere
  -- a mesma medida antes de enviar (sala.js, tamanhoNoServidor).
  constraint operacao_ate_8kb check (octet_length(op::text) <= 8192),
  constraint operacao_e_objeto check (jsonb_typeof(op) = 'object')
);
create unique index operacoes_id_da_operacao on public.operacoes (sala_id, (op ->> 'id'));
create index operacoes_sala_lamport on public.operacoes (sala_id, lamport);
create index operacoes_sala_criada_em on public.operacoes (sala_id, criada_em);
create index operacoes_autor_criada_em on public.operacoes (autor, criada_em);

-- ---------------------------------------------------------------------------
-- Tabelas internas (sem política nenhuma: ninguém de fora lê nem escreve).
-- ---------------------------------------------------------------------------
-- tentativas de entrar: o limite contra adivinhar o código
create table grupos.tentativas (
  usuario uuid not null,
  em      timestamptz not null default now(),
  acertou boolean not null
);
create index tentativas_usuario_em on grupos.tentativas (usuario, em);

-- quem a líder expulsou não volta pela mesma conta
create table grupos.expulsos (
  sala_id uuid not null references public.salas (id) on delete cascade,
  usuario uuid not null,
  em      timestamptz not null default now(),
  primary key (sala_id, usuario)
);

-- ---------------------------------------------------------------------------
-- RLS ligado em TODAS as tabelas: sem política, nega tudo.
-- ---------------------------------------------------------------------------
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
