"""Fase 11 na prancheta: a granada DESENHADA (operação `desenha_granada` do log), separada da granada com horário.
Testes 2 a 7 do prompt: linha do tempo e roteiro intactos, "Converter em granada com horário", atalhos 1 a 4,
o fluxo só pelo teclado, o espelho JS <-> Python e o anel tracejado contra os radares."""
from __future__ import annotations

import json

import pytest

from metrics.tactics import IDENTIFICADOR, aplica as aplica_py, problemas as problemas_py


def _op(seq, tipo, autor="pedro", **d):
    return {"id": f"d{seq:04d}{autor}", "seq": seq, "autor": autor, "em": "2026-10-13T00:00:00Z", "tipo": tipo, **d}


OPS = [
    _op(1, "renomeia", titulo="Desenho"), _op(2, "cria_passo", passo="p1", titulo="a"),
    _op(3, "cria_passo", passo="p2", titulo="b"),
    _op(4, "cria_peca", peca="a", lado="t", rotulo="1", passo="p1", x=-500.0, y=-600.0),
    _op(5, "desenha_granada", traco="g1", passo="p1", arma="smoke", x=-300.0, y=-400.0),
    _op(6, "desenha_granada", traco="g2", passo="p2", arma="molotov", x=10.5, y=20.0, nivel=0, dura_passos=None, area=True),
    _op(7, "define_area_desenho", traco="g1", area=True),
    _op(8, "desenha_granada", traco="g3", passo="p1", arma="flash", x=1.0, y=2.0),
    _op(9, "remove_traco", traco="g3"),
    _op(10, "define_vida", alvo="g1", dura_passos=2),
    _op(11, "desenha_granada", traco="g4", passo="p2", arma="he", x=5.0, y=5.0),
    _op(12, "anula", alvo="d0011pedro"),
]


def _doc(ops):
    return {"formato": IDENTIFICADOR, "versao": 3, "id": "desenho00001", "mapa": "de_mirage", "criada_por": "pedro",
            "criada_em": "2026-10-13T00:00:00Z", "contador": len(ops), "operacoes": ops, "calibracao": None}


# ------------------------------------------------------------------ Python
def test_o_log_materializa_a_granada_desenhada_na_camada_de_desenho():
    e = aplica_py(OPS)
    assert set(e["tracos"]) == {"g1", "g2"}
    g1 = e["tracos"]["g1"]
    assert g1["ferramenta"] == "granada" and g1["arma"] == "smoke" and g1["area"] is True
    assert g1["pontos"] == [[-300.0, -400.0]] and g1["dura_passos"] == 2
    assert e["tracos"]["g2"]["dura_passos"] is None and e["tracos"]["g2"]["area"] is True
    assert e["granadas"] == {}                                        # não é granada com horário


def test_validacao_da_operacao_nova():
    assert problemas_py(_doc(OPS)) == []
    ruins = OPS + [_op(13, "desenha_granada", traco="g9", passo="p1", arma="decoy", x=0.0, y=0.0),
                   _op(14, "desenha_granada", traco="g8", passo="p1", arma="smoke", x="a", y=0.0, area="sim"),
                   _op(15, "define_area_desenho", traco="g1", area=1)]
    erros = problemas_py(_doc(ruins))
    assert any("tipo de granada desenhada desconhecido: decoy" in p for p in erros)
    assert any("x e y precisam ser números" in p for p in erros)
    assert sum("área precisa ser verdadeiro ou falso" in p for p in erros) == 2


# ------------------------------------------------------------------ anel tracejado x radares (teste 7)
def test_anel_tracejado_passa_de_3_para_1_em_todo_radar():
    from scripts.design.mede_anel_tracejado import MINIMO, mede
    linhas = mede()
    assert len(linhas) >= 10
    piores = {l["andar"]: round(l["mesmo_passo"], 2) for l in linhas if l["mesmo_passo"] < MINIMO}
    assert not piores, piores


def test_o_tracejado_vale_para_os_dois_aneis_no_mesmo_passo():
    """O critério acima só vale se halo e contorno seguem o MESMO tracejado (no vão, nenhum dos dois)."""
    from pathlib import Path
    js = (Path(__file__).resolve().parent.parent / "dashboard" / "web" / "map_core.js").read_text(encoding="utf-8")
    corpo = js[js.index("function anelDoGlifo"):js.index("function discoComAnel")]
    assert corpo.count("setLineDash") == 1 and corpo.index("setLineDash") < corpo.index("ctx.stroke()")


# ------------------------------------------------------------------ navegador
sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_tactics_browser import (abre, clica, contexto, interno, navegador,  # noqa: E402,F401
                                        no_mapa, pagina)
from tests.test_prancheta_tempo_browser import _tatica_no_tempo  # noqa: E402


def test_espelho_js_python_com_a_granada_desenhada(contexto, pagina):
    """Teste 6: o mesmo log dá o mesmo estado e o mesmo quadro nos dois."""
    from metrics.tactics import centro_do_radar, ordem_de_criacao, quadro_do_passo
    pg = abre(contexto, pagina)
    e_js = interno(pg, f"I.aplica({json.dumps(OPS)})")
    e_py = aplica_py(OPS)
    assert e_js == e_py
    radar = interno(pg, "(({width, height, scale_px_per_unit, origin_x, origin_y}) => ({width, height, scale_px_per_unit, origin_x, origin_y}))(I.radar())")
    centro = centro_do_radar(radar)
    for i in range(len(e_py["passos"])):
        assert interno(pg, f"I.quadroDoPasso(I.aplica({json.dumps(OPS)}), {i}, I.centro())") == quadro_do_passo(e_py, i, centro)
    assert interno(pg, f"I.ordemDeCriacao(I.aplica({json.dumps(OPS)}))") == ordem_de_criacao(e_py)
    ruins = OPS + [_op(13, "desenha_granada", traco="g9", passo="p1", arma="decoy", x=0.0, y=0.0),
                   _op(14, "define_area_desenho", traco="g1", area=1)]
    for doc in (_doc(OPS), _doc(ruins)):
        assert sorted(interno(pg, f"I.problemas({json.dumps(doc)})")) == sorted(problemas_py(doc))
    pg.close()


def _granadas_desenhadas(pg):
    return interno(pg, "Object.keys(S.estado.tracos).filter(k => S.estado.tracos[k].ferramenta === 'granada')"
                       ".map(k => Object.assign({id: k}, S.estado.tracos[k]))")


def test_flash_desenhada_nao_mexe_na_linha_do_tempo_nem_no_roteiro(contexto, pagina):
    """Teste 2."""
    pg = abre(contexto, pagina)
    try:
        _tatica_no_tempo(pg)
        pg.wait_for_timeout(150)
        linha, roteiro = pg.inner_html("#pr-linha"), interno(pg, "JSON.stringify(I.eventosDe(S.e3))")
        granadas = interno(pg, "Object.keys(S.estado.granadas)")
        pg.click('#pr-barra [data-ferramenta="granada_desenho"]')
        pg.click('#pr-contexto-granada [data-arma-desenho="flash"]')
        pg.mouse.click(*no_mapa(pg, 0.3, 0.3))
        gs = _granadas_desenhadas(pg)
        assert len(gs) == 1 and gs[0]["arma"] == "flash"
        assert interno(pg, "S.doc.operacoes[S.doc.operacoes.length - 1].tipo") == "desenha_granada"
        pg.wait_for_timeout(150)
        assert interno(pg, "Object.keys(S.estado.granadas)") == granadas
        assert interno(pg, "JSON.stringify(I.eventosDe(S.e3))") == roteiro
        assert pg.inner_html("#pr-linha") == linha
        assert not pg._erros
    finally:
        pg.close()


def test_converter_em_granada_com_horario_e_um_desfazer(contexto, pagina):
    """Teste 3: uma granada, t = cabeçote, arremessador = o selecionado, destino = o ponto; um Ctrl+Z volta."""
    pg = abre(contexto, pagina)
    try:
        _tatica_no_tempo(pg)
        interno(pg, "I.defineTempo(3)")
        interno(pg, "(S.sel = {tipo: 'peca', id: 'a'}, 0)")
        pg.click('#pr-barra [data-ferramenta="granada_desenho"]')   # atualizaTudo: o painel lembra o jogador
        pg.keyboard.press("3")                                         # HE desenhada
        pg.mouse.click(*no_mapa(pg, 0.6, 0.4))
        g = _granadas_desenhadas(pg)[0]
        assert g["arma"] == "he"
        antes = interno(pg, "Object.keys(S.estado.granadas).sort()")
        clica(pg, "#pr-converte-desenho")
        depois = interno(pg, "S.e3.granadas")                 # o modelo no tempo: jogador e horário resolvidos
        novas = [k for k in depois if k not in antes]
        assert len(novas) == 1
        n = depois[novas[0]]
        assert n["arma"] == "he" and n["jogador"] == "a" and n["t"] == 3 and n["destino"] == g["pontos"][0]
        assert _granadas_desenhadas(pg) == []
        pg.keyboard.press("Control+z")
        assert sorted(interno(pg, "Object.keys(S.estado.granadas)")) == antes
        assert [x["id"] for x in _granadas_desenhadas(pg)] == [g["id"]]
        assert not pg._erros
    finally:
        pg.close()


def test_atalho_1_com_o_pincel_escolhe_a_smoke_desenhada_e_sem_ele_arma_a_smoke(contexto, pagina):
    """Teste 4."""
    pg = abre(contexto, pagina)
    try:
        pg.click('#pr-barra [data-ferramenta="granada_desenho"]')
        pg.keyboard.press("2")
        pg.keyboard.press("1")
        assert interno(pg, "S.armaDesenho") == "smoke" and interno(pg, "S.ferramenta") == "granada_desenho"
        assert interno(pg, "S.acao") is None                           # não armou a granada com horário
        pg.keyboard.press("v")
        pg.keyboard.press("1")
        assert interno(pg, "S.acao && S.acao.arma") == "smoke"          # como antes: arma a smoke com horário
        # o "?" mostra os dois usos
        acoes = [a["acao"] for a in interno(pg, "I.ATALHOS")]
        assert "Com o pincel Granada (desenho): escolhem o tipo da granada desenhada" in acoes
        assert "Smoke" in acoes
    finally:
        pg.close()


def test_fluxo_so_pelo_teclado(contexto, pagina):
    """Teste 5: G liga o pincel, 4 escolhe a molotov, as setas andam o cursor, Enter carimba, Delete apaga."""
    pg = abre(contexto, pagina)
    try:
        pg.locator("body").focus()
        pg.keyboard.press("g")
        assert interno(pg, "S.ferramenta") == "granada_desenho"
        pg.keyboard.press("4")
        pg.keyboard.press("ArrowRight")
        pg.keyboard.press("Shift+ArrowDown")
        pg.keyboard.press("Enter")
        gs = _granadas_desenhadas(pg)
        assert len(gs) == 1 and gs[0]["arma"] == "molotov"
        cx, cy = interno(pg, "[I.radar().width / 2, I.radar().height / 2]")
        esperado = interno(pg, f"I.pixelParaJogo({cx} + 8, {cy} + 32)")
        assert [round(v, 3) for v in gs[0]["pontos"][0]] == [round(v, 3) for v in esperado]
        assert interno(pg, "S.sel && S.sel.tipo") == "traco"
        pg.keyboard.press("Delete")
        assert _granadas_desenhadas(pg) == []
        assert not pg._erros
    finally:
        pg.close()
