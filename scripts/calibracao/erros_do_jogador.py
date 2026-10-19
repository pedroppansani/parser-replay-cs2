"""Seção 7 do MATERIAL_DE_CALIBRACAO.md: "Erros na aba Perfil" (fase 12, item 12.4; refeita na fase 18).

    py -3.12 -m scripts.calibracao.erros_do_jogador                    # reescreve a seção 7 no material
    py -3.12 -m scripts.calibracao.erros_do_jogador --sortear-de-novo  # idem, refazendo TODOS os exemplos
    py -3.12 -m scripts.calibracao.erros_do_jogador --tabela           # só a tabela de ocorrências por tipo

Lê as ocorrências gravadas (`data/processed/<partida>/erros_do_jogador.parquet`, de
metrics/erros/__init__.py: build) e, para as varreduras das constantes, recalcula cada partida
com outro valor (metrics/erros/__init__.py: ocorrencias aceita as constantes como argumento), uma
partida por processo (cada partida devolve só contagens; a soma é feita na ordem das
partidas, então o resultado não depende do paralelo).

Para cada constante: o valor proposto com a origem, o histograma no corpus e quantas
ocorrências cada tipo teria no valor mais baixo e no mais alto de uma faixa razoável.

EXEMPLOS FIXADOS (fase 18). Os 10 exemplos de cada tipo ficam gravados em
`scripts/calibracao/exemplos_fixados.json` (versionado): tipo, partida, round, tick,
jogador, aliado, semente e a data do sorteio. Ao rodar de novo, todo exemplo fixado
que ainda é ocorrência pelas regras atuais FICA; só os que deixaram de ser são
trocados, sorteados com a mesma semente, e o material marca "(substituído em <data>:
<motivo>)". `--sortear-de-novo` refaz todos e só se usa quando as definições mudam.
Depois que o Pedro começa a responder, os exemplos não podem trocar sem ele saber.
"""
from __future__ import annotations

import datetime
import io
import json
import math
import random
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import polars as pl

from metrics import erros as E

RAIZ = Path(__file__).resolve().parents[2]
PROCESSED = RAIZ / "data" / "processed"
MATERIAL = RAIZ / "MATERIAL_DE_CALIBRACAO.md"
TITULO_DA_SECAO = "## 7. Erros na aba Perfil"
FIXADOS = Path(__file__).resolve().parent / "exemplos_fixados.json"

# Sorteio dos exemplos: semente fixa (decisão 28) e no máximo 2 por partida (pedido 12.4).
SEMENTE_DOS_EXEMPLOS = 20261013
EXEMPLOS_POR_TIPO = 10
MAX_EXEMPLOS_POR_PARTIDA = 2

# O commit com as ocorrências da regra ANTERIOR: a tabela "antes -> depois" compara com ele. Fase 18b: o
# "antes" é a fase 18 (o merge d02b0e7e, na main b3efc9da); na fase 18 era 622f7ab1 (a regra da fase 12).
ANTES = "b3efc9da"
ROTULO_DO_ANTES = "fase 18"
TIPO_ANTIGO: dict = {}

# Faixas razoáveis de cada constante (o mais baixo e o mais alto que ainda fazem sentido de jogo).
FAIXAS = {
    "dist_troca": ("DIST_TROCA", 400.0, 800.0, "unidades"),
    "s_duelo": ("S_DUELO", 1.0, 4.0, "s"),
    "seg_aliado": ("SEG_CEGUEIRA_ALIADO", 5.0, 20.0, "s"),
    "seg_uma": ("SEG_CEGUEIRA_ALIADO_UMA", 2.0, 4.0, "s"),
    "dano_aliado": ("DANO_UTILIDADE_ALIADO", 25.0, 100.0, "de dano"),
    "recuo_minimo": ("MIN_RECUO_BAIT", 32.0, 128.0, "unidades"),
    "min_tempo": ("MIN_TEMPO_VISIVEL", 0.25, 1.0, "s"),
    "meio_fov": ("MEIO_FOV_GRAUS", 45.0, 60.0, "graus"),
    "limiar_round": ("LIMIAR_ROUND_GANHO / LIMIAR_ROUND_PERDIDO", 0.90, 0.98, "de chance"),
    "cone": ("CONE_DO_TIRO_GRAUS", 3.0, 10.0, "graus"),
}


def _valor_atual() -> dict:
    from metrics.erros import visao as V
    return {"dist_troca": E.DIST_TROCA, "s_duelo": E.S_DUELO, "seg_aliado": E.SEG_CEGUEIRA_ALIADO,
            "seg_uma": E.SEG_CEGUEIRA_ALIADO_UMA, "dano_aliado": E.DANO_UTILIDADE_ALIADO,
            "recuo_minimo": E.MIN_RECUO_BAIT, "min_tempo": E.MIN_TEMPO_VISIVEL, "meio_fov": V.MEIO_FOV_GRAUS, "limiar_round": E.LIMIAR_ROUND_GANHO,
            "cone": E.CONE_DO_TIRO_GRAUS}


def partidas() -> list[str]:
    return sorted(d.name for d in PROCESSED.glob("match_*") if (d / E.ARQUIVO).exists())


def corpus() -> pl.DataFrame:
    return pl.concat([pl.read_parquet(PROCESSED / m / E.ARQUIVO) for m in partidas()], how="vertical")


def tabela_por_tipo(oc: pl.DataFrame) -> list[str]:
    """Antes dos filtros, depois dos filtros e por nível, um tipo por linha."""
    linhas = ["| tipo | candidatos | depois dos filtros | explícito | depende da tática | saiu pelos filtros (motivo: n) |",
              "|---|---|---|---|---|---|"]
    for t in E.TIPOS:
        o = oc.filter(pl.col("tipo") == t)
        dep = o.filter(pl.col("filtro").is_null())
        fora = (o.filter(pl.col("filtro").is_not_null()).group_by("filtro", maintain_order=True).len()
                .sort(["len", "filtro"], descending=[True, False]))
        motivos = "; ".join(f"{r[0]}: {r[1]}" for r in fora.iter_rows()) or "—"
        linhas.append(f"| {E.TITULOS[t]} | {o.height} | {dep.height} | "
                      f"{dep.filter(pl.col('nivel') == E.EXPLICITO).height} | "
                      f"{dep.filter(pl.col('nivel') == E.DEPENDE).height} | {motivos} |")
    linhas.append("| Utilidade no bolso | não criado | — | — | — | o inventário na hora da morte não existe no dado (decisão 46) |")
    return linhas


# --- Antes -> depois (fase 18) ----------------------------------------------------------------------

def _antigas() -> pl.DataFrame | None:
    """As ocorrências da regra antiga (o commit ANTES), lidas do git."""
    tabelas = []
    for m in partidas():
        r = subprocess.run(["git", "show", f"{ANTES}:data/processed/{m}/{E.ARQUIVO}"], cwd=RAIZ,
                           capture_output=True)
        if r.returncode != 0:
            return None
        tabelas.append(pl.read_parquet(io.BytesIO(r.stdout)))
    return pl.concat(tabelas, how="vertical") if tabelas else None


CHAVE = ["match_id", "round_num", "tick", "steamid"]


def tabela_antes_depois(oc: pl.DataFrame, antigas: pl.DataFrame | None) -> list[str]:
    if antigas is None:
        return ["(sem o commit da regra antiga no git: a tabela não pôde ser feita)"]
    out = ["| tipo | antes | depois | seguem | saíram | por qual motivo (n) | entraram | situação corrigida |",
           "|---|---|---|---|---|---|---|---|"]
    for t in E.TIPOS:
        velhas = antigas.filter((pl.col("tipo") == TIPO_ANTIGO.get(t, t)) & pl.col("filtro").is_null())
        novas = oc.filter(pl.col("tipo") == t)
        chave = CHAVE + (["aliado_steamid"] if t in (E.NAO_TROCOU, E.POSSIVEL_BAIT, E.PERDEU_A_TROCA) else [])
        v = velhas.select(chave + ["vivos_time", "vivos_adversario"]).unique(subset=chave, keep="first", maintain_order=True)
        n = novas.select(chave + ["filtro", pl.col("vivos_time").alias("vt_novo"),
                                  pl.col("vivos_adversario").alias("va_novo")]).unique(subset=chave, keep="first",
                                                                                       maintain_order=True)
        j = v.join(n, on=chave, how="left")
        seguem = j.filter(pl.col("vt_novo").is_not_null() & pl.col("filtro").is_null())
        sairam = j.filter(pl.col("vt_novo").is_null() | pl.col("filtro").is_not_null()).with_columns(
            pl.col("filtro").fill_null("deixou de ser candidato"))
        motivos = (sairam.group_by("filtro", maintain_order=True).len().sort(["len", "filtro"], descending=[True, False]))
        txt = "; ".join(f"{r[0]}: {r[1]}" for r in motivos.iter_rows()) or "—"
        depois = novas.filter(pl.col("filtro").is_null())
        entraram = depois.select(chave).join(v.select(chave), on=chave, how="anti").height
        corrigida = seguem.filter((pl.col("vivos_time") != pl.col("vt_novo"))
                                  | (pl.col("vivos_adversario") != pl.col("va_novo"))).height
        out.append(f"| {E.TITULOS[t]} | {velhas.height} | {depois.height} | {seguem.height} | {sairam.height} | {txt} | "
                   f"{entraram} | {corrigida} |")
    return out


# --- Medidas e varreduras, uma partida por processo ---------------------------------------------------

def _contagem(oc: pl.DataFrame) -> dict:
    tot = {t: 0 for t in E.TIPOS}
    for t, n in oc.filter(pl.col("filtro").is_null()).group_by("tipo", maintain_order=True).len().iter_rows():
        tot[t] += n
    return tot


def _mede_partida(m: str) -> dict:
    """Tudo o que a seção 7.1 precisa de UMA partida: as medidas dos histogramas e as contagens de cada
    varredura. Devolve só números e tabelas pequenas, para a soma ser feita na ordem das partidas."""
    from metrics.erros import visao as V
    p = E.carrega_partida(m)
    ix = E._Indice(p)
    base = E.ocorrencias(p)
    med: dict = {k: [] for k in ("dist_troca", "s_duelo", "seg_aliado", "seg_uma", "dano_aliado", "recuo_minimo",
                                 "meio_fov", "limiar_round", "cone", "min_tempo")}
    # DIST_TROCA: distância de cada aliado vivo a quem morreu; S_DUELO: tempo desde o último dano dele
    for k, rn, t, v, a in E._mortes_de_aliado(ix):
        pos_v = {"X": k["victim_X"], "Y": k["victim_Y"], "Z": k["victim_Z"]}
        for r in ix.aliados_vivos(rn, v, t):
            d = E.distancia(r, pos_v, p.corte_de_andar)
            if d != math.inf:
                med["dist_troca"].append(d)
            ultimo = None
            for x in ix.dano:
                if int(x["round_num"]) == rn and x["tick"] <= t and (
                        (x["attacker_steamid"] is not None and int(x["attacker_steamid"]) == int(r["steamid"]))
                        or (x["victim_steamid"] is not None and int(x["victim_steamid"]) == int(r["steamid"]))) \
                        and ix.time(x["attacker_steamid"]) != ix.time(x["victim_steamid"]):
                    ultimo = x["tick"]
            if ultimo is not None:
                med["s_duelo"].append((t - ultimo) / p.tickrate)
            # MEIO_FOV: o menor ângulo entre o olhar e o matador nas amostras com a linha livre
            fim = ix.fim_da_janela(rn, t, int(r["steamid"]), a)
            angs = []
            for s in p.visao.amostras(t, fim):
                eo, ea = p.visao.estado(rn, int(r["steamid"]), s), p.visao.estado(rn, a, s)
                if eo is None or ea is None or p.visao.cego(rn, int(r["steamid"]), s):
                    continue
                if p.visao.linha_de_visao(rn, s, int(r["steamid"]), a):
                    angs.append(V.angulo_horizontal(eo[3], eo, ea))
            if angs:
                med["meio_fov"].append(min(angs))
    fl = base.filter((pl.col("tipo") == E.FLASH_NO_TIME) & pl.col("filtro").is_in([E.FILTRO_ABAIXO_DO_LIMIAR]).or_(
        pl.col("filtro").is_null()))
    med["seg_uma"] = fl["valor"].to_list()
    soma: dict = {}
    for r in fl.iter_rows(named=True):
        soma[(r["steamid"], r["side"])] = soma.get((r["steamid"], r["side"]), 0.0) + r["valor"]
    du = base.filter((pl.col("tipo") == E.DANO_DE_UTILIDADE_NO_TIME) & (pl.col("filtro").is_null()
                                                                        | (pl.col("filtro") == E.FILTRO_ABAIXO_DO_LIMIAR)))
    sd: dict = {}
    for r in du.iter_rows(named=True):
        sd[(r["steamid"], r["side"])] = sd.get((r["steamid"], r["side"]), 0.0) + r["valor"]
    for sid in sorted(p.team_of):
        for lado in E.LADOS:
            med["seg_aliado"].append(soma.get((sid, lado), 0.0))
            med["dano_aliado"].append(sd.get((sid, lado), 0.0))
    nt = base.filter(pl.col("tipo") == E.NAO_TROCOU)
    med["recuo_minimo"] = nt.filter(pl.col("filtro").is_null())["recuo"].to_list()
    med["min_tempo"] = nt.filter(pl.col("filtro").is_null() | (pl.col("filtro") == E.FILTRO_POUCO_TEMPO_VISIVEL))[
        "seg_matador_visivel"].to_list()
    med["limiar_round"] = nt.filter(pl.col("filtro").is_null() | (pl.col("filtro") == E.FILTRO_ROUND_DECIDIDO))[
        "chance_vitoria"].drop_nulls().to_list()
    # CONE: o ângulo entre a mira e a vítima nos tiros que acertaram (dano no mesmo tick)
    if p.tiros is not None and p.tiros.height and "player_X" in p.tiros.columns:
        d = p.damages.filter(pl.col("attacker_steamid").is_not_null() & (pl.col("dmg_health_real") > 0)
                             & (pl.col("attacker_side") != pl.col("victim_side"))).select(
            "tick", "attacker_steamid", "victim_X", "victim_Y")
        j = d.join(p.tiros.select("tick", "player_steamid", "player_X", "player_Y", "player_yaw"),
                   left_on=["tick", "attacker_steamid"], right_on=["tick", "player_steamid"], how="inner")
        for r in j.iter_rows(named=True):
            if r["player_yaw"] is not None:
                med["cone"].append(V.angulo_horizontal(r["player_yaw"], (r["player_X"], r["player_Y"]),
                                                       (r["victim_X"], r["victim_Y"])))
    # varreduras
    cont = {"base": _contagem(base), "sem_tempo_minimo": _contagem(_varia(p, "min_tempo", 1e-6))}  # qualquer amostra visível
    for chave, (_, baixo, alto, _) in FAIXAS.items():
        for valor in (baixo, alto):
            cont[(chave, valor)] = _contagem(_varia(p, chave, valor))
    dist = {d: _varia(p, "dist_troca", d).filter(pl.col("filtro").is_null()).select("match_id", "steamid", "side", "tipo")
            for d in DIST_TROCA_COMPARADAS}
    dois = base.filter(pl.col("tipo") == E.PERDEU_A_TROCA)
    return {"m": m, "med": med, "cont": cont, "dist": dist,
            "dois_ou_mais": dois.filter(pl.col("filtro") == E.FILTRO_DOIS_OU_MAIS).height,
            "dois_ou_mais_qualquer": dois.filter((pl.col("inimigos_visiveis") >= 2) & (
                pl.col("atirou_no_matador") | (pl.col("dano_no_matador") > 0))).height}


def _varia(p: E.Partida, chave: str, valor: float) -> pl.DataFrame:
    """As ocorrências da partida com UMA constante trocada (as outras no valor proposto)."""
    if chave in ("dist_troca", "s_duelo", "seg_aliado", "seg_uma", "dano_aliado", "recuo_minimo"):
        return E.ocorrencias(p, **{chave: valor})
    if chave == "meio_fov":
        antes = (p.visao.meio_fov, p.visao._cache)
        p.visao.meio_fov, p.visao._cache = valor, {}
        try:
            return E.ocorrencias(p)
        finally:
            p.visao.meio_fov, p.visao._cache = antes
    nomes = {"limiar_round": ("LIMIAR_ROUND_GANHO", "LIMIAR_ROUND_PERDIDO"), "cone": ("CONE_DO_TIRO_GRAUS",),
             "min_tempo": ("MIN_TEMPO_VISIVEL",)}[chave]
    guardado = {n: getattr(E, n) for n in nomes}
    try:
        if chave == "limiar_round":
            E.LIMIAR_ROUND_GANHO, E.LIMIAR_ROUND_PERDIDO = valor, round(1.0 - valor, 6)
        elif chave == "min_tempo":
            E.MIN_TEMPO_VISIVEL = valor
        else:
            E.CONE_DO_TIRO_GRAUS = valor
        return E.ocorrencias(p)
    finally:
        for n, v in guardado.items():
            setattr(E, n, v)


def mede_corpus(processos: int | None = None) -> list[dict]:
    ms = partidas()
    with ProcessPoolExecutor(max_workers=processos or 6) as ex:
        res = list(ex.map(_mede_partida, ms))
    return sorted(res, key=lambda r: r["m"])                 # a ordem das partidas, não a de chegada


# --- Histogramas e a seção 7.1 ------------------------------------------------------------------------

def histograma(valores: list[float], cortes: list[float], unidade: str, marca: float | None = None) -> list[str]:
    """Histograma em texto, com a marca do valor proposto."""
    if not valores:
        return ["```", "(sem dados)", "```"]
    cont = [0] * (len(cortes) - 1)
    acima = 0
    for v in valores:
        if v >= cortes[-1]:
            acima += 1
            continue
        for i in range(len(cortes) - 1):
            if cortes[i] <= v < cortes[i + 1]:
                cont[i] += 1
                break
    maior = max(cont + [acima]) or 1
    out = ["```"]
    for i, c in enumerate(cont):
        rot = f"{cortes[i]:>7g}-{cortes[i + 1]:<7g}"
        seta = "   <- proposto" if marca is not None and cortes[i] <= marca < cortes[i + 1] else ""
        out.append(f"  {rot} {c:6d} {'#' * round(40 * c / maior)}{seta}")
    out.append(f"  {'>= ' + format(cortes[-1], 'g'):<15} {acima:6d} {'#' * round(40 * acima / maior)}")
    out.append(f"  ({len(valores)} valores, em {unidade})")
    out.append("```")
    return out


def _percentil(v: list[float], q: float) -> float:
    s = sorted(v)
    if not s:
        return float("nan")
    i = min(len(s) - 1, max(0, round(q * (len(s) - 1))))
    return s[i]


ORIGEM = {
    "dist_troca": ("o raio de apoio do projeto (RAIO_COMPANHEIRO = 600 do perfil e das funções: \"o alcance em que "
                   "uma troca ainda acontece\"). Fase 18: só entra em \"morreu sozinho\" (um aliado a até isto não "
                   "deixa a morte ser \"sozinho\"); nos outros tipos a distância é contexto. O histograma é a distância "
                   "de cada aliado vivo a quem morreu, na hora da morte, no mesmo andar."),
    "s_duelo": ("tempo de um duelo de rifle (reação de ~0,25 s mais 0,3 a 1 s para matar), com folga. O histograma é, "
                "para cada aliado vivo de quem morreu, o tempo desde o último dano que ele deu ou levou de um inimigo "
                "antes da morte."),
    "seg_aliado": ("o percentil 90 da soma de cegueira imposta ao próprio time por jogador-partida no corpus (fase 12). "
                   "O histograma é a soma por jogador-LADO (a regra desde a fase 15)."),
    "seg_uma": ("o percentil 90 da cegueira nos aliados por flash no corpus (uma flash cheia cega de 2 a 5 s; perto "
                "do topo é a flash que estourou na cara do aliado). O histograma é a cegueira nos aliados por flash."),
    "dano_aliado": ("o percentil 95 do dano de HE e molotov no próprio time por jogador-partida no corpus (fase 12). "
                    "O histograma é a soma por jogador-lado."),
    "recuo_minimo": ("a decisão do Pedro na fase 18b (64 u: o passo de lado do jiggle não é bait). O recuo é o "
                     "deslocamento LÍQUIDO do jogador para longe do matador (parado onde estava na primeira amostra "
                     "visível), da primeira amostra visível até o fim da janela. Substitui o `RECUO_MINIMO` 120 da "
                     "fase 18 (o máximo, e o bait também por \"saiu da linha de visão\"). O mesmo valor, ao contrário, "
                     "é o \"andou na direção dele\" de \"perdeu a troca\". O histograma é o recuo em \"não trocou\"."),
    "min_tempo": ("a decisão do Pedro na fase 18b (0,5 s), SOMANDO as amostras visíveis da janela (não precisa ser "
                  "contínuo: o peek repetido também dá chance de troca). Vale para o matador visível em \"não "
                  "trocou\" e no bait e para o aliado que tira \"morreu sozinho\"; não vale para os dois ou mais "
                  "inimigos de \"perdeu a troca\". O histograma é o tempo visível em \"não trocou\" (os que "
                  "passaram e os que saíram só por isso)."),
    "meio_fov": ("a metade do campo de visão horizontal do CS2 em 16:9: 90 graus numa tela 4:3, alargados na tela "
                 "larga mantendo a vertical (Hor+), dão 106,26 graus (tan(h/2) = 4/3). 45 é quem joga em 4:3. O "
                 "histograma é, para cada aliado vivo de quem morreu, o menor ângulo entre o olhar dele e o matador "
                 "nas amostras da janela com a linha de visão livre."),
    "limiar_round": ("os valores propostos pelo Pedro na fase 18 (0,95 e 0,05), simétricos: a chance já de 19 contra 1. "
                     "O histograma é a chance de o time do jogador vencer o round logo antes da morte do aliado, em "
                     "\"não trocou\" (o modelo de round do rating). Na varredura, os dois limiares andam juntos "
                     "(0,90 e 0,10; 0,98 e 0,02)."),
    "cone": ("o percentil 99 do ângulo horizontal entre a mira e a vítima nos tiros que ACERTARAM um inimigo no "
             "corpus, arredondado para cima: um tiro que erra perto do alvo ainda é um tiro nele. O histograma é esse "
             "ângulo."),
}
CORTES = {
    "dist_troca": [0, 100, 200, 300, 400, 500, 600, 700, 800, 1000, 1200, 1500, 2000, 3000],
    "s_duelo": [0, 0.5, 1, 1.5, 2, 2.5, 3, 4, 5, 7, 10, 15],
    "seg_aliado": [0, 0.01, 2, 4, 6, 8, 10, 12, 15, 20, 30],
    "seg_uma": [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 5],
    "dano_aliado": [0, 0.01, 10, 25, 40, 50, 60, 80, 100, 150],
    "recuo_minimo": [-500, -128, -64, -32, 0, 32, 64, 96, 128, 200, 300, 500],
    "min_tempo": [0, 0.125, 0.25, 0.375, 0.5, 0.75, 1, 1.5, 2, 3, 5],
    "meio_fov": [0, 5, 10, 20, 30, 40, 45, 50, 53.13, 55, 60, 75, 90, 120, 180],
    "limiar_round": [0, 0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.98],
    "cone": [0, 0.5, 1, 1.5, 2, 3, 4, 5, 6, 8, 10, 15],
}
UNIDADE_DO_HISTOGRAMA = {"limiar_round": "chance de vitória do round"}


def secao_constantes(res: list[dict]) -> list[str]:
    atual = _valor_atual()
    base = {t: sum(r["cont"]["base"][t] for r in res) for t in E.TIPOS}
    out = ["### 7.1 As constantes", "",
           "Valor proposto, origem, histograma no corpus e quantas ocorrências (depois dos filtros) cada tipo teria "
           "no valor mais baixo e no mais alto da faixa. As outras constantes ficam no valor proposto em cada varredura. "
           "As da fase 18 são `MEIO_FOV_GRAUS`, `LIMIAR_ROUND_GANHO`/`LIMIAR_ROUND_PERDIDO` e `CONE_DO_TIRO_GRAUS`; "
           "as da calibração da fase 18b, `MIN_RECUO_BAIT` (no lugar do `RECUO_MINIMO`) e `MIN_TEMPO_VISIVEL`.", ""]
    for chave, (nome, baixo, alto, unidade) in FAIXAS.items():
        v = [x for r in res for x in r["med"][chave]]
        marca = atual[chave]
        out += [f"#### `{nome}` = {_g(marca)}" + ("" if chave == "limiar_round" else f" {unidade}")
                + (f" / {_g(E.LIMIAR_ROUND_PERDIDO)}" if chave == "limiar_round" else ""), "",
                f"Origem: {ORIGEM[chave]}", "",
                f"Mediana {_fmt(_percentil(v, 0.5), 2)}, p75 {_fmt(_percentil(v, 0.75), 2)}, "
                f"p90 {_fmt(_percentil(v, 0.90), 2)}, p95 {_fmt(_percentil(v, 0.95), 2)}, p99 {_fmt(_percentil(v, 0.99), 2)}.", ""]
        out += histograma(v, CORTES[chave], UNIDADE_DO_HISTOGRAMA.get(chave, unidade), marca)
        c_baixo = {t: sum(r["cont"][(chave, baixo)][t] for r in res) for t in E.TIPOS}
        c_alto = {t: sum(r["cont"][(chave, alto)][t] for r in res) for t in E.TIPOS}
        out += ["", f"| tipo | {nome} = {_g(baixo)} | proposto ({_g(marca)}) | {nome} = {_g(alto)} |",
                "|---|---|---|---|"]
        for t in E.TIPOS:
            out.append(f"| {E.TITULOS[t]} | {c_baixo[t]} | {base[t]} | {c_alto[t]} |")
        out.append("")
    out += ["#### `MIN_GRANADAS_NO_BOLSO`: não criada", "",
            "O tipo \"Utilidade no bolso\" exige o inventário na hora da morte. O parser lê o inventário só no fim do "
            "freeze time (`PROPS_DA_COMPRA` em `parsing/parser.py`, a tabela `compra`); na hora da morte não há o que "
            "ler. Pela regra do pedido, o tipo não foi criado e nada foi estimado (decisão 46).", ""]
    return out


# --- 7.1b Quantos pontos a melhorar cada jogador teria (fase 12b) ------------------------------------------

PERCENTIS_COMPARADOS = (50, 75, 90)                # o em uso (E.PERCENTIL_PONTO_A_MELHORAR) é um deles
DIST_TROCA_COMPARADAS = (400.0, E.DIST_TROCA, 800.0)             # um menor, o atual e um maior
ROTULO_LADO = E.ROTULO_DO_LADO


def _linhas_de_contagem(oc: pl.DataFrame) -> list[dict]:
    """Um registro por (partida, jogador, lado) do corpus: função do lado e contagem de cada tipo (só o que
    passou nos filtros). Mesmo formato que o ajuste da régua (scripts/fit_erros_reference)."""
    conta: dict = {}
    if "filtro" in oc.columns:
        oc = oc.filter(pl.col("filtro").is_null())
    for m, sid, lado, tipo, n in (oc.group_by(["match_id", "steamid", "side", "tipo"], maintain_order=True)
                                  .len().iter_rows()):
        conta[(m, int(sid), lado, tipo)] = n
    linhas = []
    for m in partidas():
        resumo = pl.read_parquet(PROCESSED / m / "structural_roles_summary.parquet")
        for r in resumo.sort(["steamid", "side"]).iter_rows(named=True):
            sid, lado = int(r["steamid"]), r["side"]
            linhas.append({"partida": m, "steamid": sid, "lado": lado, "funcao": r["funcao"], "valores": {},
                           "contagens": {t: conta.get((m, sid, lado, t), 0) for t in E.TIPOS}})
    return linhas


def _pontos_por_jogador(linhas: list[dict], ref: dict, q: float) -> tuple[dict, dict]:
    """({(partida, jogador): quantos pontos a melhorar}, {tipo: quantos pares (tipo, lado)}), com a regra da
    página: acima do percentil `q` da célula (ou do lado, se a célula é pequena) e pelo menos 2 ocorrências."""
    por_jogador: dict = {}
    por_tipo = {t: 0 for t in E.TIPOS}
    for x in linhas:
        por_jogador.setdefault((x["partida"], x["steamid"]), 0)
        for t in E.TIPOS:
            celula, _ = E.escolhe_celula(ref, "erros", t, x["lado"], x["funcao"])
            if E.acima_do_normal(x["contagens"][t], celula, percentil=q):
                por_jogador[(x["partida"], x["steamid"])] += 1
                por_tipo[t] += 1
    return por_jogador, por_tipo


def _resumo_de_pontos(por_jogador: dict) -> tuple[int, int, float, list[int]]:
    """(jogador-partidas, com pelo menos 1, média por jogador-partida, quantos com 0, 1, 2, 3 ou mais)."""
    n = len(por_jogador)
    vs = list(por_jogador.values())
    faixas = [sum(v == k for v in vs) for k in (0, 1, 2)] + [sum(v >= 3 for v in vs)]
    return n, sum(v >= 1 for v in vs), (sum(vs) / n if n else 0.0), faixas


def secao_quantos_pontos(oc: pl.DataFrame, res: list[dict] | None) -> list[str]:
    from scripts.fit_erros_reference import ajusta

    linhas = _linhas_de_contagem(oc)
    ref = ajusta(linhas)
    out = ["### 7.1b Quantos pontos a melhorar cada jogador teria", "",
           "Uma ocorrência só vira \"ponto a melhorar\" quando a contagem do jogador num lado fica ACIMA do "
           f"percentil {E.PERCENTIL_PONTO_A_MELHORAR} da referência (os jogador-lados do corpus com a mesma função "
           f"no mesmo lado; com menos de {E.MIN_REF_LADO_FUNCAO} deles, todos os jogador-lados daquele lado) e tem pelo "
           f"menos {E.MIN_OCORRENCIAS_PARA_PONTO} ocorrências. Um jogador-lado é um jogador numa partida, num dos "
           f"lados ({len(linhas)} no corpus). A tela mostra no máximo {E.MAX_PONTOS_A_MELHORAR} por jogador; as "
           "contagens abaixo são as brutas, sem esse corte.", "",
           "#### Distribuição da contagem por jogador-lado, por tipo e lado", "",
           "| tipo | lado | jogador-lados | média | mediana | p75 | p90 | máximo | com 0 |", "|---|---|---|---|---|---|---|---|---|"]
    for t in E.TIPOS:
        for lado in E.LADOS:
            v = sorted(x["contagens"][t] for x in linhas if x["lado"] == lado)
            out.append(f"| {E.TITULOS[t]} | {ROTULO_LADO[lado]} | {len(v)} | {_fmt(sum(v) / len(v), 2)} | "
                       f"{_fmt(_percentil(v, 0.5), 1)} | {_fmt(_percentil(v, 0.75), 1)} | {_fmt(_percentil(v, 0.9), 1)} | "
                       f"{max(v)} | {_fmt(100 * sum(1 for a in v if a == 0) / len(v), 0)}% |")
    out += ["", "#### Pontos a melhorar por jogador-partida, por percentil", "",
            "| percentil | jogador-partidas | com pelo menos 1 | % | média | com 0 | com 1 | com 2 | com 3 ou mais |",
            "|---|---|---|---|---|---|---|---|---|"]
    por_tipo_de = {}
    for q in PERCENTIS_COMPARADOS:
        pj, por_tipo_de[q] = _pontos_por_jogador(linhas, ref, q)
        n, com, media, f = _resumo_de_pontos(pj)
        marca = " (em uso)" if q == E.PERCENTIL_PONTO_A_MELHORAR else ""
        out.append(f"| {q}{marca} | {n} | {com} | {_fmt(100 * com / n, 0)}% | {_fmt(media, 2)} | {f[0]} | {f[1]} | "
                   f"{f[2]} | {f[3]} |")
    out += ["", "Pares (tipo, lado) que viram ponto a melhorar, por tipo:", "",
            "| tipo | " + " | ".join(f"p{q}" for q in PERCENTIS_COMPARADOS) + " |",
            "|---|" + "---|" * len(PERCENTIS_COMPARADOS)]
    for t in E.TIPOS:
        out.append(f"| {E.TITULOS[t]} | " + " | ".join(str(por_tipo_de[q][t]) for q in PERCENTIS_COMPARADOS) + " |")
    out.append("")
    if res:
        out += ["#### O efeito de `DIST_TROCA` em \"morreu sozinho\"", "",
                "Fase 18: `DIST_TROCA` só entra em \"morreu sozinho\" (nos outros tipos a troca é decidida pelo fato e "
                "a distância é contexto). Cada linha recalcula as ocorrências do corpus com outro `DIST_TROCA` (o atual "
                f"está marcado) e refaz a referência com elas. Ponto a melhorar com o percentil {E.PERCENTIL_PONTO_A_MELHORAR}. "
                "O valor da constante NÃO muda agora: depende da sua calibração.", "",
                "| `DIST_TROCA` | tipo | ocorrências no corpus | média por jogador-lado | jogador-partidas com pelo "
                "menos 1 ponto a melhorar | % |", "|---|---|---|---|---|---|"]
        for d in DIST_TROCA_COMPARADAS:
            oc_d = pl.concat([r["dist"][d] for r in res], how="vertical")
            lin = _linhas_de_contagem(oc_d)
            ref_d = ajusta(lin)
            marca = " (atual)" if d == E.DIST_TROCA else ""
            for t in (E.MORREU_SOZINHO,):
                total = sum(x["contagens"][t] for x in lin)
                pj = {}
                for x in lin:
                    pj.setdefault((x["partida"], x["steamid"]), 0)
                    celula, _ = E.escolhe_celula(ref_d, "erros", t, x["lado"], x["funcao"])
                    if E.acima_do_normal(x["contagens"][t], celula):
                        pj[(x["partida"], x["steamid"])] += 1
                com = sum(v >= 1 for v in pj.values())
                out.append(f"| {_g(d)}{marca} | {E.TITULOS[t]} | {total} | {_fmt(total / len(lin), 2)} | {com} | "
                           f"{_fmt(100 * com / len(pj), 0)}% |")
        out.append("")
    return out


def _g(x: float) -> str:
    """Número curto com vírgula decimal (4,8; 600)."""
    return format(x, "g").replace(".", ",")


def _relogio(seg: float | None) -> str:
    if seg is None:
        return "—"
    s = max(0, int(round(seg)))
    return f"{s // 60}:{s % 60:02d}"


def link_do_replay(match_id: str, round_num: int, segundos: float | None) -> str:
    """O link direto para o replay naquele instante (a página abre 3 s antes, como ao clicar num evento)."""
    t = "" if segundos is None else f"&t={segundos:g}"
    return f"docs/{match_id}.html#replay?round={round_num}{t}"


def _fmt(v, casas: int = 0) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    return f"{v:.{casas}f}".replace(".", ",")


# --- Exemplos fixados (fase 18, complemento do Pedro) --------------------------------------------------

def _chave(x: dict) -> tuple:
    return (x["tipo"], x["match_id"], int(x["round_num"]), int(x["tick"]), int(x["steamid"]),
            int(x["aliado_steamid"]) if x.get("aliado_steamid") is not None else None)


def _registro(x: dict, data: str) -> dict:
    return {"tipo": x["tipo"], "partida": x["match_id"], "round": int(x["round_num"]), "tick": int(x["tick"]),
            "jogador": x["name"], "steamid": str(int(x["steamid"])),
            "aliado_steamid": None if x.get("aliado_steamid") is None else str(int(x["aliado_steamid"])),
            "semente": SEMENTE_DOS_EXEMPLOS, "data_do_sorteio": data}


def _chave_do_registro(r: dict) -> tuple:
    return (r["tipo"], r["partida"], int(r["round"]), int(r["tick"]), int(r["steamid"]),
            int(r["aliado_steamid"]) if r.get("aliado_steamid") is not None else None)


def le_fixados(caminho: Path = FIXADOS) -> dict:
    if not caminho.exists():
        return {"_leia_isto": "", "exemplos": {}}
    return json.loads(caminho.read_text(encoding="utf-8"))


def grava_fixados(fix: dict, caminho: Path = FIXADOS) -> None:
    fix["_leia_isto"] = ("Exemplos da seção 7.2 do material de calibração (gerados por "
                         "`py -3.12 -m scripts.calibracao.erros_do_jogador`). Um exemplo fixado só é trocado quando "
                         "deixa de ser ocorrência pelas regras atuais, e o substituto diz quando e por quê; "
                         "`--sortear-de-novo` refaz todos (só quando as definições mudam).")
    caminho.write_text(json.dumps(fix, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def casos(oc: pl.DataFrame) -> dict[str, int]:
    """{tipo: ocorrências que passaram nos filtros}, da mesma tabela que o material lê."""
    return _contagem(oc)


def escolhe_exemplos(oc: pl.DataFrame, fix: dict, hoje: str, sortear_de_novo: bool = False,
                     validaveis: tuple | None = None) -> dict:
    """Para cada tipo VALIDÁVEL (pelo menos E.MIN_CASOS_PARA_VALIDAR casos no corpus), os exemplos fixados que
    ainda valem e os substitutos (mesma semente). Devolve o registro novo ({tipo: [registros]}); um substituto
    tem `substitui`, `substituido_em` e `motivo_da_substituicao`. Um tipo abaixo do mínimo não tem exemplos de
    validação (fase 18b): os casos dele vão todos para a seção "amostra insuficiente" do material."""
    validaveis = E.tipos_validaveis(casos(oc)) if validaveis is None else validaveis
    novo = {}
    for t in E.TIPOS:
        if t not in validaveis:
            continue
        todas = {_chave(x): x for x in oc.filter(pl.col("tipo") == t).to_dicts()}
        validas = [x for x in oc.filter((pl.col("tipo") == t) & pl.col("filtro").is_null()).to_dicts()]
        anteriores = [] if sortear_de_novo else list((fix.get("exemplos") or {}).get(t, []))
        ficam, trocados = [], []
        for r in anteriores:
            x = todas.get(_chave_do_registro(r))
            if x is not None and x["filtro"] is None:
                ficam.append(r)
            else:
                motivo = x["filtro"] if x is not None else "deixou de existir na tabela de ocorrências"
                trocados.append((r, motivo))
        por_partida: dict = {}
        for r in ficam:
            por_partida[r["partida"]] = por_partida.get(r["partida"], 0) + 1
        usadas = {_chave_do_registro(r) for r in ficam} | {_chave_do_registro(r) for r, _ in trocados}
        rng = random.Random(f"{SEMENTE_DOS_EXEMPLOS}-{t}")
        ordem = list(validas)
        rng.shuffle(ordem)
        sorteados = []
        faltam = EXEMPLOS_POR_TIPO - len(ficam)
        for x in ordem:
            if len(sorteados) >= faltam:
                break
            if _chave(x) in usadas or por_partida.get(x["match_id"], 0) >= MAX_EXEMPLOS_POR_PARTIDA:
                continue
            por_partida[x["match_id"]] = por_partida.get(x["match_id"], 0) + 1
            usadas.add(_chave(x))
            reg = _registro(x, hoje if (sortear_de_novo or not anteriores) else (anteriores[0]["data_do_sorteio"]))
            if trocados:
                velho, motivo = trocados[len(sorteados)] if len(sorteados) < len(trocados) else (None, None)
                if velho is not None:
                    reg.update(substitui={k: velho[k] for k in ("partida", "round", "tick", "jogador")},
                               substituido_em=hoje, motivo_da_substituicao=motivo)
            sorteados.append(reg)
        novo[t] = sorted(ficam + sorteados, key=lambda r: (r["partida"], r["round"], r["tick"], int(r["steamid"])))
    return novo


def _linha_do_exemplo(oc_por_chave: dict, r: dict) -> dict:
    return oc_por_chave[_chave_do_registro(r)]


COLUNAS_TROCA = ("| # | partida | round | relógio | jogador | aliado | matador | dist. ao aliado | dist. jogador–matador "
                 "| situação | chance de vitória antes | matador visível? (s na janela) | atirou ou deu dano no matador? "
                 "| recuou (u) | inimigos visíveis ao mesmo tempo | morte trocada? (por quem, a que distância) | ΔWPA "
                 "| nível | motivo | replay | É erro mesmo? |")
COLUNAS_UTIL = ("| # | partida | round | relógio | jogador | aliado mais atingido | situação | chance de vitória antes "
                "| {evento} | {soma} | ΔWPA | nível | motivo | replay | É erro mesmo? |")


def _sim(v) -> str:
    return "—" if v is None else ("sim" if v else "não")


def secao_exemplos(oc: pl.DataFrame, escolhidos: dict, validaveis: tuple | None = None) -> list[str]:
    por_chave = {_chave(x): x for x in oc.to_dicts()}
    validaveis = E.tipos_validaveis(casos(oc)) if validaveis is None else validaveis
    out = ["### 7.2 Dez exemplos por tipo", "",
           f"Sorteados com semente fixa ({SEMENTE_DOS_EXEMPLOS}), no máximo {MAX_EXEMPLOS_POR_PARTIDA} por partida, "
           "só entre as ocorrências que passaram nos filtros, e FIXADOS em `scripts/calibracao/exemplos_fixados.json`: "
           "rodar de novo mantém todo exemplo que ainda é ocorrência; o que deixar de ser é trocado e marcado "
           "\"(substituído em <data>: <motivo>)\". Os exemplos da fase 17 não valem mais (as definições mudaram na "
           "fase 18) e foram sorteados de novo; na calibração da fase 18b, os que deixaram de ser ocorrência foram trocados (a marca diz quando e por quê), e um tipo abaixo de `MIN_CASOS_PARA_VALIDAR` não tem exemplos de validação. O relógio é o tempo decorrido desde o fim do freeze time. O link abre "
           "o replay naquele round, 3 s antes do instante (gere o site com `py -3.12 -m scripts.build_site`). "
           "Distâncias em unidades do jogo, no mesmo andar; \"—\" quando não se aplica ou estão em andares diferentes. "
           "\"Visível\" é a linha de visão pelo mapa (com as smokes) dentro do campo de visão e sem estar cego "
           "(`metrics/visao.py`). A chance de vitória é a do time do jogador vencer o ROUND logo antes do evento "
           "(modelo de round do rating). ΔWPA em pontos de chance de vitória da partida, pela estimativa do modelo "
           "(negativo = o time perdeu chance).", "",
           "**Regra de publicação:** o tipo só aparece no site com pelo menos 8 dos 10 confirmados: \"sim\" quando "
           "o nível é explícito, ou \"depende da tática\" quando o nível é depende.", ""]
    nome = lambda s: (s or "—").replace("|", "\\|")  # noqa: E731
    for t in E.TIPOS:
        if t in validaveis:
            ex = escolhidos.get(t, [])
            out += [f"#### {E.TITULOS[t]}", "", f"Frase de como melhorar: \"{E.COMO_MELHORAR[t]}\"", "",
                    "**A frase serve?** sim / reescrever: ____", ""]
        else:
            # fase 18b: abaixo de MIN_CASOS_PARA_VALIDAR, todos os casos, só para conferir a definição
            todos = oc.filter((pl.col("tipo") == t) & pl.col("filtro").is_null()).sort(
                ["match_id", "round_num", "tick", "steamid"]).to_dicts()
            ex = [_registro(x, "") for x in todos]
            out += [f"#### {E.TITULOS[t]}: amostra insuficiente ({len(ex)} casos), só para conferir a definição", "",
                    f"Com menos de {E.MIN_CASOS_PARA_VALIDAR} casos no corpus (`MIN_CASOS_PARA_VALIDAR`, contados dos "
                    "dados), o tipo não entra na validação nem em `TIPOS_DE_ERRO_VALIDADOS`: não dá para sortear os 10 "
                    "exemplos da regra dos 8 de 10. Ele continua calculado e gravado e volta à validação normal quando "
                    "o corpus tiver casos suficientes. Estes são TODOS os casos (não são exemplos fixados): a "
                    "pergunta é se a definição pega o que você chamaria de bait.", ""]
        if not ex:
            out += ["(nenhuma ocorrência no corpus)", ""]
            continue
        util = t in (E.FLASH_NO_TIME, E.DANO_DE_UTILIDADE_NO_TIME)
        if util:
            ev, so = (("cegueira desta flash (s)", "soma do jogador no lado (s)") if t == E.FLASH_NO_TIME
                      else ("dano desta granada", "soma do jogador no lado"))
            cab = COLUNAS_UTIL.format(evento=ev, soma=so)
        else:
            cab = COLUNAS_TROCA
        out += [cab, "|" + "---|" * (cab.count("|") - 1)]
        for i, r in enumerate(ex, 1):
            x = _linha_do_exemplo(por_chave, r)
            situ = f"{x['vivos_time']} contra {x['vivos_adversario']}"
            chance = "—" if x["chance_vitoria"] is None else f"{_fmt(100 * x['chance_vitoria'], 0)}%"
            dw = "—" if x["dwpa"] is None else _fmt(100 * x["dwpa"], 1)
            motivo = x["motivo"] or ""
            if r.get("substituido_em"):
                s = r["substitui"]
                motivo += (f" (substituído em {r['substituido_em']}: {r['motivo_da_substituicao']}; era {s['partida']} "
                           f"R{s['round']} {s['jogador']})")
            comum = (f"| {i} | {x['match_id']} | {x['round_num']} | {_relogio(x['segundos'])} | {nome(x['name'])} | ")
            fim = (f"| {dw} | {E.ROTULO_DO_NIVEL[x['nivel']]} | {motivo} | "
                   f"[abrir]({link_do_replay(x['match_id'], x['round_num'], x['segundos'])}) | "
                   "sim / não / depende da tática |")
            if util:
                casas = 2 if t == E.FLASH_NO_TIME else 1
                out.append(comum + f"{nome(x['aliado'])} | {situ} | {chance} | {_fmt(x['valor'], casas)} | "
                           f"{_fmt(x['valor_soma_lado'], casas)} " + fim)
            else:
                vis = _sim(x["matador_visivel"])
                if x["matador_visivel"] and x["seg_matador_visivel"] is not None:
                    vis += f" ({_fmt(x['seg_matador_visivel'], 1)} s)"
                eng = "—" if x["atirou_no_matador"] is None else (
                    f"{'atirou' if x['atirou_no_matador'] else 'não atirou'}; dano {_fmt(x['dano_no_matador'], 0)}")
                if x["trocada"]:
                    troca = f"sim ({nome(x['trocada_por'])}, {_fmt(x['dist_de_quem_trocou'])} u)"
                else:
                    troca = _sim(x["trocada"])
                recuo = "—" if x["recuo"] is None else _fmt(x["recuo"], 0)
                if x["saiu_da_linha"]:
                    recuo += "; saiu da linha de visão"
                out.append(comum + f"{nome(x['aliado'])} | {nome(x['matador'])} | {_fmt(x['dist_aliado'])} | "
                           f"{_fmt(x['dist_matador_jogador'])} | {situ} | {chance} | {vis} | {eng} | {recuo} | "
                           f"{'—' if x['inimigos_visiveis'] is None else x['inimigos_visiveis']} | {troca} " + fim)
        out.append("")
    return out


NOTA_FASE18B = (
    "**Calibração da fase 18b (decisões do Pedro).** (1) Quem engajou o matador (atirou nele, deu dano ou andou na "
    "direção dele com ele visível) conta só em \"perdeu a troca\" (se morreu); \"não trocou\" fica para quem viu o "
    "matador e não engajou. (2) Bait exige recuo líquido de pelo menos `MIN_RECUO_BAIT` = 64 u (do primeiro tick em "
    "que ele vê o matador até o fim da janela, com o matador parado onde estava nesse tick); sair da linha de visão "
    "com menos que isso não é bait (o `RECUO_MINIMO` 120 da fase 18 saiu). (3) O matador visível precisa de pelo menos "
    "`MIN_TEMPO_VISIVEL` = 0,5 s, somados os ticks visíveis da janela, em \"não trocou\", no bait e no aliado que tira "
    "\"morreu sozinho\"; nos dois ou mais inimigos de \"perdeu a troca\", qualquer tick visível conta.")

NOTA_FASE15 = (
    '**Mudança da fase 15 (decisão 46).** "Flash no time" e "dano de utilidade no time" eram somas da partida (CT e '
    'TR juntos); passam a ser POR LADO, com o mesmo limiar (`SEG_CEGUEIRA_ALIADO` 27 s e `DANO_UTILIDADE_ALIADO` 20) '
    'aplicado a cada lado.')

NOTA_FASE18 = (
    "**Mudança da fase 18 (definições do Pedro).** (1) A troca é decidida pelo FATO (o matador morreu por um aliado "
    "dentro da janela), nunca pela distância, e toda morte trocada sai de todos os tipos (cada morte do corpus grava "
    "se foi trocada e por quem, em `mortes.parquet`). (2) Round decidido fica fora de todos os tipos: a chance de o "
    f"time vencer o round logo antes do evento acima de {_g(E.LIMIAR_ROUND_GANHO)} ou abaixo de "
    f"{_g(E.LIMIAR_ROUND_PERDIDO)}. (3) \"Não trocou\" exige o matador VISÍVEL para o jogador na janela; \"possível "
    "bait\" é o subconjunto em que ele não engajou (não atirou nele nem deu dano) e recuou mais que `RECUO_MINIMO` "
    "ou saiu da linha de visão andando (o critério \"atrás do aliado\" saiu). (4) \"Perdeu a troca\" exige ter ido "
    "trocar (atirou, deu dano ou andou na direção do matador com ele visível) e sai com dois ou mais inimigos "
    "visíveis ao mesmo tempo. (5) \"Morreu isolado\" virou \"morreu sozinho\": nenhum aliado vivo com o matador à "
    "vista na janela nem a até `DIST_TROCA`. (6) A situação conta os vivos pelas mortes: antes vinha das posições "
    "gravadas só nos ticks das kills, e uma flash ou granada antes da primeira morte do round saía \"0 contra 0\". "
    "(7) Um evento com 0 de dano ou de cegueira não é ocorrência (o 0 vem do próprio jogo: o `player_hurt` do "
    "aliado na borda da explosão). \"Candidatos\" agora inclui os casos registrados com o motivo de ficar de fora "
    "(por exemplo, todo aliado vivo de quem morreu sem troca em \"não trocou\").")

ORDEM_DOS_NIVEIS = (
    "Ordem dos níveis (a primeira regra que se aplica decide): 1) round de eco ou pistola do time, time guardando "
    "arma (evento depois do plant num round que o time perdeu), depois do fim do round ou round decidido: fora; "
    "2) morreu sozinho sendo lurker: depende; 3) primeira morte sem troca sendo entry: depende; 4) morreu sozinho ou "
    "primeira morte do AWPer no duelo de abertura: depende; 5) função só tendência: o motivo diz que a função não é "
    "firme; 6) não trocou, possível bait, perdeu a troca, flash no time e dano de utilidade no time: explícito (os "
    "dois primeiros só existem com o matador visível); 7) o resto: depende. Por isso \"morreu sozinho\" e "
    "\"primeira morte sem troca\" saem sempre como \"depende da tática\" (só o motivo muda).")


def secao(oc: pl.DataFrame, res: list[dict] | None, escolhidos: dict, antigas: pl.DataFrame | None) -> list[str]:
    n = len(partidas())
    out = [TITULO_DA_SECAO, "",
           "Gerado por `py -3.12 -m scripts.calibracao.erros_do_jogador` (fase 12, decisão 46; definições da fase 18). "
           f"Os tipos de erro de `metrics/erros.py` sobre as {n} partidas do corpus. Nenhum tipo aparece no site até "
           "você confirmar os exemplos: `TIPOS_DE_ERRO_VALIDADOS` começa vazia. Para ver a aba com todos os tipos "
           "marcados \"em validação\": `py -3.12 -m scripts.build_site --mostrar-erros-nao-validados` (gera em "
           "`preview/`, fora do git e nunca publicado).", "",
           "### 7.0 Ocorrências por tipo no corpus", ""]
    out += tabela_por_tipo(oc)
    out += ["", NOTA_FASE18B, "", NOTA_FASE18, "", NOTA_FASE15, "", f"#### Antes ({ROTULO_DO_ANTES}) -> depois (fase 18b)", "",
            f"\"Antes\" são as ocorrências da {ROTULO_DO_ANTES} (commit `{ANTES}`), \"depois\" as de agora. Uma "
            "ocorrência antiga \"segue\" se a mesma (partida, round, tick, jogador e, nos tipos de troca, o aliado) "
            "ainda passa nos filtros; se não, saiu com o motivo do filtro novo. \"Entraram\" são as novas que não "
            "existiam. \"Situação corrigida\": das que seguem, quantas mudaram de \"N contra M\".", ""]
    out += tabela_antes_depois(oc, antigas)
    if res is not None:
        base = {t: sum(r["cont"]["base"][t] for r in res) for t in E.TIPOS}
        sem = {t: sum(r["cont"]["sem_tempo_minimo"][t] for r in res) for t in E.TIPOS}
        bait = oc.filter((pl.col("tipo") == E.POSSIVEL_BAIT) & pl.col("filtro").is_null())["recuo"].sort().to_list()
        out += ["", "#### Os números da calibração da fase 18b", "",
                f"- \"Possível bait\" que sobram: {len(bait)}; recuo líquido deles: mediana {_fmt(_percentil(bait, 0.5), 0)} u, "
                f"quartis {_fmt(_percentil(bait, 0.25), 0)} e {_fmt(_percentil(bait, 0.75), 0)} u (mínimo "
                f"{_fmt(min(bait) if bait else None, 0)}, máximo {_fmt(max(bait) if bait else None, 0)}).",
                f"- \"Não trocou\" que sobram: {base[E.NAO_TROCOU]}.",
                "- Casos que saíram SÓ pelo tempo mínimo de visão (as ocorrências com o mínimo valendo qualquer amostra visível menos as de "
                "agora, com as outras regras iguais): " + "; ".join(
                    f"{E.TITULOS[t]} {sem[t] - base[t]}" for t in E.TIPOS) + ".",
                "  Em \"morreu sozinho\" o número é negativo: com o mínimo, um aliado que viu o matador por menos de 0,5 s "
                "não tira mais o caso, e a morte volta a ser \"morreu sozinho\"." if sem[E.MORREU_SOZINHO] < base[E.MORREU_SOZINHO] else ""]
    if res is not None:
        dois = sum(r["dois_ou_mais"] for r in res)
        dois_q = sum(r["dois_ou_mais_qualquer"] for r in res)
        out += ["", "#### Enfrentou dois ou mais ao mesmo tempo (informação, não é erro)", "",
                f"Foi trocar (engajou o matador), morreu sem matá-lo e tinha dois ou mais inimigos visíveis ao mesmo "
                f"tempo na janela: {dois} casos que saíram de \"perdeu a troca\" por esse motivo ({dois_q} contando os "
                "que já tinham saído antes por outro filtro, como o round decidido). Não é tipo de erro e não aparece "
                "no Perfil."]
    out += ["", ORDEM_DOS_NIVEIS, ""]
    if res is not None:
        out += secao_constantes(res)
    out += secao_quantos_pontos(oc, res)
    out += secao_exemplos(oc, escolhidos)
    out += ["### 7.3 Sua resposta", "",
            "Para cada tipo: quantos dos 10 exemplos você confirma, e se a frase de como melhorar serve. O tipo com 8 "
            "ou mais confirmados entra em `TIPOS_DE_ERRO_VALIDADOS` (`metrics/erros.py`) num item à parte; os "
            "reprovados ficam fora da tela, e eu trago uma proposta de ajuste com os números.", ""]
    return out


def grava(linhas: list[str], material: Path = MATERIAL) -> None:
    """Troca a seção 7 do material (ou a acrescenta no fim), sem tocar nas outras."""
    texto = material.read_text(encoding="utf-8")
    novo = "\n".join(linhas).rstrip() + "\n"
    i = texto.find(TITULO_DA_SECAO)
    if i < 0:
        texto = texto.rstrip() + "\n\n" + novo
    else:
        j = texto.find("\n## ", i + len(TITULO_DA_SECAO))
        texto = texto[:i] + novo + ("" if j < 0 else "\n" + texto[j + 1:])
    material.write_text(texto, encoding="utf-8", newline="\n")


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    oc = corpus()
    if "--tabela" in argv:
        print("\n".join(tabela_por_tipo(oc)))
        return 0
    hoje = datetime.date.today().isoformat()
    fix = le_fixados()
    escolhidos = escolhe_exemplos(oc, fix, hoje, sortear_de_novo="--sortear-de-novo" in argv)
    if escolhidos != fix.get("exemplos"):
        fix["exemplos"] = escolhidos
        grava_fixados(fix)
    res = mede_corpus()
    grava(secao(oc, res, escolhidos, _antigas()))
    print(f"seção 7 gravada em {MATERIAL.name} ({oc.height} ocorrências em {len(res)} partidas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
