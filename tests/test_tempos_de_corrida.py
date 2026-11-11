"""C3: a tabela dos tempos reais de corrida (`data/tempos/<mapa>.json`, feita por `scripts/build_tempos.py` a partir de `metrics/tempos_de_corrida.py`).

Três coisas: a conta em rastros inventados (o que entra e o que sai), a forma da tabela (sem corpus) e o RECÁLCULO INDEPENDENTE: outro código, em Python puro (laços
e `statistics`, sem o módulo de métricas), refaz da partida bruta toda linha da tabela e confere número a número. Esse último precisa de `data/interim` (roda aqui no PC)."""
from __future__ import annotations

import json
import statistics
from pathlib import Path

import numpy as np
import pytest

from metrics import tempos_de_corrida as T

RAIZ = Path(__file__).resolve().parents[1]
PASTA = RAIZ / "data" / "tempos"


# ---------- a conta, em rastros inventados ----------

def _rastro(xs, ys, partida="m1", walk=0.0, duck=0.0, z=0.0, passo=8, tr=64):
    n = len(xs)
    return {"partida": partida, "tick": np.arange(n) * passo, "x": np.array(xs, float), "y": np.array(ys, float), "z": np.full(n, z), "walk": np.full(n, walk),
            "duck": np.full(n, duck), "tr": tr, "passo": passo}


def _nos():
    return [{"chave": "A", "x": 0, "y": 0, "membros": [(0, 0)], "andar": ""}, {"chave": "B", "x": 1000, "y": 0, "membros": [(1000, 0)], "andar": ""}]


def _corre(v=200.0, parar_em=None, volta=False):
    """Um jogador que parte de A, corre até B a `v` u/s (uma amostra a cada 0,125 s = 25 u a 200 u/s)."""
    passo = v * 0.125
    xs = [i * passo for i in range(int(1000 / passo) + 1)]
    ys = [0.0] * len(xs)
    if parar_em is not None:
        xs = xs[:parar_em] + [xs[parar_em]] * 12 + xs[parar_em:]               # 1,5 s parado no caminho
        ys = [0.0] * len(xs)
    if volta:
        xs = xs[:len(xs) // 2] + xs[:len(xs) // 2][::-1] + xs                  # vai até a metade, volta a A e então corre
        ys = [0.0] * len(xs)
    return xs, ys


def test_uma_corrida_de_a_a_b_mede_do_ponto_mais_perto_de_a_ao_ponto_mais_perto_de_b():
    xs, ys = _corre()
    v = T.viagens([_rastro(xs, ys)], _nos(), 150.0)
    (partida, dur, walk, duck), = v[(0, 1)]
    assert abs(dur - 5.0) < 0.2 and walk == 0 and duck == 0                    # 1000 u a 200 u/s


def test_parada_longa_e_buraco_ficam_de_fora_e_quem_volta_a_a_conta_da_ultima_saida():
    xs, ys = _corre(parar_em=20)
    assert (0, 1) not in T.viagens([_rastro(xs, ys)], _nos(), 150.0)                          # 1,5 s parado no caminho
    xs, ys = _corre(volta=True)                                                               # foi até a metade, voltou a A e só então correu: a viagem é da última saída de A
    (_, dur, _, _), = T.viagens([_rastro(xs, ys)], _nos(), 150.0)[(0, 1)]
    assert abs(dur - 5.0) < 0.3
    r = _rastro(*_corre()); r["tick"] = r["tick"].copy(); r["tick"][10:] += 400   # buraco de 6 s no rastro (morte, troca de round)
    assert (0, 1) not in T.viagens([r], _nos(), 150.0)


def test_desvio_demais_e_viagem_longa_demais_ficam_de_fora():
    xs, ys = _corre()
    ys = [600 if 8 < i < 32 else 0 for i in range(len(xs))]      # sobe, anda de lado e desce: caminho bem maior que a reta
    assert (0, 1) not in T.viagens([_rastro(xs, ys)], _nos(), 150.0)
    xs, ys = _corre(v=30.0)                                                                  # 33 s: é espera, não deslocamento
    assert (0, 1) not in T.viagens([_rastro(xs, ys)], _nos(), 150.0)


def test_so_correndo_entra_na_tabela_e_o_minimo_e_20_casos_em_3_partidas():
    xs, ys = _corre()
    lote = [_rastro(xs, ys, partida=f"m{i % 3}") for i in range(20)]
    assert T.resumo(T.viagens(lote, _nos(), 150.0)[(0, 1)])["casos"] == 20
    assert T.resumo(T.viagens(lote[:19], _nos(), 150.0)[(0, 1)]) is None                      # 19 casos
    assert T.resumo(T.viagens([_rastro(xs, ys, partida="m1") for _ in range(25)], _nos(), 150.0)[(0, 1)]) is None   # 1 partida só
    andando = [_rastro(xs, ys, partida=f"m{i % 3}", walk=1.0) for i in range(25)]
    agachado = [_rastro(xs, ys, partida=f"m{i % 3}", duck=1.0) for i in range(25)]
    assert T.resumo(T.viagens(andando, _nos(), 150.0)[(0, 1)]) is None and T.resumo(T.viagens(agachado, _nos(), 150.0)[(0, 1)]) is None


def test_no_de_um_andar_so_vale_para_ticks_daquele_andar():
    xs, ys = _corre()
    nos = _nos(); nos[1]["andar"] = "baixo"
    assert (0, 1) not in T.viagens([_rastro(xs, ys, z=500.0)], nos, 150.0, corte_z=0.0)         # o jogador está em cima
    assert (0, 1) in T.viagens([_rastro(xs, ys, z=-500.0)], nos, 150.0, corte_z=0.0)


def test_o_fator_e_a_mediana_de_real_sobre_reta_com_o_erro_dito():
    nos = [{"chave": str(i), "x": 1000.0 * i, "y": 0.0, "andar": ""} for i in range(8)]
    pr = {(a, b): {"mediana": (1000.0 * abs(b - a)) / 210.6 * 1.25} for a in range(8) for b in range(8) if a != b}
    f = T.fator_do_mapa([("pontos", pr, nos)], 210.6)
    assert abs(f["valor"] - 1.25) < 0.001 and f["pares"] == 56 and f["erro_corrigido_s"] < 0.01 and f["erro_reta_s"] > 1
    assert T.fator_do_mapa([("pontos", {(0, 1): {"mediana": 5.0}}, nos)], 210.6)["valor"] is None   # poucos pares: sem fator


# ---------- a forma da tabela (sem corpus) ----------

def _tabelas():
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(PASTA.glob("de_*.json"))}


def test_toda_linha_da_tabela_respeita_o_minimo_e_a_ordem_da_faixa():
    tabelas = _tabelas()
    assert {"de_mirage", "de_dust2", "de_nuke", "de_inferno", "de_anubis", "de_ancient"} <= set(tabelas)
    assert "de_overpass" not in tabelas and "de_train" not in tabelas                       # 2 partidas e 1 partida: sem par com amostra
    for mapa, t in tabelas.items():
        assert t["minimo_casos"] == 20 and t["minimo_partidas"] == 3
        for fonte in ("pontos", "areas"):
            for a, b, p25, med, p75, n, partidas in t[fonte]:
                assert a != b and n >= 20 and partidas >= 3 and p25 <= med <= p75 and 0 < p25 < 25, (mapa, fonte, a, b)
        chaves = {k for k, *_ in t["nos"]}
        assert all(r[0] in chaves and r[1] in chaves for r in t["pontos"])                  # todo ponto da tabela tem o seu nó (a aba acha a peça pelo nó)
        f = t["fator"]
        assert f["valor"] is None or (0.5 < f["valor"] < 2.0 and f["pares"] >= T.MIN_PARES_DO_FATOR and f["erro_corrigido_s"] >= 0)


def test_so_os_mapas_com_pontos_conferidos_tem_tempo_entre_pontos():
    from scripts.comandos_contexto import contexto
    for mapa, t in _tabelas().items():
        conferidos = contexto(mapa, so_conferidos=True)["pontos"]
        assert bool(t["pontos"]) == bool(conferidos), mapa                                  # Nuke, Inferno, Anubis, Ancient: só áreas, até o Pedro conferir
        from scripts.build_tempos import nos_de_pontos
        esperados = {n["chave"]: (n["x"], n["y"]) for n in nos_de_pontos(conferidos)}
        for k, x, y, _ in t["nos"]:
            assert esperados.get(k) == (x, y), (mapa, k)                                    # a chave é o número do ponto (como o leitor monta de `alvo.ids`) e a posição bate com o CSV de hoje


def test_as_areas_da_tabela_existem_no_contexto_do_mapa():
    from scripts.comandos_contexto import contexto
    for mapa, t in _tabelas().items():
        nomes = {a["nome"] for a in contexto(mapa)["areas"]}
        assert all(r[0] in nomes and r[1] in nomes for r in t["areas"]), mapa


# ---------- o recálculo independente ----------

def _le_rastros_de_novo(mapa):
    """Outro leitor do corpus: um laço de Python por jogador e round, sem numpy nos rastros."""
    import polars as pl
    from scripts.build_lineups import INTERIM, PROCESSED, detect_tickrate, load_interim
    saida = []
    for d in sorted(INTERIM.glob("match_*")):
        meta = PROCESSED / d.name / "match_meta.json"
        if not meta.exists() or json.loads(meta.read_text(encoding="utf-8"))["map_name"] != mapa:
            continue
        t = load_interim(INTERIM, d.name)
        rounds = pl.read_parquet(PROCESSED / d.name / "rounds.parquet")
        tr = int(detect_tickrate(rounds, t["ticks"])["tickrate"]); passo = max(1, round(8 * tr / 64))
        for rd in rounds.iter_rows(named=True):
            if rd["freeze_end"] is None or rd["end"] is None:
                continue
            g = t["ticks"].filter((pl.col("round_num") == rd["round_num"]) & pl.col("is_alive") & (pl.col("tick") % passo == 0)
                                  & (pl.col("tick") >= rd["freeze_end"]) & (pl.col("tick") <= rd["end"]))
            for sid in g["steamid"].unique().to_list():
                h = g.filter(pl.col("steamid") == sid).sort("tick")
                if h.height >= 4:
                    saida.append((d.name, tr, passo, h["tick"].to_list(), h["X"].to_list(), h["Y"].to_list(), h["Z"].to_list(),
                                  [bool(v) for v in h["is_walking"].fill_null(False).to_list()], [bool(v) for v in h["ducking"].fill_null(False).to_list()]))
    return saida


def _recalcula(rastros, nos, raio, corte_z):
    """{(a, b): [(partida, duração, andando, agachado)]} em laços simples."""
    casos: dict = {}
    for partida, tr, passo, tick, X, Y, Z, walk, duck in rastros:
        n = len(tick)
        dist = []
        for i in range(n):
            linha = []
            for no in nos:
                d = min(((X[i] - mx) ** 2 + (Y[i] - my) ** 2) ** 0.5 for mx, my in no["membros"])
                if corte_z is not None and no["andar"] in ("cima", "baixo") and (Z[i] < corte_z) != (no["andar"] == "baixo"):
                    d = float("inf")
                linha.append(d)
            dist.append(linha)
        rot = []
        for i in range(n):
            m = min(dist[i]); rot.append(dist[i].index(m) if m <= raio else -1)
        visitas = []
        i = 0
        while i < n:
            j = i
            while j + 1 < n and rot[j + 1] == rot[i]:
                j += 1
            if rot[i] >= 0:
                visitas.append((rot[i], min(range(i, j + 1), key=lambda k: dist[k][rot[i]])))
            i = j + 1
        for vi in range(len(visitas)):
            a, ia = visitas[vi]
            vistos = {a}
            for b, ib in visitas[vi + 1:]:
                if b == a:
                    break
                if b in vistos:
                    continue
                vistos.add(b)
                dur = (tick[ib] - tick[ia]) / tr
                if dur > 25.0:
                    break
                if any(tick[k + 1] - tick[k] > 4 * passo for k in range(ia, ib)):
                    continue
                andado, parado = 0.0, 0.0
                for k in range(ia, ib):
                    p = ((X[k + 1] - X[k]) ** 2 + (Y[k + 1] - Y[k]) ** 2) ** 0.5
                    andado += p
                    if p / max((tick[k + 1] - tick[k]) / tr, passo / tr) < 40.0:
                        parado += passo / tr
                reta = ((X[ib] - X[ia]) ** 2 + (Y[ib] - Y[ia]) ** 2) ** 0.5
                if parado > 1.0 or reta < 1 or andado > 1.8 * reta:
                    continue
                anda = sum(walk[ia:ib + 1]) / (ib - ia + 1)
                casos.setdefault((a, b), []).append((partida, dur, anda, any(duck[ia:ib + 1])))
    return casos


def _linhas_independentes(casos, nos):
    saida = {}
    for (a, b), v in casos.items():
        v = [c for c in v if c[2] <= 0.10 and not c[3]]
        partidas = {c[0] for c in v}
        if len(v) < 20 or len(partidas) < 3:
            continue
        d = sorted(c[1] for c in v)
        q = statistics.quantiles(d, n=4, method="inclusive")
        saida[(nos[a]["chave"], nos[b]["chave"])] = (round(q[0], 2), round(statistics.median(d), 2), round(q[2], 2), len(v), len(partidas))
    return saida


@pytest.mark.parametrize("mapa,fonte", [("de_mirage", "pontos"), ("de_mirage", "areas"), ("de_nuke", "areas")])
def test_a_tabela_bate_com_um_recalculo_independente_da_partida_bruta(mapa, fonte):
    from metrics.map_areas import floor_split_z
    from scripts.build_lineups import INTERIM
    from scripts.build_tempos import nos_de_areas, nos_de_pontos
    from scripts.comandos_contexto import contexto
    if not (INTERIM / "match_01" / "ticks.parquet").exists():
        pytest.skip("sem data/interim: o recálculo roda no PC com o corpus")
    ctx = contexto(mapa, so_conferidos=True)
    nos = nos_de_pontos(ctx["pontos"]) if fonte == "pontos" else nos_de_areas(ctx["areas"])
    raio = T.RAIO_PONTOS if fonte == "pontos" else T.RAIO_AREAS
    independente = _linhas_independentes(_recalcula(_le_rastros_de_novo(mapa), nos, raio, floor_split_z(mapa)), nos)
    tabela = {(r[0], r[1]): tuple(r[2:]) for r in json.loads((PASTA / f"{mapa}.json").read_text(encoding="utf-8"))[fonte]}
    assert set(tabela) == set(independente), (sorted(set(tabela) ^ set(independente))[:5], len(tabela), len(independente))
    for k, v in tabela.items():
        assert v == pytest.approx(independente[k], abs=0.011), (k, v, independente[k])
    assert len(tabela) > 20
