"""Reescrever R2 (decisão 57): o modo Reescrever dentro da aba Replay. Entrar (cabeçalho do palco, barra, "Reescrever daqui"), o violeta só no
palco, as 10 peças nas posições reais (as vivas editáveis), arrastar, "Voltar ao real" e sair; o mapa não muda de tamanho nem de lugar."""
from __future__ import annotations

from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_tactics_browser import navegador  # noqa: E402,F401  (fixture)

RAIZ = Path(__file__).resolve().parent.parent
PARTIDA = "match_43"        # FURIA x Vitality, Mirage: o exemplo do design
ROUND = 23
TELAS = {"1440x900": (1440, 900), "1366x657": (1366, 657), "375": (375, 812)}
RECT = "() => { const r = document.getElementById('map').getBoundingClientRect(); return [r.x, r.y + scrollY, r.width, r.height].map(v => Math.round(v * 10) / 10); }"
OBS = "window.__cls = 0; new PerformanceObserver(l => { for (const e of l.getEntries()) if (!e.hadRecentInput) window.__cls += e.value; }).observe({type: 'layout-shift'});"


@pytest.fixture(scope="module")
def pagina(tmp_path_factory):
    from scripts.build_web_page import build_html
    if not (RAIZ / "data" / "processed" / PARTIDA / "web_payload.json").exists():
        pytest.skip("sem o processado")
    arq = tmp_path_factory.mktemp("rw") / f"{PARTIDA}.html"
    arq.write_text(build_html(PARTIDA), encoding="utf-8")
    return arq


def _abre(navegador, arq, w, h, round_=ROUND, frac=0.35):
    ctx = navegador.new_context(viewport={"width": w, "height": h})
    pg = ctx.new_page(); erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto(arq.as_uri() + "#replay")
    pg.wait_for_function("() => window.MapAnnotations && MapAnnotations._interno.S.reprojecoes > 0")
    pg.wait_for_timeout(500)
    pg.locator("#strip .rchip", has_text=str(round_)).first.click()
    pg.wait_for_timeout(200)
    pg.evaluate("f => { const s = document.getElementById('scrub'); s.value = Math.floor(s.max * f); s.dispatchEvent(new Event('input')); }", frac)
    pg.wait_for_timeout(300)
    if w < 1024:
        pg.evaluate("document.getElementById('map').scrollIntoView({block: 'center'})")
    return ctx, pg, erros


def _estado(pg):
    return pg.evaluate("window.__reescrever()")


def _sai(pg):
    """Sair do modo: com edições o "Sair" pede confirmação (R3), então confirma o descarte."""
    pg.click("#rw-sair")
    if pg.locator("#rw-descartar").is_visible():
        pg.click("#rw-descartar")


def test_as_duas_portas_entram_no_instante_parado_e_a_saida_devolve_o_replay(navegador, pagina):
    ctx, pg, erros = _abre(navegador, pagina, 1440, 900)
    try:
        relogio_antes = pg.inner_text("#clock b")
        elenco_antes = pg.locator("#squad-ct .plr").count() + pg.locator("#squad-t .plr").count()
        assert elenco_antes == 10
        assert pg.inner_text("#rw-entrar") == "Reescrever este round"
        assert pg.inner_text("#rw-daqui").startswith("Reescrever daqui")
        for entrar in ("#rw-entrar", "#rw-daqui"):
            assert not _estado(pg)["ativo"]
            pg.click(entrar)
            est = _estado(pg)
            assert est["ativo"] and est["relogio"] == relogio_antes, (entrar, est["relogio"], relogio_antes)
            assert pg.get_attribute("#palco", "data-tema") == "violeta"
            assert pg.inner_text("#rw-sair") == "Sair" and pg.locator("#rw-entrar").count() == 0      # o cabeçalho troca "Reescrever este round" por "Sair"
            pg.click("#rw-sair") if entrar != "#rw-daqui" else pg.keyboard.press("Escape")     # Sair e Esc
            assert not _estado(pg)["ativo"]
            assert pg.get_attribute("#palco", "data-tema") == "escuro"
            assert pg.locator("#squad-ct .plr").count() + pg.locator("#squad-t .plr").count() == 10     # os elencos voltam
            assert pg.get_attribute("#squad-ct", "data-tema") is None
            assert not pg.is_disabled("#play") and not pg.is_disabled("#scrub")
        assert erros == []
    finally:
        ctx.close()


def test_o_violeta_vale_so_para_o_palco_e_as_duas_colunas(navegador, pagina):
    ctx, pg, _ = _abre(navegador, pagina, 1440, 900)
    try:
        cores = """() => ['.site-topo', '#abas-moldura', '#strip'].map(s => getComputedStyle(document.querySelector(s)).backgroundColor).concat(
            document.documentElement.getAttribute('data-tema'), getComputedStyle(document.body).backgroundColor)"""
        antes = pg.evaluate(cores)
        fundo_antes = pg.evaluate("getComputedStyle(document.getElementById('palco')).backgroundColor")
        pg.click("#rw-entrar")
        assert pg.evaluate(cores) == antes                                                # navbar, abas, faixa e página seguem o tema da página
        violeta = pg.evaluate("""() => ['#palco', '#squad-ct', '#squad-t'].map(s => [document.querySelector(s).getAttribute('data-tema'),
            getComputedStyle(document.querySelector(s)).backgroundColor])""")
        assert all(v[0] == "violeta" for v in violeta)
        assert pg.evaluate("getComputedStyle(document.getElementById('palco')).backgroundColor") != fundo_antes
        assert len({v[1] for v in violeta}) <= 2                                          # o mesmo violeta nas três peças
        pg.click("#rw-sair")
        assert pg.evaluate("getComputedStyle(document.getElementById('palco')).backgroundColor") == fundo_antes   # no Assistir nada muda
    finally:
        ctx.close()


@pytest.mark.parametrize("tam", list(TELAS))
def test_o_mapa_fica_do_mesmo_tamanho_e_no_mesmo_lugar_em_todo_estado_e_sem_deslocamento(navegador, pagina, tam):
    w, h = TELAS[tam]
    ctx, pg, erros = _abre(navegador, pagina, w, h)
    try:
        pg.evaluate(OBS)
        rects = [pg.evaluate(RECT)]
        feed = [pg.evaluate("document.querySelector('.feed').getBoundingClientRect().top + scrollY")]
        pg.click("#rw-entrar"); pg.wait_for_timeout(200)
        rects.append(pg.evaluate(RECT)); feed.append(pg.evaluate("document.querySelector('.feed').getBoundingClientRect().top + scrollY"))
        est = _estado(pg)
        alvo = next(p for p in est["pecas"] if p["editavel"])
        xy = pg.evaluate("""n => { const e = window.__reescrever().pecas.find(p => p.nome === n), R = window.__RADAR__, r = document.getElementById('map').getBoundingClientRect();
            return [r.left + (e.x - R.origin_x) * R.scale_px_per_unit * r.width / R.width, r.top + (R.origin_y - e.y) * R.scale_px_per_unit * r.height / R.height]; }""", alvo["nome"])
        pg.mouse.move(*xy); pg.mouse.down(); pg.mouse.move(xy[0] + 40, xy[1] + 30, steps=4); pg.mouse.up()
        pg.wait_for_timeout(200)
        rects.append(pg.evaluate(RECT)); feed.append(pg.evaluate("document.querySelector('.feed').getBoundingClientRect().top + scrollY"))
        _sai(pg); pg.wait_for_timeout(200)
        rects.append(pg.evaluate(RECT)); feed.append(pg.evaluate("document.querySelector('.feed').getBoundingClientRect().top + scrollY"))
        assert len({tuple(r) for r in rects}) == 1, rects                                  # Assistir, editando, depois de arrastar e depois de sair
        if w >= 1024:                                                                       # no celular as colunas descem para baixo do mapa e podem crescer
            assert len({round(f) for f in feed}) == 1, feed                                # (no computador, nada abaixo do palco se mexe)
        assert pg.evaluate("window.__cls") == 0                                            # CLS 0 nas trocas de estado
        assert erros == []
    finally:
        ctx.close()


def test_o_cabecalho_do_palco_tem_55_px_e_o_botao_44_com_o_resumo_encurtando(navegador, pagina):
    ctx, pg, _ = _abre(navegador, pagina, 1024, 700)
    try:
        for passo in ("assistir", "editando"):
            if passo == "editando":
                pg.click("#rw-entrar")
            alt = pg.evaluate("document.querySelector('.roundhead').getBoundingClientRect().height")
            assert round(alt) == 55, (passo, alt)
            botao = "#rw-sair" if passo == "editando" else "#rw-entrar"
            assert pg.evaluate("s => document.querySelector(s).getBoundingClientRect().height", botao) >= 44
            assert pg.evaluate("s => document.querySelector(s).getBoundingClientRect().width", botao) >= 44
        assert pg.evaluate("document.getElementById('rh-res').title") != ""                # o inteiro fica no title
    finally:
        ctx.close()


def test_as_dez_pecas_nas_posicoes_reais_so_as_vivas_editam_e_arrastar_nao_mexe_no_mapa(navegador, pagina):
    ctx, pg, _ = _abre(navegador, pagina, 1440, 900)
    try:
        pg.click("#rw-entrar")
        est = _estado(pg)
        assert len(est["pecas"]) == 10
        vivas = [p for p in est["pecas"] if p["editavel"]]
        assert 0 < len(vivas) < 10                                                          # no round 23 já havia mortos no instante
        assert pg.locator(".banco .peca-rw").count() == 10
        assert pg.locator(".banco .peca-rw[aria-disabled='true']").count() == 10 - len(vivas)
        assert "morto às" in pg.locator(".banco .peca-rw[aria-disabled='true']").first.inner_text()
        # a posição de cada peça viva é a do dado (a do instante), ainda sem edição
        assert all(not p["editada"] and p["x"] == p["x0"] and p["y"] == p["y0"] for p in vivas)
        vista = pg.evaluate("(() => { const v = MapAnnotations._interno.S.view; return [v.zoom, v.panX, v.panY]; })()")
        alvo = vivas[0]
        xy = pg.evaluate("""n => { const e = window.__reescrever().pecas.find(p => p.nome === n), R = window.__RADAR__, r = document.getElementById('map').getBoundingClientRect();
            return [r.left + (e.x - R.origin_x) * R.scale_px_per_unit * r.width / R.width, r.top + (R.origin_y - e.y) * R.scale_px_per_unit * r.height / R.height]; }""", alvo["nome"])
        pg.mouse.move(*xy); pg.mouse.down(); pg.mouse.move(xy[0] + 70, xy[1] - 40, steps=5); pg.mouse.up()
        depois = {p["nome"]: p for p in _estado(pg)["pecas"]}
        mexida = depois[alvo["nome"]]
        assert mexida["editada"] and (mexida["x"], mexida["y"]) != (alvo["x"], alvo["y"])
        assert [p["nome"] for p in depois.values() if p["editada"]] == [alvo["nome"]]       # só a arrastada
        assert pg.evaluate("(() => { const v = MapAnnotations._interno.S.view; return [v.zoom, v.panX, v.panY]; })()") == vista     # o mapa não andou
        assert pg.get_attribute(f".banco .peca-rw[data-nome='{alvo['nome']}']", "aria-pressed") == "true"
        assert pg.locator(".banco .peca-rw.editada").count() == 1
        assert pg.is_enabled("#rw-voltar")
        pg.click("#rw-voltar")
        assert not any(p["editada"] for p in _estado(pg)["pecas"]) and pg.is_disabled("#rw-voltar")
        # a peça morta não se pega: arrastar sobre ela não edita nada
        morto = next(p for p in est["pecas"] if not p["editavel"])
        assert morto["x"] is None
    finally:
        ctx.close()


def test_no_modo_o_real_fica_parado_o_tocar_esta_desligado_e_trocar_de_round_sai(navegador, pagina):
    ctx, pg, _ = _abre(navegador, pagina, 1440, 900)
    try:
        pg.click("#rw-entrar")
        assert pg.is_disabled("#play") and pg.is_disabled("#scrub")
        pg.evaluate("document.activeElement.blur()")
        pg.keyboard.press("Space")
        pg.wait_for_timeout(300)
        assert pg.inner_text("#play") == "▶"
        assert "Não é uma previsão." in pg.inner_text("#squad-t")                          # a frase fixa de honestidade
        texto = pg.inner_text("#palco").lower()
        for proibido in ("venceu", "ganhou", "placar", "%"):
            assert proibido not in texto, proibido                                         # nada de placar nem de "ganharia" na sua versão
        pg.locator("#strip .rchip", has_text="22").first.click()
        assert not _estado(pg)["ativo"] and pg.locator("#squad-ct .plr").count() == 5
        assert pg.get_attribute("#palco", "data-tema") == "escuro"
    finally:
        ctx.close()


def test_a_peca_da_sua_versao_tem_contraste_de_3_para_1_contra_o_radar_nos_mapas_com_radar(navegador, tmp_path_factory):
    from scripts.build_site import match_summary
    from scripts.build_web_page import build_html
    from scripts.design.mede_peca_reescrever import JS, MINIMO
    ids = sorted(d.name for d in (RAIZ / "data" / "processed").glob("match_*"))
    por_mapa: dict[str, str] = {}
    for i in ids:
        m = match_summary(i)
        if m and m["has_radar"] and m["map"] not in por_mapa:
            por_mapa[m["map"]] = i
    if len(por_mapa) < 5:
        pytest.skip("sem partidas de mapas com radar")
    pasta = tmp_path_factory.mktemp("contraste")
    ctx = navegador.new_context(viewport={"width": 1440, "height": 900})
    try:
        for mapa, partida in por_mapa.items():
            arq = pasta / f"{partida}.html"
            arq.write_text(build_html(partida), encoding="utf-8")
            pg = ctx.new_page()
            pg.goto(arq.as_uri() + "#replay"); pg.wait_for_timeout(600)
            r = pg.evaluate(JS)
            pg.close()
            assert r and r["pior"] >= MINIMO and r["abaixo"] == 0, (mapa, r)
            assert r["piorG"] >= MINIMO and r["abaixoG"] == 0, (mapa, "fantasma", r)      # o anel tracejado do real (R3) também lê no radar
    finally:
        ctx.close()


def test_no_modo_as_setas_o_esc_do_popover_e_a_troca_de_aba_se_comportam(navegador, pagina):
    ctx, pg, _ = _abre(navegador, pagina, 1440, 900)
    try:
        rot_ct, rot_t = pg.get_attribute("#squad-ct", "aria-label"), pg.get_attribute("#squad-t", "aria-label")
        pg.click("#rw-entrar")
        assert pg.get_attribute("#squad-ct", "aria-label") == "Peças" and pg.get_attribute("#squad-t", "aria-label") == "Reescrever este round"
        valor = pg.input_value("#scrub")
        pg.evaluate("document.activeElement.blur()")
        for tecla in ("ArrowRight", "ArrowLeft", "]", "["):
            pg.keyboard.press(tecla)
        assert pg.input_value("#scrub") == valor                                          # o real não anda por teclado
        pg.click("#b-atalhos")                                                            # o popover "?" aberto: o Esc fecha ele, não o modo
        pg.keyboard.press("Escape")
        assert _estado(pg)["ativo"]
        pg.keyboard.press("Escape")
        assert not _estado(pg)["ativo"]
        assert pg.get_attribute("#squad-ct", "aria-label") == rot_ct and pg.get_attribute("#squad-t", "aria-label") == rot_t
        pg.click("#rw-entrar")
        pg.locator('[data-tab="insights"]').first.click()                                 # outra aba: sai do modo
        assert not _estado(pg)["ativo"]
        pg.locator('[data-tab="replay"]').first.click()
        assert pg.get_attribute("#palco", "data-tema") == "escuro" and pg.locator("#squad-ct .plr").count() == 5
    finally:
        ctx.close()


@pytest.mark.parametrize("largura,altura", [(1440, 900), (1366, 657), (375, 812)])
def test_nenhum_texto_do_banco_fica_cortado_e_a_linha_do_tempo_inteira(navegador, pagina, largura, altura):
    ctx, pg, _ = _abre(navegador, pagina, largura, altura)
    try:
        linha = lambda: pg.evaluate("(() => { const r = document.getElementById('scrub').getBoundingClientRect(); return r.width; })()")
        antes = linha()
        assert antes > 75, antes                                                             # no Replay normal a linha do tempo não vira ponto
        if largura < 560:
            assert pg.evaluate("getComputedStyle(document.getElementById('rw-daqui')).display") == "none"
        pg.click("#rw-entrar")
        assert linha() > 75 and abs(linha() - antes) < 1                                    # desligada, mas inteira e do mesmo tamanho
        vivas = [p for p in _estado(pg)["pecas"] if p["editavel"]]
        xy = pg.evaluate("""n => { const e = window.__reescrever().pecas.find(p => p.nome === n), R = window.__RADAR__, r = document.getElementById('map').getBoundingClientRect();
            return [r.left + (e.x - R.origin_x) * R.scale_px_per_unit * r.width / R.width, r.top + (R.origin_y - e.y) * R.scale_px_per_unit * r.height / R.height]; }""", vivas[0]["nome"])
        pg.mouse.move(*xy); pg.mouse.down(); pg.mouse.move(xy[0] + 30, xy[1] - 20, steps=4); pg.mouse.up()   # edita uma: o cartão ganha a etiqueta "editado"
        assert pg.locator(".banco .peca-rw.editada").count() == 1
        assert pg.evaluate("(() => { const s = document.getElementById('squad-ct'); return s.scrollWidth <= s.clientWidth + 1; })()")
        cortados = pg.evaluate("""() => [...document.querySelectorAll('.banco .peca-rw')].flatMap(card => {
            const c = card.getBoundingClientRect(), raio = parseFloat(getComputedStyle(card).borderTopLeftRadius) || 0, ruim = [];
            for (const f of card.querySelectorAll('.pr-nome, .pr-meio, .pr-hp, .pr-tag')) {
              const r = f.getBoundingClientRect(); if (!r.width) continue;
              if (f.scrollHeight > f.clientHeight + 1) ruim.push(f.className + ': altura cortada');
              if (f.scrollWidth > f.clientWidth + 1) ruim.push(f.className + ': texto com reticências ' + f.textContent + ' ' + f.scrollWidth + '>' + f.clientWidth);
              if (r.bottom > c.bottom - 3 || r.top < c.top + 3) ruim.push(f.className + ': encosta na borda de cima/baixo');
              if (r.left < c.left + Math.min(raio, 12) * 0.5 || r.right > c.right - 6 || c.right > document.getElementById('squad-ct').getBoundingClientRect().right - 4) ruim.push(f.className + ': encosta na borda do lado');
            }
            return ruim; })""")
        assert not cortados, cortados
        assert vivas
    finally:
        ctx.close()


def test_no_celular_o_cabecalho_tem_a_mesma_altura_nos_dois_estados(navegador, pagina):
    ctx, pg, _ = _abre(navegador, pagina, 375, 812)
    try:
        medir = "() => { const h = document.querySelector('.roundhead'), a = document.getElementById('rh-acoes').getBoundingClientRect(), g = document.querySelector('.roundhead .big').getBoundingClientRect(); return [h.getBoundingClientRect().height, a.top - g.top, document.getElementById('rh-acoes').getBoundingClientRect().left - g.right]; }"
        antes = pg.evaluate(medir)
        pg.click("#rw-entrar")
        depois = pg.evaluate(medir)
        assert antes[0] == depois[0], (antes, depois)
        assert antes[1] > 20 and depois[1] == antes[1], (antes, depois)            # o botão mora numa linha só dele, no mesmo lugar nos dois estados
    finally:
        ctx.close()


def test_editar_uma_peca_nao_mexe_em_nada_da_pagina_cls_zero(navegador, pagina):
    ctx, pg, _ = _abre(navegador, pagina, 1366, 657)
    try:
        pg.evaluate("window.__ls = 0; new PerformanceObserver(l => { for (const e of l.getEntries()) if (!e.hadRecentInput) window.__ls += e.value; }).observe({type: 'layout-shift', buffered: false});")
        pg.click("#rw-entrar")
        alvo = next(p for p in _estado(pg)["pecas"] if p["editavel"])
        xy = pg.evaluate("""n => { const e = window.__reescrever().pecas.find(p => p.nome === n), R = window.__RADAR__, r = document.getElementById('map').getBoundingClientRect();
            return [r.left + (e.x - R.origin_x) * R.scale_px_per_unit * r.width / R.width, r.top + (R.origin_y - e.y) * R.scale_px_per_unit * r.height / R.height]; }""", alvo["nome"])
        pg.mouse.move(*xy); pg.mouse.down(); pg.mouse.move(xy[0] + 40, xy[1] - 30, steps=5); pg.mouse.up(); pg.wait_for_timeout(300)
        assert pg.locator(".banco .peca-rw.editada").count() == 1
        _sai(pg); pg.wait_for_timeout(300)
        assert pg.evaluate("window.__ls") == 0
    finally:
        ctx.close()
