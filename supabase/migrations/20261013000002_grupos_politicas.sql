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
