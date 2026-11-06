"""L1: a prancheta da Nuke abre cada andar no enquadramento da ÁREA dele (decisão 54, como o Replay), com o mapa de um tamanho só durante a edição;
mapa de um andar só continua no radar inteiro (100%)."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from tests.test_tactics_browser import (  # noqa: E402,F401  (fixtures e ajudas)
    abre, arrasta_do_banco, caixa, contexto, interno, navegador, pagina, pagina_do_mapa)

CAIXA = "() => { const r = document.getElementById('pr-mapa').getBoundingClientRect(); return [Math.round(r.width * 10) / 10, Math.round(r.height * 10) / 10]; }"


def test_a_nuke_abre_no_enquadramento_do_andar_de_cima_e_troca_ao_mudar_de_andar(contexto, tmp_path_factory):
    pg = abre(contexto, pagina_do_mapa(tmp_path_factory, "de_nuke"))
    tamanho = pg.evaluate(CAIXA)
    v0 = interno(pg, "({ ...S.view })")
    assert v0["zoom"] > 1.05 and (v0["panX"] != 0 or v0["panY"] != 0)                       # aberta enquadrada na área do andar de cima, não no radar inteiro
    assert v0["zoom"] <= 2.5 + 1e-9                                                          # o teto do enquadramento (decisão 54)
    pg.evaluate("document.querySelector('[data-andar=\"1\"]').click()")
    v1 = interno(pg, "({ ...S.view })")
    assert v1["zoom"] > 1.05 and (abs(v1["panX"] - v0["panX"]) > 1 or abs(v1["panY"] - v0["panY"]) > 1 or abs(v1["zoom"] - v0["zoom"]) > 1e-6)   # cada andar, o seu quadro
    pg.evaluate("document.querySelector('[data-andar=\"0\"]').click()")
    v2 = interno(pg, "({ ...S.view })")
    assert v2 == v0                                                                          # voltar ao andar de cima volta ao mesmo quadro (zoom fixo por andar)
    assert pg.evaluate(CAIXA) == tamanho                                                     # o mapa não mudou de tamanho
    assert pg.get_attribute("#pr-zoom", "title") is not None and int(pg.inner_text("#pr-zoom").rstrip("%")) > 100


def test_o_mapa_nao_muda_de_tamanho_ao_editar_na_nuke_e_o_100_mostra_o_radar_inteiro(contexto, tmp_path_factory):
    pg = abre(contexto, pagina_do_mapa(tmp_path_factory, "de_nuke"))
    tamanho = pg.evaluate(CAIXA)
    arrasta_do_banco(pg, "ct", "1", 0.5, 0.5)                                                # peça posta, com a vista enquadrada
    assert pg.evaluate(CAIXA) == tamanho
    (peca,) = [d for d in interno(pg, "S.ultimoDesenho") if d["tipo"] == "peca"]
    assert 0 < peca["x"] < caixa(pg)["width"] * 2                                            # a peça foi desenhada (coordenada do canvas)
    pg.evaluate("document.querySelector('[data-andar=\"1\"]').click()")
    arrasta_do_banco(pg, "t", "1", 0.5, 0.5)
    assert pg.evaluate(CAIXA) == tamanho
    pg.click("#pr-zoom")                                                                     # "100%": o radar inteiro
    assert interno(pg, "S.view.zoom") == 1 and pg.evaluate(CAIXA) == tamanho


def test_mapa_de_um_andar_so_continua_no_radar_inteiro(contexto, tmp_path_factory):
    pg = abre(contexto, pagina_do_mapa(tmp_path_factory, "de_mirage"))
    assert interno(pg, "S.view.zoom") == 1 and interno(pg, "S.view.panX") == 0 and interno(pg, "S.view.panY") == 0
