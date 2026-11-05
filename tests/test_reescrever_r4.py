"""Reescrever R4 (decisão 59): trocar a granada por um arremesso REAL da biblioteca (mesmo tipo, mesmo lado, voo conhecido, sem decoy), que cai no
instante da original mais o tempo de voo da alternativa, com os estados "Carregando" e de erro. O site não diz o que a troca muda."""
from __future__ import annotations

import json
import math
import re

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_reescrever_modo import (  # noqa: E402,F401  (fixtures e ajudas)
    OBS, PARTIDA, RAIZ, RECT, _abre, _estado, _sai, navegador, pagina)
from tests.test_reescrever_r3 import _arrasta  # noqa: E402

MAPA = "de_mirage"
PRONTA = "() => window.__reescrever().trocas.biblioteca === 'pronta'"


@pytest.fixture(scope="module")
def pagina_com_biblioteca(pagina):
    """A página do teste com `arremessos/<mapa>.js` ao lado, como no site."""
    from scripts.build_tactics_page import arquivo_da_biblioteca, biblioteca_js
    bib = biblioteca_js(MAPA)
    if bib is None:
        pytest.skip("sem a biblioteca do mapa")
    destino = pagina.parent / arquivo_da_biblioteca(MAPA)
    destino.parent.mkdir(exist_ok=True)
    destino.write_text(bib, encoding="utf-8")
    return pagina


@pytest.fixture(scope="module")
def biblioteca():
    return {a["id"]: a for a in json.loads((RAIZ / "data" / "lineups" / f"{MAPA}.json").read_text(encoding="utf-8"))["arremessos"]}


def _granada(pg):
    pg.click("#rw-ferr-granada")
    pg.wait_for_function(PRONTA)


def _troca_a_primeira(pg, tipo="smoke", por=None):
    """Escolhe a primeira granada do `tipo` que tem alternativa, o primeiro grupo, e troca. Devolve o estado das trocas."""
    est = _estado(pg)["trocas"]
    for i, c in enumerate(est["candidatas"]):
        if c["k"] != tipo or (por and c["by"] != por):
            continue
        pg.locator(".rw-gr").nth(i).click()
        if pg.locator(".rw-alt").count():
            pg.locator(".rw-alt").first.click()
            pg.locator('[data-foco="trocar"]').click()
            return _estado(pg)["trocas"]
    raise AssertionError("nenhuma granada com alternativa")


def test_a_biblioteca_so_carrega_ao_usar_a_ferramenta_e_mostra_o_carregando(navegador, pagina_com_biblioteca):
    ctx = navegador.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page(); erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.add_init_script("""(() => { const o = Node.prototype.appendChild; window.__presos = []; window.__segura = true;
        Node.prototype.appendChild = function (n) { if (n && n.tagName === 'SCRIPT' && /arremessos\\//.test(n.src || '') && window.__segura) { window.__presos.push([this, n]); return n; } return o.call(this, n); };
        window.__solta = () => { window.__segura = false; window.__presos.splice(0).forEach(([p, n]) => o.call(p, n)); }; })()""")
    try:
        pg.goto(pagina_com_biblioteca.as_uri() + "#replay")
        pg.wait_for_function("() => window.MapAnnotations && MapAnnotations._interno.S.reprojecoes > 0")
        pg.wait_for_timeout(400)
        pg.locator("#strip .rchip", has_text="23").first.click(); pg.wait_for_timeout(200)
        pg.evaluate("() => { const s = document.getElementById('scrub'); s.value = Math.floor(s.max * 0.35); s.dispatchEvent(new Event('input')); }")
        pg.click("#rw-entrar")
        assert pg.evaluate("window.__presos.length") == 0                                    # antes da ferramenta, nada carrega
        antes = pg.evaluate(RECT)
        pg.click("#rw-ferr-granada"); pg.wait_for_timeout(200)
        assert pg.evaluate("window.__reescrever().trocas.biblioteca") == "carregando"
        assert pg.locator("#rw-granada [role=status]").inner_text() == "Carregando os arremessos reais do mapa…"
        assert pg.locator(".rw-esqueleto span").count() == 3 and pg.locator(".rw-gr").count() == 0
        assert pg.evaluate(RECT) == antes
        pg.evaluate("window.__solta()")
        pg.wait_for_function(PRONTA)
        assert pg.locator(".rw-gr").count() > 0 and pg.locator(".rw-esqueleto").count() == 0
        assert pg.evaluate("typeof window.Prancheta") == "undefined"                         # o apelido que o arquivo chama não fica na página
        assert pg.evaluate(RECT) == antes and erros == []
    finally:
        ctx.close()


def test_se_a_biblioteca_nao_carrega_o_erro_e_o_tentar_de_novo_e_o_resto_continua(navegador, pagina, tmp_path):
    from scripts.build_tactics_page import arquivo_da_biblioteca, biblioteca_js
    arq = tmp_path / pagina.name
    arq.write_text(pagina.read_text(encoding="utf-8"), encoding="utf-8")                    # sem o arquivo ao lado: é a falha de carregar
    ctx, pg, erros = _abre(navegador, arq, 1440, 900)
    try:
        pg.click("#rw-entrar")
        pg.click("#rw-ferr-granada")
        pg.wait_for_function("() => window.__reescrever().trocas.biblioteca === 'erro'")
        assert pg.locator("#rw-granada [role=alert]").inner_text() == "✕ Erro: os arremessos reais não carregaram. A troca de granada fica desligada; o resto do Reescrever continua."
        assert pg.locator(".rw-gr").count() == 0
        pg.click("#rw-ferr-mover")                                                           # o resto continua: arrastar uma peça
        nome = _arrasta(pg)
        assert any(p["editada"] for p in _estado(pg)["pecas"] if p["nome"] == nome)
        pg.click("#rw-ferr-granada")
        destino = arq.parent / arquivo_da_biblioteca(MAPA)
        destino.parent.mkdir(exist_ok=True)
        destino.write_text(biblioteca_js(MAPA), encoding="utf-8")                            # a rede voltou
        pg.click("#rw-gr-tentar")
        pg.wait_for_function(PRONTA)
        assert pg.locator(".rw-gr").count() > 0
        assert pg.evaluate("typeof window.Prancheta") == "undefined"
    finally:
        ctx.close()


def test_mapa_sem_biblioteca_diz_que_a_troca_nao_esta_disponivel(navegador, pagina, tmp_path):
    arq = tmp_path / pagina.name
    texto = pagina.read_text(encoding="utf-8")
    sem = re.sub(r'"biblioteca":\s*"arremessos/[^"]+"', '"biblioteca": null', texto)
    assert sem != texto
    arq.write_text(sem, encoding="utf-8")
    ctx, pg, _ = _abre(navegador, arq, 1440, 900)
    try:
        pg.click("#rw-entrar"); pg.click("#rw-ferr-granada")
        assert "não tem arremessos reais no corpus" in pg.inner_text("#rw-granada")
    finally:
        ctx.close()


def test_as_alternativas_so_do_mesmo_tipo_e_lado_com_voo_conhecido_perto_e_sem_decoy(navegador, pagina_com_biblioteca, biblioteca):
    ctx, pg, _ = _abre(navegador, pagina_com_biblioteca, 1440, 900)
    try:
        pg.click("#rw-entrar"); _granada(pg)
        est = _estado(pg)
        lado = {p["nome"]: p["lado"] for p in est["pecas"]}
        cands = est["trocas"]["candidatas"]
        assert cands and all(c["k"] != "decoy" for c in cands)                               # decoy fora
        assert all(c["f0"] > est["quadro"] for c in cands)                                   # só depois do instante
        vistos = 0
        for i, c in enumerate(cands):
            pg.locator(".rw-gr").nth(i).click()
            grupos = _estado(pg)["trocas"]["grupos"]
            for g in grupos:
                a = biblioteca[g["id"]]
                assert a["arma"] == c["k"] and a["lado"] == lado[c["by"]]                    # mesmo tipo, mesmo lado
                assert a["voo_s"] is not None and (a["arma"] != "molotov" or a["efeito_s"] is not None)   # voo (e efeito do molotov) conhecidos
                assert math.hypot(a["origem"][0] - c["origem"][0], a["origem"][1] - c["origem"][1]) <= 150
                assert g["id"] != c["lid"]                                                  # a própria granada do real não é alternativa
                vistos += 1
            assert [g["n"] for g in grupos] == sorted((g["n"] for g in grupos), reverse=True)   # o grupo com mais arremessos primeiro
        assert vistos > 5
    finally:
        ctx.close()


def test_trocar_liga_o_play_e_a_granada_cai_no_instante_da_original_mais_o_voo(navegador, pagina_com_biblioteca, biblioteca):
    ctx, pg, erros = _abre(navegador, pagina_com_biblioteca, 1440, 900)
    try:
        pg.click("#rw-entrar")
        assert pg.evaluate("document.getElementById('play').disabled")
        _granada(pg)
        tr = _troca_a_primeira(pg)["trocas"][0]
        assert not pg.evaluate("document.getElementById('play').disabled")                   # só a troca já deixa tocar
        assert tr["cai"] == tr["f0"] + max(1, round(biblioteca[tr["alt"]]["voo_s"] * 4))      # o lançamento da original mais o voo da alternativa (o voo anda em quadros de 4 por segundo)
        pg.click("#play"); pg.wait_for_timeout(300); pg.click("#play")
        assert _estado(pg)["sua"]

        def mostra(q):
            pg.evaluate("q => { const s = document.getElementById('scrub'); s.disabled = false; s.value = q; s.dispatchEvent(new Event('input')); }", q)
            return _estado(pg)
        e = mostra(math.floor(tr["f0"]) + 1)
        assert e["soNoReal"] >= 1 and e["trocas"]["virtuais"]["nades"] == 1                  # a original só no real; a trocada em voo
        e = mostra(math.ceil(tr["cai"]) + 1)
        v = e["trocas"]["virtuais"]
        assert v["smokes"] + v["fires"] + v["pops"] == 1                                     # a zona ou o estouro da trocada existe no mapa
        pg.click("#rw-editar"); pg.click("#rw-voltar")                                       # Voltar ao real limpa as trocas
        assert _estado(pg)["trocas"]["trocas"] == [] and pg.evaluate("document.getElementById('play').disabled")
        assert erros == []
    finally:
        ctx.close()


def test_o_que_mudou_diz_a_troca_sem_prometer_nada(navegador, pagina_com_biblioteca):
    ctx, pg, _ = _abre(navegador, pagina_com_biblioteca, 1440, 900)
    try:
        pg.click("#rw-entrar"); _granada(pg); _troca_a_primeira(pg)
        itens = pg.locator("#rw-mudou li").all_inner_texts()
        assert len(itens) == 1
        assert re.match(r"No real, a (smoke|flash|granada HE|molotov) de \S+ das \d:\d\d caiu .+\. Na sua versão, ela cai .+ às \d:\d\d, [\d,]+ s depois de sair da mão", itens[0]), itens[0]
        assert itens[0].endswith("O site não diz o que isso muda nos duelos.")
        painel = pg.inner_text("#squad-t").lower()
        fora = painel.replace("o site não simula o cs2 e não diz quem venceria os duelos", "").replace("não é uma previsão", "")
        assert not re.search(r"ganh|venc|vit[óo]ria|placar|melhor|pior|resultado|prever|previs[ãa]o\b(?!\.)|n[ãa]o morre|sobreviv|salv", fora), fora
    finally:
        ctx.close()


def test_se_quem_lancou_foi_movido_a_troca_nao_vale_e_o_site_diz(navegador, pagina_com_biblioteca):
    ctx, pg, _ = _abre(navegador, pagina_com_biblioteca, 1440, 900)
    try:
        pg.click("#rw-entrar"); _granada(pg)
        by = _troca_a_primeira(pg, por="ZywOo")["trocas"][0]["by"]        # sozinho no meio: o arraste não pega outra peça
        pg.click("#rw-ferr-mover"); _arrasta(pg, by)
        assert not _estado(pg)["trocas"]["trocas"][0]["valida"]
        assert "não vale" in pg.inner_text("#rw-mudou") and "fica só no real" in pg.inner_text("#rw-mudou")
        pg.click("#rw-ferr-granada")
        pg.locator(".rw-gr").filter(has_text=by).first.click()
        assert "foi movido" in pg.inner_text(".rw-gr-det") and pg.locator(".rw-alt").count() == 0    # não oferece troca de quem foi movido
    finally:
        ctx.close()


def test_trocar_a_granada_tambem_pede_confirmacao_ao_sair_e_ao_trocar_de_round(navegador, pagina_com_biblioteca):
    ctx, pg, _ = _abre(navegador, pagina_com_biblioteca, 1440, 900)
    try:
        pg.click("#rw-entrar"); _granada(pg); _troca_a_primeira(pg)
        pg.click("#rw-sair")
        assert pg.evaluate("document.querySelector('.rw-dialogo').open") and "granadas que você trocou" in pg.inner_text(".rw-dialogo")
        pg.click("#rw-continuar")
        pg.locator("#strip .rchip", has_text="22").first.click()
        assert pg.evaluate("document.querySelector('.rw-dialogo').open")                     # trocar de round também pergunta
        pg.click("#rw-descartar")
        assert not _estado(pg)["ativo"]
        pg.click("#rw-entrar")
        assert _estado(pg)["trocas"]["trocas"] == []
    finally:
        ctx.close()


@pytest.mark.parametrize("tam", [(1440, 900), (1366, 657), (375, 812)])
def test_escolher_trocar_e_tocar_nao_mexem_no_mapa_cls_zero_e_a_ferramenta_tem_teclado(navegador, pagina_com_biblioteca, tam):
    ctx, pg, erros = _abre(navegador, pagina_com_biblioteca, *tam)
    try:
        pg.evaluate(OBS)
        antes = pg.evaluate(RECT)
        pg.click("#rw-entrar")
        pg.click("#rw-ferr-granada"); pg.wait_for_function(PRONTA)
        assert pg.evaluate(RECT) == antes
        _troca_a_primeira(pg)
        assert pg.evaluate(RECT) == antes
        assert pg.evaluate("document.activeElement.classList.contains('rw-gr')")              # depois de trocar, o foco volta à lista
        pg.click("#play"); pg.wait_for_timeout(700); pg.click("#play")
        assert pg.evaluate(RECT) == antes
        assert pg.evaluate("window.__cls") == 0 and erros == []
        pg.click("#rw-editar")
        pg.focus("#rw-ferr-granada"); pg.keyboard.press("ArrowLeft")                          # setas no grupo de ferramentas
        assert pg.get_attribute("#rw-ferr-mover", "aria-checked") == "true"
    finally:
        ctx.close()


def test_todo_rotulo_da_troca_vem_do_python_e_existe():
    from leitura.reescrever import TEXTOS_DO_MODO
    js = (RAIZ / "dashboard" / "web" / "partida" / "11-reescrever-granada.js").read_text(encoding="utf-8")
    usados = set(re.findall(r"\bTX\.([a-z_0-9]+)", js)) | set(re.findall(r'TX\["(\w+)"\]', js)) | {"ferr_mover", "ferr_granada"}
    faltam = usados - set(TEXTOS_DO_MODO) - {"smoke_s", "biblioteca"}                        # os dois entram no build (constante do projeto e arquivo da biblioteca)
    assert not faltam, faltam


def test_flash_trocada_vira_um_estouro_sem_efeito_afirmado(navegador, pagina_com_biblioteca):
    ctx, pg, erros = _abre(navegador, pagina_com_biblioteca, 1440, 900)
    try:
        pg.click("#rw-entrar"); _granada(pg)
        tr = _troca_a_primeira(pg, tipo="flash")["trocas"][0]
        pg.click("#play"); pg.wait_for_timeout(200); pg.click("#play")
        pg.evaluate("q => { const s = document.getElementById('scrub'); s.disabled = false; s.value = q; s.dispatchEvent(new Event('input')); }", tr["cai"] + 1)
        assert _estado(pg)["trocas"]["virtuais"]["pops"] == 1
        from leitura.reescrever import TEXTOS_DO_MODO
        assert TEXTOS_DO_MODO["sem_efeito"] == "sem efeito calculado"
        assert erros == []
    finally:
        ctx.close()
