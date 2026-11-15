"""PC1: o dado e a busca do caminho das peças pelo mapa (decisões 69 e 70). Nada muda na tela: nenhuma página pede o grafo ainda (PC2).

O que se prova: o dado derivado da malha tem a origem e o crédito e nunca o `.nav`; o grafo não atravessa parede nem inventa o sentido contrário de uma queda; o erro do tempo pelo caminho contra o tempo real da C3 é
o da PC0 (cerca de 10% na Mirage) e bem melhor que o da reta; os 4 exemplos da PC0 dão os mesmos tempos; o JS faz o mesmo que o Python e uma consulta com a CPU 4 vezes mais lenta fica abaixo de 50 ms."""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

import pytest

from scripts.caminhos.avalia import avalia, pares_do_mapa
from scripts.caminhos.busca import PASSO_DO_FIO_U, VELOCIDADE_U_S, Caminhos
from scripts.caminhos.corpus import SALTO_MAX_U

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "data" / "caminhos"
MALHA = PASTA / "malha"
MAPAS = sorted(f.stem for f in PASTA.glob("*.json"))
COM_TEMPO = ["de_mirage", "de_dust2", "de_nuke", "de_inferno", "de_anubis", "de_ancient"]


def _dados(mapa: str) -> dict:
    return json.loads((PASTA / f"{mapa}.json").read_text(encoding="utf-8"))


def _arestas(d: dict) -> list[tuple[int, int]]:
    e, ant, saida = d["e"], 0, []
    for k in range(0, len(e), 2):
        ant += e[k]
        saida.append((ant, e[k + 1]))
    return saida


def test_ha_o_grafo_dos_dez_mapas_e_a_malha_derivada_dos_dez():
    esperados = {"de_ancient", "de_anubis", "de_cache", "de_dust2", "de_inferno", "de_mirage", "de_nuke", "de_overpass", "de_train", "de_vertigo"}
    assert esperados <= set(MAPAS) and esperados <= {f.stem for f in MALHA.glob("*.json")}


@pytest.mark.parametrize("mapa", sorted(f.stem for f in MALHA.glob("*.json")))
def test_a_malha_derivada_diz_de_onde_veio_com_o_credito_e_nunca_traz_o_nav(mapa):
    m = json.loads((MALHA / f"{mapa}.json").read_text(encoding="utf-8"))
    o = m["origem"]
    assert o["nav_versao"] >= 30 and len(o["sha256"]) == 64 and o["awpy"] and m["gerado_em"]      # a versão do `.nav`, o sha256 dele e a data
    assert "Valve" in m["credito"] and "não comercial" in m["credito"] and "não tem ligação" in m["credito"]      # o crédito da decisão 69 (como o dos radares)
    n = len(m["areas"]["id"])
    assert len(m["areas"]["poli"]) == n and all(len(q) % 3 == 0 and len(q) >= 9 for q in m["areas"]["poli"])
    assert all(0 <= v < n for v in m["lig"]) and len(m["lig"]) % 2 == 0
    assert not list(RAIZ.rglob("*.nav")), "o `.nav` original nunca entra no repositório (decisão 69)"


@pytest.mark.parametrize("mapa", MAPAS)
def test_o_formato_do_grafo_fecha(mapa):
    d = _dados(mapa)
    n = d["nc"] + d["na"]
    assert len(d["p"]) == 3 * n and len(d["poli"]) == d["na"] and d["versao"] == 1 and d["celula_u"] == 64
    arestas = _arestas(d)
    assert arestas == sorted(arestas) and all(0 <= a < n and 0 <= b < n and a != b for a, b in arestas)
    assert "Valve" in d["credito"] or d["na"] == 0


@pytest.mark.parametrize("mapa", MAPAS)
def test_o_grafo_nao_inventa_o_sentido_contrario_entre_as_areas_nem_atravessa_o_andar_pelo_corpus(mapa):
    d = _dados(mapa)
    nc = d["nc"]
    entre_areas = {(a - nc, b - nc) for a, b in _arestas(d) if a >= nc and b >= nc}
    m = json.loads((MALHA / f"{mapa}.json").read_text(encoding="utf-8"))
    lig = m["lig"]
    assert entre_areas == {(lig[k], lig[k + 1]) for k in range(0, len(lig), 2)}      # as ligações entre áreas são EXATAMENTE as da malha: nenhum sentido a mais
    p = d["p"]
    corpus = [(a, b) for a, b in _arestas(d) if a < nc and b < nc]
    inversas = {(b, a) for a, b in corpus}
    quedas = [(a, b) for a, b in corpus if p[3 * b + 2] - p[3 * a + 2] <= -100]
    assert all(q not in inversas for q in quedas)      # uma queda do corpus só existe no sentido em que foi feita
    if d["andar_z"] is not None:      # mapa de dois andares: o corpus não cruza o andar (entre andares a malha vem primeiro)
        assert not any((p[3 * a + 2] < d["andar_z"]) != (p[3 * b + 2] < d["andar_z"]) for a, b in corpus)
    assert all(math.dist(p[3 * a:3 * a + 3], p[3 * b:3 * b + 3]) < 2 * SALTO_MAX_U for a, b in corpus)      # cada ligação do corpus é um passo de verdade (entre amostras seguidas)


METADE_DO_JOGADOR_U = 16.0      # o jogador tem 32 u de largura: cortar a quina entre duas áreas ligadas, a até meia largura da área, não é atravessar parede


def _dist_ao_poligono(poli, x, y) -> float:
    melhor = math.inf
    for k in range(len(poli)):
        ax, ay = poli[k]
        bx, by = poli[(k + 1) % len(poli)]
        vx, vy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((x - ax) * vx + (y - ay) * vy) / ((vx * vx + vy * vy) or 1.0)))
        melhor = min(melhor, math.hypot(x - (ax + t * vx), y - (ay + t * vy)))
    return melhor


def _perto_de_uma_area(g, x: float, y: float) -> bool:
    """O ponto está dentro de alguma área da malha (de TODAS), ou a meia largura do jogador de uma."""
    cand = set()
    for ax in range(int(x // 128) - 1, int(x // 128) + 2):
        for ay in range(int(y // 128) - 1, int(y // 128) + 2):
            cand.update(g._grade_a.get((ax, ay), []))
    return any(g._contem(i, x, y) or _dist_ao_poligono(g.poli[i], x, y) <= METADE_DO_JOGADOR_U for i in cand)


def _amostra(mapa: str, n: int = 120):
    pares, nos, zs = pares_do_mapa(mapa)
    rnd = random.Random(3)
    ok = [(a, b) for a, b, *_ in pares if a in nos and b in nos]
    return [((*nos[a], zs.get(a)), (*nos[b], zs.get(b))) for a, b in rnd.sample(ok, min(n, len(ok)))]


@pytest.mark.parametrize("mapa", ["de_mirage", "de_nuke", "de_dust2"])
def test_nenhum_trecho_do_caminho_atravessa_parede_e_a_queda_so_desce(mapa):
    d = _dados(mapa)
    g = Caminhos(d)
    nc = d["nc"]
    adj = {a: set() for a in range(nc + d["na"])}
    for a, b in _arestas(d):
        adj[a].add(b)
    todas = [(c, g.poli[a]) for a, c in enumerate(g.poli)]      # os polígonos de TODAS as áreas, não só os da rota: a prova é independente da busca
    for p, q in _amostra(mapa):
        r = g.caminho(p, q)
        assert r is not None
        nos = r["nos"]
        assert all(nos[k + 1] in adj[nos[k]] for k in range(len(nos) - 1))      # cada passo da rota é uma ligação que existe (e na direção em que existe)
        pts = r["pontos"]
        for k in range(1, len(pts) - 2):      # os trechos de dentro (as pontas ligam o ponto do Pedro ao primeiro nó)
            a, b = pts[k], pts[k + 1]
            nav = any(math.dist(a[:2], (g.px[n], g.py[n])) < 1e-6 and n >= nc for n in nos) and any(math.dist(b[:2], (g.px[n], g.py[n])) < 1e-6 and n >= nc for n in nos)
            if not nav:      # corpus: de um centro a outro de células ligadas (um passo de verdade)
                assert math.dist(a, b) < 2 * SALTO_MAX_U
                continue
            m = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) // PASSO_DO_FIO_U))      # malha: a reta toda dentro de alguma área que existe (ou a meia largura do jogador de uma)
            for s in range(m + 1):
                x, y = a[0] + (b[0] - a[0]) * s / m, a[1] + (b[1] - a[1]) * s / m
                assert _perto_de_uma_area(g, x, y), (mapa, a, b, s)
    # queda de uma mão só: de baixo para cima nunca é pela ligação que só desce
    quedas = [(a, b) for a, bs in adj.items() for b in bs if a < nc and b < nc and g.pz[b] - g.pz[a] <= -100 and a not in adj[b]]
    for a, b in quedas[:20]:
        r = g.caminho((g.px[b], g.py[b], g.pz[b]), (g.px[a], g.py[a], g.pz[a]))
        assert r is None or all(not (r["nos"][k] == b and r["nos"][k + 1] == a) for k in range(len(r["nos"]) - 1))



# O erro mediano do tempo (250 u/s) contra o tempo real da C3, com o MESMO cálculo da PC0 (`scripts/pc0/compara_fontes.py`): o teto é o da PC0 com folga de 1,5 ponto percentual.
TETO = {"de_mirage": 10.5, "de_dust2": 13.5, "de_nuke": 12.5, "de_inferno": 8.5, "de_anubis": 7.0, "de_ancient": 6.5}


@pytest.mark.parametrize("mapa", COM_TEMPO)
def test_o_erro_do_tempo_pelo_caminho_fica_no_da_pc0_e_bem_abaixo_do_da_reta(mapa):
    r = avalia(mapa)
    assert r["pares"] == r["total"]      # o caminho existe em todos os pares da tabela
    assert r["erro_mediano_%"] <= TETO[mapa], r
    assert r["erro_mediano_%"] <= r["reta_mediano_%"] - 4, r      # melhora a reta em pelo menos 4 pontos percentuais
    assert r["dentro_15%"] >= r["reta_dentro_15%"] + 10, r
    assert abs(r["vies_s"]) < 0.5      # sem viés: a reta subestimava (-0,65 s na Mirage)


def test_os_quatro_exemplos_da_pc0_dao_os_mesmos_tempos():
    from scripts.comandos_contexto import contexto
    from scripts.pc0.exemplos import nos_por_nome
    d = _dados("de_mirage")
    g = Caminhos(d)
    nos = nos_por_nome(contexto("de_mirage", so_conferidos=True)["pontos"])
    esperado = {("Base TR", "Meio"): 11.2, ("CT", "L"): 11.5, ("Janela Mercado", "L"): 5.8, ("Janelão", "L"): 3.5}      # os tempos do corpus na PC0 (s)
    for (na, nb), t in esperado.items():
        a, b = nos[na][0], nos[nb][0]
        r = g.caminho((a["x"], a["y"], d["z_pontos"][a["chave"]]), (b["x"], b["y"], d["z_pontos"][b["chave"]]))
        assert abs(r["comprimento"] / VELOCIDADE_U_S - t) <= 0.3, (na, nb, r["comprimento"] / VELOCIDADE_U_S)
    # "Janelão -> L": só o corpus tem o pulo que os jogadores fazem (3,5 s); a malha dos bots daria a volta (9,7 s)
    a, b = nos["Janelão"][0], nos["L"][0]
    r = g.caminho((a["x"], a["y"], d["z_pontos"][a["chave"]]), (b["x"], b["y"], d["z_pontos"][b["chave"]]))
    assert r["fonte"] == "corpus"


def test_a_malha_cobre_onde_o_corpus_nao_passou_e_o_fio_puxado_melhora_o_erro():
    """Vertigo e Cache não têm partida no corpus: só a malha (fonte "malha"); e o fio puxado melhora o erro da malha sozinha na Mirage (33,6% -> 10,0% na PC1)."""
    for mapa in ("de_vertigo", "de_cache"):
        d = _dados(mapa)
        assert d["nc"] == 0 and d["na"] > 2000
        g = Caminhos(d)
        a, b = 0, d["na"] - 1
        pa, pb = (g.px[a], g.py[a], g.pz[a]), (g.px[b], g.py[b], g.pz[b])
        r = g.caminho(pa, pb)
        assert r is None or r["fonte"] == "malha"
    from scripts.caminhos.avalia import so_malha
    d = _dados("de_mirage")
    g = Caminhos(so_malha(d))
    com, sem = avalia("de_mirage", True, g), avalia("de_mirage", False, g)
    assert sem["erro_mediano_%"] > 25 and com["erro_mediano_%"] < 12 and com["erro_mediano_%"] < sem["erro_mediano_%"] / 2


def test_sem_ponto_perto_de_nada_nao_ha_caminho():
    g = Caminhos(_dados("de_mirage"))
    assert g.caminho((90000.0, 90000.0, 0.0), (0.0, 0.0, -150.0)) is None      # fora do mapa: sem célula nem área; o plano volta para a reta "estimado: linha reta"


def test_nenhuma_pagina_pede_o_grafo_ainda_e_o_build_so_entrega_o_dado(tmp_path):
    from scripts.build_caminhos import ARQUIVO_DO_MODULO, escreve
    from scripts.build_tactics_page import build_html as build_prancheta
    from scripts.build_web_page import build_html
    for html in (build_prancheta("de_mirage", biblioteca_externa=True, plano_externo=True, leitor_externo=True), build_html("match_43")):
        assert "caminhos/" not in html and "caminho.js" not in html and "__recebeCaminhos" not in html
    escritos = escreve(tmp_path)
    assert ARQUIVO_DO_MODULO in escritos and len([e for e in escritos if e.startswith("caminhos/")]) == len(MAPAS)
    texto = (tmp_path / "caminhos" / "de_mirage.js").read_text(encoding="utf-8")
    assert texto.startswith("window.__recebeCaminhos && window.__recebeCaminhos(") and json.loads(texto[len("window.__recebeCaminhos && window.__recebeCaminhos("):-3])["mapa"] == "de_mirage"


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# o JS faz o mesmo que o Python, e rápido (CPU 4x mais lenta)
# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------

sync_api = pytest.importorskip("playwright.sync_api")
from tests.test_tactics_browser import navegador  # noqa: E402,F401

MODULO = (RAIZ / "dashboard" / "web" / "comandos" / "caminho.js").read_text(encoding="utf-8")


def _pagina_do_modulo(navegador, mapa: str):
    ctx = navegador.new_context()
    pg = ctx.new_page()
    pg.set_content("<!doctype html><meta charset=utf-8>")
    pg.add_script_tag(content=MODULO)
    pg.evaluate("d => { window.__g = CaminhoDosMapas.cria(d); }", _dados(mapa))
    return ctx, pg


@pytest.mark.parametrize("mapa", ["de_mirage", "de_nuke"])
def test_o_js_dá_o_mesmo_comprimento_e_a_mesma_rota_que_o_python(navegador, mapa):
    g = Caminhos(_dados(mapa))
    consultas = _amostra(mapa, 80)
    esperado = [g.caminho(p, q) for p, q in consultas]
    ctx, pg = _pagina_do_modulo(navegador, mapa)
    try:
        r = pg.evaluate("cs => cs.map(([p, q]) => { const r = window.__g.caminho(p, q); return r && { c: r.comprimento, f: r.fonte, n: r.nos, q: r.quedas }; })", [list(map(list, c)) for c in consultas])
        for e, j in zip(esperado, r):
            assert (e is None) == (j is None)
            if e:
                assert abs(e["comprimento"] - j["c"]) < 0.01 and e["fonte"] == j["f"] and e["nos"] == j["n"] and e["quedas"] == j["q"]
    finally:
        ctx.close()


def test_uma_consulta_com_a_cpu_4x_mais_lenta_fica_abaixo_de_50_ms(navegador):
    ctx = navegador.new_context()
    pg = ctx.new_page()
    try:
        pg.set_content("<!doctype html><meta charset=utf-8>")
        pg.context.new_cdp_session(pg).send("Emulation.setCPUThrottlingRate", {"rate": 4})
        pg.add_script_tag(content=MODULO)
        consultas = [list(map(list, c)) for c in _amostra("de_mirage", 100) + _amostra("de_nuke", 50)]
        d = _dados("de_vertigo")      # o pior caso: só a malha (sem corpus), pares sorteados do mapa inteiro, com o fio puxado nos trechos longos
        rnd = random.Random(1)
        v = [[[d["p"][3 * a + i] for i in range(3)], [d["p"][3 * b + i] for i in range(3)]] for a, b in ((rnd.randrange(d["na"]), rnd.randrange(d["na"])) for _ in range(100))]
        for mapa, qs in (("de_mirage", consultas[:100]), ("de_nuke", consultas[100:]), ("de_vertigo", v)):
            r = pg.evaluate("""([d, cs]) => { const t0 = performance.now(); const g = CaminhoDosMapas.cria(d), montou = performance.now() - t0, ms = [];
                for (const [p, q] of cs) { const t = performance.now(); g.caminho(p, q); ms.push(performance.now() - t); }
                ms.sort((a, b) => a - b); return { montou, mediana: ms[Math.floor(ms.length / 2)], max: ms[ms.length - 1] }; }""", [_dados(mapa), qs])
            assert r["max"] < 50 and r["montou"] < 500, (mapa, r)
    finally:
        ctx.close()
