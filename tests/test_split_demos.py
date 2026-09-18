"""
Demo dividida pelo GOTV (-p1/-p2) e numeração de partidas.

Casos reais que motivaram cada teste:
- o Overpass de FURIA x Vitality chegou em duas demos, em PASTAS DIFERENTES
  ("X" e "X - Copia"), e virou duas partidas com placares falsos (7-5 e 8-3);
- o próximo id era a CONTAGEM de partidas + 1, então remover uma partida fazia
  a próxima demo nova sobrescrever outra existente.
"""
from __future__ import annotations

from pathlib import Path

import polars as pl

from parsing.parser import merge_interim
from scripts import process_all_demos as pad


def test_partes_em_pastas_de_copia_diferentes_viram_um_grupo():
    demos = [
        Path("demos/serie-x - Copia/a-vs-b-m1-overpass-p1.dem"),
        Path("demos/serie-x/a-vs-b-m1-overpass-p2.dem"),
        Path("demos/serie-x - Copia (2)/a-vs-b-m2-ancient.dem"),
    ]
    grupos = pad.group_demos(list(reversed(demos)))
    divididos = [g for g in grupos if len(g) > 1]
    assert len(grupos) == 2
    # a ordem das partes é p1, p2 -- é a ordem em que os rounds são empilhados
    assert [p.name for p in divididos[0]] == ["a-vs-b-m1-overpass-p1.dem", "a-vs-b-m1-overpass-p2.dem"]


def test_mesmo_mapa_de_series_diferentes_nao_se_mistura():
    demos = [
        Path("demos/evento-1/a-vs-b-m1-overpass-p1.dem"),
        Path("demos/evento-2/a-vs-b-m1-overpass-p2.dem"),
    ]
    assert all(len(g) == 1 for g in pad.group_demos(demos))


def _parte(pasta: Path, ticks: list[int], rounds: list[int]) -> None:
    pasta.mkdir(parents=True)
    pl.DataFrame({"round_num": rounds, "tick": ticks, "steamid": [1] * len(ticks)}).write_parquet(
        pasta / "ticks.parquet"
    )
    pl.DataFrame(
        {"round_num": sorted(set(rounds)), "start": [min(ticks)] * len(set(rounds)),
         "end": [max(ticks)] * len(set(rounds)), "winner": ["ct"] * len(set(rounds))}
    ).write_parquet(pasta / "rounds.parquet")
    (pasta / "header.json").write_text('{"map_name": "de_overpass"}', encoding="utf-8")


def test_fusao_desloca_tick_e_round_da_segunda_parte(tmp_path):
    # as duas partes recomeçam do zero, como no GOTV de verdade
    _parte(tmp_path / "p1", ticks=[10, 500], rounds=[1, 12])
    _parte(tmp_path / "p2", ticks=[20, 300], rounds=[1, 11])

    dest = merge_interim(tmp_path, ["p1", "p2"], "fundida")
    ticks = pl.read_parquet(dest / "ticks.parquet")
    rounds = pl.read_parquet(dest / "rounds.parquet")

    assert ticks["round_num"].to_list() == [1, 12, 13, 23]
    # nenhum tick da parte 2 pode cair antes do último da parte 1
    assert ticks["tick"].to_list()[2] > 500
    assert ticks["tick"].is_sorted()
    assert rounds["round_num"].to_list() == [1, 12, 13, 23]
    assert (rounds["start"] <= rounds["end"]).all()


def test_proximo_id_usa_o_maior_existente_e_nao_a_contagem(tmp_path, monkeypatch):
    for nome in ("match_01", "match_02", "match_05"):
        (tmp_path / nome).mkdir()
    monkeypatch.setattr(pad, "PROCESSED_DIR", tmp_path)
    # pela contagem daria 4 -- e a demo seguinte ainda cairia em cima da match_05
    assert pad.next_match_index() == 6
