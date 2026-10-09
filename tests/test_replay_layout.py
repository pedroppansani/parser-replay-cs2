"""O Replay da direção "Sala de demo" (design-B2): tocar visível sem rolar, faixa de rounds, legenda com os
glifos reais, atalhos no "?", ferramentas embaixo da legenda, rótulos do mapa e anel duplo."""
from __future__ import annotations

from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_tactics_browser import navegador  # noqa: E402,F401  (fixture)

RAIZ = Path(__file__).resolve().parent.parent
PARTIDA = "match_02"   # Mirage, 22 rounds (MR12: separador depois do 12)


@pytest.fixture(scope="module")
def pagina_html(tmp_path_factory):
    from scripts.build_web_page import build_html
    if not (RAIZ / "data" / "processed" / PARTIDA / "web_payload.json").exists():
        pytest.skip("sem o processado")
    arq = tmp_path_factory.mktemp("replay") / f"{PARTIDA}.html"
    arq.write_text(build_html(PARTIDA), encoding="utf-8")
    return arq


def _abre(navegador, arq, w=1440, h=900, hash_="#replay"):
    ctx = navegador.new_context(viewport={"width": w, "height": h})
    pg = ctx.new_page()
    erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto(arq.as_uri() + hash_)
    pg.wait_for_selector("#play", state="attached")
    pg.wait_for_timeout(400)
    pg._erros = erros
    return ctx, pg


def _para_em(pg, fracao):
    pg.evaluate("""f => { const s = document.getElementById('scrub'); s.value = Math.round(+s.max * f);
                          s.dispatchEvent(new Event('input')); }""", fracao)
    pg.wait_for_timeout(150)


@pytest.mark.parametrize("w,h", [(1440, 900), (375, 667), (375, 812)])
def test_o_tocar_aparece_sem_rolar_abrindo_pelo_hash_e_pela_aba(navegador, pagina_html, w, h):
    for hash_ in ("#replay", ""):
        ctx, pg = _abre(navegador, pagina_html, w, h, hash_)
        try:
            if not hash_:
                pg.click('[data-tab="replay"]')
                pg.wait_for_timeout(200)
            r = pg.evaluate("""() => { const t = document.getElementById('play'), b = t.getBoundingClientRect();
                const el = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
                return {dentro: b.top >= 0 && b.bottom <= innerHeight, eleMesmo: el === t || t.contains(el),
                        rolagem: scrollY, w: b.width, h: b.height}; }""")
            assert r["dentro"] and r["eleMesmo"] and r["rolagem"] == 0, (w, h, hash_, r)
            assert r["w"] >= 44 and r["h"] >= 44
            assert pg._erros == []
        finally:
            ctx.close()


def test_a_faixa_de_rounds_tem_chips_de_44_losango_no_decisivo_e_separador_no_meio_tempo(navegador, pagina_html):
    ctx, pg = _abre(navegador, pagina_html)
    try:
        chips = pg.locator("#strip .rchip")
        caixa = chips.first.bounding_box()
        assert caixa["width"] >= 44 and caixa["height"] >= 44
        filhos = pg.eval_on_selector_all("#strip > *", "els => els.map(e => e.className)")
        i = filhos.index("meio-tempo")
        assert filhos[:i] == ["rchip" if "key" not in c else c for c in filhos[:i]] and i == 12
        losango = pg.eval_on_selector("#strip .rchip.key", "e => getComputedStyle(e, '::before').transform")
        assert losango not in ("none", "")
        # escolher um round depois do separador seleciona o chip certo (os índices não contam o separador)
        pg.locator("#strip .rchip", has_text="15").first.click()
        assert pg.eval_on_selector_all("#strip .rchip[aria-pressed=true]", "els => els.map(e => e.textContent)") == ["15"]
        assert pg.inner_text("#rh-round") == "Round 15"
    finally:
        ctx.close()


def test_legenda_com_glifos_reais_e_ferramentas_embaixo_dela(navegador, pagina_html):
    ctx, pg = _abre(navegador, pagina_html)
    try:
        itens = pg.eval_on_selector_all("#maplegend span", "els => els.map(e => [e.textContent, !!e.querySelector('canvas')])")
        assert [t for t, _ in itens] == ["CT", "TR", "Smoke", "Flash", "HE", "Molotov", "morto"]
        assert all(c for _, c in itens)
        # cada glifo foi de fato desenhado (canvas com pixel pintado)
        pintados = pg.eval_on_selector_all("#maplegend canvas", """els => els.map(c => {
            const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
            let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i] > 0) n++; return n; })""")
        assert all(n > 20 for n in pintados), pintados
        ordem = pg.evaluate("""() => ['map', 'play', 'maplegend', 'anot-barra'].map(id =>
            document.getElementById(id).getBoundingClientRect().top)""")
        assert ordem == sorted(ordem), ordem
    finally:
        ctx.close()


def test_o_transporte_gruda_no_pe_da_tela(navegador, pagina_html):
    ctx, pg = _abre(navegador, pagina_html, 375, 667)
    try:
        estilo = pg.eval_on_selector(".transport", "e => [getComputedStyle(e).position, getComputedStyle(e).bottom]")
        assert estilo == ["sticky", "0px"]
    finally:
        ctx.close()


def test_o_interrogacao_abre_e_fecha_os_atalhos(navegador, pagina_html):
    ctx, pg = _abre(navegador, pagina_html)
    try:
        assert pg.is_hidden("#atalhos")
        pg.click("#b-atalhos")
        assert pg.is_visible("#atalhos") and pg.get_attribute("#b-atalhos", "aria-expanded") == "true"
        assert "0,25×" in pg.inner_text("#atalhos") and "espaço" in pg.inner_text("#atalhos")
        pg.keyboard.press("Escape")
        assert pg.is_hidden("#atalhos") and pg.get_attribute("#b-atalhos", "aria-expanded") == "false"
        pg.click("#b-atalhos")
        pg.click("#rh-round")                     # clique fora fecha
        assert pg.is_hidden("#atalhos")
        # os atalhos não ficam mais como parágrafos fixos acima do mapa
        assert pg.locator('[data-panel="replay"] .lead').count() == 0
    finally:
        ctx.close()


@pytest.mark.parametrize("w,h", [(1440, 900), (375, 667)])
def test_os_rotulos_do_mapa_tem_tamanho_de_tela_e_nao_se_sobrepoem(navegador, pagina_html, w, h):
    ctx, pg = _abre(navegador, pagina_html, w, h)
    try:
        _para_em(pg, 0.45)
        caixas = pg.evaluate("window.__medicaoRotulos.caixas()")
        assert len(caixas) >= 5
        # 12,5 px de fonte em px de TELA: a altura da letra não depende da largura do mapa
        assert all(c["alt"] >= 7.5 for c in caixas), caixas
        for i, a in enumerate(caixas):
            for b in caixas[i + 1:]:
                sobrepoe = a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"] and \
                    a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"]
                assert not sobrepoe, (a["txt"], b["txt"])
        # o gancho de medição troca o modo e redesenha
        pg.evaluate("window.__medicaoRotulos.define('sem_texto')")
        assert pg.evaluate("window.__medicaoRotulos.caixas().length") == 0
        pg.evaluate("window.__medicaoRotulos.define('normal')")
        assert pg.evaluate("window.__medicaoRotulos.caixas().length") == len(caixas)
    finally:
        ctx.close()


def test_a_peca_do_replay_tem_o_anel_duplo(navegador, pagina_html):
    """Em volta da peça viva: a cor do lado, o contorno escuro e o halo claro, nessa ordem de dentro para fora."""
    from metrics.paleta import le_tokens
    tk = le_tokens()
    hexa = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))  # noqa: E731
    ctx, pg = _abre(navegador, pagina_html)
    try:
        r = pg.evaluate("""() => {
            const c = document.createElement('canvas'); c.width = c.height = 60;
            const g = c.getContext('2d');
            MapCore.desenhaJogador(g, 30, 30, {cor: getComputedStyle(document.documentElement).getPropertyValue('--ct').trim(),
                                               estado: 'vivo', hp: 100, nome: ''});
            const px = x => Array.from(g.getImageData(x, 30, 1, 1).data.slice(0, 3));
            return [px(30), px(30 + 7), px(30 + 9)]; }""")
        # ±2 por canal: o Chromium do CI arredonda a borda suavizada um nível diferente do Chrome local
        perto = lambda px, cor: max(abs(a - b) for a, b in zip(px, hexa(tk[cor]))) <= 2  # noqa: E731
        assert perto(r[0], "ct") and perto(r[1], "contorno") and perto(r[2], "tinta"), r
    finally:
        ctx.close()
