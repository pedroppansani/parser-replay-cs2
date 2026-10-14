// Confere as migrações de supabase/migrations num Postgres 17 de verdade (PGlite,
// compilado para WASM), com um "calço" do que o Supabase já traz pronto: os papéis
// anon e authenticated, auth.users e auth.uid(), realtime.messages, realtime.topic()
// e realtime.send(). É a prova local das políticas ANTES do projeto real existir;
// não substitui a parte B (tests/test_grupos_integracao.py), que roda contra o
// Supabase de verdade (o Realtime, o login anônimo e o pg_cron não estão aqui).
//
// Uso (fora do pytest; precisa de Node 20+):
//   npm install --prefix supabase/tests @electric-sql/pglite@0.3.7
//   node supabase/tests/politicas_no_pglite.mjs .
// A migração 5 (pg_cron) falha aqui de propósito: o PGlite não tem a extensão.
import { PGlite } from '@electric-sql/pglite';
import fs from 'fs';
import path from 'path';

const raiz = process.argv[2];
const db = new PGlite();
const shim = `
create role anon nologin; create role authenticated nologin;
create schema auth; create table auth.users (id uuid primary key, is_anonymous boolean not null default false, created_at timestamptz not null default now());
create function auth.uid() returns uuid language sql stable as $$ select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$;
grant usage on schema auth to authenticated, anon; grant execute on function auth.uid() to authenticated, anon;
create schema realtime;
create table realtime.messages (id bigserial primary key, topic text not null, extension text not null, payload jsonb, event text, private boolean, inserted_at timestamptz default now());
alter table realtime.messages enable row level security;
create function realtime.topic() returns text language sql stable as $$ select nullif(current_setting('realtime.topic', true), '') $$;
create function realtime.send(payload jsonb, event text, topic text, private boolean default true) returns void language sql security definer as $$
  insert into realtime.messages (topic, extension, payload, event, private) values (topic, 'broadcast', payload, event, private) $$;
grant usage on schema realtime to authenticated; grant select, insert on realtime.messages to authenticated;
grant usage on sequence realtime.messages_id_seq to authenticated;
grant execute on function realtime.topic() to authenticated;
grant usage on schema public to authenticated, anon;
create publication supabase_realtime;
`;
await db.exec(shim);
const pasta = path.join(raiz, 'supabase', 'migrations');
for (const f of fs.readdirSync(pasta).sort()) {
  const sql = fs.readFileSync(path.join(pasta, f), 'utf8');
  try { await db.exec(sql); console.log('OK   ', f); }
  catch (e) { console.log('FALHA', f, '->', e.message); }
}

let falhas = 0;
function confere(nome, cond, extra) { console.log((cond ? 'ok    ' : 'FALHOU') + ' ' + nome + (extra ? '  ' + extra : '')); if (!cond) falhas++; }
async function como(uid, sql, params = [], topico = null) {
  await db.exec(`reset role; select set_config('request.jwt.claim.sub', '${uid || ''}', false); select set_config('realtime.topic', '${topico || ''}', false); set role authenticated;`);
  try { return { linhas: (await db.query(sql, params)).rows }; }
  catch (e) { return { erro: e.message, codigo: e.code }; }
  finally { await db.exec('reset role'); }
}
const U = n => '00000000-0000-4000-8000-' + String(n).padStart(12, '0');
for (let i = 1; i <= 15; i++) await db.query('insert into auth.users values ($1)', [U(i)]);
const A = U(1), B = U(2), C = U(3), D = U(4);
let opSeq = 0;
const op = (autor, extra = {}) => { opSeq++; return JSON.stringify(Object.assign({ id: 'op' + opSeq + 'x'.repeat(10), seq: opSeq, autor, em: '2026-10-13T00:00:00Z', tipo: 'move_peca' }, extra)); };
const insereOp = (uid, sala, nick, extra) => { const o = op(nick, extra); return como(uid, 'insert into public.operacoes (sala_id, lamport, op) values ($1, $2, $3::jsonb) returning id', [sala, JSON.parse(o).seq, o]); };

// criar e entrar
let r = await como(A, "insert into public.salas (lider, mapa, cabecalho) values ($1, 'de_mirage', '{\"id\":\"t1\"}'::jsonb) returning id, codigo, todos_podem_desenhar", [A]);
confere('a líder cria a sala (código do servidor)', r.linhas && /^[ABCDEFGHJKMNPQRSTUVWXYZ23456789]{8}$/.test(r.linhas[0].codigo), JSON.stringify(r));
const sala = r.linhas[0].id, codigo = r.linhas[0].codigo;
r = await como(B, "insert into public.salas (lider, mapa, cabecalho) values ($1, 'de_mirage', '{}'::jsonb)", [A]);
confere('ninguém cria sala em nome de outra pessoa', !!r.erro, r.erro);
r = await como(A, 'select public.entrar_na_sala($1, $2) j', [codigo, 'nomad']);
confere('a líder entra', r.linhas && r.linhas[0].j.ok, JSON.stringify(r));
r = await como(B, 'select public.entrar_na_sala($1, $2) j', [codigo.toLowerCase(), 'ztrike']);
confere('membro entra (código sem caixa)', r.linhas && r.linhas[0].j.ok && r.linhas[0].j.todos_podem_desenhar === false, JSON.stringify(r));
r = await como(D, 'select public.entrar_na_sala($1, $2) j', [codigo, 'NOMAD']);
confere('nick repetido (sem caixa) é recusado', r.linhas && r.linhas[0].j.motivo === 'nick_em_uso', JSON.stringify(r));
r = await como(D, 'select public.entrar_na_sala($1, $2) j', [codigo, '<script>']);
confere('nick com < > é recusado', r.linhas && r.linhas[0].j.motivo === 'nick_invalido', JSON.stringify(r));
r = await como(D, 'select public.entrar_na_sala($1, $2) j', [codigo, 'Dé_v.1']);
confere('nick com acento entra', r.linhas && r.linhas[0].j.ok, JSON.stringify(r));

// B1: quem não é membro não lê nada
for (const t of ['salas', 'membros', 'operacoes']) {
  r = await como(C, `select count(*)::int n from public.${t}`);
  confere(`não membro não lê ${t}`, r.linhas && r.linhas[0].n === 0, JSON.stringify(r));
}
r = await insereOp(A, sala, 'nomad');
confere('a líder insere operação', !!r.linhas, JSON.stringify(r));
r = await como(B, 'select count(*)::int n from public.operacoes');
confere('membro lê as operações', r.linhas && r.linhas[0].n === 1);
// B2: membro sem permissão não insere, chamando a API direto
r = await insereOp(B, sala, 'ztrike');
confere('membro sem permissão não insere', r.erro && /row-level security/.test(r.erro), r.erro);
r = await insereOp(C, sala, 'x');
confere('não membro não insere', !!r.erro, r.erro);
r = await como(B, 'insert into public.operacoes (sala_id, autor, lamport, op) values ($1, $2, 99, $3::jsonb)', [sala, A, op('nomad', { seq: 99 })]);
confere('ninguém insere em nome de outro autor', !!r.erro, r.erro);
// B3: membro não muda pode_desenhar
r = await como(B, 'update public.membros set pode_desenhar = true where sala_id = $1 returning usuario', [sala]);
confere('membro não muda o próprio pode_desenhar', (r.linhas && r.linhas.length === 0) || !!r.erro, JSON.stringify(r));
r = await como(B, 'update public.membros set nick = $2 where sala_id = $1 returning usuario', [sala, 'outro']);
confere('membro não muda o nick depois de entrar (sem grant)', !!r.erro, r.erro);
r = await como(B, 'insert into public.membros (sala_id, usuario, nick) values ($1, $2, $3)', [sala, C, 'intruso']);
confere('ninguém insere membro direto', !!r.erro, r.erro);
r = await como(B, 'update public.salas set todos_podem_desenhar = true where id = $1 returning id', [sala]);
confere('membro não liga todos podem desenhar', (r.linhas && r.linhas.length === 0) || !!r.erro, JSON.stringify(r));
// a líder libera
r = await como(A, 'update public.membros set pode_desenhar = true where sala_id = $1 and usuario = $2 returning usuario', [sala, B]);
confere('a líder libera', r.linhas && r.linhas.length === 1, JSON.stringify(r));
r = await insereOp(B, sala, 'ztrike');
confere('membro liberado insere', !!r.linhas, JSON.stringify(r));
// B5: ninguém atualiza nem apaga operação
r = await como(A, "update public.operacoes set op = '{}'::jsonb returning id");
confere('ninguém atualiza operação (nem a líder)', !!r.erro, r.erro);
r = await como(A, 'delete from public.operacoes returning id');
confere('ninguém apaga operação (nem a líder)', !!r.erro, r.erro);
// B6: acima de 8 KB
r = await insereOp(A, sala, 'nomad', { lixo: 'x'.repeat(8200) });
confere('operação acima de 8 KB é recusada', r.erro && /operacao_ate_8kb/.test(r.erro), r.erro);
r = await insereOp(A, sala, 'nomad', { lixo: 'x'.repeat(8000) });
confere('operação de quase 8 KB passa', !!r.linhas, r.erro);
// operação malformada
r = await como(A, "insert into public.operacoes (sala_id, lamport, op) values ($1, 5000, '{\"tipo\":\"x\"}'::jsonb)", [sala]);
confere('operação sem id/seq/autor é recusada', r.erro && /operacao_invalida/.test(r.erro), r.erro);
r = await como(A, 'insert into public.operacoes (sala_id, lamport, op) values ($1, 777, $2::jsonb)', [sala, op('nomad', { seq: 778 })]);
confere('seq diferente do lamport é recusado', r.erro && /operacao_invalida/.test(r.erro), r.erro);
// unicidade
const repetida = op('nomad');
r = await como(A, 'insert into public.operacoes (sala_id, lamport, op) values ($1, $2, $3::jsonb)', [sala, JSON.parse(repetida).seq, repetida]);
r = await como(A, 'insert into public.operacoes (sala_id, lamport, op) values ($1, $2, $3::jsonb)', [sala, JSON.parse(repetida).seq, repetida]);
confere('a mesma operação duas vezes é recusada', r.erro && /duplicate|unique/.test(r.erro), r.erro);
// B7: ritmo (numa transação só: o now() é o mesmo)
await db.exec(`reset role; select set_config('request.jwt.claim.sub', '${D}', false); set role authenticated;`);
let erroRitmo = null, aceitas = 0;
await db.exec('begin');
await db.exec("set local role postgres; update public.membros set pode_desenhar = true where usuario = '" + D + "'; set local role authenticated");
for (let i = 0; i < 25; i++) {
  const o = op('Dé_v.1');
  try { await db.query('savepoint s'); await db.query('insert into public.operacoes (sala_id, lamport, op) values ($1, $2, $3::jsonb)', [sala, JSON.parse(o).seq, o]); aceitas++; await db.query('release savepoint s'); }
  catch (e) { erroRitmo = e.message; await db.query('rollback to savepoint s'); }
}
await db.exec('commit'); await db.exec('reset role');
confere('o ritmo aceita 20 e recusa o excesso', aceitas === 20 && /ritmo/.test(erroRitmo || ''), aceitas + ' aceitas; ' + erroRitmo);

// realtime.messages
r = await como(B, 'select count(*)::int n from realtime.messages', [], 'sala:' + sala);
confere('membro lê o canal da sala', r.linhas && r.linhas[0].n > 0, JSON.stringify(r));
r = await como(C, 'select count(*)::int n from realtime.messages', [], 'sala:' + sala);
confere('não membro não lê o canal da sala', r.linhas && r.linhas[0].n === 0, JSON.stringify(r));
r = await como(B, "insert into realtime.messages (topic, extension, payload) values ($1, 'presence', '{}')", ['sala:' + sala], 'sala:' + sala);
confere('membro marca presença', !r.erro, r.erro);
r = await como(B, "insert into realtime.messages (topic, extension, payload) values ($1, 'broadcast', '{}')", ['sala:' + sala], 'sala:' + sala);
confere('membro não transmite o cabeçote', !!r.erro, r.erro);
r = await como(A, "insert into realtime.messages (topic, extension, payload) values ($1, 'broadcast', '{}')", ['sala:' + sala], 'sala:' + sala);
confere('a líder transmite o cabeçote', !r.erro, r.erro);
r = await como(C, "insert into realtime.messages (topic, extension, payload) values ($1, 'presence', '{}')", ['sala:' + sala], 'sala:' + sala);
confere('não membro não marca presença', !!r.erro, r.erro);
const avisos = (await db.query("select payload from realtime.messages where event = 'mudou' and topic = $1", ['sala:' + sala])).rows;
confere('o banco avisa o canal da sala (entrada, permissão)', avisos.length >= 4, avisos.length + ' avisos');

// B8: expulsar
r = await como(A, 'delete from public.membros where sala_id = $1 and usuario = $2 returning usuario', [sala, B]);
confere('a líder expulsa', r.linhas && r.linhas.length === 1, JSON.stringify(r));
r = await como(B, 'select count(*)::int n from public.operacoes');
confere('o expulso perde a leitura', r.linhas && r.linhas[0].n === 0);
r = await insereOp(B, sala, 'ztrike');
confere('o expulso perde a escrita', !!r.erro, r.erro);
r = await como(B, 'select public.entrar_na_sala($1, $2) j', [codigo, 'ztrike2']);
confere('o expulso não volta pela mesma conta', r.linhas && r.linhas[0].j.motivo === 'expulso', JSON.stringify(r));
r = await como(D, 'delete from public.membros where sala_id = $1 and usuario = $2 returning usuario', [sala, A]);
confere('membro não expulsa a líder', (r.linhas && r.linhas.length === 0) || !!r.erro, JSON.stringify(r));
r = await como(A, 'delete from public.membros where sala_id = $1 and usuario = $2 returning usuario', [sala, A]);
confere('a líder não sai sem transferir', (r.linhas && r.linhas.length === 0) || !!r.erro, JSON.stringify(r));

// "todos podem desenhar"
const E = U(5);
r = await como(A, 'update public.salas set todos_podem_desenhar = true where id = $1 returning id', [sala]);
confere('a líder liga todos podem desenhar', r.linhas && r.linhas.length === 1, JSON.stringify(r));
r = await como(E, 'select public.entrar_na_sala($1, $2) j', [codigo, 'eve']);
r = await insereOp(E, sala, 'eve');
confere('com todos podem desenhar, quem entra desenha', !!r.linhas, r.erro);
await como(A, 'update public.salas set todos_podem_desenhar = false where id = $1', [sala]);

// B9: transferir liderança
r = await como(A, 'update public.salas set lider = $2 where id = $1 returning lider', [sala, C]);
confere('não transfere para quem não é membro', !!r.erro || (r.linhas && r.linhas.length === 0), JSON.stringify(r));
r = await como(A, 'update public.salas set lider = $2 where id = $1 returning lider', [sala, D]);
confere('a líder transfere para um membro', r.linhas && r.linhas.length === 1, JSON.stringify(r));
r = await como(A, 'update public.salas set todos_podem_desenhar = true where id = $1 returning id', [sala]);
confere('a líder antiga perde os poderes (sala)', (r.linhas && r.linhas.length === 0) || !!r.erro, JSON.stringify(r));
r = await como(A, 'update public.membros set pode_desenhar = true where sala_id = $1 returning usuario', [sala]);
confere('a líder antiga perde os poderes (membros)', (r.linhas && r.linhas.length === 0) || !!r.erro, JSON.stringify(r));
r = await insereOp(A, sala, 'nomad');
confere('a líder antiga (sem pode_desenhar) não desenha mais', !!r.erro, r.erro);
r = await como(D, 'update public.membros set pode_desenhar = true where sala_id = $1 and usuario = $2 returning usuario', [sala, A]);
confere('a líder nova libera', r.linhas && r.linhas.length === 1, JSON.stringify(r));

// B4: sala cheia e encerrada
for (let i = 6; i <= 12; i++) await como(U(i), 'select public.entrar_na_sala($1, $2)', [codigo, 'm' + i]);
r = await como(U(13), 'select public.entrar_na_sala($1, $2) j', [codigo, 'm13']);
const n = (await db.query('select count(*)::int n from public.membros where sala_id = $1', [sala])).rows[0].n;
confere('a sala para em 10 membros', n === 10 && r.linhas[0].j.motivo === 'sala_cheia', n + ' membros; ' + JSON.stringify(r));
r = await como(D, 'update public.salas set encerrada = true where id = $1 returning id', [sala]);
confere('a líder encerra', r.linhas && r.linhas.length === 1, JSON.stringify(r));
r = await como(D, 'update public.salas set encerrada = false where id = $1 returning id', [sala]);
confere('encerrar é definitivo', !!r.erro, r.erro);
r = await insereOp(D, sala, 'Dé_v.1');
confere('sala encerrada não aceita operação (nem da líder)', !!r.erro, r.erro);
await como(U(6), 'delete from public.membros where sala_id = $1 and usuario = $2', [sala, U(6)]);
r = await como(U(13), 'select public.entrar_na_sala($1, $2) j', [codigo, 'm13']);
confere('ninguém entra em sala encerrada', r.linhas && r.linhas[0].j.motivo === 'encerrada', JSON.stringify(r));
r = await como(U(6), 'select count(*)::int n from public.operacoes');
confere('quem saiu não lê mais', r.linhas && r.linhas[0].n === 0);

// adivinhar o código
let ultimo = null;
for (let i = 0; i < 6; i++) { r = await como(U(14), 'select public.entrar_na_sala($1, $2) j', ['AAAAAAA' + 'BCDEFGH'[i], 'chute']); ultimo = r.linhas[0].j.motivo; }
r = await como(U(14), 'select public.entrar_na_sala($1, $2) j', [codigo, 'chute']);
confere('5 códigos errados travam a entrada por 10 min (até com o código certo)', ultimo === 'muitas_tentativas' && r.linhas[0].j.motivo === 'muitas_tentativas', ultimo + ' / ' + JSON.stringify(r));
r = await como(U(14), 'select count(*)::int n from grupos.tentativas');
confere('ninguém lê as tentativas', !!r.erro, r.erro);
r = await como(A, 'select grupos.limpa_salas_antigas()');
confere('ninguém de fora roda a limpeza', !!r.erro, r.erro);

// limite de salas por hora
let criadas = 0, erroSalas = null;
for (let i = 0; i < 6; i++) {
  r = await como(U(15), "insert into public.salas (lider, mapa, cabecalho) values ($1, 'de_nuke', '{}'::jsonb) returning id", [U(15)]);
  if (r.linhas) criadas++; else erroSalas = r.erro;
}
confere('no máximo 5 salas por hora por pessoa', criadas === 5 && /muitas_salas/.test(erroSalas || ''), criadas + ' ' + erroSalas);

// limpeza de 30 dias
await db.query("update public.salas set ultima_atividade = now() - interval '31 days' where id = $1", [sala]);
const apagadas = (await db.query('select grupos.limpa_salas_antigas() n')).rows[0].n;
const restoOps = (await db.query('select count(*)::int n from public.operacoes where sala_id = $1', [sala])).rows[0].n;
const restoMem = (await db.query('select count(*)::int n from public.membros where sala_id = $1', [sala])).rows[0].n;
confere('a limpeza apaga a sala parada com operações e membros', apagadas === 1 && restoOps === 0 && restoMem === 0, apagadas + ' ' + restoOps + ' ' + restoMem);


// =============================================================================
// Fase 16b: tetos de uso (B-2), L-1, L-2, L-3 e L-5 (migrações 6 e 7)
// =============================================================================
let proximoUsuario = 100;
async function novoUsuario() {
  const id = U(++proximoUsuario);
  await db.query('insert into auth.users (id) values ($1)', [id]);
  return id;
}
const NICK_OK = 'lider';
const opX = (id, seq, extra = {}) => Object.assign({ id, seq, autor: 'nomad', em: '2026-10-14T00:00:00Z', tipo: 'move_peca' }, extra);
const criaSala = (uid, ops, cab = { id: 't1' }, nick = NICK_OK, mapa = 'de_mirage') =>
  como(uid, 'select public.cria_sala($1, $2, $3::jsonb) j', [mapa, nick, JSON.stringify({ cabecalho: cab, operacoes: ops })]);
const insereX = (uid, sala, o) => como(uid, 'insert into public.operacoes (sala_id, lamport, op) values ($1, $2, $3::jsonb) returning id', [sala, o.seq, JSON.stringify(o)]);
// linhas que o gatilho não vê (aqui o gatilho é o que se quer testar: o enchimento passa por fora dele)
async function enche(sala, autor, quantas, segundosAtras, lamportInicial) {
  await db.exec('reset role; set session_replication_role = replica');
  await db.query(`insert into public.operacoes (sala_id, autor, lamport, op, criada_em)
    select $1::uuid, $2::uuid, $4::bigint + g, jsonb_build_object('id', 'enc' || $2::text || g, 'tipo', 'move_peca', 'autor', 'x', 'em', '', 'seq', $4::bigint + g),
           now() - make_interval(secs => $3) from generate_series(1, $5::int) g`, [sala, autor, segundosAtras, lamportInicial, quantas]);
  await db.exec('set session_replication_role = origin');
}
const numero = async (sql, params = []) => Number((await db.query(sql, params)).rows[0].n);

// --- cria_sala: o estado inicial numa linha só ---
const L1 = await novoUsuario(), M1 = await novoUsuario();
const iniciais = [opX('ini00001', 1, { tipo: 'renomeia', titulo: 'x' }), opX('ini00002', 2, { tipo: 'cria_passo', passo: 'p1', titulo: '' }), opX('ini00003', 7)];
r = await criaSala(L1, iniciais);
confere('cria_sala cria a sala e entra como líder, com o estado inicial', r.linhas && r.linhas[0].j.ok && /^[A-Z2-9]{8}$/.test(r.linhas[0].j.codigo), JSON.stringify(r));
const salaC = r.linhas[0].j.sala_id, codigoC = r.linhas[0].j.codigo;
let linha = (await db.query('select operacoes_iniciais, lamport_inicial::int li, total_ops, total_bytes::int tb, (select nick from public.membros where sala_id = s.id and usuario = s.lider) nick, (select count(*)::int from public.operacoes where sala_id = s.id) n from public.salas s where id = $1', [salaC])).rows[0];
confere('o estado inicial fica na sala (3 operações, nenhuma linha em operacoes), com maior seq e totais', linha.operacoes_iniciais.length === 3 && linha.n === 0 && linha.li === 7 && linha.total_ops === 3 && linha.tb > 100 && linha.nick === NICK_OK, JSON.stringify(linha));
r = await como(M1, 'select public.entrar_na_sala($1, $2) j', [codigoC, 'ana']);
confere('quem entra recebe o estado inicial (operacoes_iniciais) como a primeira parte do log', r.linhas && r.linhas[0].j.ok && r.linhas[0].j.operacoes_iniciais.length === 3 && r.linhas[0].j.operacoes_iniciais[2].id === 'ini00003', JSON.stringify(r).slice(0, 200));
r = await como(L1, 'select count(*)::int n from public.salas where id = $1', [salaC]);
confere('a líder lê a sala que criou', r.linhas && r.linhas[0].n === 1);
r = await como(await novoUsuario(), 'select count(*)::int n from public.salas where id = $1', [salaC]);
confere('não membro não lê a sala (nem o estado inicial)', r.linhas && r.linhas[0].n === 0);
r = await insereX(L1, salaC, opX('ini00003', 8));
confere('operação nova com o id de uma do estado inicial é recusada (a sala continuaria abrindo)', r.erro && /duplicate|unique/.test(r.erro), r.erro);
r = await insereX(L1, salaC, opX('novo0001', 8));
confere('operação nova com id novo entra depois do estado inicial', !!r.linhas, r.erro);
confere('o total da sala conta o estado inicial e a nova operação', (await numero('select total_ops n from public.salas where id = $1', [salaC])) === 4);
const semEmIni = opX('semem001', 1); delete semEmIni.em;
for (const [nome, cab, ops, nick, esperado] of [
  ['operação sem em', {}, [semEmIni], NICK_OK, /operacao_invalida/],
  ['operação de tipo desconhecido', {}, [opX('tipo0001', 1, { tipo: 'rm_rf' })], NICK_OK, /operacao_invalida/],
  ['operação com id repetido', {}, [opX('repet001', 1), opX('repet001', 2)], NICK_OK, /operacao_invalida/],
  ['operação com seq 0', {}, [opX('seq00001', 0)], NICK_OK, /operacao_invalida/],
  ['operação acima de 8 KB', {}, [opX('grande01', 1, { lixo: 'x'.repeat(8200) })], NICK_OK, /operacao_ate_8kb/],
  ['cabeçalho acima de 8 KB', { lixo: 'x'.repeat(8300) }, [], NICK_OK, /operacao_ate_8kb/],
  ['nick inválido', {}, [], '<b>', /nick_invalido/],
]) {
  r = await criaSala(await novoUsuario(), ops, cab, nick);
  confere(`cria_sala recusa: ${nome}`, r.erro && esperado.test(r.erro), r.erro);
}
r = await como(await novoUsuario(), 'select public.cria_sala($1, $2, $3::jsonb) j', ['de_mirage', NICK_OK, '[]']);
confere('cria_sala recusa estado que não é objeto', r.erro && /estado_invalido/.test(r.erro), r.erro);
r = await criaSala(await novoUsuario(), [], {}, NICK_OK, 'mirage; drop');
confere('cria_sala recusa mapa fora do formato', r.erro && /mapa_invalido/.test(r.erro), r.erro);
await db.exec('reset role; set role anon');
r = await db.query("select public.cria_sala('de_mirage', 'x', '{}'::jsonb)").catch(e => ({ erro: e.message }));
await db.exec('reset role');
confere('o papel anon não executa cria_sala', r.erro && /permission denied/.test(r.erro), r.erro);

// --- B-2: teto por sala (operações e bytes, estado inicial incluído) ---
const mil = n => Array.from({ length: n }, (_, i) => opX('mil' + String(i).padStart(6, '0'), i + 1));
r = await criaSala(await novoUsuario(), mil(5001));
confere('cria_sala recusa 5.001 operações (sala_no_limite)', r.erro && /sala_no_limite/.test(r.erro), r.erro);
const LS = await novoUsuario();
r = await criaSala(LS, mil(4999));
confere('cria_sala aceita 4.999 operações', r.linhas && r.linhas[0].j.ok, r.erro);
const salaS = r.linhas[0].j.sala_id;
r = await insereX(LS, salaS, opX('quinto001', 5000));
confere('a sala aceita exatamente 5.000 operações', !!r.linhas, r.erro);
r = await insereX(LS, salaS, opX('quinto002', 5001));
confere('a 5.001ª operação é recusada com o código sala_no_limite', r.erro && /sala_no_limite/.test(r.erro), r.erro);
r = await criaSala(await novoUsuario(), mil(5000));
confere('cria_sala aceita exatamente 5.000 operações', r.linhas && r.linhas[0].j.ok, r.erro);
// 2 MB: 256 operações de EXATAMENTE 8.192 bytes (o texto do jsonb, medido no próprio banco) somam 2.097.152
const medida = async ops => numero('select coalesce(sum(octet_length(e::text)), 0)::bigint n from jsonb_array_elements($1::jsonb) e', [JSON.stringify(ops)]);
const opDe = async (i, bytes) => {
  const vazia = opX('gra' + String(i).padStart(6, '0'), i + 1, { lixo: '' });
  vazia.lixo = 'x'.repeat(bytes - await medida([vazia]));
  return vazia;
};
const cheias = [];
for (let i = 0; i < 256; i++) cheias.push(await opDe(i, 8192));
confere('(o enchimento de 2 MB bate no byte)', (await medida(cheias)) === 2097152, String(await medida(cheias)));
r = await criaSala(await novoUsuario(), cheias);
confere('cria_sala aceita exatamente 2 MB de operações', r.linhas && r.linhas[0].j.ok, r.erro);
const passa = cheias.slice(0, 255).concat([await opDe(300, 4096), await opDe(301, 4097)]);
confere('(o excesso é de 1 byte)', (await medida(passa)) === 2097153, String(await medida(passa)));
r = await criaSala(await novoUsuario(), passa);
confere('cria_sala recusa 2 MB mais 1 byte (sala_no_limite)', r.erro && /sala_no_limite/.test(r.erro), r.erro);
const LB = await novoUsuario();
r = await criaSala(LB, cheias.slice(0, 255));
const salaB = r.linhas[0].j.sala_id;
r = await insereX(LB, salaB, await opDe(400, 8192));
confere('a sala aceita operações até exatamente 2 MB no total', !!r.linhas && (await numero('select total_bytes n from public.salas where id = $1', [salaB])) === 2097152, r.erro);
r = await insereX(LB, salaB, opX('bytes002', 401));
confere('uma operação a mais, mesmo pequena, passa de 2 MB e é recusada (sala_no_limite)', r.erro && /sala_no_limite/.test(r.erro), r.erro);

// --- B-2: segundo teto por autor (300 por minuto, 3.000 por hora) ---
const LA = await novoUsuario();
r = await criaSala(LA, []);
const salaA = r.linhas[0].j.sala_id;
await enche(salaA, LA, 299, 30, 0);
r = await insereX(LA, salaA, opX('minuto01', 300));
confere('o autor chega a 300 operações em 1 minuto', !!r.linhas, r.erro);
r = await insereX(LA, salaA, opX('minuto02', 301));
confere('a 301ª operação em 1 minuto é recusada (autor_no_limite, por minuto)', r.erro && /autor_no_limite/.test(r.erro), JSON.stringify(r));
const LH = await novoUsuario();
r = await criaSala(LH, []);
const salaH = r.linhas[0].j.sala_id;
await enche(salaH, LH, 2999, 1800, 0);
r = await insereX(LH, salaH, opX('hora0001', 3000));
confere('o autor chega a 3.000 operações em 1 hora', !!r.linhas, r.erro);
r = await insereX(LH, salaH, opX('hora0002', 3001));
confere('a 3.001ª operação em 1 hora é recusada (autor_no_limite, por hora)', r.erro && /autor_no_limite/.test(r.erro), JSON.stringify(r));
await db.query("update public.operacoes set criada_em = now() - interval '2 hours' where autor = $1", [LH]);
r = await insereX(LH, salaH, opX('hora0003', 3001));
confere('passada a hora, o autor volta a escrever', !!r.linhas, r.erro);

// --- L-2: salto de Lamport ---
const LL = await novoUsuario();
r = await criaSala(LL, []);
const salaL = r.linhas[0].j.sala_id;
r = await insereX(LL, salaL, opX('salto001', 1001));
confere('L-2: salto de 1.001 acima do maior da sala é recusado', r.erro && /operacao_invalida/.test(r.erro), r.erro);
r = await insereX(LL, salaL, opX('salto002', 1000));
confere('L-2: salto de exatamente 1.000 é aceito', !!r.linhas, r.erro);
r = await insereX(LL, salaL, opX('salto003', 2001));
confere('L-2: 1.001 acima do novo maior é recusado', r.erro && /operacao_invalida/.test(r.erro), r.erro);
r = await insereX(LL, salaL, opX('salto004', 2000));
confere('L-2: 1.000 acima do novo maior é aceito', !!r.linhas, r.erro);
const LM = await novoUsuario();
r = await criaSala(LM, [opX('inicial01', 5000)]);
r = await insereX(LM, r.linhas[0].j.sala_id, opX('salto005', 6001));
confere('L-2: o salto também conta a partir do maior do estado inicial', r.erro && /operacao_invalida/.test(r.erro), r.erro);

// --- L-3: forma mínima e lista de tipos (a lista do SQL é conferida contra o JS e o Python em tests/test_grupos_migracoes.py) ---
const tipos = (await db.query('select unnest(grupos.tipos_de_operacao()) t')).rows.map(x => x.t);
confere('L-3: a lista de tipos tem as 26 operações da prancheta', tipos.length === 26 && new Set(tipos).size === 26, tipos.length + '');
let todosValidos = true;
for (const t of tipos) { const e = await db.query('select grupos.valida_operacao($1::jsonb)', [JSON.stringify(opX('tipo' + t, 1, { tipo: t }))]).catch(e => e); if (e.message) todosValidos = false; }
confere('L-3: cada tipo da lista passa na forma mínima', todosValidos);
const LT = await novoUsuario();
r = await criaSala(LT, []);
const salaT = r.linhas[0].j.sala_id;
const semEm = opX('semem002', 1); delete semEm.em;
r = await insereX(LT, salaT, semEm);
confere('L-3: operação sem em é recusada', r.erro && /operacao_invalida/.test(r.erro), r.erro);
r = await insereX(LT, salaT, opX('em00001', 1, { em: 12 }));
confere('L-3: em que não é texto é recusado', r.erro && /operacao_invalida/.test(r.erro), r.erro);
r = await insereX(LT, salaT, opX('tipo0002', 1, { tipo: 'move_peca2' }));
confere('L-3: tipo fora da lista é recusado', r.erro && /operacao_invalida/.test(r.erro), r.erro);
r = await insereX(LT, salaT, opX('tipo0003', 1, { tipo: 'desenha_granada' }));
confere('L-3: tipo da lista (desenha_granada) é aceito', !!r.linhas, r.erro);

// --- B-2 (d) e L-1: entrar_na_sala ---
const LE = await novoUsuario();
r = await criaSala(LE, []);
const codigoE = r.linhas[0].j.codigo;
const ME = await novoUsuario();
const tentativas = () => numero('select count(*)::int n from grupos.tentativas');
const antes = await tentativas();
for (let i = 0; i < 10; i++) r = await como(ME, 'select public.entrar_na_sala($1, $2) j', [codigoE, 'ana']);
confere('chamadas certas de entrar_na_sala não gravam em tentativas (contagem igual antes e depois)', (await tentativas()) === antes && r.linhas[0].j.ok, antes + ' -> ' + await tentativas());
const NE = await novoUsuario();
const motivos = [];
for (let i = 0; i < 31; i++) { r = await como(NE, 'select public.entrar_na_sala($1, $2) j', [codigoE, 'ana2']); motivos.push(r.linhas[0].j.motivo || 'ok'); }
confere('as 30 primeiras chamadas em 1 minuto passam e a 31ª volta muitas_chamadas', motivos.slice(0, 30).every(m => m !== 'muitas_chamadas') && motivos[30] === 'muitas_chamadas', motivos.slice(28).join(','));
confere('(o contador é uma linha por conta, não cresce)', (await numero('select count(*)::int n from grupos.chamadas where usuario = $1', [NE])) === 1);
await db.query("update grupos.chamadas set inicio = now() - interval '2 minutes' where usuario = $1", [NE]);
r = await como(NE, 'select public.entrar_na_sala($1, $2) j', [codigoE, 'ana2']);
confere('passado 1 minuto, a conta volta a chamar', r.linhas[0].j.motivo !== 'muitas_chamadas', JSON.stringify(r));
r = await como(NE, 'select count(*)::int n from grupos.chamadas');
confere('ninguém lê grupos.chamadas', !!r.erro, r.erro);
const LP = await novoUsuario();
const errados = await Promise.all(Array.from({ length: 30 }, (_, i) => como(LP, 'select public.entrar_na_sala($1, $2) j', ['ZZZZZZZ' + 'BCDEFGHJKMNPQRSTUVWXYZ23456789'[i % 30], 'x'])));
const erradosGravados = await numero('select count(*)::int n from grupos.tentativas where usuario = $1', [LP]);
const recusados = errados.filter(e => e.linhas && e.linhas[0].j.motivo === 'muitas_tentativas').length;
confere('L-1: 30 chamadas com código errado da mesma conta gravam no máximo 5 erros e as demais voltam muitas_tentativas', erradosGravados === 5 && recusados === 25, erradosGravados + ' erros; ' + recusados + ' recusadas');

// --- L-5: usuários anônimos órfãos ---
async function usuarioAnonimo(idade, anonimo = true) {
  const id = U(++proximoUsuario);
  await db.query(`insert into auth.users (id, is_anonymous, created_at) values ($1, $2, now() - interval '${idade}')`, [id, anonimo]);
  return id;
}
const orfao = await usuarioAnonimo('3 days'), novoOrfao = await usuarioAnonimo('1 day');
const comEmail = await usuarioAnonimo('3 days', false), membroVelho = await usuarioAnonimo('3 days'), liderVelho = await usuarioAnonimo('3 days'), escritorVelho = await usuarioAnonimo('3 days');
r = await criaSala(liderVelho, [], {}, 'velho');
const salaV = r.linhas[0].j.sala_id, codigoV = r.linhas[0].j.codigo;
await como(membroVelho, 'select public.entrar_na_sala($1, $2) j', [codigoV, 'mv']);
await como(escritorVelho, 'select public.entrar_na_sala($1, $2) j', [codigoV, 'ev']);
await como(liderVelho, 'update public.membros set pode_desenhar = true where sala_id = $1 and usuario = $2', [salaV, escritorVelho]);
await insereX(escritorVelho, salaV, opX('escrit001', 1));
await como(escritorVelho, 'delete from public.membros where sala_id = $1 and usuario = $2', [salaV, escritorVelho]);   // saiu, a operação dele fica
const existe = async id => (await numero('select count(*)::int n from auth.users where id = $1', [id])) === 1;
await db.query('select grupos.limpa_salas_antigas()');
confere('L-5: o anônimo órfão com mais de 2 dias sai', !(await existe(orfao)));
confere('L-5: o órfão com menos de 2 dias fica', await existe(novoOrfao));
confere('L-5: o usuário que não é anônimo fica', await existe(comEmail));
confere('L-5: o membro de uma sala fica', await existe(membroVelho));
confere('L-5: a líder de uma sala fica', await existe(liderVelho));
confere('L-5: quem escreveu numa sala viva fica (apagá-lo apagaria a operação, em cascata)', await existe(escritorVelho)
  && (await numero('select count(*)::int n from public.operacoes where sala_id = $1', [salaV])) === 1);

// --- B-2: teto global de salas ativas (200) ---
const ativasSql = "select count(*)::int n from public.salas where ultima_atividade > now() - interval '30 days'";
let criadasNoTeto = 0, erroTeto = null;
while (criadasNoTeto < 300) {
  r = await criaSala(await novoUsuario(), []);
  if (r.erro) { erroTeto = r.erro; break; }
  criadasNoTeto++;
}
confere('a sala 201 ativa é recusada (servidor_cheio) e há exatamente 200 ativas', /servidor_cheio/.test(erroTeto || '') && (await numero(ativasSql)) === 200, (await numero(ativasSql)) + ' ativas; ' + erroTeto);
const ultimoU = await novoUsuario();
r = await como(ultimoU, "insert into public.salas (lider, mapa, cabecalho) values ($1, 'de_nuke', '{}'::jsonb)", [ultimoU]);
confere('o insert direto de sala também para no teto global', r.erro && /servidor_cheio/.test(r.erro), r.erro);
await db.query("update public.salas set ultima_atividade = now() - interval '31 days' where id = (select id from public.salas order by criada_em desc limit 1)");
r = await criaSala(await novoUsuario(), []);
confere('uma sala parada há mais de 30 dias deixa de contar para o teto', !!(r.linhas && r.linhas[0].j.ok), r.erro);

console.log(falhas ? `\n${falhas} FALHA(S)` : '\nTUDO OK');
