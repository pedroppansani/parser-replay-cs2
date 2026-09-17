"""
Ajusta o rating no CONJUNTO das partidas.

Dois ajustes diferentes, e só o primeiro roda hoje:

1. **Referência de escala** (`metrics/rating_reference.json`). As médias de cada
   sub-rating no corpus inteiro. Sem ela o rating cai para a média da própria
   partida, e aí toda partida tem média 1,00 por construção -- o número deixa de
   comparar jogadores de partidas diferentes, que é para o que ele serve.
   Mesmo padrão de `global_model.json` e `archetype_reference.json` (decisão 16).

2. **Pesos dos sub-ratings**, por regressão contra os ratings oficiais
   publicados. Este é o ajuste que valida a implementação, e ele depende de
   `data/reference/hltv_ratings.json` estar preenchido. Ver `--fit-pesos`.

Sobre o item 2, um aviso que não dá para contornar com código: as 9 demos do
corpus são partidas de FACEIT (arquivos identificados por UUID de FACEIT, e os
elencos são pugs, não line-ups profissionais). **A HLTV não publica rating para
partidas de FACEIT.** A calibração só faz sentido com demos de partidas oficiais
cobertas pela HLTV.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import polars as pl

from parsing.parser import kills_do_round_jogado
from metrics.rating import (
    ModeloDeRound,
    PESOS_PROVISORIOS,
    REFERENCIA_FILE,
    amostras_de_round,
    dispersao_de_referencia,
    grupo_do_round,
    rating,
)
from scripts.build_insights import resolve_teams, side_of_team

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HLTV_FILE = PROJECT_ROOT / "data" / "reference" / "hltv_ratings.json"

# Mínimo de partidas para a regressão contra os ratings oficiais fazer sentido.
#
# São seis coeficientes e dez jogadores por partida. A regra prática de 10 a 15
# observações por coeficiente pede 60 a 90 linhas de TREINO, ou seja 6 a 9
# partidas -- e ainda sobra a necessidade de um conjunto de teste separado por
# partida, que precisa de pelo menos 3 para o erro não ser uma partida só.
MIN_PARTIDAS_TREINO = 7
MIN_PARTIDAS_TESTE = 3
MIN_PARTIDAS_TOTAL = MIN_PARTIDAS_TREINO + MIN_PARTIDAS_TESTE


def carrega_partida(match_id: str) -> tuple:
    """Tabelas e contexto de uma partida já processada."""
    processed = PROJECT_ROOT / "data" / "processed" / match_id
    interim = PROJECT_ROOT / "data" / "interim" / match_id

    rounds = pl.read_parquet(processed / "rounds.parquet")
    kills = kills_do_round_jogado(pl.read_parquet(interim / "kills.parquet"), rounds)
    ticks = pl.read_parquet(interim / "ticks.parquet")
    blind = interim / "player_blind.parquet"

    tabelas = {
        "rounds": rounds,
        "kills": kills,
        "ticks": ticks,
        "damages": pl.read_parquet(interim / "damages.parquet"),
        "player_blind": pl.read_parquet(blind) if blind.exists() else None,
    }
    team_of, _ = resolve_teams(ticks)
    vencedor = {
        int(r["round_num"]): ("A" if r["winner"] == side_of_team("A", int(r["round_num"])) else "B")
        for r in rounds.iter_rows(named=True)
    }
    kast = pl.read_parquet(processed / "kast_summary.parquet")
    return tabelas, team_of, vencedor, kast


def partidas_disponiveis() -> list[str]:
    return sorted(
        d.name for d in (PROJECT_ROOT / "data" / "processed").glob("match_*")
        if (PROJECT_ROOT / "data" / "interim" / d.name / "kills.parquet").exists()
    )


def modelo_global(ids: list[str]) -> ModeloDeRound:
    """Um modelo de round só, ajustado no conjunto -- não um por partida.

    Mesmo motivo da decisão 11: um modelo por partida aprende as idiossincrasias
    daquela partida e os números deixam de ser comparáveis entre páginas.
    """
    Xs, ys = [], []
    for mid in ids:
        tabelas, team_of, vencedor, _ = carrega_partida(mid)
        grupos = grupo_do_round(tabelas["ticks"], tabelas["rounds"])
        X, y = amostras_de_round(
            tabelas["kills"], tabelas["rounds"], grupos, team_of, vencedor
        )
        if X.shape[0]:
            Xs.append(X)
            ys.append(y)
    if not Xs:
        return ModeloDeRound()
    return ModeloDeRound().treina(np.vstack(Xs), np.concatenate(ys))


def componentes_do_corpus(ids: list[str], modelo: ModeloDeRound) -> pl.DataFrame:
    """Os seis sub-ratings de cada jogador em cada partida, em unidade bruta."""
    linhas = []
    for mid in ids:
        tabelas, team_of, vencedor, kast = carrega_partida(mid)
        _, resumo = rating(tabelas, team_of, vencedor, kast, 64, modelo=modelo)
        for j in resumo["jogadores"]:
            linhas.append({**j, "match_id": mid})
    return pl.DataFrame(linhas, infer_schema_length=None)


def ajusta_referencia(ids: list[str]) -> dict:
    """Calcula e grava as médias de escala do conjunto."""
    modelo = modelo_global(ids)
    comp = componentes_do_corpus(ids, modelo)

    medias = {
        nome: float(comp[f"sub_{nome}"].mean())
        for nome in PESOS_PROVISORIOS
    }
    desvios = {
        nome: float(comp[f"sub_{nome}"].std() or 0.0)
        for nome in PESOS_PROVISORIOS
    }
    referencia = {
        "medias": medias,
        "desvios": desvios,
        "dispersao_alvo": dispersao_de_referencia(medias, desvios),
        "n_partidas": len(ids),
        "n_jogador_partidas": comp.height,
        "modelo_de_round": modelo.metricas,
        "pesos_usados": dict(PESOS_PROVISORIOS),
        "aviso": (
            "Medias de escala do conjunto. Os PESOS ainda sao provisorios: os "
            "oficiais da HLTV sao fechados e os daqui so podem ser estimados por "
            "regressao contra ratings publicados (--fit-pesos)."
        ),
    }
    REFERENCIA_FILE.write_text(
        json.dumps(referencia, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return referencia


def esqueleto_hltv(ids: list[str]) -> Path:
    """Cria o arquivo para o Pedro preencher com os ratings oficiais.

    O esqueleto já vem com os nicks de cada partida, para ele só encostar o
    número ao lado em vez de transcrever elenco.
    """
    HLTV_FILE.parent.mkdir(parents=True, exist_ok=True)
    existente = (
        json.loads(HLTV_FILE.read_text(encoding="utf-8")) if HLTV_FILE.exists() else {}
    )
    partidas = existente.get("partidas", {})

    for mid in ids:
        processed = PROJECT_ROOT / "data" / "processed" / mid
        meta = json.loads((processed / "match_meta.json").read_text(encoding="utf-8"))
        insights = json.loads((processed / "insights.json").read_text(encoding="utf-8"))
        rosters = insights["match"]["rosters"]

        antigo = partidas.get(mid, {})
        jogadores = antigo.get("jogadores", {})
        for nome in rosters["A"] + rosters["B"]:
            jogadores.setdefault(nome, None)

        partidas[mid] = {
            "mapa": meta.get("map_name"),
            "placar": f"{insights['match']['score_a']}-{insights['match']['score_b']}",
            # Estes dois campos identificam a partida na HLTV. Sem eles nao da
            # para conferir de onde o numero veio.
            "hltv_match_id": antigo.get("hltv_match_id"),
            "evento": antigo.get("evento"),
            "jogadores": jogadores,
        }

    conteudo = {
        "_leia_isto": (
            "Preencha o rating oficial publicado de cada jogador. Deixe null o "
            "que nao tiver. Partidas de FACEIT NAO tem rating na HLTV -- so "
            "partidas oficiais cobertas por ela servem para a calibracao."
        ),
        "_fonte_da_metodologia": "https://www.hltv.org/news/41283/introducing-rating-30",
        "partidas": partidas,
    }
    HLTV_FILE.write_text(json.dumps(conteudo, ensure_ascii=False, indent=2), encoding="utf-8")
    return HLTV_FILE


def _linhas_com_alvo(comp: pl.DataFrame) -> pl.DataFrame:
    """Junta os componentes calculados com o rating oficial, quando existe."""
    if not HLTV_FILE.exists():
        return comp.head(0)
    dados = json.loads(HLTV_FILE.read_text(encoding="utf-8")).get("partidas", {})
    alvo = []
    for mid, info in dados.items():
        for nome, valor in (info.get("jogadores") or {}).items():
            if valor is not None:
                alvo.append({"match_id": mid, "name": nome, "rating_oficial": float(valor)})
    if not alvo:
        return comp.head(0)
    return comp.join(pl.DataFrame(alvo), on=["match_id", "name"], how="inner")


def ajusta_pesos(ids: list[str]) -> dict:
    """Regressão dos componentes contra os ratings oficiais publicados.

    Regras que fazem a diferença entre validar e se enganar:

    - a divisão treino/teste é por PARTIDA, nunca por jogador. Com o mesmo jogo
      dos dois lados da divisão, o erro de teste fica otimista e não significa
      nada -- os dez jogadores de uma partida compartilham o mesmo adversário,
      o mesmo mapa e o mesmo placar;
    - o erro reportado é o de TESTE;
    - o modelo é linear com seis coeficientes. Com ~10 linhas por partida, o teto
      razoável é esse: qualquer coisa mais complexa decora em vez de aprender.
    """
    modelo = modelo_global(ids)
    comp = componentes_do_corpus(ids, modelo)
    dados = _linhas_com_alvo(comp)

    partidas_com_alvo = sorted(set(dados["match_id"].to_list())) if dados.height else []
    if len(partidas_com_alvo) < MIN_PARTIDAS_TOTAL:
        return {
            "ajustou": False,
            "partidas_com_rating_oficial": len(partidas_com_alvo),
            "minimo": MIN_PARTIDAS_TOTAL,
            "motivo": (
                f"Preciso de pelo menos {MIN_PARTIDAS_TOTAL} partidas com rating "
                f"oficial ({MIN_PARTIDAS_TREINO} de treino + {MIN_PARTIDAS_TESTE} "
                f"de teste). Hoje ha {len(partidas_com_alvo)}."
            ),
        }

    from sklearn.linear_model import LinearRegression

    corte = len(partidas_com_alvo) - MIN_PARTIDAS_TESTE
    treino_ids = set(partidas_com_alvo[:corte])
    nomes = list(PESOS_PROVISORIOS)
    colunas = [f"sub_{n}" for n in nomes]

    treino = dados.filter(pl.col("match_id").is_in(list(treino_ids)))
    teste = dados.filter(~pl.col("match_id").is_in(list(treino_ids)))

    reg = LinearRegression().fit(
        treino.select(colunas).to_numpy(), treino["rating_oficial"].to_numpy()
    )
    prev = reg.predict(teste.select(colunas).to_numpy())
    real = teste["rating_oficial"].to_numpy()

    return {
        "ajustou": True,
        "partidas_treino": sorted(treino_ids),
        "partidas_teste": sorted(set(teste["match_id"].to_list())),
        "coeficientes": dict(zip(nomes, reg.coef_.round(4).tolist())),
        "intercepto": float(reg.intercept_),
        "erro_medio_absoluto_teste": float(np.mean(np.abs(prev - real))),
        "correlacao_teste": float(np.corrcoef(prev, real)[0, 1]) if len(real) > 1 else None,
        "n_teste": int(len(real)),
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Ajusta a escala e os pesos do rating.")
    p.add_argument("--fit-pesos", action="store_true",
                   help="tenta a regressão contra os ratings oficiais")
    p.add_argument("--esqueleto", action="store_true",
                   help="(re)cria data/reference/hltv_ratings.json para preencher")
    args = p.parse_args()

    ids = partidas_disponiveis()
    print(f"{len(ids)} partidas processadas: {', '.join(ids)}\n")

    if args.esqueleto:
        caminho = esqueleto_hltv(ids)
        print(f"Esqueleto em {caminho}")
        return

    if args.fit_pesos:
        r = ajusta_pesos(ids)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return

    ref = ajusta_referencia(ids)
    print("Referência de escala gravada em", REFERENCIA_FILE)
    print(json.dumps(ref, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
