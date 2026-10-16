"""Seção "Quanto cada round pesou" da aba Placar (troca do gráfico de linha da chance de vitória).

A barra de cada round é `wp_a_depois - wp_a_antes` da curva que o payload já publica; nenhum número
novo entra na página (o bloco do Python é só texto) e o round decisivo é o publicado.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

import pytest

from leitura.peso_dos_rounds import bloco, placar_antes_e_depois, variacao
from metrics.formatting import format_pp
from metrics.paleta import contraste, le_tokens

RAIZ = Path(__file__).resolve().parent.parent
PROCESSED = RAIZ / "data" / "processed"
TEMPLATE = (RAIZ / "dashboard" / "web" / "template.html").read_text(encoding="utf-8")
NOMES = {"A": "Alfa", "B": "Bravo"}


def _payloads():
    return [(p.parent.name, json.loads(p.read_text(encoding="utf-8")))
            for p in sorted(PROCESSED.glob("match_*/web_payload.json"))]


def _curva(*vencedores: str) -> list[dict]:
    """Curva sintética no formato de `metrics.win_probability.curva_da_partida` (MR12)."""
    from metrics.win_probability import curva_da_partida
    a = b = 0
    prog = []
    for i, v in enumerate(vencedores, start=1):
        a, b = (a + 1, b) if v == "A" else (a, b + 1)
        prog.append({"round": i, "winner_team": v, "score_a": a, "score_b": b})
    return curva_da_partida(prog).to_dicts()


def _payload(vencedores: str) -> dict:
    from metrics.win_probability import round_decisivo, curva_da_partida
    import polars as pl
    curva = _curva(*vencedores)
    resumo = round_decisivo(pl.DataFrame(curva))
    return {"win_probability": {"curve": curva, "top": resumo["top"], "empate_no_topo": resumo["empate_no_topo"],
                                "maior_wpa": resumo["maior_wpa"], "minimo_exigido": resumo["minimo_exigido"]},
            "decisive_round": resumo["decisivo"]}


# --- Nenhum número publicado muda ------------------------------------------------

def test_a_soma_das_barras_e_a_chance_final_menos_a_inicial():
    payloads = _payloads()
    if not payloads:
        pytest.skip("sem o processado")
    for nome, d in payloads:
        curva = d["win_probability"]["curve"]
        soma = sum(variacao(c) for c in curva)
        assert math.isclose(soma, curva[-1]["wp_a_depois"] - curva[0]["wp_a_antes"], abs_tol=1e-9), nome
        # a curva é contínua: o "antes" de um round é o "depois" do anterior, e o primeiro antes é o 0-0
        for ant, atual in zip(curva, curva[1:]):
            assert math.isclose(atual["wp_a_antes"], ant["wp_a_depois"], abs_tol=1e-12), (nome, atual["round"])
        assert curva[0]["wp_a_antes"] == 0.5, nome


def test_a_barra_e_a_variacao_ja_publicada():
    for nome, d in _payloads() or [("sintética", _payload("AABABBAAB"))]:
        for c in d["win_probability"]["curve"]:
            assert math.isclose(variacao(c), c["wpa_a"], abs_tol=1e-12), (nome, c["round"])


def test_o_bloco_da_pagina_so_tem_texto():
    """Só texto: a impressão dos números (scripts/design/impressao_numeros.py) não ganha linha."""
    b = bloco(_payload("AABABBAABBAABAB"), NOMES)

    def folhas(v):
        if isinstance(v, dict):
            for x in v.values():
                yield from folhas(x)
        elif isinstance(v, list):
            for x in v:
                yield from folhas(x)
        else:
            yield v
    assert all(isinstance(x, str) for x in folhas(b))


# --- Os textos --------------------------------------------------------------------

def test_format_pp_tem_sinal_e_menos_tipografico():
    assert format_pp(0.25) == "+25 pp"
    assert format_pp(-0.188) == "−19 pp"
    assert format_pp(0.004) == "+0,4 pp"
    assert format_pp(0) == "0 pp"


def test_rotulos_cartoes_e_placares_saem_da_curva():
    p = _payload("AABAB")
    b = bloco(p, NOMES)
    curva = p["win_probability"]["curve"]
    assert len(b["rotulos"]) == len(b["frases"]) == len(b["placares"]) == len(curva)
    assert b["rotulos"][2] == format_pp(variacao(curva[2])) and b["rotulos"][2].startswith("−")
    assert b["placares"][2].replace("⁠", "") == "2–0 → 2–1"
    assert placar_antes_e_depois(curva[0])[0].replace("⁠", "") == "0–0"
    assert len(b["cartoes"]) == len(p["win_probability"]["top"])
    for t, c in zip(p["win_probability"]["top"], b["cartoes"]):
        assert c["cabecalho"].startswith(f"Round {t['round']} · ")
        assert NOMES[t["winner_team"]] + " venceu o round" in c["variacao"]
    assert "Time A" not in json.dumps(b, ensure_ascii=False)


def test_a_abertura_cita_dois_rounds_da_partida_e_nao_fala_de_inclinacao():
    p = _payload("AAAAAAAABBBBABAB")
    b = bloco(p, NOMES)
    curva = p["win_probability"]["curve"]
    menor = min(curva, key=lambda c: (abs(variacao(c)), c["round"]))
    maior = min(curva, key=lambda c: (-abs(variacao(c)), c["round"]))
    assert f"o round {menor['round']}, no " in b["abertura"] and f"o round {maior['round']}, no " in b["abertura"]
    assert format_pp(abs(variacao(maior))).lstrip("+") in b["abertura"]
    assert "inclina" not in b["abertura"] + b["nota"]


def test_a_nota_usa_o_decisivo_publicado_e_explica_o_empate():
    # 11-11 -> 12-11 e 12-11 -> 13-11 mexem o mesmo tanto (25 pp): o decisivo é o primeiro
    vencedores = "AB" * 11 + "AA"
    p = _payload(vencedores)
    rd = p["decisive_round"]["round"]
    assert rd == 23
    nota = bloco(p, NOMES)["nota"]
    assert "Os rounds 23 e 24 mexeram o mesmo tanto (25 pp)" in nota and "o round 23." in nota


def test_a_nota_sem_round_decisivo_diz_a_maior_barra_e_o_minimo():
    p = _payload("A" * 13)
    assert p["decisive_round"] is None
    nota = bloco(p, NOMES)["nota"]
    maior = p["win_probability"]["top"][0]
    assert f"a do round {maior['round']}" in nota and "não tem round decisivo" in nota


def test_no_corpus_a_nota_cita_o_round_decisivo_publicado():
    payloads = _payloads()
    if not payloads:
        pytest.skip("sem o processado")
    for nome, d in payloads:
        b = bloco(d, NOMES)
        dec = d.get("decisive_round")
        if dec is None:
            assert "não tem round decisivo" in b["nota"], nome
        else:
            assert re.search(rf"\b{dec['round']}\b", b["nota"]), nome
            # e o decisivo é a maior barra (ou empata com ela): ninguém o elege de novo aqui
            maior = max(abs(variacao(c)) for c in d["win_probability"]["curve"])
            assert math.isclose(abs(dec["wpa_a"]), maior, abs_tol=1e-12), nome


# --- A página ---------------------------------------------------------------------

def _placar_do_template() -> str:
    return TEMPLATE[TEMPLATE.index('data-panel="rounds"'):TEMPLATE.index('data-panel="jogadores"')]


def test_o_template_nao_tem_texto_fixo_da_secao_nem_a_frase_da_inclinacao():
    placar = _placar_do_template()
    assert "inclinação" not in placar and "A chance de vitória, round a round" not in placar
    assert '<h3 class="sec" id="peso-titulo" style="font-size:20px;margin-top:30px"></h3>' in placar
    assert '<p class="lead" id="peso-abertura"></p>' in placar
    assert 'id="peso-tabela"' in placar and 'id="peso-cartoes"' in placar


def _funcao_do_grafico() -> str:
    ini = TEMPLATE.index("(function pesoDosRounds() {")
    return TEMPLATE[ini:TEMPLATE.index("  })();", ini)]


def test_o_grafico_usa_so_os_tokens_de_hoje_e_eles_passam_no_validador():
    js = _funcao_do_grafico()
    assert not re.search(r"#[0-9a-fA-F]{3,6}\b", js), "cor escrita à mão no gráfico"
    usados = set(re.findall(r"\bC\.(\w+)", js))
    assert usados <= {"ct", "tr", "decisivo", "tinta2", "apagado", "borda", "linha", "fNum", "fTexto"}, usados
    assert set(re.findall(r"var\(--([\w-]+)\)", js)) <= {"ct", "tr", "decisivo", "apagado"}
    tk = le_tokens()
    # marcas (barras, contorno do decisivo) >= 3:1 e rótulos >= 4,5:1 contra o card (--superficie)
    for marca in ("ct", "tr", "decisivo"):
        assert contraste(tk[marca], tk["superficie"]) >= 3.0, marca
    for texto in ("tinta-2", "apagado", "decisivo"):
        assert contraste(tk[texto], tk["superficie"]) >= 4.5, texto


# --- No navegador -----------------------------------------------------------------

sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_annotations_browser import navegador  # noqa: E402,F401  (fixture)


def _pagina(tmp_path, match_id: str) -> Path:
    if not (PROCESSED / match_id / "web_payload.json").exists():
        pytest.skip(f"sem o processado da {match_id}")
    from scripts.build_web_page import build_html
    html = tmp_path / f"{match_id}.html"
    html.write_text(build_html(match_id), encoding="utf-8")
    return html


def _abre_placar(navegador, html: Path, largura: int, movimento: str = "no-preference"):
    ctx = navegador.new_context(viewport={"width": largura, "height": 900}, reduced_motion=movimento)
    pg = ctx.new_page()
    erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto(html.as_uri())
    pg.click('[data-tab="rounds"]')
    pg.wait_for_timeout(150)
    assert not erros, erros
    return ctx, pg


CAIXAS = """() => [...document.querySelectorAll('#wpchart .pesobar')].map(b => {
  const r = b.getBoundingClientRect(); return {w: r.width, h: r.height, v: +b.dataset.variacao}; })"""
ROTULOS = """() => { const g = document.querySelector('#wpchart .peso-rotulos');
  if (!g || getComputedStyle(g).display === 'none') return [];
  return [...g.querySelectorAll('text')].map(t => { const r = t.getBoundingClientRect();
    return {x0: r.left, x1: r.right, y0: r.top, y1: r.bottom, t: t.textContent}; }); }"""


def _sem_sobreposicao(caixas: list[dict]) -> bool:
    return not any(a["x0"] < b["x1"] and b["x0"] < a["x1"] and a["y0"] < b["y1"] and b["y0"] < a["y1"]
                   for i, a in enumerate(caixas) for b in caixas[i + 1:])


def test_30_rounds_com_prorrogacao_em_375_px_nenhuma_barra_some_e_nada_rola_de_lado(navegador, tmp_path):
    html = _pagina(tmp_path, "match_37")          # Spirit 16 × 14 Natus Vincere: 30 rounds, com prorrogação
    ctx, pg = _abre_placar(navegador, html, 375)
    try:
        assert pg.evaluate("document.documentElement.scrollWidth") <= 375
        barras = pg.evaluate(CAIXAS)
        curva = json.loads((PROCESSED / "match_37" / "web_payload.json").read_text(encoding="utf-8"))["win_probability"]["curve"]
        assert len(barras) == len(curva) == 30
        assert all(b["w"] >= 1 and b["h"] >= 1 for b in barras), barras
        # a soma do que está desenhado é a chance final menos a inicial
        assert math.isclose(sum(b["v"] for b in barras), curva[-1]["wp_a_depois"] - curva[0]["wp_a_antes"], abs_tol=1e-9)
        assert _sem_sobreposicao(pg.evaluate(ROTULOS))
        assert pg.locator("#peso-tabela tbody tr").count() == 30
        assert pg.locator("#peso-cartoes .peso-cartao").count() == 3
    finally:
        ctx.close()


def test_em_1440_px_os_tres_maiores_tem_rotulo_sem_sobrepor(navegador, tmp_path):
    for match_id in ("match_39", "match_37"):
        html = _pagina(tmp_path, match_id)
        ctx, pg = _abre_placar(navegador, html, 1440)
        try:
            rot = pg.evaluate(ROTULOS)
            assert len(rot) == 3 and _sem_sobreposicao(rot), (match_id, rot)
            # a barra não tem transição (com ou sem reduzir movimento, nada anima)
            assert pg.evaluate("getComputedStyle(document.querySelector('#wpchart .pesobar')).transitionDuration") == "0s"
        finally:
            ctx.close()


def test_teclado_dica_hover_sincronizado_e_clique(navegador, tmp_path):
    html = _pagina(tmp_path, "match_39")
    d = json.loads((PROCESSED / "match_39" / "web_payload.json").read_text(encoding="utf-8"))
    rd = d["decisive_round"]["round"]
    ctx, pg = _abre_placar(navegador, html, 1440, movimento="reduce")
    try:
        alvos = pg.locator("#wpchart .pesohit")
        assert alvos.count() == len(d["win_probability"]["curve"])
        assert all(alvos.nth(i).get_attribute("tabindex") == "0" for i in range(alvos.count()))
        i = rd - 1
        # foco pelo teclado: a dica aparece, com o mesmo conteúdo do gráfico de cima e a variação
        alvos.nth(i).focus()
        dica = pg.locator("#wpchart ~ .rtip")
        assert dica.is_visible()
        texto = dica.text_content()
        assert f"Round {rd}" in texto and "+25 pp" in texto and "clique para assistir" in texto
        assert "Round decisivo" in alvos.nth(i).get_attribute("aria-label")
        # o mesmo round acende no gráfico de cima
        assert pg.evaluate(f"document.querySelectorAll('#swing .swingdot')[{i}].classList.contains('hot')")
        alvos.nth(i).blur()
        assert not pg.evaluate(f"document.querySelectorAll('#swing .swingdot')[{i}].classList.contains('hot')")
        # e o contrário: o mouse no gráfico de cima acende a barra
        pg.locator(f'#swing .swinghit[aria-label="Round {rd}: assistir"]').hover()
        assert pg.evaluate(f"document.querySelector('#wpchart .pesobar[data-round=\"{rd}\"]').classList.contains('hot')")
        # com reduzir movimento, nada anima
        # (a regra global de reduzir movimento põe 0,01 ms em toda transição da página: nada se vê animar)
        duracoes = pg.evaluate("document.getAnimations().filter(a => a.effect && a.effect.target && "
                               "a.effect.target.closest && a.effect.target.closest('#wpchart, #peso-cartoes'))"
                               ".map(a => a.effect.getTiming().duration)")
        assert all(d <= 0.01 for d in duracoes), duracoes
        # o cartão do decisivo leva a marca, e "Assistir no mapa" abre o round no replay
        primeiro = pg.locator("#peso-cartoes .peso-cartao").first
        assert "decisivo" in primeiro.inner_text()
        primeiro.locator(".pc-ir").click()
        assert pg.locator('[data-tab="replay"]').get_attribute("aria-selected") == "true"
    finally:
        ctx.close()
