"""
Ajusta a RÉGUA do perfil por jogador: a distribuição agregada e ANÔNIMA do
corpus, uma mediana por taxa.

    py -3.12 -m scripts.fit_perfil_reference            # mostra
    py -3.12 -m scripts.fit_perfil_reference --gravar   # grava a referência

Saída: `metrics/perfil_reference.json` -- só números, nenhum nome de jogador.

POR QUE EXISTE (regra dos três níveis, decisão do Pedro)
-------------------------------------------------------
A referência de cada taxa era a mediana dos OUTROS NOVE jogadores da mesma
partida. Isso responde "ele está acima dos companheiros e dos adversários DE
HOJE", que muda conforme quem entrou em quadra: o mesmo 40% vira destaque ou
banalidade dependendo do adversário daquele mapa. A régua passa a ser a
distribuição do CORPUS -- agregada e anônima --, que é estável e não depende de
quem jogou a partida aberta.

O nível 1 da regra (os números do JOGADOR são só da partida aberta) continua
valendo e não é afetado: o que vem do corpus é a RÉGUA, nunca o número dele.

Refazer quando o corpus crescer, junto com as outras referências
(`fit_archetype_reference`, `fit_economia`). Sem o arquivo, o perfil cai na
mediana dos outros jogadores da própria partida e MARCA isso -- é o nível 3:
sem seletor, com aviso.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from metrics.player_profile import TAXAS_POR_ROUND, TAXAS_TODAS  # noqa: E402

PROCESSED = PROJECT_ROOT / "data" / "processed"
SAIDA = PROJECT_ROOT / "metrics" / "perfil_reference.json"

# Mínimo de jogador-partidas para uma taxa entrar na régua. Abaixo disso a
# mediana do corpus não é mais firme que a da própria partida, e aí não vale a
# troca -- a taxa fica sem régua de corpus e cai na da partida, marcada.
MIN_JOGADOR_PARTIDAS = 50


def colunas_de_taxa() -> list[str]:
    sensiveis = [c for c, _, por_lado in TAXAS_POR_ROUND if por_lado]
    return TAXAS_TODAS + [f"{c}_{lado}" for c in sensiveis for lado in ("ct", "t")]


def carrega() -> pl.DataFrame:
    partes = [pl.read_parquet(d / "player_profile.parquet")
              for d in sorted(PROCESSED.glob("match_*")) if (d / "player_profile.parquet").exists()]
    if not partes:
        raise SystemExit("sem data/processed/*/player_profile.parquet")
    return pl.concat(partes, how="diagonal_relaxed")


def ajusta(perfis: pl.DataFrame) -> dict:
    medianas, descartadas = {}, []
    for col in colunas_de_taxa():
        if col not in perfis.columns:
            continue
        v = perfis[col].drop_nulls()
        if v.len() < MIN_JOGADOR_PARTIDAS:
            descartadas.append((col, v.len()))
            continue
        medianas[col] = float(v.median())
    return {
        "_leia_isto": (
            "Régua do perfil por jogador: mediana de cada taxa no CORPUS, agregada e ANÔNIMA "
            "(nenhum nome, nenhum steamid). Usada por metrics/player_profile para dizer se uma "
            "taxa é alta ou baixa, no lugar da mediana dos outros jogadores da mesma partida. "
            "Os números DO JOGADOR continuam saindo só da partida aberta. "
            "Refazer com scripts/fit_perfil_reference.py quando o corpus crescer."
        ),
        "n_partidas": perfis["match_id"].n_unique(),
        "n_jogador_partidas": perfis.height,
        "min_jogador_partidas": MIN_JOGADOR_PARTIDAS,
        "medianas": dict(sorted(medianas.items())),
        "sem_regua": dict(descartadas),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Ajusta a régua do perfil (mediana do corpus).")
    ap.add_argument("--gravar", action="store_true")
    args = ap.parse_args()

    ref = ajusta(carrega())
    print(f"{ref['n_jogador_partidas']} jogador-partidas em {ref['n_partidas']} partidas; "
          f"{len(ref['medianas'])} taxas com régua de corpus"
          + (f", {len(ref['sem_regua'])} sem (amostra < {MIN_JOGADOR_PARTIDAS})" if ref["sem_regua"] else ""))
    for col, v in list(ref["medianas"].items())[:8]:
        print(f"  {col:<38} mediana {v:.3f}")
    if args.gravar:
        SAIDA.write_text(json.dumps(ref, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\ngravado em {SAIDA.relative_to(PROJECT_ROOT).as_posix()}")
    else:
        print("\n(simulação: use --gravar)")


if __name__ == "__main__":
    main()
