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


# --- Etapa 2: editor v2 -------------------------------------------------------

_PAGINAS: dict = {}


def pagina_do_mapa(tmp_path_factory, mapa):
    """Prancheta de qualquer mapa (uma vez por sessão de teste)."""
    if mapa not in _PAGINAS:
        from scripts.build_tactics_page import build_html
        html = tmp_path_factory.mktemp(f"prancheta_{mapa}") / f"prancheta_{mapa}.html"
        html.write_text(build_html(mapa), encoding="utf-8")
        _PAGINAS[mapa] = html
    return _PAGINAS[mapa]


def no_radar(pg, px, py):
    """Pixel do RADAR -> posição na tela (sem zoom)."""
    c = caixa(pg)
    w = interno(pg, "I.radar().width")
    return c["x"] + px * c["width"] / w, c["y"] + py * c["height"] / w


def solta_foco(pg):
    pg.evaluate("() => document.activeElement && document.activeElement.blur()")


def ultimo(pg, tipo):
    return [d for d in interno(pg, "S.ultimoDesenho") if d["tipo"] == tipo]


def test_espelho_js_python_com_todas_as_operacoes(contexto, pagina):
    """O mesmo log, com todas as operações das versões 1 e 2, dá o mesmo estado
    e o mesmo quadro de cada passo no JS e no Python."""
    from metrics.tactics import aplica as aplica_py, centro_do_radar, ordem_de_criacao, quadro_do_passo

    def op(seq, tipo, autor="pedro", **d):
        return {"id": f"x{seq:04d}{autor}", "seq": seq, "autor": autor, "em": "2026-09-26T00:00:00Z", "tipo": tipo, **d}
    real = {"id": "match_02:6:901", "comando": "setpos 1 2 3; setang 4 5 0", "origem": [1, 2, 3],
            "destino": [9, 9, 9], "pitch": 4.0, "yaw": 5.0}
    ops = [
        op(1, "renomeia", titulo="Espelho"), op(2, "cria_passo", passo="p1", titulo="a"),
        op(3, "cria_passo", passo="p2", titulo="b"), op(4, "cria_passo", passo="p3", titulo="c"),
        op(5, "cria_passo", passo="p4", titulo="d"), op(6, "renomeia_passo", passo="p2", titulo="b2"),
        op(7, "define_duracao", passo="p3", segundos=3.5),
        op(8, "cria_peca", peca="a", lado="ct", rotulo="1", passo="p1", x=-500.0, y=-600.0),
        op(9, "cria_peca", peca="b", lado="t", rotulo="2", passo="p1", x=-900.5, y=100.0, yaw=270.0),
        op(10, "move_peca", peca="a", passo="p2", x=-450.0, y=-500.0),
        op(11, "gira_peca", peca="a", passo="p3", yaw=33.0), op(12, "tira_peca", peca="b", passo="p3"),
        op(13, "cria_peca", peca="c", lado="t", rotulo="3", passo="p2", x=0.0, y=0.0),
        op(14, "remove_peca", peca="c"),
        op(15, "cria_granada", granada="g1", arma="smoke", passo="p1", origem=[-500.0, -600.0], destino=[-300.0, -400.0]),
        op(16, "cria_granada", granada="g2", arma="flash", passo="p2", origem=[-450.0, -500.0], destino=[-200.0, -250.0], arremesso=real),
        op(17, "move_granada", granada="g2", origem=[-450.0, -500.0], destino=[-210.0, -260.0]),
        op(18, "cria_granada", granada="g3", arma="he", passo="p2", origem=[0.0, 0.0], destino=[1.0, 1.0]),
        op(19, "remove_granada", granada="g3"),
        op(20, "cria_traco", traco="t1", passo="p2", ferramenta="seta", cor="#eb6834", espessura=4, pontos=[[0, 0], [50, 50]]),
        op(21, "cria_traco", traco="t2", passo="p3", ferramenta="caneta", cor="#2a78d6", espessura=2, pontos=[[1, 1], [2, 3], [4, 4]]),
        op(22, "define_vida", alvo="t1", dura_passos=None), op(23, "remove_traco", traco="t2"),
        op(24, "cria_granada", granada="g4", arma="molotov", passo="p3", origem=[5.0, 5.0], destino=[6.0, 6.0], dura_passos=2),
        op(25, "anula", alvo="x0017pedro"), op(26, "anula", alvo="x0023pedro"), op(27, "reativa", alvo="x0023pedro"),
        op(28, "anula", autor="ana", alvo="x0010pedro"),       # inválida: outro autor
        op(29, "remove_passo", passo="p4"),
    ]
    pg = abre(contexto, pagina)
    e_js = interno(pg, f"I.aplica({json.dumps(ops)})")
    e_py = aplica_py(ops)
    assert e_js == e_py
    radar = interno(pg, "(({width, height, scale_px_per_unit, origin_x, origin_y}) => ({width, height, scale_px_per_unit, origin_x, origin_y}))(I.radar())")
    centro = centro_do_radar(radar)
    assert interno(pg, "I.centro()") == centro
    for i in range(len(e_py["passos"])):
        q_js = interno(pg, f"I.quadroDoPasso(I.aplica({json.dumps(ops)}), {i}, I.centro())")
        assert q_js == quadro_do_passo(e_py, i, centro), f"passo {i}"
    assert interno(pg, f"I.ordemDeCriacao(I.aplica({json.dumps(ops)}))") == ordem_de_criacao(e_py)


def test_criar_tatica_na_pagina_da_partida_abre_a_prancheta_limpa(navegador, tmp_path_factory):
    from scripts.build_tactics_page import build_html as prancheta
    from scripts.build_web_page import build_html as partida
    pasta = tmp_path_factory.mktemp("site")
    (pasta / "prancheta_de_mirage.html").write_text(prancheta("de_mirage"), encoding="utf-8")
    (pasta / "match_02.html").write_text(partida("match_02"), encoding="utf-8")
    ctx = navegador.new_context(viewport={"width": 1300, "height": 950})
    try:
        pg = ctx.new_page()
        # deixa uma tática com conteúdo aberta nesta aba
        pg.goto((pasta / "prancheta_de_mirage.html").as_uri())
        pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
        arrasta_do_banco(pg, "ct", "1", 0.5, 0.5)
        interno(pg, "I.gravaAgora()")
        velha = interno(pg, "S.doc.id")
        pg.goto((pasta / "match_02.html").as_uri())
        pg.locator('[data-tab="replay"]').first.click()
        pg.click("#anot-criar-tatica")
        pg.wait_for_function("() => window.Prancheta && Prancheta._interno.S.estado !== null")
        assert pg.url.endswith("prancheta_de_mirage.html")          # o ?nova foi consumido
        assert interno(pg, "S.doc.id") != velha
        assert interno(pg, "Object.keys(S.estado.pecas).length") == 0
        assert interno(pg, "S.estado.passos.length") == 1
        assert pg.locator(".pr-ficha").count() == 10
    finally:
        ctx.close()


def test_girar_pela_alca_ate_90_aponta_para_cima(contexto, pagina):
    pg = abre(contexto, pagina)
    arrasta_do_banco(pg, "t", "1", 0.5, 0.5)
    pid = interno(pg, "S.sel.id")
    ax, ay = interno(pg, f"I.alca('{pid}')")
    p = interno(pg, f"I.quadroDoPasso(S.estado, 0, I.centro()).pecas['{pid}']")
    cx, cy = interno(pg, f"I.jogoParaPixel({p['x']}, {p['y']})")
    pg.mouse.move(*no_radar(pg, ax, ay))
    pg.mouse.down()
    pg.mouse.move(*no_radar(pg, cx, cy - 60), steps=8)
    pg.mouse.up()
    (gira,) = [o for o in interno(pg, "S.doc.operacoes") if o["tipo"] == "gira_peca"]
    assert gira["yaw"] == 90
    # sem seleção, a alça (branca com contorno escuro) sai de cima da ponta
    pg.keyboard.press("Escape")
    # a ponta está ACIMA do centro na tela: branco do halo acima, mapa abaixo
    branco = pg.evaluate(f"""() => {{
      const c = document.getElementById('pr-mapa'), k = c.width / Prancheta._interno.radar().width;
      const d = 20 * k, x = {cx} * k, y = {cy} * k, g = c.getContext('2d');
      const px = (yy) => Array.from(g.getImageData(Math.round(x), Math.round(yy), 1, 1).data.slice(0, 3));
      return [px(y - d), px(y + d)];
    }}""")
    assert min(branco[0]) > 225, f"acima do centro devia ser a ponta branca: {branco[0]}"
    assert min(branco[1]) < 225, f"abaixo do centro devia ser o mapa: {branco[1]}"


def test_traco_fica_no_passo_dele(contexto, pagina):
    pg = abre(contexto, pagina)
    pg.click("#pr-novo-passo")
    pg.click('[data-passo="1"]')
    pg.click('#pr-barra [data-ferramenta="caneta"]')
    c = caixa(pg)
    pg.mouse.move(*no_mapa(pg, 0.3, 0.3)); pg.mouse.down()
    for i in range(1, 10):
        pg.mouse.move(*no_mapa(pg, 0.3 + 0.03 * i, 0.3 + 0.01 * i * i / 3), steps=1)
    pg.mouse.up()
    (op,) = [o for o in interno(pg, "S.doc.operacoes") if o["tipo"] == "cria_traco"]
    assert op["passo"] == interno(pg, "S.estado.passos[0].passo")
    assert [d["id"] for d in ultimo(pg, "traco")] == [op["traco"]]
    pg.click('[data-passo="2"]')
    assert ultimo(pg, "traco") == []             # dura_passos 1: só no passo dele
    pg.click('[data-passo="1"]')
    assert len(ultimo(pg, "traco")) == 1


def test_smoke_do_passo_1_aparece_no_passo_3_so_com_a_area(contexto, pagina):
    pg = abre(contexto, pagina)
    pg.click("#pr-novo-passo"); pg.click("#pr-novo-passo")
    pg.click('[data-passo="1"]')
    pg.click('[data-arma="smoke"]'); pg.click('aside [data-ferramenta="granada"]')
    pg.mouse.click(*no_mapa(pg, 0.4, 0.4)); pg.mouse.click(*no_mapa(pg, 0.55, 0.5))
    (g1,) = ultimo(pg, "granada")
    assert g1["linha"] and g1["area"]
    pg.click('[data-passo="3"]')
    (g3,) = ultimo(pg, "granada")
    assert g3["id"] == g1["id"] and g3["area"] and not g3["linha"]


def test_desfazer_e_refazer_voltam_ao_estado_exato_em_cada_operacao(contexto, pagina):
    pg = abre(contexto, pagina)

    def confere(nome, acao):
        solta_foco(pg)
        antes = interno(pg, "S.estado")
        acao()
        solta_foco(pg)
        depois = interno(pg, "S.estado")
        assert depois != antes, f"{nome}: a ação não mudou nada"
        pg.keyboard.press("Control+z")
        assert interno(pg, "S.estado") == antes, f"{nome}: Ctrl+Z não voltou"
        pg.keyboard.press("Control+y")
        assert interno(pg, "S.estado") == depois, f"{nome}: Ctrl+Y não refez"
        pg.keyboard.press("Control+z"); pg.keyboard.press("Control+Shift+z")
        assert interno(pg, "S.estado") == depois, f"{nome}: Ctrl+Shift+Z não refez"

    confere("cria_peca", lambda: arrasta_do_banco(pg, "ct", "2", 0.5, 0.5))
    pid = interno(pg, "Object.keys(S.estado.pecas)[0]")
    interno(pg, f"(S.sel = {{tipo: 'peca', id: '{pid}'}}, 0)")

    def move():
        pg.mouse.move(*no_mapa(pg, 0.5, 0.5)); pg.mouse.down()
        pg.mouse.move(*no_mapa(pg, 0.55, 0.45), steps=5); pg.mouse.up()
    confere("move_peca", move)

    def gira():
        interno(pg, f"(S.sel = {{tipo: 'peca', id: '{pid}'}}, I.reprojeta(), 0)")
        ax, ay = interno(pg, f"I.alca('{pid}')")
        pg.mouse.move(*no_radar(pg, ax, ay)); pg.mouse.down()
        pg.mouse.move(*no_radar(pg, ax + 40, ay + 40), steps=5); pg.mouse.up()
    confere("gira_peca", gira)
    confere("renomeia", lambda: (pg.fill("#pr-titulo", "Outro nome"), pg.press("#pr-titulo", "Tab")))
    confere("cria_passo", lambda: pg.click("#pr-novo-passo"))
    pg.click('[data-passo="1"]')
    confere("renomeia_passo", lambda: (pg.fill("#pr-passo-titulo", "abre"), pg.press("#pr-passo-titulo", "Tab")))
    confere("define_duracao", lambda: (pg.fill("#pr-passo-duracao", "3.5"), pg.press("#pr-passo-duracao", "Tab")))

    def granada():
        pg.click('[data-arma="molotov"]'); pg.click('aside [data-ferramenta="granada"]')
        pg.mouse.click(*no_mapa(pg, 0.3, 0.6)); pg.mouse.click(*no_mapa(pg, 0.35, 0.7))
        pg.click('aside [data-ferramenta="mover"]')
    confere("cria_granada", granada)
    gid = interno(pg, "Object.keys(S.estado.granadas)[0]")
    pg.mouse.click(*no_mapa(pg, 0.35, 0.7))             # seleciona a granada pelo destino
    confere("define_vida", lambda: pg.check("#pr-vida-fim"))

    def move_granada():
        d = interno(pg, f"S.estado.granadas['{gid}'].destino")
        px = interno(pg, f"I.jogoParaPixel({d[0]}, {d[1]})")
        pg.mouse.move(*no_radar(pg, *px)); pg.mouse.down()
        pg.mouse.move(*no_radar(pg, px[0] + 30, px[1] + 10), steps=5); pg.mouse.up()
    confere("move_granada", move_granada)

    def traco():
        pg.click('#pr-barra [data-ferramenta="seta"]')
        pg.mouse.move(*no_mapa(pg, 0.2, 0.2)); pg.mouse.down()
        pg.mouse.move(*no_mapa(pg, 0.3, 0.25), steps=5); pg.mouse.up()
    confere("cria_traco", traco)

    def borracha():
        pg.click('#pr-barra [data-ferramenta="borracha"]')
        pg.mouse.click(*no_mapa(pg, 0.25, 0.225))
    confere("remove_traco", borracha)
    pg.click('aside [data-ferramenta="mover"]')
    interno(pg, f"(S.sel = {{tipo: 'peca', id: '{pid}'}}, 0)")
    pg.click('[data-passo="1"]'); interno(pg, f"(S.sel = {{tipo: 'peca', id: '{pid}'}}, 0)")
    pg.evaluate("() => Prancheta._interno.reprojeta()")
    interno(pg, "(document.getElementById('pr-selecao'), 0)")
    pg.mouse.click(*no_mapa(pg, 0.55, 0.45))            # seleciona a peça pelo clique
    confere("tira_peca", lambda: pg.click("#pr-tira-peca"))
    pg.keyboard.press("Control+z")                       # a peça volta ao mapa neste passo
    pg.mouse.click(*no_mapa(pg, 0.55, 0.45))
    confere("remove_peca (desfazer devolve com histórico)", lambda: pg.click("#pr-apaga-peca"))
    pg.once("dialog", lambda d: d.accept())
    confere("remove_passo", lambda: (pg.click('[data-passo="2"]'), pg.click("#pr-remove-passo")))


def test_tela_cheia_zoom_e_redimensionar_nao_mudam_coordenada_guardada(contexto, pagina):
    pg = abre(contexto, pagina)
    arrasta_do_banco(pg, "ct", "3", 0.45, 0.55)
    pg.click('[data-arma="smoke"]'); pg.click('aside [data-ferramenta="granada"]')
    pg.mouse.click(*no_mapa(pg, 0.45, 0.55)); pg.mouse.click(*no_mapa(pg, 0.6, 0.4))
    antes = interno(pg, "S.doc.operacoes")
    pg.click("#pr-tela-cheia")
    pg.wait_for_function("() => !!document.fullscreenElement")
    pg.wait_for_timeout(200)
    interno(pg, "(I.aplicaZoom(3), 0)")
    pg.keyboard.press("Escape")
    pg.evaluate("() => document.fullscreenElement && document.exitFullscreen()")
    pg.wait_for_function("() => !document.fullscreenElement")
    pg.set_viewport_size({"width": 900, "height": 800})
    pg.wait_for_timeout(200)
    assert interno(pg, "S.doc.operacoes") == antes
    c = caixa(pg)
    assert abs(c["width"] - c["height"]) <= 1


def test_nuke_peca_no_andar_de_baixo_fica_esmaecida_no_de_cima(contexto, tmp_path_factory):
    pg = abre(contexto, pagina_do_mapa(tmp_path_factory, "de_nuke"))
    pg.click('[data-andar="1"]')
    arrasta_do_banco(pg, "ct", "1", 0.5, 0.5)
    (op,) = [o for o in interno(pg, "S.doc.operacoes") if o["tipo"] == "cria_peca"]
    assert op["nivel"] == 1
    assert ultimo(pg, "peca")[0]["alfa"] == 1
    pg.click('[data-andar="0"]')
    assert ultimo(pg, "peca")[0]["alfa"] < 1


def test_vertigo_abre_sem_busca_de_arremesso_e_diz_por_que(contexto, tmp_path_factory):
    pg = abre(contexto, pagina_do_mapa(tmp_path_factory, "de_vertigo"))
    assert pg.locator('aside [data-ferramenta="buscar"]').is_disabled()
    motivo = pg.locator("#pr-sem-biblioteca")
    assert motivo.is_visible() and "não há partidas" in motivo.text_content()


# --- Etapa 3: reprodução --------------------------------------------------------

def _tatica_de_reproducao(pg):
    """Três passos: peça que anda e gira de 350° para 10°, peça que entra, smoke
    que fica, flash de um passo, dois traços no mesmo passo."""
    def op(seq, tipo, **d):
        return {"id": f"r{seq:04d}", "seq": seq, "autor": "pedro", "em": "2026-09-26T00:00:00Z", "tipo": tipo, **d}
    ops = [
        op(1, "renomeia", titulo="Reprodução"),
        op(2, "cria_passo", passo="p1", titulo="posições"), op(3, "cria_passo", passo="p2", titulo="utilidade"),
        op(4, "cria_passo", passo="p3", titulo="entrada"), op(5, "define_duracao", passo="p2", segundos=3.0),
        op(6, "cria_peca", peca="a", lado="t", rotulo="1", passo="p1", x=-1200.0, y=300.0, yaw=350.0),
        op(7, "gira_peca", peca="a", passo="p2", yaw=10.0),
        op(8, "move_peca", peca="a", passo="p3", x=-800.0, y=-100.0),
        op(9, "cria_peca", peca="b", lado="t", rotulo="2", passo="p2", x=-1100.0, y=200.0),
        op(10, "cria_granada", granada="s", arma="smoke", passo="p1", origem=[-1200.0, 300.0], destino=[-700.0, -300.0]),
        op(11, "cria_traco", traco="t1", passo="p2", ferramenta="caneta", cor="#eb6834", espessura=4,
           pontos=[[-900, 0], [-850, -20], [-800, -60], [-760, -110], [-720, -170]]),
        op(12, "cria_traco", traco="t2", passo="p2", ferramenta="seta", cor="#2a78d6", espessura=4,
           pontos=[[-1000, 100], [-700, 100]]),
        op(13, "cria_granada", granada="f", arma="flash", passo="p2", origem=[-1100.0, 200.0], destino=[-900.0, -50.0]),
    ]
    doc = interno(pg, "S.doc")
    doc.update({"id": "reproducao0001", "versao": 2, "contador": 13, "operacoes": ops})
    assert interno(pg, f"I.importaTexto({json.dumps(json.dumps(doc))})") is True
    return doc


def _cena(pg, t):
    return interno(pg, f"I.estadoNoTempo(S.estado, {t}, I.centro())")


def _fins(pg):
    """Instante em que cada passo fica completo (fim do intervalo dele)."""
    lt = interno(pg, "I.linhaDoTempo(S.estado)")
    durs = interno(pg, "S.estado.passos.map(p => p.duracao_s)")
    return [i + d for i, d in zip(lt["inicios"], durs)]


def test_no_fim_de_cada_passo_a_reproducao_e_o_quadro_do_passo(contexto, pagina):
    pg = abre(contexto, pagina)
    _tatica_de_reproducao(pg)
    for k, t in enumerate(_fins(pg)):
        c, q = _cena(pg, t), interno(pg, f"I.quadroDoPasso(S.estado, {k}, I.centro())")
        assert c["indice"] == k
        assert {i: (p["x"], p["y"], p["nivel"], p["yaw"]) for i, p in c["pecas"].items()} == \
               {i: (p["x"], p["y"], p["nivel"], p["yaw"]) for i, p in q["pecas"].items()}, f"passo {k}"
        assert {i: g["linha"] == 1 for i, g in c["granadas"].items()} == \
               {i: g["nasceu_neste_passo"] for i, g in q["granadas"].items()}
        assert {i: tr["pontos"] for i, tr in c["tracos"].items()} == {i: tr["pontos"] for i, tr in q["tracos"].items()}
        assert all(e["alfa"] == 1 for grupo in ("pecas", "granadas", "tracos") for e in c[grupo].values())


def test_no_comeco_as_pecas_ja_estao_no_lugar(contexto, pagina):
    pg = abre(contexto, pagina)
    _tatica_de_reproducao(pg)
    c = _cena(pg, 0)
    assert (c["pecas"]["a"]["x"], c["pecas"]["a"]["y"], c["pecas"]["a"]["yaw"]) == (-1200.0, 300.0, 350.0)
    assert c["granadas"] == {}                    # a smoke do passo 1 ainda vai aparecer


def test_no_meio_da_transicao_de_350_para_10_a_direcao_e_0(contexto, pagina):
    pg = abre(contexto, pagina)
    _tatica_de_reproducao(pg)
    fins = _fins(pg)
    meio = fins[0] + (fins[1] - fins[0]) / 2
    yaw = _cena(pg, meio)["pecas"]["a"]["yaw"]
    assert min(yaw, 360 - yaw) < 1e-9, yaw
    # e nunca passa por 180: o caminho é o curto
    for i in range(1, 20):
        v = _cena(pg, fins[0] + (fins[1] - fins[0]) * i / 20)["pecas"]["a"]["yaw"]
        assert min(v, 360 - v) <= 10 + 1e-9, v


def test_um_traco_so_comeca_depois_que_o_anterior_ficou_completo(contexto, pagina):
    pg = abre(contexto, pagina)
    _tatica_de_reproducao(pg)
    fins = _fins(pg)
    viu_parcial = False
    for i in range(0, 61):
        c = _cena(pg, fins[0] + (fins[1] - fins[0]) * i / 60)
        t1, t2 = c["tracos"].get("t1"), c["tracos"].get("t2")
        if t1 and t1["progresso"] < 1:
            viu_parcial = True
            assert t2 is None, "o segundo traço começou antes do primeiro terminar"
        if t2:
            assert t1 and t1["progresso"] == 1 and len(t1["pontos"]) == 5
    assert viu_parcial, "o primeiro traço não foi riscado aos poucos"


def test_elemento_de_um_passo_criado_no_passo_2_nao_aparece_no_3(contexto, pagina):
    pg = abre(contexto, pagina)
    _tatica_de_reproducao(pg)
    fins = _fins(pg)
    assert "f" in _cena(pg, fins[1])["granadas"]
    meio3 = fins[1] + (fins[2] - fins[1]) / 2
    c = _cena(pg, meio3)
    assert "f" not in c["granadas"] and "t1" not in c["tracos"]
    assert "s" in c["granadas"] and c["granadas"]["s"]["linha"] == 0   # a smoke fica, só a área


def _arredonda(v):
    if isinstance(v, float):
        return round(v, 9)
    if isinstance(v, list):
        return [_arredonda(x) for x in v]
    if isinstance(v, dict):
        return {k: _arredonda(x) for k, x in v.items() if k != "t"}
    return v


def test_arrastar_a_barra_e_tocar_ate_o_mesmo_t_dao_o_mesmo_quadro(contexto, pagina):
    pg = abre(contexto, pagina)
    _tatica_de_reproducao(pg)
    pg.click("#pr-reproduzir")
    pg.click("#pr-velocidade"); pg.click("#pr-velocidade")          # 4x
    pg.wait_for_timeout(700)
    pg.click("#pr-toca")                                           # pausa
    t = interno(pg, "S.reproducao.t")
    tocado = interno(pg, "S.reproducao.cena")
    assert 0 < t < tocado["total"]
    interno(pg, "(I.reproduzAte(0), 0)")
    barra = pg.locator("#pr-tempo")
    barra.evaluate(f"(b, v) => {{ b.value = v; b.dispatchEvent(new Event('input')); }}", str(round(t * 1000)))
    arrastado = interno(pg, "S.reproducao.cena")
    assert _arredonda(arrastado) == _arredonda(_cena(pg, round(t * 1000) / 1000))
    # e o quadro tocado é a função pura naquele t
    assert _arredonda(tocado) == _arredonda(_cena(pg, t))


def test_durante_a_reproducao_nada_e_editavel_e_editar_volta_no_passo(contexto, pagina):
    pg = abre(contexto, pagina)
    _tatica_de_reproducao(pg)
    n = len(interno(pg, "S.doc.operacoes"))
    pg.click("#pr-reproduzir"); pg.click("#pr-toca")
    assert interno(pg, "document.querySelector('aside').hasAttribute('inert')")
    assert not pg.locator("#pr-barra").is_visible() and pg.locator("#pr-player").is_visible()
    pg.mouse.move(*no_mapa(pg, 0.5, 0.5)); pg.mouse.down()
    pg.mouse.move(*no_mapa(pg, 0.6, 0.6), steps=5); pg.mouse.up()
    arrasta_do_banco(pg, "ct", "5", 0.4, 0.4)
    assert len(interno(pg, "S.doc.operacoes")) == n
    fins = _fins(pg)
    interno(pg, f"(I.reproduzAte({fins[0] + 0.5}), 0)")                 # no meio do passo 2
    pg.click("#pr-editar")
    assert interno(pg, "S.reproducao") is None and interno(pg, "S.passo") == 1
    assert not interno(pg, "document.querySelector('aside').hasAttribute('inert')")
    assert pg.locator("#pr-barra").is_visible() and not pg.locator("#pr-player").is_visible()


def test_atalhos_do_replay_na_reproducao(contexto, pagina):
    pg = abre(contexto, pagina)
    _tatica_de_reproducao(pg)
    pg.click("#pr-reproduzir"); pg.click("#pr-toca")
    solta_foco(pg)
    fins = _fins(pg)
    pg.keyboard.press("ArrowRight")
    assert interno(pg, "S.reproducao.t") == fins[0]
    pg.keyboard.press("ArrowRight")
    assert interno(pg, "S.reproducao.t") == fins[1]
    pg.keyboard.press("ArrowLeft")
    assert interno(pg, "S.reproducao.t") == fins[0]
    pg.keyboard.press("]")
    assert interno(pg, "S.reproducao.velocidade") == 2
    pg.keyboard.press("["); pg.keyboard.press("[")
    assert interno(pg, "S.reproducao.velocidade") == 0.5
    pg.keyboard.press(" ")
    assert interno(pg, "S.reproducao.tocando") is True


def test_salvar_recarregar_abrir_pela_lista_e_reproduzir_da_o_mesmo(contexto, pagina):
    pg = abre(contexto, pagina)
    doc = _tatica_de_reproducao(pg)
    instantes = [0, 0.7, 2.0, 3.3, 4.9, 6.5, 7.0]
    antes = [_cena(pg, t) for t in instantes]
    interno(pg, "I.gravaAgora()")
    pg.reload()
    pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
    pg.click("#pr-nova")                                            # outra tática aberta
    pg.select_option("#pr-taticas", doc["id"])                      # abre pela lista
    assert interno(pg, "S.doc.id") == doc["id"]
    pg.click("#pr-reproduzir"); pg.click("#pr-toca")
    depois = []
    for t in instantes:
        interno(pg, f"(I.reproduzAte({t}), 0)")
        depois.append(interno(pg, "S.reproducao.cena"))
    assert depois == antes


# --- Tática a partir de um instante do replay -------------------------------------

def test_tatica_deste_instante_leva_os_jogadores_vivos_do_quadro(navegador, tmp_path_factory):
    from scripts.build_tactics_page import build_html as prancheta
    from scripts.build_web_page import build_html as partida
    pasta = tmp_path_factory.mktemp("instante")
    (pasta / "prancheta_de_mirage.html").write_text(prancheta("de_mirage"), encoding="utf-8")
    (pasta / "match_02.html").write_text(partida("match_02"), encoding="utf-8")
    rep = json.loads((PROJECT_ROOT / "data" / "processed" / "match_02" / "replay.json").read_text(encoding="utf-8"))
    rodada = next(r for r in rep["rounds"] if r["round"] == 6)
    quadro = rodada["frames"] // 2
    esperado = sorted((p["name"], p["side"], p["x"][quadro], p["y"][quadro], p["d"][quadro])
                      for p in rodada["players"] if p["alive"][quadro])
    ctx = navegador.new_context(viewport={"width": 1400, "height": 1000})
    try:
        pg = ctx.new_page()
        pg.goto((pasta / "match_02.html").as_uri())
        pg.locator('[data-tab="replay"]').first.click()
        pg.wait_for_function("() => window.MapAnnotations && MapAnnotations._interno.S.reprojecoes > 0")
        pg.locator("#strip button", has_text="6").first.click()
        pg.evaluate(f"() => {{ const s = document.getElementById('scrub'); s.value = {quadro}; s.dispatchEvent(new Event('input')); }}")
        pg.click("#anot-tatica-instante")
        pg.wait_for_function("() => window.Prancheta && Prancheta._interno.S.estado !== null")
        assert pg.url.endswith("prancheta_de_mirage.html")            # o #instante foi consumido
        pecas = interno(pg, "I.quadroDoPasso(S.estado, 0, I.centro()).pecas")
        obtido = sorted((p["rotulo"], p["lado"], p["x"], p["y"], p["yaw"]) for p in pecas.values())
        assert obtido == esperado and len(obtido) >= 1
        assert "round 6" in interno(pg, "S.estado.titulo")
        assert all(not p["direcao_padrao"] for p in pecas.values())
        # nasce gravada: é uma tática com conteúdo
        assert interno(pg, f"I.armazem().carrega(S.doc.id) !== null")
    finally:
        ctx.close()


def test_instante_com_jogador_invalido_fica_de_fora_com_aviso(contexto, pagina):
    retrato = {"partida": "x", "round": 3, "relogio": "1:20", "jogadores": [
        {"nome": "ok", "lado": "t", "x": -1000.0, "y": 200.0, "yaw": 90, "nivel": 0},
        {"nome": "ruim", "lado": "espectador", "x": 0, "y": 0, "yaw": 0, "nivel": 0},
        {"nome": "andar", "lado": "ct", "x": 0, "y": 0, "yaw": 0, "nivel": 1},   # a Mirage tem um andar
    ]}
    pg = contexto.new_page()
    pg.goto(pagina.as_uri() + "#instante=" + __import__("urllib.parse").parse.quote(json.dumps(retrato)))
    pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
    rotulos = [p["rotulo"] for p in interno(pg, "S.estado.pecas").values()]
    assert rotulos == ["ok"]
    assert "2 jogador(es)" in pg.locator("#pr-aviso").text_content()


def test_instante_ilegivel_abre_tatica_nova_e_avisa(contexto, pagina):
    pg = contexto.new_page()
    pg.goto(pagina.as_uri() + "#instante=%7Bquebrado")
    pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
    assert interno(pg, "Object.keys(S.estado.pecas).length") == 0
    assert "não pôde ser lido" in pg.locator("#pr-aviso").text_content()


def _site_instante(tmp_path_factory, nome="instante2"):
    from scripts.build_tactics_page import build_html as prancheta
    from scripts.build_web_page import build_html as partida
    pasta = tmp_path_factory.mktemp(nome)
    for mapa, mid in (("de_mirage", "match_02"), ("de_nuke", "match_05")):
        (pasta / f"prancheta_{mapa}.html").write_text(prancheta(mapa), encoding="utf-8")
        (pasta / f"{mid}.html").write_text(partida(mid), encoding="utf-8")
    return pasta


def _abre_replay(pg, pasta, mid, rodada, quadro):
    pg.goto((pasta / f"{mid}.html").as_uri())
    pg.locator('[data-tab="replay"]').first.click()
    pg.wait_for_function("() => window.MapAnnotations && MapAnnotations._interno.S.reprojecoes > 0")
    pg.locator("#strip button", has_text=str(rodada)).first.click()
    if quadro is not None:
        pg.evaluate(f"() => {{ const s = document.getElementById('scrub'); s.value = {quadro}; s.dispatchEvent(new Event('input')); }}")


def test_recarregar_a_prancheta_do_instante_nao_duplica_a_tatica(navegador, tmp_path_factory):
    pasta = _site_instante(tmp_path_factory, "recarga")
    ctx = navegador.new_context(viewport={"width": 1400, "height": 1000})
    try:
        pg = ctx.new_page()
        _abre_replay(pg, pasta, "match_02", 6, 40)
        pg.click("#anot-tatica-instante")
        pg.wait_for_function("() => window.Prancheta && Prancheta._interno.S.estado !== null")
        assert "#instante" not in pg.url
        doc = interno(pg, "S.doc.id")
        pg.reload()
        pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
        assert interno(pg, "S.doc.id") == doc
        assert interno(pg, "I.armazem().lista('de_mirage').length") == 1
        pg.go_back()                                     # voltar ao replay e ir de novo não pode reaproveitar o hash
        pg.go_forward()
        pg.wait_for_function("() => window.Prancheta && Prancheta._interno.S.estado !== null")
        assert interno(pg, "I.armazem().lista('de_mirage').length") == 1
    finally:
        ctx.close()


def test_o_relogio_do_titulo_e_o_do_quadro_usado(navegador, tmp_path_factory):
    """Com o replay entre dois quadros (pos fracionário), o título leva o
    relógio do quadro inteiro i0 -- o mesmo de onde saem as peças."""
    pasta = _site_instante(tmp_path_factory, "relogio")
    ctx = navegador.new_context(viewport={"width": 1400, "height": 1000})
    try:
        pg = ctx.new_page()
        _abre_replay(pg, pasta, "match_02", 6, 40)
        solta_foco(pg)                    # com foco num botão o espaço é ignorado (guarda do replay)
        pg.keyboard.press("Space"); pg.wait_for_timeout(900); pg.keyboard.press("Space")   # toca e pausa no meio
        inst = pg.evaluate("() => MapAnnotations._interno.instante()")
        quadro = inst["quadro"]
        assert quadro > 40, "o replay não tocou: o teste não estaria entre dois quadros"
        assert int(pg.evaluate("() => document.getElementById('scrub').value")) == quadro
        pg.evaluate(f"() => {{ const s = document.getElementById('scrub'); s.value = {quadro}; s.dispatchEvent(new Event('input')); }}")
        assert inst["relogio"] == pg.locator("#clock b").text_content()
        assert "4 por segundo" in pg.locator("#anot-tatica-instante").get_attribute("title")
    finally:
        ctx.close()


ELENCO_TESTE = [{"nome": n, "lado": "t"} for n in ("donk", "sh1ro", "zont1x", "magixx", "chopper")] + \
               [{"nome": n, "lado": "ct"} for n in ("ZywOo", "apEX", "flameZ", "mezii", "ropz")]


def _abre_instante(contexto, pagina, retrato):
    import urllib.parse
    pg = contexto.new_page()
    pg.goto(pagina.as_uri() + "#instante=" + urllib.parse.quote(json.dumps(retrato)))
    pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
    return pg


def _retrato_com_um_morto():
    vivos = [dict(j, x=-1200.0 + 60 * i, y=300.0 - 40 * i, yaw=0, nivel=0)
             for i, j in enumerate(ELENCO_TESTE) if j["nome"] != "sh1ro"]
    return {"partida": "match_02", "round": 6, "quadro": 40, "relogio": "1:05",
            "elenco": ELENCO_TESTE, "jogadores": vivos}


def test_o_espelho_valida_a_origem_igual_ao_python(contexto, pagina):
    from metrics.tactics import problemas_da_origem
    casos = [
        {"partida": "match_02", "round": 6, "quadro": 40, "relogio": "1:05", "elenco": ELENCO_TESTE},
        {"partida": "match_02", "round": 0, "quadro": -1, "relogio": 5, "elenco": ELENCO_TESTE},
        {"partida": "m", "round": 6, "quadro": 4, "relogio": "x", "elenco": ELENCO_TESTE + [{"nome": "extra", "lado": "t"}]},
        {"partida": "m", "round": 6, "quadro": 4, "relogio": "x", "elenco": ELENCO_TESTE[:9] + [{"nome": "donk", "lado": "ct"}]},
        {"partida": "m", "round": 6, "quadro": 4, "relogio": "x", "elenco": []},
    ]
    pg = abre(contexto, pagina)
    for c in casos:
        js = interno(pg, f"I.problemasDaOrigem({json.dumps(c)})")
        assert len(js) == len(problemas_da_origem(c)), c


def test_banco_de_tatica_do_replay_mostra_os_jogadores_do_round(contexto, pagina):
    pg = _abre_instante(contexto, pagina, _retrato_com_um_morto())
    assert interno(pg, "S.doc.origem.round") == 6
    fichas = pg.locator(".pr-ficha")
    assert sorted(fichas.nth(i).get_attribute("data-rotulo") for i in range(fichas.count())) == \
           sorted(j["nome"] for j in ELENCO_TESTE)
    assert "no-mapa" in pg.locator('.pr-ficha[data-rotulo="donk"]').get_attribute("class")
    assert "no-mapa" not in pg.locator('.pr-ficha[data-rotulo="sh1ro"]').get_attribute("class")
    n_pecas = interno(pg, "Object.keys(S.estado.pecas).length")

    # arrastar um VIVO move a peça dele, não cria outra
    arrasta_do_banco(pg, "t", "donk", 0.6, 0.6)
    ops = interno(pg, "S.doc.operacoes")
    assert ops[-1]["tipo"] == "move_peca"
    assert interno(pg, "Object.keys(S.estado.pecas).length") == n_pecas
    # arrastar o MORTO cria a peça com o nome dele
    arrasta_do_banco(pg, "t", "sh1ro", 0.4, 0.6)
    ops = interno(pg, "S.doc.operacoes")
    assert ops[-1]["tipo"] == "cria_peca" and ops[-1]["rotulo"] == "sh1ro"
    assert interno(pg, "Object.keys(S.estado.pecas).length") == n_pecas + 1


def test_tatica_que_nao_veio_do_replay_continua_com_o_banco_numerado(contexto, pagina):
    pg = abre(contexto, pagina)
    assert interno(pg, "S.doc.origem === undefined")
    fichas = pg.locator(".pr-ficha")
    assert sorted(fichas.nth(i).get_attribute("data-rotulo") for i in range(fichas.count())) == \
           sorted([str(n) for n in range(1, 6)] * 2)


def test_o_espelho_confere_os_mortos_igual_ao_python(contexto, pagina):
    from metrics.tactics import problemas_da_origem
    base = {"partida": "m", "round": 6, "quadro": 40, "relogio": "1:05", "elenco": ELENCO_TESTE}
    casos = [dict(base, mortos=[{"nome": "donk", "lado": "t", "ordem": 1}]),
             dict(base, mortos=[{"nome": "fantasma", "lado": "t", "ordem": 1}]),
             dict(base, mortos=[{"nome": "donk", "lado": "ct", "ordem": 1}]),
             dict(base, mortos=[{"nome": "donk", "lado": "t", "ordem": 1}, {"nome": "ropz", "lado": "ct", "ordem": 1}]),
             dict(base, mortos="x")]
    pg = abre(contexto, pagina)
    for c in casos:
        assert len(interno(pg, f"I.problemasDaOrigem({json.dumps(c)})")) == len(problemas_da_origem(c)), c


def test_instante_com_mortos_mostra_o_placar_e_a_ordem_das_mortes(navegador, tmp_path_factory):
    """Os mortos não viram peça: vão no placar de vivos do título e na descrição,
    por lado e na ordem das mortes, conferidos contra o replay.json."""
    pasta = _site_instante(tmp_path_factory, "mortos")
    rep = json.loads((PROJECT_ROOT / "data" / "processed" / "match_02" / "replay.json").read_text(encoding="utf-8"))
    rodada, quadro = None, None
    for r in rep["rounds"]:                    # um instante com morto dos dois lados e vivo dos dois
        for q in range(r["frames"]):
            vivos = {s: sum(1 for p in r["players"] if p["side"] == s and p["alive"][q]) for s in ("t", "ct")}
            if 0 < vivos["t"] < 5 and 0 < vivos["ct"] < 5:
                rodada, quadro = r, q
                break
        if rodada:
            break
    assert rodada, "nenhum instante com mortos dos dois lados na match_02"
    primeira = {p["name"]: next(q for q in range(quadro + 1) if not p["alive"][q])
                for p in rodada["players"] if not p["alive"][quadro]}
    ordem = sorted(primeira, key=lambda n: (primeira[n], n))
    lado = {p["name"]: p["side"] for p in rodada["players"]}
    ctx = navegador.new_context(viewport={"width": 1400, "height": 1000})
    try:
        pg = ctx.new_page()
        _abre_replay(pg, pasta, "match_02", rodada["round"], quadro)
        pg.click("#anot-tatica-instante")
        pg.wait_for_function("() => window.Prancheta && Prancheta._interno.S.estado !== null")
        mortos = interno(pg, "S.doc.origem.mortos")
        assert [m["nome"] for m in sorted(mortos, key=lambda m: m["ordem"])] == ordem
        pecas = {p["rotulo"] for p in interno(pg, "S.estado.pecas").values()}
        assert not pecas & set(ordem)                          # morto não vira peça
        titulo = interno(pg, "S.estado.titulo")
        assert titulo.endswith(f"· {vivos['t']}v{vivos['ct']}")
        assert f"round {rodada['round']}" in titulo
        desc = pg.locator("#pr-origem").text_content()
        for s, rot in (("t", "TR"), ("ct", "CT")):
            doLado = [n for n in ordem if lado[n] == s]
            trecho = ", ".join(f"{n} ({ordem.index(n) + 1}ª morte)" for n in doLado)
            assert f"Mortos {rot}: {trecho}." in desc, desc
    finally:
        ctx.close()


def test_espelho_da_origem_desconhecida(contexto, pagina):
    from metrics.tactics import aplica as aplica_py, centro_do_radar, problemas as problemas_py, quadro_do_passo

    def op(seq, tipo, **d):
        return {"id": f"u{seq:04d}", "seq": seq, "autor": "pedro", "em": "x", "tipo": tipo, **d}
    ops = [op(1, "cria_passo", passo="p1", titulo=""), op(2, "cria_passo", passo="p2", titulo=""),
           op(3, "cria_granada", granada="a", arma="molotov", passo="p1", origem=[5.0, 5.0], destino=[5.0, 5.0],
              origem_desconhecida=True),
           op(4, "cria_granada", granada="b", arma="smoke", passo="p1", origem=[6.0, 6.0], destino=[6.0, 6.0],
              origem_desconhecida=True),
           op(5, "move_granada", granada="b", origem=[0.0, 0.0], destino=[6.0, 6.0])]
    pg = abre(contexto, pagina)
    assert interno(pg, f"I.aplica({json.dumps(ops)})") == aplica_py(ops)
    for i in range(2):
        assert interno(pg, f"I.quadroDoPasso(I.aplica({json.dumps(ops)}), {i}, I.centro())") == \
            quadro_do_passo(aplica_py(ops), i, interno(pg, "I.centro()"))
    doc = interno(pg, "S.doc")
    for ruim in (dict(ops[2], destino=[9.0, 9.0]), dict(ops[2], origem_desconhecida="sim")):
        d = dict(doc, operacoes=[ops[0], ruim], contador=3)
        assert bool(interno(pg, f"I.problemas({json.dumps(d)}, 1).length")) == bool(problemas_py(d))
    # o desenho: sem linha no passo em que nasce
    d = dict(doc, id="semorigem0001", operacoes=ops[:3], contador=3, versao=2)
    assert interno(pg, f"I.importaTexto({json.dumps(json.dumps(d))})") is True
    (g,) = ultimo(pg, "granada")
    assert not g["linha"] and g["area"]


def test_instante_com_smoke_ativa_e_granada_no_ar_liga_ao_arremesso(navegador, tmp_path_factory):
    """A tática tem exatamente as granadas ativas do instante, e cada uma com a
    origem LIGADA: o arremesso real da biblioteca, ou a posição da soltura."""
    pasta = _site_instante(tmp_path_factory, "granadas")
    rep = json.loads((PROJECT_ROOT / "data" / "processed" / "match_02" / "replay.json").read_text(encoding="utf-8"))
    bib = {a["id"]: a for a in json.loads((PROJECT_ROOT / "data" / "lineups" / "de_mirage.json")
                                          .read_text(encoding="utf-8"))["arremessos"]}
    achado = None
    for r in rep["rounds"]:
        for q in range(r["frames"]):
            smokes = [z for z in r["smokes"] if z["f0"] <= q <= z["f1"] and z["l"]]
            ativos_ids = {z["l"]["id"] for z in r["smokes"] + r["fires"] if z["f0"] <= q <= z["f1"] and z["l"]}
            no_ar = [n for n in r["nades"] if n["f0"] <= q < n["f0"] + len(n["x"]) - 1 and n["l"]
                     and n["l"]["id"] not in ativos_ids]
            todas_z = [z for z in r["smokes"] + r["fires"] if z["f0"] <= q <= z["f1"]]
            todas_n = [n for n in r["nades"] if n["f0"] <= q < n["f0"] + len(n["x"]) - 1
                       and not (n["l"] and n["l"]["id"] in ativos_ids)]
            if len(smokes) == 1 and len(no_ar) == 1 and len(todas_z) == 1 and len(todas_n) == 1:
                achado = (r, q, smokes[0], no_ar[0])
                break
        if achado:
            break
    assert achado, "nenhum instante com exatamente uma smoke ativa e uma granada no ar"
    r, q, smoke, voo = achado
    ctx = navegador.new_context(viewport={"width": 1400, "height": 1000})
    try:
        pg = ctx.new_page()
        _abre_replay(pg, pasta, "match_02", r["round"], q)
        pg.click("#anot-tatica-instante")
        pg.wait_for_function("() => window.Prancheta && Prancheta._interno.S.estado !== null")
        granadas = list(interno(pg, "S.estado.granadas").values())
        assert len(granadas) == 2
        for alvo in (smoke, voo):
            arma = "smoke" if alvo is smoke else voo["k"]
            if alvo["l"]["id"] in bib:
                (g,) = [g for g in granadas if g["arremesso"] and g["arremesso"]["id"] == alvo["l"]["id"]]
                assert g["origem"] == bib[alvo["l"]["id"]]["origem"][:2]
            else:
                (g,) = [g for g in granadas if g["origem"] == alvo["l"]["o"][:2]]
                assert g["arremesso"] is None
            assert g["arma"] == arma and "origem_desconhecida" not in g
        assert interno(pg, "S.estado.granadas[Object.keys(S.estado.granadas)[0]].passo") == interno(pg, "S.estado.passos[0].passo")
    finally:
        ctx.close()
