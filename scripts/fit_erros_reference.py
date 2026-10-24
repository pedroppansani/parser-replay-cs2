"""
Ajusta a régua da aba Perfil (fase 12b): a referência ANÔNIMA do corpus, por (lado, função).

    py -3.12 -m scripts.fit_erros_reference            # mostra
    py -3.12 -m scripts.fit_erros_reference --gravar   # grava metrics/erros_reference.json

Um jogador-lado é um jogador numa partida, num dos lados. A célula (lado, função) reúne os jogador-lados
com a mesma função no mesmo lado; "__todas__" é o lado inteiro. Os lados nunca se misturam. Guarda:
- por tipo de erro, o HISTOGRAMA das contagens por jogador-lado ({contagem: quantos}), do qual a página
  tira o percentil (metrics.erros.PERCENTIL_PONTO_A_MELHORAR) e a mediana;
- por métrica de ponto forte (metrics/erros/__init__.py: METRICAS_DE_PONTO_FORTE), recalculada só com os rounds do lado,
  a mediana do valor (só valores medidos e sem amostra fraca).
Nenhum nome nem steamid (decisão 30). Célula com menos de MIN_REF_LADO_FUNCAO jogador-lados não é usada
pela página (vale o lado inteiro), mas fica registrada com o seu n. Refazer quando o corpus crescer, junto
com as outras referências.
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

def jogador_lados(processed: Path = PROCESSED) -> list[dict]:
    """Uma linha por (partida, jogador, lado): lado, função, contagem por tipo e valores das métricas."""
    linhas = []
    for d in sorted(processed.glob("match_*")):
        precisa = (E.ARQUIVO, "structural_roles_summary.parquet", "player_profile_rounds.parquet",
                   "impacto_per_round.parquet")
        if not all((d / f).exists() for f in precisa):
            continue
        oc = pl.read_parquet(d / E.ARQUIVO).filter(pl.col("filtro").is_null())
        resumo = pl.read_parquet(d / "structural_roles_summary.parquet")
        por_lado = E.metricas_por_lado(pl.read_parquet(d / "player_profile_rounds.parquet"),
                                       pl.read_parquet(d / "impacto_per_round.parquet"))
        for r in resumo.sort(["steamid", "side"]).iter_rows(named=True):
            sid, lado = int(r["steamid"]), r["side"]
            dele = oc.filter((pl.col("steamid") == sid) & (pl.col("side") == lado))
            cont = {t: dele.filter(pl.col("tipo") == t).height for t in E.TIPOS}
            valores = {c: v for c, (v, _, den) in por_lado.get((sid, lado), {}).items()
                       if v is not None and not E.amostra_fraca(c, den)}
            linhas.append({"partida": d.name, "lado": lado, "funcao": r["funcao"], "contagens": cont,
                           "valores": valores})
    return linhas


def celulas_do_lado(linhas: list[dict], lado: str) -> dict[str, list[dict]]:
    do_lado = [x for x in linhas if x["lado"] == lado]
    celulas = {E.TODAS: do_lado}
    for f in sorted({x["funcao"] for x in do_lado if x["funcao"]}):
        celulas[f] = [x for x in do_lado if x["funcao"] == f]
    return celulas


def ajusta(linhas: list[dict]) -> dict:
    n_celula, erros, metricas = {}, {t: {} for t in E.TIPOS}, {c: {} for c, _, _ in E.METRICAS_DE_PONTO_FORTE}
    for lado in E.LADOS:
        celulas = celulas_do_lado(linhas, lado)
        n_celula[lado] = {f: len(v) for f, v in celulas.items()}
        for t in E.TIPOS:
            erros[t][lado] = {}
            for f, v in celulas.items():
                hist: dict[str, int] = {}
                for x in v:
                    k = str(x["contagens"][t])
                    hist[k] = hist.get(k, 0) + 1
                erros[t][lado][f] = {"n": len(v), "hist": dict(sorted(hist.items(), key=lambda kv: int(kv[0])))}
        for c in metricas:
            metricas[c][lado] = {}
            for f, v in celulas.items():
                vals = [x["valores"][c] for x in v if c in x["valores"]]
                if vals:
                    metricas[c][lado][f] = {"n": len(v), "n_valores": len(vals),
                                            "mediana": float(statistics.median(vals))}
    return {
        "_leia_isto": (
            "Régua da aba Perfil (fase 12b): CORPUS por (lado, função), agregada e ANÔNIMA (nenhum nome, nenhum "
            "steamid). Um jogador-lado é um jogador numa partida, num dos lados; os lados nunca se misturam. "
            "'erros': histograma das contagens de cada tipo de metrics/erros.py por jogador-lado, depois dos "
            "filtros; 'metricas': mediana das métricas de ponto forte recalculadas só com os rounds do lado. "
            f"A chave '{E.TODAS}' é o lado inteiro, usado quando a célula (lado, função) tem menos de "
            "min_ref_lado_funcao jogador-lados. Refazer com scripts/fit_erros_reference.py quando o corpus crescer."),
        "n_partidas": len({x["partida"] for x in linhas}),
        "n_jogador_lados": len(linhas),
        "min_ref_lado_funcao": E.MIN_REF_LADO_FUNCAO,
        "jogador_lados_por_celula": n_celula,
        "erros": erros,
        "metricas": metricas,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Ajusta a régua anônima da aba Perfil (fase 12b).")
    ap.add_argument("--gravar", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    ref = ajusta(jogador_lados())
    texto = json.dumps(ref, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.gravar:
        E.REFERENCIA_FILE.write_text(texto, encoding="utf-8", newline="\n")
        print(f"gravado {E.REFERENCIA_FILE.relative_to(PROJECT_ROOT).as_posix()} "
              f"({ref['n_jogador_lados']} jogador-lados, {ref['n_partidas']} partidas)")
    else:
        print(texto)


if __name__ == "__main__":
    main()
