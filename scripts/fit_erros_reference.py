"""
Ajusta a régua da aba Perfil (fase 12): a referência ANÔNIMA do corpus, por função.

    py -3.12 -m scripts.fit_erros_reference            # mostra
    py -3.12 -m scripts.fit_erros_reference --gravar   # grava metrics/erros_reference.json

Duas réguas, só medianas, nenhum nome nem steamid (decisão 30):
- por tipo de erro, a mediana da contagem de ocorrências por jogador-partida, para quem tem a mesma
  função principal ("a mediana de quem joga suporte é 1");
- por métrica de ponto forte (metrics/erros.METRICAS_DE_PONTO_FORTE), a mediana do valor, por função.

Função com menos de MIN_JOGADOR_PARTIDAS_POR_FUNCAO jogador-partidas fica sem régua própria, e a página
usa a do corpus inteiro, dizendo isso. Refazer quando o corpus crescer, junto com as outras referências.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from metrics import erros as E  # noqa: E402

PROCESSED = PROJECT_ROOT / "data" / "processed"


def jogador_partidas() -> list[dict]:
    """Uma linha por (partida, jogador): função principal, contagem por tipo e valores das métricas."""
    linhas = []
    for d in sorted(PROCESSED.glob("match_*")):
        if not (d / E.ARQUIVO).exists() or not (d / "player_profile.parquet").exists():
            continue
        oc = pl.read_parquet(d / E.ARQUIVO).filter(pl.col("filtro").is_null())
        perfil = pl.read_parquet(d / "player_profile.parquet")
        resumo = pl.read_parquet(d / "structural_roles_summary.parquet")
        for p in perfil.sort("steamid").iter_rows(named=True):
            sid = int(p["steamid"])
            funcao = E.funcao_principal(resumo.filter(pl.col("steamid") == sid).to_dicts())
            dele = oc.filter(pl.col("steamid") == sid)
            cont = {t: dele.filter(pl.col("tipo") == t).height for t in E.TIPOS}
            valores = {c: p.get(c) for c, _, _ in E.METRICAS_DE_PONTO_FORTE
                       if p.get(c) is not None and not p.get(f"{c}_fraco")}
            linhas.append({"partida": d.name, "funcao": funcao, "contagens": cont, "valores": valores})
    return linhas


def ajusta(linhas: list[dict]) -> dict:
    funcoes = sorted({x["funcao"] for x in linhas if x["funcao"]})
    por_funcao = {f: [x for x in linhas if x["funcao"] == f] for f in funcoes}
    n_funcao = {f: len(v) for f, v in por_funcao.items()}
    validas = [f for f in funcoes if n_funcao[f] >= E.MIN_JOGADOR_PARTIDAS_POR_FUNCAO]

    def mediana(vs: list[float]) -> float | None:
        return float(statistics.median(vs)) if vs else None

    erros = {}
    for t in E.TIPOS:
        erros[t] = {E.TODAS: mediana([x["contagens"][t] for x in linhas])}
        for f in validas:
            erros[t][f] = mediana([x["contagens"][t] for x in por_funcao[f]])
    metricas = {}
    for c, _, _ in E.METRICAS_DE_PONTO_FORTE:
        metricas[c] = {E.TODAS: mediana([x["valores"][c] for x in linhas if c in x["valores"]])}
        for f in validas:
            m = mediana([x["valores"][c] for x in por_funcao[f] if c in x["valores"]])
            if m is not None:
                metricas[c][f] = m
    return {
        "_leia_isto": (
            "Régua da aba Perfil (fase 12): medianas do CORPUS por função principal, agregadas e ANÔNIMAS "
            "(nenhum nome, nenhum steamid). 'erros': contagem de ocorrências por jogador-partida de cada tipo "
            "de metrics/erros.py, depois dos filtros; 'metricas': valor das métricas de ponto forte. A chave "
            f"'{E.TODAS}' é o corpus inteiro, usado quando a função não tem régua própria. Refazer com "
            "scripts/fit_erros_reference.py quando o corpus crescer."),
        "n_partidas": len({x["partida"] for x in linhas}),
        "n_jogador_partidas": len(linhas),
        "min_jogador_partidas_por_funcao": E.MIN_JOGADOR_PARTIDAS_POR_FUNCAO,
        "jogador_partidas_por_funcao": n_funcao,
        "erros": erros,
        "metricas": metricas,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Ajusta a régua anônima da aba Perfil (fase 12).")
    ap.add_argument("--gravar", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    ref = ajusta(jogador_partidas())
    texto = json.dumps(ref, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.gravar:
        E.REFERENCIA_FILE.write_text(texto, encoding="utf-8", newline="\n")
        print(f"gravado {E.REFERENCIA_FILE.relative_to(PROJECT_ROOT).as_posix()} "
              f"({ref['n_jogador_partidas']} jogador-partidas, {ref['n_partidas']} partidas)")
    else:
        print(texto)


if __name__ == "__main__":
    main()
