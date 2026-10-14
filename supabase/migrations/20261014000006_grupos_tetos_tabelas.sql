-- =============================================================================
-- Grupos na prancheta (fase 16b, achado B-2 da revisão de segurança) -- 6/7: colunas e tabela dos tetos.
--
-- As migrações 1 a 5 ficam como estão (o projeto novo aplica todas de uma vez, em ordem). Esta e a 7 só
-- ACRESCENTAM: colunas na sala (o estado inicial da tática e os totais) e a tabela que conta as chamadas de
-- entrar_na_sala; as funções novas e as trocadas estão na 7.
--
-- O log da sala passa a ser o ESTADO INICIAL (as operações que a tática já tinha ao virar grupo, numa linha só,
-- em salas.operacoes_iniciais) seguido das linhas de `operacoes`. Nenhuma operação muda de significado
-- (decisão 47): o cliente junta as duas partes e aplica na ordem de sempre (Lamport, autor, id).
-- =============================================================================

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
