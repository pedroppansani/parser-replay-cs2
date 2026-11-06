"""L1 (cartões 15 e 29 da fila do Reescrever): o nome do destino de uma alternativa de granada é o nome de lugar DO MAPA mais perto do ponto de queda
(a tabela dos nomes que o mapa desenha), e na Nuke vem do andar certo (pelo Z do destino); antes vinha do `place` da demo e, na Nuke, ficava sem nome."""
from __future__ import annotations

import json
import math
import re

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_reescrever_modo import (  # noqa: E402,F401  (fixtures e ajudas)
    RAIZ, _abre, _estado, navegador, pagina)

PRONTA = "() => window.__reescrever().trocas.biblioteca === 'pronta'"


def _clica(pg, sel, nth=0):
    pg.evaluate("([s, i]) => document.querySelectorAll(s)[i].click()", [sel, nth])
    pg.wait_for_timeout(120)


def _pagina_do_mapa(tmp_path_factory, partida, mapa):
    from scripts.build_site import match_summary, times_das_partidas
    from scripts.build_tactics_page import arquivo_da_biblioteca, biblioteca_js
    from scripts.build_web_page import build_html
    if not (RAIZ / "data" / "processed" / partida / "web_payload.json").exists() or not (RAIZ / "data" / "lineups" / f"{mapa}.json").exists():
        pytest.skip("sem o processado ou a biblioteca")
    pasta = tmp_path_factory.mktemp(f"l1_{mapa}")
    arq = pasta / f"{partida}.html"
    arq.write_text(build_html(partida), encoding="utf-8")
    ids = {a["partida"] for a in json.loads((RAIZ / "data" / "lineups" / f"{mapa}.json").read_text(encoding="utf-8"))["arremessos"]}
    bib = biblioteca_js(mapa, times_das_partidas([s for s in (match_summary(i) for i in sorted(ids)) if s]))
    destino = pasta / arquivo_da_biblioteca(mapa)
    destino.parent.mkdir(exist_ok=True)
    destino.write_text(bib, encoding="utf-8")
    return arq


@pytest.fixture(scope="module")
def mirage(tmp_path_factory):
    return _pagina_do_mapa(tmp_path_factory, "match_43", "de_mirage")


@pytest.fixture(scope="module")
def nuke(tmp_path_factory):
    return _pagina_do_mapa(tmp_path_factory, "match_05", "de_nuke")


def _lugares_e_radar(pg):
    return pg.evaluate("() => ({ L: window.__RADAR__.lugares, R: { ox: window.__RADAR__.origin_x, oy: window.__RADAR__.origin_y, s: window.__RADAR__.scale_px_per_unit } })")


def _mais_perto(L, R, destino, andar):
    """O nome do lugar do mapa mais perto do ponto (de novo em Python, independente do JS): o bombsite só conta na primeira âncora (é a letra do mapa)."""
    px, py = (destino[0] - R["ox"]) * R["s"], (R["oy"] - destino[1]) * R["s"]
    melhor, dm = None, math.inf
    for ix, ancoras in L["rotulos"][andar]:
        if re.fullmatch(r"Bombsite[A-Z]", L["nomes"][ix]):
            ancoras = ancoras[:1]
        for ax, ay in ancoras:
            d = math.hypot(ax - px, ay - py)
            if d < dm:
                dm, melhor = d, L["textos"][ix]
    return melhor


def _grupos(pg, tipo, por=None):
    _clica(pg, "#rw-entrar"); _clica(pg, "#rw-ferr-granada"); pg.wait_for_function(PRONTA)
    est = _estado(pg)["trocas"]
    for i, c in enumerate(est["candidatas"]):
        if c["k"] != tipo or (por and c["by"] != por):
            continue
        _clica(pg, ".rw-gr", i)
        g = _estado(pg)["trocas"]["grupos"]
        if g:
            return g
    pytest.skip("nenhuma granada com alternativa")


def _biblioteca(mapa):
    return {a["id"]: a for a in json.loads((RAIZ / "data" / "lineups" / f"{mapa}.json").read_text(encoding="utf-8"))["arremessos"]}


def test_o_destino_da_alternativa_tem_o_nome_do_lugar_do_mapa_mais_perto_do_ponto_de_queda(navegador, mirage):
    ctx, pg, erros = _abre(navegador, mirage, 1440, 900)
    try:
        grupos = _grupos(pg, "smoke", "ZywOo")
        d = _lugares_e_radar(pg); bib = _biblioteca("de_mirage")
        for g in grupos:
            assert g["lugar"] == _mais_perto(d["L"], d["R"], bib[g["id"]]["destino"], 0), g
        assert len({g["lugar"] for g in grupos}) == len(grupos)                                 # um grupo por nome
        assert not erros
    finally:
        ctx.close()


def test_a_alternativa_perto_do_stairs_nao_e_mais_chamada_de_bombsite_a(navegador, mirage):
    """O caso do Pedro: o `place` da demo dizia "BombsiteA" para um ponto que o mapa mostra junto de STAIRS. Agora a lista só chama de BOMBSITE A o que está
    mais perto da letra A do mapa do que de qualquer outro nome."""
    ctx, pg, erros = _abre(navegador, mirage, 1440, 900)
    try:
        grupos = _grupos(pg, "smoke", "ZywOo")
        nomes = {g["lugar"] for g in grupos}
        assert "STAIRS" in nomes                                                                 # o ponto que a grade da demo chamava de BombsiteA
        d = _lugares_e_radar(pg); bib = _biblioteca("de_mirage")
        for g in grupos:
            if g["lugar"] == "BOMBSITE A":
                destino = bib[g["id"]]["destino"]
                assert _mais_perto(d["L"], d["R"], destino, 0) == "BOMBSITE A"
        assert not erros
    finally:
        ctx.close()


def test_na_nuke_o_destino_da_troca_tem_nome_e_do_andar_certo(navegador, nuke):
    ctx, pg, erros = _abre(navegador, nuke, 1440, 900, round_=2, frac=0.5)
    try:
        grupos = _grupos(pg, "smoke")
        d = _lugares_e_radar(pg); bib = _biblioteca("de_nuke")
        corte = json.loads((RAIZ / "assets" / "radars" / "de_nuke.json").read_text(encoding="utf-8"))["vertical_sections"]["lower"]["max"]    # -495: o corte dos andares
        andares = set()
        for g in grupos:
            destino = bib[g["id"]]["destino"]
            andar = 1 if destino[2] < corte else 0
            andares.add(andar)
            assert g["lugar"] is not None, g                                                     # antes ficava sem nome
            assert g["lugar"] == _mais_perto(d["L"], d["R"], destino, andar), (g, andar)
            assert g["lugar"] in {d["L"]["textos"][ix] for ix, _ in d["L"]["rotulos"][andar]}     # e é um nome do andar do destino
        assert not erros
    finally:
        ctx.close()


def test_na_nuke_o_o_que_mudou_diz_os_lugares_do_real_e_da_troca(navegador, nuke):
    ctx, pg, erros = _abre(navegador, nuke, 1440, 900, round_=2, frac=0.5)
    try:
        _grupos(pg, "smoke")
        _clica(pg, ".rw-alt", 0); _clica(pg, '[data-foco="trocar"]')
        texto = " ".join(pg.locator("#rw-mudou li").all_inner_texts())
        assert re.search(r"caiu em [A-Z ]+\. Na sua versão, ela cai em [A-Z ]+ às \d:\d\d", texto), texto     # com os nomes (antes: "no ponto do real" / "no ponto escolhido")
        assert "no ponto do real" not in texto and "no ponto escolhido" not in texto
        assert not erros
    finally:
        ctx.close()
