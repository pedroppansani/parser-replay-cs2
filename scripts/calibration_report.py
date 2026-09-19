"""
Distribuição de cada índice de função, para recalibrar os pisos olhando o dado.

    py -3.12 -m scripts.calibration_report
    py -3.12 -m scripts.calibration_report --indice first_contact_share

Os pisos de `metrics/player_roles.py` (âncora 0,80, lurker 0,40, entry 0,32...)
foram escolhidos com 9 partidas de FACEIT. Com o corpus maior eles podem estar
em outro lugar da distribuição -- este relatório mostra o ANTES (as 9 de FACEIT)
e o DEPOIS (o corpus inteiro, e só as profissionais), com:

  - quartis e histograma em texto;
  - quantos jogadores ficam de cada lado do piso;
  - e, separado, os LÍDERES DE TIME: o rótulo exige liderar o próprio time E
    passar do piso, então é entre os líderes que o piso realmente filtra.

Não muda piso nenhum. Os pisos são do Pedro (CLAUDE.md, pontos de calibração).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from metrics.player_roles import TRAIT_SPECS  # noqa: E402

PROCESSED = PROJECT_ROOT / "data" / "processed"
MANIFESTO = PROJECT_ROOT / "data" / "manifest.json"

# Largura do histograma em caracteres e número de faixas.
LARGURA_BARRA = 40
N_FAIXAS = 12


def origem_das_partidas() -> dict[str, str]:
    dados = json.loads(MANIFESTO.read_text(encoding="utf-8"))["partidas"]
    return {m: v.get("origem", "?") for m, v in dados.items()}


def carrega(tabela: str) -> pl.DataFrame:
    """Uma tabela processada de todas as partidas, com match_id e origem."""
    origem = origem_das_partidas()
    partes = []
    for d in sorted(PROCESSED.glob("match_*")):
        p = d / f"{tabela}.parquet"
        if p.exists():
            df = pl.read_parquet(p)
            partes.append(df.with_columns(pl.lit(d.name).alias("match_id"),
                                          pl.lit(origem.get(d.name, "?")).alias("origem")))
    return pl.concat(partes, how="diagonal_relaxed") if partes else pl.DataFrame()


def histograma(valores: np.ndarray, piso: float | None, lo: float, hi: float) -> list[str]:
    """Histograma em texto; a faixa que contém o piso sai marcada."""
    if hi <= lo:
        hi = lo + 1e-9
    bordas = np.linspace(lo, hi, N_FAIXAS + 1)
    cont, _ = np.histogram(valores, bins=bordas)
    maior = max(1, int(cont.max()))
    linhas = []
    for i, n in enumerate(cont):
        a, b = bordas[i], bordas[i + 1]
        marca = " <- piso" if piso is not None and a <= piso < b else ""
        barra = "█" * int(round(LARGURA_BARRA * n / maior))
        linhas.append(f"    {a:8.3f} - {b:8.3f} | {barra:<{LARGURA_BARRA}} {n:4d}{marca}")
    return linhas


def resumo(nome: str, v: np.ndarray, piso: float | None, alto_e: bool = True) -> list[str]:
    if v.size == 0:
        return [f"  {nome}: sem dado"]
    q = np.quantile(v, [0, 0.25, 0.5, 0.75, 1])
    txt = (f"  {nome:<34} n={v.size:4d}  min {q[0]:.3f}  Q1 {q[1]:.3f}  mediana {q[2]:.3f}"
           f"  Q3 {q[3]:.3f}  max {q[4]:.3f}")
    if piso is not None:
        passa = int((v >= piso).sum()) if alto_e else int((v <= piso).sum())
        pct_piso = float((v < piso).mean())
        txt += f"\n  {'':<34} passam do piso {piso}: {passa} de {v.size} ({passa / v.size:.0%}) -- o piso está no percentil {pct_piso:.0%}"
    return [txt]


def lideres(df: pl.DataFrame, coluna: str) -> pl.DataFrame:
    """O maior valor de cada (partida, time): quem disputaria o rótulo."""
    return (df.drop_nulls(coluna).sort(coluna, descending=True)
            .group_by(["match_id", "team"], maintain_order=True).first())


def bloco(df: pl.DataFrame, coluna: str, piso: float | None, titulo: str) -> list[str]:
    linhas = [f"\n=== {titulo} ({coluna}) ==="]
    tudo = df.drop_nulls(coluna)
    if tudo.height == 0:
        return linhas + ["  sem dado"]
    lo, hi = float(tudo[coluna].min()), float(tudo[coluna].max())
    for rot, filtro in (("ANTES: 9 de FACEIT", pl.col("origem") == "faceit"),
                        ("DEPOIS: corpus inteiro", pl.lit(True)),
                        ("DEPOIS: só profissionais", pl.col("origem") == "profissional")):
        sub = tudo.filter(filtro)
        v = sub[coluna].to_numpy().astype(float)
        linhas += [f" {rot}"] + resumo("todos os jogadores", v, piso)
        if "team" in sub.columns:
            lv = lideres(sub, coluna)[coluna].to_numpy().astype(float)
            linhas += resumo("líderes de time (quem disputa)", lv, piso)
        if rot != "DEPOIS: só profissionais":
            linhas += histograma(v, piso, lo, hi)
    return linhas


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--indice", help="mostra só este índice (nome da coluna)")
    args = ap.parse_args()

    funcoes = carrega("player_roles")
    papeis = carrega("archetypes_summary")
    saida: list[str] = [
        "RELATÓRIO DE CALIBRAÇÃO -- distribuição de cada índice de função",
        f"partidas: {funcoes['match_id'].n_unique()} ({(funcoes.unique('match_id')['origem'] == 'faceit').sum()} de FACEIT)",
        "O rótulo exige LIDERAR o time e passar do piso: veja a linha dos líderes.",
    ]

    for t in TRAIT_SPECS:
        if args.indice and args.indice != t.column:
            continue
        saida += bloco(funcoes, t.column, t.floor, f"{t.label} -- piso {t.floor}")

    from metrics.archetypes import LIMIAR_CRITICO, PAPEIS, PAPEIS_CRITICOS
    for papel in PAPEIS:
        col = f"idx_{papel}"
        if args.indice and args.indice != col:
            continue
        if col in papeis.columns:
            piso = LIMIAR_CRITICO if papel in PAPEIS_CRITICOS else None
            saida += bloco(papeis, col, piso, f"papel {PAPEIS[papel][0]}"
                           + (f" -- limiar de destaque {piso}" if piso else " -- percentil, sem piso"))
    if "sacrifice_index" in papeis.columns and (not args.indice or args.indice == "sacrifice_index"):
        from metrics.archetypes import PISO_BAITER, PISO_CARREGA_PIANO
        saida += bloco(papeis, "sacrifice_index", PISO_CARREGA_PIANO,
                       f"eixo carrega piano <-> baiter -- piso do piano {PISO_CARREGA_PIANO}, do baiter {PISO_BAITER}")
        v = papeis.drop_nulls("sacrifice_index")["sacrifice_index"].to_numpy()
        saida.append(f"  lado do baiter: {int((v <= PISO_BAITER).sum())} de {v.size} jogador-partidas em {PISO_BAITER} ou abaixo")

    print("\n".join(saida))


if __name__ == "__main__":
    main()
