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
import re
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
        # o rating sai por steamid; o rating oficial foi transcrito por nick, que é
        # o que a HLTV mostra -- mesma fonte de nome do elenco (resolve_teams)
        nick = dict(
            tabelas["ticks"].group_by("steamid").agg(pl.col("name").last()).iter_rows()
        )
        for j in resumo["jogadores"]:
            linhas.append({**j, "name": nick.get(j["steamid"]), "match_id": mid})
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


# Demo de FACEIT vem com nome de UUID ("1-0007ce25-...dem"); demo profissional
# vem com o slug do evento e do confronto. Demo dividida pelo GOTV (servidor
# reiniciou no meio do mapa) termina em "-p1.dem", "-p2.dem".
_FACEIT = re.compile(r"^\d-[0-9a-f]{8}-[0-9a-f]{4}-")
_DIVIDIDA = re.compile(r"-p(\d+)\.dem$")
_ARQUIVO_PRO = re.compile(r"^(?P<confronto>.+?-vs-.+?)-m(?P<mapa>\d+)-")


def identifica_origem(source_dem: str) -> dict:
    """Evento, confronto e se a partida serve para calibrar, a partir do caminho.

    Serve para o preenchimento do rating oficial ser uma busca de segundos na
    HLTV, e para marcar sozinho o que NÃO pode entrar na regressão:

    - FACEIT: a HLTV não publica rating para pug;
    - demo dividida: a HLTV avalia o mapa inteiro, e cada metade tem só parte das
      estatísticas. Casar o rating do mapa com uma metade ensinaria o modelo
      errado sem erro nenhum aparecer.
    """
    caminho = Path(source_dem.replace("\\", "/"))
    arquivo, pasta = caminho.name, caminho.parent.name
    vazio = {"evento": None, "confronto": None, "mapa_da_serie": None}

    if _FACEIT.match(arquivo):
        return {**vazio, "usar_na_calibracao": False,
                "motivo": "FACEIT: a HLTV nao publica rating para esta partida"}

    m = _ARQUIVO_PRO.match(arquivo)
    confronto = m.group("confronto") if m else None
    evento = None
    if confronto and f"-{confronto}-" in f"-{pasta}":
        evento = pasta[: pasta.find(confronto)].rstrip("-") or None
    info = {"evento": evento, "confronto": confronto,
            "mapa_da_serie": int(m.group("mapa")) if m else None}

    parte = _DIVIDIDA.search(arquivo)
    if parte:
        return {**info, "usar_na_calibracao": False,
                "motivo": (f"demo dividida (parte {parte.group(1)}): o rating oficial e do "
                           "mapa inteiro, esta demo tem so uma parte dos rounds")}
    return {**info, "usar_na_calibracao": True, "motivo": None}


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

        origem = identifica_origem(meta.get("source_dem", ""))
        usar, motivo = origem["usar_na_calibracao"], origem["motivo"]
        # demo dividida que já foi FUNDIDA (process_all_demos) é o mapa inteiro de
        # novo: volta a servir para calibrar
        if len(meta.get("source_parts") or []) > 1:
            usar, motivo = True, None
        # uma decisão manual já gravada no arquivo vale mais que a heurística
        if "usar_na_calibracao" in antigo:
            usar, motivo = antigo["usar_na_calibracao"], antigo.get("motivo", motivo)

        partidas[mid] = {
            "mapa": meta.get("map_name"),
            "placar": f"{insights['match']['score_a']}-{insights['match']['score_b']}",
            # Estes campos identificam a partida na HLTV. Sem eles nao da para
            # conferir de onde o numero veio.
            "hltv_match_id": antigo.get("hltv_match_id"),
            "evento": antigo.get("evento") or origem["evento"],
            "confronto": antigo.get("confronto") or origem["confronto"],
            "mapa_da_serie": antigo.get("mapa_da_serie") or origem["mapa_da_serie"],
            "usar_na_calibracao": usar,
            "motivo": motivo,
            # de onde veio o hltv_match_id e se ele foi conferido pelo placar
            "nota": antigo.get("nota"),
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
        # Trava explícita, não só "valor nulo": uma metade de demo dividida com o
        # rating do MAPA INTEIRO preenchido por engano corromperia a regressão
        # sem nenhum aviso -- o número parece válido, só não corresponde às
        # estatísticas daquela metade.
        if info.get("usar_na_calibracao") is False:
            continue
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
    - o erro reportado é o de TESTE, em validação deixa-uma-PARTIDA-fora: com 13
      partidas, separar só as 3 últimas faz o erro depender de quais 3 são;
    - o modelo é linear com seis coeficientes. Com ~10 linhas por partida, o teto
      razoável é esse: qualquer coisa mais complexa decora em vez de aprender;
    - a regressão roda sobre os sub-ratings NORMALIZADOS (`norm_*`), que é a
      escala em que os pesos são aplicados em `metrics/rating.py`. Nas unidades
      brutas o coeficiente não é peso: o Round Swing vive perto de zero e saía
      com 5,3, e não dava para comparar com os pesos provisórios;
    - os pesos são NÃO-NEGATIVOS. Kills, dano e multikills se correlacionam
      0,74-0,89 entre si, e a regressão livre resolvia a colinearidade dando peso
      NEGATIVO a kills (-0,14) -- "matar piora o rating" não é leitura de jogo, é
      a regressão trocando um sinal por outro quase igual;
    - o resultado vem sempre ao lado de duas referências, medidas do mesmo
      jeito: os pesos atuais como estão, e os pesos atuais só reescalados
      (a + b * rating). Se o ajuste completo não bate a reescala, o que está
      errado é a escala, não os pesos.
    """
    from scipy.optimize import nnls
    from sklearn.linear_model import LinearRegression

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

    nomes = list(PESOS_PROVISORIOS)
    colunas = [f"norm_{n}" for n in nomes]
    real = dados["rating_oficial"].to_numpy()

    def _nao_negativo(X, y):
        # a coluna de uns é o intercepto, que também fica >= 0
        w, _ = nnls(np.hstack([X, np.ones((len(X), 1))]), y)
        return w

    def _reescala(X, y):
        reg = LinearRegression().fit(X, y)
        return np.append(reg.coef_, reg.intercept_)

    def _deixa_uma_fora(ajusta, cols) -> dict:
        prev = np.zeros(dados.height)
        for mid in partidas_com_alvo:
            teste = (dados["match_id"] == mid).to_numpy()
            X = dados.select(cols).to_numpy()
            w = ajusta(X[~teste], real[~teste])
            prev[teste] = X[teste] @ w[:-1] + w[-1]
        return _erro(prev)

    def _erro(prev) -> dict:
        return {
            "erro_medio_absoluto": round(float(np.mean(np.abs(prev - real))), 3),
            "correlacao": round(float(np.corrcoef(prev, real)[0, 1]), 3),
        }

    w = _nao_negativo(dados.select(colunas).to_numpy(), real)
    return {
        "ajustou": True,
        "partidas": partidas_com_alvo,
        "n_jogador_partidas": dados.height,
        "validacao": "deixa uma partida fora",
        "pesos_atuais": _erro(dados["rating"].to_numpy()),
        "pesos_atuais_so_reescalados": _deixa_uma_fora(_reescala, ["rating"]),
        "pesos_ajustados": _deixa_uma_fora(_nao_negativo, colunas),
        # ajustados no conjunto inteiro; o erro acima é o de fora da amostra
        "pesos": {n: round(float(v), 3) for n, v in zip(nomes, w[:-1])},
        "intercepto": round(float(w[-1]), 3),
        "dispersao": {
            "desvio_do_rating_atual": round(float(dados["rating"].std()), 3),
            "desvio_do_oficial": round(float(np.std(real, ddof=1)), 3),
        },
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
