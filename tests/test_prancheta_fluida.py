"""Prancheta fluida (2026-09-27): cada clique faz uma coisa previsível, e a
linha de dica diz qual é ANTES do clique. Playwright + Chrome, na mesma página
dos testes de test_tactics_browser.py (de onde vêm os fixtures).

Nada aqui cria operação nova: os testes conferem que o clique emite as MESMAS
operações do arrasto (move_peca, gira_peca, cria_peca, cria_granada).
"""
from __future__ import annotations

import math

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_tactics_browser import (clica, preenche, aba_do_painel,  # noqa: E402,F401  (fixtures)
    abre, arrasta_do_banco, caixa, contexto, interno, navegador, no_mapa, pagina,
)


def ops(pg, tipo):
    return [o for o in interno(pg, "S.doc.operacoes") if o["tipo"] == tipo]


def solta_foco(pg):
    pg.evaluate("() => document.activeElement && document.activeElement.blur && document.activeElement.blur()")


def clica_ficha(pg, lado, rotulo):
    pg.click(f'.pr-ficha.{lado}[data-rotulo="{rotulo}"]')


def pos_da_peca(pg, pid):
    p = interno(pg, f"I.quadroDoPasso(S.estado, S.passo, I.centro()).pecas['{pid}']")
    return p["x"], p["y"]


def jogo_do_ponto(pg, fx, fy):
    """Coordenada de jogo do ponto (fx, fy) da caixa do mapa, sem zoom."""
    r = interno(pg, "I.radar().width")
    return interno(pg, f"I.pixelParaJogo({r} * {fx}, {r} * {fy})")


def coloca(pg, lado, rotulo, fx, fy):
    clica_ficha(pg, lado, rotulo)
    pg.mouse.click(*no_mapa(pg, fx, fy))
    return interno(pg, "S.sel.id")


def test_clique_para_mover_emite_um_move_peca_na_posicao_do_segundo_clique(contexto, pagina):
    pg = abre(contexto, pagina)
    pid = coloca(pg, "ct", "1", 0.4, 0.4)
    antes = len(ops(pg, "move_peca"))
    # fase 8a: mover é ARRASTAR (clicar na peça traça caminho); a peça vai do
    # lugar dela até o ponto onde é solta, acima do limiar de arrasto
    x0, y0 = no_mapa(pg, 0.4, 0.4)
    x1, y1 = no_mapa(pg, 0.6, 0.55)
    pg.mouse.move(x0, y0); pg.mouse.down(); pg.mouse.move(x1, y1, steps=8); pg.mouse.up()
    movs = ops(pg, "move_peca")
    assert len(movs) == antes + 1
    alvo = jogo_do_ponto(pg, 0.6, 0.55)
    tol = 2 * interno(pg, "I.radar().width") / caixa(pg)["width"] / interno(pg, "I.radar().scale_px_per_unit")
    assert abs(movs[-1]["x"] - alvo[0]) <= tol and abs(movs[-1]["y"] - alvo[1]) <= tol
    assert movs[-1]["peca"] == pid


def test_clique_no_banco_cria_e_clique_na_ficha_no_mapa_so_seleciona(contexto, pagina):
    pg = abre(contexto, pagina)
    clica_ficha(pg, "t", "2")
    assert interno(pg, "I.estadoDaInteracao()") == "colocando_peca"
    pg.mouse.click(*no_mapa(pg, 0.3, 0.6))
    assert len(ops(pg, "cria_peca")) == 1
    pid = interno(pg, "S.sel.id")
    interno(pg, "(S.sel = null, 0)")
    clica_ficha(pg, "t", "2")                        # já está no mapa: seleciona, sem criar
    assert len(ops(pg, "cria_peca")) == 1
    assert interno(pg, "S.sel") == {"tipo": "peca", "id": pid}
    assert interno(pg, "I.estadoDaInteracao()") == "peca_selecionada"


def test_granada_a_partir_da_selecao_sai_da_peca_e_a_peca_continua_selecionada(contexto, pagina):
    pg = abre(contexto, pagina)
    pid = coloca(pg, "ct", "2", 0.45, 0.5)
    solta_foco(pg)
    pg.keyboard.press("1")
    assert interno(pg, "I.estadoDaInteracao()") == "granada_destino"
    pg.mouse.click(*no_mapa(pg, 0.6, 0.35))
    (g,) = ops(pg, "cria_granada")
    assert g["arma"] == "smoke"
    x, y = pos_da_peca(pg, pid)
    assert (g["origem"][0], g["origem"][1]) == (x, y)
    assert interno(pg, "S.sel") == {"tipo": "peca", "id": pid}


def test_tres_granadas_do_mesmo_jogador_em_seis_acoes(contexto, pagina):
    pg = abre(contexto, pagina)
    coloca(pg, "ct", "3", 0.45, 0.5)
    solta_foco(pg)
    for tecla, fx in (("1", 0.6), ("2", 0.65), ("4", 0.7)):
        pg.keyboard.press(tecla)
        pg.mouse.click(*no_mapa(pg, fx, 0.35))
    assert [g["arma"] for g in ops(pg, "cria_granada")] == ["smoke", "flash", "molotov"]


def test_granada_sem_selecao_escolhe_a_peca_como_origem(contexto, pagina):
    pg = abre(contexto, pagina)
    pid = coloca(pg, "t", "4", 0.35, 0.4)
    interno(pg, "(S.sel = null, 0)")
    solta_foco(pg)
    pg.keyboard.press("2")
    assert interno(pg, "I.estadoDaInteracao()") == "granada_origem"
    pg.mouse.click(*no_mapa(pg, 0.35, 0.4))           # na peça: ela é a origem
    assert interno(pg, "I.estadoDaInteracao()") == "granada_destino"
    pg.mouse.click(*no_mapa(pg, 0.55, 0.3))
    (g,) = ops(pg, "cria_granada")
    assert g["arma"] == "flash"
    assert (g["origem"][0], g["origem"][1]) == pos_da_peca(pg, pid)


def test_botao_direito_vira_a_peca_para_o_ponto_sem_menu_do_navegador(contexto, pagina):
    pg = abre(contexto, pagina)
    pid = coloca(pg, "ct", "5", 0.5, 0.5)
    pg.mouse.click(*no_mapa(pg, 0.7, 0.3), button="right")
    (gira,) = ops(pg, "gira_peca")
    x, y = pos_da_peca(pg, pid)
    alvo = jogo_do_ponto(pg, 0.7, 0.3)
    esperado = math.degrees(math.atan2(alvo[1] - y, alvo[0] - x)) % 360
    assert abs(((gira["yaw"] - esperado + 180) % 360) - 180) <= 1.0
    bloqueado = pg.evaluate("""() => {
      const e = new MouseEvent('contextmenu', {bubbles: true, cancelable: true});
      return !document.getElementById('pr-mapa').dispatchEvent(e);
    }""")
    assert bloqueado, "o menu de contexto do navegador não foi desligado no mapa"


def test_esc_desfaz_um_nivel_por_vez(contexto, pagina):
    pg = abre(contexto, pagina)
    pid = coloca(pg, "ct", "1", 0.5, 0.5)
    solta_foco(pg)
    pg.keyboard.press("2")                            # origem pendente: a peça
    assert interno(pg, "I.estadoDaInteracao()") == "granada_destino"
    pg.keyboard.press("Escape")
    assert interno(pg, "S.acao") is None
    assert interno(pg, "S.sel") == {"tipo": "peca", "id": pid}
    pg.keyboard.press("Escape")
    assert interno(pg, "S.sel") is None
    assert interno(pg, "I.estadoDaInteracao()") == "livre"


def test_clique_contra_arrasto_pelo_limiar(contexto, pagina):
    pg = abre(contexto, pagina)
    pid = coloca(pg, "t", "1", 0.4, 0.4)
    limiar = interno(pg, "I.LIMIAR_ARRASTO_PX")
    # fase 8a: a peça chega a (0.6, 0.6) por arrasto (mover por clique saiu)
    x0, y0 = no_mapa(pg, 0.4, 0.4)
    x, y = no_mapa(pg, 0.6, 0.6)
    pg.mouse.move(x0, y0); pg.mouse.down(); pg.mouse.move(x, y, steps=8); pg.mouse.up()
    assert len(ops(pg, "move_peca")) == 1
    # abaixo do limiar, sobre a peça: é CLIQUE (traça caminho, não move)
    pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(x + limiar / 2, y, steps=2); pg.mouse.up()
    assert len(ops(pg, "move_peca")) == 1 and interno(pg, "I.estadoDaInteracao()") == "tracando_caminho"
    pg.keyboard.press("Escape")
    # acima do limiar, sobre a peça: é ARRASTO, e continua emitindo UM move_peca
    px, py = no_mapa(pg, 0.6, 0.6)
    pg.mouse.move(px, py); pg.mouse.down(); pg.mouse.move(px + 60, py + 30, steps=6); pg.mouse.up()
    assert len(ops(pg, "move_peca")) == 2
    assert ops(pg, "move_peca")[-1]["peca"] == pid


def test_selecao_segue_entre_passos(contexto, pagina):
    pg = abre(contexto, pagina)
    pid = coloca(pg, "ct", "2", 0.5, 0.5)
    solta_foco(pg)
    pg.keyboard.press("n")                            # novo passo, e vai para ele
    assert interno(pg, "S.passo") == 1
    assert interno(pg, "S.sel") == {"tipo": "peca", "id": pid}
    pg.keyboard.press(",")
    assert interno(pg, "S.passo") == 0 and interno(pg, "S.sel.id") == pid
    pg.keyboard.press(".")
    assert interno(pg, "S.passo") == 1 and interno(pg, "S.sel.id") == pid


def test_a_dica_mostra_o_texto_do_estado_em_cada_estado_da_tabela(contexto, pagina):
    pg = abre(contexto, pagina)
    estados = set(interno(pg, "Object.keys(I.ESTADOS)"))
    vistos = set()

    def confere(esperado):
        assert interno(pg, "I.estadoDaInteracao()") == esperado
        texto = pg.locator("#pr-dica-estado").inner_text()
        assert texto == interno(pg, "I.dicaAtual()") and texto
        vistos.add(esperado)

    confere("livre")
    clica_ficha(pg, "ct", "3"); confere("colocando_peca")
    pg.mouse.click(*no_mapa(pg, 0.5, 0.5)); confere("peca_selecionada")
    assert "CT 3 selecionado" in pg.locator("#pr-dica-estado").inner_text()
    # fase 8a: clicar na peça traça caminho; Esc volta à peça selecionada
    pg.mouse.click(*no_mapa(pg, 0.5, 0.5)); confere("tracando_caminho")
    pg.keyboard.press("Escape"); confere("peca_selecionada")
    solta_foco(pg)
    pg.keyboard.press("1"); confere("granada_destino")
    pg.mouse.click(*no_mapa(pg, 0.6, 0.4))
    interno(pg, "(S.sel = null, S.busca = null, S.sugestao = null, 0)")
    pg.keyboard.press("2"); confere("granada_origem")
    pg.keyboard.press("Escape")
    gid = interno(pg, "Object.keys(S.estado.granadas)[0]")
    interno(pg, f"(S.sel = {{tipo: 'granada', id: '{gid}'}}, 0)")
    pg.click("#pr-selecionar"); interno(pg, f"(S.sel = {{tipo: 'granada', id: '{gid}'}}, 0)")
    pg.evaluate("() => Prancheta._interno.reprojeta()")
    pg.mouse.click(*no_mapa(pg, 0.6, 0.4)); confere("granada_selecionada")
    pg.click('#pr-barra [data-ferramenta="caneta"]'); confere("desenhando")
    clica(pg, 'aside [data-ferramenta="buscar"]'); confere("buscando")
    assert vistos == estados, estados - vistos


def test_atalhos_sem_tecla_repetida_e_painel_de_ajuda_lista_todos(contexto, pagina):
    pg = abre(contexto, pagina)
    atalhos = interno(pg, "I.ATALHOS")
    teclas = [a["tecla"] for a in atalhos]
    assert len(teclas) == len(set(teclas)), "tecla repetida no mapa de atalhos"
    solta_foco(pg)
    pg.keyboard.press("?")
    painel = pg.locator("#pr-ajuda")
    assert painel.is_visible()
    assert painel.locator("dt").count() == len(atalhos)
    for a in atalhos:
        assert a["acao"] in painel.inner_text()
    pg.keyboard.press("Escape")
    assert pg.locator("#pr-ajuda").count() == 0


def test_texto_no_mapa_sem_window_prompt(contexto, pagina):
    pg = abre(contexto, pagina)
    pg.evaluate("() => { window.__prompts = 0; window.prompt = () => { window.__prompts++; return 'x'; }; }")
    solta_foco(pg)
    pg.keyboard.press("t")
    pg.mouse.click(*no_mapa(pg, 0.3, 0.3))
    campo = pg.locator("#pr-editor-texto")
    assert campo.is_visible()
    campo.fill("smoke no CT")
    campo.press("Enter")
    (tr,) = ops(pg, "cria_traco")
    assert tr["ferramenta"] == "texto" and tr["texto"] == "smoke no CT"
    pg.mouse.click(*no_mapa(pg, 0.6, 0.6))
    pg.locator("#pr-editor-texto").fill("não vale")
    pg.locator("#pr-editor-texto").press("Escape")
    assert len(ops(pg, "cria_traco")) == 1
    assert pg.evaluate("() => window.__prompts") == 0


def test_cor_e_espessura_so_aparecem_com_ferramenta_de_desenho(contexto, pagina):
    pg = abre(contexto, pagina)
    ctx = pg.locator("#pr-contexto-desenho")
    assert not ctx.is_visible()
    pg.click('#pr-barra [data-ferramenta="seta"]')
    assert ctx.is_visible()
    pg.click("#pr-selecionar")
    assert not ctx.is_visible()
    assert not pg.locator("#pr-filtros-busca").is_visible()
    aba_do_painel(pg, "granadas")
    clica(pg, 'aside [data-ferramenta="buscar"]')
    assert pg.locator("#pr-filtros-busca").is_visible()


def test_metrica_de_fluidez_o_roteiro_fica_mais_curto(contexto, pagina):
    """Roteiro fixo: colocar os 5 CT, jogar 2 smokes de jogadores diferentes e
    mover 2 jogadores no passo 2. Conta ações (cliques, teclas e arrastos) no
    caminho ANTIGO (botões do painel, que continuam existindo) e no NOVO."""
    pontos = [(0.30, 0.30), (0.40, 0.30), (0.50, 0.30), (0.60, 0.30), (0.70, 0.30)]

    def antigo(pg):
        n = 0
        for i, (fx, fy) in enumerate(pontos, start=1):
            arrasta_do_banco(pg, "ct", str(i), fx, fy); n += 1
        aba_do_painel(pg, "granadas")
        clica(pg, '[data-arma="smoke"]'); n += 1
        clica(pg, 'aside [data-ferramenta="granada"]'); n += 1
        for (fx, fy), dest in ((pontos[0], (0.3, 0.6)), (pontos[1], (0.4, 0.6))):
            pg.mouse.click(*no_mapa(pg, fx, fy)); pg.mouse.click(*no_mapa(pg, *dest)); n += 2
        clica(pg, "#pr-novo-passo"); n += 1
        clica(pg, 'aside [data-ferramenta="mover"]'); n += 1
        for fx, fy in pontos[:2]:
            pg.mouse.move(*no_mapa(pg, fx, fy)); pg.mouse.down()
            pg.mouse.move(*no_mapa(pg, fx, fy + 0.15), steps=5); pg.mouse.up(); n += 1
        return n

    def novo(pg):
        n = 0
        for i, (fx, fy) in enumerate(pontos, start=1):
            arrasta_do_banco(pg, "ct", str(i), fx, fy); n += 1
        solta_foco(pg)
        for (fx, fy), dest in ((pontos[0], (0.3, 0.6)), (pontos[1], (0.4, 0.6))):
            pg.mouse.click(*no_mapa(pg, fx, fy)); n += 1          # seleciona o jogador
            pg.keyboard.press("1"); n += 1
            pg.mouse.click(*no_mapa(pg, *dest)); n += 1
        pg.keyboard.press("n"); n += 1                              # novo passo (a seleção segue)
        for fx, fy in pontos[:2]:
            pg.mouse.move(*no_mapa(pg, fx, fy)); pg.mouse.down()
            pg.mouse.move(*no_mapa(pg, fx, fy + 0.15), steps=5); pg.mouse.up(); n += 1
        return n

    resultados = {}
    for nome, roteiro in (("antes", antigo), ("depois", novo)):
        pg = abre(contexto, pagina)
        n = roteiro(pg)
        assert len(ops(pg, "cria_peca")) == 5
        assert len(ops(pg, "cria_granada")) == 2
        assert len([o for o in ops(pg, "move_peca")]) == 2
        resultados[nome] = n
        pg.close()
    print(f"\nmétrica de fluidez (ações): antes {resultados['antes']}, depois {resultados['depois']}")
    assert resultados["depois"] < resultados["antes"], resultados


def test_clique_sem_movimento_nunca_move_a_peca_e_esc_nao_cria_operacao(contexto, pagina):
    """Fase 8a: um clique na peça (abaixo do limiar) entra em traçando caminho;
    Esc sai sem nada no log."""
    pg = abre(contexto, pagina)
    pid = coloca(pg, "ct", "1", 0.45, 0.45)
    antes = interno(pg, "S.doc.operacoes.length")
    pos = pos_da_peca(pg, pid)
    limiar = interno(pg, "I.LIMIAR_ARRASTO_PX")
    x, y = no_mapa(pg, 0.45, 0.45)
    pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(x + limiar * 0.75, y, steps=3); pg.mouse.up()
    assert interno(pg, "I.estadoDaInteracao()") == "tracando_caminho"
    assert pos_da_peca(pg, pid) == pos
    pg.keyboard.press("Escape")
    assert interno(pg, "I.estadoDaInteracao()") != "tracando_caminho"
    assert interno(pg, "S.doc.operacoes.length") == antes and pos_da_peca(pg, pid) == pos
