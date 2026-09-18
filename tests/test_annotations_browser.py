"""
Testes de NAVEGADOR da camada de desenho (dashboard/web/annotations.js).

Rodam a página de verdade, gerada por `build_web_page`, num Chrome controlado
pelo Playwright, e conferem o que aparece na TELA -- o pixel composto pelo
navegador, não o conteúdo de um canvas isolado. A distinção importa e foi o que
deixou a regressão do mapa passar: o canvas do mapa estava desenhado o tempo
todo, e o que a pessoa via era a camada de anotação, opaca, por cima dele. Um
teste que lesse o canvas do mapa teria passado com o mapa invisível.

Sem Playwright ou sem Chrome instalado os testes são PULADOS, com o motivo no
relatório. Para rodar: `py -3.12 -m pip install playwright` (usa o Chrome já
instalado na máquina; não precisa baixar navegador).
"""
from __future__ import annotations

import io
import json
import math
from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")
from PIL import Image  # noqa: E402

from metrics.annotations import valida  # noqa: E402
from scripts.build_web_page import build_html  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Fundo do painel (#161d26). É a cor que aparece onde o mapa NÃO está: com a
# regressão, a área inteira do mapa ficava nesta cor.
FUNDO = (22, 29, 38)

# Fração mínima da área do mapa, na tela, que não é o fundo do painel. O radar
# tem muita área escura fora do caminhável, então o número não chega perto de
# 100%. Medido nos 7 mapas com radar, com o mapa VISÍVEL: Nuke 0,170, Ancient
# 0,259, Inferno 0,306, Anubis 0,311, Mirage 0,315, Overpass 0,371, Dust2
# 0,496. Com a camada opaca por cima (a regressão): 0,000 nos 7.
MIN_MAPA_VISIVEL = 0.10

COR_PADRAO = (0xEB, 0x68, 0x34)


# --- Montagem ----------------------------------------------------------------

def _partida_com_radar() -> tuple[str, dict] | None:
    for d in sorted((PROJECT_ROOT / "data" / "processed").glob("match_*")):
        meta = d / "match_meta.json"
        if not (meta.exists() and (d / "web_payload.json").exists() and (d / "replay.json").exists()):
            continue
        mapa = json.loads(meta.read_text(encoding="utf-8"))["map_name"]
        radar = PROJECT_ROOT / "assets" / "radars" / f"{mapa}.json"
        if radar.exists():
            return d.name, json.loads(radar.read_text(encoding="utf-8"))
    return None


@pytest.fixture(scope="module")
def partida(tmp_path_factory):
    achada = _partida_com_radar()
    if achada is None:
        pytest.skip("nenhuma partida processada com radar calibrado")
    match_id, radar = achada
    html = tmp_path_factory.mktemp("web") / f"{match_id}.html"
    html.write_text(build_html(match_id), encoding="utf-8")
    return {"html": html, "radar": radar, "match_id": match_id}


@pytest.fixture(scope="module")
def navegador():
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch(channel="chrome")
        except Exception:
            try:
                b = p.chromium.launch()
            except Exception as err:  # pragma: no cover - depende da máquina
                pytest.skip(f"sem Chrome para o Playwright: {err}")
        yield b
        b.close()


@pytest.fixture
def contexto(navegador):
    # Contexto novo por teste = armazenamento do navegador vazio por teste.
    ctx = navegador.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
    yield ctx
    ctx.close()


def abre(ctx, partida, erros: list | None = None):
    pg = ctx.new_page()
    erros = erros if erros is not None else []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto(partida["html"].as_uri())
    pg.locator('[data-tab="replay"]').first.click()
    pg.wait_for_function("() => window.MapAnnotations && MapAnnotations._interno.S.reprojecoes > 0")
    espera_mapa(pg)
    assert not erros, f"erro de JavaScript na página: {erros}"
    return pg


# --- Leitura da tela -----------------------------------------------------------

def _captura(pg, x, y, w, h) -> Image.Image:
    png = pg.screenshot(clip={"x": x, "y": y, "width": w, "height": h})
    return Image.open(io.BytesIO(png)).convert("RGB")


def _pixels(img: Image.Image) -> list:
    return list(img.get_flattened_data() if hasattr(img, "get_flattened_data") else img.getdata())


def na_vista(pg):
    """Traz o mapa para dentro da janela. A captura só enxerga o que está na
    tela, e a página tem conteúdo acima do replay: sem isso a medição olha para
    fora do mapa e não mede nada."""
    pg.evaluate("""() => { const c = document.getElementById('map');
        const r = c.getBoundingClientRect();
        if (r.top < 0 || r.bottom > innerHeight) c.scrollIntoView({ block: 'center' }); }""")


def fracao_de_mapa(pg) -> float:
    """Fração da área do mapa, NA TELA, que não é o fundo do painel."""
    na_vista(pg)
    c = pg.locator("#map").bounding_box()
    img = _captura(pg, c["x"], c["y"], c["width"], c["height"]).resize((120, 120))
    px = _pixels(img)
    fora_do_fundo = sum(1 for p in px if max(abs(p[i] - FUNDO[i]) for i in range(3)) > 12)
    return fora_do_fundo / len(px)


def espera_mapa(pg, minimo=MIN_MAPA_VISIVEL, ms=4000):
    """O radar é uma imagem embutida que decodifica de forma assíncrona."""
    fr = 0.0
    for _ in range(ms // 100):
        fr = fracao_de_mapa(pg)
        if fr >= minimo:
            return fr
        pg.wait_for_timeout(100)
    return fr


def traco_na_tela(pg, g, cor, raio=5, tolerancia=40) -> bool:
    """O ponto de JOGO `g` aparece na tela com a cor `cor`?

    Projeta pela caixa ATUAL do mapa -- é assim que se prova que o traço
    continua sobre o mesmo lugar do mapa depois de qualquer mudança de tamanho.
    """
    na_vista(pg)
    x, y = _ponto_na_tela(pg, g)
    img = _captura(pg, x - raio, y - raio, 2 * raio + 1, 2 * raio + 1)
    return any(max(abs(p[i] - cor[i]) for i in range(3)) <= tolerancia for p in _pixels(img))


def _ponto_na_tela(pg, g):
    """Coordenada de JOGO -> posição na tela, pela caixa ATUAL do mapa."""
    return tuple(pg.evaluate(
        """(g) => {
          const I = MapAnnotations._interno, v = I.S.view;
          const p = I.jogoParaPixel(g[0], g[1]);
          const r = document.getElementById('map').getBoundingClientRect();
          const escala = r.width / I.radar().width;
          return [r.left + (p[0] * v.zoom + v.panX) * escala, r.top + (p[1] * v.zoom + v.panY) * escala];
        }""",
        g,
    ))


def modelo(pg) -> dict:
    return pg.evaluate("() => MapAnnotations._interno.documento()")


def estado(pg, campo):
    return pg.evaluate(f"() => MapAnnotations._interno.S.{campo}")


def liga(pg):
    pg.click("#anot-toggle")
    assert estado(pg, "ligado") is True


def desenha_arco(pg, deslocamento=0.0, grossa=True):
    """Meia-volta à mão, no meio do mapa. Devolve os pontos na tela."""
    if grossa:
        pg.click('[data-espessura="7"]')
    na_vista(pg)
    c = pg.locator("#map").bounding_box()
    cx = c["x"] + c["width"] * 0.5
    cy = c["y"] + c["height"] * (0.45 + deslocamento)
    r = c["width"] * 0.18
    pts = [(cx + r * math.cos(t), cy + r * math.sin(t))
           for t in (math.pi * i / 24 for i in range(25))]
    pg.mouse.move(*pts[0])
    pg.mouse.down()
    for p in pts[1:]:
        pg.mouse.move(*p, steps=2)
    pg.mouse.up()
    return pts


def meio_do_traco(tr):
    return tr["pontos"][len(tr["pontos"]) // 2]


def reprojecoes(pg) -> int:
    return estado(pg, "reprojecoes")


def espera_reprojecao(pg, antes):
    pg.wait_for_function(f"() => MapAnnotations._interno.S.reprojecoes > {antes}")
    pg.wait_for_timeout(120)


# --- Problema 1: o mapa aparece ---------------------------------------------

def test_o_mapa_aparece_ao_abrir(contexto, partida):
    """A regressão: a camada de anotação, opaca, cobria o mapa inteiro."""
    pg = abre(contexto, partida)
    assert fracao_de_mapa(pg) >= MIN_MAPA_VISIVEL
    # e a camada, que fica por cima, não tem fundo nenhum
    fundos = pg.evaluate("""() => [...document.querySelectorAll('.anot-camada')]
                             .map(c => getComputedStyle(c).backgroundColor)""")
    assert fundos and all(f in ("rgba(0, 0, 0, 0)", "transparent") for f in fundos), fundos


def test_redimensionar_redesenha_todas_as_camadas(contexto, partida):
    """Redimensionar APAGA o canvas: o mapa e os traços têm que voltar os dois.

    Este é o teste que impede a regressão do mapa de voltar. Ele cobre os dois
    caminhos: a janela mudando de tamanho de verdade (o canvas muda de
    resolução e é apagado) e o caso direto -- o mapa apagado por fora e um
    `resize` que tem que redesenhá-lo, não só a camada de desenho.
    """
    pg = abre(contexto, partida)
    liga(pg)
    desenha_arco(pg)
    tr = modelo(pg)["rounds"]
    (traco,) = [t for lista in tr.values() for t in lista]

    largura_antes = pg.evaluate("() => document.getElementById('map').width")
    antes = reprojecoes(pg)
    pg.set_viewport_size({"width": 500, "height": 900})
    espera_reprojecao(pg, antes)

    assert pg.evaluate("() => document.getElementById('map').width") != largura_antes, \
        "o teste precisa de uma mudança de resolução real, senão não mede nada"
    assert espera_mapa(pg) >= MIN_MAPA_VISIVEL
    assert traco_na_tela(pg, meio_do_traco(traco), COR_PADRAO)

    # controle: apagar o mapa por fora apaga mesmo (senão o teste não mede nada)
    pg.evaluate("() => { const c = document.getElementById('map'); c.width = c.width; }")
    assert fracao_de_mapa(pg) < 0.05
    antes = reprojecoes(pg)
    pg.evaluate("() => window.dispatchEvent(new Event('resize'))")
    espera_reprojecao(pg, antes)
    assert fracao_de_mapa(pg) >= MIN_MAPA_VISIVEL, "o resize redesenhou só a camada de desenho"
    assert traco_na_tela(pg, meio_do_traco(traco), COR_PADRAO)


def test_densidade_de_pixel_entra_na_resolucao(navegador, partida):
    ctx = navegador.new_context(viewport={"width": 1280, "height": 900}, device_scale_factor=2)
    try:
        pg = abre(ctx, partida)
        largura, css = pg.evaluate(
            "() => { const c = document.getElementById('map'); return [c.width, c.clientWidth]; }")
        assert largura == round(css * 2)
        assert fracao_de_mapa(pg) >= MIN_MAPA_VISIVEL
    finally:
        ctx.close()


def test_tela_cheia_mantem_mapa_proporcao_e_coordenadas(contexto, partida):
    """Entrar e sair de tela cheia: mapa visível, proporção do radar, e as
    coordenadas ARMAZENADAS do traço idênticas -- o traço continua sobre o
    mesmo ponto do mapa."""
    pg = abre(contexto, partida)
    liga(pg)
    desenha_arco(pg)
    doc_antes = modelo(pg)
    (traco,) = [t for lista in doc_antes["rounds"].values() for t in lista]
    caixa_normal = pg.locator("#map").bounding_box()

    antes = reprojecoes(pg)
    pg.click("#anot-fs")
    pg.wait_for_function("() => !!document.fullscreenElement")
    espera_reprojecao(pg, antes)

    caixa = pg.locator("#map").bounding_box()
    vp = pg.viewport_size
    rw, rh = partida["radar"]["width"], partida["radar"]["height"]
    assert caixa["width"] / caixa["height"] == pytest.approx(rw / rh, rel=0.01)
    assert caixa["width"] <= vp["width"] + 1 and caixa["height"] <= vp["height"] + 1
    assert caixa["height"] > caixa_normal["height"]
    assert espera_mapa(pg) >= MIN_MAPA_VISIVEL
    assert modelo(pg) == doc_antes
    assert traco_na_tela(pg, meio_do_traco(traco), COR_PADRAO)

    antes = reprojecoes(pg)
    pg.evaluate("() => document.exitFullscreen()")
    pg.wait_for_function("() => !document.fullscreenElement")
    espera_reprojecao(pg, antes)
    assert espera_mapa(pg) >= MIN_MAPA_VISIVEL
    assert modelo(pg) == doc_antes
    assert traco_na_tela(pg, meio_do_traco(traco), COR_PADRAO)


# --- Problema 2: um clique e já desenha ---------------------------------------

def test_um_clique_ja_desenha_a_mao_livre(contexto, partida):
    """Arrastar em curva produz curva: a ferramenta padrão é a caneta, e ela
    guarda o caminho da mão, não um segmento entre início e fim."""
    pg = abre(contexto, partida)
    pg.click("#anot-toggle")
    assert estado(pg, "ligado") is True
    assert estado(pg, "ferramenta") == "caneta"

    desenha_arco(pg, grossa=False)
    (traco,) = [t for lista in modelo(pg)["rounds"].values() for t in lista]
    assert traco["ferramenta"] == "caneta"
    pts = traco["pontos"]
    assert len(pts) >= 10

    # distância máxima dos pontos à corda entre o primeiro e o último: numa
    # reta é zero; numa meia-volta é o raio
    (x0, y0), (x1, y1) = pts[0], pts[-1]
    corda = math.hypot(x1 - x0, y1 - y0)
    flecha = max(abs((x1 - x0) * (y0 - y) - (x0 - x) * (y1 - y0)) / corda for x, y in pts)
    assert flecha > corda * 0.3


def test_reabre_com_a_ultima_ferramenta_usada(contexto, partida):
    pg = abre(contexto, partida)
    liga(pg)
    pg.click('[data-ferramenta="seta"]')
    pg.click("#anot-toggle")               # sai
    assert estado(pg, "ligado") is False
    pg.click("#anot-toggle")               # volta
    assert estado(pg, "ferramenta") == "seta"


def test_desligado_a_camada_nao_intercepta_o_ponteiro(contexto, partida):
    """Com o modo desligado, o clique chega no que está embaixo."""
    pg = abre(contexto, partida)
    pg.evaluate("""() => { window.__cliques = 0;
        document.getElementById('map').addEventListener('click', () => window.__cliques++); }""")
    liga(pg)
    pg.keyboard.press("Escape")            # Esc sai do modo
    assert estado(pg, "ligado") is False
    assert pg.evaluate("() => getComputedStyle(document.querySelector('.anot-camada')).pointerEvents") == "none"
    na_vista(pg)
    c = pg.locator("#map").bounding_box()
    centro = (c["x"] + c["width"] / 2, c["y"] + c["height"] / 2)
    assert pg.evaluate(f"() => document.elementFromPoint({centro[0]}, {centro[1]}).id") == "map"
    pg.mouse.click(*centro)
    assert pg.evaluate("() => window.__cliques") == 1

    liga(pg)
    pg.click("#anot-toggle")               # segundo clique também sai
    na_vista(pg)
    c = pg.locator("#map").bounding_box()
    pg.mouse.click(c["x"] + c["width"] / 2, c["y"] + c["height"] / 2)
    assert pg.evaluate("() => window.__cliques") == 2


# --- Problema 3: os desenhos voltam ------------------------------------------

def test_o_desenho_volta_ao_trocar_de_round(contexto, partida):
    pg = abre(contexto, partida)
    liga(pg)
    desenha_arco(pg)
    r0 = estado(pg, "round")
    (traco,) = [t for lista in modelo(pg)["rounds"].values() for t in lista]

    botoes = pg.locator("#strip button")
    outro = next(i for i in range(botoes.count()) if botoes.nth(i).inner_text().strip() != str(r0))
    botoes.nth(outro).click()
    assert estado(pg, "round") != r0
    assert pg.evaluate("() => MapAnnotations._interno.visiveis().length") == 0

    volta = next(i for i in range(botoes.count()) if botoes.nth(i).inner_text().strip() == str(r0))
    botoes.nth(volta).click()
    pg.wait_for_timeout(150)
    assert pg.evaluate("() => MapAnnotations._interno.visiveis().length") == 1
    assert traco_na_tela(pg, meio_do_traco(traco), COR_PADRAO)


def test_o_modelo_salvo_e_recarregado_reproduz_os_mesmos_tracos(contexto, partida):
    """Recarregar a página: os traços voltam idênticos, e na tela."""
    pg = abre(contexto, partida)
    liga(pg)
    desenha_arco(pg)
    pg.click('[data-ferramenta="seta"]')
    desenha_arco(pg, deslocamento=0.2)
    antes = modelo(pg)
    assert sum(len(v) for v in antes["rounds"].values()) == 2

    pg.reload()
    pg.locator('[data-tab="replay"]').first.click()
    pg.wait_for_function("() => MapAnnotations._interno.S.reprojecoes > 0")
    espera_mapa(pg)
    depois = modelo(pg)
    assert depois == antes
    caneta = next(t for lista in depois["rounds"].values() for t in lista if t["ferramenta"] == "caneta")
    assert traco_na_tela(pg, meio_do_traco(caneta), COR_PADRAO)


def test_falha_no_armazenamento_nao_derruba_a_pagina(navegador, partida):
    """Armazenamento bloqueado: a página abre, o mapa aparece, dá para desenhar,
    e a barra avisa que não vai salvar."""
    ctx = navegador.new_context(viewport={"width": 1280, "height": 900})
    ctx.add_init_script("""
      for (const nome of ['localStorage', 'sessionStorage']) {
        Object.defineProperty(window, nome, {
          configurable: true,
          get() { throw new DOMException('bloqueado', 'SecurityError'); }
        });
      }""")
    try:
        erros: list = []
        pg = abre(ctx, partida, erros)
        assert fracao_de_mapa(pg) >= MIN_MAPA_VISIVEL
        liga(pg)
        desenha_arco(pg)
        pg.wait_for_timeout(600)            # passa do atraso da gravação
        assert sum(len(v) for v in modelo(pg)["rounds"].values()) == 1
        assert pg.inner_text("#anot-status").strip() != ""
        assert not erros, erros
    finally:
        ctx.close()


def test_exportar_e_importar_reproduz_os_tracos(navegador, contexto, partida):
    """O arquivo exportado abre em OUTRO navegador com os mesmos traços, e
    passa na validação do lado Python -- inclusive a da calibração, que é a
    prova de que as duas pontas calculam a mesma impressão."""
    pg = abre(contexto, partida)
    liga(pg)
    desenha_arco(pg)
    antes = modelo(pg)
    with pg.expect_download() as baixado:
        pg.click("#anot-exportar")
    doc = json.loads(Path(baixado.value.path()).read_text(encoding="utf-8"))
    assert doc == antes
    assert valida(doc, partida["radar"]) == []
    for lista in doc["rounds"].values():
        for t in lista:
            assert t["mapa"] == partida["radar"]["map"]
            assert t["calibracao"] == doc["calibracao"]

    outro = navegador.new_context(viewport={"width": 1280, "height": 900})
    try:
        pg2 = abre(outro, partida)
        caminho = baixado.value.path()
        pg2.set_input_files("#anot-arquivo", str(caminho))
        pg2.wait_for_function("() => Object.keys(MapAnnotations._interno.documento().rounds).length > 0")
        assert modelo(pg2) == antes
        # importar de novo não duplica
        pg2.set_input_files("#anot-arquivo", str(caminho))
        pg2.wait_for_timeout(300)
        assert modelo(pg2) == antes
    finally:
        outro.close()


# --- Problema 4: seletor de cor ----------------------------------------------

def test_cor_escolhida_vale_so_para_os_proximos_tracos(contexto, partida):
    pg = abre(contexto, partida)
    liga(pg)
    desenha_arco(pg)

    pg.click("#anot-cor-seta")
    pg.fill("#anot-cor-hex", "#12ab34")
    pg.keyboard.press("Escape")            # fechar o seletor aplica a cor
    assert estado(pg, "cor") == "#12ab34"
    assert pg.evaluate("() => getComputedStyle(document.getElementById('anot-cor-atual')).backgroundColor") \
        == "rgb(18, 171, 52)"

    desenha_arco(pg, deslocamento=0.2)
    t1, t2 = [t for lista in modelo(pg)["rounds"].values() for t in lista]
    assert t1["cor"] == "#eb6834"          # o traço já feito não muda
    assert t2["cor"] == "#12ab34"
    assert traco_na_tela(pg, meio_do_traco(t2), (0x12, 0xAB, 0x34))

    # RGB digitado, fechado por clique fora
    pg.click("#anot-cor-seta")
    pg.fill("#anot-cor-r", "200")
    pg.fill("#anot-cor-g", "10")
    pg.fill("#anot-cor-b", "90")
    pg.click("#rh-round")
    assert estado(pg, "cor") == "#c80a5a"

    # a fileira de recentes troca sem reabrir o seletor
    recentes = pg.evaluate("() => [...document.querySelectorAll('[data-recente]')].map(b => b.dataset.recente)")
    assert recentes[:2] == ["#c80a5a", "#12ab34"]
    pg.click('[data-recente="#12ab34"]')
    assert estado(pg, "cor") == "#12ab34"
    assert pg.evaluate("() => document.getElementById('anot-seletor').hidden") is True


def test_cor_invalida_nao_e_aplicada(contexto, partida):
    pg = abre(contexto, partida)
    liga(pg)
    pg.click("#anot-cor-seta")
    pg.fill("#anot-cor-hex", "#12zz34")
    assert pg.get_attribute("#anot-cor-hex", "aria-invalid") == "true"
    pg.keyboard.press("Escape")
    assert estado(pg, "cor") == "#eb6834"
