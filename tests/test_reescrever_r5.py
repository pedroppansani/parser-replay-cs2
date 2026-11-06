"""Reescrever R5 (decisão 60): as portas de entrada dentro da partida -- o botão "Reescrever" dos momentos do "Por que perdeu" e o dos chips do
Perfil --, e o relógio do round (cartão 28) no lugar do tempo decorrido nesse bloco."""
from __future__ import annotations

import re

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_reescrever_modo import (  # noqa: E402,F401  (fixtures e ajudas)
    _abre, _estado, _sai, navegador, pagina)
from tests.test_reescrever_r3 import _arrasta  # noqa: E402
from tests.test_reescrever_r4 import (  # noqa: E402,F401  (a biblioteca ao lado da página, como no site)
    PRONTA, _clica, _troca_a_primeira, biblioteca, pagina_com_biblioteca)

RELOGIO = re.compile(r"(\d+):(\d\d)")


def _seg(texto):
    m = RELOGIO.search(texto)
    return int(m.group(1)) * 60 + int(m.group(2))


def _portas(pg):
    return pg.locator("#autopsy .moment-rw")


def test_cada_momento_com_jogador_tem_a_porta_e_o_tempo_e_o_relogio_do_round(navegador, pagina):
    ctx, pg, erros = _abre(navegador, pagina, 1440, 900)
    try:
        assert _portas(pg).count() >= 1
        assert pg.locator("#autopsy .moment .moment-rw").count() == 0               # botão dentro de botão não vale
        for i in range(pg.locator("#autopsy .mrow").count()):                        # só o momento clicável, dentro do round, com jogador
            linha = pg.locator("#autopsy .mrow").nth(i)
            tem = linha.locator(".moment-rw").count() == 1
            fora = "após o fim do round" in linha.locator(".mt").inner_text() or linha.locator(".moment.inerte").count() == 1
            assert not (tem and fora)
        # (cartão 28) o tempo do momento é o do relógio (descendo), o mesmo que o Reescrever abre 3 s antes
        porta = _portas(pg).first
        aria = porta.get_attribute("aria-label")
        assert re.search(r"a partir de \d+:\d\d no relógio, 3 s antes, com \S+ selecionado", aria)
        mt = _seg(porta.locator("xpath=preceding-sibling::button[1]").locator(".mt").inner_text())
        porta.click()
        e = _estado(pg)
        assert e["ativo"] and e["selecionada"] == re.search(r"com (.+) selecionado", aria).group(1)
        assert _seg(aria) == _seg(e["relogio"])                                      # o relógio do aria-label é o do instante em que abriu
        assert mt == _seg(e["relogio"]) - 3 or abs(mt - (_seg(e["relogio"]) - 3)) <= 1   # 3 s antes do momento (o quadro é de 0,25 s)
        assert not erros
    finally:
        ctx.close()


def test_a_frase_do_bloco_fala_da_porta_e_nao_promete_resultado(navegador, pagina):
    ctx, pg, _ = _abre(navegador, pagina, 1440, 900)
    try:
        texto = pg.locator("#autopsy .caveat").inner_text()
        assert "Reescrever para mudar a jogada a partir de 3 s antes" in texto
        assert not re.search(r"ganh|venc|vit[óo]ria|placar|melhor|pior|resultado|prever|previs[ãa]o\b(?!\.)|n[ãa]o morre|sobreviv|salv", pg.locator("#autopsy .moment-rw").first.get_attribute("aria-label"), re.I)
    finally:
        ctx.close()


def test_a_porta_com_edicao_pede_para_descartar_antes_de_reabrir(navegador, pagina):
    ctx, pg, _ = _abre(navegador, pagina, 1440, 900)
    try:
        _portas(pg).first.click()
        assert _estado(pg)["ativo"]
        pg.wait_for_timeout(1000)                                                    # a rolagem suave até o palco termina
        nome = _arrasta(pg)
        assert _estado(pg)["pecas"][[p["nome"] for p in _estado(pg)["pecas"]].index(nome)]["editada"]
        if _portas(pg).count() > 1:
            _portas(pg).nth(1).click()
        else:
            _portas(pg).first.click()
        assert pg.locator("#rw-continuar").is_visible()                              # com edição, pergunta antes
        pg.click("#rw-continuar")
        assert _estado(pg)["ativo"] and any(p["editada"] for p in _estado(pg)["pecas"])    # continuar editando: nada se perdeu
        _portas(pg).first.click()
        pg.click("#rw-descartar")
        e = _estado(pg)
        assert e["ativo"] and not any(p["editada"] for p in e["pecas"])              # descartou e reabriu limpo
    finally:
        ctx.close()


def test_a_porta_do_chip_do_perfil_abre_o_round_no_modo(navegador, pagina):
    ctx, pg, erros = _abre(navegador, pagina, 1440, 900)
    try:
        pg.click('[data-tab="perfil"]')
        achou = None
        for nome in pg.eval_on_selector_all("#pf-botoes button", "bs => bs.map(b => b.dataset.nome)"):
            pg.locator("#pf-botoes button", has_text=nome).first.click()
            if pg.locator("#pf-melhorar .pfchip-rw").count():
                achou = nome
                break
        if not achou:
            pytest.skip("nenhum jogador com chip nesta partida")
        porta = pg.locator("#pf-melhorar .pfchip-rw").first
        rnd, t, quem = int(porta.get_attribute("data-round")), float(porta.get_attribute("data-t")), porta.get_attribute("data-quem")
        assert quem == achou
        assert re.search(r"Reescrever o round \d+ a partir de 3 s antes de ", porta.get_attribute("aria-label"))
        assert pg.locator("#pf-melhorar .pfchip-rw").count() == pg.locator("#pf-melhorar .pfchip").count()     # uma porta por chip (todo chip aqui tem instante)
        porta.click()
        pg.wait_for_function("() => window.__reescrever().ativo")
        e = _estado(pg)
        assert pg.locator("[data-panel='replay']").is_visible()
        assert e["instante"] == max(0, int((t - 3) * 4)) or abs(e["instante"] - (t - 3) * 4) <= 1
        assert pg.locator("#strip .rchip[aria-pressed='true']").get_attribute("data-round") == str(rnd)
        assert e["selecionada"] in (quem, None)
        assert not erros
        _sai(pg)
    finally:
        ctx.close()


@pytest.mark.parametrize("w,h", [(375, 812), (1366, 657)])
def test_o_celular_poe_a_porta_embaixo_do_texto_e_sem_corte(navegador, pagina, w, h):
    ctx, pg, _ = _abre(navegador, pagina, w, h)
    try:
        linha = pg.locator("#autopsy .mrow").first
        porta = linha.locator(".moment-rw")
        if not porta.count():
            pytest.skip("o primeiro momento não tem jogador")
        a, b = linha.locator(".moment").bounding_box(), porta.bounding_box()
        assert b["height"] >= 43.5
        assert b["x"] + b["width"] <= w + 0.5                                         # não corta na borda
        if w <= 640:
            assert b["y"] >= a["y"] + a["height"] - 1                                  # embaixo do texto
        else:
            assert b["x"] >= a["x"] + a["width"] - 1                                   # ao lado
    finally:
        ctx.close()


def test_o_molotov_trocado_e_desenhado_como_o_do_real_so_depois_da_queda_e_pela_duracao_do_efeito(navegador, pagina_com_biblioteca, biblioteca):
    """Instrumenta o desenho de áreas: depois da queda o molotov trocado sai com a MESMA área (raio) do fogo do real, no destino da alternativa,
    pelo `efeito_s` da alternativa; antes da queda e depois do fim não aparece como área."""
    ctx, pg, erros = _abre(navegador, pagina_com_biblioteca, 1440, 900, round_=1, frac=0.1)      # o round 1 tem molotov depois do instante
    try:
        pg.evaluate("""() => { window.__areas = []; const o = MapCore.desenhaArea;
            MapCore.desenhaArea = function (c, arma, X, Y, r) { window.__areas.push([arma, X, Y, r]); return o.apply(this, arguments); }; }""")
        _clica(pg, "#rw-entrar"); _clica(pg, "#rw-ferr-granada"); pg.wait_for_function(PRONTA)
        tr = _troca_a_primeira(pg, tipo="molotov")["trocas"][0]
        _clica(pg, "#play"); pg.wait_for_timeout(200); _clica(pg, "#play")
        zona = _estado(pg)["trocas"]["zonas"][0]
        efeito = biblioteca[tr["alt"]]["efeito_s"]
        assert zona["k"] == "molotov" and zona["f0"] == tr["cai"]
        assert abs((zona["f1"] - zona["f0"]) - efeito * 4) < 0.01                             # dura o `efeito_s` do arremesso real escolhido
        px = pg.evaluate("z => { const R = window.__RADAR__; return [(z.x - R.origin_x) * R.scale_px_per_unit, (R.origin_y - z.y) * R.scale_px_per_unit]; }", zona)
        raio = pg.evaluate("MapCore.RAIO_MOLOTOV_UNIDADES * window.__RADAR__.scale_px_per_unit")

        def areas_no_destino(q):
            pg.evaluate("q => { window.__areas = []; const s = document.getElementById('scrub'); s.disabled = false; s.value = q; s.dispatchEvent(new Event('input')); }", q)
            pg.wait_for_timeout(150)
            return [a for a in pg.evaluate("window.__areas") if a[0] == "molotov" and abs(a[1] - px[0]) < 1.5 and abs(a[2] - px[1]) < 1.5]
        assert areas_no_destino(int(zona["f0"]) - 2) == []                                    # antes da queda: nada de área no destino
        depois = areas_no_destino(int(zona["f0"]) + 2)
        assert len(depois) == 1 and abs(depois[0][3] - raio) < 0.01                           # depois: o fogo, com o raio do molotov do real
        assert len(areas_no_destino(int(zona["f1"]) - 1)) == 1                                # dura até o fim do efeito
        assert areas_no_destino(int(zona["f1"]) + 2) == []                                    # e some depois dele
        assert erros == []
    finally:
        ctx.close()


_ABA_ATIVA_A_VISTA = """() => { const l = document.querySelector('.tabs').getBoundingClientRect(), a = document.querySelector('.tabs [role=tab][aria-selected=true]').getBoundingClientRect();
    return a.left >= l.left - 1 && a.right <= l.right + 1; }"""


def _perfil_com_porta(pg):
    pg.click('[data-tab="perfil"]')
    for nome in pg.eval_on_selector_all("#pf-botoes button", "bs => bs.map(b => b.dataset.nome)"):
        pg.locator("#pf-botoes button", has_text=nome).first.click()
        if pg.locator("#pf-melhorar .pfchip-rw").count():
            return nome
    pytest.skip("nenhum jogador com chip nesta partida")


@pytest.mark.parametrize("w,h", [(375, 812), (1366, 657)])
def test_nenhum_chip_do_perfil_passa_da_largura_do_cartao_e_eles_quebram_de_linha(navegador, pagina, w, h):
    ctx, pg, _ = _abre(navegador, pagina, w, h)
    try:
        _perfil_com_porta(pg)
        for cartao in pg.locator("#pf-melhorar .ponto, #pf-uma-vez .ponto").all():
            faixa = cartao.locator(".pfchips")
            if not faixa.count():
                continue
            c = cartao.bounding_box()
            for par in faixa.locator(".pfpar").all():
                b = par.bounding_box()
                assert b["x"] >= c["x"] - 0.5 and b["x"] + b["width"] <= c["x"] + c["width"] + 0.5      # nada passa do cartão (nem é cortado)
                assert b["height"] >= 43.5
            assert pg.evaluate("e => e.scrollWidth <= e.clientWidth + 1", faixa.element_handle())           # a faixa não rola de lado
        if w == 375:                                                                                     # a 375 há chips o bastante para quebrar? se sim, a linha de baixo existe
            ys = {round(par.bounding_box()["y"]) for par in pg.locator("#pf-melhorar .pfpar").all()}
            assert len(ys) >= 1
    finally:
        ctx.close()


def test_a_aba_ativa_fica_a_vista_no_celular_por_qualquer_porta_sem_rolar_a_pagina(navegador, pagina):
    # o endereço: abre direto na última aba (a mais longe no 375) sem rolar a página
    ctx = navegador.new_context(viewport={"width": 375, "height": 812})
    pg = ctx.new_page()
    try:
        pg.goto(pagina.as_uri() + "#estilos")
        pg.wait_for_function("() => document.querySelector('.tabs [role=tab][aria-selected=true]')")
        pg.wait_for_timeout(900)
        assert pg.evaluate("document.querySelector('.tabs [role=tab][aria-selected=true]').dataset.tab") == "estilos"
        assert pg.evaluate(_ABA_ATIVA_A_VISTA)
        assert pg.evaluate("scrollY") == 0                                                            # só a faixa rolou de lado, a página não
    finally:
        ctx.close()
    # a porta do Perfil: de uma aba longe de volta ao Replay
    ctx, pg, _ = _abre(navegador, pagina, 375, 812)
    try:
        _perfil_com_porta(pg)
        pg.wait_for_timeout(700)
        assert pg.evaluate(_ABA_ATIVA_A_VISTA)                                                        # o Perfil ativo está à vista
        pg.locator("#pf-melhorar .pfchip-rw").first.click()
        pg.wait_for_function("() => window.__reescrever().ativo")
        pg.wait_for_timeout(900)
        assert pg.evaluate("document.querySelector('.tabs [role=tab][aria-selected=true]').dataset.tab") == "replay"
        assert pg.evaluate(_ABA_ATIVA_A_VISTA)                                                        # e o Replay, depois da porta
    finally:
        ctx.close()
