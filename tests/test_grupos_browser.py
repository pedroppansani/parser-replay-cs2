"""Grupos na prancheta (fase 13, item 13.6, parte A): a sala como transporte, no navegador, com a SalaFalsa.

A página é a prancheta de sempre com o bloco do grupo injetado no modo "falsa" (sala.js: o servidor em memória
com as MESMAS regras de supabase/migrations, inclusive as recusas do RLS). A tela é UM cliente (o membro, ou a
líder no teste de criar); os outros são clientes sem tela na mesma página, que falam com o mesmo servidor falso.
"""
from __future__ import annotations

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_tactics_browser import contexto, interno, navegador, no_radar  # noqa: E402,F401

MAPA = "de_mirage"
UID_DA_TELA = "u-tela"

# Clientes sem tela (a líder e outros membros) e a sala criada pela líder com a tática aberta na tela.
CLIENTES_JS = r"""
window.__cliente = function (uid, nick) {
  const s = Sala.SalaFalsa(window.__servidorFalso, { uid });
  const c = { s, uid, nick, ops: {}, seq: 0, cab: null, avisos: [] };
  c.recebe = (l) => { if (!c.ops[l.op.id]) { c.ops[l.op.id] = l.op; c.seq = Math.max(c.seq, l.op.seq); } };
  c.liga = () => s.conecta({ aoReceber: c.recebe, aoMudar: (a) => c.avisos.push(a), aoPresenca: () => {},
                             aoCabecote: (x) => { c.cab = x; }, aoConexao: () => {} });
  let n = 0;
  c.op = (tipo, dados) => {
    const op = Object.assign({ id: uid.replace(/\W/g, '') + 'op' + (++n), seq: ++c.seq, autor: nick,
                               em: new Date().toISOString(), tipo }, dados);
    c.ops[op.id] = op;
    return op;
  };
  c.envia = (ops) => s.envia(ops.map((o) => ({ lamport: o.seq, op: o })));
  c.estado = () => Prancheta.grupo.aplica(Object.values(c.ops));
  return c;
};
window.__criaSala = async function () {
  const doc = Prancheta.grupo.documento();
  const L = window.__cliente('u-lider', 'nomad');
  await L.s.prepara();
  const cab = {};
  Object.keys(doc).forEach((k) => { if (k !== 'operacoes' && k !== 'contador') cab[k] = doc[k]; });
  const r = await L.s.criar({ mapa: doc.mapa, cabecalho: cab });
  await L.s.entrar(r.codigo, 'nomad');
  doc.operacoes.forEach((o) => { L.ops[o.id] = o; L.seq = Math.max(L.seq, o.seq); });
  await L.envia(doc.operacoes);
  await L.liga();
  const passo = Prancheta.grupo.estado().passos[0].passo, c = Prancheta._interno.centro();
  await L.envia([L.op('cria_peca', { peca: 'pecaztrike', lado: 't', rotulo: 'ztrike', passo, x: c[0], y: c[1] })]);
  window.__lider = L; window.__passo = passo;
  return r.codigo;
};
"""


@pytest.fixture(scope="module")
def pagina_grupo(tmp_path_factory):
    from scripts.build_tactics_page import arquivo_da_pagina, build_html
    html = tmp_path_factory.mktemp("grupo") / arquivo_da_pagina(MAPA)
    html.write_text(build_html(MAPA, grupo={"modo": "falsa", "site": "https://exemplo.github.io/site/",
                                            "pagina": arquivo_da_pagina(MAPA),
                                            "falsa": {"uid": UID_DA_TELA, "atrasoMs": 5}}), encoding="utf-8")
    return html


def abre_grupo(ctx, pagina):
    pg = ctx.new_page()
    erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.add_init_script(CLIENTES_JS)
    pg.goto(pagina.as_uri())
    pg.wait_for_function("() => Prancheta._interno.S.estado !== null && !!document.getElementById('pr-painel-grupo')")
    pg._erros = erros
    return pg


def G(pg, expr):
    return pg.evaluate(f"() => {{ const G = Grupo._interno.G(); return {expr}; }}")


def entra_pela_aba(pg, codigo, nick="spinx"):
    pg.evaluate("() => Prancheta._interno.abaDoPainel('grupo')")
    pg.fill("#gr-nick", nick)
    pg.fill("#gr-codigo", codigo)
    pg.click('[data-acao="entrar"]')
    pg.wait_for_function("() => Grupo._interno.G().fase === 'dentro' && Grupo._interno.G().membros.length > 0")


def membro_na_sala(ctx, pagina):
    """A líder (sem tela) cria a sala com uma peça; a tela entra como membro, sem permissão."""
    pg = abre_grupo(ctx, pagina)
    codigo = pg.evaluate("async () => await window.__criaSala()")
    entra_pela_aba(pg, codigo)
    pg.wait_for_function("() => !!Prancheta._interno.S.estado.pecas.pecaztrike")
    return pg, codigo


def arrasta_a_peca(pg, peca="pecaztrike", dx=80, dy=40):
    pos = pg.evaluate(f"""() => {{ const S = Prancheta._interno.S, I = Prancheta._interno;
        const q = Object.values(S.estado.pecas['{peca}'].posicoes).pop(); return I.jogoParaPixel(q[0], q[1]); }}""")
    x, y = no_radar(pg, *pos)
    pg.locator("#pr-mapa").scroll_into_view_if_needed()
    x, y = no_radar(pg, *pos)
    pg.mouse.move(x, y)
    pg.mouse.down()
    pg.mouse.move(x + dx, y + dy, steps=8)
    pg.mouse.up()


def posicao(pg, peca="pecaztrike"):
    return interno(pg, f"Object.values(S.estado.pecas['{peca}'].posicoes).pop()")


def dica(pg):
    return pg.inner_text("#pr-dica-estado")


# --- 1. convergência ----------------------------------------------------------

def test_tres_clientes_em_200_ordens_diferentes_terminam_no_mesmo_estado(contexto, pagina_grupo):
    """Três autores com relógios de Lamport concorrentes (mesmo seq em autores diferentes), conflitos na mesma
    peça e no mesmo passo, desfazer e refazer; cada cliente recebe tudo numa ordem aleatória (semente fixa), em
    lotes e com repetidas. Os três terminam no estado de aplicar o log inteiro -- e a tela também."""
    pg = abre_grupo(contexto, pagina_grupo)
    r = pg.evaluate("""() => {
      const rnd = Sala.aleatorio(20261013), ops = [], autores = ['nomad', 'spinx', 'ztrike'];
      const passo = 'passo1', pecas = ['p1', 'p2', 'p3'];
      ops.push({ id: 'a0', seq: 1, autor: 'nomad', em: '', tipo: 'renomeia', titulo: 'x' });
      ops.push({ id: 'a1', seq: 2, autor: 'nomad', em: '', tipo: 'cria_passo', passo, titulo: '' });
      pecas.forEach((p, i) => ops.push({ id: 'c' + i, seq: 3, autor: autores[i], em: '', tipo: 'cria_peca', peca: p,
                                          lado: 't', rotulo: p, passo, x: 0, y: 0 }));
      const relogio = { nomad: 3, spinx: 3, ztrike: 3 }, minhas = { nomad: [], spinx: [], ztrike: [] };
      for (let k = 0; k < 90; k++) {
        const a = autores[Math.floor(rnd() * 3)];
        // às vezes o autor viu tudo (pula o relógio), às vezes está atrasado (seq igual ao de outro)
        if (rnd() < 0.3) relogio[a] = Math.max(...Object.values(relogio));
        const seq = ++relogio[a], id = a + 'm' + k, x = rnd();
        let op;
        if (minhas[a].length && x < 0.15) op = { tipo: 'anula', alvo: minhas[a][Math.floor(rnd() * minhas[a].length)] };
        else if (minhas[a].length && x < 0.22) op = { tipo: 'reativa', alvo: minhas[a][Math.floor(rnd() * minhas[a].length)] };
        else op = { tipo: 'move_peca', peca: pecas[Math.floor(rnd() * 3)], passo, x: Math.round(rnd() * 900), y: Math.round(rnd() * 900) };
        ops.push(Object.assign({ id, seq, autor: a, em: '' }, op));
        if (op.tipo === 'move_peca') minhas[a].push(id);
      }
      const esperado = JSON.stringify(Prancheta.grupo.aplica(ops));
      const embaralha = (lista, r) => { const v = lista.slice(); for (let i = v.length - 1; i > 0; i--) {
          const j = Math.floor(r() * (i + 1)); [v[i], v[j]] = [v[j], v[i]]; } return v; };
      let diferentes = 0, ordensDistintas = new Set();
      for (let rodada = 1; rodada <= 200; rodada++) {
        const estados = [0, 1, 2].map((c) => {
          const r = Sala.aleatorio(rodada * 7 + c), ordem = embaralha(ops, r), log = {};
          ordensDistintas.add(ordem.map((o) => o.id).join());
          // entrega em lotes de tamanho aleatório, com 10% repetidas (reenvio depois de cair)
          for (let i = 0; i < ordem.length;) {
            const n = 1 + Math.floor(r() * 6);
            ordem.slice(i, i + n).forEach((o) => { if (!log[o.id]) log[o.id] = o; if (r() < 0.1) log[o.id] = o; });
            i += n;
          }
          return JSON.stringify(Prancheta.grupo.aplica(Object.values(log)));
        });
        if (!(estados[0] === estados[1] && estados[1] === estados[2] && estados[0] === esperado)) diferentes++;
      }
      // a tela: as mesmas operações por Prancheta.grupo.recebe (o caminho de quem está num grupo), embaralhadas
      const doc = Prancheta.grupo.documento();
      doc.operacoes = []; doc.contador = 0;
      embaralha(ops, Sala.aleatorio(99)).forEach((o) => Prancheta.grupo.recebe([o, o]));
      const tela = JSON.stringify(Prancheta.grupo.aplica(Prancheta.grupo.documento().operacoes));
      return { diferentes, distintas: ordensDistintas.size, n: ops.length, tela: tela === esperado,
               contador: Prancheta.grupo.documento().contador, maior: Math.max(...ops.map((o) => o.seq)),
               semRepetidas: new Set(Prancheta.grupo.documento().operacoes.map((o) => o.id)).size === ops.length };
    }""")
    assert r["diferentes"] == 0
    assert r["distintas"] == 600                      # 3 x 200 ordens, todas diferentes
    assert r["tela"] and r["semRepetidas"] and r["contador"] == r["maior"]
    assert not pg._erros


def test_a_mesma_sala_com_a_tela_converge_com_entrega_embaralhada(contexto, pagina_grupo):
    """Com o servidor falso embaralhando a entrega, a tela (membro com permissão) e a líder desenham juntas e
    terminam com o mesmo log e o mesmo estado."""
    pg, _ = membro_na_sala(contexto, pagina_grupo)
    pg.evaluate("async () => { await window.__lider.s.permite('u-tela', true); window.__servidorFalso.embaralhaMs = 40; }")
    pg.wait_for_function("() => Grupo._interno.podeDesenhar()")
    for i in range(4):
        arrasta_a_peca(pg, dx=20 + 10 * i, dy=10)
        pg.evaluate("""async (i) => { const L = window.__lider;
            await L.envia([L.op('move_peca', { peca: 'pecaztrike', passo: window.__passo, x: 100 * i, y: -50 * i })]); }""", i)
    pg.wait_for_function("""() => { const L = window.__lider, d = Prancheta.grupo.documento();
        return Grupo._interno.G().fila.length === 0 && d.operacoes.length === Object.keys(L.ops).length
               && d.operacoes.length === window.__servidorFalso.ops.length; }""", timeout=10000)
    iguais = pg.evaluate("() => JSON.stringify(window.__lider.estado()) === JSON.stringify(Prancheta._interno.S.estado)")
    assert iguais
    assert not pg._erros


# --- 2. permissão -------------------------------------------------------------

def test_sem_permissao_a_alteracao_e_recusada_desfeita_e_a_dica_diz_o_motivo(contexto, pagina_grupo):
    pg, _ = membro_na_sala(contexto, pagina_grupo)
    antes = posicao(pg)
    # a tela espelha o servidor: ferramentas de edição desligadas, com o motivo no title (§8)
    caneta = pg.locator('#pr-barra [data-ferramenta="caneta"]')
    assert caneta.is_disabled() and caneta.get_attribute("title") == "A líder não liberou desenho para você."
    assert pg.locator("#pr-desfaz").is_disabled()
    assert pg.inner_text("#gr-permissao") == "Só a líder desenha agora"
    # selecionar e mover continuam (o arrasto tenta; quem recusa é o servidor)
    arrasta_a_peca(pg)
    pg.wait_for_function("() => document.getElementById('pr-dica-estado').textContent === 'A líder não liberou desenho para você.'")
    assert posicao(pg) == antes                     # a recusa já tirou a operação do log
    assert not [o for o in interno(pg, "S.doc.operacoes") if o["tipo"] == "move_peca"]   # saiu do log
    assert interno(pg, "S.pilhaDesfazer.length") == 0
    assert pg.evaluate("() => window.__servidorFalso.ops.filter((l) => l.autor === 'u-tela').length") == 0

    # a líder libera: a mesma ação passa e chega à líder
    pg.evaluate("async () => window.__lider.s.permite('u-tela', true)")
    pg.wait_for_function("() => Grupo._interno.podeDesenhar() && !document.querySelector('#pr-barra [data-ferramenta=\"caneta\"]').disabled")
    assert pg.inner_text("#gr-permissao") == "Você pode desenhar"
    arrasta_a_peca(pg)
    pg.wait_for_function("() => Object.values(window.__lider.ops).some((o) => o.tipo === 'move_peca' && o.autor === 'spinx')")
    assert posicao(pg) != antes
    assert not pg._erros


def test_granada_desenhada_tambem_e_desenhar(contexto, pagina_grupo):
    """A granada desenhada da fase 11 (desenha_granada) é alteração da tática: sem permissão, o pincel fica
    desligado e a operação, se sair, é recusada pelo servidor e tirada do log."""
    pg, _ = membro_na_sala(contexto, pagina_grupo)
    pincel = pg.locator('#pr-barra [data-ferramenta="granada_desenho"]')
    assert pincel.is_disabled() and pincel.get_attribute("title") == "A líder não liberou desenho para você."
    pg.evaluate("""() => { const c = Prancheta._interno.centro();
        Prancheta._interno.emiteLote([['desenha_granada', { traco: 'gd1', passo: window.__passo, arma: 'smoke', x: c[0], y: c[1] }]]); }""")
    pg.wait_for_function("() => document.getElementById('pr-dica-estado').textContent === 'A líder não liberou desenho para você.'")
    assert not [o for o in interno(pg, "S.doc.operacoes") if o["tipo"] == "desenha_granada"]
    pg.evaluate("async () => window.__lider.s.permite('u-tela', true)")
    pg.wait_for_function("() => !document.querySelector('#pr-barra [data-ferramenta=\"granada_desenho\"]').disabled")
    pg.evaluate("""() => { const c = Prancheta._interno.centro();
        Prancheta._interno.emiteLote([['desenha_granada', { traco: 'gd2', passo: window.__passo, arma: 'flash', x: c[0], y: c[1] }]]); }""")
    pg.wait_for_function("() => Object.values(window.__lider.ops).some((o) => o.tipo === 'desenha_granada')")
    assert not pg._erros


def test_todos_podem_desenhar_libera_todos_e_expulsar_tira_o_acesso_na_hora(contexto, pagina_grupo):
    pg, codigo = membro_na_sala(contexto, pagina_grupo)
    # um terceiro, sem tela
    pg.evaluate(f"""async () => {{ const c = window.__cliente('u-ana', 'ana'); await c.s.prepara();
        await c.s.entrar('{codigo}', 'ana'); window.__ana = c; }}""")
    recusa = pg.evaluate("""async () => { const c = window.__ana;
        return (await c.envia([c.op('move_peca', { peca: 'pecaztrike', passo: window.__passo, x: 1, y: 1 })])).motivo; }""")
    assert recusa == "permissao"
    pg.evaluate("async () => window.__lider.s.todosPodem(true)")
    pg.wait_for_function("() => Grupo._interno.podeDesenhar()")
    assert pg.inner_text("#gr-permissao") == "Você pode desenhar"
    ok = pg.evaluate("""async () => { const c = window.__ana;
        return (await c.envia([c.op('move_peca', { peca: 'pecaztrike', passo: window.__passo, x: 2, y: 2 })])).ok; }""")
    assert ok
    arrasta_a_peca(pg)
    pg.wait_for_function("() => window.__servidorFalso.ops.some((l) => l.autor === 'u-tela')")

    # expulsar: o membro sai na hora, o servidor recusa leitura e escrita e ele não volta pela mesma conta
    pg.evaluate("async () => window.__lider.s.expulsa('u-tela')")
    pg.wait_for_function("() => Grupo._interno.G().fase === 'fora'")
    assert "A líder tirou você deste grupo." in pg.inner_text("#gr-status")
    assert not pg.locator('#pr-barra [data-ferramenta="caneta"]').is_disabled()   # a tática local volta a ser dela
    nada = pg.evaluate("""async () => { const s = Sala.SalaFalsa(window.__servidorFalso, { uid: 'u-tela' });
        const e = await s.entrar(arguments[0], 'spinx'); return e.motivo; }""".replace("arguments[0]", repr(codigo)))
    assert nada == "expulso"
    assert not pg._erros


# --- 3. desfazer em grupo -------------------------------------------------------

def test_cada_um_desfaz_so_o_que_e_seu(contexto, pagina_grupo):
    pg, _ = membro_na_sala(contexto, pagina_grupo)
    pg.evaluate("async () => window.__lider.s.permite('u-tela', true)")
    pg.wait_for_function("() => Grupo._interno.podeDesenhar()")
    arrasta_a_peca(pg, dx=60, dy=0)
    pg.wait_for_function("() => Object.values(window.__lider.ops).some((o) => o.autor === 'spinx')")
    # a líder, que já viu a do membro, move a mesma peça depois (vence pela ordem do log: seq maior)
    pg.evaluate("""async () => { const L = window.__lider;
        await L.envia([L.op('move_peca', { peca: 'pecaztrike', passo: window.__passo, x: 333, y: 444 })]); }""")
    pg.wait_for_function("() => JSON.stringify(Object.values(Prancheta._interno.S.estado.pecas.pecaztrike.posicoes).pop()) === '[333,444]'")
    # o membro desfaz: só a operação dele é anulada; a da líder continua valendo
    assert pg.evaluate("() => Prancheta._interno.desfaz()") is True
    pg.wait_for_function("() => window.__servidorFalso.ops.some((l) => l.op.tipo === 'anula')")
    anula = pg.evaluate("() => window.__servidorFalso.ops.filter((l) => l.op.tipo === 'anula').map((l) => l.op)")
    minha = pg.evaluate("() => window.__servidorFalso.ops.filter((l) => l.autor === 'u-tela' && l.op.tipo === 'move_peca')[0].op.id")
    assert len(anula) == 1 and anula[0]["alvo"] == minha and anula[0]["autor"] == "spinx"
    assert posicao(pg) == [333, 444]
    # nada mais na pilha: as operações da líder e as da criação nunca foram do desfazer do membro
    assert pg.evaluate("() => Prancheta._interno.desfaz()") is False
    pg.wait_for_function("() => JSON.stringify(window.__lider.estado()) === JSON.stringify(Prancheta._interno.S.estado)")
    assert not pg._erros


# --- 4. seguir a líder ----------------------------------------------------------

def test_o_cabecote_segue_a_lider_desligar_solta_e_voltar_religa(contexto, pagina_grupo):
    pg, _ = membro_na_sala(contexto, pagina_grupo)
    assert G(pg, "G.seguir") is True
    assert pg.get_attribute('[data-acao="seguir"]', "aria-pressed") == "true"
    pg.evaluate("() => window.__lider.s.anunciaCabecote({ modo: 'editor', t: 30 })")
    pg.wait_for_function("() => Prancheta._interno.S.t === 30")
    pg.evaluate("() => window.__lider.s.anunciaCabecote({ modo: 'reproducao', t: 12, tocando: false, velocidade: 2 })")
    pg.wait_for_function("() => !!Prancheta._interno.S.reproducao && Math.abs(Prancheta._interno.S.reproducao.t - 12) < 1e-6")
    assert interno(pg, "S.reproducao.velocidade") == 2 and interno(pg, "S.reproducao.tocando") is False
    pg.evaluate("() => window.__lider.s.anunciaCabecote({ modo: 'editor', t: 40 })")
    pg.wait_for_function("() => !Prancheta._interno.S.reproducao && Prancheta._interno.S.t === 40")
    # o membro mexe no cabeçote por conta própria: solta
    pg.evaluate("() => { const c = document.getElementById('pr-cabecote'); c.value = '5'; c.dispatchEvent(new Event('input')); }")
    assert G(pg, "G.seguir") is False
    assert pg.is_visible('[data-acao="voltar"]')
    pg.evaluate("() => window.__lider.s.anunciaCabecote({ modo: 'editor', t: 50 })")
    pg.wait_for_timeout(100)
    assert interno(pg, "S.t") == 5
    # "Voltar para a líder" religa e vai para onde ela está
    pg.evaluate("() => Prancheta._interno.abaDoPainel('grupo')")
    pg.click('[data-acao="voltar"]')
    assert G(pg, "G.seguir") is True and interno(pg, "S.t") == 50
    assert not pg._erros


def test_so_a_lider_transmite_o_cabecote(contexto, pagina_grupo):
    pg, codigo = membro_na_sala(contexto, pagina_grupo)
    r = pg.evaluate(f"""async () => {{ const c = window.__cliente('u-ana', 'ana'); await c.s.prepara();
        await c.s.entrar('{codigo}', 'ana'); return window.__servidorFalso.chama('u-ana', 'cabecote', {{ sala: Grupo._interno.G().salaId,
        estado: {{ modo: 'editor', t: 77 }} }}); }}""")
    assert r["motivo"] == "permissao"
    pg.wait_for_timeout(60)
    assert interno(pg, "S.t") != 77


# --- 5. reconexão ---------------------------------------------------------------

def test_cair_perder_50_operacoes_e_voltar_sem_duplicar(contexto, pagina_grupo):
    pg, _ = membro_na_sala(contexto, pagina_grupo)
    pg.evaluate("async () => window.__lider.s.permite('u-tela', true)")
    pg.wait_for_function("() => Grupo._interno.podeDesenhar()")
    pg.evaluate("() => window.__servidorFalso.derruba('u-tela')")
    pg.wait_for_function("() => document.getElementById('gr-erro') && document.getElementById('gr-erro').textContent.includes('Grupo indisponível agora. A tática continua salva neste navegador.')")
    # 50 operações da líder que a tela não recebe (em lotes de 10, no ritmo do servidor)
    pg.evaluate("""async () => { const L = window.__lider;
        for (let k = 0; k < 5; k++) {
          const lote = []; for (let i = 0; i < 10; i++) lote.push(L.op('move_peca', { peca: 'pecaztrike', passo: window.__passo, x: k * 10 + i, y: i }));
          const r = await L.envia(lote); if (!r.ok) throw new Error(r.motivo);
          await new Promise((ok) => setTimeout(ok, 1100));
        } }""")
    perdidas = pg.evaluate("() => window.__servidorFalso.ops.length - Prancheta.grupo.documento().operacoes.length")
    assert perdidas == 50
    # caída, a tela continua funcionando sozinha: a alteração fica aqui e sai quando a conexão voltar
    arrasta_a_peca(pg, dx=30, dy=30)
    assert G(pg, "G.fila.length") >= 1
    pg.evaluate("() => window.__servidorFalso.religa('u-tela')")
    pg.wait_for_function("""() => { const d = Prancheta.grupo.documento(), srv = window.__servidorFalso;
        return Grupo._interno.G().fila.length === 0 && d.operacoes.length === srv.ops.length; }""", timeout=10000)
    r = pg.evaluate("""() => { const d = Prancheta.grupo.documento(), srv = window.__servidorFalso;
        const ids = d.operacoes.map((o) => o.id);
        const L = window.__lider; srv.ops.forEach((l) => L.recebe(l));
        return { unicas: new Set(ids).size === ids.length, servidorUnicas: new Set(srv.ops.map((l) => l.op.id)).size === srv.ops.length,
                 iguais: JSON.stringify(L.estado()) === JSON.stringify(Prancheta._interno.S.estado),
                 erro: !!document.getElementById('gr-erro') }; }""")
    assert r == {"unicas": True, "servidorUnicas": True, "iguais": True, "erro": False}
    assert not pg._erros


# --- criar pela aba, painel da líder --------------------------------------------

def test_a_lider_cria_pela_aba_e_controla_o_grupo(contexto, pagina_grupo):
    pg = abre_grupo(contexto, pagina_grupo)
    pg.evaluate("() => Prancheta._interno.abaDoPainel('grupo')")
    assert Grupo_nada_pedido(pg)
    assert "O servidor guarda só o nick" in pg.inner_text("#pr-painel-grupo")
    pg.fill("#gr-nick", "nomad")
    pg.click('[data-acao="criar"]')
    pg.wait_for_function("() => Grupo._interno.G().fase === 'dentro'")
    codigo = pg.inner_text("#gr-codigo-sala")
    assert len(codigo) == 8 and all(c in "ABCDEFGHJKMNPQRSTUVWXYZ23456789" for c in codigo)
    # o estado inicial subiu: as operações que já existiam
    pg.wait_for_function("() => window.__servidorFalso.ops.length === Prancheta.grupo.documento().operacoes.length")
    pg.click('[data-acao="copiar"]')
    assert f"#sala={codigo}" in pg.inner_text("#gr-status")
    # alguém entra e aparece na lista; a líder libera e tira o desenho dele
    pg.evaluate(f"""async () => {{ const c = window.__cliente('u-ana', 'ana'); await c.s.prepara();
        await c.s.entrar('{codigo}', 'ana'); await c.liga(); window.__ana = c; }}""")
    pg.wait_for_selector('.gr-membro[data-usuario="u-ana"]')
    assert "online" in pg.inner_text('.gr-membro[data-usuario="u-ana"]')
    pg.click('.gr-membro[data-usuario="u-ana"] [data-acao="permite"]')
    pg.wait_for_function("() => document.querySelector('.gr-membro[data-usuario=\"u-ana\"] [data-acao=\"permite\"]').getAttribute('aria-pressed') === 'true'")
    pg.click('[data-acao="todos"]')
    pg.wait_for_function("() => Grupo._interno.G().todos === true")
    # a operação da líder chega a quem está na sala
    pg.evaluate("() => { const c = document.getElementById('pr-cabecote'); c.value = '20'; c.dispatchEvent(new Event('input')); }")
    pg.wait_for_function("() => window.__ana.cab && window.__ana.cab.t === 20")
    # encerrar pede confirmação e deixa tudo só leitura
    pg.click('[data-acao="encerrar"]')
    assert pg.is_visible('[data-acao="confirma-encerrar"]')
    pg.click('[data-acao="confirma-encerrar"]')
    pg.wait_for_function("() => Grupo._interno.G().encerrada === true")
    assert pg.locator('#pr-barra [data-ferramenta="caneta"]').is_disabled()
    r = pg.evaluate("""async () => { const c = window.__ana;
        return (await c.envia([c.op('renomeia', { titulo: 'depois' })])).motivo; }""")
    assert r == "permissao"
    assert not pg._erros


def test_transferir_lideranca(contexto, pagina_grupo):
    pg, _ = membro_na_sala(contexto, pagina_grupo)
    pg.evaluate("async () => window.__lider.s.transfere('u-tela')")
    pg.wait_for_function("() => Grupo._interno.G().papel === 'lider'")
    assert pg.is_visible('[data-acao="todos"]') and Grupo_podeDesenhar(pg)
    # a líder antiga perdeu os poderes no servidor
    r = pg.evaluate("async () => (await window.__lider.s.todosPodem(true))")
    assert pg.evaluate("() => Grupo._interno.G().todos") is False and r.get("dados") == []
    pg.click('[data-acao="transferir"]')
    pg.select_option("#gr-transferir-para", "u-lider")
    pg.click('[data-acao="confirma-transferir"]')
    pg.wait_for_function("() => Grupo._interno.G().papel === 'membro'")
    assert not pg._erros


def test_nick_e_dado_nunca_marcacao(contexto, pagina_grupo):
    pg, codigo = membro_na_sala(contexto, pagina_grupo)
    mau = '<img src=x onerror="window.__x=1">'
    pg.evaluate(f"""async () => {{ window.__servidorFalso.semCheckDeNick = true;
        const c = window.__cliente('u-mau', {mau!r}); await c.s.prepara(); await c.s.entrar('{codigo}', {mau!r}); await c.liga();
        await window.__lider.s.permite('u-mau', true);
        await c.envia([c.op('move_peca', {{ peca: 'pecaztrike', passo: window.__passo, x: 5, y: 5 }})]); }}""")
    pg.wait_for_selector('.gr-membro[data-usuario="u-mau"]')
    assert mau in pg.inner_text('.gr-membro[data-usuario="u-mau"]')
    assert pg.locator("#pr-painel-grupo img").count() == 0
    pg.wait_for_function(f"() => document.getElementById('pr-dica-estado').textContent.startsWith({mau!r})")
    assert pg.evaluate("() => window.__x") is None
    assert not pg._erros


def test_etiqueta_de_quem_alterou_some_em_3_segundos(contexto, pagina_grupo):
    pg, _ = membro_na_sala(contexto, pagina_grupo)
    pg.evaluate("""async () => { const L = window.__lider;
        await L.envia([L.op('move_peca', { peca: 'pecaztrike', passo: window.__passo, x: 9, y: 9 })]); }""")
    pg.wait_for_function("() => document.getElementById('pr-dica-estado').textContent === 'nomad moveu ztrike'")
    assert pg.evaluate("() => Grupo._interno.DURACAO_DA_ETIQUETA_MS") == 3000
    pg.wait_for_function("() => document.getElementById('pr-dica-estado').textContent !== 'nomad moveu ztrike'", timeout=4500)


def test_entrada_recusada_diz_por_que_e_nao_entra(contexto, pagina_grupo):
    pg = abre_grupo(contexto, pagina_grupo)
    codigo = pg.evaluate("async () => await window.__criaSala()")
    pg.evaluate("() => Prancheta._interno.abaDoPainel('grupo')")
    pg.fill("#gr-nick", "NOMAD")                                    # nick já usado (sem caixa)
    pg.fill("#gr-codigo", codigo)
    pg.click('[data-acao="entrar"]')
    pg.wait_for_function("() => document.getElementById('gr-status').textContent === 'Já tem alguém com esse nick no grupo.'")
    assert G(pg, "G.fase") == "fora"
    pg.fill("#gr-nick", "outro")
    pg.fill("#gr-codigo", "ABCDEFGH")
    pg.click('[data-acao="entrar"]')
    pg.wait_for_function("() => document.getElementById('gr-status').textContent === 'Nenhum grupo com esse código.'")


def test_o_link_da_sala_abre_a_aba_com_o_codigo(contexto, pagina_grupo):
    pg = contexto.new_page()
    pg.add_init_script(CLIENTES_JS)
    pg.goto(pagina_grupo.as_uri() + "#sala=K7M2Q9XR")
    pg.wait_for_function("() => !!document.getElementById('gr-codigo')")
    assert pg.input_value("#gr-codigo") == "K7M2Q9XR"
    assert pg.get_attribute("#pr-aba-grupo", "aria-selected") == "true"
    # abrir o link não faz pedido nenhum: só o clique em "Entrar"
    assert Grupo_nada_pedido(pg)


def Grupo_nada_pedido(pg):
    return pg.evaluate("() => !window.__servidorFalso || window.__servidorFalso.pedidos.length === 0")


def Grupo_podeDesenhar(pg):
    return pg.evaluate("() => Grupo._interno.podeDesenhar()")
