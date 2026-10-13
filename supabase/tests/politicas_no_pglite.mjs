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
create schema auth; create table auth.users (id uuid primary key);
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

console.log(falhas ? `\n${falhas} FALHA(S)` : '\nTUDO OK');
