"""RS2: o Round swing na página da partida. A coluna "Round swing (p.p.)" da tabela de jogadores (depois do Rating, com a frase e o aviso na legenda) e a linha do Perfil
(menos de 30 rounds: o motivo, sem número; 30 a 99: número com "±"; 100 ou mais: com "±" e "estável"; também para o jogador do "Comparar com").
O número da tabela é o do `insights.json`; o leitor de tela lê por extenso ("mais"/"menos"); o CLS é 0; a página Jogadores não ganha o número."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from leitura.round_swing_texto import MENOS, TEXTOS, da_partida, do_corpus, estado, leitor, numero

RAIZ = Path(__file__).resolve().parent.parent
AGG = RAIZ / "data" / "player_profiles" / "round_swing.json"


# --- os textos (Python puro) ------------------------------------------------------------------------------------------------------

def test_o_sinal_vem_sempre_escrito_com_o_menos_tipografico():
    assert numero(5.84) == "+5,8" and numero(-2.14) == MENOS + "2,1" and MENOS == "−"
    assert numero(0.0) == "0,0" and numero(-0.04) == "0,0" and numero(0.04) == "0,0"       # o que arredonda para zero não tem sinal
    assert "-" not in numero(-3.3)                                                          # nunca o hífen


def test_o_leitor_de_tela_le_por_extenso_com_mais_e_menos():
    assert leitor(5.84, 1.2) == "mais 5,8 pontos percentuais por round, mais ou menos 1,2"
    assert leitor(-2.14) == "menos 2,1 pontos percentuais por round"
    assert leitor(0.0) == "zero pontos percentuais por round"
    assert "+" not in leitor(5.0) and MENOS not in leitor(-5.0)


@pytest.mark.parametrize("n,esperado", [(0, "poucos"), (24, "poucos"), (29, "poucos"), (30, "intermediario"), (99, "intermediario"), (100, "estavel"), (447, "estavel")])
def test_os_tres_estados_do_perfil_pelo_numero_de_rounds(n, esperado):
    assert estado(n) == esperado


def _bloco(rounds, pp=5.76, erro=1.2, partidas=3):
    return {"rounds": rounds, "pp_por_round": pp, "erro_padrao_pp": erro, "partidas": partidas}


def test_menos_de_30_rounds_escreve_o_motivo_e_nao_mostra_o_numero():
    c = do_corpus(_bloco(24, partidas=1))
    assert c["estado"] == "poucos" and c["numero"] == ""
    assert c["motivo"] == "poucos rounds para um número confiável (24 de 30)"
    assert "5,8" not in c["l"] and "±" not in c["numero"]


def test_de_30_a_99_tem_numero_com_mais_ou_menos_e_so_com_100_e_estavel():
    meio = do_corpus(_bloco(78, -2.0, 2.1, 4))
    assert meio["estado"] == "intermediario" and meio["numero"] == MENOS + "2,0 ± 2,1" and meio["contagem"] == "4 partidas, 78 rounds"
    assert "estável" not in meio["l"]
    est = do_corpus(_bloco(447, 5.76, 1.2, 21))
    assert est["estado"] == "estavel" and est["numero"] == "+5,8 ± 1,2" and est["l"].endswith("; estável")
    assert est["l"].startswith(f"{TEXTOS['titulo_do_perfil']}: mais 5,8 pontos percentuais por round, mais ou menos 1,2")


def test_a_celula_da_partida_e_o_numero_do_insights():
    assert da_partida({"pp_por_round": -3.7}) == {"t": MENOS + "3,7", "l": "menos 3,7 pontos percentuais por round"}
    assert da_partida(None) is None and da_partida({"pp_por_round": None}) is None


def test_as_frases_decididas_estao_no_texto():
    assert TEXTOS["frase"] == "Round swing: quanto o jogador mexeu, por round, na chance de o time vencer o round; implementação própria, o número pode diferir do da HLTV."
    assert TEXTOS["aviso_partida"] == "Numa partida, o round swing varia cerca de ±4 p.p. só por acaso: ele conta o que aconteceu, não quem é melhor."
    assert TEXTOS["selo"] == "implementação própria" and TEXTOS["coluna"] == "Round swing (p.p.)"


def test_a_pagina_jogadores_nao_ganha_o_round_swing():
    """Fora desta fase: nem coluna nem ordenação na página Jogadores (72 de 116 jogadores sem número estável induziriam a erro)."""
    for arq in ("metrics/agregado_jogadores.py", "scripts/build_jogadores.py"):
        assert "round_swing" not in (RAIZ / arq).read_text(encoding="utf-8").lower()


# --- a página (navegador) --------------------------------------------------------------------------------------------------------

sync_api = pytest.importorskip("playwright.sync_api")
from tests.test_tactics_browser import navegador  # noqa: E402,F401  (fixture)

OBS = "window.__cls = 0; new PerformanceObserver(l => { for (const e of l.getEntries()) if (!e.hadRecentInput) window.__cls += e.value; }).observe({type: 'layout-shift'});"
TELAS = {"1440x900": (1440, 900), "1366x657": (1366, 657), "375": (375, 812)}


def _agregado():
    if not AGG.exists():
        pytest.skip("sem o agregado do round swing (rode o reprocessa)")
    return json.loads(AGG.read_text(encoding="utf-8"))["jogadores"]


def _insights(m):
    return json.loads((RAIZ / "data" / "processed" / m / "insights.json").read_text(encoding="utf-8"))


def _jogador_no_estado(partida, est):
    agg = _agregado()
    for p in sorted(_insights(partida)["players"], key=lambda p: p["name"].lower()):
        b = agg[str(p["steamid"])]
        if estado(b["rounds"]) == est:
            return p["name"]
    pytest.skip(f"{partida}: ninguém no estado {est}")


@pytest.fixture(scope="module")
def paginas(tmp_path_factory):
    from scripts.build_web_page import build_html
    pasta = tmp_path_factory.mktemp("rs2")
    out = {}
    for m in ("match_09", "match_21", "match_23"):
        if not (RAIZ / "data" / "processed" / m / "web_payload.json").exists():
            pytest.skip("sem o processado")
        (pasta / f"{m}.html").write_text(build_html(m), encoding="utf-8")
        out[m] = pasta / f"{m}.html"
    return out


def _abre(navegador, arq, aba, w=1440, h=900):
    ctx = navegador.new_context(viewport={"width": w, "height": h})
    ctx.add_init_script(OBS)
    pg = ctx.new_page(); erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto(arq.as_uri()); pg.wait_for_timeout(300)
    pg.locator(f'[data-tab="{aba}"]').first.click(); pg.wait_for_timeout(250)
    return ctx, pg, erros


def test_a_coluna_vem_depois_do_rating_e_a_legenda_tem_a_frase_o_pp_e_o_aviso(navegador, paginas):
    ctx, pg, erros = _abre(navegador, paginas["match_21"], "jogadores")
    try:
        cab = [t.strip() for t in pg.locator("#players thead th").all_inner_texts()]
        assert cab[1].lower().startswith("rating") and cab[2].lower() == "round swing (p.p.)", cab     # o CSS põe em maiúsculas
        legenda = pg.inner_text("#legenda-swing")
        assert TEXTOS["frase"] in legenda and "p.p. = pontos percentuais" in legenda and TEXTOS["aviso_partida"] in legenda
        assert pg.locator("#players-legenda").inner_text().count("p.p. = pontos percentuais") == 1         # "p.p." é explicado uma vez só
        assert erros == []
    finally:
        ctx.close()


def test_o_numero_da_tabela_e_o_do_insights_e_o_leitor_le_por_extenso(navegador, paginas):
    ins = {p["name"]: p["round_swing"]["pp_por_round"] for p in _insights("match_21")["players"]}
    ctx, pg, _ = _abre(navegador, paginas["match_21"], "jogadores")
    try:
        linhas = pg.locator("#players tbody tr")
        assert linhas.count() == 10
        for i in range(10):
            nome = linhas.nth(i).locator("th .nk").inner_text().strip()
            visivel = linhas.nth(i).locator("td.rswing [aria-hidden]").inner_text()
            lido = linhas.nth(i).locator("td.rswing .so-leitor").inner_text()
            assert visivel == numero(ins[nome]), (nome, visivel, ins[nome])
            assert re.fullmatch(r"(mais|menos) \d+,\d pontos percentuais por round|zero pontos percentuais por round", lido), lido
            assert visivel[0] in ("+", MENOS, "0")                                    # o sinal escrito, não só a cor
    finally:
        ctx.close()


@pytest.mark.parametrize("partida,est", [("match_09", "poucos"), ("match_21", "intermediario"), ("match_23", "estavel")])
def test_os_tres_estados_do_perfil_na_tela(navegador, paginas, partida, est):
    nome = _jogador_no_estado(partida, est)
    ctx, pg, erros = _abre(navegador, paginas[partida], "perfil")
    try:
        pg.locator(f'#pf-botoes button[data-nome="{nome}"]').click(); pg.wait_for_timeout(200)
        linha = pg.locator("#pf-cab .pf-swing").first
        assert linha.get_attribute("data-estado") == est
        visivel = linha.locator("[aria-hidden]").inner_text()
        lido = linha.locator(".so-leitor").inner_text()
        assert "implementação própria" in visivel
        if est == "poucos":
            assert re.search(r"poucos rounds para um número confiável \(\d+ de 30\)", visivel) and "±" not in visivel and not re.search(r"[+−]\d", visivel)
        else:
            assert re.search(r"[+−]?\d+,\d ± \d+,\d", visivel)
            assert ("estável" in visivel) == (est == "estavel")
            assert re.search(r"(mais|menos) \d+,\d pontos percentuais por round, mais ou menos \d+,\d", lido) or "zero pontos" in lido
        assert erros == []
    finally:
        ctx.close()


def test_o_jogador_comparado_ganha_a_mesma_linha(navegador, paginas):
    a, b = _jogador_no_estado("match_23", "estavel"), _jogador_no_estado("match_23", "poucos")
    ctx, pg, _ = _abre(navegador, paginas["match_23"], "perfil")
    try:
        pg.locator(f'#pf-botoes button[data-nome="{a}"]').click()
        assert pg.locator("#pf-cab .pf-swing").count() == 1
        pg.select_option("#pf-b", b); pg.wait_for_timeout(200)
        assert pg.locator("#pf-cab .pf-swing").count() == 2
        segunda = pg.locator("#pf-cab .pf-swing[data-jogador=comparado]")
        assert segunda.get_attribute("data-estado") == "poucos" and b in segunda.inner_text()
    finally:
        ctx.close()


@pytest.mark.parametrize("tam", list(TELAS))
def test_cls_zero_na_partida_e_no_perfil_e_a_pagina_nao_ganha_rolagem_lateral(navegador, paginas, tam):
    w, h = TELAS[tam]
    ctx, pg, erros = _abre(navegador, paginas["match_23"], "jogadores", w, h)
    try:
        assert pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"), "a página ganhou rolagem lateral"
        pg.locator('[data-tab="perfil"]').first.click(); pg.wait_for_timeout(300)
        pg.locator("#pf-botoes button").nth(1).click(); pg.wait_for_timeout(300)
        assert pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
        assert pg.evaluate("window.__cls") == 0
        assert erros == []
    finally:
        ctx.close()


def test_a_altura_das_linhas_da_tabela_nao_muda_com_a_coluna(navegador, paginas):
    """A linha da tabela tem o nome e o time (64 px): o número de uma linha só não a engorda."""
    ctx, pg, _ = _abre(navegador, paginas["match_21"], "jogadores", 375, 812)
    try:
        alturas = pg.evaluate("[...document.querySelectorAll('#players tbody tr')].map(r => Math.round(r.getBoundingClientRect().height))")
        assert len(set(alturas)) == 1 and alturas[0] <= 65, alturas
    finally:
        ctx.close()


# --- celular: o número embaixo do Rating, e a legenda fora da caixa que rola (ajustes da RS2) --------------------------------------------

def _estado_da_tabela(pg):
    return pg.evaluate("""() => { const vis = e => !!e && getComputedStyle(e).display !== 'none';
        return { coluna: vis(document.querySelector('#players th.col-swing')), mini: vis(document.querySelector('#players .rs-mini')) }; }""")


@pytest.mark.parametrize("largura,celular", [(375, True), (430, True), (431, False), (768, False), (1440, False)])
def test_a_coluna_troca_pelo_numero_embaixo_do_rating_ate_430_px(navegador, paginas, largura, celular):
    ctx, pg, _ = _abre(navegador, paginas["match_21"], "jogadores", largura, 900)
    try:
        assert _estado_da_tabela(pg) == {"coluna": not celular, "mini": celular}, largura
    finally:
        ctx.close()


def test_no_celular_o_numero_embaixo_do_rating_e_o_do_insights_e_o_leitor_le_o_mesmo_texto_da_coluna(navegador, paginas):
    ins = {p["name"]: p["round_swing"]["pp_por_round"] for p in _insights("match_21")["players"]}
    ctx, pg, _ = _abre(navegador, paginas["match_21"], "jogadores", 375, 812)
    ctx2, pg2, _ = _abre(navegador, paginas["match_21"], "jogadores", 1440, 900)
    try:
        for i in range(10):
            nome = pg.locator("#players tbody tr").nth(i).locator("th .nk").inner_text().strip()
            mini = pg.locator("#players tbody tr").nth(i).locator(".rs-mini")
            assert mini.locator("[aria-hidden]").inner_text() == "swing " + numero(ins[nome]), nome
            lido_celular = mini.locator(".so-leitor").inner_text()
            nome2 = pg2.locator("#players tbody tr").nth(i).locator("th .nk").inner_text().strip()
            assert nome2 == nome
            assert lido_celular == pg2.locator("#players tbody tr").nth(i).locator("td.rswing .so-leitor").inner_text()     # o mesmo texto da coluna
    finally:
        ctx.close(); ctx2.close()


def test_a_altura_da_linha_e_a_mesma_no_celular_com_o_numero_embaixo_e_no_computador(navegador, paginas):
    ctx, pg, _ = _abre(navegador, paginas["match_21"], "jogadores", 375, 812)
    ctx2, pg2, _ = _abre(navegador, paginas["match_21"], "jogadores", 1440, 900)
    js = "[...document.querySelectorAll('#players tbody tr')].map(r => Math.round(r.getBoundingClientRect().height))"
    try:
        a, b = pg.evaluate(js), pg2.evaluate(js)
        assert len(set(a)) == 1 and a == b, (a, b)                                 # 64 px nas duas telas: o "swing +9,5" cabe na altura que o time já dá
        # o número não sai da célula do Rating
        assert pg.evaluate("[...document.querySelectorAll('#players tbody tr')].every(r => { const c = r.querySelector('td.rt'), m = r.querySelector('.rs-mini'); return c.contains(m) && m.getBoundingClientRect().bottom <= r.getBoundingClientRect().bottom; })")
    finally:
        ctx.close(); ctx2.close()


@pytest.mark.parametrize("largura", [375, 1440])
def test_a_legenda_fica_fora_da_caixa_que_rola_e_inteira_com_a_tabela_rolada_ate_o_fim(navegador, paginas, largura):
    ctx, pg, _ = _abre(navegador, paginas["match_21"], "jogadores", largura, 812)
    try:
        assert pg.evaluate("!document.getElementById('players').contains(document.getElementById('players-legenda'))")
        pg.evaluate("const t = document.getElementById('players'); t.scrollLeft = t.scrollWidth")
        r = pg.evaluate("(() => { const b = document.getElementById('players-legenda').getBoundingClientRect(); return [b.left, b.right, innerWidth]; })()")
        assert r[0] >= 0 and r[1] <= r[2] + 0.5, r
        texto = pg.inner_text("#players-legenda")
        assert "Rating 3.0" in texto and TEXTOS["frase"] in texto and "Mira:" in texto
    finally:
        ctx.close()
