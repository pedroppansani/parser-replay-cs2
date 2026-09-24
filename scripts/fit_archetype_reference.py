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
from metrics.archetypes import MIN_ROUNDS_FUNCAO_NA_REFERENCIA
from metrics.player_roles import resolve_teams
from metrics.sides import side_of_team
from metrics.positioning import position_samples

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
INTERIM_DIR = PROJECT_ROOT / "data" / "interim"

# Tabelas de data/processed/ que os papéis consomem.
SAIDAS = ("cluster_features", "grenades_per_round", "awp_summary", "player_round_areas",
          # a função do round: é dentro dela que a isca é comparada (decisão 15a)
          "structural_roles")


def winner_team_by_round(rounds: pl.DataFrame) -> dict[int, str]:
    """round -> "A"/"B". O demo entrega o vencedor como LADO, e o lado troca."""
    out: dict[int, str] = {}
    for row in rounds.iter_rows(named=True):
        rn = int(row["round_num"])
        out[rn] = "A" if row["winner"] == side_of_team("A", rn) else "B"
    return out


def carrega_partida(match_id: str) -> tuple[dict, dict, pl.DataFrame, pl.DataFrame, dict, dict]:
    """Tudo que `compute_for_match` precisa, lido do disco."""
    processed = PROCESSED_DIR / match_id

    # load_interim, e não o parquet cru: é o MESMO caminho do pipeline (kills do
    # round jogado, corte do freeze time, dano corrigido, cegueira reconstruída).
    # Lendo cru, a referência era ajustada sobre um dado diferente do que ela
    # depois escala.
    from parsing.parser import load_interim

    tables = load_interim(INTERIM_DIR, match_id)
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

    # PASSO 1: a isca esperada de cada FUNÇÃO, no corpus inteiro. Sem isso, a
    # isca relativa de cada jogador não tem contra o que ser comparada (decisão
    # 15a: comparar com a média geral confunde função com atitude).
    carregadas = {}
    rounds_de_isca = []
    for match_id in partidas:
        if not (INTERIM_DIR / match_id / "ticks.parquet").exists():
            print(f"  {match_id}: sem parse em data/interim/, pulando")
            continue
        carregadas[match_id] = carrega_partida(match_id)
        tables, outputs, positions, areas, team_of, winners = carregadas[match_id]
        per_round, _ = compute_for_match(
            tables, outputs, positions, areas, team_of, winners, reference=None
        )
        rounds_de_isca.append(per_round.select("funcao_do_round", "isca_no_round", "sacrificio"))

    isca = pl.concat(rounds_de_isca, how="diagonal")
    geral = float(isca["isca_no_round"].mean())
    por_funcao = isca.group_by("funcao_do_round", maintain_order=True).agg(
        pl.len().alias("rounds"), pl.col("isca_no_round").mean().alias("media"))
    isca_por_funcao = {"_geral": geral}
    fracas = []
    for r in por_funcao.iter_rows(named=True):
        # função com pouca gente no corpus não sustenta uma média própria
        if r["rounds"] >= MIN_ROUNDS_FUNCAO_NA_REFERENCIA:
            isca_por_funcao[r["funcao_do_round"]] = float(r["media"])
        else:
            fracas.append((r["funcao_do_round"], r["rounds"]))
    print("\nisca esperada por função (mortes de companheiro por perto sem troca, por round):")
    for f, v in sorted(isca_por_funcao.items(), key=lambda kv: -kv[1]):
        n = por_funcao.filter(pl.col("funcao_do_round") == f)["rounds"]
        print(f"  {f:<14} {v:.3f}" + (f"  ({int(n[0])} rounds)" if n.len() else "  (todas as funções)"))
    if fracas:
        print("  amostra fraca, caem na média geral:", ", ".join(f"{f} ({n})" for f, n in fracas))

    # O mesmo para o braco do SACRIFICIO (opcao (a) do Pedro, 2026-09-24): os
    # DOIS bracos do eixo carrega piano <-> baiter sao normalizados dentro da
    # funcao estrutural. Sem isto, o AWPer -- que paga a conta menos que a media
    # geral porque o trabalho dele e jogar de tras -- era empurrado para a ponta
    # do baiter: 16% dos jogador-partidas e 57% dos baiters.
    sac_por_funcao = {"_geral": float(isca["sacrificio"].mean())}
    sac_funcao = isca.group_by("funcao_do_round", maintain_order=True).agg(
        pl.len().alias("rounds"), pl.col("sacrificio").mean().alias("media"))
    for r in sac_funcao.iter_rows(named=True):
        if r["rounds"] >= MIN_ROUNDS_FUNCAO_NA_REFERENCIA:
            sac_por_funcao[r["funcao_do_round"]] = float(r["media"])
    print("\nsacrificio esperado por funcao (pagou a conta E o time colheu, por round):")
    for nome_f, v in sorted(sac_por_funcao.items(), key=lambda kv: -kv[1]):
        print(f"  {nome_f:<14} {v:.3f}")

    # PASSO 2: os componentes já com a isca comparada dentro da função
    pedacos = []
    for match_id, (tables, outputs, positions, areas, team_of, winners) in carregadas.items():
        _, resumo = compute_for_match(
            tables, outputs, positions, areas, team_of, winners,
            reference={"isca_por_funcao": isca_por_funcao,
                       "sacrificio_por_funcao": sac_por_funcao},
        )
        pedacos.append(resumo.with_columns(pl.lit(match_id).alias("match_id")))
        print(f"  {match_id}: {resumo.height} jogadores")

    componentes = pl.concat(pedacos, how="diagonal")
    referencia = build_reference(componentes)
    referencia["isca_por_funcao"] = isca_por_funcao
    referencia["sacrificio_por_funcao"] = sac_por_funcao

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
