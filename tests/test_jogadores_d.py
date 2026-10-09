"""Página de jogadores da direção "Sala de demo" (design-D, entrega-sala-de-demo §7.3): aviso de corpus, letras
A/B/C em cinza, faixa em toda métrica acima do mínimo, só o bruto abaixo dele e faixa assimétrica desenhada
na posição certa."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
PROCESSED = RAIZ / "data" / "processed"

sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_tactics_browser import navegador  # noqa: E402,F401  (fixture)


@pytest.fixture(scope="module")
def dados():
    if not any(PROCESSED.glob("match_*/player_profile.parquet")):
        pytest.skip("sem o processado")
    from metrics.agregado_jogadores import para_a_pagina
    return para_a_pagina()


def _abre(navegador, tmp_path, dados, w=1300, h=900):
    from scripts.build_jogadores import TEXTOS, WEB
    from scripts.json_em_script import js
    from scripts.design_head import aplica          # tokens e fontes, como no build real
    html = aplica((WEB / "jogadores.html").read_text(encoding="utf-8")
            .replace("/*__MAP_CORE__*/", (WEB / "map_core.js").read_text(encoding="utf-8"))
            .replace("/*__DADOS__*/null", js(dados)).replace("/*__TEXTOS__*/null", js(TEXTOS)))
    f = tmp_path / "jogadores.html"
    f.write_text(html, encoding="utf-8")
    pg = navegador.new_page(viewport={"width": w, "height": h})
    erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto(f.as_uri())
    pg._erros = erros
    return pg


def test_a_pagina_gerada_tem_o_aviso_de_corpus_e_o_topo_do_site():
    from scripts.build_jogadores import TEXTOS, build_html
    html = build_html()
    assert '<header class="site-topo">' in html and 'aria-current="page">Jogadores<' in html
    assert TEXTOS["aviso"].startswith("Esta é a visão do corpus, não de uma partida")


def test_letras_em_tons_de_cinza_e_no_maximo_tres(navegador, tmp_path, dados):
    pg = _abre(navegador, tmp_path, dados)
    try:
        assert pg.eval_on_selector_all("#pilulas .letra", "els => els.map(e => e.textContent)") == ["A", "B"]
        cores = pg.eval_on_selector_all("#pilulas .letra", "els => els.map(e => getComputedStyle(e).backgroundColor)")
        # tons de cinza do tema (tinta, tinta-2, apagado); nunca a cor de lado nem a do decisivo
        from metrics.paleta import le_tokens
        tk = le_tokens()
        rgb = lambda h: f"rgb({int(h[1:3], 16)}, {int(h[3:5], 16)}, {int(h[5:7], 16)})"  # noqa: E731
        assert cores == [rgb(tk["tinta"]), rgb(tk["tinta-2"])], cores
        assert not set(cores) & {rgb(tk[n]) for n in ("ct", "tr", "decisivo")}
        valor = pg.eval_on_selector_all("#adiciona option", "os => os.map(o => o.value).filter(Boolean)")[0]
        pg.select_option("#adiciona", valor)
        assert pg.is_disabled("#adiciona")
        # o ✕ tem 44 px e tira o jogador; o select volta a funcionar
        x = pg.locator("#pilulas button").first
        caixa = x.bounding_box()
        assert caixa["width"] >= 44 and caixa["height"] >= 44
        x.click()
        assert len(pg.evaluate("Jogadores._interno.selecionados()")) == 2 and not pg.is_disabled("#adiciona")
        assert pg._erros == []
    finally:
        pg.close()


def test_faixa_em_toda_metrica_acima_do_minimo_e_so_o_bruto_abaixo(navegador, tmp_path, dados):
    pg = _abre(navegador, tmp_path, dados)
    try:
        r = pg.evaluate("""() => {
            const I = Jogadores._interno, out = [];
            document.querySelectorAll('.metrica').forEach(sec => {
              const chave = sec.dataset.chave, col = I.D.chaves.indexOf(chave);
              const formato = I.D.metricas.find(m => chave.startsWith(m.chave)).formato;
              sec.querySelectorAll('.linha-jog').forEach(l => {
                const s = I.soma(I.D.linhas.filter(r => r[0] === +l.dataset.i), col);
                out.push({chave, formato, partidas: s.partidas, d: s.d, faixa: !!l.querySelector('.faixa'),
                          estado: (l.querySelector('[data-estado]') || {}).dataset ? l.querySelector('[data-estado]')?.dataset.estado : null,
                          texto: l.textContent});
              });
            });
            return out; }""")
        assert r
        for x in r:
            acima = x["partidas"] >= 3 and not (x["formato"] == "pct" and x["d"] < 10)
            if acima:
                assert x["faixa"], x
            else:
                assert not x["faixa"], x
                if x["formato"] == "pct" and x["d"] < 10:
                    assert x["estado"] == "amostra" and "amostra pequena" in x["texto"] and "%" not in x["texto"], x
    finally:
        pg.close()


def test_um_jogador_de_uma_partida_aparece_sem_faixa_e_com_a_contagem(navegador, tmp_path, dados):
    d = json.loads(json.dumps(dados))
    um = next(i for i, j in enumerate(d["jogadores"]) if j["partidas"] == 1)
    pg = _abre(navegador, tmp_path, d)
    try:
        pg.locator("#pilulas button").first.click()
        pg.select_option("#adiciona", str(um))
        linha = pg.locator(f".metrica[data-chave='rating'] .linha-jog[data-i='{um}']")
        assert linha.locator(".faixa").count() == 0 and "1 partida" in linha.inner_text()
    finally:
        pg.close()


def test_a_faixa_assimetrica_fica_onde_o_intervalo_manda(navegador, tmp_path, dados):
    """O ponto vai na posição do valor e a faixa de `inferior` a `superior`, sem supor simetria."""
    pg = _abre(navegador, tmp_path, dados)
    try:
        casos = pg.evaluate("""() => {
            const out = [];
            document.querySelectorAll('.linha-jog').forEach(l => {
              const f = l.querySelector('.faixa'), p = l.querySelector('.ponto'), tr = l.querySelector('.trilho');
              if (!f) return;
              const T = tr.getBoundingClientRect(), F = f.getBoundingClientRect(), P = p.getBoundingClientRect();
              out.push({esq: (F.left - T.left) / T.width, dir: (F.right - T.left) / T.width,
                        ponto: (P.left + P.width / 2 - T.left) / T.width, titulo: tr.title});
            });
            return out; }""")
        assert casos
        assimetricos = [c for c in casos if abs((c["ponto"] - c["esq"]) - (c["dir"] - c["ponto"])) > 0.03]
        assert assimetricos, "o corpus tem casos assimétricos (encolhimento + reamostragem)"
        for c in casos:
            assert 0 <= c["esq"] <= c["dir"] <= 1.0001, c
            assert "intervalo de" in c["titulo"]
    finally:
        pg.close()


def test_filtro_sem_dado_mostra_o_vazio(navegador, tmp_path, dados):
    d = json.loads(json.dumps(dados))
    # um mapa a mais, sem linha nenhuma: escolher ele não tem round desses jogadores
    d["mapas"].append("de_ficticio")
    pg = _abre(navegador, tmp_path, d)
    try:
        pg.click(f'#chips-mapa button[data-valor="{len(d["mapas"]) - 1}"]')
        assert "Nenhum round desses jogadores com esse filtro" in pg.inner_text("#graficos")
        assert pg._erros == []
    finally:
        pg.close()
