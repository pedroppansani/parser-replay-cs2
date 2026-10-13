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
