"""Resumo e Jogadores da direção "Sala de demo" (design-B3): card do MVP com o erro típico em texto, tabela
reordenada com "começou", grupos fechados com o destaque na linha e lembrados no navegador, comparar com o
rating, "Mira" explicada, dado degradado sem número e a página funcionando sem localStorage."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
TEMPLATE = (RAIZ / "dashboard" / "web" / "template.html").read_text(encoding="utf-8")
PARTIDA = "match_02"


def test_nenhum_numero_de_erro_do_rating_escrito_no_template():
    """O erro típico vem do numeros_citaveis.json pelo build (decisão 37); o template não traz o número."""
    assert not re.search(r"0[,.]0(79|788|77)\b", TEMPLATE)
    assert "PAGINA.erro_rating" in TEMPLATE


def test_o_erro_do_rating_da_pagina_e_o_da_validacao_fora_da_amostra():
    from scripts.build_web_page import dados_da_pagina
    from scripts.numeros_citaveis import carrega
    d = dados_da_pagina(PARTIDA)
    esperado = carrega()["rating"]["fora_da_amostra"]["erro_medio"]
    assert d["erro_rating"] == f"{esperado:.3f}".replace(".", ",")
    assert d["metodo_rating"].endswith("README.md#como-sei-que-os-números-estão-certos")
    readme = (RAIZ / "README.md").read_text(encoding="utf-8")
    assert "## Como sei que os números estão certos" in readme       # a âncora do "método" existe


def test_a_classe_do_evento_da_linha_do_tempo_nao_e_reaproveitada():
    """Regra herdada da auditoria (item 3): `.ev` só na linha do tempo; o card de estilo usa `.pc-ev`."""
    js = TEMPLATE[TEMPLATE.index("</style>"):]
    usos = re.findall(r"class='([^']*\bev\b[^']*)'|className = \"([^\"]*\bev\b[^\"]*)\"", js)
    assert usos, "a linha do tempo usa .ev"
    assert "pc-ev" in TEMPLATE
    # nenhum elemento do card de estilo (classe "pc...") leva também a classe "ev" (o hífen não separa classe)
    for valor in re.findall(r"class='([^']*)'", js):
        tokens = valor.split()
        if any(tk.startswith("pc") for tk in tokens):
            assert "ev" not in tokens, valor


def test_resumo_de_cada_grupo_e_frase_pronta_do_python():
    from metrics.impacto import ABERTOS_POR_PADRAO, resumo_dos_grupos
    assert ABERTOS_POR_PADRAO == set()                                 # todos fechados por padrão
    perfil = json.loads((RAIZ / "data" / "processed" / PARTIDA / "web_payload.json").read_text(encoding="utf-8"))["player_profile"]
    r = resumo_dos_grupos(perfil)
    assert set(r) == {"Utilidade", "Trocas", "Economia", "Situações"}
    assert r["Utilidade"].startswith("mais cegueira imposta: ")
    assert resumo_dos_grupos(perfil, ["sem equipamento no round 3"])["Economia"].startswith("▲ degradado")
    sem_equip = [{k: v for k, v in linha.items() if not k.startswith("rating_")} for linha in perfil]
    assert resumo_dos_grupos(sem_equip)["Economia"] == "sem dado de equipamento nesta partida"
    # estável: a mesma entrada em outra ordem dá a mesma frase (desempate pelo nome)
    assert resumo_dos_grupos(list(reversed(perfil))) == r


# ------------------------------------------------------------------ no navegador
sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_tactics_browser import navegador  # noqa: E402,F401  (fixture)


@pytest.fixture(scope="module")
def pagina_html(tmp_path_factory):
    from scripts.build_web_page import build_html
    if not (RAIZ / "data" / "processed" / PARTIDA / "web_payload.json").exists():
        pytest.skip("sem o processado")
    arq = tmp_path_factory.mktemp("b3") / f"{PARTIDA}.html"
    arq.write_text(build_html(PARTIDA), encoding="utf-8")
    return arq


def _abre(navegador, arq, w=1300, h=900, hash_="", bloqueia_armazenamento=False, ctx=None):
    ctx = ctx or navegador.new_context(viewport={"width": w, "height": h})
    if bloqueia_armazenamento:
        ctx.add_init_script("""Object.defineProperty(window, 'localStorage', { get() { throw new Error('bloqueado'); } });""")
    pg = ctx.new_page()
    erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto(arq.as_uri() + hash_)
    pg.wait_for_selector("[role=tab][data-tab]")
    pg.wait_for_timeout(300)
    pg._erros = erros
    return ctx, pg


def test_o_card_do_mvp_tem_o_rating_e_o_erro_em_texto_sem_faixa(navegador, pagina_html):
    from scripts.build_web_page import dados_da_pagina
    ctx, pg = _abre(navegador, pagina_html)
    try:
        card = pg.locator("#fig-mvp")
        assert card.locator(".rt-num").inner_text() == "1,73"
        erro = card.locator(".rt-erro").inner_text()
        assert f"erro típico contra o rating oficial: {dados_da_pagina(PARTIDA)['erro_rating']}" in erro and "método" in erro
        assert card.locator("svg circle").count() == 0                  # sem anel/faixa em volta do rating
        assert "2º maior rating: donk666, 1,50" in card.inner_text()
        assert pg._erros == []
    finally:
        ctx.close()


def test_a_tabela_tem_a_ordem_nova_a_coluna_fixa_e_a_etiqueta_comecou(navegador, pagina_html):
    ctx, pg = _abre(navegador, pagina_html, hash_="#jogadores")
    try:
        cab = pg.eval_on_selector_all(".tabela-jog thead th", "els => els.map(e => e.textContent.trim())")
        assert cab[:7] == ["Jogador", "Rating*", "ADR", "KAST", "K", "A", "M"]
        assert pg.eval_on_selector(".tabela-jog tbody th", "e => getComputedStyle(e).position") == "sticky"
        linhas = pg.locator(".tabela-jog tbody tr")
        assert linhas.count() == 10
        etiquetas = pg.eval_on_selector_all(".tabela-jog tbody .tag.comecou", "els => els.map(e => e.textContent)")
        assert len(etiquetas) == 10 and set(etiquetas) == {"começou CT", "começou TR"}
        # a mira explicada: title no cabeçalho e a mesma frase na legenda da tabela
        dica = pg.evaluate("() => JSON.parse(document.getElementById('payload').textContent).dica_mira")
        assert pg.get_attribute(".tabela-jog thead th[title]:last-child", "title") == dica
        assert pg.inner_text("#legenda-mira") == "Mira: " + dica
        # ordenar por kills: o primeiro passa a ser quem tem mais kills; alvo de 44 px
        botao = pg.locator(".tabela-jog thead button[data-ordem='k']")
        caixa = botao.bounding_box()
        assert caixa["width"] >= 44 and caixa["height"] >= 44
        botao.click()
        ks = pg.eval_on_selector_all(".tabela-jog tbody tr td:nth-of-type(4)", "els => els.map(e => +e.textContent)")
        assert ks == sorted(ks, reverse=True)
    finally:
        ctx.close()


def test_grupos_abrem_fechados_com_o_destaque_na_linha_e_sao_lembrados(navegador, pagina_html):
    from scripts.build_web_page import dados_da_pagina
    resumos = dados_da_pagina(PARTIDA)["resumo_dos_grupos"]
    ctx = navegador.new_context(viewport={"width": 1300, "height": 900})
    try:
        _, pg = _abre(navegador, pagina_html, hash_="#jogadores", ctx=ctx)
        grupos = pg.locator("details.imp-grupo")
        assert grupos.count() == 4
        assert pg.eval_on_selector_all("details.imp-grupo", "els => els.filter(d => d.open).length") == 0
        for nome, frase in resumos.items():
            linha = pg.locator(f"details.imp-grupo[data-grupo='{nome}'] > summary").inner_text()
            assert nome in linha and frase in linha, (nome, linha)
        pg.locator("details.imp-grupo[data-grupo='Trocas'] > summary").click()
        # o evento toggle é assíncrono: espera a gravação antes de fechar a página
        pg.wait_for_function("() => (localStorage.getItem('parser-cs2:grupos-jogadores') || '').includes('Trocas')")
        pg.close()
        # outra visita, mesmo navegador: o grupo aberto continua aberto
        _, pg = _abre(navegador, pagina_html, hash_="#jogadores", ctx=ctx)
        abertos = pg.eval_on_selector_all("details.imp-grupo", "els => els.filter(d => d.open).map(d => d.dataset.grupo)")
        assert abertos == ["Trocas"]
    finally:
        ctx.close()


def test_a_pagina_funciona_com_o_armazenamento_bloqueado(navegador, pagina_html):
    ctx, pg = _abre(navegador, pagina_html, hash_="#jogadores", bloqueia_armazenamento=True)
    try:
        assert pg.locator("details.imp-grupo").count() == 4
        assert pg.eval_on_selector_all("details.imp-grupo", "els => els.filter(d => d.open).length") == 0
        pg.locator("details.imp-grupo[data-grupo='Utilidade'] > summary").click()
        assert pg.eval_on_selector("details.imp-grupo[data-grupo='Utilidade']", "d => d.open")
        for aba in ("insights", "replay", "rounds", "perfil", "estilos"):
            pg.click(f'[data-tab="{aba}"]')
        assert pg.locator(".tabela-jog tbody tr").count() == 10
        assert pg._erros == [], pg._erros                                # nenhuma exceção de JS na página toda
    finally:
        ctx.close()


def test_comparar_mostra_o_rating_com_o_erro_tipico_e_sem_faixa(navegador, pagina_html):
    ctx, pg = _abre(navegador, pagina_html, hash_="#jogadores")
    try:
        texto = pg.inner_text("#cmp-tabela")
        assert "erro típico contra o rating oficial" in texto
        assert pg.locator("#cmp-tabela td[data-chave='rating']").count() == 2
        assert pg.locator("#comparar svg, #comparar canvas, #comparar .bar").count() == 0
    finally:
        ctx.close()


def test_com_o_rating_degradado_o_card_nao_mostra_numero_e_diz_degradado(navegador, tmp_path):
    from scripts.build_web_page import build_html
    orig = RAIZ / "data" / "processed" / "match_23"
    if not (orig / "web_payload.json").exists():
        pytest.skip("sem o processado da match_23")
    base = tmp_path / "dados"
    base.mkdir()
    for arq in ("replay.json", "breakdown.json", "match_meta.json"):
        (base / arq).write_text((orig / arq).read_text(encoding="utf-8"), encoding="utf-8")
    payload = json.loads((orig / "web_payload.json").read_text(encoding="utf-8"))
    motivo = "Rating não mostrado nesta partida: economia estimada só nesta partida."
    payload["rating_info"] = {**payload["rating_info"], "modo_degradado": ["x"], "texto_degradado": motivo}
    (base / "web_payload.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    pagina = tmp_path / "p.html"
    pagina.write_text(build_html("match_23", base=base), encoding="utf-8")
    ctx, pg = _abre(navegador, pagina)
    try:
        card = pg.inner_text("#fig-mvp")
        assert "▲ degradado" in card and motivo in card
        assert not re.search(r"\d", card.replace(motivo, "")), card     # nenhum valor numérico no cartão
        pg.click('[data-tab="jogadores"]')
        assert "▲ degradado" in pg.inner_text("details.imp-grupo[data-grupo='Economia'] > summary")
        assert "erro típico" not in pg.inner_text("#cmp-tabela")
    finally:
        ctx.close()


def test_a_frase_do_vice_compara_a_diferenca_dos_ratings_com_o_erro_tipico():
    """`margem` do card é a margem de ruído; a frase usa a DIFERENÇA entre MVP e vice."""
    from scripts.build_web_page import _vice_dentro_do_erro
    c = {"rating": {"fora_da_amostra": {"erro_medio": 0.0788}}}
    assert _vice_dentro_do_erro({"rating": 1.20, "vice_rating": 1.15, "margem": 0.0788}, c) is True
    assert _vice_dentro_do_erro({"rating": 1.73, "vice_rating": 1.50, "margem": 0.0788}, c) is False
    assert _vice_dentro_do_erro({"rating": 1.0, "vice_rating": None}, c) is False
    assert _vice_dentro_do_erro(None, c) is False
