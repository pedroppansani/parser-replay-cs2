"""Comparação de jogadores (fase 7, item 7.3): na partida e na página do corpus."""
from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest

from metrics.agregado_jogadores import encolhe, k_de_encolhimento, linhas_por_partida, para_a_pagina

RAIZ = Path(__file__).resolve().parent.parent
PROCESSED = RAIZ / "data" / "processed"


@pytest.fixture(scope="module")
def pagina():
    if not any(PROCESSED.glob("match_*/player_profile.parquet")):
        pytest.skip("sem o processado")
    return para_a_pagina()


def test_o_agregado_e_por_steamid_e_junta_o_mesmo_jogador_com_nomes_diferentes(pagina):
    nicks = json.loads((RAIZ / "data" / "reference" / "nicks_conhecidos.json").read_text(encoding="utf-8"))
    linhas = linhas_por_partida()
    por_steamid = linhas.group_by("steamid").agg(pl.col("name").n_unique().alias("nomes"), pl.len().alias("partidas"))
    varios = por_steamid.filter(pl.col("nomes") > 1)
    assert varios.height >= 1, "o corpus tem jogadores com mais de um nick (decisão 25)"
    ids = [j["steamid"] for j in pagina["jogadores"]]
    assert len(ids) == len(set(ids)) == por_steamid.height
    for r in varios.iter_rows(named=True):
        j = next(x for x in pagina["jogadores"] if x["steamid"] == str(r["steamid"]))
        assert j["partidas"] == r["partidas"]
    assert nicks  # a tabela de nicks existe; o agrupamento não depende dela


def test_o_encolhimento_puxa_quem_tem_uma_partida_e_quase_nao_mexe_em_quem_tem_vinte(pagina):
    for chave in ("rating", "adr", "kast"):
        k = pagina["k"][chave]
        assert k is not None and 0 < k < 5, (chave, k)
        um = encolhe(2.0, 1.0, 1, k)
        vinte = encolhe(2.0, 1.0, 20, k)
        assert abs(um - 1.0) < 0.5        # menos da metade do caminho: perto da média
        assert abs(vinte - 1.0) > 0.8     # mais de 80% do próprio número
    assert encolhe(2.0, 1.0, 5, None) == 1.0   # sem separação entre jogadores: a média


def test_k_sem_variacao_entre_jogadores_e_none_e_com_variacao_e_finito():
    iguais = pl.DataFrame({"steamid": [1, 1, 2, 2, 3, 3], "x_n": [1.0, 3.0, 3.0, 1.0, 2.0, 2.0],
                           "x_d": [4.0] * 6})
    assert k_de_encolhimento(iguais, "x") is None
    diferentes = pl.DataFrame({"steamid": [1, 1, 2, 2, 3, 3], "x_n": [1.0, 1.1, 2.0, 2.1, 3.0, 3.1],
                               "x_d": [4.0] * 6})
    k = k_de_encolhimento(diferentes, "x")
    assert k is not None and k < 0.1


sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_annotations_browser import abre, contexto, navegador, partida  # noqa: E402,F401  (fixtures)


def test_a_comparacao_na_partida_so_oferece_jogadores_daquela_partida(contexto, partida):
    # resposta 6 do Pedro: "comparar dois" fica na aba Jogadores, não na Perfil
    pg = abre(contexto, partida)
    pg.click('[role=tab][data-tab="jogadores"]')
    nomes = pg.evaluate("() => JSON.parse(document.getElementById('payload').textContent).player_profile.map(p => p.name)")
    for sel in ("#cmp-a", "#cmp-b"):
        opcoes = pg.eval_on_selector_all(sel + " option", "os => os.map(o => o.value).filter(Boolean)")
        assert sorted(opcoes) == sorted(nomes) and len(opcoes) == 10
    url = pg.url
    pg.select_option("#cmp-b", nomes[1])
    tabela = pg.inner_text("#cmp-tabela")
    # as métricas de impacto e as do perfil entram, com o rótulo do Python e a régua do corpus
    assert "Dano por HE" in tabela and "Joga longe do time" in tabela and "régua do corpus" in tabela
    assert "Rating com o time em compra cheia" in tabela
    assert pg.url == url                                   # a seleção é estado da tela
    assert pg.locator("#comparar .pfbarra, #comparar canvas, #comparar svg").count() == 0   # sem faixa
    # a aba Perfil não ganhou as métricas de impacto
    pg.click('[role=tab][data-tab="perfil"]')
    assert "Dano por HE" not in pg.inner_text("#pf-tabela")
    pg.close()


def _pagina_com(navegador, tmp_path, dados):
    from scripts.build_jogadores import TEXTOS, WEB
    from scripts.json_em_script import js
    html = ((WEB / "jogadores.html").read_text(encoding="utf-8")
            .replace("/*__MAP_CORE__*/", (WEB / "map_core.js").read_text(encoding="utf-8"))
            .replace("/*__DADOS__*/null", js(dados)).replace("/*__TEXTOS__*/null", js(TEXTOS)))
    f = tmp_path / "jogadores.html"
    f.write_text(html, encoding="utf-8")
    pg = navegador.new_page(viewport={"width": 1300, "height": 900})
    erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto(f.as_uri())
    return pg, erros


def test_nome_com_codigo_entra_literal_na_pagina_do_corpus(navegador, tmp_path, pagina):
    mau = '<img src=x onerror="window.__x=1">'
    dados = json.loads(json.dumps(pagina))
    dados["jogadores"][0]["nome"] = mau
    dados["jogadores"][0]["funcao"] = "<b>f</b>"
    pg, erros = _pagina_com(navegador, tmp_path, dados)
    assert erros == []
    assert pg.evaluate("() => window.__x") is None and pg.locator("#lista img").count() == 0
    assert mau in pg.inner_text("#lista")
    pg.close()


def test_a_soma_da_pagina_bate_com_a_do_python(navegador, tmp_path, pagina):
    pg, erros = _pagina_com(navegador, tmp_path, pagina)
    assert erros == []
    i = max(range(len(pagina["jogadores"])), key=lambda j: pagina["jogadores"][j]["partidas"])
    col = pagina["chaves"].index("adr")
    js_v = pg.evaluate(f"""() => {{ const I = Jogadores._interno;
        return I.soma(I.D.linhas.filter(r => r[0] === {i}), {col}).v; }}""")
    linhas = [r for r in pagina["linhas"] if r[0] == i]
    py_v = sum(r[4 + col][0] for r in linhas) / sum(r[4 + col][1] for r in linhas)
    assert js_v == pytest.approx(py_v)
    pg.close()


def test_filtros_de_lado_e_mapa_e_ate_tres_jogadores(navegador, tmp_path, pagina):
    pg, erros = _pagina_com(navegador, tmp_path, pagina)
    todas = pg.locator(".metrica").count()
    pg.select_option("#lado", "ct")
    so_ct = pg.locator(".metrica").count()
    com_lado = sum(1 for m in pagina["metricas"] if m["lado"])
    assert so_ct == com_lado < todas
    assert all(c.endswith("_ct") for c in pg.eval_on_selector_all(".metrica", "e => e.map(x => x.dataset.chave)"))
    pg.select_option("#lado", "")
    pg.select_option("#mapa", "0")
    assert pg.locator(".metrica").count() == todas
    for cb in pg.locator("#lista input[type=checkbox]").all()[:4]:
        if not cb.is_checked():
            cb.check()
    assert len(pg.evaluate("Jogadores._interno.selecionados()")) == 3
    assert erros == []
    pg.close()
