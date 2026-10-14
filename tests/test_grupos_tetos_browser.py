"""Grupos na prancheta (fase 16b): tetos de uso, estado inicial numa linha só, L-2, L-3 e L-5, no navegador.

A SalaFalsa (sala.js) repete as regras das migrações 6 e 7 (as do PGlite, em supabase/tests/politicas_no_pglite.mjs);
aqui se confere o que a TELA faz com cada recusa e o que o cliente faz com o estado inicial. Os limites do servidor
falso são baixados por opção (`falsa.limites`) para chegar ao teto sem milhares de operações.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_grupos_browser import (CLIENTES_JS, G, MAPA, UID_DA_TELA, abre_grupo,  # noqa: E402
                                       entra_pela_aba, Grupo_nada_pedido)
from tests.test_tactics_browser import contexto, interno, navegador  # noqa: E402,F401

RAIZ = Path(__file__).resolve().parents[1]

FRASES = {
    "sala_no_limite": "Esta sala chegou ao limite de alterações",
    "autor_no_limite": "Você está alterando rápido demais; espere um pouco",
    "servidor_cheio": "O servidor de grupos está cheio agora",
    "muitas_chamadas": "Muitas tentativas; espere um minuto",
}


def _pagina(tmp_path_factory, nome, falsa=None, mapa=MAPA):
    from scripts.build_tactics_page import arquivo_da_pagina, build_html
    html = tmp_path_factory.mktemp(nome) / arquivo_da_pagina(mapa)
    cfg = {"uid": UID_DA_TELA, "atrasoMs": 5}
    cfg.update(falsa or {})
    html.write_text(build_html(mapa, grupo={"modo": "falsa", "site": "https://exemplo.github.io/site/",
                                            "pagina": arquivo_da_pagina(mapa), "falsa": cfg}), encoding="utf-8")
    return html


@pytest.fixture(scope="module")
def pagina_normal(tmp_path_factory):
    return _pagina(tmp_path_factory, "tetos_normal")


def cria_pela_aba(pg, nick="nomad"):
    pg.evaluate("() => Prancheta._interno.abaDoPainel('grupo')")
    pg.fill("#gr-nick", nick)
    pg.click('[data-acao="criar"]')


def frase_da_dica(pg):
    return pg.inner_text("#pr-dica-estado")


# --- o estado inicial numa linha só ----------------------------------------------------------------------------------

def test_criar_sobe_o_estado_inicial_numa_linha_so_e_quem_entra_recebe_o_mesmo_log(contexto, pagina_normal):
    pg = abre_grupo(contexto, pagina_normal)
    # a tática já tem alterações antes de virar grupo
    pg.evaluate("""() => { const c = Prancheta._interno.centro(), passo = Prancheta.grupo.estado().passos[0].passo;
        Prancheta._interno.emiteLote([['cria_peca', { peca: 'pecaa1', lado: 't', rotulo: 'ztrike', passo, x: c[0], y: c[1] }],
                                      ['renomeia', { titulo: 'antes do grupo' }]]); }""")
    antes = pg.evaluate("() => Prancheta.grupo.documento().operacoes.length")
    assert antes >= 4
    cria_pela_aba(pg)
    pg.wait_for_function("() => Grupo._interno.G().fase === 'dentro'")
    pg.wait_for_function("() => Grupo._interno.G().fila.length === 0 && !Grupo._interno.G().enviando")
    r = pg.evaluate("""() => { const srv = window.__servidorFalso, G = Grupo._interno.G();
        return { pedidos: srv.pedidos.filter((n) => n !== 'prepara'), tabela: srv.ops.length, inicial: srv.inicialDe(G.salaId).length,
                 totais: srv.totaisDe(G.salaId).ops }; }""")
    # UM pedido de criação (cria_sala) e nenhum lote de operações: o estado inicial vai dentro dele
    assert r["pedidos"][0] == "cria_sala" and r["pedidos"].count("cria_sala") == 1
    assert "envia" not in r["pedidos"] and "criar" not in r["pedidos"] and "entrar" not in r["pedidos"]
    assert r["inicial"] == antes and r["tabela"] == 0 and r["totais"] == antes
    # quem entra recebe o estado inicial como a primeira parte do log e chega ao MESMO estado
    codigo = pg.inner_text("#gr-codigo-sala")
    r = pg.evaluate(f"""async () => {{ const c = window.__cliente('u-ana', 'ana'); await c.s.prepara();
        const e = await c.s.entrar('{codigo}', 'ana');
        (e.operacoes_iniciais || []).forEach((o) => c.recebe({{ op: o }}));
        const linhas = await c.s.operacoes(); linhas.forEach((l) => c.recebe(l));
        return {{ ok: e.ok, iniciais: (e.operacoes_iniciais || []).length,
                  igual: JSON.stringify(c.estado()) === JSON.stringify(Prancheta._interno.S.estado) }}; }}""")
    assert r == {"ok": True, "iniciais": antes, "igual": True}
    # uma alteração nova depois do estado inicial vai pela tabela e chega a quem está na sala
    pg.evaluate("() => Prancheta._interno.emiteLote([['renomeia', { titulo: 'depois' }]])")
    pg.wait_for_function("() => window.__servidorFalso.ops.length === 1")
    assert not pg._erros


def test_alteracao_feita_enquanto_o_grupo_e_criado_nao_se_perde(contexto, tmp_path_factory):
    pagina = _pagina(tmp_path_factory, "tetos_lento", {"atrasoMs": 300})
    pg = abre_grupo(contexto, pagina)
    cria_pela_aba(pg)
    pg.wait_for_function("() => Grupo._interno.G().fase === 'entrando'")
    pg.evaluate("() => { const d = Prancheta.grupo.documento(); Prancheta._interno.emiteLote([['renomeia', { titulo: 'no meio' }]]); }")
    pg.wait_for_function("() => Grupo._interno.G().fase === 'dentro' && Grupo._interno.G().fila.length === 0 && !Grupo._interno.G().enviando")
    pg.wait_for_function("() => window.__servidorFalso.ops.some((l) => l.op.titulo === 'no meio')")
    assert not pg._erros


# --- os tetos, cada um com a sua frase ---------------------------------------------------------------------------------

def test_teto_da_sala_diz_a_frase_e_desfaz_a_alteracao(contexto, tmp_path_factory):
    pagina = _pagina(tmp_path_factory, "tetos_sala", {"limites": {"maxOpsPorSala": 3}})
    pg = abre_grupo(contexto, pagina)
    cria_pela_aba(pg)                                   # 2 operações do estado inicial; sobra 1
    pg.wait_for_function("() => Grupo._interno.G().fase === 'dentro'")
    pg.evaluate("() => Prancheta._interno.emiteLote([['renomeia', { titulo: 'a' }]])")
    pg.wait_for_function("() => window.__servidorFalso.ops.length === 1")
    pg.evaluate("() => Prancheta._interno.emiteLote([['renomeia', { titulo: 'b' }]])")
    pg.wait_for_function(f"() => document.getElementById('pr-dica-estado').textContent === {json.dumps(FRASES['sala_no_limite'])}")
    assert not [o for o in interno(pg, "S.doc.operacoes") if o["tipo"] == "renomeia" and o.get("titulo") == "b"]
    assert pg.evaluate("() => window.__servidorFalso.ops.length") == 1
    assert not pg._erros


def test_teto_por_autor_diz_a_frase_e_desfaz_a_alteracao(contexto, tmp_path_factory):
    pagina = _pagina(tmp_path_factory, "tetos_autor", {"limites": {"maxOpsPorMinuto": 2}})
    pg = abre_grupo(contexto, pagina)
    cria_pela_aba(pg)
    pg.wait_for_function("() => Grupo._interno.G().fase === 'dentro'")
    for t in ("a", "b"):
        pg.evaluate(f"() => Prancheta._interno.emiteLote([['renomeia', {{ titulo: '{t}' }}]])")
        pg.wait_for_function(f"() => window.__servidorFalso.ops.length === {1 if t == 'a' else 2}")
    pg.evaluate("() => Prancheta._interno.emiteLote([['renomeia', { titulo: 'c' }]])")
    pg.wait_for_function(f"() => document.getElementById('pr-dica-estado').textContent === {json.dumps(FRASES['autor_no_limite'])}")
    assert not [o for o in interno(pg, "S.doc.operacoes") if o.get("titulo") == "c"]
    assert not pg._erros


def test_teto_global_de_salas_diz_a_frase_e_nao_cria_o_grupo(contexto, tmp_path_factory):
    pagina = _pagina(tmp_path_factory, "tetos_global", {"limites": {"maxSalasAtivas": 0}})
    pg = abre_grupo(contexto, pagina)
    cria_pela_aba(pg)
    pg.wait_for_function(f"() => document.getElementById('gr-status').textContent === {json.dumps(FRASES['servidor_cheio'])}")
    assert G(pg, "G.fase") == "fora"
    assert pg.evaluate("() => Object.keys(window.__servidorFalso.inicialDe('sala-1')).length") == 0
    assert not pg._erros


def test_teto_de_chamadas_de_entrar_diz_a_frase(contexto, tmp_path_factory):
    pagina = _pagina(tmp_path_factory, "tetos_chamadas", {"limites": {"maxChamadasPorMinuto": 2}})
    pg = abre_grupo(contexto, pagina)
    pg.evaluate("() => Prancheta._interno.abaDoPainel('grupo')")
    for i in range(3):
        pg.fill("#gr-nick", "spinx")
        pg.fill("#gr-codigo", "ABCDEFGH")
        pg.click('[data-acao="entrar"]')
        pg.wait_for_function("() => Grupo._interno.G().fase === 'fora' && document.querySelector('.erro-campo, #gr-status').textContent.length > 0")
    pg.wait_for_function(f"() => document.getElementById('gr-status').textContent === {json.dumps(FRASES['muitas_chamadas'])}")
    assert not pg._erros


def test_tatica_acima_do_teto_da_sala_nem_tenta_criar(contexto, tmp_path_factory):
    pagina = _pagina(tmp_path_factory, "tetos_impedimento", {"limites": {"maxOpsPorSala": 1}})
    pg = abre_grupo(contexto, pagina)
    antes = pg.evaluate("() => window.__servidorFalso.pedidos.length")
    r = pg.evaluate("() => Grupo._interno.impedimento({ operacoes: new Array(5001).fill(0).map((_, i) => ({ id: 'x' + i, seq: i + 1 })), mapa: 'de_mirage' })")
    assert "limite de um grupo" in r
    assert pg.evaluate("() => window.__servidorFalso.pedidos.length") == antes


# --- L-2 e L-3, com a SalaFalsa (as mesmas regras do PGlite) ----------------------------------------------------------

def test_l2_salto_de_lamport_acima_de_1000_e_recusado(contexto, pagina_normal):
    pg = abre_grupo(contexto, pagina_normal)
    r = pg.evaluate("""async () => {
        const L = window.__cliente('u-lider', 'nomad'); await L.s.prepara();
        const sala = await L.s.criar({ mapa: 'de_mirage', cabecalho: { id: 't' } }); await L.s.entrar(sala.codigo, 'nomad');
        const op = (seq, id) => ({ id, seq, autor: 'nomad', em: '', tipo: 'renomeia', titulo: 'x' });
        const res = {};
        res.salto1001 = (await L.s.envia([{ lamport: 1001, op: op(1001, 'sa1001') }])).motivo;
        res.salto1000 = (await L.s.envia([{ lamport: 1000, op: op(1000, 'sa1000') }])).ok;
        res.depois1001 = (await L.s.envia([{ lamport: 2001, op: op(2001, 'sb2001') }])).motivo;
        res.depois1000 = (await L.s.envia([{ lamport: 2000, op: op(2000, 'sb2000') }])).ok;
        return res; }""")
    assert r == {"salto1001": "invalida", "salto1000": True, "depois1001": "invalida", "depois1000": True}


def test_l3_operacao_sem_em_ou_de_tipo_desconhecido_e_recusada(contexto, pagina_normal):
    pg = abre_grupo(contexto, pagina_normal)
    r = pg.evaluate("""async () => {
        const L = window.__cliente('u-lider', 'nomad'); await L.s.prepara();
        const sala = await L.s.criar({ mapa: 'de_mirage', cabecalho: { id: 't' } }); await L.s.entrar(sala.codigo, 'nomad');
        const base = (id, extra) => Object.assign({ id, seq: 1, autor: 'nomad', em: '', tipo: 'renomeia', titulo: 'x' }, extra);
        const tenta = async (op) => (await L.s.envia([{ lamport: 1, op }])).motivo || 'aceita';
        const semEm = base('semem001', {}); delete semEm.em;
        return { semEm: await tenta(semEm), emNumero: await tenta(base('emnum001', { em: 5 })),
                 tipoNovo: await tenta(base('tipo0001', { tipo: 'apaga_tudo' })), ok: await tenta(base('ok000001', {})) }; }""")
    assert r == {"semEm": "invalida", "emNumero": "invalida", "tipoNovo": "invalida", "ok": "aceita"}


def test_l3_a_lista_de_tipos_do_servidor_falso_e_a_da_prancheta(contexto, pagina_normal):
    pg = abre_grupo(contexto, pagina_normal)
    tipos = pg.evaluate("() => Prancheta.grupo.tipos()")
    assert len(tipos) == 26 and "desenha_granada" in tipos and "define_area_desenho" in tipos


# --- L-5: a sessão apagada no servidor ---------------------------------------------------------------------------------

def test_l5_com_a_sessao_apagada_no_servidor_o_proximo_entrar_refaz_o_login_sozinho(contexto, pagina_normal):
    pg = abre_grupo(contexto, pagina_normal)
    codigo = pg.evaluate("async () => await window.__criaSala()")
    entra_pela_aba(pg, codigo)                                   # entra como u-tela
    uid_antes = G(pg, "G.uid")
    pg.evaluate("() => Grupo._interno.sair()")
    pg.wait_for_function("() => Grupo._interno.G().fase === 'fora'")
    # a limpeza diária apaga o usuário anônimo órfão (a sessão guardada no navegador continua lá)
    pg.evaluate(f"() => window.__servidorFalso.apagaUsuario('{uid_antes}')")
    pg.evaluate("() => Prancheta._interno.abaDoPainel('grupo')")
    pg.fill("#gr-nick", "spinx")
    pg.fill("#gr-codigo", codigo)
    pg.click('[data-acao="entrar"]')
    pg.wait_for_function("() => Grupo._interno.G().fase === 'dentro' && Grupo._interno.G().membros.length > 0")
    assert G(pg, "G.uid") != uid_antes                           # login anônimo novo, sozinho
    assert pg.locator("#gr-erro").count() == 0 and G(pg, "G.erro") == ""   # nenhum erro na tela
    assert pg.locator(".erro-campo").count() == 0
    assert not pg._erros


def test_l5_supabase_js_confere_a_sessao_guardada_e_refaz_o_login(contexto, pagina_normal):
    """O cliente real (SalaSupabase) com um supabase-js de mentira: sessão guardada de usuário que o servidor apagou."""
    pg = contexto.new_page()
    pg.goto(pagina_normal.as_uri())
    pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
    r = pg.evaluate("""async () => {
        const chamadas = [];
        const fabrica = (sessaoGuardada, getUser) => ({ createClient: () => ({ auth: {
          getSession: async () => ({ data: { session: sessaoGuardada }, error: null }),
          getUser: async () => getUser,
          signOut: async (o) => { chamadas.push('signOut:' + (o && o.scope)); return { error: null }; },
          signInAnonymously: async () => { chamadas.push('login'); return { data: { user: { id: 'novo-anonimo' } }, error: null }; } } }) });
        const sessao = { user: { id: 'velho' } };
        const sala = () => Sala.SalaSupabase({ url: 'https://x.invalid', chave: 'k', biblioteca: 'nao-carrega.js' });
        const saida = {};
        window.supabase = fabrica(sessao, { data: { user: null }, error: { name: 'AuthApiError', status: 403, message: 'user_not_found' } });
        saida.apagado = await sala().prepara(); saida.chamadasApagado = chamadas.splice(0);
        window.supabase = fabrica(sessao, { data: { user: { id: 'velho' } }, error: null });
        saida.vivo = await sala().prepara(); saida.chamadasVivo = chamadas.splice(0);
        window.supabase = fabrica(sessao, { data: { user: null }, error: { name: 'AuthRetryableFetchError', status: 0, message: 'rede' } });
        saida.semRede = await sala().prepara(); saida.chamadasSemRede = chamadas.splice(0);
        window.supabase = fabrica(null, null);
        saida.semSessao = await sala().prepara(); saida.chamadasSemSessao = chamadas.splice(0);
        return saida; }""")
    assert r == {"apagado": "novo-anonimo", "chamadasApagado": ["signOut:local", "login"],
                 "vivo": "velho", "chamadasVivo": [],
                 "semRede": "velho", "chamadasSemRede": [],
                 "semSessao": "novo-anonimo", "chamadasSemSessao": ["login"]}


# --- o maior round real: criar o grupo em até 10 segundos (Fast 4G) --------------------------------------------------

DOC_DO_MAIOR_ROUND = RAIZ / "supabase" / "medicao" / "maior_round_documento.json"


@pytest.mark.skipif(not DOC_DO_MAIOR_ROUND.exists(), reason="sem o documento do maior round (scripts.mede_round_na_prancheta --grava-maior)")
def test_criar_grupo_do_maior_round_real_leva_ate_10_segundos_em_fast_4g(contexto, tmp_path_factory):
    medicao = json.loads((RAIZ / "supabase" / "medicao" / "maior_round_na_prancheta.json").read_text(encoding="utf-8"))
    rede = {"latenciaMs": 165, "subidaBps": 1_500_000, "descidaBps": 9_000_000}   # Fast 4G, como mede_lcp_cls.py
    pagina = _pagina(tmp_path_factory, "tetos_round", {"atrasoMs": 0, "rede": rede}, mapa=medicao["maior_em_bytes"]["mapa"])
    doc = json.loads(DOC_DO_MAIOR_ROUND.read_text(encoding="utf-8"))
    pg = contexto.new_page()
    erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.add_init_script(CLIENTES_JS)
    pg.goto(pagina.as_uri())
    pg.wait_for_function("() => Prancheta._interno.S.estado !== null && !!document.getElementById('pr-painel-grupo')")
    assert pg.evaluate("(d) => Prancheta.grupo.usaDocumento(d)", doc) == ""
    assert len(pg.evaluate("() => Prancheta.grupo.documento().operacoes")) == medicao["maior_em_bytes"]["ops"]
    pg.evaluate("() => Prancheta._interno.abaDoPainel('grupo')")
    pg.fill("#gr-nick", "nomad")
    t0 = pg.evaluate("() => performance.now()")
    pg.click('[data-acao="criar"]')
    pg.wait_for_function("() => Grupo._interno.G().fase === 'dentro' && Grupo._interno.G().fila.length === 0 && !Grupo._interno.G().enviando",
                         timeout=30000)
    gasto = (pg.evaluate("() => performance.now()") - t0) / 1000
    assert gasto <= 10, gasto
    r = pg.evaluate("""() => { const srv = window.__servidorFalso, G = Grupo._interno.G();
        return { pedidos: srv.pedidos, inicial: srv.inicialDe(G.salaId).length, tabela: srv.ops.length,
                 bytes: Math.max(...srv.trafego.map((t) => t.bytes)) }; }""")
    assert r["inicial"] == medicao["maior_em_bytes"]["ops"] and r["tabela"] == 0
    assert "envia" not in r["pedidos"]
    assert r["bytes"] < 2 * 1024 * 1024
    assert not erros
