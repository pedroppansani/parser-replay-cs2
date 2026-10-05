"""Inventário de toda métrica por jogador que o projeto calcula (fase 7, item 7.1). Não muda nada.

Para cada coluna das tabelas por jogador gravadas em data/processed/ (e dos
campos por jogador do insights), quatro perguntas:

  1. o módulo que a calcula;
  2. se aparece na tela e onde (procura o nome do campo no template e no payload);
  3. se tem referência do corpus e amostra mínima;
  4. se tem gabarito (degrau da escada contra a HLTV) ou só invariante.

As variantes de uma mesma taxa do perfil (_n, _d, _ref, _fraco, _ct, _t) entram
como UMA linha: são o bruto, a régua e a marca da mesma métrica (decisão 7a).

Uso:
    py -3.12 -m pesquisa.inventario_metricas            # imprime a tabela em Markdown
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import polars as pl

RAIZ = Path(__file__).resolve().parents[1]
PARTIDA = RAIZ / "data" / "processed" / "match_01"
TEMPLATE = (RAIZ / "dashboard" / "web" / "template.html").read_text(encoding="utf-8")

# tabela -> módulo que a grava (o pipeline em scripts/process_demo.py e leitura/insights.py)
MODULO = {
    "adr_summary": "metrics/basic_metrics.py", "kast_summary": "metrics/basic_metrics.py",
    "trade_kills_summary": "metrics/basic_metrics.py", "utility_damage_summary": "metrics/basic_metrics.py",
    "grenades_summary": "metrics/grenades.py", "awp_summary": "metrics/awp_metrics.py",
    "crosshair_summary": "metrics/crosshair.py", "anchor_summary": "metrics/site_roles.py",
    "lurk_summary": "metrics/site_roles.py", "archetypes_summary": "metrics/archetypes.py",
    "structural_roles_summary": "metrics/structural_roles.py", "player_profile": "metrics/player_profile.py",
    "player_roles": "metrics/player_roles.py", "insights.players": "leitura/insights.py + metrics/rating.py",
}
IGNORAR = {"steamid", "name", "team", "match_id", "tickrate", "partidas", "side", "regua_origem",
           "regua_partidas", "regua_jogador_partidas", "home_area", "funcao_dominante", "modo_degradado",
           "role_evidence", "manual_role", "role_is_manual", "match_rounds"}
SUFIXOS = ("_n", "_d", "_ref", "_fraco")

# Degraus da escada (scripts/escada_validacao.py e o degrau 4, por série) e o rating.
ESCADA = {"adr": "degrau 3 (ADR)", "kast_pct": "degrau 3 (KAST)", "kast_rounds": "degrau 3 (KAST)",
          "total_kills": "degrau 1 (kills)", "kills_totais": "degrau 1 (kills)", "mortes": "degrau 1 (mortes)",
          "opening_kills": "degrau 4 (aberturas)", "multikill_rounds": "degrau 4 (rounds de multi-kill)",
          "clutch_wins": "degrau 4 (clutches)", "clutches": "degrau 4 (clutches)",
          "clutch_convertidos": "degrau 4 (clutches)", "rating": "rating contra a HLTV (catraca)"}
INVARIANTE = {"kast_pct": "KAST entre 0 e 100, sem nulo", "adr": "sem nulo", "total_damage": "sem nulo",
              "rounds_played": "sem nulo", "first_contact_share": "sem nulo", "awp_share": "sem nulo",
              "sacrifice_index": "sem nulo", "idx_carry": "sem nulo", "rating": "média acompanha a oficial"}


def _base(col: str) -> str:
    for s in SUFIXOS:
        if col.endswith(s):
            col = col[: -len(s)]
    return re.sub(r"_(ct|t)$", "", col)


def _na_tela(col: str) -> str:
    """Onde o campo aparece no template: a seção (função JS) que o lê."""
    secoes = [(m.start(), m.group(1)) for m in re.finditer(r"\(function (\w+)\(\)", TEMPLATE)]
    achados = set()
    for m in re.finditer(rf"[.\"']{re.escape(col)}\b", TEMPLATE):
        antes = [nome for pos, nome in secoes if pos < m.start()]
        achados.add(antes[-1] if antes else "cabeçalho")
    nomes = {"players": "Jogadores (tabela)", "roles": "Jogadores (funções)", "perfil": "Perfil",
             "wpchart": "Resumo (gráfico)", "swing": "Resumo (vantagem)"}
    return ", ".join(sorted(nomes.get(a, a) for a in achados)) or "não"


def _referencia(tabela: str, col: str, colunas: set[str]) -> str:
    if f"{col}_ref" in colunas:
        return "régua do corpus (perfil_reference) + bruto + amostra fraca"
    if tabela == "archetypes_summary" and col.startswith("idx_"):
        return "percentil global (archetype_reference)"
    if col == "rating":
        return "referência de escala (rating_reference) + amostra fraca"
    if tabela == "player_roles" and col in ("first_contact_share", "awp_share", "enemy_blind_por_round",
                                            "never_left_share", "off_team_relativo", "trade_share", "adr"):
        return "piso do rótulo + amostra mínima (decisão 39)"
    return "não"


def linhas() -> list[dict]:
    vistas, saida = set(), []
    tabelas = sorted(PARTIDA.glob("*_summary.parquet")) + [PARTIDA / "player_profile.parquet",
                                                           PARTIDA / "player_roles.parquet"]
    for f in tabelas:
        nome = f.stem
        colunas = set(pl.read_parquet(f).columns)
        for c in sorted(colunas):
            b = _base(c)
            if b in IGNORAR or c in IGNORAR or (b, nome) in vistas:
                continue
            vistas.add((b, nome))
            saida.append({"metrica": b, "tabela": nome, "modulo": MODULO.get(nome, "?"),
                          "tela": _na_tela(b), "referencia": _referencia(nome, b, colunas),
                          "gabarito": ESCADA.get(b) or (f"invariante: {INVARIANTE[b]}" if b in INVARIANTE else "não")})
    ins = json.loads((PARTIDA / "insights.json").read_text(encoding="utf-8"))
    for c in sorted(ins["players"][0]):
        if c in IGNORAR or any(c == l["metrica"] for l in saida):
            continue
        saida.append({"metrica": c, "tabela": "insights.players", "modulo": MODULO["insights.players"],
                      "tela": _na_tela(c), "referencia": _referencia("insights.players", c, set(ins["players"][0])),
                      "gabarito": ESCADA.get(c) or (f"invariante: {INVARIANTE[c]}" if c in INVARIANTE else "não")})
    return saida


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ls = linhas()
    print(f"{len(ls)} métricas por jogador; na tela: {sum(l['tela'] != 'não' for l in ls)}; "
          f"com referência: {sum(l['referencia'] != 'não' for l in ls)}; com gabarito ou invariante: "
          f"{sum(l['gabarito'] != 'não' for l in ls)}\n")
    print("| métrica | tabela | módulo | na tela | referência e amostra | gabarito ou invariante |")
    print("|---|---|---|---|---|---|")
    for l in ls:
        print(f"| `{l['metrica']}` | {l['tabela']} | {l['modulo']} | {l['tela']} | {l['referencia']} | {l['gabarito']} |")


if __name__ == "__main__":
    main()
