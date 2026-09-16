"""
Ajusta a escala dos papéis no conjunto das partidas processadas.

Por que existe: o índice de cada papel precisa responder "o quanto este jogador
se destaca NESTE papel comparado ao que é normal nele". Normalizar dentro da
própria partida não responde isso -- numa partida em que ninguém se destacou,
alguém ainda fica em 1,0, e o card de destaque mostraria um jogador mediano como
se fosse o retrato da partida. A referência é a distribuição de cada componente
no conjunto, guardada como quantis em `metrics/archetype_reference.json`.

É o mesmo padrão do `clustering/global_model.json`: ajusta uma vez sobre todas as
partidas, aplica em cada uma.

Rode sempre que processar uma demo nova ou mexer na definição de um componente.
Mexer num componente sem reajustar deixa a escala apontando para a definição
antiga, o que é pior que não ter referência -- porque não aparece.

Uso:
    py -3.12 -m scripts.fit_archetype_reference
    py -3.12 -m scripts.fit_archetype_reference --dry-run
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import polars as pl

from metrics.archetypes import (
    REFERENCE_FILE,
    archetype_indices,
    build_reference,
    compute_for_match,
)
from metrics.player_roles import HALFTIME_ROUND, resolve_teams
from metrics.positioning import position_samples

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
INTERIM_DIR = PROJECT_ROOT / "data" / "interim"

# Tabelas de data/processed/ que os papéis consomem.
SAIDAS = ("cluster_features", "grenades_per_round", "awp_summary", "player_round_areas")


def side_of_team(team: str, round_num: int) -> str:
    """Que lado o time joga num round (troca depois do intervalo)."""
    primeiro_tempo = round_num <= HALFTIME_ROUND
    if team == "A":
        return "t" if primeiro_tempo else "ct"
    return "ct" if primeiro_tempo else "t"


def winner_team_by_round(rounds: pl.DataFrame) -> dict[int, str]:
    """round -> "A"/"B". O demo entrega o vencedor como LADO, e o lado troca."""
    out: dict[int, str] = {}
    for row in rounds.iter_rows(named=True):
        rn = int(row["round_num"])
        out[rn] = "A" if row["winner"] == side_of_team("A", rn) else "B"
    return out


def carrega_partida(match_id: str) -> tuple[dict, dict, pl.DataFrame, pl.DataFrame, dict, dict]:
    """Tudo que `compute_for_match` precisa, lido do disco."""
    interim = INTERIM_DIR / match_id
    processed = PROCESSED_DIR / match_id

    tables = {
        nome: pl.read_parquet(interim / f"{nome}.parquet")
        for nome in ("ticks", "kills", "rounds", "damages")
    }
    outputs = {
        nome: pl.read_parquet(processed / f"{nome}.parquet")
        for nome in SAIDAS
        if (processed / f"{nome}.parquet").exists()
    }

    team_of, _ = resolve_teams(tables["ticks"])
    positions = position_samples(tables["ticks"], tables["rounds"])
    areas = outputs.get("player_round_areas", pl.DataFrame())
    return tables, outputs, positions, areas, team_of, winner_team_by_round(tables["rounds"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Ajusta a referência de escala dos papéis.")
    parser.add_argument("--dry-run", action="store_true", help="mostra sem gravar")
    args = parser.parse_args()

    partidas = sorted(d.name for d in PROCESSED_DIR.glob("match_*") if d.is_dir())
    if not partidas:
        raise SystemExit("Nenhuma partida processada em data/processed/.")

    pedacos = []
    for match_id in partidas:
        interim = INTERIM_DIR / match_id
        if not (interim / "ticks.parquet").exists():
            print(f"  {match_id}: sem parse em data/interim/, pulando")
            continue
        tables, outputs, positions, areas, team_of, winners = carrega_partida(match_id)
        # reference=None de propósito: a referência está sendo CONSTRUÍDA agora, e
        # usar a anterior aqui faria a escala nova depender da velha.
        _, resumo = compute_for_match(
            tables, outputs, positions, areas, team_of, winners, reference=None
        )
        pedacos.append(resumo.with_columns(pl.lit(match_id).alias("match_id")))
        print(f"  {match_id}: {resumo.height} jogadores")

    componentes = pl.concat(pedacos, how="diagonal")
    referencia = build_reference(componentes)

    print(f"\n{componentes.height} jogador-partidas, {len(referencia['quantis'])} componentes")
    print("\nmediana de cada componente no conjunto:")
    for nome, quantis in sorted(referencia["quantis"].items()):
        print(f"  {nome:<28} {quantis[49]:>10.3f}   (p90 {quantis[89]:>10.3f})")

    if args.dry_run:
        print("\n--dry-run: nada gravado.")
        return

    REFERENCE_FILE.write_text(
        json.dumps(referencia, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"\nReferência salva em {REFERENCE_FILE.relative_to(PROJECT_ROOT)}")
    print("Reprocesse as partidas para os índices saírem na escala nova.")


if __name__ == "__main__":
    main()
