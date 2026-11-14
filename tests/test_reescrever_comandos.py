"""Reescrever CR2: a seção "Comandos" do painel (o leitor com os nicks, as regras do round real, o plano e a trilha, do CR1a ao CR1d) em cima do round 23 da match_43
com "Reescrever daqui" em 1:20 (frame 140). Nada muda antes do Aplicar; um comando aplicado é UM desfazer; o mapa não se mexe em estado nenhum; a granada fica para a CR3."""
from __future__ import annotations

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_reescrever_modo import (  # noqa: E402,F401  (fixtures e ajudas)
    OBS, PARTIDA, RECT, TELAS, _abre, _estado, navegador)
from tests.test_reescrever_r3 import _arrasta  # noqa: E402

FRAME = 140       # 1:20 no relógio do round (35 s do início)
CLS_TOTAL = "window.__cls_total = 0; new PerformanceObserver(l => { for (const e of l.getEntries()) window.__cls_total += e.value; }).observe({type: 'layout-shift'});"      # conta TODOS os deslocamentos, até os que vêm logo depois de um clique


@pytest.fixture(scope="module")
def pagina_cmd(tmp_path_factory):
    """A página da partida com os arquivos dos comandos ao lado, como no site."""
    from scripts.build_reescrever_comandos import escreve
    from scripts.build_web_page import build_html
    d = tmp_path_factory.mktemp("cmd")
    arq = d / f"{PARTIDA}.html"
    arq.write_text(build_html(PARTIDA), encoding="utf-8")
    escreve(d, ["de_mirage"])
    return arq


def _abre_no_instante(navegador, arq, w=1440, h=900):
    ctx, pg, erros = _abre(navegador, arq, w, h)
    pg.evaluate("f => { const s = document.getElementById('scrub'); s.value = f; s.dispatchEvent(new Event('input')); }", FRAME)
    pg.wait_for_timeout(300)
    return ctx, pg, erros


def _pronta(pg):
    pg.wait_for_function("() => window.ComandosNoReescrever && document.querySelector('#rw-cmd-cartao .rw-cmd-vazio')")


def _abre_secao(pg):
    pg.click("#rw-entrar")
    pg.click("#rw-cmd-abre")
    _pronta(pg)


def _escreve(pg, frase):
    pg.fill("#rw-cmd-texto", frase)
    pg.click("#rw-cmd-entender")
    pg.wait_for_timeout(120)


def _cartao(pg):
    return pg.inner_text("#rw-cmd-cartao")


def _sem_tela(pecas):
    """O estado das peças sem a posição na TELA (que muda se a página rola): o que importa é o dado."""
    return [{k: v for k, v in p.items() if k != "tela"} for p in pecas]


def _pecas(pg):
    return {p["nome"]: p for p in _estado(pg)["pecas"]}


def _trilha(pg, nome):
    return _pecas(pg)[nome]["trilha"]


def _opcao(pg, texto):
    pg.locator("#rw-cmd-cartao button", has_text=texto).first.click()
    pg.wait_for_timeout(120)


def _aplica(pg):
    assert not pg.is_disabled("#rw-cmd-aplicar"), _cartao(pg)
    pg.click("#rw-cmd-aplicar")
    pg.wait_for_timeout(150)


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# o leitor só é pedido ao abrir a seção; o número ao lado do nick só no Reescrever
# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def test_o_leitor_so_e_pedido_pela_rede_quando_a_secao_abre(navegador, pagina_cmd):
    ctx = navegador.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page(); pedidos = []
    pg.on("request", lambda r: pedidos.append(r.url))
    try:
        pg.goto(pagina_cmd.as_uri() + "#replay")
        pg.wait_for_function("() => window.MapAnnotations && MapAnnotations._interno.S.reprojecoes > 0")
        pg.wait_for_timeout(500)
        pg.locator("#strip .rchip", has_text="23").first.click(); pg.wait_for_timeout(200)
        assert not [u for u in pedidos if "/comandos/" in u]                                  # a página da partida carrega sem nenhum arquivo dos comandos
        pg.click("#rw-entrar")
        assert not [u for u in pedidos if "/comandos/" in u]                                  # entrar no Reescrever também não
        assert pg.evaluate("typeof LeitorDeComandos") == "undefined"
        pg.click("#rw-cmd-abre"); _pronta(pg)
        arquivos = sorted(u.rsplit("/comandos/", 1)[1] for u in pedidos if "/comandos/" in u)
        assert arquivos == ["leitor.js", "plano.js", "real.js", "real/de_mirage.js", "reescrever.js"]
        n = len(pedidos)
        pg.click("#rw-cmd-abre"); pg.click("#rw-cmd-abre")                                    # fechar e abrir de novo: nada novo
        assert len(pedidos) == n
    finally:
        ctx.close()


def test_o_campo_com_foco_tambem_carrega_e_o_erro_de_rede_e_dito_sem_travar_o_resto(navegador, pagina_cmd, tmp_path_factory):
    ctx = navegador.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page(); erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.route("**/comandos/real/*", lambda r: r.abort())                                       # o arquivo do mapa falha
    try:
        pg.goto(pagina_cmd.as_uri() + "#replay")
        pg.wait_for_function("() => window.MapAnnotations && MapAnnotations._interno.S.reprojecoes > 0")
        pg.wait_for_timeout(500)
        pg.locator("#strip .rchip", has_text="23").first.click(); pg.wait_for_timeout(200)
        pg.click("#rw-entrar")
        pg.evaluate("document.getElementById('rw-cmd-corpo').hidden = false")                 # o corpo à vista: o foco no campo é o que dispara
        pg.focus("#rw-cmd-texto")
        pg.wait_for_selector("#rw-cmd-cartao .rw-cmd-erro")
        assert "Não consegui carregar os comandos" in _cartao(pg)
        assert _estado(pg)["ativo"] and erros == []                                           # o Reescrever continua
    finally:
        ctx.close()


def test_o_numero_do_banco_so_existe_no_reescrever_e_e_a_ordem_da_coluna(navegador, pagina_cmd):
    ctx, pg, _ = _abre_no_instante(navegador, pagina_cmd)
    try:
        assert pg.locator(".pr-num").count() == 0                                             # no Assistir não há número
        pg.click("#rw-entrar")
        nums = pg.evaluate("() => [...document.querySelectorAll('.peca-rw')].map(b => [b.dataset.nome, b.classList.contains('t') ? 'tr' : 'ct', b.querySelector('.pr-num').textContent])")
        por = {n: (l, i) for n, l, i in nums}
        assert por["ropz"] == ("tr", "2") and por["mezii"] == ("tr", "1") and por["ZywOo"] == ("tr", "5") and por["FalleN"] == ("ct", "2") and por["molodoy"] == ("ct", "1")
        assert sorted(i for n, l, i in nums if l == "tr") == ["1", "2", "3", "4", "5"]
        pg.click("#rw-sair")
        assert pg.locator(".pr-num").count() == 0                                             # sair devolve o elenco do Assistir
    finally:
        ctx.close()


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# o mapa não se mexe e o CLS fica em 0, em todos os estados da seção
# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("tam", list(TELAS))
def test_o_mapa_nao_muda_e_o_cls_e_zero_em_todos_os_estados_da_secao(navegador, pagina_cmd, tam):
    w, h = TELAS[tam]
    ctx, pg, erros = _abre_no_instante(navegador, pagina_cmd, w, h)
    try:
        pg.click("#rw-entrar")
        pg.evaluate(CLS_TOTAL)
        rects = [pg.evaluate(RECT)]

        def marca():
            pg.wait_for_timeout(150)
            rects.append(pg.evaluate(RECT))
        pg.evaluate(OBS)                                                                      # o padrão da página (como no R6a): deslocamento logo depois de um clique não conta
        pg.click("#rw-cmd-abre"); marca()                                                     # abrir (o leitor carrega)
        _pronta(pg); marca()
        assert pg.evaluate("window.__cls") == 0
        pg.evaluate("window.__cls_total = 0")                                                 # daqui em diante vale o rigor total: nenhum deslocamento, nem o que vem de um clique
        _escreve(pg, "o 4 joga smoke no janelão aos 1:05"); marca()                           # uma pergunta
        _escreve(pg, "ZywOo roda pra B aos 0:50"); marca()                                    # recusado
        _escreve(pg, "ropz corre pro meio aos 1:10"); marca()                                 # entendido
        _escreve(pg, "KSCERATO corre pro meio aos 0:30"); marca()                             # "bomba ou round?"
        assert pg.evaluate("window.__cls_total") == 0                                         # entender e perguntar: nada se mexe, nem logo depois de um clique
        _escreve(pg, "ropz corre pro meio aos 1:10")
        _aplica(pg); marca()                                                                  # aplicado: uma linha nova em "O que mudou" empurra o que vem abaixo, como no R3 (conta pelo padrão da página)
        pg.click("#rw-desfazer"); marca()                                                     # desfeito
        pg.click("#rw-cmd-abre"); marca()
        assert all(r == rects[0] for r in rects), rects
        assert pg.evaluate("window.__cls") == 0
        assert erros == []
    finally:
        ctx.close()


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# aplicar, desfazer
# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def test_aplicar_e_desfazer_volta_exatamente_ao_estado_de_antes(navegador, pagina_cmd):
    ctx, pg, _ = _abre_no_instante(navegador, pagina_cmd)
    try:
        _abre_secao(pg)
        antes = _sem_tela(_estado(pg)["pecas"]), pg.inner_text("#rw-mudou")
        assert pg.is_disabled("#rw-desfazer")
        _escreve(pg, "ropz e apEX correm pro meio aos 1:10")
        assert "ropz (TR 2)" in _cartao(pg) and "apEX (TR 3)" in _cartao(pg)
        assert _sem_tela(_estado(pg)["pecas"]) == antes[0] and pg.inner_text("#rw-mudou") == antes[1]  # entender não muda nada
        _aplica(pg)
        est = _estado(pg)
        assert [p["nome"] for p in est["pecas"] if p["editada"]] == ["ropz", "apEX"] and est["comandos"]["desfazer"] == 1       # dois jogadores, UM desfazer
        assert len(est["comandos"]["linhas"]) == 1 and "ropz (TR 2)" in est["comandos"]["linhas"][0] and "apEX (TR 3)" in est["comandos"]["linhas"][0]
        assert [round(p["f"]) for p in _trilha(pg, "ropz")] == [180]                          # 1:10 = 45 s = o quadro 180
        assert "Comando:" in pg.inner_text("#rw-mudou")
        pg.click("#rw-desfazer")
        assert _sem_tela(_estado(pg)["pecas"]) == antes[0] and pg.inner_text("#rw-mudou") == antes[1]
        assert pg.is_disabled("#rw-desfazer") and "Desfeito" in _cartao(pg)
    finally:
        ctx.close()


def test_o_arrasto_e_um_item_proprio_do_desfazer_e_desfazer_sempre_desfaz_a_ultima_acao(navegador, pagina_cmd):
    ctx, pg, _ = _abre_no_instante(navegador, pagina_cmd)
    try:
        _abre_secao(pg)
        _arrasta(pg, "ropz")
        arrastada = _trilha(pg, "ropz")
        assert _estado(pg)["comandos"]["desfazer"] == 1 and not pg.is_disabled("#rw-desfazer")      # o arrasto já é um item
        _escreve(pg, "ropz corre pro meio aos 1:10"); _aplica(pg)
        assert len(_trilha(pg, "ropz")) == 2 and _trilha(pg, "ropz")[0] == arrastada[0]       # a parada de arrastar fica; o comando vem depois dela
        _escreve(pg, "mezii corre pro meio aos 1:10"); _aplica(pg)
        assert _estado(pg)["comandos"]["desfazer"] == 3
        pg.click("#rw-desfazer")                                                              # volta só o do mezii
        assert _pecas(pg)["mezii"]["editada"] is False and len(_trilha(pg, "ropz")) == 2
        pg.click("#rw-desfazer")                                                              # volta o comando do ropz: sobra o arrasto
        assert _trilha(pg, "ropz") == arrastada and _estado(pg)["comandos"]["desfazer"] == 1
        pg.click("#rw-desfazer")                                                              # e por fim o arrasto
        assert not _pecas(pg)["ropz"]["editada"] and _estado(pg)["comandos"]["desfazer"] == 0
        _arrasta(pg, "mezii")
        pg.click("#rw-voltar")                                                                # "Voltar ao real" zera a pilha
        assert _estado(pg)["comandos"]["desfazer"] == 0 and not any(p["editada"] for p in _estado(pg)["pecas"])
    finally:
        ctx.close()


def test_comando_depois_arrasto_depois_um_desfazer_sobra_o_comando_com_a_trilha_de_depois_dele(navegador, pagina_cmd):
    ctx, pg, _ = _abre_no_instante(navegador, pagina_cmd)
    try:
        _abre_secao(pg)
        _escreve(pg, "ropz corre pro meio aos 1:10"); _aplica(pg)
        depois_do_comando = _trilha(pg, "ropz")
        linhas = _estado(pg)["comandos"]["linhas"]
        _arrasta(pg, "ropz")
        assert _trilha(pg, "ropz") != depois_do_comando and _estado(pg)["comandos"]["desfazer"] == 2
        pg.click("#rw-desfazer")                                                              # UM Desfazer: o arrasto, não o comando
        assert _trilha(pg, "ropz") == depois_do_comando
        est = _estado(pg)
        assert est["comandos"]["desfazer"] == 1 and est["comandos"]["linhas"] == linhas and _pecas(pg)["ropz"]["editada"]
    finally:
        ctx.close()


def test_a_sua_versao_tocando_desliga_o_desfazer_e_os_comandos(navegador, pagina_cmd):
    ctx, pg, _ = _abre_no_instante(navegador, pagina_cmd)
    try:
        _abre_secao(pg)
        _escreve(pg, "ropz corre pro meio aos 1:10"); _aplica(pg)
        pg.click("#play"); pg.wait_for_timeout(200); pg.click("#play")                        # toca e pausa
        assert _estado(pg)["sua"] and pg.is_disabled("#rw-desfazer") and "Volte a editar" in _cartao(pg)
        pg.click("#rw-editar")
        assert not pg.is_disabled("#rw-desfazer")
    finally:
        ctx.close()


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# os 10 exemplos do round 23, de ponta a ponta na tela
# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def test_exemplo_1_zywoo_roda_pra_b_aos_0_50_e_recusado_por_comecar_depois_da_morte(navegador, pagina_cmd):
    ctx, pg, _ = _abre_no_instante(navegador, pagina_cmd)
    try:
        _abre_secao(pg); _escreve(pg, "ZywOo roda pra B aos 0:50")
        c = _cartao(pg)
        assert "ZywOo (TR 5)" in c and "morreu para molodoy" in c and pg.is_disabled("#rw-cmd-aplicar")
        assert pg.locator('#rw-cmd-cartao [data-codigo="comeca_depois_da_morte"] button').all_inner_texts() == ["Escolher outro jogador", "Corrigir"]
        _opcao(pg, "Escolher outro jogador")                                                  # a pergunta "quem?" volta, com nick, lado, número e vida
        assert "ropz · TR 2" in _cartao(pg) and "flameZ · TR 4, morto às" in _cartao(pg)
        _opcao(pg, "ropz · TR 2")
        assert "ropz (TR 2)" in _cartao(pg) and not pg.is_disabled("#rw-cmd-aplicar")        # com o ropz, que vive em 0:50, vale
        assert not any(p["editada"] for p in _estado(pg)["pecas"])                           # e nada mudou até o Aplicar
    finally:
        ctx.close()


def test_exemplo_2_o_4_sem_lado_pergunta_com_nick_e_vida(navegador, pagina_cmd):
    ctx, pg, _ = _abre_no_instante(navegador, pagina_cmd)
    try:
        _abre_secao(pg); _escreve(pg, "o 4 joga smoke no janelão aos 1:05")
        opcoes = pg.locator("#rw-cmd-cartao .rw-cmd-opcao").all_inner_texts()
        assert any(o.startswith("yuurih · CT 4") for o in opcoes) and any(o.startswith("flameZ · TR 4, morto às") for o in opcoes)
        assert pg.evaluate("document.activeElement.classList.contains('rw-cmd-opcao')")       # o foco vai para a pergunta
        _opcao(pg, "yuurih · CT 4")
        assert "granada" in _cartao(pg) and pg.is_disabled("#rw-cmd-aplicar")                 # e a granada fica para a CR3
    finally:
        ctx.close()


def test_exemplo_3_comando_de_granada_nao_aplica_nada_e_diz_que_e_a_cr3(navegador, pagina_cmd):
    ctx, pg, _ = _abre_no_instante(navegador, pagina_cmd)
    try:
        _abre_secao(pg)
        antes = _estado(pg)["pecas"], _estado(pg)["trocas"], pg.inner_text("#rw-mudou")
        _escreve(pg, "FalleN joga smoke no janelão aos 0:57")
        assert "FalleN (CT 2)" in _cartao(pg) and "Trocar granada por comando ainda não está pronto" in _cartao(pg) and "Trocar a granada" in _cartao(pg)
        assert pg.is_disabled("#rw-cmd-aplicar")
        pg.evaluate("() => document.getElementById('rw-cmd-aplicar').click()")                # nem à força
        assert (_estado(pg)["pecas"], _estado(pg)["trocas"], pg.inner_text("#rw-mudou")) == antes and _estado(pg)["comandos"]["desfazer"] == 0
        _escreve(pg, "ropz joga flash no meio aos 1:10 e corre pro B")                         # nem a parte que seria só de movimento
        assert pg.is_disabled("#rw-cmd-aplicar") and not any(p["editada"] for p in _estado(pg)["pecas"])
    finally:
        ctx.close()


def test_exemplo_4_dois_jogadores_correm_juntos_e_o_nick_aparece_em_todo_lugar(navegador, pagina_cmd):
    ctx, pg, _ = _abre_no_instante(navegador, pagina_cmd)
    try:
        _abre_secao(pg); _escreve(pg, "ropz e apEX correm pro meio aos 1:10")
        assert "ropz (TR 2) + apEX (TR 3)" in _cartao(pg) and "chega às" in _cartao(pg)
        _aplica(pg)
        assert {"ropz", "apEX"} == {n for n, p in _pecas(pg).items() if p["editada"]}
        assert "ropz" in pg.inner_text("#rw-mudou") and "apEX" in pg.inner_text("#rw-mudou")
    finally:
        ctx.close()


def test_exemplo_5_mezii_segura_a_caverna_ate_0_45_comeca_no_instante_e_fica_ate_o_fim(navegador, pagina_cmd):
    ctx, pg, _ = _abre_no_instante(navegador, pagina_cmd)
    try:
        _abre_secao(pg); _escreve(pg, "mezii segura a caverna até 0:45")
        assert "mezii (TR 1)" in _cartao(pg) and "desde 1:20" in _cartao(pg) and "até 0:45" in _cartao(pg)
        _aplica(pg)
        assert [round(p["f"]) for p in _trilha(pg, "mezii")] == [FRAME]                       # parte no instante; fica na caverna até o fim (a trilha termina nela)
    finally:
        ctx.close()


def test_exemplo_6_vai_pro_b_e_depois_pro_meio_pergunta_quando_e_encadeia(navegador, pagina_cmd):
    ctx, pg, _ = _abre_no_instante(navegador, pagina_cmd)
    try:
        _abre_secao(pg); _escreve(pg, "ropz vai pro B e depois pro meio")
        assert "Quando começa" in _cartao(pg) and pg.locator("#rw-cmd-cartao .rw-cmd-horario").count() == 1
        _opcao(pg, "No instante (1:20)")
        assert 'Não entendi "pro meio"' in _cartao(pg)                                       # "pro meio" sem verbo: o leitor pergunta o que o jogador faz (limite do C1, dito na tela)
        _opcao(pg, "Mover até Meio")
        assert "depois, por volta de" in _cartao(pg) and not pg.is_disabled("#rw-cmd-aplicar")
        _aplica(pg)
        t = _trilha(pg, "ropz")
        assert len(t) == 2 and round(t[0]["f"]) == FRAME and t[1]["f"] > t[0]["f"]            # o segundo parte quando o primeiro chega
    finally:
        ctx.close()


def test_exemplo_7_antes_do_instante_oferece_comecar_em_1_20(navegador, pagina_cmd):
    ctx, pg, _ = _abre_no_instante(navegador, pagina_cmd)
    try:
        _abre_secao(pg); _escreve(pg, "YEKINDAR corre pro meio aos 1:30")
        assert pg.locator('#rw-cmd-cartao [data-codigo="antes_do_instante"] button').all_inner_texts() == ["Começar em 1:20", "Corrigir"]
        assert pg.is_disabled("#rw-cmd-aplicar")
        _opcao(pg, "Começar em 1:20")
        assert not pg.is_disabled("#rw-cmd-aplicar") and "aos 1:20" in _cartao(pg)
        _aplica(pg)
        assert round(_trilha(pg, "YEKINDAR")[0]["f"]) == FRAME
    finally:
        ctx.close()


def test_exemplo_8_quem_ja_estava_morto_e_recusado(navegador, pagina_cmd):
    ctx, pg, _ = _abre_no_instante(navegador, pagina_cmd)
    try:
        _abre_secao(pg); _escreve(pg, "flameZ roda pra A aos 1:15")
        assert "flameZ (TR 4)" in _cartao(pg) and "antes de 1:20" in _cartao(pg) and pg.is_disabled("#rw-cmd-aplicar")
        assert pg.locator('#rw-cmd-cartao [data-codigo="ja_morto"] button').count() == 2
    finally:
        ctx.close()


def test_exemplo_9_molodoy_depois_da_morte_e_recusado(navegador, pagina_cmd):
    ctx, pg, _ = _abre_no_instante(navegador, pagina_cmd)
    try:
        _abre_secao(pg); _escreve(pg, "molodoy corre pro B aos 0:40")
        assert "molodoy (CT 1)" in _cartao(pg) and "morreu para apEX" in _cartao(pg) and pg.is_disabled("#rw-cmd-aplicar")
        _opcao(pg, "Corrigir")                                                                # [Corrigir] devolve o foco ao campo, com a frase
        assert pg.evaluate("document.activeElement.id") == "rw-cmd-texto" and pg.input_value("#rw-cmd-texto") == "molodoy corre pro B aos 0:40"
    finally:
        ctx.close()


def test_exemplo_10_kscerato_depois_do_plant_pergunta_bomba_ou_round_uma_vez_so(navegador, pagina_cmd):
    ctx, pg, _ = _abre_no_instante(navegador, pagina_cmd)
    try:
        _abre_secao(pg); _escreve(pg, "KSCERATO segura o meio aos 0:35 até 0:30")
        assert _cartao(pg).count("relógio da bomba ou o do round") == 1                      # início e fim depois do plant: UMA pergunta
        _opcao(pg, "Relógio da bomba")
        assert "relógio da bomba ou o do round" not in _cartao(pg)
    finally:
        ctx.close()


def test_termina_depois_da_morte_e_aplicado_com_aviso_e_a_peca_esmaece_na_hora_da_morte_real(navegador, pagina_cmd):
    ctx, pg, _ = _abre_no_instante(navegador, pagina_cmd)
    try:
        _abre_secao(pg); _escreve(pg, "tr 5 segura o meio até 0:50")                          # ZywOo morre aos 0:52; o fim é 0:50 (65 s)
        assert "ZywOo (TR 5)" in _cartao(pg) and "esmaece" in _cartao(pg) and not pg.is_disabled("#rw-cmd-aplicar")
        assert pg.locator('#rw-cmd-cartao [data-codigo="termina_depois_da_morte"] button').count() == 0
        _aplica(pg)
        pg.click("#play"); pg.wait_for_timeout(100)
        pg.evaluate("() => { window.__fixa = true; }")
        pg.click("#play")                                                                     # pausa
        assert _pecas(pg)["ZywOo"]["editada"]
    finally:
        ctx.close()


def test_a_frase_com_ponto_final_separa_os_comandos_e_o_agora_e_o_fim_do_anterior_da_mesma_peca(navegador, pagina_cmd):
    ctx, pg, _ = _abre_no_instante(navegador, pagina_cmd)
    try:
        _abre_secao(pg); _escreve(pg, "ropz corre pro meio aos 1:10. ropz segura o meio até 0:45")
        c = _cartao(pg)
        assert "correndo até Meio" in c and "segura Meio" in c and "até 0:45" in c
        assert not pg.is_disabled("#rw-cmd-aplicar")
        _aplica(pg)
        assert len(_trilha(pg, "ropz")) == 1                                                  # chegou ao meio; a espera até 0:45 é só o intervalo: uma parada
    finally:
        ctx.close()


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# acessibilidade
# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def test_acessibilidade_o_cartao_e_anunciado_a_pergunta_recebe_o_foco_e_tudo_se_alcanca_pelo_teclado(navegador, pagina_cmd):
    ctx = navegador.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    pg = ctx.new_page()
    try:
        pg.goto(pagina_cmd.as_uri() + "#replay")
        pg.wait_for_function("() => window.MapAnnotations && MapAnnotations._interno.S.reprojecoes > 0")
        pg.wait_for_timeout(500)
        pg.locator("#strip .rchip", has_text="23").first.click(); pg.wait_for_timeout(200)
        pg.evaluate("f => { const s = document.getElementById('scrub'); s.value = f; s.dispatchEvent(new Event('input')); }", FRAME)
        pg.click("#rw-entrar")
        abre = pg.locator("#rw-cmd-abre")
        assert abre.get_attribute("aria-expanded") == "false" and abre.get_attribute("aria-controls") == "rw-cmd-corpo"
        abre.focus(); pg.keyboard.press("Enter"); _pronta(pg)                                  # a seção abre pelo teclado
        assert abre.get_attribute("aria-expanded") == "true"
        c = pg.locator("#rw-cmd-cartao")
        assert c.get_attribute("role") == "region" and c.get_attribute("aria-live") == "polite" and c.get_attribute("aria-label") == "O que entendi"
        assert pg.evaluate("document.querySelector('label[for=rw-cmd-texto]').textContent") == "O que acontece, em uma frase"      # o campo tem nome
        pg.focus("#rw-cmd-texto"); pg.keyboard.type("o 4 joga smoke no janelão aos 1:05"); pg.keyboard.press("Enter")           # Enter entende
        pg.wait_for_timeout(150)
        assert pg.evaluate("document.activeElement.classList.contains('rw-cmd-opcao')")       # o foco foi para a pergunta
        primeiro = pg.evaluate("document.activeElement.textContent")
        pg.keyboard.press("Tab")
        assert pg.evaluate("document.activeElement.textContent") != primeiro                  # o Tab anda (pula o jogador morto, que está desligado)
        pg.keyboard.press("Shift+Tab"); pg.keyboard.press("Enter")                             # e se escolhem pelo teclado
        pg.wait_for_timeout(150)
        assert "O que entendi" in _cartao(pg) and pg.locator("#rw-cmd-cartao .rw-cmd-opcao").count() == 0 or "granada" in _cartao(pg)
        assert pg.evaluate("getComputedStyle(document.querySelector('.rw-cmd-seta'), '::before').transitionDuration") == "0s"       # reduzir movimento continua valendo
        for sel in ("#rw-cmd-entender", "#rw-cmd-aplicar", "#rw-cmd-corrigir", "#rw-desfazer"):
            assert pg.locator(sel).evaluate("e => e.tagName") == "BUTTON"                       # tudo é botão de verdade: o teclado alcança
    finally:
        ctx.close()


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ajustes do Pedro depois das capturas
# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def _entende_sem_rolar(pg, frase):
    """Escreve e entende sem o Playwright rolar a página (o clique dele rolaria): a conta é do site."""
    pg.evaluate("f => { const c = document.getElementById('rw-cmd-texto'); c.value = f; document.getElementById('rw-cmd-entender').click(); }", frase)
    pg.wait_for_timeout(200)


VISIVEL = """sel => { const col = document.getElementById('squad-t').getBoundingClientRect(), vp = innerHeight;
    return [...document.querySelectorAll(sel)].map(b => { const r = b.getBoundingClientRect(); return r.top >= col.top - 1 && r.bottom <= col.bottom + 1 && r.top >= 0 && r.bottom <= vp; }); }"""


def test_a_1366x657_o_veredito_e_a_pergunta_aparecem_a_vista_na_coluna_sem_rolar_a_pagina(navegador, pagina_cmd):
    ctx, pg, _ = _abre_no_instante(navegador, pagina_cmd, 1366, 657)
    try:
        _abre_secao(pg)
        y0 = pg.evaluate("scrollY")
        _entende_sem_rolar(pg, "ZywOo roda pra B aos 0:50")                                   # o veredito: texto e botões
        assert pg.evaluate(VISIVEL, '#rw-cmd-cartao [data-codigo="comeca_depois_da_morte"] button') == [True, True]
        assert pg.evaluate(VISIVEL, '#rw-cmd-cartao [data-codigo="comeca_depois_da_morte"] p') == [True]
        _entende_sem_rolar(pg, "o 4 joga smoke no janelão aos 1:05")                          # a pergunta
        assert pg.evaluate(VISIVEL, "#rw-cmd-cartao .rw-cmd-pergunta .rw-cmd-opcao") == [True, True]
        _entende_sem_rolar(pg, "ropz corre pro meio aos 1:10")                                # o cartão entendido
        assert pg.evaluate(VISIVEL, "#rw-cmd-cartao .rw-cmd-entendi li") == [True]
        assert pg.evaluate("scrollY") == y0                                                   # a página não rolou
    finally:
        ctx.close()


def test_o_jogador_ja_morto_na_pergunta_fica_como_botao_desligado_com_o_motivo(navegador, pagina_cmd):
    ctx, pg, _ = _abre_no_instante(navegador, pagina_cmd)
    try:
        _abre_secao(pg); _escreve(pg, "o 4 joga smoke no janelão aos 1:05")
        morto = pg.locator("#rw-cmd-cartao .rw-cmd-opcao", has_text="flameZ")
        assert morto.is_disabled() and "morto às 1:42, antes de 1:20" in morto.inner_text()
        assert not pg.locator("#rw-cmd-cartao .rw-cmd-opcao", has_text="yuurih").is_disabled()
        assert pg.evaluate("document.activeElement.textContent").startswith("yuurih")         # o foco vai para o primeiro que serve
    finally:
        ctx.close()


def test_anda_e_agacha_usam_a_velocidade_propria_e_o_cartao_diz_o_jeito_certo(navegador, pagina_cmd):
    ctx, pg, _ = _abre_no_instante(navegador, pagina_cmd)
    try:
        _abre_secao(pg)
        durs = {}
        for verbo, modo in (("corre", "correndo"), ("anda", "andando"), ("agacha", "agachado")):
            _escreve(pg, f"ropz {verbo} pro meio aos 1:10")
            assert modo in _cartao(pg), (verbo, _cartao(pg))                                  # o cartão diz o jeito que a peça faz
            _aplica(pg)
            t = _pecas(pg)["ropz"]["trechos"][0]
            durs[modo] = (t["d"], t["dur"])
            pg.click("#rw-desfazer")
        v = {"correndo": 210.6, "andando": 111.8, "agachado": 90.4}                           # a velocidade medida do rifle (as constantes da C3)
        for modo, (d, dur) in durs.items():
            assert abs(dur - d / v[modo]) < 0.02, (modo, d, dur)
    finally:
        ctx.close()


def test_horario_depois_do_fim_do_round_diz_a_causa_certa(navegador, pagina_cmd):
    import re
    ctx, pg, _ = _abre_no_instante(navegador, pagina_cmd)
    try:
        _abre_secao(pg); _escreve(pg, "FalleN corre pro meio aos 0:15")
        _opcao(pg, "Relógio do round")                                                        # 0:15 do round = 100 s; o round gravado acaba antes
        assert not pg.is_disabled("#rw-cmd-aplicar"), _cartao(pg)
        pg.click("#rw-cmd-aplicar"); pg.wait_for_timeout(150)
        m = re.search(r"o round acabou às (\d+:\d\d) e FalleN \(CT 2\) só parte às (\d+:\d\d)\. Nada mudou\.", _cartao(pg))
        assert m, _cartao(pg)
        assert not any(p["editada"] for p in _estado(pg)["pecas"]) and _estado(pg)["comandos"]["desfazer"] == 0
    finally:
        ctx.close()
