"""Grupos na prancheta (fase 13, item 13.6, parte B): integração contra o projeto REAL do Supabase.

Pula sem configuração (SUPABASE_URL e SUPABASE_ANON_KEY no ambiente ou no .env) e sem o pedido explícito
GRUPOS_INTEGRACAO=1: cada rodada cria usuários anônimos de verdade (o Supabase limita a 30 por hora por IP),
então não roda na suíte comum nem no CI. Roda só localmente, depois do cartão 10 de
notas/PENDENCIAS_PARA_O_PEDRO.md:

    $env:GRUPOS_INTEGRACAO = "1"; py -3.12 -m pytest tests/test_grupos_integracao.py -v

Os usuários anônimos vivem em clientes do supabase-js separados dentro de uma página servida por http (sem
sessão guardada), e as chamadas são as da API, sem passar pela tela -- é o que um atacante faria.
"""
from __future__ import annotations

import http.server
import json
import os
import statistics
import threading
from functools import partial
from pathlib import Path

import pytest

from scripts import grupos_config as gc

RAIZ = Path(__file__).resolve().parents[1]
MAPA = "de_mirage"


def _config():
    amb = dict(gc.le_env())
    amb.update({k: v for k, v in os.environ.items() if k in ("SUPABASE_URL", "SUPABASE_ANON_KEY") and v})
    return amb.get("SUPABASE_URL"), amb.get("SUPABASE_ANON_KEY")


URL, CHAVE = _config()
pytestmark = pytest.mark.skipif(
    not (URL and CHAVE and os.environ.get("GRUPOS_INTEGRACAO") == "1"),
    reason="parte B: precisa do projeto real (SUPABASE_URL e SUPABASE_ANON_KEY) e de GRUPOS_INTEGRACAO=1")

sync_api = pytest.importorskip("playwright.sync_api")
from tests.test_tactics_browser import navegador  # noqa: E402,F401

# Clientes anônimos independentes (sem sessão guardada) e atalhos para as chamadas.
CLIENTES_JS = r"""
window.__novo = async function (nome) {
  const c = supabase.createClient(window.__URL, window.__CHAVE,
    { auth: { persistSession: false, autoRefreshToken: false, storageKey: 'teste-' + nome } });
  const r = await c.auth.signInAnonymously();
  if (r.error) throw new Error('login anônimo: ' + r.error.message);
  c.__uid = r.data.user.id;
  return c;
};
window.__u = {};
window.__op = function (c, seq, extra) {
  return Object.assign({ id: c.__uid.replace(/-/g, '').slice(0, 20) + 's' + seq, seq, autor: 'teste', em: new Date().toISOString(),
                         tipo: 'renomeia', titulo: 't' + seq }, extra || {});
};
"""


@pytest.fixture(scope="module")
def site_real(tmp_path_factory):
    from scripts.build_tactics_page import arquivo_da_pagina, build_html
    raiz = tmp_path_factory.mktemp("site_real")
    (raiz / "vendor").mkdir()
    (raiz / "vendor" / gc.ARQUIVO_SUPABASE_JS).write_bytes(gc.confere_biblioteca().read_bytes())
    pagina = arquivo_da_pagina(MAPA)
    cfg = gc.configuracao(None, pagina, ambiente={"SUPABASE_URL": URL, "SUPABASE_ANON_KEY": CHAVE}, ativos=True)
    (raiz / pagina).write_text(build_html(MAPA, grupo=cfg), encoding="utf-8")
    cfg_arquivo = dict(cfg, arquivoLocal=True)
    (raiz / "arquivo.html").write_text(build_html(MAPA, grupo=cfg_arquivo), encoding="utf-8")
    (raiz / "api.html").write_text(
        f'<!doctype html><meta charset="utf-8"><script src="vendor/{gc.ARQUIVO_SUPABASE_JS}"></script>', encoding="utf-8")
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), partial(http.server.SimpleHTTPRequestHandler, directory=str(raiz)))
    srv.RequestHandlerClass.log_message = lambda *a: None
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield {"base": f"http://127.0.0.1:{srv.server_address[1]}", "pagina": pagina, "raiz": raiz}
    srv.shutdown()


@pytest.fixture(scope="module")
def api(navegador, site_real):
    ctx = navegador.new_context()
    pg = ctx.new_page()
    pg.goto(site_real["base"] + "/api.html")
    pg.evaluate(f"() => {{ window.__URL = {URL!r}; window.__CHAVE = {CHAVE!r}; }}")
    pg.evaluate(CLIENTES_JS)
    # uma sala com a líder L, o membro M (sem permissão) e o de fora F
    pg.evaluate("""async () => {
      const U = window.__u;
      for (const n of ['L', 'M', 'F', 'N']) U[n] = await window.__novo(n);
      const s = await U.L.from('salas').insert({ lider: U.L.__uid, mapa: 'de_mirage', cabecalho: { id: 'integracao' } })
        .select('id,codigo').single();
      if (s.error) throw new Error(s.error.message);
      window.__sala = s.data;
      for (const [n, nick] of [['L', 'lider'], ['M', 'membro'], ['N', 'novo']]) {
        const e = await U[n].rpc('entrar_na_sala', { p_codigo: s.data.codigo, p_nick: nick });
        if (e.error || !e.data.ok) throw new Error('entrar: ' + JSON.stringify(e));
      }
      const o = window.__op(U.L, 1);
      const r = await U.L.from('operacoes').insert({ sala_id: s.data.id, lamport: 1, op: o });
      if (r.error) throw new Error(r.error.message);
    }""")
    yield pg
    ctx.close()


def js(pg, corpo):
    return pg.evaluate("async () => { const U = window.__u, S = window.__sala; " + corpo + " }")


def test_b1_quem_nao_e_membro_nao_le_nada(api):
    r = js(api, """const out = {};
      for (const t of ['salas', 'membros', 'operacoes']) out[t] = (await U.F.from(t).select('*').eq(t === 'salas' ? 'id' : 'sala_id', S.id)).data.length;
      return out;""")
    assert r == {"salas": 0, "membros": 0, "operacoes": 0}


def test_b2_membro_sem_permissao_nao_insere_pela_api(api):
    r = js(api, "return (await U.M.from('operacoes').insert({ sala_id: S.id, lamport: 1, op: window.__op(U.M, 1) })).error;")
    assert r and r["code"] == "42501"


def test_b3_membro_nao_muda_pode_desenhar(api):
    r = js(api, """await U.M.from('membros').update({ pode_desenhar: true }).eq('sala_id', S.id);
      return (await U.L.from('membros').select('usuario,pode_desenhar').eq('sala_id', S.id)).data.filter((m) => m.pode_desenhar).length;""")
    assert r == 0


def test_b5_ninguem_atualiza_nem_apaga_operacao(api):
    r = js(api, """const a = await U.L.from('operacoes').update({ op: {} }).eq('sala_id', S.id).select();
      const b = await U.L.from('operacoes').delete().eq('sala_id', S.id).select();
      const n = (await U.L.from('operacoes').select('id').eq('sala_id', S.id)).data.length;
      return [!!a.error || a.data.length === 0, !!b.error || b.data.length === 0, n];""")
    assert r[0] and r[1] and r[2] >= 1


def test_b6_operacao_acima_de_8_kb_e_recusada(api):
    r = js(api, "return (await U.L.from('operacoes').insert({ sala_id: S.id, lamport: 2, op: window.__op(U.L, 2, { lixo: 'x'.repeat(8300) }) })).error;")
    assert r and "operacao_ate_8kb" in (r.get("message") or "")


def test_b7_o_ritmo_recusa_o_excesso(api):
    r = js(api, """const lote = []; for (let i = 0; i < 25; i++) lote.push({ sala_id: S.id, lamport: 100 + i, op: window.__op(U.L, 100 + i) });
      return (await U.L.from('operacoes').insert(lote)).error;""")
    assert r and "ritmo" in (r.get("message") or "")


def test_b8_expulso_perde_leitura_e_escrita(api):
    r = js(api, """await U.L.from('membros').update({ pode_desenhar: true }).eq('sala_id', S.id).eq('usuario', U.N.__uid);
      const antes = (await U.N.from('operacoes').insert({ sala_id: S.id, lamport: 1, op: window.__op(U.N, 1) })).error;
      await U.L.from('membros').delete().eq('sala_id', S.id).eq('usuario', U.N.__uid);
      const le = (await U.N.from('operacoes').select('id').eq('sala_id', S.id)).data.length;
      const escreve = (await U.N.from('operacoes').insert({ sala_id: S.id, lamport: 2, op: window.__op(U.N, 2) })).error;
      const volta = (await U.N.rpc('entrar_na_sala', { p_codigo: S.codigo, p_nick: 'novo2' })).data;
      return { antes: !antes, le, escreve: !!escreve, volta: volta.motivo };""")
    assert r == {"antes": True, "le": 0, "escreve": True, "volta": "expulso"}


def test_b9_transferir_lideranca(api):
    r = js(api, """const t = await U.L.from('salas').update({ lider: U.M.__uid }).eq('id', S.id).select();
      const velha = await U.L.from('salas').update({ todos_podem_desenhar: true }).eq('id', S.id).select();
      const nova = await U.M.from('salas').update({ todos_podem_desenhar: false }).eq('id', S.id).select();
      await U.M.from('salas').update({ lider: U.L.__uid }).eq('id', S.id);
      return { transferiu: !t.error && t.data.length === 1, velha: velha.data.length, nova: nova.data.length };""")
    assert r == {"transferiu": True, "velha": 0, "nova": 1}


def test_b4_sala_cheia_e_sala_encerrada(api):
    r = js(api, """const s = (await U.L.from('salas').insert({ lider: U.L.__uid, mapa: 'de_mirage', cabecalho: {} }).select('id,codigo').single()).data;
      await U.L.rpc('entrar_na_sala', { p_codigo: s.codigo, p_nick: 'lider' });
      for (let i = 0; i < 9; i++) { const c = await window.__novo('x' + i); await c.rpc('entrar_na_sala', { p_codigo: s.codigo, p_nick: 'm' + i }); }
      const extra = await window.__novo('extra');
      const cheia = (await extra.rpc('entrar_na_sala', { p_codigo: s.codigo, p_nick: 'onze' })).data.motivo;
      await U.L.from('salas').update({ encerrada: true }).eq('id', S.id);
      const encerrada = (await extra.rpc('entrar_na_sala', { p_codigo: S.codigo, p_nick: 'tarde' })).data.motivo;
      return { cheia, encerrada };""")
    assert r == {"cheia": "sala_cheia", "encerrada": "encerrada"}


def _abre(navegador, url):
    ctx = navegador.new_context(viewport={"width": 1300, "height": 950})
    pg = ctx.new_page()
    pg.goto(url)
    pg.wait_for_function("() => Prancheta._interno.S.estado !== null && !!document.getElementById('pr-painel-grupo')")
    pg.evaluate("() => Prancheta._interno.abaDoPainel('grupo')")
    return ctx, pg


def test_b10_duas_janelas_na_mesma_sala(navegador, site_real):
    url = site_real["base"] + "/" + site_real["pagina"]
    c1, lider = _abre(navegador, url)
    c2, membro = _abre(navegador, url)
    try:
        lider.fill("#gr-nick", "lider")
        lider.click('[data-acao="criar"]')
        lider.wait_for_function("() => Grupo._interno.G().fase === 'dentro'", timeout=20000)
        codigo = lider.inner_text("#gr-codigo-sala")
        membro.fill("#gr-nick", "membro")
        membro.fill("#gr-codigo", codigo)
        membro.click('[data-acao="entrar"]')
        membro.wait_for_function("() => Grupo._interno.G().fase === 'dentro'", timeout=20000)
        tempos = []
        for i in range(20):
            # a líder renomeia a tática (uma operação renomeia, pelo campo da aba Tática)
            t0 = lider.evaluate(f"""() => {{ const t = document.getElementById('pr-titulo'); t.value = 'envio {i}';
                t.dispatchEvent(new Event('change')); return Date.now(); }}""")
            membro.wait_for_function(f"() => Prancheta._interno.S.estado.titulo === 'envio {i}'", timeout=10000)
            tempos.append(membro.evaluate("() => Date.now()") - t0)
            lider.wait_for_timeout(120)
        assert statistics.median(tempos) < 2000, tempos
        # a líder dá e tira a permissão: as ferramentas do membro acompanham
        membro_uid = membro.evaluate("() => Grupo._interno.G().uid")
        lider.click(f'.gr-membro[data-usuario="{membro_uid}"] [data-acao="permite"]')
        membro.wait_for_function("() => !document.querySelector('#pr-barra [data-ferramenta=\"caneta\"]').disabled", timeout=10000)
        lider.click(f'.gr-membro[data-usuario="{membro_uid}"] [data-acao="permite"]')
        membro.wait_for_function("() => document.querySelector('#pr-barra [data-ferramenta=\"caneta\"]').disabled", timeout=10000)
        lider.click('[data-acao="encerrar"]')
        lider.click('[data-acao="confirma-encerrar"]')
    finally:
        c1.close(); c2.close()


def test_b11_aberta_como_arquivo(navegador, site_real):
    """Registra se o grupo funciona com a página aberta como arquivo (origem nula). Se passar, a decisão 47
    manda trocar GRUPOS_NO_ARQUIVO_LOCAL para True."""
    ctx = navegador.new_context()
    pg = ctx.new_page()
    try:
        # como o build_site publica: o supabase-js em vendor/, ao lado da página
        pg.goto((site_real["raiz"] / "arquivo.html").as_uri())
        pg.wait_for_function("() => !!document.getElementById('pr-painel-grupo')")
        pg.evaluate("() => Prancheta._interno.abaDoPainel('grupo')")
        pg.fill("#gr-nick", "arquivo")
        pg.click('[data-acao="criar"]')
        pg.wait_for_function("() => Grupo._interno.G().fase !== 'entrando'", timeout=20000)
        assert pg.evaluate("() => Grupo._interno.G().fase") == "dentro", pg.inner_text("#pr-painel-grupo")
        pg.click('[data-acao="encerrar"]')
        pg.click('[data-acao="confirma-encerrar"]')
    finally:
        ctx.close()


# =====================================================================================================================
# Parte B ampliada (fase 16b; condição 3 do relatório de segurança de 2026-10-13): B12 a B19, mais a medição do tempo
# de criar um grupo a partir do maior round real. Roda depois dos passos do Pedro no Supabase real (cartão 10 e as
# migrações 1 a 7 aplicadas). Cada teste usa a sala e as contas DELE (a sala do módulo acima fica encerrada pelo B4).
# =====================================================================================================================

REALTIME_JS = r"""
// assina um canal e devolve o estado final ('SUBSCRIBED' ou o erro), guardando o que chega em window.__rec[nome]
window.__rec = {};
window.__canal = async function (nome, c, topico, privado, ops) {
  ops = ops || {};
  window.__rec[nome] = { status: null, insert: [], mudou: [], cabecote: [] };
  await c.realtime.setAuth();
  const ch = c.channel(topico, { config: { private: privado, broadcast: { self: false } } });
  if (ops.postgres) ch.on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'operacoes', filter: 'sala_id=eq.' + ops.postgres },
                          (p) => window.__rec[nome].insert.push(p.new.id));
  ch.on('broadcast', { event: 'mudou' }, (p) => window.__rec[nome].mudou.push(p.payload));
  ch.on('broadcast', { event: 'cabecote' }, (p) => window.__rec[nome].cabecote.push(p.payload));
  const estado = await new Promise((ok) => {
    const t = setTimeout(() => ok('TIMEOUT'), 12000);
    ch.subscribe((s) => { if (['SUBSCRIBED', 'CHANNEL_ERROR', 'TIMED_OUT', 'CLOSED'].includes(s)) { clearTimeout(t); ok(s); } });
  });
  window.__rec[nome].status = estado;
  window.__rec[nome].canal = ch;
  return estado;
};
window.__espera = (ms) => new Promise((ok) => setTimeout(ok, ms));
"""

JANELA_DE_ENTREGA_MS = 6000     # quanto esperar por uma mensagem que DEVE chegar; a que não deve chegar espera o mesmo


@pytest.fixture(scope="module")
def api2(navegador, site_real):
    """Uma sala só desta bateria: a líder L2, o membro M2 (sem permissão) e o de fora F2; criada por cria_sala."""
    ctx = navegador.new_context()
    pg = ctx.new_page()
    pg.goto(site_real["base"] + "/api.html")
    pg.evaluate(f"() => {{ window.__URL = {URL!r}; window.__CHAVE = {CHAVE!r}; }}")
    pg.evaluate(CLIENTES_JS)
    pg.evaluate(REALTIME_JS)
    pg.evaluate("""async () => {
      const U = window.__u;
      for (const n of ['L2', 'M2', 'F2']) U[n] = await window.__novo(n);
      const op = window.__op(U.L2, 1, { tipo: 'renomeia', titulo: 'b12' });
      const r = await U.L2.rpc('cria_sala', { p_mapa: 'de_mirage', p_nick: 'lider2', p_estado_inicial: { cabecalho: { id: 'b12' }, operacoes: [op] } });
      if (r.error || !r.data.ok) throw new Error('cria_sala: ' + JSON.stringify(r));
      window.__sala2 = r.data;
      const e = await U.M2.rpc('entrar_na_sala', { p_codigo: r.data.codigo, p_nick: 'membro2' });
      if (e.error || !e.data.ok) throw new Error('entrar: ' + JSON.stringify(e));
    }""")
    yield pg
    pg.evaluate("""async () => { try { await window.__u.L2.from('salas').update({ encerrada: true }).eq('id', window.__sala2.sala_id); } catch (e) {} }""")
    ctx.close()


def js2(pg, corpo):
    return pg.evaluate("async () => { const U = window.__u, S = window.__sala2, esp = window.__espera; " + corpo + " }")


def _db():
    """Conexão direta ao Postgres do projeto (opcional): SUPABASE_DB_URL no ambiente ou no .env. É a connection string do
    banco, um segredo do Pedro: nunca no repositório. Sem ela (ou sem o psycopg), o que depende dela pula."""
    amb = dict(gc.le_env())
    amb.update({k: v for k, v in os.environ.items() if k == "SUPABASE_DB_URL" and v})
    url = amb.get("SUPABASE_DB_URL")
    if not url:
        pytest.skip("sem SUPABASE_DB_URL (a connection string do banco, só no ambiente ou no .env)")
    psycopg = pytest.importorskip("psycopg", reason="pip install psycopg[binary] (só para esta parte da parte B)")
    return psycopg.connect(url, autocommit=True)


def test_b12_nao_membro_nao_recebe_postgres_changes_de_operacoes(api2):
    """Um não membro assinando Postgres Changes de operacoes com sala_id=eq.<id> não recebe NENHUM INSERT enquanto um
    membro recebe (o Realtime confere o RLS de leitura da tabela para cada assinante)."""
    r = js2(api2, """
      const topico = 'sala:' + S.sala_id;
      const membro = await window.__canal('membro', U.M2, topico, true, { postgres: S.sala_id });
      // o de fora tenta o mesmo filtro, num canal NÃO privado de outro tópico (o do tópico da sala ele nem consegue abrir: B13)
      const fora = await window.__canal('fora', U.F2, 'fora-' + S.sala_id, false, { postgres: S.sala_id });
      await esp(1500);
      const ins = await U.L2.from('operacoes').insert({ sala_id: S.sala_id, lamport: 2, op: window.__op(U.L2, 2, { titulo: 'b12-insert' }) });
      await esp(""" + str(JANELA_DE_ENTREGA_MS) + """);
      return { membro, fora, erro: ins.error && ins.error.message, membroRecebeu: window.__rec.membro.insert.length, foraRecebeu: window.__rec.fora.insert.length };""")
    assert r["erro"] is None and r["membro"] == "SUBSCRIBED", r
    assert r["membroRecebeu"] == 1 and r["foraRecebeu"] == 0, r


def test_b13_nao_membro_nao_entra_no_canal_privado_e_o_canal_publico_nao_entrega(api2):
    """Não membro não entra no canal privado `sala:<id>`; entrar com canal NÃO privado no mesmo tópico não entrega nada nem
    deixa enviar (com "Allow public access" do Realtime DESLIGADO, passo do cartão 10)."""
    r = js2(api2, """
      const topico = 'sala:' + S.sala_id;
      const lider = await window.__canal('lider', U.L2, topico, true);
      const membro = await window.__canal('membro13', U.M2, topico, true);
      const foraPrivado = await window.__canal('foraPrivado', U.F2, topico, true);
      const foraPublico = await window.__canal('foraPublico', U.F2, topico, false);
      await esp(1000);
      // a líder transmite o cabeçote no canal privado: o membro recebe, os de fora não
      window.__rec.lider.canal.send({ type: 'broadcast', event: 'cabecote', payload: { t: 7 } });
      // o de fora tenta enviar pelo canal público: ninguém do canal privado pode receber
      window.__rec.foraPublico.canal.send({ type: 'broadcast', event: 'cabecote', payload: { t: 99 } });
      await esp(""" + str(JANELA_DE_ENTREGA_MS) + """);
      const r = (n) => window.__rec[n].cabecote.map((p) => p.t);
      return { lider, membro, foraPrivado, foraPublico, membroRecebeu: r('membro13'), foraPrivadoRecebeu: r('foraPrivado'),
               foraPublicoRecebeu: r('foraPublico') };""")
    assert r["lider"] == "SUBSCRIBED" and r["membro"] == "SUBSCRIBED", r
    assert r["foraPrivado"] != "SUBSCRIBED", r                      # o canal privado recusa quem não é membro
    assert r["membroRecebeu"] == [7], r                              # só o cabeçote da líder; o 99 do de fora não chega
    assert r["foraPrivadoRecebeu"] == [] and r["foraPublicoRecebeu"] == [], r


def test_b14_membro_recebe_o_mudou_do_banco_e_so_a_lider_emite_cabecote(api2):
    """O membro recebe o broadcast `mudou` que o banco manda (realtime.send, por gatilho) e só a líder consegue emitir
    `cabecote`: o cabeçote de um membro não chega à líder."""
    r = js2(api2, """
      const topico = 'sala:' + S.sala_id;
      const lider = await window.__canal('lider14', U.L2, topico, true);
      const membro = await window.__canal('membro14', U.M2, topico, true);
      await esp(1000);
      // a líder libera o membro: o gatilho avisa o canal da sala
      const up = await U.L2.from('membros').update({ pode_desenhar: true }).eq('sala_id', S.sala_id).eq('usuario', U.M2.__uid).select();
      window.__rec.membro14.canal.send({ type: 'broadcast', event: 'cabecote', payload: { t: 55 } });   // o membro NÃO pode
      window.__rec.lider14.canal.send({ type: 'broadcast', event: 'cabecote', payload: { t: 11 } });    // a líder pode
      await esp(""" + str(JANELA_DE_ENTREGA_MS) + """);
      await U.L2.from('membros').update({ pode_desenhar: false }).eq('sala_id', S.sala_id).eq('usuario', U.M2.__uid);
      return { lider, membro, linhas: up.data && up.data.length,
               mudou: window.__rec.membro14.mudou.map((m) => [m.tabela, m.evento, m.pode_desenhar]),
               liderRecebeuCabecote: window.__rec.lider14.cabecote.map((p) => p.t), membroRecebeuCabecote: window.__rec.membro14.cabecote.map((p) => p.t) };""")
    assert r["lider"] == "SUBSCRIBED" and r["membro"] == "SUBSCRIBED" and r["linhas"] == 1, r
    assert ["membros", "UPDATE", True] in r["mudou"], r
    assert r["membroRecebeuCabecote"] == [11], r                       # o da líder chegou
    assert 55 not in r["liderRecebeuCabecote"], r                      # o do membro, não


def test_b15_os_tetos_de_uso_respondem_como_no_pglite(navegador, site_real, api2):
    """B-2 contra o servidor real: teto por sala (estado inicial incluído), por autor (300 por minuto), de chamadas de
    entrar_na_sala (30 por minuto) e, com GRUPOS_B15_GLOBAL=1, o global de 200 salas ativas (enche o servidor: depois, no
    SQL Editor, `delete from public.salas where cabecalho->>'id' = 'b15-global';`)."""
    r = js2(api2, """
      const op = (c, seq, extra) => window.__op(c, seq, extra || {});
      const L = await window.__novo('b15'); const out = {};
      const mil = (n) => Array.from({ length: n }, (_, i) => Object.assign(op(L, i + 1), { id: 'b15m' + String(i).padStart(6, '0') }));
      const cria = (ops) => L.rpc('cria_sala', { p_mapa: 'de_mirage', p_nick: 'b15', p_estado_inicial: { cabecalho: { id: 'b15' }, operacoes: ops } });
      // por sala: 5.001 operações no estado inicial é recusado; 4.999 passa, a 5.000ª entra e a 5.001ª não
      out.cria5001 = ((await cria(mil(5001))).error || {}).message || 'aceita';
      const cheia = await cria(mil(4999));
      out.cria4999 = !!(cheia.data && cheia.data.ok);
      const id = cheia.data.sala_id;
      out.quinto = ((await L.from('operacoes').insert({ sala_id: id, lamport: 5000, op: op(L, 5000) })).error || {}).message || 'aceita';
      out.sexto = ((await L.from('operacoes').insert({ sala_id: id, lamport: 5001, op: op(L, 5001) })).error || {}).message || 'aceita';
      return out;""")
    assert "sala_no_limite" in r["cria5001"] and r["cria4999"] and r["quinto"] == "aceita" and "sala_no_limite" in r["sexto"], r

    # por autor: 300 por minuto (em lotes de 20, no ritmo do servidor); a 301ª é recusada com o código próprio
    r = js2(api2, """
      const L = await window.__novo('b15autor'); const out = { erros: [] };
      const s = (await L.rpc('cria_sala', { p_mapa: 'de_mirage', p_nick: 'b15a', p_estado_inicial: { cabecalho: { id: 'b15a' }, operacoes: [] } })).data;
      let seq = 0, aceitas = 0, t0 = Date.now();
      while (aceitas < 300 && Date.now() - t0 < 50000) {
        const lote = []; for (let i = 0; i < 20; i++) { seq++; lote.push({ sala_id: s.sala_id, lamport: seq, op: window.__op(L, seq) }); }
        const e = (await L.from('operacoes').insert(lote)).error;
        if (e) out.erros.push(e.message); else aceitas += 20;
        await esp(1100);
      }
      seq++;
      out.aceitas = aceitas;
      out.a301 = ((await L.from('operacoes').insert({ sala_id: s.sala_id, lamport: seq, op: window.__op(L, seq) })).error || {}).message || 'aceita';
      out.dentroDoMinuto = Date.now() - t0 < 60000;
      return out;""")
    assert r["aceitas"] == 300 and r["dentroDoMinuto"], r
    assert "autor_no_limite" in r["a301"], r

    # chamadas de entrar_na_sala: 30 por minuto por conta; a 31ª volta muitas_chamadas
    r = js2(api2, """
      const L = await window.__novo('b15chamadas'); const out = [];
      const s = (await L.rpc('cria_sala', { p_mapa: 'de_mirage', p_nick: 'b15c', p_estado_inicial: { cabecalho: { id: 'b15c' }, operacoes: [] } })).data;
      for (let i = 0; i < 31; i++) out.push(((await L.rpc('entrar_na_sala', { p_codigo: s.codigo, p_nick: 'b15c' })).data || {}).motivo || 'ok');
      return { motivos: out, codigo: s.codigo };""")
    assert r["motivos"][:30] == ["ok"] * 30 and r["motivos"][30] == "muitas_chamadas", r


def test_b15_a_chamada_certa_de_entrar_na_sala_nao_cresce_a_tabela_tentativas(api2):
    """B-2 (d): 30 chamadas certas não gravam nada em grupos.tentativas (precisa de SUPABASE_DB_URL: a tabela não é lida pela API)."""
    banco = _db()
    with banco.cursor() as cur:
        cur.execute("select count(*) from grupos.tentativas")
        antes = cur.fetchone()[0]
    js2(api2, """
      const L = await window.__novo('b15tent');
      const s = (await L.rpc('cria_sala', { p_mapa: 'de_mirage', p_nick: 'b15t', p_estado_inicial: { cabecalho: { id: 'b15t' }, operacoes: [] } })).data;
      for (let i = 0; i < 30; i++) await L.rpc('entrar_na_sala', { p_codigo: s.codigo, p_nick: 'b15t' });
      return true;""")
    with banco.cursor() as cur:
        cur.execute("select count(*) from grupos.tentativas")
        depois = cur.fetchone()[0]
    banco.close()
    assert depois == antes, (antes, depois)


@pytest.mark.skipif(os.environ.get("GRUPOS_B15_GLOBAL") != "1",
                    reason="enche o servidor com 200 salas (GRUPOS_B15_GLOBAL=1; limpar depois pelo SQL Editor)")
def test_b15_teto_global_de_200_salas_ativas(api2):
    """A sala 201 ativa é recusada com servidor_cheio. Cria salas com contas novas (5 por conta por hora, e o Supabase só
    deixa 30 logins anônimos por hora por IP: rodar com o limite de logins anônimos do painel já subido)."""
    r = js2(api2, """
      let criadas = 0, ultimo = null;
      for (let u = 0; u < 60 && !ultimo; u++) {
        const c = await window.__novo('g' + u);
        for (let i = 0; i < 5 && !ultimo; i++) {
          const r = await c.rpc('cria_sala', { p_mapa: 'de_mirage', p_nick: 'g' + i, p_estado_inicial: { cabecalho: { id: 'b15-global' }, operacoes: [] } });
          if (r.error) ultimo = r.error.message; else criadas++;
        }
      }
      return { criadas, ultimo };""")
    assert r["ultimo"] and "servidor_cheio" in r["ultimo"], r


@pytest.mark.xfail(reason="depende de B-1 (o cliente valida cada operação recebida): fase do CLIENTE, em outro branch", strict=False)
def test_b16_operacao_malformada_da_lider_nao_derruba_o_navegador_do_membro(navegador, site_real, api2):
    """Uma operação que o SERVIDOR aceita (forma mínima e tipo da lista) mas a prancheta não consegue aplicar (ex.: cria_granada
    com origem texto), inserida pela líder pela API, não derruba a página de um membro conectado nem depois de recarregar."""
    url = site_real["base"] + "/" + site_real["pagina"]
    c1, membro = _abre(navegador, url)
    erros = []
    membro.on("pageerror", lambda e: erros.append(str(e)))
    try:
        codigo = js2(api2, "return S.codigo;")
        membro.fill("#gr-nick", "membro16")
        membro.fill("#gr-codigo", codigo)
        membro.click('[data-acao="entrar"]')
        membro.wait_for_function("() => Grupo._interno.G().fase === 'dentro'", timeout=20000)
        antes = membro.evaluate("() => JSON.stringify(Prancheta._interno.S.estado)")
        passo = membro.evaluate("() => Prancheta.grupo.estado().passos.length ? Prancheta.grupo.estado().passos[0].passo : 'p1'")
        ruins = [
            {"tipo": "cria_granada", "passo": passo, "granada": "g16", "origem": "x", "destino": [0, 0], "arma": "smoke"},
            {"tipo": "cria_traco", "passo": passo, "traco": "t16", "ferramenta": "caneta", "cor": "#000000", "espessura": 4, "pontos": 7},
            {"tipo": "cria_peca", "passo": "passo-que-nao-existe", "peca": "p16", "lado": "t", "rotulo": "x", "x": "a", "y": "b"},
            {"tipo": "move_peca", "peca": "p16", "passo": passo},
            {"tipo": "cria_caminho", "peca": "p16", "pontos": "texto"},
        ]
        for i, extra in enumerate(ruins):
            js2(api2, f"""const o = Object.assign(window.__op(U.L2, 100 + {i}, {{}}), {json.dumps(extra)}, {{ id: 'b16ruim{i}', seq: 100 + {i} }});
              const r = await U.L2.from('operacoes').insert({{ sala_id: S.sala_id, lamport: 100 + {i}, op: o }});
              await esp(1200); return r.error;""")
        membro.wait_for_timeout(3000)
        assert not erros, erros
        assert membro.evaluate("() => JSON.stringify(Prancheta._interno.S.estado)") == antes
        assert not [o for o in membro.evaluate("() => Prancheta.grupo.documento().operacoes") if str(o.get("id", "")).startswith("b16ruim")]
        membro.reload()
        membro.wait_for_function("() => Prancheta._interno.S.estado !== null", timeout=20000)
        assert not erros, erros
    finally:
        c1.close()


def test_b17_o_agendamento_da_limpeza_existe_e_a_funcao_roda():
    """cron.job tem `grupos-limpa-salas-antigas` e grupos.limpa_salas_antigas() roda sem erro (precisa de SUPABASE_DB_URL)."""
    banco = _db()
    try:
        with banco.cursor() as cur:
            cur.execute("select jobname, schedule, command from cron.job where jobname = 'grupos-limpa-salas-antigas'")
            job = cur.fetchall()
            assert len(job) == 1 and "grupos.limpa_salas_antigas" in job[0][2], job
            cur.execute("select grupos.limpa_salas_antigas()")
            assert cur.fetchone()[0] >= 0
    finally:
        banco.close()


def test_b18_30_chamadas_paralelas_com_codigo_errado_gravam_no_maximo_5_erros(api2):
    """L-1: 30 chamadas em paralelo da MESMA conta com código errado: no máximo 5 voltam `nao_existe` (o resto, `muitas_tentativas`).
    Depende da trava consultiva da migração 7; se ela faltar, este teste falha e o relatório registra o L-1 como aberto."""
    r = js2(api2, """
      const c = await window.__novo('b18');
      const codigos = Array.from({ length: 30 }, (_, i) => 'ZZZZZZZ' + 'BCDEFGHJKMNPQRSTUVWXYZ23456789'[i]);
      const rs = await Promise.all(codigos.map((k) => c.rpc('entrar_na_sala', { p_codigo: k, p_nick: 'x' })));
      const motivos = rs.map((x) => (x.data || {}).motivo || (x.error && x.error.message) || 'ok');
      return { nao_existe: motivos.filter((m) => m === 'nao_existe').length, travadas: motivos.filter((m) => m === 'muitas_tentativas').length, motivos };""")
    assert r["nao_existe"] <= 5, r
    assert r["nao_existe"] + r["travadas"] == 30, r


def test_b19_cadastro_por_email_e_recusado(api2):
    """L-8: o cadastro por e-mail tem de estar DESLIGADO no painel (só Anonymous). A chamada usa um endereço .invalid, que nunca
    existe; se o provedor estivesse ligado, o Supabase tentaria criar a conta (e o teste falha)."""
    r = js2(api2, """
      const c = supabase.createClient(window.__URL, window.__CHAVE, { auth: { persistSession: false, autoRefreshToken: false, storageKey: 'teste-b19' } });
      const x = await c.auth.signUp({ email: 'b19-' + Math.random().toString(16).slice(2) + '@exemplo.invalid', password: 'Aaaa-1111-bbbb-2222' });
      return { erro: x.error && { code: x.error.code, status: x.error.status, message: x.error.message }, sessao: !!(x.data && x.data.session) };""")
    assert r["erro"] and not r["sessao"], r
    assert r["erro"]["code"] in ("email_provider_disabled", "signup_disabled") or r["erro"]["status"] in (400, 403, 422), r


def test_b20_criar_grupo_do_maior_round_real_leva_ate_10_segundos(navegador):
    """O tempo de criar um grupo a partir do MAIOR round real (supabase/medicao/maior_round_documento.json) contra o servidor
    real, na rede Fast 4G emulada pelo Chrome (165 ms, 1,5 Mbit/s de subida) e CPU 4x mais lenta: mediana de 5 rodadas
    (cada uma com uma conta anônima nova). Imprime os cinco tempos (pytest -s). Requisito: no máximo 10 s."""
    import json as _json
    from scripts.build_tactics_page import arquivo_da_pagina, build_html

    medicao = _json.loads((RAIZ / "supabase" / "medicao" / "maior_round_na_prancheta.json").read_text(encoding="utf-8"))
    doc = _json.loads((RAIZ / "supabase" / "medicao" / "maior_round_documento.json").read_text(encoding="utf-8"))
    mapa = medicao["maior_em_bytes"]["mapa"]
    import tempfile
    pasta = Path(tempfile.mkdtemp(prefix="b20_"))
    (pasta / "vendor").mkdir()
    (pasta / "vendor" / gc.ARQUIVO_SUPABASE_JS).write_bytes(gc.confere_biblioteca().read_bytes())
    pagina = arquivo_da_pagina(mapa)
    cfg = gc.configuracao(None, pagina, ambiente={"SUPABASE_URL": URL, "SUPABASE_ANON_KEY": CHAVE}, ativos=True)
    (pasta / pagina).write_text(build_html(mapa, grupo=cfg), encoding="utf-8")
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), partial(http.server.SimpleHTTPRequestHandler, directory=str(pasta)))
    srv.RequestHandlerClass.log_message = lambda *a: None
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    tempos = []
    try:
        for _ in range(5):
            ctx = navegador.new_context(viewport={"width": 375, "height": 667})
            try:
                pg = ctx.new_page()
                cdp = ctx.new_cdp_session(pg)
                cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
                pg.goto(f"http://127.0.0.1:{srv.server_address[1]}/{pagina}")
                pg.wait_for_function("() => Prancheta._interno.S.estado !== null && !!document.getElementById('pr-painel-grupo')")
                assert pg.evaluate("(d) => Prancheta.grupo.usaDocumento(d)", doc) == ""
                pg.evaluate("() => Prancheta._interno.abaDoPainel('grupo')")
                pg.fill("#gr-nick", "b20")
                # a rede emulada vale a partir do clique (o login anônimo e o supabase-js entram na conta, como para o usuário)
                cdp.send("Network.enable")
                cdp.send("Network.emulateNetworkConditions", {"offline": False, "latency": 165,
                                                              "downloadThroughput": 9_000_000 / 8, "uploadThroughput": 1_500_000 / 8})
                t0 = pg.evaluate("() => performance.now()")
                pg.click('[data-acao="criar"]')
                pg.wait_for_function("() => Grupo._interno.G().fase === 'dentro' && Grupo._interno.G().fila.length === 0 "
                                     "&& !Grupo._interno.G().enviando", timeout=120000)
                tempos.append((pg.evaluate("() => performance.now()") - t0) / 1000)
                pg.click('[data-acao="encerrar"]')
                pg.click('[data-acao="confirma-encerrar"]')
            finally:
                ctx.close()
    finally:
        srv.shutdown()
    print("\ncriar grupo do maior round real (Fast 4G, CPU 4x):", [round(t, 2) for t in tempos], "mediana", round(statistics.median(tempos), 2), "s")
    assert statistics.median(tempos) <= 10, tempos
