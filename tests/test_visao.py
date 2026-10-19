"""Quem vê quem (fase 18, item 18.1; metrics/erros/visao.py): linha de visão pelo mapa + campo de visão.

- a grade dá a MESMA resposta que o verificador do awpy 2.0.2 (`awpy.visibility.VisibilityChecker`),
  num conjunto de paredes montado à mão e, se a malha estiver no disco, na Mirage;
- parede e smoke fecham a linha; o campo de visão é a metade de 106,26 graus; cego não vê;
- o .mesh do awpy-data vira os mesmos triângulos.
"""
from __future__ import annotations

import math
import struct

import numpy as np
import polars as pl
import pytest

from metrics.erros import visao as V


def _parede(x: float, y0: float = -500.0, y1: float = 500.0, z0: float = -100.0, z1: float = 300.0) -> np.ndarray:
    """Uma parede no plano x = const (dois triângulos)."""
    a, b, c, d = (x, y0, z0), (x, y1, z0), (x, y1, z1), (x, y0, z1)
    return np.array([[a, b, c], [a, c, d]], dtype=float)


def test_meio_campo_de_visao_e_o_do_cs2_em_16_por_9():
    # 90 graus na horizontal em 4:3, alargado para 16:9 mantendo a vertical: 106,26 graus
    assert V.MEIO_FOV_GRAUS == pytest.approx(53.13, abs=0.01)


def test_parede_fecha_a_linha_e_o_resto_fica_livre():
    m = V.Malha(_parede(500.0))
    assert not m.linha_livre((0, 0, 64), (1000, 0, 64))           # atravessa a parede
    assert m.linha_livre((0, 0, 64), (400, 0, 64))                # para antes dela
    assert m.linha_livre((0, 0, 64), (1000, 0, 700))              # passa por cima (em x = 500 está a 382; a parede vai até 300)
    assert m.linha_livre((0, 900, 64), (1000, 900, 64))           # passa ao lado


def test_a_grade_responde_igual_ao_awpy_2_0_2():
    from awpy.vector import Vector3
    from awpy.visibility import Triangle, VisibilityChecker

    rng = np.random.default_rng(18)
    tris = np.concatenate([_parede(float(x), float(y), float(y) + 300.0, 0.0, float(h))
                           for x, y, h in zip(rng.uniform(-1500, 1500, 40), rng.uniform(-1500, 1500, 40),
                                              rng.uniform(50, 300, 40))])
    m = V.Malha(tris, celula=97.0)
    vc = VisibilityChecker(triangles=[Triangle(*(Vector3(*map(float, p)) for p in t)) for t in tris])
    a = rng.uniform(-2000, 2000, (600, 3))
    b = rng.uniform(-2000, 2000, (600, 3))
    a[:, 2] = rng.uniform(0, 200, 600)
    b[:, 2] = rng.uniform(0, 200, 600)
    nossa = [m.linha_livre(x, y) for x, y in zip(a, b)]
    deles = [vc.is_visible(tuple(x), tuple(y)) for x, y in zip(a, b)]
    assert nossa == deles
    assert 50 < sum(nossa) < 550                                  # o conjunto tem dos dois casos


def test_na_mirage_a_grade_responde_igual_ao_awpy():
    if not V.malha_disponivel("de_mirage"):
        pytest.skip("sem a malha da Mirage (py -3.12 -m scripts.visao_malhas)")
    import sys

    from awpy.vector import Vector3
    from awpy.visibility import Triangle, VisibilityChecker
    sys.setrecursionlimit(100000)
    tri = V.le_tri(V.TRIS_DIR / "de_mirage.tri")
    m = V.Malha(tri)
    vc = VisibilityChecker(triangles=[Triangle(*(Vector3(*map(float, p)) for p in t)) for t in tri])
    rng = np.random.default_rng(7)
    # pontos dentro da caixa do mapa, na altura dos olhos acima do chão mais baixo
    lo, hi = tri.reshape(-1, 3).min(axis=0), tri.reshape(-1, 3).max(axis=0)
    a = rng.uniform(lo, hi, (200, 3))
    b = rng.uniform(lo, hi, (200, 3))
    assert [m.linha_livre(x, y) for x, y in zip(a, b)] == [vc.is_visible(tuple(x), tuple(y)) for x, y in zip(a, b)]


def _ticks(linhas: list[tuple]) -> pl.DataFrame:
    """(tick, steamid, x, y, z, yaw) num round 1."""
    return pl.DataFrame([{"round_num": 1, "tick": t, "steamid": s, "X": float(x), "Y": float(y), "Z": float(z),
                          "yaw": float(yaw)} for t, s, x, y, z, yaw in linhas])


def test_visivel_exige_campo_de_visao_linha_livre_e_nao_estar_cego():
    # 1 em (0,0) olhando para +X; 2 em (1000, 0)
    t = _ticks([(100, 1, 0, 0, 0, 0.0), (100, 2, 1000, 0, 0, 180.0)])
    assert V.Visao(t, None).visivel(1, 100, 1, 2)
    # de costas: fora do campo de visão
    t2 = _ticks([(100, 1, 0, 0, 0, 180.0), (100, 2, 1000, 0, 0, 180.0)])
    assert not V.Visao(t2, None).visivel(1, 100, 1, 2)
    # na borda: 50 graus dentro, 56 fora
    for yaw, esperado in ((50.0, True), (56.0, False)):
        t3 = _ticks([(100, 1, 0, 0, 0, yaw), (100, 2, 1000, 0, 0, 0.0)])
        assert V.Visao(t3, None).visivel(1, 100, 1, 2) is esperado
    # parede no meio
    assert not V.Visao(t, V.Malha(_parede(500.0))).visivel(1, 100, 1, 2)
    # smoke ativa no meio fecha; antes de ela estourar, não
    vis = V.Visao(t, None, smokes=[(1, 90, 200, 500.0, 0.0, 0.0)])
    assert not vis.visivel(1, 100, 1, 2)
    assert V.Visao(t, None, smokes=[(1, 150, 200, 500.0, 0.0, 0.0)]).visivel(1, 100, 1, 2)
    # cego não vê
    assert not V.Visao(t, None, cegueira={(1, 1): [(90, 130)]}).visivel(1, 100, 1, 2)


def test_so_a_cabeca_aparecendo_ainda_e_visivel():
    # parede baixa até a altura do peito (z 0 a 50): a cabeça (64) aparece
    t = _ticks([(100, 1, 0, 0, 0, 0.0), (100, 2, 1000, 0, 0, 180.0)])
    assert V.Visao(t, V.Malha(_parede(500.0, z1=50.0))).visivel(1, 100, 1, 2)
    assert not V.Visao(t, V.Malha(_parede(500.0, z1=90.0))).visivel(1, 100, 1, 2)


def test_amostras_da_janela():
    v = V.Visao(_ticks([(0, 1, 0, 0, 0, 0.0)]), None)
    assert v.amostras(100, 120) == [100, 108, 116, 120]
    assert v.amostras(100, 100) == [100]
    assert v.amostras(101, 100) == []


def test_o_mesh_do_awpy_data_vira_os_mesmos_triangulos():
    from scripts.visao_malhas import mesh_para_triangulos
    vert = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype="<f4")
    idx = np.array([[0, 1, 2], [0, 2, 3]], dtype="<u4")
    dados = struct.pack("<4sIII", b"AWMH", 1, 4, 2) + vert.tobytes() + idx.tobytes()
    tri = mesh_para_triangulos(dados)
    assert tri.shape == (2, 3, 3)
    assert tri[1].tolist() == [[0, 0, 0], [0, 1, 0], [0, 0, 1]]
    with pytest.raises(ValueError):
        mesh_para_triangulos(dados[:-4])


def test_angulo_horizontal_da_a_volta():
    assert V.angulo_horizontal(179.0, (0, 0), (-1, -0.01)) == pytest.approx(1.57, abs=0.05)
    assert V.angulo_horizontal(90.0, (0, 0), (0, 10)) == pytest.approx(0.0)
    assert math.isclose(V.angulo_horizontal(0.0, (0, 0), (-10, 0)), 180.0)
