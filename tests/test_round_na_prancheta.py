"""O round inteiro na prancheta (fase 9): modelo em Python e o caminho replay -> prancheta."""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

import pytest

from metrics.round_na_prancheta import (TOLERANCIA_U, caminho_do_jogador, douglas_peucker, payload_do_round,
                                        posicao_no_caminho)

RAIZ = Path(__file__).resolve().parents[1]
PROCESSED = RAIZ / "data" / "processed"
LIMITE_HASH_BYTES = 150 * 1024


def _replay(mid):
    return json.loads((PROCESSED / mid / "replay.json").read_text(encoding="utf-8"))


def test_douglas_peucker_no_tempo_limita_o_erro_no_horario():
    rnd = random.Random(20261005)
    x = y = 0.0
    pontos = []
    for t in range(400):
        if rnd.random() < 0.2:                       # parado de vez em quando
            pass
        else:
            x += rnd.uniform(-40, 60)
            y += rnd.uniform(-50, 50)
        pontos.append((t, x, y))
    pontos += [(400 + k, x - 30 * k, y) for k in range(10)] + [(410 + k, x - 300 + 30 * k, y) for k in range(10)]
    for tol in (2, 8, 32):
        ficam = douglas_peucker(pontos, tol)
        simples = [[pontos[i][0], pontos[i][1], pontos[i][2], 0, 0] for i in ficam]
        assert ficam[0] == 0 and ficam[-1] == len(pontos) - 1
        pior = max(math.hypot(*(a - b for a, b in zip(posicao_no_caminho(simples, t), (px, py))))
                   for t, px, py in pontos)
        assert pior <= tol + 1e-9
    # o vaivém na mesma reta não some (a versão só espacial apagaria a volta)
    assert len(douglas_peucker(pontos[-20:], 8)) >= 3


def test_morte_e_troca_de_andar_viram_ponto():
    p = {"x": [0, 10, 20, 30, 40, 50], "y": [0] * 6, "d": [0] * 6, "alive": [1, 1, 1, 1, 0, 0], "lv": [0, 0, 1, 1, 1, 1]}
    pontos, morte = caminho_do_jogador(p, 100)
    assert morte == 4 and [q[0] for q in pontos] == [0, 1, 2, 3]   # a troca de andar entre 1 e 2 fica
    assert caminho_do_jogador({**p, "alive": [1] * 6}, 100)[1] is None


def test_o_maior_round_do_corpus_cabe_no_hash():
    import zlib
    maior = 0
    for f in sorted(PROCESSED.glob("*/replay.json")):
        rep = json.loads(f.read_text(encoding="utf-8"))
        for rd in rep["rounds"]:
            bruto = json.dumps(payload_do_round(rep, rd, TOLERANCIA_U, f.parent.name), ensure_ascii=False,
                               separators=(",", ":")).encode("utf-8")
            maior = max(maior, math.ceil(len(zlib.compress(bruto, 6)) * 4 / 3))
    assert 0 < maior <= LIMITE_HASH_BYTES


# --- navegador -------------------------------------------------------------------

pytest.importorskip("playwright.sync_api")
from tests.test_tactics_browser import _abre_replay, _site_instante, interno, navegador  # noqa: E402,F401


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    return _site_instante(tmp_path_factory, "round")


def _abre_round(navegador, site, mid="match_02", rodada=6, quadro=40):
    ctx = navegador.new_context(viewport={"width": 1400, "height": 1000})
    pg = ctx.new_page()
    pg._erros = []
    pg.on("pageerror", lambda e: pg._erros.append(str(e)))
    _abre_replay(pg, site, mid, rodada, quadro)
    pg.click("#anot-toggle")
    pg.click("#anot-abrir-round")
    pg.wait_for_function("() => window.Prancheta && Prancheta._interno.S.doc && Prancheta._interno.S.doc.origem"
                         " && Prancheta._interno.S.doc.origem.base_real")
    return ctx, pg


def test_o_payload_do_navegador_e_o_do_python(navegador, site):
    ctx = navegador.new_context()
    try:
        pg = ctx.new_page()
        pg.goto((site / "match_02.html").as_uri())
        rep = _replay("match_02")
        for rd in rep["rounds"][:6]:
            js = pg.evaluate(f"""() => {{ const R = JSON.parse(document.getElementById('replay').textContent);
                const rd = R.rounds.find(r => r.round === {rd['round']});
                return MapCore.roundParaPrancheta(R.sample_hz, rd, {TOLERANCIA_U}, 'match_02'); }}""")
            assert js == json.loads(json.dumps(payload_do_round(rep, rd, TOLERANCIA_U, "match_02")))
    finally:
        ctx.close()


def test_abrir_poe_o_cabecote_no_instante_e_as_pecas_no_lugar_do_replay(navegador, site):
    ctx, pg = _abre_round(navegador, site)
    try:
        assert pg.locator("#anot-abrir-round").count() == 0 and "#round" not in pg.url
        assert interno(pg, "S.t") == 10.0                              # quadro 40 a 4 por segundo
        rd = next(r for r in _replay("match_02")["rounds"] if r["round"] == 6)
        quadro = interno(pg, "I.quadroNoTempo(S.e3, S.t, I.centro())")
        por_nome = {p["rotulo"]: p for p in quadro["pecas"].values()}
        vivos = {p["name"] for p in rd["players"] if p["alive"][40]}
        assert set(por_nome) == vivos
        for p in rd["players"]:
            if p["name"] in vivos:
                q = por_nome[p["name"]]
                assert math.hypot(q["x"] - p["x"][40], q["y"] - p["y"][40]) <= TOLERANCIA_U
        assert "round 6" in interno(pg, "S.estado.titulo")
        # função do replay, banco com os nomes reais
        assert any(p["funcao"] for p in interno(pg, "S.e3.pecas").values())
        assert pg.locator("#pr-funcoes-banco select[data-do-replay]").count() >= 1
        assert "(do replay)" in pg.text_content("#pr-funcoes-banco")
        assert not pg._erros
    finally:
        ctx.close()


def test_reproduzir_mortes_e_granadas_nos_horarios_do_replay(navegador, site):
    ctx, pg = _abre_round(navegador, site)
    try:
        rd = next(r for r in _replay("match_02")["rounds"] if r["round"] == 6)
        e3 = interno(pg, "S.e3")
        por_nome = {p["rotulo"]: p for p in e3["pecas"].values()}
        for p in rd["players"]:
            if all(p["alive"]):
                continue
            morte = p["alive"].index(0) / 4
            pts = [pt for pt in por_nome[p["name"]]["pontos"] if pt.get("morte")]
            assert len(pts) == 1 and abs(pts[0]["t"] - morte) <= 0.25
            antes = interno(pg, f"I.quadroNoTempo(S.e3, {morte - 0.25}, I.centro()).pecas")
            depois = interno(pg, f"I.quadroNoTempo(S.e3, {morte}, I.centro())")
            assert any(q["rotulo"] == p["name"] for q in antes.values())
            assert not any(q["rotulo"] == p["name"] for q in depois["pecas"].values())
            assert any(m["rotulo"] == p["name"] for m in depois["mortos"].values())
        reais = sorted((g["k"], g["f0"] / 4, g["x"][-1], g["y"][-1]) for g in rd["nades"] if g.get("x"))
        obtidas = sorted((g["arma"], g["t"], g["destino"][0], g["destino"][1]) for g in e3["granadas"].values())
        assert obtidas == reais
        # tocando: no relógio, do primeiro evento em diante
        pg.click("#pr-reproduzir")
        assert interno(pg, "S.reproducao.modo") == "relogio"
    finally:
        ctx.close()


def _arrasta_peca(pg, pid, dx, dy):
    q = interno(pg, f"I.quadroNoTempo(S.e3, S.t, I.centro()).pecas['{pid}']")
    px = interno(pg, f"I.jogoParaPixel({q['x']}, {q['y']})")
    c = pg.locator("#pr-mapa").bounding_box()
    w = interno(pg, "I.radar().width")
    x, y = c["x"] + px[0] * c["width"] / w, c["y"] + px[1] * c["height"] / w
    pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(x + dx, y + dy, steps=6); pg.mouse.up()


def test_editar_em_t_mantem_o_real_antes_de_t_e_os_outros_jogadores(navegador, site):
    ctx, pg = _abre_round(navegador, site)
    try:
        pg.locator("#pr-mapa").scroll_into_view_if_needed()
        pid = sorted(interno(pg, "Object.keys(I.quadroNoTempo(S.e3, S.t, I.centro()).pecas)"))[0]
        _arrasta_peca(pg, pid, 50, -30)
        assert interno(pg, "S.pilhaDesfazer.length") == 1                   # uma ação só
        horarios = [i * 0.5 for i in range(0, 120)]
        real = interno(pg, f"{json.dumps(horarios)}.map(t => I.quadroNoTempo(I.e3Real(), t, I.centro()).pecas)")
        agora = interno(pg, f"{json.dumps(horarios)}.map(t => I.quadroNoTempo(S.e3, t, I.centro()).pecas)")
        # 6 casas: a âncora divide o trecho e a interpolação pode diferir no último bit
        from tests.test_tactics_tempo import _arredonda
        real, agora = _arredonda(real), _arredonda(agora)
        mudou = False
        for t, a, b in zip(horarios, real, agora):
            for k in set(a) | set(b):
                if k != pid or t < 10.0:
                    assert a.get(k) == b.get(k), (t, k)
                elif a.get(k) != b.get(k):
                    mudou = True
        assert mudou
        # depois de t, o jogador editado não tem mais ponto real
        assert interno(pg, f"I.cortaReal('{pid}', 10)") == []
    finally:
        ctx.close()


def test_fantasma_aparece_e_some_e_voltar_ao_real_devolve_o_round(navegador, site):
    ctx, pg = _abre_round(navegador, site)
    try:
        assert pg.locator("#pr-real").is_visible()
        original = interno(pg, "S.e3")
        pg.locator("#pr-mapa").scroll_into_view_if_needed()
        pid = sorted(interno(pg, "Object.keys(I.quadroNoTempo(S.e3, S.t, I.centro()).pecas)"))[0]
        _arrasta_peca(pg, pid, 60, 20)
        interno(pg, "(I.defineTempo(14), 0)")
        assert interno(pg, "S.e3") != original
        pg.locator("#pr-fantasma").scroll_into_view_if_needed()
        pg.click("#pr-fantasma")
        assert interno(pg, "S.ultimoFantasma.n") > 0 and pg.get_attribute("#pr-fantasma", "aria-pressed") == "true"
        pg.click("#pr-fantasma")
        assert interno(pg, "S.ultimoFantasma") is None
        pg.click("#pr-volta-real")
        assert interno(pg, "S.e3") == original
        assert json.dumps(interno(pg, "S.e3"), sort_keys=True) == json.dumps(interno(pg, "I.e3Real()"), sort_keys=True)
        interno(pg, "I.refaz()")                                            # refazer devolve a edição
        assert interno(pg, "S.e3") != original
    finally:
        ctx.close()


def test_recarregar_nao_cria_outra_tatica(navegador, site):
    ctx, pg = _abre_round(navegador, site)
    try:
        doc = interno(pg, "S.doc.id")
        pg.reload()
        pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
        assert interno(pg, "S.doc.id") == doc
        assert interno(pg, "I.armazem().lista('de_mirage').length") == 1
    finally:
        ctx.close()


def test_nome_com_codigo_continua_literal(navegador, site):
    ctx = navegador.new_context(viewport={"width": 1400, "height": 1000})
    try:
        pg = ctx.new_page()
        pg.goto((site / "prancheta_de_mirage.html").as_uri())
        pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
        nome = '<img src=x onerror="window.__pwn=1">'
        r = {"partida": "x", "round": 2, "hz": 4,
             "instante": {"quadro": 4, "relogio": "1:54", "mortos": []},
             "jogadores": [{"nome": nome, "lado": "t", "pontos": [[0, -1200, 300, 90, 0], [8, -1000, 100, 90, 0]],
                            "morte": None}],
             "granadas": [], "bomba": None, "funcoes": {}}
        texto = pg.evaluate(f"() => MapCore.compactaParaUrl({json.dumps(r)})")
        pg.close()
        pg = ctx.new_page()                       # carga nova: só trocar o hash não reabre a página
        pg.goto((site / "prancheta_de_mirage.html").as_uri() + "#round=" + texto)
        pg.wait_for_function("() => Prancheta._interno.S.doc && Prancheta._interno.S.doc.origem")
        assert pg.evaluate("() => window.__pwn") is None
        assert pg.locator("aside img").count() == 0 and pg.locator("#pr-linha img").count() == 0
        # o rótulo da peça vai até 32 caracteres (como no instante), literal
        assert nome[:32] in pg.text_content("#pr-roteiro")
        assert interno(pg, "Object.values(S.estado.pecas)[0].rotulo") == nome[:32]
    finally:
        ctx.close()


def test_espelho_do_round_aberto_e_da_origem(navegador, site):
    from metrics.tactics import estado_no_tempo, linha_do_tempo, problemas, problemas_da_origem
    from tests.test_tactics_tempo import _arredonda
    ctx, pg = _abre_round(navegador, site)
    try:
        doc = interno(pg, "S.doc")
        centro = interno(pg, "I.centro()")
        py = linha_do_tempo(doc["operacoes"], centro)
        assert _arredonda(interno(pg, "I.taticaNoTempo(S.doc.operacoes)")) == _arredonda(py)
        for t in (0.0, 10.0, 23.5, 40.0, 55.0):
            js = interno(pg, f"I.quadroNoTempo(I.taticaNoTempo(S.doc.operacoes), {t}, I.centro())")
            assert _arredonda(js) == _arredonda(estado_no_tempo(py, t, centro)), t
        assert problemas(doc) == [] and interno(pg, "I.problemas(S.doc, 1)") == []
        o = doc["origem"]
        for ruim in ({**o, "base_real": 0}, {**o, "base_real": "7"}, o):
            assert bool(problemas_da_origem(ruim)) == bool(interno(pg, f"I.problemasDaOrigem({json.dumps(ruim)})"))
        assert problemas_da_origem({**o, "base_real": 0})
    finally:
        ctx.close()
