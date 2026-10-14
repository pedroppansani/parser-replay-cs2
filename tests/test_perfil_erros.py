"""A aba Perfil nova (fase 12): o bloco do Python, a publicação só dos tipos validados, os chips de
round que abrem o Replay no round e no tempo, a comparação só com jogadores da partida e o endereço
`#replay?round=&t=` (pedido 12.6, itens 5 a 8)."""
from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest

from leitura import perfil_erros as PE
from metrics import erros as E

RAIZ = Path(__file__).resolve().parent.parent
PARTIDA = "match_47"


def _base() -> Path:
    base = RAIZ / "data" / "processed" / PARTIDA
    if not (base / E.ARQUIVO).exists() or not (base / "web_payload.json").exists():
        pytest.skip("sem as ocorrências gravadas da partida")
    return base


def _bloco(**kw) -> dict:
    from scripts.build_web_page import cabecalho_da_partida
    base = _base()
    payload = json.loads((base / "web_payload.json").read_text(encoding="utf-8"))
    return PE.bloco_da_partida(base, payload, cabecalho_da_partida(PARTIDA, base), **kw)


# --- O bloco do Python --------------------------------------------------------------------------------

def test_sem_tipo_validado_nenhum_erro_vai_para_o_bloco():
    b = _bloco()
    assert b["estado"] == "em_validacao" and b["tipos"] == []
    assert all(j["melhorar"] == [] and j["uma_vez"] == [] and j["contagens"] == {} for j in b["jogadores"])
    assert b["textos"]["em_validacao"] == "Em validação: os tipos de erro aparecem depois de conferidos"
    assert b["link_como_e_conferido"].endswith("MATERIAL_DE_CALIBRACAO.md#7-erros-na-aba-perfil")


def test_com_um_tipo_validado_so_ele_aparece():
    b = _bloco(validados={E.NAO_TROCOU})
    assert [t["id"] for t in b["tipos"]] == [E.NAO_TROCOU]
    tipos = {m["tipo"] for j in b["jogadores"] for m in j["melhorar"]}
    assert tipos == {E.NAO_TROCOU}
    assert all(not m["em_validacao"] for j in b["jogadores"] for m in j["melhorar"])


def test_a_previa_mostra_todos_os_tipos_em_validacao_e_no_maximo_tres():
    b = _bloco(preview=True)
    assert b["estado"] == "preview" and [t["id"] for t in b["tipos"]] == list(E.TIPOS)
    for j in b["jogadores"]:
        assert len(j["melhorar"]) <= E.MAX_PONTOS_A_MELHORAR and len(j["fortes"]) <= E.MAX_PONTOS_FORTES
        niveis = [m["nivel"] for m in j["melhorar"]]
        assert niveis == sorted(niveis, key=lambda n: n != E.EXPLICITO)        # explícitos antes
        for m in j["melhorar"]:
            assert m["em_validacao"]
            assert len(m["chips"]) >= E.MIN_OCORRENCIAS_PARA_PONTO
            if m["nivel"] == E.EXPLICITO:
                assert m["frase"] == E.COMO_MELHORAR[m["tipo"]]
            else:
                assert m["frase"].endswith(E.CONFERIR_COM_O_TIME)
            assert m["custo"] == "" or "pela estimativa do modelo" in m["custo"] or m["custo"].startswith("sem custo")
        for u in j["uma_vez"]:
            # Detalhes agora tem dois motivos (fase 12b): uma vez só, ou dentro do normal da referência
            if u["contagem"].startswith("1 vez"):
                assert u["motivo"] == PE.TEXTOS["uma_vez"]
            else:
                assert u["motivo"].startswith("dentro do normal para")


def test_o_jogador_aberto_por_padrao_e_o_de_maior_rating():
    base = _base()
    payload = json.loads((base / "web_payload.json").read_text(encoding="utf-8"))
    maior = sorted(payload["players"], key=lambda p: (-(p.get("rating") or 0), p["name"].lower()))[0]["name"]
    assert _bloco()["padrao"] == maior


def test_o_custo_e_a_soma_das_quedas_em_pontos():
    assert PE._custo([-0.031, -0.02])[1] == "custou cerca de 5 pontos de chance de vitória, pela estimativa do modelo"
    assert PE._custo([-0.004])[1].startswith("custou menos de 1 ponto")
    assert PE._custo([None])[1].startswith("sem custo estimado")


def test_ponto_depende_da_tatica_usa_o_motivo_como_frase():
    oc = [{"nivel": E.DEPENDE, "motivo": E.MOTIVO_LURKER, "dwpa": -0.01, "round_num": r, "tick": 10 * r,
           "segundos": 12.0} for r in (3, 7)]
    m = PE._ponto_a_melhorar(E.MORREU_ISOLADO, oc, 24, None, "lurker", False)
    assert m["frase"] == "Jogar longe do time é a função do lurker. " + E.CONFERIR_COM_O_TIME
    assert m["nivel_rotulo"] == "depende da tática" and m["contagem"] == "2 vezes em 24 rounds"
    assert [c["round"] for c in m["chips"]] == [3, 7] and m["chips"][0]["t"] == 12.0


def test_todo_chip_da_pagina_tem_lado_e_relogio_e_leva_ao_round_e_ao_momento():
    # fase 15: todo erro é de um lado só e o chip diz o round e o relógio ("R12 · 1:14")
    bloco = _bloco(preview=True)
    n = 0
    for j in bloco["jogadores"]:
        for m in j["melhorar"]:
            chips = list(m["chips"])
            assert all(c["lado"] == m["lado"] for c in chips)          # o chip é do lado do card
            for c in chips:
                n += 1
                assert c["lado"] in ("ct", "t") and c["lado_rotulo"] in ("no CT", "no TR")
                assert c["relogio"] and c["texto"] == f"R{c['round']} · {c['relogio']}"
                assert c["t"] is not None
                assert c["titulo"].startswith(f"Round {c['round']}, {c['relogio']}: abre o Replay")
        for u in j["uma_vez"]:
            for c in u["chips"]:
                n += 1
                assert c["lado"] in ("ct", "t") and c["relogio"]
    assert n > 0


def test_o_relogio_do_chip_e_o_do_replay():
    # 12,0 s depois do freeze, sem plant: 1:55 - 12 s = 1:43
    oc = [{"nivel": E.DEPENDE, "motivo": E.MOTIVO_LURKER, "dwpa": None, "round_num": 3, "tick": 30, "segundos": 12.0,
           "side": "t", "relogio": "1:43"}]
    c = PE._chips(oc)[0]
    assert (c["rotulo"], c["texto"], c["lado"]) == ("R3", "R3 · 1:43", "t")
    sem = [{**oc[0], "relogio": None}]
    assert PE._chips(sem)[0]["relogio"] == "1:43"


# --- Publicação no site ------------------------------------------------------------------------------

def test_com_a_lista_vazia_nenhum_tipo_aparece_na_pagina_e_com_um_so_ele(monkeypatch):
    from scripts.build_web_page import build_html
    _base()
    titulos = list(E.TITULOS.values())
    html = build_html(PARTIDA)
    assert not any(t in html for t in titulos), [t for t in titulos if t in html]
    monkeypatch.setattr(E, "TIPOS_DE_ERRO_VALIDADOS", frozenset({E.PERDEU_A_TROCA}))
    html = build_html(PARTIDA)
    assert E.TITULOS[E.PERDEU_A_TROCA] in html
    assert not any(t in html for t in titulos if t != E.TITULOS[E.PERDEU_A_TROCA])


def test_docs_publicado_nao_tem_tipo_de_erro():
    paginas = sorted((RAIZ / "docs").glob("match_*.html"))
    if not paginas:
        pytest.skip("sem docs/ gerado")
    for p in paginas:
        texto = p.read_text(encoding="utf-8")
        assert not any(t in texto for t in E.TITULOS.values()), p.name


# --- No navegador --------------------------------------------------------------------------------------

from tests.test_annotations_browser import navegador  # noqa: E402,F401  (fixture)


@pytest.fixture(scope="module")
def previa(tmp_path_factory):
    from scripts.build_web_page import build_html
    _base()
    html = tmp_path_factory.mktemp("perfil") / f"{PARTIDA}.html"
    html.write_text(build_html(PARTIDA, preview=True), encoding="utf-8")
    return html


def _abre(navegador, html: Path, hash_: str = "#perfil", largura: int = 1300):
    ctx = navegador.new_context(viewport={"width": largura, "height": 900})
    pg = ctx.new_page()
    erros: list = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto(html.as_uri() + hash_)
    pg.wait_for_selector("#pf-cab .nk")
    pg._erros = erros
    return ctx, pg


def _com_chip(pg):
    """Abre um jogador da prévia que tenha chip (com o p90, o jogador aberto por padrão pode não ter ponto)."""
    for nome in pg.eval_on_selector_all("#pf-botoes button", "bs => bs.map(b => b.dataset.nome)"):
        pg.locator("#pf-botoes button", has_text=nome).first.click()
        if pg.locator("#pf-melhorar .pfchip").count():
            return nome
    pytest.skip("nenhum jogador com chip na partida")


def test_os_chips_abrem_o_replay_no_round_e_no_tempo(navegador, previa):
    ctx, pg = _abre(navegador, previa)
    try:
        _com_chip(pg)
        chip = pg.locator("#pf-melhorar .pfchip").first
        rnd, t = int(chip.get_attribute("data-round")), float(chip.get_attribute("data-t"))
        chip.click()
        assert pg.get_attribute('[data-tab="replay"]', "aria-selected") == "true"
        assert pg.inner_text("#rh-round") == f"Round {rnd}"
        hz = pg.evaluate("() => JSON.parse(document.getElementById('replay').textContent).sample_hz")
        assert int(pg.input_value("#scrub")) == int(max(0.0, t - 3) * hz)       # 3 s antes, como os eventos
        assert pg.url.endswith(f"#replay?round={rnd}&t={t:g}")
        assert pg._erros == []
    finally:
        ctx.close()


def test_o_endereco_com_round_e_tempo_abre_o_replay(navegador, previa):
    ctx = navegador.new_context(viewport={"width": 1300, "height": 900})
    pg = ctx.new_page()
    try:
        pg.goto(previa.as_uri() + "#replay?round=3&t=20")
        pg.wait_for_timeout(300)
        assert pg.get_attribute('[data-tab="replay"]', "aria-selected") == "true"
        assert pg.inner_text("#rh-round") == "Round 3"
        hz = pg.evaluate("() => JSON.parse(document.getElementById('replay').textContent).sample_hz")
        assert int(pg.input_value("#scrub")) == int(17 * hz)
    finally:
        ctx.close()


def test_a_comparacao_so_oferece_jogadores_desta_partida(navegador, previa):
    ctx, pg = _abre(navegador, previa)
    try:
        nomes = pg.evaluate("() => JSON.parse(document.getElementById('payload').textContent).player_profile.map(p => p.name)")
        escolhido = pg.inner_text("#pf-cab .nk")
        opcoes = pg.eval_on_selector_all("#pf-b option", "os => os.map(o => o.value).filter(Boolean)")
        assert sorted(opcoes) == sorted(n for n in nomes if n != escolhido) and len(opcoes) == 9
        pg.select_option("#pf-b", opcoes[0])
        tabela = pg.inner_text("#pf-cmp")
        assert escolhido in tabela and opcoes[0] in tabela
        assert pg.locator("#pf-cmp svg, #pf-cmp canvas, #pf-cmp .pfbarra").count() == 0   # sem faixa nem radar
        # trocar de jogador tira ele mesmo da lista
        pg.locator("#pf-botoes button", has_text=opcoes[1]).first.click()
        assert opcoes[1] not in pg.eval_on_selector_all("#pf-b option", "os => os.map(o => o.value)")
        assert pg._erros == []
    finally:
        ctx.close()


def test_sem_tipo_validado_a_secao_diz_em_validacao_e_detalhes_fecha(navegador, tmp_path):
    from scripts.build_web_page import build_html
    _base()
    html = tmp_path / f"{PARTIDA}.html"
    html.write_text(build_html(PARTIDA), encoding="utf-8")
    ctx, pg = _abre(navegador, html, largura=375)
    try:
        assert "Em validação: os tipos de erro aparecem depois de conferidos" in pg.inner_text("#pf-melhorar")
        assert pg.locator("#pf-em-validacao a").get_attribute("href").endswith("#7-erros-na-aba-perfil")
        assert pg.locator("#pf-melhorar .ponto").count() == 0
        assert not pg.eval_on_selector("#pf-detalhes", "d => d.open")
        # a explicação nunca usa as cores de erro e de aviso para o jogador
        cores = pg.eval_on_selector_all("#pf-melhorar *, #pf-fortes *, #pf-cab *",
                                        "els => els.map(e => getComputedStyle(e).color)")
        raiz = pg.evaluate("() => { const s = getComputedStyle(document.documentElement); "
                           "return [s.getPropertyValue('--erro').trim(), s.getPropertyValue('--aviso').trim()]; }")
        assert raiz == ["#ff6b6b", "#ffea3d"]
        assert "rgb(255, 107, 107)" not in cores and "rgb(255, 234, 61)" not in cores
        assert pg.evaluate("() => document.documentElement.scrollWidth") <= 375       # uma coluna, sem rolar
        assert pg._erros == []
    finally:
        ctx.close()


# --- Fase 15 (§19): a forma dos cards, dos chips e do bloco Detalhes ---------------------------------------

def _com_dois_niveis(pg):
    """Abre um jogador da prévia que tenha ponto explícito e ponto depende da tática."""
    for nome in pg.eval_on_selector_all("#pf-botoes button", "bs => bs.map(b => b.dataset.nome)"):
        pg.locator("#pf-botoes button", has_text=nome).first.click()
        if pg.locator(".ponto.explicito").count() and pg.locator(".ponto.depende:not(.compacto)").count():
            return nome
    pytest.skip("nenhum jogador com os dois níveis na partida")


def test_explicito_nao_e_verde_e_vem_antes_do_depende(navegador, previa):
    ctx, pg = _abre(navegador, previa)
    try:
        _com_dois_niveis(pg)
        assert pg.locator(".ponto.melhorar .tag.decisivo").count() == 0       # decisão 46 (fase 15): o verde não marca erro
        niveis = pg.eval_on_selector_all(".ponto.melhorar", "ps => ps.map(p => p.classList.contains('explicito'))")
        assert niveis == sorted(niveis, reverse=True)                          # explícitos primeiro
        assert pg.locator(".ponto.explicito .tag.explicito").count() == pg.locator(".ponto.explicito").count()
        # nenhuma cor de sistema no card de erro (--erro, --aviso)
        cores = pg.evaluate("""() => { const v = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
            return [v('--erro'), v('--aviso')]; }""")
        usadas = pg.evaluate("""() => [...document.querySelectorAll('.ponto.melhorar, .ponto.melhorar *')].flatMap(e => {
            const c = getComputedStyle(e); return [c.color, c.borderTopColor, c.borderLeftColor, c.backgroundColor]; })""")
        def rgb(h): return "rgb(%d, %d, %d)" % (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16))
        assert not any(rgb(c) in usadas for c in cores)
    finally:
        ctx.close()


def test_chip_mostra_round_e_relogio_e_marca_visitado(navegador, previa):
    ctx, pg = _abre(navegador, previa, largura=375)
    try:
        _com_dois_niveis(pg)
        chip = pg.locator("#pf-melhorar .pfchip").first
        n, h = chip.locator(".n").inner_text(), chip.locator(".h").inner_text()
        assert n.startswith("R") and ":" in h
        assert f"{n[1:]}, {h}" in chip.get_attribute("aria-label")
        box = chip.bounding_box()
        assert box["height"] >= 44 and box["width"] >= 44
        assert chip.get_attribute("data-visitado") is None
        chip.click()
        pg.click('[data-tab="perfil"]')
        assert pg.locator("#pf-melhorar .pfchip").first.get_attribute("data-visitado") is not None
        assert "(já aberto)" in pg.locator("#pf-melhorar .pfchip").first.get_attribute("aria-label")
    finally:
        ctx.close()


def test_detalhes_fecha_por_padrao_lembra_e_nao_estoura_375(navegador, previa):
    ctx, pg = _abre(navegador, previa, largura=375)
    try:
        assert pg.evaluate("() => document.getElementById('pf-detalhes').open") is False
        assert pg.locator("#pf-detalhes .g-resumo").is_visible()
        pg.locator("#pf-detalhes > summary").click()
        assert not pg.locator("#pf-detalhes .g-resumo").is_visible()           # a linha de resumo some ao abrir
        assert pg.evaluate("() => document.documentElement.scrollWidth") <= 375
        assert pg.evaluate("() => localStorage.getItem('parser-cs2:perfil-detalhes')") == "1"
    finally:
        ctx.close()
