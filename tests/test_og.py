"""Imagem de compartilhamento e carregamento da partida (v2-6, decisão 48; plano v2-0 §4.6 e dúvidas 5 e 7).

A imagem 1200x630 sai do build em Pillow, sem navegador, com os mesmos bytes a cada build e sem metadado; a og:image
de cada página aponta para um arquivo que o build escreve. O esqueleto do Replay aparece com `?estado=carregando` e
some quando a página termina de carregar."""
from __future__ import annotations

import io
import json
import re
import struct
from pathlib import Path

import pytest
from PIL import Image

from scripts.design.gera_og import imagem_da_landing, imagem_da_partida

RAIZ = Path(__file__).resolve().parent.parent
PROCESSADO = RAIZ / "data" / "processed"
SITE = "https://pedroppansani.github.io/parser-replay-cs2/"
PESO_MAXIMO = 100_000            # bytes por PNG (plano: 70 a 95 KB; saem bem menores)
EMAIL = re.compile(rb"[\w.+-]+@[\w-]+\.[\w.]+")


def _blocos(png: bytes) -> list[str]:
    """Os tipos de bloco do PNG, na ordem."""
    i, tipos = 8, []
    while i < len(png):
        n, tipo = struct.unpack(">I4s", png[i:i + 8])
        tipos.append(tipo.decode("ascii"))
        i += 12 + n
    return tipos


def _exemplos() -> dict[str, bytes]:
    return {
        "partida": imagem_da_partida("de_mirage", ("Time de -_-siNNer", "Time de adamS"), (13, 5), "A",
                                     ["Mirage · IEM Cologne Major 2026", "Decidida no round 19 · MVP donk666"]),
        "nome longo": imagem_da_partida("de_nuke", ("Um nome de time comprido demais para caber", "B"), (16, 14),
                                        "B", ["Nuke", ""]),
        "sem radar": imagem_da_partida("de_inexistente", ("A", "B"), (13, 0), None, ["?"]),
        "landing": imagem_da_landing("de_dust2", "Cada round, explicado.", "Replay de partidas de CS2"),
    }


def test_a_imagem_e_deterministica_1200x630_leve_e_sem_metadado():
    a, b = _exemplos(), _exemplos()
    for nome, png in a.items():
        assert png == b[nome], nome
        assert Image.open(io.BytesIO(png)).size == (1200, 630), nome
        assert len(png) <= PESO_MAXIMO, (nome, len(png))
        assert set(_blocos(png)) <= {"IHDR", "PLTE", "tRNS", "IDAT", "IEND"}, (nome, _blocos(png))
        assert not EMAIL.search(png), nome


def _partidas(n: int) -> list[dict]:
    from scripts.build_site import match_summary
    ids = sorted(d.name for d in PROCESSADO.glob("match_*"))[:n]
    return [m for m in (match_summary(i) for i in ids) if m]


def test_og_image_de_cada_pagina_aponta_para_um_arquivo_gerado(tmp_path):
    from scripts.build_jogadores import build_html as jogadores
    from scripts.build_site import build_index, gera_imagens_og
    from scripts.build_tactics_page import build_html as prancheta
    from scripts.build_web_page import build_html as partida
    partidas = _partidas(2)
    if not partidas:
        pytest.skip("sem partida processada")
    gera_imagens_og(tmp_path, partidas)
    repo = "https://github.com/pedroppansani/parser-replay-cs2"
    paginas = {"landing": build_index(partidas, repo, [], numeros=None),
               "prancheta": prancheta("de_mirage", site=SITE), "jogadores": jogadores(SITE)}
    for m in partidas:
        paginas[m["id"]] = partida(m["id"], site={"matches": [], "current": m["id"], "repo": repo})
    for nome, html in paginas.items():
        url = re.search(r'property="og:image" content="([^"]+)"', html).group(1)
        assert url.startswith(SITE), nome
        arquivo = tmp_path / url[len(SITE):]
        assert arquivo.is_file(), (nome, url)
        assert Image.open(arquivo).size == (1200, 630)
        assert 'property="og:image:width" content="1200"' in html and 'property="og:image:height" content="630"' in html
        assert not EMAIL.search(html.encode("utf-8")), nome
    for m in partidas:
        assert f'og/{m["id"]}.png' in paginas[m["id"]]
    assert len(list((tmp_path / "og").glob("*.png"))) == len(partidas) + 1


def test_a_partida_tem_o_esqueleto_com_a_mascara_e_sem_porcentagem():
    from scripts.build_web_page import build_html as partida
    m = next(iter(_partidas(1)), None)
    if m is None:
        pytest.skip("sem partida processada")
    html = partida(m["id"])
    bloco = re.search(r'<div class="carregando" id="carregando" role="status"[^>]*>.*?</div>', html, re.S).group(0)
    assert "--m:url(data:image/webp;base64," in bloco
    assert not re.search(r"\d", re.sub(r"style=\"[^\"]*\"", "", bloco))      # nenhum número, nenhuma porcentagem
    assert "<!--__CARREGANDO__-->" not in html


sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_annotations_browser import contexto, navegador, partida  # noqa: E402,F401  (fixtures)


def test_o_esqueleto_aparece_com_estado_carregando_e_some_com_o_replay_montado(contexto, partida):
    pg = contexto.new_page()
    pg.goto(partida["html"].as_uri() + "#replay")
    pg.wait_for_function("() => document.readyState === 'complete'")
    pg.wait_for_function("() => document.getElementById('carregando').hidden")
    assert not pg.locator("#carregando").is_visible()
    forcado = contexto.new_page()
    forcado.goto(partida["html"].as_uri() + "?estado=carregando#replay")
    forcado.wait_for_function("() => document.readyState === 'complete'")
    forcado.wait_for_timeout(200)
    esq = forcado.locator("#carregando")
    assert esq.is_visible()
    caixa, mapa = esq.bounding_box(), forcado.locator("#map").bounding_box()
    assert abs(caixa["width"] - mapa["width"]) < 2 and abs(caixa["height"] - mapa["height"]) < 2   # cobre o mapa
    assert json.loads(forcado.evaluate("JSON.stringify(getComputedStyle(document.querySelector('#carregando i')).maskImage)")) != "none"
