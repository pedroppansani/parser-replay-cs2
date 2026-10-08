"""O cabeçalho da partida (design-B1): nome dos lados, linha do decisor, título único, rodapé "Limites",
arredondamento do empate e as abas (Resumo primeiro, hash, setas, "›")."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
PROCESSED = RAIZ / "data" / "processed"


def _partidas() -> list[str]:
    return sorted(p.name for p in PROCESSED.glob("match_*") if (p / "web_payload.json").exists())


def test_o_nome_do_lado_faceit_e_o_primeiro_nick_em_ordem_alfabetica_sem_caixa():
    from metrics.times import nome_do_lado_faceit
    assert nome_do_lado_faceit(["rol1ng-", "Z_o_R_o", "donk666", "_AmadeuS", "t1ltedbot"]) == "Time de _AmadeuS"
    assert nome_do_lado_faceit(["xhx", "KREEDZ666", "HLEB", "9amaterasu9", "s-chilla"]) == "Time de 9amaterasu9"
    # maiúscula e minúscula do mesmo nick: a caixa não decide, a ordem do código desempata
    assert nome_do_lado_faceit(["bob", "Bob", "zed"]) == "Time de Bob"
    assert nome_do_lado_faceit(["Zed", "adam", "Bea"]) == "Time de adam"
    assert nome_do_lado_faceit([]) == ""


def test_o_nome_nao_depende_da_ordem_em_que_os_nicks_chegam():
    from metrics.times import nome_do_lado_faceit
    nicks = ["gamma", "Alpha", "beta", "delta", "Echo"]
    assert {nome_do_lado_faceit(nicks[i:] + nicks[:i]) for i in range(5)} == {"Time de Alpha"}


def test_nenhum_lado_se_chama_time_a_ou_time_b():
    from scripts.build_web_page import cabecalho_da_partida
    for m in _partidas():
        c = cabecalho_da_partida(m)
        assert c, m
        for lado in c["lados"].values():
            assert not re.search(r"\bTime [AB]\b", lado["nome"]), (m, lado)
            assert lado["nome"].strip(), m


def test_os_nomes_sao_os_mesmos_em_duas_execucoes_com_hash_diferente():
    """`PYTHONHASHSEED` muda a ordem de qualquer set/dict por hash; o nome do lado não pode depender dela."""
    codigo = ("import json;from scripts.build_web_page import cabecalho_da_partida as c, titulo_da_pagina as t;"
              "import sys;ids=sys.argv[1:];print(json.dumps({i:[c(i)['lados'],t(i)] for i in ids},sort_keys=True,ensure_ascii=False))")
    ids = _partidas()
    if not ids:
        pytest.skip("sem o processado")
    saidas = []
    for semente in ("1", "4242"):
        r = subprocess.run([sys.executable, "-c", codigo, *ids], cwd=RAIZ, capture_output=True, encoding="utf-8",
                           env={**os.environ, "PYTHONHASHSEED": semente, "PYTHONIOENCODING": "utf-8"})
        assert r.returncode == 0, r.stderr[-400:]
        saidas.append(r.stdout)
    assert saidas[0] == saidas[1]


def test_o_nome_so_muda_a_exibicao_e_os_agregados_por_time_continuam_nos_mesmos_ids():
    """Os identificadores internos (A/B) e os rosters do payload não são tocados pelo nome do lado."""
    from scripts.build_web_page import com_os_nomes_dos_lados, cabecalho_da_partida
    for m in _partidas()[:6]:
        texto = (PROCESSED / m / "web_payload.json").read_text(encoding="utf-8")
        antes, depois = json.loads(texto), json.loads(com_os_nomes_dos_lados(texto, cabecalho_da_partida(m)))
        narr_antes, narr_depois = antes.pop("narrative"), depois.pop("narrative")
        assert antes == depois, m                      # tudo fora da narrativa, idêntico (números, rosters, ids)
        assert set(narr_antes) == set(narr_depois)
        # nenhum número da frase muda: só o nome entra no lugar de "Time A"/"Time B"
        nomes = [lado["nome"] for lado in cabecalho_da_partida(m)["lados"].values()]
        for k in narr_antes:
            if narr_antes[k] is None:
                continue
            sem_nome = narr_depois[k]
            for nome in sorted(nomes, key=len, reverse=True):
                sem_nome = sem_nome.replace(nome, "")
            numeros = lambda s: re.findall(r"\d+(?:,\d+)?", s)  # noqa: E731
            assert numeros(re.sub(r"Time [AB]", "", narr_antes[k])) == numeros(sem_nome), (m, k)


def test_a_linha_do_decisor():
    from leitura.narrativa import linha_do_decisor
    assert linha_do_decisor(24, "m0NESY") == "Decidida no round 24 · MVP m0NESY"
    assert linha_do_decisor(None, "m0NESY") == "Nenhum round decidiu sozinho · MVP m0NESY"
    assert linha_do_decisor(7, None) == "Decidida no round 7"


def test_o_criterio_do_empate_nao_diz_o_mesmo_numero_arredondado_duas_vezes():
    from leitura.narrativa import criterio_do_decisivo
    resumo = {"decisivo": {"round": 15, "wpa_abs": 0.1231}, "empate_no_topo": True,
              "top": [{"round": 15, "wpa_abs": 0.1231}, {"round": 16, "wpa_abs": 0.1201}]}
    frase = criterio_do_decisivo(resumo)
    assert "12% contra 12%" not in frase
    assert "12,0% contra 12,3%" in frase
    # quando arredondam diferente, continua inteiro
    resumo["top"][1]["wpa_abs"] = 0.08
    assert "(8% contra 12%)" in criterio_do_decisivo(resumo)


def test_nenhuma_narrativa_do_corpus_repete_o_percentual_do_empate():
    for m in _partidas():
        criterio = json.loads((PROCESSED / m / "web_payload.json").read_text(encoding="utf-8"))["narrative"]["criterion"]
        # percentual inteiro repetido ("12% contra 12%") é o defeito; com uma casa ("15,6% contra 15,6%") os
        # dois rounds empatam de verdade e a frase diz isso
        for a, b in re.findall(r"\((\d+(?:,\d)?)% contra (\d+(?:,\d)?)%\)", criterio):
            assert a != b or "," in a, (m, criterio)


def test_o_titulo_e_unico_por_partida_e_traz_placar_mapa_e_o_site():
    from scripts.build_web_page import titulo_da_pagina
    titulos = {m: titulo_da_pagina(m) for m in _partidas()}
    assert len(set(titulos.values())) == len(titulos), [t for t in titulos.values() if list(titulos.values()).count(t) > 1]
    for t in titulos.values():
        assert t.endswith(" · Parser de Replay CS2") and " × " in t, t


def test_a_descricao_diz_quem_venceu_onde_e_em_que_round():
    from scripts.build_web_page import cabecalho_da_partida, descricao_da_pagina
    d = descricao_da_pagina("match_02")
    c = cabecalho_da_partida("match_02")
    v = c["lados"][c["venceu"]]["nome"]
    assert d.startswith(f"{v} venceu ") and " em Mirage (FACEIT)." in d and f"Decidida no round {c['round_decisivo']}." in d


def test_o_rodape_limites_bate_com_o_numeros_citaveis():
    from scripts.build_web_page import rodape_html
    from scripts.numeros_citaveis import carrega
    c = carrega()
    rodape = rodape_html(c)
    po = c["corpus"]["por_origem"]
    assert f"{po['profissional']} profissionais e {po['faceit']} da FACEIT" in rodape
    assert "nível profissional" not in rodape


# ------------------------------------------------------------------ no navegador
sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_tactics_browser import navegador  # noqa: E402,F401  (fixture)


@pytest.fixture(scope="module")
def pagina_html(tmp_path_factory):
    from scripts.build_web_page import build_html
    if not (PROCESSED / "match_02" / "web_payload.json").exists():
        pytest.skip("sem o processado da match_02")
    arq = tmp_path_factory.mktemp("cab") / "match_02.html"
    arq.write_text(build_html("match_02"), encoding="utf-8")
    return arq


def _abre(navegador, arq, largura=1300, hash_=""):
    ctx = navegador.new_context(viewport={"width": largura, "height": 900})
    pg = ctx.new_page()
    erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto(arq.as_uri() + hash_)
    pg.wait_for_selector("[role=tab][data-tab]")
    pg._erros = erros
    return ctx, pg


def test_o_h1_e_o_placar_com_venceu_e_a_etiqueta_comecou(navegador, pagina_html):
    ctx, pg = _abre(navegador, pagina_html)
    try:
        assert pg.locator("h1").count() == 1
        lados = pg.locator("h1 .lado")
        assert lados.count() == 2
        assert pg.locator("h1 .tag-venceu").count() == 1                   # só o vencedor leva "venceu"
        assert pg.locator("h1 .lado.venceu .tag-venceu").count() == 1
        etiquetas = pg.eval_on_selector_all("h1 .tag.comecou", "els => els.map(e => e.textContent)")
        assert sorted(etiquetas) == ["começou CT", "começou TR"]
        # o lado do nome tem o nome inteiro em `title` (o texto trunca no celular)
        for i in range(2):
            nome = lados.nth(i).locator(".nome")
            assert nome.get_attribute("title") == nome.text_content()
        # sem borda colorida no placar: a cor de lado é só a etiqueta
        assert pg.eval_on_selector("h1 .lado", "e => getComputedStyle(e).borderLeftWidth") == "0px"
        assert re.fullmatch(r"Decidida no round \d+ · MVP .+|Nenhum round decidiu sozinho · MVP .+", pg.inner_text("#decisor"))
        assert "parser próprio" not in pg.inner_text(".crumbs")
        assert pg._erros == []
    finally:
        ctx.close()


def test_o_resumo_abre_primeiro_e_o_hash_abre_a_aba_pedida(navegador, pagina_html):
    ctx, pg = _abre(navegador, pagina_html)
    try:
        assert pg.eval_on_selector_all("[role=tab]", "els => els.map(e => e.textContent)") == [
            "Resumo", "Replay", "Jogadores", "Placar", "Perfil", "Estilos"]
        assert pg.get_attribute('[data-tab="insights"]', "aria-selected") == "true"
        assert not pg.is_hidden('[data-panel="insights"]') and pg.is_hidden('[data-panel="replay"]')
        pg.click('[data-tab="jogadores"]')
        assert pg.evaluate("() => location.hash") == "#jogadores"
    finally:
        ctx.close()
    for hash_, aba in (("#replay", "replay"), ("#placar", "rounds"), ("#estilos", "estilos"), ("#nada", "insights")):
        ctx, pg = _abre(navegador, pagina_html, hash_=hash_)
        try:
            assert pg.get_attribute(f'[data-tab="{aba}"]', "aria-selected") == "true", hash_
            assert not pg.is_hidden(f'[data-panel="{aba}"]'), hash_
            assert pg._erros == []
        finally:
            ctx.close()


def test_no_celular_o_botao_mais_aparece_rola_as_abas_e_some_no_fim(navegador, pagina_html):
    ctx, pg = _abre(navegador, pagina_html, largura=375)
    try:
        mais = pg.locator("#abas-mais")
        assert pg.eval_on_selector("#abas-moldura", "e => e.classList.contains('sobra-dir')")
        assert mais.is_visible()
        caixa = mais.bounding_box()
        assert caixa["width"] >= 44 and caixa["height"] >= 44
        antes = pg.evaluate("() => document.querySelector('.tabs').scrollLeft")
        for _ in range(4):
            if not mais.is_visible():
                break
            mais.click()
            pg.wait_for_timeout(450)
        assert pg.evaluate("() => document.querySelector('.tabs').scrollLeft") > antes
        assert not mais.is_visible() and pg.eval_on_selector("#abas-moldura", "e => e.classList.contains('sobra-esq')")
        assert pg.evaluate("() => document.documentElement.scrollWidth") <= 375
    finally:
        ctx.close()
    ctx, pg = _abre(navegador, pagina_html, largura=1300)
    try:
        assert not pg.locator("#abas-mais").is_visible()                      # em tela larga cabem as seis
    finally:
        ctx.close()
