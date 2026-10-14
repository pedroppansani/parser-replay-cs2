"""Revisão de segurança dos grupos, parte do CLIENTE (fase 16b): B-1 (validar toda operação recebida) e B-3 (aviso
de privacidade), no navegador, com a SalaFalsa.

B-1: a líder (um atacante com a API direta) insere pelo `ServidorFalso.injeta` operações que o servidor aceita
mas que o cliente tem de recusar; a tela de quem está na sala continua a de antes, a dica avisa uma vez, o
console registra sem os dados, a página recarregada abre sem erro e a tática local não contém a operação. Uma
tática envenenada já salva abre como tática nova e o documento vai para a chave `...:recusada`.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from tests.operacoes_malformadas import MALFORMADAS, SEM_A_FORMA_MINIMA  # noqa: E402
from tests.test_grupos_browser import (  # noqa: E402,F401
    G, MAPA, abre_grupo, dica, entra_pela_aba, membro_na_sala, pagina_grupo,
)
from tests.test_tactics_browser import contexto, interno, navegador  # noqa: E402,F401

RAIZ = Path(__file__).resolve().parent.parent
AVISO = "Uma alteração recebida estava malformada e foi ignorada."


def injeta(pg, op, uid="u-lider"):
    """O que a líder faz pela API direta: a linha entra no servidor sem passar pela forma mínima do cliente."""
    pg.evaluate("""([sala, uid, t]) => { window.__servidorFalso.injeta(sala, uid, JSON.parse(t)); }""",
                [G(pg, "G.salaId"), uid, json.dumps(op)])
    pg.wait_for_timeout(60)         # a entrega do servidor falso (5 ms) e a reaplicação em microtarefa


def estado_e_log(pg):
    return pg.evaluate("() => { const S = Prancheta._interno.S; return [JSON.stringify(S.estado), S.doc.operacoes.length]; }")


def com_id_unico(rotulo, op, n):
    """Cada caso entra com id próprio (o servidor falso não repete id), menos os casos que testam o id."""
    if isinstance(op, dict) and not rotulo.startswith("id "):
        return {**op, "id": f"x{n:04d}"}
    return op


# --- B-1 ------------------------------------------------------------------------------------------------------

def test_operacao_malformada_vinda_da_sala_e_descartada_sem_mudar_a_tela(contexto, pagina_grupo):
    pg, _ = membro_na_sala(contexto, pagina_grupo)
    console = []
    pg.on("console", lambda m: console.append(m.text))
    passo = pg.evaluate("() => window.__passo")
    estado0, n0 = estado_e_log(pg)
    ultimo0 = G(pg, "G.ultimo.lamport")
    for n, (rotulo, op) in enumerate(MALFORMADAS + SEM_A_FORMA_MINIMA):
        if op is None:
            continue         # `null` nem chega a um cliente (o gatilho do servidor recusa), e o cliente de teste da líder não o lê
        op = com_id_unico(rotulo, op, n)
        if isinstance(op, dict) and op.get("passo") == "passo0001":
            op["passo"] = passo
        injeta(pg, op)
        assert estado_e_log(pg) == [estado0, n0], rotulo           # a tela segue a de antes e a operação não entrou no log
        if op:
            assert dica(pg).startswith(AVISO) or AVISO in dica(pg), (rotulo, dica(pg))
    assert not pg._erros, pg._erros
    # a reconexão não pula as operações boas por causa do Lamport gigante de uma operação recusada
    assert G(pg, "G.ultimo.lamport") == ultimo0
    # a boa que vem depois entra normalmente
    pg.evaluate("""async () => { const L = window.__lider; await L.envia([{ id: 'depois1', seq: 5000, autor: 'nomad', em: 'x', tipo: 'renomeia', titulo: 'depois' }]); }""")
    pg.wait_for_function("() => Prancheta._interno.S.estado.titulo === 'depois'")
    # o console diz que descartou, só com a contagem: nada da operação (nem o texto dos campos) vai para lá
    avisos = [t for t in console if "descartada" in t]
    assert avisos and all(re.fullmatch(r"\[prancheta\] \d+ alteração\(ões\) recebida\(s\) descartada\(s\) por formato inválido", t) for t in avisos), avisos
    juntos = " ".join(console)
    for proibido in ("atacante", "constructor", "__proto__", "explode", "origem", "x0000"):
        assert proibido not in juntos, proibido


def test_a_pagina_recarregada_abre_sem_erro_e_a_tatica_local_nao_tem_a_operacao(contexto, pagina_grupo):
    pg, _ = membro_na_sala(contexto, pagina_grupo)
    passo = pg.evaluate("() => window.__passo")
    ruins = [
        {"id": "ruim1", "seq": 50, "autor": "atacante", "em": "x", "tipo": "cria_granada", "granada": "g", "passo": passo,
         "origem": "x", "destino": [0, 0], "arma": "smoke"},              # o exemplo do relatório
        {"id": "ruim2", "seq": 51, "autor": "atacante", "em": "x", "tipo": "cria_traco", "traco": "t", "passo": passo,
         "ferramenta": "seta", "cor": "#eb6834", "espessura": 4, "pontos": 5},
    ]
    for op in ruins:
        injeta(pg, op)
    assert "ruim" not in json.dumps(pg.evaluate("() => Prancheta._interno.S.doc.operacoes.map((o) => o.id)"))
    pg.evaluate("() => Prancheta._interno.gravaAgora()")
    pg.reload()
    pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
    assert not pg._erros, pg._erros
    ids = pg.evaluate("() => Prancheta._interno.S.doc.operacoes.map((o) => o.id)")
    assert "ruim1" not in ids and "ruim2" not in ids
    guardado = pg.evaluate("""() => Object.keys(localStorage).filter((k) => k.includes('tatica:')).map((k) => localStorage.getItem(k)).join('|')""")
    assert "ruim1" not in guardado and "ruim2" not in guardado


def test_lote_que_derruba_o_reaplica_e_desfeito_e_as_boas_do_lote_ficam(contexto, pagina_grupo):
    """Uma operação que passa na validação mas faz o `reaplica` lançar (simulado: o relógio da tela lança quando o
    log tem a operação de título BOMBA) desfaz o lote; as outras do mesmo lote entram, uma por uma."""
    pg, _ = membro_na_sala(contexto, pagina_grupo)
    console = []
    pg.on("console", lambda m: console.append(m.text))
    pg.evaluate("""() => {
      const original = MapCore.relogio;
      window.__lancou = 0;
      MapCore.relogio = function () {
        if (Prancheta._interno.S.doc.operacoes.some((o) => o.titulo === 'BOMBA')) { window.__lancou++; throw new Error('boom'); }
        return original.apply(this, arguments);
      };
    }""")
    estado0, n0 = estado_e_log(pg)
    # as duas ao mesmo tempo (um lote): a boa e a que derruba
    pg.evaluate("""([sala]) => {
      const mk = (id, seq, titulo) => ({ id, seq, autor: 'atacante', em: 'x', tipo: 'renomeia', titulo });
      window.__servidorFalso.injeta(sala, 'u-lider', mk('lote1', 60, 'BOA'));
      window.__servidorFalso.injeta(sala, 'u-lider', mk('lote2', 61, 'BOMBA'));
    }""", [G(pg, "G.salaId")])
    pg.wait_for_function("() => Prancheta._interno.S.estado.titulo === 'BOA'")
    assert pg.evaluate("() => window.__lancou") > 0                    # o reaplica lançou de verdade
    ids = pg.evaluate("() => Prancheta._interno.S.doc.operacoes.map((o) => o.id)")
    assert "lote1" in ids and "lote2" not in ids
    assert AVISO in dica(pg)
    assert not pg._erros, pg._erros
    assert any("descartada" in t for t in console)
    # a prancheta segue viva: uma operação boa seguinte ainda entra
    pg.evaluate("""async () => { const L = window.__lider; await L.envia([L.op('renomeia', { titulo: 'viva' })]); }""")
    pg.wait_for_function("() => Prancheta._interno.S.estado.titulo === 'viva'")


def test_a_dica_avisa_uma_vez_por_lote_e_some_sozinha(contexto, pagina_grupo):
    pg, _ = membro_na_sala(contexto, pagina_grupo)
    sala = G(pg, "G.salaId")
    pg.evaluate("""([sala]) => {
      for (let i = 0; i < 5; i++) window.__servidorFalso.injeta(sala, 'u-lider',
        { id: 'mal' + i, seq: 70 + i, autor: 'a', em: 'x', tipo: 'cria_granada', granada: 'g' + i, passo: window.__passo, origem: 'x', destino: [0, 0], arma: 'smoke' });
    }""", [sala])
    pg.wait_for_function("() => document.getElementById('pr-dica-estado').innerText.includes('malformada')")
    assert dica(pg).count("malformada") == 1                          # uma frase para o lote inteiro
    pg.wait_for_function("() => !document.getElementById('pr-dica-estado').innerText.includes('malformada')", timeout=9000)


def test_tatica_envenenada_ja_salva_abre_como_tatica_nova_e_vai_para_a_chave_recusada(contexto, pagina_grupo):
    pg = abre_grupo(contexto, pagina_grupo)
    # o armazém do navegador chama `aplica` ao gravar; grava-se o texto cru, como estava no disco antes da correção
    id_ = pg.evaluate("""() => {
      const S = Prancheta._interno.S, passo = S.estado.passos[0].passo, doc = JSON.parse(JSON.stringify(S.doc));
      doc.operacoes.push({ id: 'envenenada1', seq: doc.contador + 1, autor: 'atacante', em: 'x', tipo: 'cria_granada',
                           granada: 'g', passo, origem: 'x', destino: [0, 0], arma: 'smoke' });
      doc.contador += 1;
      doc.operacoes.push({ id: 'ok0001', seq: doc.contador + 1, autor: 'eu', em: 'x', tipo: 'renomeia', titulo: 'Envenenada' });
      doc.contador += 1;
      localStorage.setItem('prancheta:tatica:' + doc.id, JSON.stringify(doc));
      localStorage.setItem('prancheta:indice', JSON.stringify({ [doc.id]: { id: doc.id, mapa: doc.mapa, titulo: 'Envenenada',
                                                                           atualizada_em: new Date().toISOString(), autores: ['eu'] } }));
      sessionStorage.setItem('prancheta:aberta:' + doc.mapa, doc.id);
      return doc.id;
    }""")
    # recarrega sem deixar o pagehide da página velha regravar a tática (ele grava a de memória, que é a boa)
    pg.evaluate("() => { Prancheta._interno.armazem().grava = () => true; }")
    pg.reload()
    pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
    assert not pg._erros, pg._erros
    # abriu uma tática NOVA (outra id, sem a operação envenenada) e avisou
    novo = pg.evaluate("() => Prancheta._interno.S.doc")
    assert novo["id"] != id_
    assert "envenenada1" not in json.dumps(novo)
    assert "formato inválido" in pg.inner_text("#pr-aviso")
    # o documento recusado está inteiro numa chave separada
    chave = f"prancheta:tatica:{id_}:recusada"
    guardado = pg.evaluate("(k) => localStorage.getItem(k)", chave)
    assert guardado and "envenenada1" in guardado and "ok0001" in guardado
    # e deixou de ser uma tática da biblioteca (não reabre sozinha nem trava a página de novo)
    assert pg.evaluate("(k) => localStorage.getItem(k)", f"prancheta:tatica:{id_}") is None
    assert id_ not in pg.evaluate("() => Object.keys(JSON.parse(localStorage.getItem('prancheta:indice') || '{}'))")


# --- B-3 ------------------------------------------------------------------------------------------------------

def texto_do_aviso(pg):
    return " ".join(pg.inner_text("#gr-guarda-texto").split())


def test_o_aviso_de_privacidade_diz_tudo_e_o_contato_e_uma_issue_do_github(contexto, pagina_grupo):
    pg = abre_grupo(contexto, pagina_grupo)
    pg.evaluate("() => Prancheta._interno.abaDoPainel('grupo')")
    esperado = pg.evaluate("() => Grupo._interno.O_QUE_GUARDA")
    assert texto_do_aviso(pg) == esperado
    for trecho in ("o nick", "quem está em cada grupo", "a tática inteira", "nomes de autor", "IP e navegador",
                   "30 dias é apagado", "peça no GitHub"):
        assert trecho in esperado, trecho
    link = pg.locator("#gr-guarda-texto a")
    assert link.get_attribute("href") == "https://github.com/pedroppansani/parser-replay-cs2/issues/new"
    assert link.inner_text() == "peça no GitHub"
    assert link.get_attribute("rel") == "noopener noreferrer"
    # aparece ANTES do botão "Criar grupo" (e do "Entrar num grupo")
    ordem = pg.evaluate("""() => { const p = document.getElementById('pr-painel-grupo'), a = document.getElementById('gr-guarda-texto'),
        b = p.querySelector('[data-acao="criar"]'), c = p.querySelector('[data-acao="entrar"]');
        return [!!(b.compareDocumentPosition(a) & Node.DOCUMENT_POSITION_FOLLOWING), !!(c.compareDocumentPosition(a) & Node.DOCUMENT_POSITION_FOLLOWING)]; }""")
    assert ordem == [True, True]
    # nenhum e-mail no site
    html = pg.content()
    assert "mailto:" not in html and not re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", pg.inner_text("body"))


def test_o_aviso_esta_no_documento_de_seguranca_com_o_mesmo_texto(contexto, pagina_grupo):
    pg = abre_grupo(contexto, pagina_grupo)
    esperado = pg.evaluate("() => Grupo._interno.O_QUE_GUARDA")
    doc = " ".join((RAIZ / "notas" / "seguranca" / "grupos.md").read_text(encoding="utf-8").split())
    assert esperado in doc
    assert "@" not in esperado


def test_antes_de_criar_o_grupo_a_tela_lista_os_nomes_de_autor_e_nao_regrava_nada(contexto, pagina_grupo):
    pg = abre_grupo(contexto, pagina_grupo)
    pg.evaluate("() => Prancheta._interno.abaDoPainel('grupo')")
    # sem nome no campo "autor" o autor é o padrão "anônimo": não é nome nenhum, a lista não aparece
    assert pg.locator("#gr-autores").count() == 0
    # com nomes (a pessoa preenche o campo e faz alterações; uma cópia de outra pessoa soma o dela)
    pg.evaluate("""() => { Prancheta._interno.armazem().autor('Maria Silva'); }""")
    pg.evaluate("""() => {
      const S = Prancheta._interno.S, passo = S.estado.passos[0].passo;
      S.doc.criada_por = 'Maria Silva';
      S.doc.operacoes.push({ id: 'cop1', seq: S.doc.contador + 1, autor: 'João Souza', em: 'x', tipo: 'renomeia', titulo: 'Tática' });
      S.doc.contador += 1;
      S.doc.operacoes.push({ id: 'cop2', seq: S.doc.contador + 1, autor: 'Maria Silva', em: 'x', tipo: 'renomeia_passo', passo, titulo: 'a' });
      S.doc.contador += 1;
      Prancheta._interno.defineTempo(0);       // qualquer atualização da tela
    }""")
    pg.wait_for_selector("#gr-autores")
    frase = " ".join(pg.inner_text("#gr-autores").split())
    assert frase == "Esta tática tem estes nomes de autor, que vão para o servidor: Maria Silva, João Souza."
    antes = pg.evaluate("() => JSON.stringify(Prancheta._interno.S.doc.operacoes)")
    # criar o grupo manda as operações como estão: nenhuma é regravada (decisão 47)
    pg.fill("#gr-nick", "maria")
    pg.click('[data-acao="criar"]')
    pg.wait_for_function("() => Grupo._interno.G().fase === 'dentro'")
    # fase 16b (servidor): o estado inicial vai numa linha só (cria_sala), não mais como linhas de `operacoes`
    pg.wait_for_function("() => window.__servidorFalso.inicialDe(Grupo._interno.G().salaId).length >= 4")
    no_servidor = pg.evaluate("() => window.__servidorFalso.inicialDe(Grupo._interno.G().salaId)")
    local = json.loads(antes)
    assert [o for o in no_servidor if o["id"] in {x["id"] for x in local}] == local
    assert pg.evaluate("() => Prancheta._interno.S.doc.operacoes.map((o) => o.autor)").count("João Souza") == 1
    # dentro do grupo, o aviso de antes de criar some junto com o formulário
    assert pg.locator("#gr-autores").count() == 0


def test_o_aviso_tambem_aparece_no_convite_sem_a_lista_de_nomes(contexto, pagina_grupo):
    pg = abre_grupo(contexto, pagina_grupo)
    pg.evaluate("() => localStorage.setItem('prancheta:grupo-nick', 'spinx')")
    pg.goto(pagina_grupo.as_uri() + "#sala=ABCDEFGH")
    pg.reload()
    pg.wait_for_function("() => !!document.getElementById('gr-entrar-convite')")
    assert texto_do_aviso(pg) == pg.evaluate("() => Grupo._interno.O_QUE_GUARDA")
    assert pg.locator("#gr-autores").count() == 0
