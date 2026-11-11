"""C2: a aba Comandos da prancheta. O leitor (C1) está testado à parte; aqui, a tela: o que o site mostra que entendeu, as perguntas, o Aplicar num lote só
(um desfazer), o tempo de corrida estimado e dito, a troca de andar sem estimativa, e o mapa que não muda de tamanho."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from tests.test_tactics_browser import (  # noqa: E402,F401  (fixtures e ajudas)
    abre, aba_do_painel, arrasta_do_banco, contexto, interno, navegador, pagina_do_mapa)

CAIXA = "() => { const r = document.getElementById('pr-mapa').getBoundingClientRect(); return [Math.round(r.width * 10) / 10, Math.round(r.height * 10) / 10]; }"


def _pagina(contexto, tmp_path_factory, mapa="de_mirage", largura=1440, altura=900):
    pg = abre(contexto, pagina_do_mapa(tmp_path_factory, mapa))
    pg.set_viewport_size({"width": largura, "height": altura})
    return pg


def _escreve(pg, frase):
    aba_do_painel(pg, "comandos")
    pg.fill("#pr-cmd-texto", frase)
    pg.click("#pr-cmd-entender")


def _ops(pg):
    return interno(pg, "S.doc.operacoes.map(o => o.tipo)")


def _poe_ficha(pg, lado, rotulo, fx=0.5, fy=0.5):
    aba_do_painel(pg, "jogadores")
    arrasta_do_banco(pg, lado, rotulo, fx, fy)


def test_a_aba_comandos_fica_entre_granadas_e_tatica_sem_erro_de_pagina(contexto, tmp_path_factory):
    pg = _pagina(contexto, tmp_path_factory)
    assert pg.eval_on_selector_all("#pr-abas [role=tab]", "els => els.map(e => e.textContent)") == ["Jogadores", "Granadas", "Comandos", "Tática"]
    aba_do_painel(pg, "comandos")
    assert pg.is_visible("#pr-cmd-texto") and pg.is_visible("#pr-cmd-entender") and pg.is_hidden("#pr-cmd-acoes")
    assert pg.get_attribute("#pr-cmd-texto", "maxlength") == "300"
    assert not [e for e in pg._erros if "Failed to load" not in e]


def test_entender_nao_muda_a_tatica_e_mostra_o_que_entendeu(contexto, tmp_path_factory):
    pg = _pagina(contexto, tmp_path_factory)
    antes = _ops(pg)
    _escreve(pg, "tr 2 joga smoke no B aos 1:30 e depois corre até o meio")
    linhas = pg.locator("#pr-cmd-entendi li").all_inner_texts()
    assert linhas == ["TR 2 · Smoke em B · aos 1:30", "TR 2 · correndo até Meio · depois"]
    assert _ops(pg) == antes                                                              # nada muda no mapa até aplicar
    assert pg.is_disabled("#pr-cmd-aplicar")                                              # TR 2 não está no mapa
    assert "TR 2 ainda não está no mapa" in pg.inner_text("#pr-cmd-resultado")


def test_o_exemplo_do_pedro_aplicado_vira_um_lote_e_um_desfazer_volta_tudo(contexto, tmp_path_factory):
    pg = _pagina(contexto, tmp_path_factory)
    _poe_ficha(pg, "t", "2", 0.3, 0.3)
    antes = _ops(pg)
    _escreve(pg, "tr 2 joga uma molotov na caverna aos 1:20 e roda pra TV correndo")
    linhas = pg.locator("#pr-cmd-entendi li").all_inner_texts()
    assert linhas[0].startswith("TR 2 · Molotov em Caverna · aos 1:20") and linhas[1].startswith("TR 2 · correndo até TV · depois")
    assert "chega não antes de" in linhas[1] and "estimado" in linhas[1]                  # o tempo de corrida é estimado e a tela diz
    assert "Ainda não busco o arremesso real" in pg.inner_text("#pr-cmd-origem")           # a granada sai de onde o jogador está: dito, sem prometer o arremesso real
    assert pg.is_enabled("#pr-cmd-aplicar")
    pg.click("#pr-cmd-aplicar")
    novas = _ops(pg)[len(antes):]
    assert novas.count("cria_granada") == 1 and novas.count("cria_caminho") >= 1 and set(novas) <= {"cria_granada", "cria_caminho"}
    g = interno(pg, "Object.values(S.e3.granadas)[0]")
    assert g["arma"] == "molotov" and abs(g["t"] - 35) < 0.01 and g["jogador"] is not None
    assert interno(pg, "I.problemas(JSON.parse(JSON.stringify(S.doc)), 1)") == []         # a validação do site aceita as operações
    assert "Aplicado" in pg.inner_text("#pr-cmd-resultado") and pg.input_value("#pr-cmd-texto") == ""
    roteiro = pg.locator("#pr-roteiro .pr-evento-texto").all_inner_texts()                # a ficha ficou parada até o horário do comando: o roteiro diz "fica", não "chega"
    assert any(" fica em " in r and " até 1:20" in r for r in roteiro) and not any(r.startswith("TR 2 chega em") and r.endswith(" 1:20") for r in roteiro)
    pg.evaluate("() => Prancheta._interno.desfaz()")                                       # UM desfazer volta o comando inteiro
    assert "Aplicado" not in pg.inner_text("#pr-cmd-resultado")                            # e o aviso de "Aplicado" some com o desfazer
    assert interno(pg, "Object.keys(S.e3.granadas).length") == 0
    assert interno(pg, "Object.values(S.e3.pecas).flatMap(p => p.pontos).filter(pt => pt.caminho).length") == 0


def test_pergunta_uma_de_cada_vez_com_botoes_e_horario_digitado(contexto, tmp_path_factory):
    pg = _pagina(contexto, tmp_path_factory)
    _escreve(pg, "o jogador 2 joga smoke na caverna")
    assert "De qual time é" in pg.inner_text(".pr-cmd-pergunta-texto")
    assert pg.locator(".pr-cmd-opcao").all_inner_texts() == ["TR 2", "CT 2"]
    pg.click(".pr-cmd-opcao >> text=TR 2")
    assert "Quando começa" in pg.inner_text(".pr-cmd-pergunta-texto")
    pg.fill("#pr-cmd-horario", "1:20")
    pg.press("#pr-cmd-horario", "Enter")
    assert pg.locator("#pr-cmd-entendi li").all_inner_texts() == ["TR 2 · Smoke em Caverna · aos 1:20"]
    assert pg.locator(".pr-cmd-pergunta").count() == 0


def test_horario_fora_do_round_e_palavra_desconhecida_nao_passam(contexto, tmp_path_factory):
    pg = _pagina(contexto, tmp_path_factory)
    _poe_ficha(pg, "t", "2")
    _escreve(pg, "tr 2 vai pro meio aos 1:00 rapidinho")
    assert pg.is_disabled("#pr-cmd-aplicar") and "rapidinho" in pg.inner_text("#pr-cmd-resultado")
    pg.click("#pr-cmd-corrigir")
    assert pg.evaluate("() => document.activeElement.id") == "pr-cmd-texto" and pg.is_hidden("#pr-cmd-acoes")
    _escreve(pg, "ct 3 corre pro meio")
    pg.fill("#pr-cmd-horario", "3:20")
    pg.press("#pr-cmd-horario", "Enter")
    assert "não existe no round" in pg.inner_text("#pr-cmd-resultado") and pg.is_disabled("#pr-cmd-aplicar")


def _pagina_da_nuke_com_todos_os_pontos(contexto, tmp_path_factory):
    """Os pontos da Nuke ainda não estão conferidos (a página de produção não os traz); o teste monta a página com todos, para exercer a troca de andar."""
    from scripts import build_tactics_page as bt
    from scripts.comandos_contexto import contexto as contexto_do_mapa
    original = bt._comandos
    bt._comandos = lambda mapa, tempos_externos=False: {k: v for k, v in contexto_do_mapa(mapa).items() if k != "jogadores"}
    try:
        html = tmp_path_factory.mktemp("nuke_todos") / "prancheta_de_nuke.html"
        html.write_text(bt.build_html("de_nuke"), encoding="utf-8")
    finally:
        bt._comandos = original
    pg = abre(contexto, html)
    pg.set_viewport_size({"width": 1440, "height": 900})
    return pg


def test_na_pagina_de_producao_so_os_mapas_conferidos_trazem_os_pontos_do_pedro(contexto, tmp_path_factory):
    pg = _pagina(contexto, tmp_path_factory, "de_nuke")
    pg.evaluate("() => Prancheta._interno.abaDoPainel('comandos')")
    assert "ainda não foram conferidos" in pg.inner_text("#pr-cmd-nomes")                  # Nuke: valem os nomes do jogo, em inglês
    _escreve(pg, "tr 2 vai pro silo aos 1:00")
    assert pg.locator("#pr-cmd-entendi li").all_inner_texts() == ["TR 2 · correndo até Silo · aos 1:00"]   # a área da demo, sem pergunta de andar


def test_troca_de_andar_nao_estima_o_tempo_e_pergunta_a_chegada(contexto, tmp_path_factory):
    pg = _pagina_da_nuke_com_todos_os_pontos(contexto, tmp_path_factory)
    _poe_ficha(pg, "t", "2", 0.5, 0.35)
    _escreve(pg, "tr 2 vai pro silo aos 1:00")
    pg.click(".pr-cmd-opcao >> text=baixo")
    assert "Não estimei o tempo por causa da troca de andar" in pg.inner_text(".pr-cmd-pergunta-texto")
    assert pg.is_disabled("#pr-cmd-aplicar") and "chega por volta de" not in pg.inner_text("#pr-cmd-entendi")      # nada de linha reta
    pg.fill("#pr-cmd-horario", "0:50")
    pg.press("#pr-cmd-horario", "Enter")
    assert pg.is_enabled("#pr-cmd-aplicar")
    pg.click("#pr-cmd-aplicar")
    pts = interno(pg, "Object.values(S.e3.pecas).flatMap(p => p.pontos).filter(pt => pt.caminho && pt.nivel === 1)")
    assert len(pts) == 1 and abs(pts[0]["t"] - 65) < 0.01                                   # chega às 0:50 (65 s do início), o que a pessoa disse


def test_o_mapa_nao_muda_de_tamanho_ao_escrever_perguntar_e_aplicar(contexto, tmp_path_factory):
    pg = _pagina(contexto, tmp_path_factory)
    _poe_ficha(pg, "t", "2")
    tamanho = pg.evaluate(CAIXA)
    _escreve(pg, "o 2 joga smoke na b aos 1:30")
    assert pg.evaluate(CAIXA) == tamanho
    pg.click(".pr-cmd-opcao >> text=TR 2")
    assert pg.evaluate(CAIXA) == tamanho
    pg.click("#pr-cmd-aplicar")
    assert pg.evaluate(CAIXA) == tamanho


@pytest.mark.parametrize("largura,altura", [(375, 812), (1366, 657), (1440, 900)])
def test_nada_estoura_a_largura_e_os_controles_tem_area_de_toque(contexto, tmp_path_factory, largura, altura):
    pg = _pagina(contexto, tmp_path_factory, largura=largura, altura=altura)
    _escreve(pg, "o jogador 2 joga a molotov na caverna aos 1:20 e roda pra tv correndo")
    pg.wait_for_timeout(100)
    assert pg.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")
    for sel in ("#pr-cmd-entender", "#pr-cmd-corrigir", ".pr-cmd-opcao"):
        c = pg.locator(sel).first.bounding_box()
        assert c["height"] >= 40, (sel, c)


def test_a_pergunta_recebe_o_foco_e_o_cartao_acompanha_a_tatica(contexto, tmp_path_factory):
    pg = _pagina(contexto, tmp_path_factory)
    _escreve(pg, "o jogador 2 joga smoke na caverna")
    assert "pr-cmd-opcao" in pg.evaluate("() => document.activeElement.className")                 # a primeira opção, para quem usa o teclado
    pg.keyboard.press("Enter")                                                                      # TR 2 (primeira opção)
    assert pg.evaluate("() => document.activeElement.id") == "pr-cmd-horario"                       # a pergunta do horário leva o foco ao campo
    pg.fill("#pr-cmd-horario", "1:20")
    pg.press("#pr-cmd-horario", "Enter")
    assert pg.is_disabled("#pr-cmd-aplicar") and "ainda não está no mapa" in pg.inner_text("#pr-cmd-resultado")
    _poe_ficha(pg, "t", "2")                                                                        # a ficha entra depois de "Entender"
    aba_do_painel(pg, "comandos")
    assert pg.is_enabled("#pr-cmd-aplicar") and "ainda não está no mapa" not in pg.inner_text("#pr-cmd-resultado")


def test_num_round_real_as_fichas_tem_nome_e_a_aba_avisa(contexto, tmp_path_factory):
    """Em round real a ficha se chama pelo nome do jogador: "TR 2" não vale; a aba diz, em vez de só "ainda não está no mapa"."""
    pg = _pagina(contexto, tmp_path_factory)
    aba_do_painel(pg, "comandos")
    assert pg.locator("#pr-cmd-round").count() == 0
    pg.evaluate("""() => { const I = Prancheta._interno, S = I.S;
        I.emiteLote([["cria_peca", { peca: "demo-niko", lado: "t", rotulo: "NiKo", passo: S.estado.passos[0].passo, x: 0, y: 0, nivel: 0 }]]); }""")
    assert "têm o nome do jogador" in pg.inner_text("#pr-cmd-round")
    pg.evaluate("() => Prancheta._interno.desfaz()")
    assert pg.locator("#pr-cmd-round").count() == 0


def test_segundos_soltos_na_resposta_pedem_relogio_ou_inicio_em_vez_de_calar(contexto, tmp_path_factory):
    pg = _pagina(contexto, tmp_path_factory)
    _escreve(pg, "tr 2 joga smoke na b")
    pg.fill("#pr-cmd-horario", "40 segundos")
    pg.press("#pr-cmd-horario", "Enter")
    assert "40 segundos contados como?" in pg.inner_text("#pr-cmd-resultado")
    pg.fill("#pr-cmd-horario", "40 s do início")
    pg.press("#pr-cmd-horario", "Enter")
    assert pg.locator("#pr-cmd-entendi li").all_inner_texts() == ["TR 2 · Smoke em B · aos 40 s do início"]
