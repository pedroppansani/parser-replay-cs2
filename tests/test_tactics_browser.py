"""
Testes de NAVEGADOR da prancheta tática (dashboard/web/tactics.js), num Chrome
controlado pelo Playwright, na página gerada por scripts/build_tactics_page.py.

Sem Playwright ou sem Chrome, são pulados com o motivo no relatório.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from metrics.tactics import aplica, valida  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MAPA = "de_mirage"


@pytest.fixture(scope="module")
def pagina(tmp_path_factory):
    if not (PROJECT_ROOT / "data" / "lineups" / f"{MAPA}.json").exists():
        pytest.skip("biblioteca de arremessos não gerada (scripts/build_lineups.py)")
    from scripts.build_tactics_page import build_html
    html = tmp_path_factory.mktemp("prancheta") / f"prancheta_{MAPA}.html"
    html.write_text(build_html(MAPA), encoding="utf-8")
    return html


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
    ctx = navegador.new_context(viewport={"width": 1300, "height": 950}, accept_downloads=True)
    yield ctx
    ctx.close()


def abre(ctx, pagina):
    pg = ctx.new_page()
    erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto(pagina.as_uri())
    pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
    pg._erros = erros
    return pg


def interno(pg, expr):
    return pg.evaluate(f"() => {{ const I = Prancheta._interno, S = I.S; return {expr}; }}")


def caixa(pg):
    return pg.locator("#pr-mapa").bounding_box()


def no_mapa(pg, fx, fy):
    c = caixa(pg)
    return c["x"] + c["width"] * fx, c["y"] + c["height"] * fy


def arrasta_do_banco(pg, lado, rotulo, fx, fy):
    f = pg.locator(f'.pr-ficha.{lado}[data-rotulo="{rotulo}"]').bounding_box()
    pg.mouse.move(f["x"] + f["width"] / 2, f["y"] + f["height"] / 2)
    pg.mouse.down()
    pg.mouse.move(*no_mapa(pg, fx, fy), steps=6)
    pg.mouse.up()


def test_abre_sem_erro_e_com_uma_tatica_nova(contexto, pagina):
    pg = abre(contexto, pagina)
    assert not pg._erros
    assert interno(pg, "S.estado.passos.length") == 1
    assert interno(pg, "S.doc.formato") == "prancheta-cs2"


def test_o_mapa_nao_e_esticado(contexto, pagina):
    """REGRESSÃO: o canvas saía 896 x 910 -- o max-width cortava só a largura."""
    pg = abre(contexto, pagina)
    for largura in (1300, 1000, 700):
        pg.set_viewport_size({"width": largura, "height": 950})
        pg.wait_for_timeout(100)
        c = caixa(pg)
        assert abs(c["width"] - c["height"]) <= 1, f"{largura}: {c}"


def test_peca_arrastada_do_banco_fica_em_coordenada_de_jogo(contexto, pagina):
    pg = abre(contexto, pagina)
    arrasta_do_banco(pg, "ct", "1", 0.5, 0.5)
    (op,) = [o for o in interno(pg, "S.doc.operacoes") if o["tipo"] == "cria_peca"]
    radar = interno(pg, "(({width, scale_px_per_unit}) => ({width, scale_px_per_unit}))(I.radar())")
    esperado = interno(pg, f"I.pixelParaJogo({radar['width']} / 2, {radar['width']} / 2)")
    # um pixel de TELA de tolerância, convertido para unidade de jogo
    tol = radar["width"] / caixa(pg)["width"] / radar["scale_px_per_unit"]
    assert abs(op["x"] - esperado[0]) <= tol and abs(op["y"] - esperado[1]) <= tol
    assert op["lado"] == "ct" and op["rotulo"] == "1"


def test_mover_no_passo_2_nao_muda_o_passo_1(contexto, pagina):
    pg = abre(contexto, pagina)
    arrasta_do_banco(pg, "t", "3", 0.3, 0.3)
    p1 = interno(pg, "Object.values(S.estado.pecas)[0].posicoes")
    pg.click("#pr-novo-passo")
    assert interno(pg, "S.passo") == 1
    pg.mouse.move(*no_mapa(pg, 0.3, 0.3))
    pg.mouse.down()
    pg.mouse.move(*no_mapa(pg, 0.6, 0.4), steps=6)
    pg.mouse.up()
    pecas = interno(pg, "S.estado.pecas")
    (peca,) = pecas.values()
    assert len(peca["posicoes"]) == 2
    pg.click('[data-passo="1"]')
    assert interno(pg, "I.posicaoNoPasso(Object.values(S.estado.pecas)[0], S.estado.passos, 0)") == \
        list(p1.values())[0]


def test_buscar_arremesso_real_poe_a_granada_com_o_comando(contexto, pagina):
    """A prioridade da prancheta: clicar onde a smoke deve cair e sair com um
    arremesso REAL do corpus, com o comando de console dele."""
    pg = abre(contexto, pagina)
    pg.click('[data-arma="smoke"]')
    pg.click('[data-ferramenta="buscar"]')
    pg.mouse.click(*no_mapa(pg, 0.48, 0.52))
    assert pg.locator(".pr-lista li").count() > 0
    pg.locator(".pr-lista li").first.click()
    (g,) = interno(pg, "Object.values(S.estado.granadas)")
    assert g["arma"] == "smoke" and g["arremesso"] is not None
    assert pg.locator("#pr-comando").text_content() == g["arremesso"]["comando"]
    # e o destino da granada é o do arremesso real, não o do clique
    assert g["destino"] == g["arremesso"]["destino"][:2]


def test_so_parados_filtra_a_busca(contexto, pagina):
    pg = abre(contexto, pagina)
    pg.click('[data-ferramenta="buscar"]')
    pg.check("#pr-so-parado")
    pg.mouse.click(*no_mapa(pg, 0.48, 0.52))
    res = interno(pg, "S.busca.resultados")
    assert res and all(r["movimento"] == "parado" and not r["no_ar"] for r in res)


def test_exportado_e_valido_no_python_e_da_o_mesmo_estado(contexto, pagina):
    """O JS e o Python aplicam o MESMO log e chegam ao mesmo estado."""
    pg = abre(contexto, pagina)
    arrasta_do_banco(pg, "ct", "2", 0.4, 0.6)
    pg.click('[data-ferramenta="buscar"]')
    pg.mouse.click(*no_mapa(pg, 0.48, 0.52))
    pg.locator(".pr-lista li").first.click()
    pg.click("#pr-novo-passo")
    with pg.expect_download() as dl:
        pg.click("#pr-exporta")
    doc = json.loads(Path(dl.value.path()).read_text(encoding="utf-8"))
    estado_py = valida(doc)
    assert estado_py == interno(pg, "S.estado")
    assert estado_py == aplica(doc["operacoes"])


def test_recarregar_mantem_a_tatica(contexto, pagina):
    pg = abre(contexto, pagina)
    arrasta_do_banco(pg, "t", "5", 0.7, 0.7)
    pg.fill("#pr-titulo", "Rush B")
    pg.press("#pr-titulo", "Enter")
    pg.locator("#pr-titulo").blur()
    interno(pg, "I.gravaAgora()")
    antes = interno(pg, "S.doc")
    pg.reload()
    pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
    assert interno(pg, "S.doc") == antes
    assert interno(pg, "S.estado.titulo") == "Rush B"


def test_importar_a_mesma_tatica_de_outro_autor_mescla(contexto, pagina):
    pg = abre(contexto, pagina)
    arrasta_do_banco(pg, "ct", "1", 0.5, 0.5)
    interno(pg, "I.gravaAgora()")
    doc = interno(pg, "S.doc")
    # outro autor, em paralelo, renomeou com o mesmo número de ordem seguinte
    outra = json.loads(json.dumps(doc))
    outra["operacoes"].append({"id": "opdaana0001", "seq": doc["contador"] + 1, "autor": "ana",
                               "em": "2026-09-26T00:00:00Z", "tipo": "renomeia", "titulo": "Da Ana"})
    outra["contador"] = doc["contador"] + 1
    arrasta_do_banco(pg, "t", "1", 0.2, 0.2)          # enquanto isso, edição local
    assert interno(pg, f"I.importaTexto({json.dumps(json.dumps(outra))})") is True
    ops = interno(pg, "S.doc.operacoes")
    assert "opdaana0001" in [o["id"] for o in ops]
    assert sum(o["tipo"] == "cria_peca" for o in ops) == 2      # a edição local ficou
    assert interno(pg, "S.estado.titulo") == "Da Ana"


def test_importacao_de_outra_calibracao_e_recusada(contexto, pagina):
    pg = abre(contexto, pagina)
    doc = interno(pg, "S.doc")
    doc["calibracao"] = "outra"
    doc["id"] = "outratatica0001"
    assert interno(pg, f"I.importaTexto({json.dumps(json.dumps(doc))})") is False
    assert "calibração" in pg.locator("#pr-aviso").text_content()
