"""
Exporta um único JSON compacto com tudo que o painel web consome.

Separado do dashboard Streamlit de propósito: o Streamlit é a ferramenta de
trabalho (lê os parquet direto e mostra tudo), e o painel web é a peça de
portfólio — precisa ser leve, autocontido e sem dependência de servidor.

Uso:
    python -m scripts.export_web_payload match_01
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import polars as pl

from clustering.playstyle import describe_clusters, load_cluster_names
from metrics.player_profile import cards_de_estilo
from metrics.structural_roles import FUNCOES, texto_empate
from scripts.narrative import descreve_jogador

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _perfil_acumulado(steamids: list[int]) -> list[dict]:
    """Perfil somado de todas as partidas, só para quem jogou ESTA partida.

    O recorte existe por peso: são 73 jogadores no conjunto e ~160 colunas por
    jogador, e mandar todos em cada página somava 400KB de gente que aquela
    página nunca mostra.

    Ausente é caso legítimo: numa primeira partida processada o acumulado ainda
    não existe, e a interface cai para o perfil da partida. Ver
    scripts/build_player_profiles.py.
    """
    caminho = PROJECT_ROOT / "data" / "player_profiles" / "summary.parquet"
    if not caminho.exists():
        return []
    return pl.read_parquet(caminho).filter(pl.col("steamid").is_in(steamids)).to_dicts()


def build(match_id: str) -> Path:
    processed = PROJECT_ROOT / "data" / "processed" / match_id
    insights = json.loads((processed / "insights.json").read_text(encoding="utf-8"))

    def rd(name: str) -> pl.DataFrame:
        return pl.read_parquet(processed / f"{name}.parquet")

    # --- heatmap: arredonda pra reduzir bytes; é textura, não medição ---
    heat = rd("heatmap_bins").select(
        pl.col("side"),
        pl.col("x").round(0).cast(pl.Int32),
        pl.col("y").round(0).cast(pl.Int32),
        pl.col("samples").cast(pl.Int32),
    )

    # --- dano por round de cada jogador, pra sparkline ---
    adr_round = rd("adr_per_round").select(["round_num", "name", "damage"])
    damage_by_player: dict[str, list[int]] = {}
    for row in adr_round.sort("round_num").iter_rows(named=True):
        damage_by_player.setdefault(row["name"], []).append(int(row["damage"]))

    kast_round = rd("kast_per_round").select(["round_num", "name", "kast_round"])
    kast_by_player: dict[str, list[int]] = {}
    for row in kast_round.sort("round_num").iter_rows(named=True):
        kast_by_player.setdefault(row["name"], []).append(int(bool(row["kast_round"])))

    clusters = rd("cluster_assignments").select(
        pl.col("cluster"),
        pl.col("name"),
        pl.col("round_num"),
        pl.col("pca_1").round(3),
        pl.col("pca_2").round(3),
        pl.col("damage").cast(pl.Int32),
    )
    cluster_profiles = rd("cluster_profiles")
    # Descrição em português de cada grupo. Sem ela o painel mostrava "Cluster 0"
    # e um gráfico de pontos com eixos de PCA -- verdadeiro e ilegível.
    #
    # Sai do perfil GLOBAL, não do perfil desta partida: o modelo é um só para as
    # nove (ver decisão 11 do CLAUDE.md), então o grupo 3 tem que significar a
    # mesma coisa em todas as páginas. Descrever pelo recorte da partida fazia o
    # mesmo grupo mudar de descrição de uma página para a outra.
    perfil_global = PROJECT_ROOT / "data" / "global_clusters" / "cluster_profiles.parquet"
    cluster_descriptions = (
        describe_clusters(pl.read_parquet(perfil_global))
        if perfil_global.exists()
        else describe_clusters(cluster_profiles)
    )

    crosshair = rd("crosshair_summary").select(
        ["name", "crosshair_score", "height_score", "direction_score",
         "median_enemy_aim_error_deg", "median_prefire_match_deg"]
    )
    awp = rd("awp_summary")
    awp_rounds = rd("awp_per_round").filter(pl.col("engagement_tick").is_not_null()).select(
        ["round_num", "name", "side", "time_to_first_shot_s", "net_displacement",
         "slow_fraction", "style", "outcome", "shot_place"]
    )
    setup_dev = rd("setup_deviation")
    standard_setup = rd("standard_setup")

    roles = rd("player_roles").select(
        ["name", "team", "role", "role_evidence", "role_is_manual", "adr", "kast_pct",
         "median_first_contact_s", "first_contact_share", "survival_rate",
         "avg_distance_from_team", "trade_share", "awp_share", "flash_thrown",
         "enemies_flashed", "enemy_blind_seconds", "team_blind_seconds", "flash_assists",
         "smoke_thrown", "utility_damage", "nades_per_round"]
    )
    traits = rd("player_traits").select(["name", "team", "trait", "label", "evidence", "priority"])
    grenades = rd("grenades_summary")

    perfil = rd("player_profile")

    # Função estrutural por lado. Vai junto do perfil comportamental de
    # propósito: são duas leituras independentes do mesmo jogador -- o que ele
    # FAZ no round (aqui) e COMO ele faz (o perfil). Ver metrics/structural_roles.py.
    resumo_funcoes = rd("structural_roles_summary")
    # Empate na função dominante (structural_roles.MARGEM_EMPATE_FUNCAO_ROUNDS):
    # o texto com as concentrações lado a lado sai pronto do Python (decisão 18).
    funcoes = resumo_funcoes.select(
        ["steamid", "name", "side", "funcao", "rounds_na_funcao", "rounds_no_lado",
         "concentracao", "amostra_fraca"]
    ).with_columns(pl.Series("texto_empate", [texto_empate(r) for r in resumo_funcoes.iter_rows(named=True)],
                             dtype=pl.String))

    def com_descricao(linhas: list[dict]) -> list[dict]:
        """Anexa a leitura em português de cada perfil.

        Gerada em Python e não no template pelo mesmo motivo das frases dos cards
        (decisão 18 do CLAUDE.md): assim a regra "característica sem denominador
        suficiente não vira afirmação" é testável.
        """
        for linha in linhas:
            linha["descricao"] = descreve_jogador(linha)
        return linhas

    insights["player_profile"] = com_descricao(insights.get("player_profile", []))

    payload = {
        **insights,
        "heatmap": heat.to_dicts(),
        "damage_by_player": damage_by_player,
        "kast_by_player": kast_by_player,
        # As atribuições round a round e os perfis de grupo saíram do payload
        # junto com a seção que os desenhava: eram 220 linhas por página que
        # ninguém mais lê. O que fica é a DESCRIÇÃO de cada grupo, que a aba
        # Perfil usa para dizer o jeito de jogar mais frequente do jogador.
        "cluster_descriptions": cluster_descriptions.to_dicts(),
        # Os nomes que o Pedro deu aos grupos, se deu. Sem isto no payload, o
        # cluster_names.json nunca chegava à página e a nomeação não teria efeito
        # nenhum -- o arquivo existiria só para o dashboard local.
        "cluster_names": load_cluster_names(),
        # Quem joga em cada grupo: top 3 por fração dos próprios rounds, com o
        # bruto ("7 de 22 rounds — 32%"), e quem não tem grupo dominante.
        "cards_de_estilo": cards_de_estilo(rd("cluster_assignments")),
        # Perfil acumulado do jogador em TODAS as partidas processadas. Vai junto
        # do perfil desta partida porque a interface precisa deixar claro sobre
        # quantas partidas e quantos rounds cada taxa foi montada -- 40% em 22
        # rounds e 40% em 180 não são a mesma afirmação.
        "structural_roles": funcoes.to_dicts(),
        "structural_role_labels": {k: v[0] for k, v in FUNCOES.items()},
        "player_profile_summary": com_descricao(
            _perfil_acumulado(perfil["steamid"].to_list())
        ),
        "crosshair": crosshair.to_dicts(),
        "awp": awp.to_dicts(),
        "awp_rounds": awp_rounds.to_dicts(),
        "setup_deviation": setup_dev.to_dicts(),
        "standard_setup": standard_setup.to_dicts(),
        "roles": roles.to_dicts(),
        "traits": traits.to_dicts(),
        "grenades": grenades.to_dicts(),
    }

    out = processed / "web_payload.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str), encoding="utf-8")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Exporta o JSON consumido pelo painel web.")
    parser.add_argument("match_id", type=str)
    args = parser.parse_args()
    out = build(args.match_id)
    print(f"{out}  ({out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
