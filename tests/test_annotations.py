"""
Testes da camada de anotação: geometria, formato e contrato da interface.

O que é testado DE VERDADE e o que é testado por estrutura -- a distinção
importa e está declarada em cada teste:

- a **geometria** (projeção nos dois sentidos, proporção, reprojeção) vive em
  `metrics/annotations.py` justamente para poder ser testada de verdade. É ela
  que decide se a seta aponta para o lugar certo, e é o único jeito de checar
  isso sem um navegador;
- o **comportamento de interface** (camada inativa não intercepta clique, evento
  de ponteiro em vez de mouse, pausa ao começar o traço) é JavaScript e este
  projeto não tem runtime de JS nos testes. Aqui ele é verificado pela presença
  da construção correta no arquivo. É mais fraco que um teste de navegador, e
  está marcado como estrutural para ninguém confundir as duas coisas.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from metrics.annotations import (
    CORES,
    ESPESSURAS,
    FERRAMENTAS,
    FORMATO,
    caixa_do_mapa,
    documento_vazio,
    impressao_da_calibracao,
    jogo_para_pixel,
    pixel_para_jogo,
    tracos_do_round,
    valida,
)

JS = Path("dashboard/web/annotations.js")
TEMPLATE = Path("dashboard/web/template.html")

RADAR = {
    "map": "de_mirage",
    "width": 1024,
    "height": 1024,
    "scale_px_per_unit": 0.2,
    "origin_x": -3230.0,
    "origin_y": 1713.0,
}


# --- Geometria ---------------------------------------------------------------

@pytest.mark.parametrize("x,y", [(0.0, 0.0), (-2000.0, 900.0), (1500.5, -1200.25)])
def test_a_projecao_volta_no_mesmo_ponto(x, y):
    """Pixel -> jogo -> pixel tem que fechar. É a inversa exata, não aproximada."""
    px, py = jogo_para_pixel(x, y, RADAR)
    gx, gy = pixel_para_jogo(px, py, RADAR)
    assert gx == pytest.approx(x, abs=1e-9)
    assert gy == pytest.approx(y, abs=1e-9)


def test_o_eixo_y_e_invertido():
    """No jogo o Y cresce pro norte; na imagem cresce pra baixo.

    Errar esse sinal espelha o mapa na vertical, e o desenho fica plausível o
    bastante para ninguém notar de imediato -- que é o pior jeito de errar.
    """
    _, py_alto = jogo_para_pixel(0.0, 1000.0, RADAR)
    _, py_baixo = jogo_para_pixel(0.0, -1000.0, RADAR)
    assert py_alto < py_baixo


def test_o_desenho_nao_muda_quando_a_tela_muda():
    """A propriedade central: a coordenada ARMAZENADA é de jogo e não se mexe.

    O mesmo traço, projetado em janela pequena e em tela cheia, dá pixels
    diferentes -- e é isso que tem que acontecer. O que não pode mudar é o dado
    guardado, e é ele que faz a seta continuar apontando pro fundo do bomb.
    """
    traco = [(-1500.0, 400.0), (-900.0, 120.0)]

    pequena = caixa_do_mapa(520, 520, RADAR)
    cheia = caixa_do_mapa(1920, 1080, RADAR)
    assert cheia["escala"] > pequena["escala"]

    # os pixels mudam...
    px_p = [jogo_para_pixel(x, y, RADAR)[0] * pequena["escala"] for x, y in traco]
    px_c = [jogo_para_pixel(x, y, RADAR)[0] * cheia["escala"] for x, y in traco]
    assert px_p != px_c

    # ...e o dado guardado, não. Reprojetando de volta, o ponto é o mesmo.
    for (gx, gy) in traco:
        pxi, pyi = jogo_para_pixel(gx, gy, RADAR)
        assert pixel_para_jogo(pxi, pyi, RADAR) == pytest.approx((gx, gy), abs=1e-9)


@pytest.mark.parametrize("w,h", [(1920, 1080), (1080, 1920), (800, 800), (2560, 1440)])
def test_a_proporcao_do_mapa_nao_muda_com_a_tela(w, h):
    """O mapa cresce até o limite da MENOR dimensão e centraliza.

    Nunca esticado: já houve bug de proporção neste projeto (dado em retrato num
    canvas em paisagem), e esticar é exatamente o que produz aquilo.
    """
    caixa = caixa_do_mapa(w, h, RADAR)
    assert caixa["proporcao"] == pytest.approx(RADAR["width"] / RADAR["height"])
    assert caixa["largura"] <= w + 1e-9 and caixa["altura"] <= h + 1e-9
    # o excedente vira espaço vazio, dos dois lados igualmente
    assert caixa["offset_x"] >= -1e-9 and caixa["offset_y"] >= -1e-9


# --- Versão da calibração ----------------------------------------------------

def test_a_impressao_muda_quando_a_calibracao_muda():
    """Sem isso, um recalibrar futuro desloca todo desenho antigo em silêncio."""
    base = impressao_da_calibracao(RADAR)
    assert base == impressao_da_calibracao(dict(RADAR))       # estável
    assert base != impressao_da_calibracao({**RADAR, "scale_px_per_unit": 0.2001})
    assert base != impressao_da_calibracao({**RADAR, "origin_x": -3229.0})
    assert base != impressao_da_calibracao({**RADAR, "map": "de_dust2"})


def test_documento_com_calibracao_antiga_e_apontado_na_validacao():
    doc = documento_vazio("match_01", RADAR)
    assert valida(doc, RADAR) == []

    mudado = {**RADAR, "scale_px_per_unit": 0.25}
    problemas = valida(doc, mudado)
    assert any("reprojetadas" in p for p in problemas)


# --- Formato -----------------------------------------------------------------

def test_trocar_de_round_nao_mistura_desenhos():
    """Rabisco de um round não pode vazar no outro. A separação é do FORMATO.

    Estar no formato, e não só na interface, é o que garante que ela sobrevive a
    exportar, reabrir e recarregar.
    """
    doc = documento_vazio("match_01", RADAR)
    doc["rounds"]["3"] = [{"ferramenta": "seta", "pontos": [[0, 0], [10, 10]]}]
    doc["rounds"]["4"] = [
        {"ferramenta": "caneta", "pontos": [[1, 1], [2, 2]]},
        {"ferramenta": "elipse", "pontos": [[3, 3], [9, 9]]},
    ]
    assert len(tracos_do_round(doc, 3)) == 1
    assert len(tracos_do_round(doc, 4)) == 2
    assert tracos_do_round(doc, 5) == []
    assert tracos_do_round(doc, 3)[0]["ferramenta"] == "seta"


def test_a_validacao_junta_todos_os_problemas():
    """Quem confere um arquivo quer a lista inteira, não uma descoberta por vez."""
    ruim = {
        "formato": 99, "match_id": "", "calibracao": "",
        "rounds": {"1": [{"ferramenta": "laser", "pontos": []}]},
    }
    problemas = valida(ruim)
    assert len(problemas) >= 4
    assert any("formato" in p for p in problemas)
    assert any("match_id" in p for p in problemas)
    assert any("laser" in p for p in problemas)
    assert any("sem pontos" in p for p in problemas)


def test_o_documento_carrega_mapa_e_calibracao():
    doc = documento_vazio("match_07", RADAR)
    assert doc["formato"] == FORMATO
    assert doc["match_id"] == "match_07"
    assert doc["mapa"] == "de_mirage"
    assert doc["calibracao"] == impressao_da_calibracao(RADAR)


def test_as_ferramentas_e_a_paleta_batem_com_a_camada_js():
    """Se Python e JS divergirem, um arquivo exportado num não abre no outro."""
    js = JS.read_text(encoding="utf-8")
    for f in FERRAMENTAS:
        assert f'id: "{f}"' in js, f"ferramenta {f} não existe na camada JS"
    for hexa in CORES.values():
        assert hexa.lower() in js.lower(), f"cor {hexa} não está na camada JS"
    assert f"var ESPESSURAS = {list(ESPESSURAS)};".replace("'", '"') in js.replace("'", '"')
    assert f"var FORMATO = {FORMATO};" in js


# --- Contrato da interface (ESTRUTURAL: não há runtime de JS nos testes) -----

def test_estrutural_a_camada_desligada_nao_intercepta_clique():
    """Com o modo desligado, clicar num jogador tem que chegar no jogador.

    Duas travas: o CSS já nasce com `pointer-events: none` (para um erro do JS
    falhar pro lado seguro) e o JS só liga quando o modo de desenho liga.
    """
    css = TEMPLATE.read_text(encoding="utf-8")
    bloco = css[css.index(".anot-camada {"):css.index(".anot-barra {")]
    assert "pointer-events: none;" in bloco

    js = JS.read_text(encoding="utf-8")
    assert 'camada.style.pointerEvents = S.ligado ? "auto" : "none";' in js
    assert 'rascunho.style.pointerEvents = "none";' in js


def test_estrutural_usa_evento_de_ponteiro_e_nao_de_mouse():
    """Ponteiro atende mouse, toque e caneta de tablet com o mesmo código."""
    js = JS.read_text(encoding="utf-8")
    assert "pointerdown" in js and "pointermove" in js and "pointerup" in js
    for antigo in ("mousedown", "mousemove", "mouseup", "touchstart"):
        assert antigo not in js, f"{antigo} não deveria existir na camada"


def test_estrutural_pausa_a_reproducao_ao_comecar_o_traco():
    """Ninguém consegue desenhar em cima de boneco que está andando."""
    js = JS.read_text(encoding="utf-8")
    inicio = js.index("function comecou(")
    fim = js.index("function moveu(")
    assert "opts.pause()" in js[inicio:fim]


def test_estrutural_respeita_a_densidade_de_pixels():
    """Sem devicePixelRatio, o traço fino sai borrado em tela de alta resolução."""
    js = JS.read_text(encoding="utf-8")
    assert "devicePixelRatio" in js
    assert js.count("devicePixelRatio") >= 3


def test_estrutural_o_traco_em_andamento_vive_na_camada_de_rascunho():
    """Consolidar só ao soltar é o que impede um traço longo de repintar tudo."""
    js = JS.read_text(encoding="utf-8")
    assert "function repintaRascunho()" in js
    inicio = js.index("function moveu(")
    fim = js.index("function soltou(")
    assert "repintaRascunho()" in js[inicio:fim]
    assert "repinta()" not in js[inicio:fim], "mover o ponteiro não pode repintar tudo"


def test_estrutural_a_camada_vive_em_arquivo_separado():
    """O template já está grande demais."""
    assert JS.exists()
    tpl = TEMPLATE.read_text(encoding="utf-8")
    assert "/*__ANNOTATIONS__*/" in tpl
    assert "window.MapAnnotations = (function" not in tpl


def test_estrutural_o_mapa_e_a_camada_usam_a_mesma_transformacao():
    """Se as duas divergirem, a seta aponta pro lugar errado no primeiro zoom."""
    tpl = TEMPLATE.read_text(encoding="utf-8")
    assert "MapAnnotations.applyView(ctx)" in tpl
    js = JS.read_text(encoding="utf-8")
    assert "function applyView(ctx)" in js
    assert "applyView(ctxC)" in js and "applyView(ctxR)" in js


def test_estrutural_trocar_de_round_avisa_a_camada():
    tpl = TEMPLATE.read_text(encoding="utf-8")
    inicio = tpl.index("function selectRound(r) {")
    assert "MapAnnotations.setRound(r.round)" in tpl[inicio:inicio + 700]


def test_estrutural_a_pagina_construida_leva_a_camada_junto():
    """A página é um arquivo único que abre offline: o JS separado é injetado."""
    construida = Path("docs/match_01.html")
    if not construida.exists():
        pytest.skip("site ainda não construído")
    h = construida.read_text(encoding="utf-8")
    assert "window.MapAnnotations" in h
    assert "/*__ANNOTATIONS__*/" not in h
