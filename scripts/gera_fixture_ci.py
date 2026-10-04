"""Gera a fixture do interim que o CI usa (auditoria, item 5.7).

O interim não é versionado (data/interim/ fica fora do git), então a escada
contra a HLTV e a soma zero do Round Swing nunca rodavam no CI. Esta fixture
guarda duas partidas, com só o que esses testes leem:

  - match_45: a menor partida profissional sem prorrogação (15 rounds);
  - match_16: a menor com prorrogação (29 rounds).

As duas têm os dois lados (toda partida troca no round 12). Das tabelas de
eventos (kills, damages, player_blind, compra) vão todas as colunas -- são
pequenas; de `ticks`, que é a grande, só as colunas que a soma zero e a
identificação dos times usam. Parquet em zstd. O total tem de ficar em até
10 MB (há teste).

Uso:
    py -3.12 -m scripts.gera_fixture_ci
"""
from __future__ import annotations

import sys
from pathlib import Path

import polars as pl

RAIZ = Path(__file__).resolve().parents[1]
INTERIM = RAIZ / "data" / "interim"
DESTINO = RAIZ / "tests" / "fixtures" / "interim_ci"
PARTIDAS = ("match_45", "match_16")
EVENTOS = ("kills", "damages", "player_blind", "compra")
COLUNAS_DE_TICKS = ["tick", "round_num", "steamid", "name", "side", "active_weapon_name", "current_equip_value"]
LIMITE_BYTES = 10 * 1024 * 1024


def gera() -> int:
    total = 0
    for m in PARTIDAS:
        saida = DESTINO / m
        saida.mkdir(parents=True, exist_ok=True)
        for nome in EVENTOS:
            origem = INTERIM / m / f"{nome}.parquet"
            if origem.exists():
                pl.read_parquet(origem).write_parquet(saida / f"{nome}.parquet", compression="zstd", compression_level=19)
        pl.read_parquet(INTERIM / m / "ticks.parquet", columns=COLUNAS_DE_TICKS).write_parquet(
            saida / "ticks.parquet", compression="zstd", compression_level=19)
        total += sum(f.stat().st_size for f in saida.iterdir())
    return total


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    total = gera()
    print(f"fixture em {DESTINO.relative_to(RAIZ).as_posix()}: {total / 1024 / 1024:.2f} MB (limite 10 MB)")
    if total > LIMITE_BYTES:
        raise SystemExit("passou de 10 MB: pare e pergunte ao Pedro (auditoria 5.7)")


if __name__ == "__main__":
    main()
