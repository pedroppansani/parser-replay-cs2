"""Reescrever R3 (decisão 58): tocar a sua versão, o fantasma do real onde difere, "O que mudou" (com o aviso da morte, D3) e a confirmação ao sair
com edições. A regra de honestidade vale aqui: nenhum texto diz nem sugere que a sua versão ganharia."""
from __future__ import annotations

import re

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_reescrever_modo import (  # noqa: E402,F401  (fixtures e ajudas)
    OBS, RECT, _abre, _estado, _sai, navegador, pagina)

XY = """n => { const e = window.__reescrever().pecas.find(p => p.nome === n), R = window.__RADAR__, r = document.getElementById('map').getBoundingClientRect();
    return [r.left + (e.x - R.origin_x) * R.scale_px_per_unit * r.width / R.width, r.top + (R.origin_y - e.y) * R.scale_px_per_unit * r.height / R.height]; }"""


def _arrasta(pg, nome=None, dx=70, dy=-50):
    est = _estado(pg)
    nome = nome or next(p for p in est["pecas"] if p["editavel"])["nome"]
    xy = pg.evaluate(XY, nome)
    pg.mouse.move(*xy); pg.mouse.down(); pg.mouse.move(xy[0] + dx, xy[1] + dy, steps=5); pg.mouse.up()
    pg.wait_for_timeout(150)
    return nome


def test_sem_edicao_o_sair_e_o_esc_saem_direto(navegador, pagina):
    ctx, pg, _ = _abre(navegador, pagina, 1440, 900)
    try:
        pg.click("#rw-entrar"); pg.click("#rw-sair")
        assert not _estado(pg)["ativo"] and pg.locator(".rw-dialogo").count() == 0
        pg.click("#rw-entrar"); pg.keyboard.press("Escape")
        assert not _estado(pg)["ativo"]
    finally:
        ctx.close()


def test_com_edicao_o_sair_e_o_esc_pedem_confirmacao_com_foco_e_teclado(navegador, pagina):
    ctx, pg, _ = _abre(navegador, pagina, 1440, 900)
    try:
        pg.click("#rw-entrar"); _arrasta(pg)
        for abre in (lambda: pg.click("#rw-sair"), lambda: pg.keyboard.press("Escape")):
            abre()
            assert pg.evaluate("document.querySelector('.rw-dialogo').open")
            assert _estado(pg)["ativo"]                                                   # ainda não descartou
            assert pg.inner_text(".rw-dialogo h3") == "Descartar a sua versão?"
            assert pg.evaluate("document.activeElement.id") == "rw-continuar"             # o foco abre no botão seguro
            pg.keyboard.press("Tab"); assert pg.evaluate("document.activeElement.id") == "rw-descartar"
            pg.keyboard.press("Tab"); assert pg.evaluate("document.activeElement.id") == "rw-continuar"        # o foco dá a volta, não sai do aviso
            pg.keyboard.press("Shift+Tab"); assert pg.evaluate("document.activeElement.id") == "rw-descartar"
            pg.keyboard.press("Shift+Tab")
            pg.keyboard.press("Escape")                                                    # o Esc do aviso é "Continuar editando"
            assert not pg.evaluate("document.querySelector('.rw-dialogo').open") and _estado(pg)["ativo"]
            assert any(p["editada"] for p in _estado(pg)["pecas"])                        # a edição continua
        pg.click("#rw-sair"); pg.click("#rw-continuar")
        assert _estado(pg)["ativo"] and pg.evaluate("document.activeElement.id") == "rw-sair"        # o foco volta para quem abriu
        pg.click("#rw-sair"); pg.keyboard.press("Enter")                                  # Enter no foco inicial = Continuar editando
        assert _estado(pg)["ativo"]
        pg.click("#rw-sair"); pg.click("#rw-descartar")
        est = _estado(pg)
        assert not est["ativo"]                                                           # saiu e descartou
        pg.click("#rw-entrar")
        assert not any(p["editada"] for p in _estado(pg)["pecas"])
    finally:
        ctx.close()


def test_o_play_so_vale_com_peca_movida_e_a_peca_anda_na_velocidade_medida_ate_o_ponto(navegador, pagina):
    ctx, pg, erros = _abre(navegador, pagina, 1440, 900)
    try:
        pg.click("#rw-entrar")
        assert pg.evaluate("document.getElementById('play').disabled")                    # sem peça movida não há o que tocar
        nome = _arrasta(pg)
        assert not pg.evaluate("document.getElementById('play').disabled")
        assert pg.evaluate("document.getElementById('speed').disabled") is False
        antes = next(p for p in _estado(pg)["pecas"] if p["nome"] == nome)
        pg.click("#play"); pg.wait_for_timeout(1500); pg.click("#play")                  # toca e pausa
        est = _estado(pg)
        assert est["sua"] and est["quadro"] > est["instante"]
        p = next(q for q in est["pecas"] if q["nome"] == nome)
        decorrido = (est["quadro"] - est["instante"]) / 4                                  # 4 quadros por segundo
        andou = ((p["agora"][0] - p["x0"]) ** 2 + (p["agora"][1] - p["y0"]) ** 2) ** 0.5
        total = ((antes["x"] - antes["x0"]) ** 2 + (antes["y"] - antes["y0"]) ** 2) ** 0.5
        assert abs(andou - min(total, p["velocidade"] * decorrido)) < 1.5                  # velocidade medida (a da prancheta), em linha reta
        # nada é editável enquanto a sua versão toca: arrastar não mexe na peça
        xy = pg.evaluate(XY, nome)
        pg.mouse.move(*xy); pg.mouse.down(); pg.mouse.move(xy[0] + 50, xy[1], steps=3); pg.mouse.up()
        assert next(q for q in _estado(pg)["pecas"] if q["nome"] == nome)["x"] == antes["x"]
        pg.click("#rw-editar")                                                             # "Voltar a editar": de volta ao instante
        est = _estado(pg)
        assert not est["sua"] and est["quadro"] == est["instante"]
        assert erros == []
    finally:
        ctx.close()


def test_o_fantasma_so_aparece_onde_a_sua_versao_difere_e_a_morte_do_real_fica_so_nele(navegador, pagina):
    ctx, pg, _ = _abre(navegador, pagina, 1440, 900)
    try:
        pg.click("#rw-entrar")
        assert _estado(pg)["fantasmas"] == []                                              # antes de tocar não há fantasma
        nome = _arrasta(pg, "molodoy")
        pg.click("#play"); pg.wait_for_timeout(1200); pg.click("#play")
        est = _estado(pg)
        assert [f["nome"] for f in est["fantasmas"]] == [nome]                            # só quem foi editado, e só onde difere do real
        assert est["soNoReal"] > 0                                                         # a smoke do molodoy depois do instante fica só no real
        pg.click("#rw-fantasma")
        assert "Desligado" in pg.inner_text("#rw-fantasma") and pg.get_attribute("#rw-fantasma", "aria-pressed") == "false"
        pg.click("#rw-fantasma")
        assert "Ligado" in pg.inner_text("#rw-fantasma")
        # a morte do real do editado só existe no fantasma: no fim, o fantasma é ✕ e a peça da sua versão segue viva
        pg.evaluate("() => { const s = document.getElementById('scrub'); s.disabled = false; }")
        pg.click("#rw-voltar"); pg.wait_for_timeout(100)
        assert _estado(pg)["fantasmas"] == [] and not _estado(pg)["sua"]                   # voltar ao real limpa tudo
    finally:
        ctx.close()


def test_o_que_mudou_conta_o_movimento_a_morte_do_real_e_avisa_do_duelo_sem_prometer_nada(navegador, pagina):
    ctx, pg, _ = _abre(navegador, pagina, 1440, 900)
    try:
        pg.click("#rw-entrar")
        assert "Nada ainda" in pg.inner_text("#rw-mudou")
        _arrasta(pg, "molodoy")
        itens = pg.locator("#rw-mudou li").all_inner_texts()
        assert itens[0].startswith("molodoy sai de CTSpawn às 1:21 e vai até o ponto marcado: chega às ")
        texto = " ".join(itens)
        assert "No real, molodoy matou ZywOo às 0:52. Na sua versão molodoy saiu do lugar, mas a morte acontece como no real" in texto   # D3 (a)
        assert "No real, molodoy morreu para apEX às 0:47. Na sua versão, o site não refaz esse duelo." in texto
        assert "fica só no real" in texto                                                  # a granada que ele jogaria depois
        assert pg.get_attribute("#rw-mudou", "aria-live") == "polite"
        # honestidade: o site nunca diz nem sugere que a sua versão ganharia
        painel = pg.inner_text("#squad-t").lower()
        fora_da_frase = painel.replace("o site não simula o cs2 e não diz quem venceria os duelos", "")
        assert not re.search(r"ganh|venc|vit[óo]ria|placar|melhor|pior|resultado|prever|previs[ãa]o\b(?!\.)|n[ãa]o morre|sobreviv|salv", fora_da_frase.replace("não é uma previsão", "")), fora_da_frase
        pg.click("#rw-voltar")
        assert "Nada ainda" in pg.inner_text("#rw-mudou")
    finally:
        ctx.close()


@pytest.mark.parametrize("tam", [(1440, 900), (1366, 657), (375, 812)])
def test_tocar_pausar_e_voltar_a_editar_nao_mexem_no_mapa_nem_na_pagina_cls_zero(navegador, pagina, tam):
    ctx, pg, erros = _abre(navegador, pagina, *tam)
    try:
        pg.evaluate(OBS)
        antes = pg.evaluate(RECT)
        feed = pg.evaluate("document.querySelector('.feed').getBoundingClientRect().top + scrollY")
        pg.click("#rw-entrar"); _arrasta(pg, "molodoy", 40, -30)
        pg.click("#play"); pg.wait_for_timeout(900)
        assert pg.evaluate(RECT) == antes                                                  # tocando
        pg.click("#play"); pg.wait_for_timeout(100)
        assert pg.evaluate(RECT) == antes                                                  # pausada
        pg.click("#rw-editar"); pg.wait_for_timeout(100)
        _sai(pg); pg.wait_for_timeout(200)
        assert pg.evaluate(RECT) == antes
        if tam[0] >= 1024:
            assert round(pg.evaluate("document.querySelector('.feed').getBoundingClientRect().top + scrollY")) == round(feed)
        assert pg.evaluate("window.__cls") == 0
        assert erros == []
    finally:
        ctx.close()


def test_todo_rotulo_que_o_modo_usa_vem_do_python_e_existe():
    from pathlib import Path
    from leitura.reescrever import TEXTOS_DO_MODO
    js = (Path(__file__).resolve().parent.parent / "dashboard" / "web" / "partida" / "10-reescrever.js").read_text(encoding="utf-8")
    usados = set(re.findall(r"\bTX\.([a-z_0-9]+)", js))
    assert usados, "o modo não lê nenhum rótulo?"
    faltam = usados - set(TEXTOS_DO_MODO) - {"velocidade"}       # `velocidade` entra no build (a mesma tabela da prancheta, decisão 43)
    assert not faltam, faltam


def test_movida_por_menos_de_8_u_volta_ao_real_e_o_foco_nao_se_perde_ao_voltar_a_editar(navegador, pagina):
    ctx, pg, _ = _abre(navegador, pagina, 1440, 900)
    try:
        pg.click("#rw-entrar")
        _arrasta(pg, "FalleN", 0.5, 0)                                                      # um empurrãozinho: não conta como edição
        assert not any(p["editada"] for p in _estado(pg)["pecas"])
        assert pg.evaluate("document.getElementById('play').disabled")
        _arrasta(pg, "molodoy")
        pg.click("#play"); pg.wait_for_timeout(300)
        pg.click("#rw-sair")                                                               # abrir o aviso pausa a sua versão
        assert not pg.evaluate("document.getElementById('play').getAttribute('aria-label') === 'Pausar a sua versão'")
        pg.click("#rw-continuar")
        pg.focus("#rw-editar"); pg.keyboard.press("Enter")
        assert pg.evaluate("document.activeElement !== document.body")                     # o botão que se desligou não deixa o foco cair no vazio
    finally:
        ctx.close()


def test_depois_da_morte_do_real_a_peca_editada_fica_esmaecida_e_o_fantasma_vira_x(navegador, pagina):
    ctx, pg, _ = _abre(navegador, pagina, 1440, 900)
    try:
        pg.click("#rw-entrar"); _arrasta(pg, "molodoy")
        pg.click("#play"); pg.wait_for_timeout(300); pg.click("#play")
        assert _estado(pg)["esmaecidas"] == []                                             # no começo ele está vivo nos dois
        pg.evaluate("() => { const s = document.getElementById('scrub'); s.value = s.max; s.dispatchEvent(new Event('input')); }")
        est = _estado(pg)
        assert est["esmaecidas"] == ["molodoy"]                                           # o real já o matou: a peça da sua versão não parece viva e bem
        assert [f for f in est["fantasmas"] if f["nome"] == "molodoy" and not f["vivo"]]  # e o ✕ do real fica onde ele morreu
    finally:
        ctx.close()


def test_a_flash_o_plant_e_o_desarme_do_editado_entram_em_o_que_mudou_com_a_mesma_frase(navegador, pagina):
    ctx, pg, _ = _abre(navegador, pagina, 1440, 900, round_=13, frac=0.1)             # round 13: apEX flasha e planta, YEKINDAR desarma
    try:
        pg.click("#rw-entrar")
        _arrasta(pg, "apEX", 40, 20); _arrasta(pg, "YEKINDAR", -40, 20)
        texto = " ".join(pg.locator("#rw-mudou li").all_inner_texts())
        assert "No real, apEX plantou a bomba às " in texto
        assert "No real, YEKINDAR desarmou a bomba às " in texto
        assert "No real, a flash de apEX das " in texto and " cegou " in texto
        assert texto.count("Na sua versão, o site mantém o que aconteceu no real.") >= 3
    finally:
        ctx.close()


def test_trocar_de_round_ou_de_aba_com_edicao_pergunta_antes_de_descartar(navegador, pagina):
    ctx, pg, _ = _abre(navegador, pagina, 1440, 900)
    try:
        pg.click("#rw-entrar")
        pg.locator("#strip .rchip", has_text="22").first.click()                           # sem edição: troca direto
        assert not _estado(pg)["ativo"]
        pg.click("#rw-entrar"); _arrasta(pg)
        for destino in (lambda: pg.locator("#strip .rchip", has_text="21").first.click(), lambda: pg.locator("[data-tab='jogadores']").first.click()):
            destino()
            assert pg.evaluate("document.querySelector('.rw-dialogo').open") and _estado(pg)["ativo"]       # perguntou e ainda não saiu
            pg.click("#rw-continuar")
            assert _estado(pg)["ativo"] and any(p["editada"] for p in _estado(pg)["pecas"])                  # Continuar editando: nada muda
            assert pg.evaluate("document.querySelector('[data-tab=replay]').getAttribute('aria-selected')") == "true"
        pg.locator("#strip .rchip", has_text="21").first.click(); pg.click("#rw-descartar")
        assert not _estado(pg)["ativo"] and "21" in pg.evaluate("document.querySelector('.roundhead .big').textContent")   # descartou e foi para o round 21
        pg.click("#rw-entrar"); _arrasta(pg)
        pg.locator("[data-tab='jogadores']").first.click(); pg.click("#rw-descartar")
        assert not _estado(pg)["ativo"] and pg.evaluate("document.querySelector('[data-tab=jogadores]').getAttribute('aria-selected')") == "true"
    finally:
        ctx.close()
