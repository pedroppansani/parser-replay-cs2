"""
Rating de jogador — implementação própria da metodologia do Rating 3.0 da HLTV.

O QUE ESTE MÓDULO É, E O QUE ELE NÃO É
--------------------------------------
A HLTV publicou a METODOLOGIA do Rating 3.0, não a fórmula. Os coeficientes e os
pesos de cada sub-rating são fechados. Então **este número não é o Rating 3.0 da
HLTV e não pode ser apresentado como se fosse** -- afirmar isso seria falso.

O que existe aqui é uma reimplementação da metodologia publicada, com os
coeficientes ESTIMADOS a partir do corpus deste projeto. Em toda a interface o
rótulo diz isso. A fonte da metodologia está citada no README.

Isso não enfraquece o trabalho: implementar uma metodologia documentada e
validar o resultado contra os ratings oficiais publicados é engenharia. Copiar
uma fórmula fechada não seria nem possível.

OS SEIS SUB-RATINGS
-------------------
Cinco vêm do Rating 2.1 e são ajustados por economia -- kills, dano,
sobrevivência, KAST e multi-kills. O sexto é o **Round Swing**, que mede quanto
cada ação mudou a chance do time ganhar AQUELE round.

O ajuste por economia responde a uma crítica velha ao rating: matar um inimigo
de pistola inicial num round em que seu time já tinha 75% de chance não vale o
mesmo que matar um rifle num round parelho. O peso da kill sai da taxa de
vitória do confronto de equipamentos, estimada no corpus.

O Round Swing é a mesma máquina de `metrics/win_probability.py`, mas um nível
abaixo: lá o estado é o placar da partida, aqui é o estado do round (vivos,
bomba, equipamento, lado). E a diferença de espaço de estados obriga a mudar de
método -- ver `ModeloDeRound`.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import polars as pl

# ---------------------------------------------------------------------------
# Grupos de equipamento
#
# A HLTV agrupa por preço de colete + arma mais cara. Os seis grupos abaixo são
# os publicados. A arma considerada é a MELHOR que o jogador teve no round, não
# a que estava na mão num tick qualquer: quem compra AWP e morre com a pistola
# na mão comprou AWP.
# ---------------------------------------------------------------------------

GRUPOS = (
    "pistola_inicial",
    "pistola_melhorada",
    "smg_shotgun",
    "rifle_t2",
    "rifle_t1",
    "sniper",
)

# Nome de exibição do demo -> grupo. O demo entrega "MAC-10" e "AK-47", não
# "weapon_mac10" (medido: foi assim que a detecção de SMG falhou uma vez).
ARMA_PARA_GRUPO = {
    # snipers
    "AWP": "sniper", "SSG 08": "sniper", "SCAR-20": "sniper", "G3SG1": "sniper",
    # rifles tier 1
    "AK-47": "rifle_t1", "M4A4": "rifle_t1", "M4A1-S": "rifle_t1",
    "SG 553": "rifle_t1", "AUG": "rifle_t1",
    # rifles tier 2
    "Galil AR": "rifle_t2", "FAMAS": "rifle_t2",
    # SMG e shotgun
    "MP9": "smg_shotgun", "MAC-10": "smg_shotgun", "MP7": "smg_shotgun",
    "MP5-SD": "smg_shotgun", "UMP-45": "smg_shotgun", "P90": "smg_shotgun",
    "PP-Bizon": "smg_shotgun", "Nova": "smg_shotgun", "XM1014": "smg_shotgun",
    "MAG-7": "smg_shotgun", "Sawed-Off": "smg_shotgun",
    "M249": "smg_shotgun", "Negev": "smg_shotgun",
    # pistolas melhoradas
    "Desert Eagle": "pistola_melhorada", "Five-SeveN": "pistola_melhorada",
    "Tec-9": "pistola_melhorada", "CZ75-Auto": "pistola_melhorada",
    "P250": "pistola_melhorada", "Dual Berettas": "pistola_melhorada",
    "R8 Revolver": "pistola_melhorada",
    # pistolas iniciais
    "Glock-18": "pistola_inicial", "USP-S": "pistola_inicial",
    "P2000": "pistola_inicial",
}

# Ordem de força, para escolher a MELHOR arma do round.
FORCA_DO_GRUPO = {g: i for i, g in enumerate(GRUPOS)}

# ---------------------------------------------------------------------------
# Conversão de taxa de vitória em peso da kill
#
# Os dois únicos pontos que a HLTV publicou, no lado TR:
#   confronto rifle x rifle, 48% de vitória  -> kill vale ~1,10
#   matar uma pistola inicial, 75% de vitória -> kill vale  0,54
#
# Com dois pontos, a reta que passa por eles é a única leitura possível sem
# inventar curvatura. Ela é declarada aqui em vez de espalhada no código porque é
# o coração do ajuste por economia, e porque é o primeiro lugar a mexer se a HLTV
# publicar um terceiro ponto.
#
#   peso = A + B * taxa,  resolvido pelos dois pontos acima
# ---------------------------------------------------------------------------
_PONTO_1 = (0.48, 1.10)
_PONTO_2 = (0.75, 0.54)
PESO_KILL_B = (_PONTO_2[1] - _PONTO_1[1]) / (_PONTO_2[0] - _PONTO_1[0])   # ~ -2,074
PESO_KILL_A = _PONTO_1[1] - PESO_KILL_B * _PONTO_1[0]                     # ~  2,096

# A reta extrapolada sairia do razoável nos extremos (taxa 0 ou 1 quase nunca é
# observada com amostra honesta). O corte mantém o peso numa faixa defensável.
PESO_KILL_MIN = 0.30
PESO_KILL_MAX = 2.00

# Encolhimento das taxas de vitória por confronto na direção da taxa do LADO.
#
# São 6x6x2 = 72 células e o corpus tem ~1.900 lados-round: várias células ficam
# com meia dúzia de casos, e frequência empírica ali é ruído. `n` casos pesam
# `n / (n + K)` contra a taxa base do lado. K = 20 significa que uma célula
# precisa de 20 rounds para valer metade do próprio peso.
K_ENCOLHIMENTO = 20.0

# ---------------------------------------------------------------------------
# Round Swing: divisão do crédito
#
# A HLTV divide o crédito de cada kill entre quem deu o dano final, quem deu
# dano, quem cegou e quem trocou. Os pesos são fechados lá; estes são os deste
# projeto, e somam exatamente 1,0 -- é isso que garante que o crédito distribuído
# nunca exceda a variação de probabilidade do evento (há teste travando).
# ---------------------------------------------------------------------------
# O matador fica com o que sobra depois de dano, flash e trade (no mínimo
# 0,55 quando todos existem): o swing de cada evento soma zero entre os dez.
CREDITO_KILL = 0.55
CREDITO_DANO = 0.25
CREDITO_FLASH = 0.10
CREDITO_TRADE = 0.10

# Janela em que uma flash ainda explica a kill que veio depois.
SEGUNDOS_FLASH_ANTES_DA_KILL = 3.0
# Janela de troca, a mesma do resto do projeto.
SEGUNDOS_TRADE = 5.0
# Dano abaixo disto não divide crédito -- um tiro de raspão não fez a kill.
DANO_MINIMO_PARA_CREDITO = 20.0

# Dano PRÓPRIO na vítima abaixo do qual a kill é "assistida": o companheiro fez
# o trabalho e o jogador deu o tiro final. Publicado pela HLTV para o Kill
# Rating do 2.0. Medido no corpus: 20,7% das kills; a regressão dá peso 0,208 à
# kill limpa e 0,014 à assistida -- ou seja, ela vale quase nada.
DANO_PROPRIO_PARA_KILL_LIMPA = 60.0

# ---------------------------------------------------------------------------
# Pesos dos seis sub-ratings no agregado.
#
# PROVISÓRIOS, e marcados como tal de propósito: os oficiais são fechados, e o
# caminho certo para estimá-los é regressão contra os ratings publicados
# (scripts/fit_rating.py). Até haver partidas com rating oficial preenchido em
# data/reference/hltv_ratings.json, estes valores são um ponto de partida
# informado pela documentação da HLTV -- que diz que a fórmula foi reajustada
# depois do lançamento para dar MAIS peso a kills.
# ---------------------------------------------------------------------------
# Oito componentes: as kills entram separadas em LIMPA (o jogador causou pelo
# menos DANO_PROPRIO_PARA_KILL_LIMPA na vítima) e ASSISTIDA, e a morte trocada
# entra como CRÉDITO DE VOLTA ao lado da sobrevivência -- "morte trocada pune
# menos" não cabe num peso negativo, e os pesos aqui são não-negativos de
# propósito (ver scripts/fit_rating).
PESOS_PROVISORIOS = {
    "kills_limpas": 0.25,
    "kills_assistidas": 0.03,
    "dano": 0.18,
    "sobrevivencia": 0.12,
    "mortes_trocadas": 0.03,
    "kast": 0.15,
    "multikills": 0.09,
    "round_swing": 0.15,
}

# Abaixo disto o rating do jogador não é apresentado como confiável. 30 rounds é
# pouco mais de uma metade: abaixo disso um único round bom move o número mais
# que o desempenho.
MIN_ROUNDS_CONFIAVEL = 30

# Os cinco sub-ratings de escala de RAZÃO (só valores não-negativos, e o zero
# quer dizer "nada"). Nesses, normalizar é dividir pela média do conjunto.
SUB_RATINGS_RAZAO = ("kills_limpas", "kills_assistidas", "dano", "sobrevivencia",
                     "mortes_trocadas", "kast", "multikills")

# O Round Swing NÃO é escala de razão: ele tem sinal, e a média dele no corpus é
# NEGATIVA (-0,043 nas 9 partidas). A regra da HLTV de que round perdido não gera
# swing positivo corta os positivos de quem perdeu e deixa os débitos inteiros,
# então o total do corpus pende para baixo -- e é assim que tem que ser.
#
# Consequência: dividir pela média inverteria o sinal de todo mundo (um jogador
# com swing positivo sairia com sub-rating negativo). Foi o que aconteceu na
# primeira versão. Aqui ele é centrado em 1,00 e escalado pelo desvio:
#
#   norm = 1 + (x - média) / desvio * dispersão_alvo
#
# `dispersão_alvo` não é escolhida: é a MEDIANA do desvio relativo dos outros
# cinco (medido: 0,185 a 0,697, mediana 0,356). Sem ela o swing teria desvio 1,0
# normalizado e dominaria o agregado sozinho.


# ---------------------------------------------------------------------------
# Equipamento
# ---------------------------------------------------------------------------

def grupo_do_round(ticks: pl.DataFrame, rounds: pl.DataFrame) -> pl.DataFrame:
    """Grupo de equipamento de cada (round, jogador).

    A melhor arma que ele teve em mãos durante o round de jogo -- quem comprou
    AWP e morreu segurando a pistola comprou AWP. Warmup e tempo parado ficam de
    fora pelo mesmo critério do resto do projeto (decisão 8b).
    """
    janela = rounds.select(["round_num", "freeze_end", "end"])
    base = (
        ticks.join(janela, on="round_num", how="inner")
        .filter((pl.col("tick") >= pl.col("freeze_end")) & (pl.col("tick") <= pl.col("end")))
        .select(["round_num", "steamid", "side", "active_weapon_name", "current_equip_value"])
        .with_columns(
            pl.col("active_weapon_name")
            .replace_strict(ARMA_PARA_GRUPO, default=None)
            .alias("grupo")
        )
        .drop_nulls("grupo")
        .with_columns(
            pl.col("grupo").replace_strict(FORCA_DO_GRUPO, default=0).alias("forca")
        )
    )
    return (
        base.group_by(["round_num", "steamid"], maintain_order=True)
        .agg(
            pl.col("side").first(),
            pl.col("grupo").sort_by("forca").last(),
            pl.col("current_equip_value").max().alias("equip"),
        )
    )


def taxas_por_confronto(
    grupos: pl.DataFrame, rounds: pl.DataFrame, team_of: dict[int, str],
    vencedor_por_round: dict[int, str],
) -> tuple[dict, dict]:
    """Taxa de vitória de cada confronto (lado, meu grupo, grupo deles).

    O grupo de um TIME num round é a moda dos cinco: é assim que se fala de
    economia no jogo ("eles estão de rifle"), e usar o grupo individual faria o
    mesmo round contar seis vezes com cinco respostas diferentes.

    As células esparsas encolhem na direção da taxa do lado (`K_ENCOLHIMENTO`).
    Sem isso, um confronto visto três vezes com três vitórias vira "100% de
    vitória" e o peso da kill derretia para o mínimo.
    """
    por_time = (
        grupos.with_columns(
            pl.col("steamid")
            .map_elements(lambda s: team_of.get(s), return_dtype=pl.String)
            .alias("time")
        )
        .drop_nulls("time")
        .group_by(["round_num", "time"], maintain_order=True)
        .agg(pl.col("grupo").mode().sort().first(), pl.col("side").mode().sort().first())
    )

    linhas = []
    for rn, g in por_time.group_by("round_num", maintain_order=True):
        rn = int(rn[0]) if isinstance(rn, tuple) else int(rn)
        if g.height != 2:
            continue
        a, b = g.row(0, named=True), g.row(1, named=True)
        venc = vencedor_por_round.get(rn)
        for eu, ele in ((a, b), (b, a)):
            linhas.append({
                "side": eu["side"], "meu": eu["grupo"], "dele": ele["grupo"],
                "venceu": 1 if venc == eu["time"] else 0,
            })

    if not linhas:
        return {}, {}

    df = pl.DataFrame(linhas)
    base_lado = {
        r["side"]: float(r["taxa"])
        for r in df.group_by("side", maintain_order=True).agg(pl.col("venceu").mean().alias("taxa")).iter_rows(named=True)
    }
    celulas = {}
    for r in (
        df.group_by(["side", "meu", "dele"], maintain_order=True)
        .agg(pl.col("venceu").mean().alias("taxa"), pl.len().alias("n"))
        .iter_rows(named=True)
    ):
        n = float(r["n"])
        base = base_lado.get(r["side"], 0.5)
        peso = n / (n + K_ENCOLHIMENTO)
        celulas[(r["side"], r["meu"], r["dele"])] = {
            "taxa": peso * float(r["taxa"]) + (1 - peso) * base,
            "taxa_crua": float(r["taxa"]),
            "n": int(r["n"]),
        }
    return celulas, base_lado


class CelulasComFallback(dict):
    """Tabela de confrontos que, sem a célula com colete, cai na mesma célula
    sem colete (e o rating cai na taxa do lado se nem ela existir)."""

    def get(self, chave, default=None):
        if chave in self:
            return self[chave]
        lado, meu, dele = chave
        sem = (lado, str(meu).split("|")[0], str(dele).split("|")[0])
        return dict.get(self, sem, default)


def peso_da_kill(taxa: float | None) -> float:
    """Quanto vale uma kill num confronto com aquela taxa de vitória.

    Quanto MAIOR a chance que o time já tinha, MENOS a kill vale: matar quem
    estava de pistola inicial num round já ganho não é o mesmo que matar um
    rifle num round parelho. A reta vem dos dois pontos publicados pela HLTV --
    ver o cabeçalho das constantes.
    """
    if taxa is None:
        taxa = 0.5
    return float(np.clip(PESO_KILL_A + PESO_KILL_B * float(taxa), PESO_KILL_MIN, PESO_KILL_MAX))


# ---------------------------------------------------------------------------
# Round Swing
# ---------------------------------------------------------------------------

class ModeloDeRound:
    """P(ganhar o round | estado), por regressão logística.

    Por que NÃO frequência empírica por estado: o espaço tem centenas de
    combinações (vivos x vivos x bomba x equipamento x lado) e o corpus tem cerca
    de 200 rounds por partida. Contar por estado produziria "100% de vitória" a
    partir de dois casos observados, e o Round Swing inteiro viraria ruído.

    Um modelo paramétrico com quatro entradas generaliza com poucos rounds e
    nunca devolve certeza absoluta. O preço é supor que o efeito de cada entrada
    é monotônico e aditivo na escala logit -- o que é razoável para diferença de
    vivos e de equipamento, e é a troca certa neste tamanho de corpus.

    A qualidade depende do tamanho do corpus e MELHORA a cada demo processada;
    `metricas` reporta calibração (Brier) e separação (AUC) para isso não virar
    fé.
    """

    COLUNAS = ("dif_vivos", "dif_equip_milhares", "bomba_a_favor", "eh_ct")

    def __init__(self):
        self.modelo = None
        self.metricas: dict = {}

    def treina(self, X: np.ndarray, y: np.ndarray) -> "ModeloDeRound":
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import brier_score_loss, roc_auc_score

        if X.shape[0] < 50 or len(set(y.tolist())) < 2:
            self.modelo = None
            self.metricas = {"amostras": int(X.shape[0]), "treinou": False}
            return self

        self.modelo = LogisticRegression(max_iter=1000)
        self.modelo.fit(X, y)
        p = self.modelo.predict_proba(X)[:, 1]
        self.metricas = {
            "amostras": int(X.shape[0]),
            "treinou": True,
            # Brier: erro quadrático da probabilidade. Mede CALIBRAÇÃO -- se o
            # modelo diz 70% e acerta 70% das vezes, ele é honesto.
            "brier": float(brier_score_loss(y, p)),
            # AUC mede SEPARAÇÃO: se ele ordena bem os estados vencedores.
            "auc": float(roc_auc_score(y, p)),
            # precisão cheia: o pipeline de cada partida reconstrói o modelo a
            # partir daqui (da_referencia), e arredondar mudaria o Round Swing
            "coeficientes": dict(zip(self.COLUNAS, self.modelo.coef_[0].tolist())),
            "intercepto": float(self.modelo.intercept_[0]),
        }
        return self

    @classmethod
    def da_referencia(cls, metricas: dict | None) -> "ModeloDeRound":
        """O modelo GLOBAL, reconstruído dos coeficientes gravados na
        referência de escala -- sem retreinar a cada partida (decisão 11: um
        modelo só, senão o Round Swing de uma página não compara com o de outra).
        """
        m = cls()
        m.metricas = dict(metricas or {})
        if metricas and metricas.get("treinou") and metricas.get("coeficientes"):
            m._coef = np.array([float(metricas["coeficientes"][c]) for c in cls.COLUNAS])
            m._intercepto = float(metricas["intercepto"])
        return m

    def prob(self, X: np.ndarray) -> np.ndarray:
        """Probabilidade de vitória. Sempre em (0, 1), nunca 0 nem 1 cravados."""
        if self.modelo is None and getattr(self, "_coef", None) is not None:
            p = 1.0 / (1.0 + np.exp(-(X @ self._coef + self._intercepto)))
            return np.clip(p, 1e-6, 1 - 1e-6)
        if self.modelo is None:
            return np.full(X.shape[0], 0.5)
        return np.clip(self.modelo.predict_proba(X)[:, 1], 1e-6, 1 - 1e-6)


def _estado(dif_vivos: int, dif_equip: float, bomba: bool, eh_ct: bool) -> list[float]:
    """Vetor de entrada do modelo, do ponto de vista de UM lado.

    Equipamento em milhares para o coeficiente ficar legível ao lado dos outros.

    A bomba entra COM SINAL, e isso não é detalhe: cada evento gera duas linhas,
    uma por lado, com rótulos opostos. Uma flag `bomba_plantada` valeria 1 nas
    duas, ficaria perfeitamente não-informativa por construção, e o coeficiente
    saía em -0,0001 -- foi exatamente o que aconteceu na primeira versão. Bomba
    plantada é vantagem de QUEM PLANTOU, então vale +1 para o TR e -1 para o CT.
    """
    if not bomba:
        favor = 0.0
    else:
        favor = -1.0 if eh_ct else 1.0
    return [float(dif_vivos), float(dif_equip) / 1000.0, favor, 1.0 if eh_ct else 0.0]


def amostras_de_round(
    kills: pl.DataFrame, rounds: pl.DataFrame, grupos: pl.DataFrame,
    team_of: dict[int, str], vencedor_por_round: dict[int, str],
) -> tuple[np.ndarray, np.ndarray]:
    """Uma linha de treino por (evento, lado): o estado e se aquele lado venceu."""
    equip_por_round = (
        grupos.with_columns(
            pl.col("steamid").map_elements(lambda s: team_of.get(s), return_dtype=pl.String).alias("time")
        )
        .drop_nulls("time")
        .group_by(["round_num", "time"], maintain_order=True)
        .agg(pl.col("equip").sum().alias("equip_time"), pl.col("side").mode().sort().first())
    )
    equip = {
        (int(r["round_num"]), r["time"]): (float(r["equip_time"]), r["side"])
        for r in equip_por_round.iter_rows(named=True)
    }

    plant = {
        int(r["round_num"]): r["bomb_plant"]
        for r in rounds.select(["round_num", "bomb_plant"]).iter_rows(named=True)
    }

    X, y = [], []
    for rn_t, rk in kills.sort("tick").group_by("round_num", maintain_order=True):
        rn = int(rn_t[0]) if isinstance(rn_t, tuple) else int(rn_t)
        vivos = {"A": 5, "B": 5}
        t_plant = plant.get(rn)
        venc = vencedor_por_round.get(rn)
        if venc is None:
            continue

        for k in rk.iter_rows(named=True):
            time_vitima = team_of.get(k["victim_steamid"])
            if time_vitima is None:
                continue
            vivos[time_vitima] -= 1
            bomba = t_plant is not None and k["tick"] >= int(t_plant)
            for time in ("A", "B"):
                outro = "B" if time == "A" else "A"
                eq_meu, lado = equip.get((rn, time), (0.0, "ct"))
                eq_dele, _ = equip.get((rn, outro), (0.0, "ct"))
                X.append(_estado(vivos[time] - vivos[outro], eq_meu - eq_dele,
                                 bomba, lado == "ct"))
                y.append(1 if venc == time else 0)

    if not X:
        return np.zeros((0, 4)), np.zeros(0)
    return np.array(X, dtype=float), np.array(y, dtype=int)


def swing_por_evento(
    kills: pl.DataFrame, damages: pl.DataFrame, blinds: pl.DataFrame | None,
    rounds: pl.DataFrame, grupos: pl.DataFrame, modelo: ModeloDeRound,
    team_of: dict[int, str], vencedor_por_round: dict[int, str], tickrate: int,
) -> pl.DataFrame:
    """Round Swing de cada kill, ja dividido entre os envolvidos.

    A variacao de probabilidade de um evento e UMA so; o que muda e quem levou o
    credito dela. A soma distribuida nunca excede essa variacao -- os pesos somam
    1,0 e a parcela sem destinatario simplesmente nao e distribuida, em vez de
    ser jogada no matador. Nem todo pedaco de swing e atribuivel, e fingir que e
    seria inventar contribuicao.

    A vitima e debitada da variacao inteira: a morte dela custou ao time dela
    exatamente o que rendeu ao outro. Com isso o swing de um evento soma zero
    entre os dez jogadores, que e a propriedade que torna o numero comparavel.

    Leitura declarada: a HLTV diz que o credito vai para "quem deu o dano final,
    quem deu dano, quem cegou e quem trocou". "Quem trocou" e ambiguo -- aqui e o
    proprio matador, quando a kill dele troca a morte recente de um companheiro.
    E recalibravel (`CREDITO_TRADE`).
    """
    equip_por_round = (
        grupos.with_columns(
            pl.col("steamid").map_elements(lambda s: team_of.get(s), return_dtype=pl.String).alias("time")
        )
        .drop_nulls("time")
        .group_by(["round_num", "time"], maintain_order=True)
        .agg(pl.col("equip").sum().alias("equip_time"), pl.col("side").mode().sort().first())
    )
    equip = {
        (int(r["round_num"]), r["time"]): (float(r["equip_time"]), r["side"])
        for r in equip_por_round.iter_rows(named=True)
    }
    plant = {
        int(r["round_num"]): r["bomb_plant"]
        for r in rounds.select(["round_num", "bomb_plant"]).iter_rows(named=True)
    }

    janela_trade = int(SEGUNDOS_TRADE * tickrate)
    janela_flash = int(SEGUNDOS_FLASH_ANTES_DA_KILL * tickrate)
    fim_do_round = dict(rounds.select(pl.col("round_num").cast(pl.Int64), "end").iter_rows())

    linhas = []
    for rn_t, rk in kills.sort("tick").group_by("round_num", maintain_order=True):
        rn = int(rn_t[0]) if isinstance(rn_t, tuple) else int(rn_t)
        vivos = {"A": 5, "B": 5}
        t_plant = plant.get(rn)
        # Round DECIDIDO não move probabilidade: a morte pela bomba é o próprio
        # fim do round, e as kills da cauda acontecem depois dele. Medido: no
        # Swing oficial elas somam zero; contadas aqui, a vítima pagava uma
        # variação que ninguém recebia.
        fim = fim_do_round.get(rn)
        eventos = [e for e in rk.to_dicts()
                   if (fim is None or e["tick"] < fim) and e.get("weapon") != "planted_c4"]

        dmg_round = damages.filter(pl.col("round_num") == rn)
        blind_round = (
            None if blinds is None or blinds.height == 0
            else blinds.filter(pl.col("round_num") == rn)
        )

        for i, k in enumerate(eventos):
            time_vitima = team_of.get(k["victim_steamid"])
            time_matador = team_of.get(k["attacker_steamid"])
            if time_vitima is None:
                continue
            outro = "B" if time_vitima == "A" else "A"

            bomba = t_plant is not None and k["tick"] >= int(t_plant)
            antes = dict(vivos)
            vivos[time_vitima] -= 1

            # a variacao e medida do ponto de vista do time que MATOU
            beneficiado = time_matador if time_matador and time_matador != time_vitima else outro
            adversario = "B" if beneficiado == "A" else "A"
            eq_meu, lado = equip.get((rn, beneficiado), (0.0, "ct"))
            eq_dele, _ = equip.get((rn, adversario), (0.0, "ct"))

            p_antes = modelo.prob(np.array([_estado(
                antes[beneficiado] - antes[adversario], eq_meu - eq_dele, bomba, lado == "ct")]))[0]
            p_depois = modelo.prob(np.array([_estado(
                vivos[beneficiado] - vivos[adversario], eq_meu - eq_dele, bomba, lado == "ct")]))[0]
            delta = float(p_depois - p_antes)

            # --- a vitima paga a conta inteira -----------------------------
            linhas.append({"round_num": rn, "steamid": k["victim_steamid"],
                           "swing": -delta, "papel": "morreu"})

            if time_matador is None or time_matador == time_vitima:
                # morte sem atacante (queda, bomba) ou fogo amigo: ninguem leva
                # credito, mas a vitima ja pagou
                continue

            # --- dano final: fica com o que os outros não levaram -----------
            # REGRESSÃO (Fase D): o matador levava só CREDITO_KILL (55%) e a parte
            # sem destinatário -- sem dano de outro, sem flash, sem trade -- não
            # ia para ninguém. O swing de um evento, que esta docstring promete
            # somar zero, pendia para baixo: média -4,67 p.p. por round contra
            # -0,01 do Swing oficial da HLTV, e escala 0,70 da oficial.
            # Com a sobra para o matador: escala 0,95-1,01, erro 4,71 -> 1,93.
            i_matador = len(linhas)
            linhas.append({"round_num": rn, "steamid": k["attacker_steamid"],
                           "swing": delta, "papel": "kill"})

            # --- quem deu dano antes --------------------------------------
            anteriores = dmg_round.filter(
                (pl.col("victim_steamid") == k["victim_steamid"])
                & (pl.col("tick") <= k["tick"])
                & (pl.col("attacker_steamid") != k["attacker_steamid"])
                & pl.col("attacker_steamid").is_not_null()
            )
            if anteriores.height:
                por_jogador = (
                    anteriores.group_by("attacker_steamid", maintain_order=True)
                    .agg(pl.col("dmg_health_real").sum().alias("d"))
                    .filter(pl.col("d") >= DANO_MINIMO_PARA_CREDITO)
                )
                por_jogador = por_jogador.filter(
                    pl.col("attacker_steamid").map_elements(
                        lambda s: team_of.get(s) == time_matador, return_dtype=pl.Boolean)
                )
                total = float(por_jogador["d"].sum() or 0)
                if total > 0:
                    for r in por_jogador.iter_rows(named=True):
                        linhas.append({
                            "round_num": rn, "steamid": r["attacker_steamid"],
                            "swing": delta * CREDITO_DANO * float(r["d"]) / total,
                            "papel": "dano",
                        })

            # --- quem cegou a vitima ---------------------------------------
            if blind_round is not None and blind_round.height:
                cegou = blind_round.filter(
                    (pl.col("user_steamid") == k["victim_steamid"])
                    & (pl.col("tick") <= k["tick"])
                    & (pl.col("tick") >= k["tick"] - janela_flash)
                    & (pl.col("attacker_steamid") != k["attacker_steamid"])
                )
                if cegou.height:
                    quem = cegou.sort("blind_duration").row(-1, named=True)["attacker_steamid"]
                    if team_of.get(quem) == time_matador:
                        linhas.append({"round_num": rn, "steamid": quem,
                                       "swing": delta * CREDITO_FLASH, "papel": "flash"})

            # --- a kill trocou a morte recente de um companheiro? ----------
            trocou = any(
                team_of.get(a["victim_steamid"]) == time_matador
                and a["attacker_steamid"] == k["victim_steamid"]
                and k["tick"] - a["tick"] <= janela_trade
                for a in eventos[:i]
            )
            if trocou:
                linhas.append({"round_num": rn, "steamid": k["attacker_steamid"],
                               "swing": delta * CREDITO_TRADE, "papel": "trade"})
            linhas[i_matador]["swing"] = delta - sum(l["swing"] for l in linhas[i_matador + 1:])

        # --- fim do round: a chance vai do último estado a 1 (ou 0) ----------
        # O salto final (bomba explodindo, desarme, tempo, a última kill não
        # levar a exatamente 100%) não é de nenhuma kill e antes não ia para
        # ninguém. Vai em partes iguais para quem TERMINOU VIVO: o time que
        # venceu recebe, o que perdeu e ainda tinha gente viva paga. Medido
        # contra os 310 Swings oficiais: escala 0,95 -> 1,01, erro 2,08 -> 1,93.
        venc_time = vencedor_por_round.get(rn)
        if venc_time in ("A", "B"):
            perd_time = "B" if venc_time == "A" else "A"
            mortos = {e["victim_steamid"] for e in eventos}
            vivos_fim = {tm: [s for s, x in team_of.items() if x == tm and s not in mortos]
                         for tm in ("A", "B")}
            eq_v, lado_v = equip.get((rn, venc_time), (0.0, "ct"))
            eq_p, _ = equip.get((rn, perd_time), (0.0, "ct"))
            p_fim = modelo.prob(np.array([_estado(
                len(vivos_fim[venc_time]) - len(vivos_fim[perd_time]), eq_v - eq_p,
                t_plant is not None, lado_v == "ct")]))[0]
            salto = 1.0 - float(p_fim)
            # Os dois lados do salto SEMPRE têm destinatário, senão a soma do
            # round vaza (medido: sem isto, 1 de 31 partidas somava zero).
            # - vencedor sem ninguém vivo (bomba explode com o TR todo morto):
            #   o salto é do time inteiro que plantou e segurou;
            # - perdedor sem ninguém vivo: a última morte é a que fechou o round,
            #   e é ela que paga o salto que o modelo ainda não tinha dado.
            ganham = vivos_fim[venc_time] or [s for s, x in team_of.items() if x == venc_time]
            ultima = [e["victim_steamid"] for e in eventos if team_of.get(e["victim_steamid"]) == perd_time]
            pagam = vivos_fim[perd_time] or ultima[-1:]
            for sid in ganham:
                linhas.append({"round_num": rn, "steamid": sid,
                               "swing": salto / len(ganham), "papel": "fim_do_round"})
            for sid in pagam:
                linhas.append({"round_num": rn, "steamid": sid,
                               "swing": -salto / len(pagam), "papel": "fim_do_round"})

    if not linhas:
        return pl.DataFrame(
            schema={"round_num": pl.Int64, "steamid": pl.Int64, "swing": pl.Float64}
        )

    swing = pl.DataFrame(linhas)
    # Variação de probabilidade PURA, sem corte para round perdido (decisão
    # 22k do CLAUDE.md). A HLTV escreve que "round perdido não gera Swing
    # positivo", mas o Swing oficial soma zero em 28 de 31 partidas, e cortar o
    # positivo de quem perdeu faria a soma de TODA partida ficar negativa (a
    # nossa ficava em -8,7 por partida). A frase descreve o time, não uma regra
    # por jogador: o time que perde o round já soma negativo por construção.
    return swing.group_by(["round_num", "steamid"], maintain_order=True).agg(pl.col("swing").sum())


# ---------------------------------------------------------------------------
# Os seis sub-ratings
# ---------------------------------------------------------------------------

REFERENCIA_FILE = Path(__file__).resolve().parent / "rating_reference.json"


# Pesos AJUSTADOS contra os ratings oficiais publicados, gravados por
# `scripts/fit_rating.py --fit-pesos --gravar`. Quando o arquivo existe, eles
# substituem os provisórios; os provisórios ficam como plano B (primeira
# execução, corpus sem rating oficial).
#
# Os pesos valem para a REFERÊNCIA DE ESCALA sobre a qual foram ajustados: a
# regressão roda sobre os sub-ratings normalizados, e normalizar depende das
# médias do corpus. Por isso o arquivo guarda as médias usadas, e o rating
# avisa (`pesos_desatualizados`) quando a referência mudou desde o ajuste.
PESOS_FILE = Path(__file__).resolve().parent / "rating_weights.json"


def carrega_pesos() -> dict:
    """{"pesos", "intercepto", "origem", "medias_da_referencia"}."""
    if PESOS_FILE.exists():
        dados = json.loads(PESOS_FILE.read_text(encoding="utf-8"))
        # O arquivo pode ser de uma lista de componentes ANTERIOR (foi o caso
        # quando as kills se separaram em limpa/assistida). Nesse caso ele não
        # serve: cair nos provisórios e dizer isso é melhor que estourar ou,
        # pior, completar com zero em silêncio.
        if set(PESOS_PROVISORIOS) <= set(dados.get("pesos", {})):
            return {
                "pesos": {n: float(dados["pesos"][n]) for n in PESOS_PROVISORIOS},
                "intercepto": float(dados.get("intercepto", 0.0)),
                "origem": "ajustados contra ratings oficiais",
                "medias_da_referencia": dados.get("medias_da_referencia"),
            }
        return {"pesos": dict(PESOS_PROVISORIOS), "intercepto": 0.0,
                "origem": "provisorios (o arquivo de pesos é de outra lista de componentes; refaça --fit-pesos --gravar)",
                "medias_da_referencia": None}
    return {"pesos": dict(PESOS_PROVISORIOS), "intercepto": 0.0,
            "origem": "provisorios", "medias_da_referencia": None}


def carrega_referencia() -> dict | None:
    """Medias de cada sub-rating no conjunto das partidas.

    Mesmo padrao de `archetype_reference.json` e `global_model.json` (decisao 16):
    a escala e ajustada no CONJUNTO, nunca dentro da partida. Normalizar dentro
    da partida faria a media dar 1,00 em toda partida por construcao, e o rating
    deixaria de comparar jogadores de partidas diferentes -- que e exatamente
    para o que ele serve.
    """
    if not REFERENCIA_FILE.exists():
        return None
    return json.loads(REFERENCIA_FILE.read_text(encoding="utf-8"))


def sub_ratings(
    kills: pl.DataFrame, damages: pl.DataFrame, rounds: pl.DataFrame,
    grupos: pl.DataFrame, swing: pl.DataFrame, kast: pl.DataFrame,
    celulas: dict, team_of: dict[int, str], tickrate: int = 64,
) -> pl.DataFrame:
    """Os seis componentes por jogador, ainda em unidade bruta (por round).

    Os cinco primeiros sao do Rating 2.1 com ajuste de economia; o sexto e o
    Round Swing. Eles saem SEPARADOS de proposito: o agregado sozinho nao deixa
    conferir nada, e a aba de perfil abre os seis justamente para dar pra ver que
    o jogador tem rating alto por swing e baixo por sobrevivencia.
    """
    n_rounds = rounds.height
    grupo_de = {
        (int(r["round_num"]), int(r["steamid"])): (r["grupo"], r["side"])
        for r in grupos.iter_rows(named=True)
    }

    # Dano PRÓPRIO do matador naquela vítima, naquele round: é ele que separa a
    # kill limpa da assistida (DANO_PROPRIO_PARA_KILL_LIMPA).
    meu_dano = {}
    for d in damages.iter_rows(named=True):
        atk, vit = d["attacker_steamid"], d["victim_steamid"]
        if atk is None or vit is None or team_of.get(atk) == team_of.get(vit):
            continue
        chave = (int(d["round_num"]), int(atk), int(vit))
        meu_dano[chave] = meu_dano.get(chave, 0.0) + float(d["dmg_health_real"])

    # --- peso de cada kill pela economia do confronto ---------------------
    linhas_kill = []
    for k in kills.iter_rows(named=True):
        atk, vit = k["attacker_steamid"], k["victim_steamid"]
        if atk is None or vit is None or team_of.get(atk) == team_of.get(vit):
            continue
        rn = int(k["round_num"])
        meu = grupo_de.get((rn, int(atk)))
        dele = grupo_de.get((rn, int(vit)))
        if meu is None or dele is None:
            peso = 1.0
        else:
            celula = celulas.get((meu[1], meu[0], dele[0]))
            peso = peso_da_kill(None if celula is None else celula["taxa"])
        limpa = meu_dano.get((rn, int(atk), int(vit)), 0.0) >= DANO_PROPRIO_PARA_KILL_LIMPA
        linhas_kill.append({"steamid": atk, "round_num": rn, "peso": peso, "limpa": limpa})

    esquema_kill = {"steamid": pl.Int64, "round_num": pl.Int64, "peso": pl.Float64, "limpa": pl.Boolean}
    por_kill = (
        pl.DataFrame(linhas_kill, schema=esquema_kill) if linhas_kill
        else pl.DataFrame(schema=esquema_kill)
    )

    kills_ajustadas = por_kill.group_by("steamid", maintain_order=True).agg(
        pl.col("peso").sum().alias("kills_ponderadas"), pl.len().alias("kills_cruas"),
        pl.col("peso").filter(pl.col("limpa")).sum().alias("kills_limpas_ponderadas"),
        pl.col("peso").filter(~pl.col("limpa")).sum().alias("kills_assistidas_ponderadas"),
    )
    # multi-kill: rounds com 2 ou mais kills, ponderados pelo peso medio deles
    multi = (
        por_kill.group_by(["steamid", "round_num"], maintain_order=True)
        .agg(pl.len().alias("n"), pl.col("peso").mean().alias("peso_medio"))
        .filter(pl.col("n") >= 2)
        .group_by("steamid", maintain_order=True)
        .agg(((pl.col("n") - 1) * pl.col("peso_medio")).sum().alias("multikills_ponderados"))
    )

    # --- dano, ponderado pelo grupo de quem levou -------------------------
    linhas_dano = []
    for d in damages.iter_rows(named=True):
        atk, vit = d["attacker_steamid"], d["victim_steamid"]
        if atk is None or vit is None or team_of.get(atk) == team_of.get(vit):
            continue
        rn = int(d["round_num"])
        meu = grupo_de.get((rn, int(atk)))
        dele = grupo_de.get((rn, int(vit)))
        celula = None if meu is None or dele is None else celulas.get((meu[1], meu[0], dele[0]))
        peso = peso_da_kill(None if celula is None else celula["taxa"])
        linhas_dano.append({"steamid": atk, "round_num": rn, "dano": float(d["dmg_health_real"]) * peso})
    dano = (
        pl.DataFrame(linhas_dano, schema={"steamid": pl.Int64, "round_num": pl.Int64, "dano": pl.Float64})
        .group_by("steamid", maintain_order=True).agg(pl.col("dano").sum().alias("dano_ponderado"))
        if linhas_dano else pl.DataFrame(schema={"steamid": pl.Int64, "dano_ponderado": pl.Float64})
    )

    mortes = (
        kills.filter(pl.col("victim_steamid").is_not_null())
        .group_by("victim_steamid", maintain_order=True).agg(pl.len().alias("mortes"))
        .rename({"victim_steamid": "steamid"})
    )
    # Morte TROCADA: a mesma marcação do KAST (basic_metrics), usada aqui como
    # crédito de volta -- morrer e o time trocar não é morrer à toa.
    from metrics.basic_metrics import DEFAULT_TRADE_WINDOW_SECONDS, traded_deaths

    trocadas = traded_deaths(kills, DEFAULT_TRADE_WINDOW_SECONDS, tickrate)
    trocadas_por_jogador = (
        trocadas.filter(pl.col("was_traded")).group_by("steamid", maintain_order=True).agg(pl.len().alias("mortes_trocadas"))
        .select(pl.col("steamid").cast(pl.Int64), "mortes_trocadas")
        if trocadas.height else pl.DataFrame(schema={"steamid": pl.Int64, "mortes_trocadas": pl.UInt32})
    )
    swing_total = swing.group_by("steamid", maintain_order=True).agg(pl.col("swing").sum().alias("swing_total"))

    base = (
        pl.DataFrame({"steamid": sorted(team_of)}, schema={"steamid": pl.Int64})
        .join(kills_ajustadas, on="steamid", how="left")
        .join(multi, on="steamid", how="left")
        .join(dano, on="steamid", how="left")
        .join(mortes, on="steamid", how="left")
        .join(trocadas_por_jogador, on="steamid", how="left")
        .join(swing_total, on="steamid", how="left")
        .join(_kast_por_jogador(kast), on="steamid", how="left")
        .fill_null(0)
    )

    resultado = base.with_columns(
        pl.lit(n_rounds).alias("rounds"),
        (pl.col("kills_ponderadas") / n_rounds).alias("sub_kills"),
        (pl.col("kills_limpas_ponderadas") / n_rounds).alias("sub_kills_limpas"),
        (pl.col("kills_assistidas_ponderadas") / n_rounds).alias("sub_kills_assistidas"),
        (pl.col("dano_ponderado") / n_rounds).alias("sub_dano"),
        (1.0 - pl.col("mortes") / n_rounds).alias("sub_sobrevivencia"),
        (pl.col("mortes_trocadas") / n_rounds).alias("sub_mortes_trocadas"),
        (pl.col("kast_pct") / 100.0).alias("sub_kast"),
        (pl.col("multikills_ponderados") / n_rounds).alias("sub_multikills"),
        (pl.col("swing_total") / n_rounds).alias("sub_round_swing"),
    )

    # Os mesmos seis, separados por lado (ver componentes_por_lado). Ficam em
    # colunas `sub_<nome>_ct` e `sub_<nome>_t`, com os rounds de cada lado; é
    # `rating()` que decide se normaliza por lado ou no agregado.
    lado_de = {chave: v[1] for chave, v in grupo_de.items()}
    por_lado = componentes_por_lado(por_kill, linhas_dano, kills, swing, kast, lado_de, team_of, trocadas)
    if por_lado.height:
        colunas = ["rounds_lado"] + [f"sub_{n}" for n in PESOS_PROVISORIOS]
        largo = por_lado.select(["steamid", "lado", *colunas]).pivot(
            on="lado", index="steamid", values=colunas)
        # o pivot nomeia "sub_kills_ct"/"sub_kills_t" quando há mais de um valor
        renomes = {c: c.replace("_lado_", "_") for c in largo.columns if c.startswith("rounds_lado_")}
        largo = largo.rename(renomes)
        resultado = resultado.join(largo, on="steamid", how="left")
    return resultado


def _kast_por_jogador(kast: pl.DataFrame) -> pl.DataFrame:
    """KAST% por jogador, aceitando o resumo OU a tabela round a round.

    O round a round é o que permite separar CT de TR (ver componentes_por_lado);
    o resumo continua servindo para quem só tem ele.
    """
    if "kast_pct" in kast.columns:
        return kast.select(pl.col("steamid").cast(pl.Int64), "kast_pct")
    return (kast.group_by("steamid", maintain_order=True)
            .agg((100.0 * pl.col("kast_round").cast(pl.Float64).mean()).alias("kast_pct"))
            .select(pl.col("steamid").cast(pl.Int64), "kast_pct"))


def componentes_por_lado(
    por_kill: pl.DataFrame, linhas_dano: list[dict], kills: pl.DataFrame,
    swing: pl.DataFrame, kast: pl.DataFrame, lado_de: dict, team_of: dict[int, str],
    trocadas: pl.DataFrame | None = None,
) -> pl.DataFrame:
    """Os mesmos componentes, mas separados em CT e TR.

    Por que separado (metodologia do Rating 2.0 da HLTV, que publica dez
    sub-ratings, cinco por lado): os dois lados são trabalhos diferentes e têm
    escalas diferentes -- no corpus, a sobrevivência de CT é sistematicamente
    maior que a de TR. Normalizar tudo junto faz o jogador ser comparado com uma
    média que mistura os dois, e quem jogou mais rounds de um lado ganha ou perde
    por isso. `rating()` normaliza cada lado contra a média DAQUELE lado e junta
    os dois pelos rounds jogados em cada um.
    """
    lado = pl.Series("lado", [], dtype=pl.Utf8)
    rounds_lado = {}
    for (rn, sid), s in lado_de.items():
        rounds_lado[(sid, s)] = rounds_lado.get((sid, s), 0) + 1
    base = pl.DataFrame(
        [{"steamid": sid, "lado": s, "rounds_lado": n} for (sid, s), n in rounds_lado.items()],
        schema={"steamid": pl.Int64, "lado": pl.Utf8, "rounds_lado": pl.Int64},
    )
    if base.height == 0:
        return base

    def _lado(rn, sid):
        return lado_de.get((int(rn), int(sid)))

    k = por_kill.with_columns(
        pl.struct(["round_num", "steamid"]).map_elements(
            lambda r: _lado(r["round_num"], r["steamid"]), return_dtype=pl.Utf8).alias("lado")
    ).drop_nulls("lado")
    kills_lado = k.group_by("steamid", "lado", maintain_order=True).agg(
        pl.col("peso").sum().alias("kills_ponderadas"),
        pl.col("peso").filter(pl.col("limpa")).sum().alias("kills_limpas_ponderadas"),
        pl.col("peso").filter(~pl.col("limpa")).sum().alias("kills_assistidas_ponderadas"),
    )
    multi_lado = (
        k.group_by("steamid", "lado", "round_num", maintain_order=True)
        .agg(pl.len().alias("n"), pl.col("peso").mean().alias("peso_medio"))
        .filter(pl.col("n") >= 2)
        .group_by("steamid", "lado", maintain_order=True)
        .agg(((pl.col("n") - 1) * pl.col("peso_medio")).sum().alias("multikills_ponderados"))
    )
    dano_lado = (
        pl.DataFrame(linhas_dano, schema={"steamid": pl.Int64, "round_num": pl.Int64, "dano": pl.Float64})
        .with_columns(pl.struct(["round_num", "steamid"]).map_elements(
            lambda r: _lado(r["round_num"], r["steamid"]), return_dtype=pl.Utf8).alias("lado"))
        .drop_nulls("lado").group_by("steamid", "lado", maintain_order=True).agg(pl.col("dano").sum().alias("dano_ponderado"))
        if linhas_dano else pl.DataFrame(schema={"steamid": pl.Int64, "lado": pl.Utf8, "dano_ponderado": pl.Float64})
    )
    mortes_lado = (
        kills.filter(pl.col("victim_steamid").is_not_null())
        .select(pl.col("victim_steamid").cast(pl.Int64).alias("steamid"), pl.col("round_num").cast(pl.Int64))
        .with_columns(pl.struct(["round_num", "steamid"]).map_elements(
            lambda r: _lado(r["round_num"], r["steamid"]), return_dtype=pl.Utf8).alias("lado"))
        .drop_nulls("lado").group_by("steamid", "lado", maintain_order=True).agg(pl.len().alias("mortes"))
    )
    swing_lado = (
        swing.select(pl.col("steamid").cast(pl.Int64), pl.col("round_num").cast(pl.Int64), "swing")
        .with_columns(pl.struct(["round_num", "steamid"]).map_elements(
            lambda r: _lado(r["round_num"], r["steamid"]), return_dtype=pl.Utf8).alias("lado"))
        .drop_nulls("lado").group_by("steamid", "lado", maintain_order=True).agg(pl.col("swing").sum().alias("swing_total"))
    )
    # KAST por lado exige o dado ROUND A ROUND. Com só o resumo (kast_pct), o
    # KAST do jogador entra igual nos dois lados -- e o resumo avisa.
    if "kast_round" in kast.columns:
        kast_lado = (
            kast.select(pl.col("steamid").cast(pl.Int64), pl.col("round_num").cast(pl.Int64), "kast_round")
            .with_columns(pl.struct(["round_num", "steamid"]).map_elements(
                lambda r: _lado(r["round_num"], r["steamid"]), return_dtype=pl.Utf8).alias("lado"))
            .drop_nulls("lado").group_by("steamid", "lado", maintain_order=True)
            .agg((100.0 * pl.col("kast_round").cast(pl.Float64).mean()).alias("kast_pct"))
        )
    else:
        kast_lado = base.join(
            kast.select(pl.col("steamid").cast(pl.Int64), "kast_pct"), on="steamid", how="left"
        ).select("steamid", "lado", "kast_pct")

    if trocadas is not None and trocadas.height:
        trocadas_lado = (
            trocadas.filter(pl.col("was_traded"))
            .select(pl.col("steamid").cast(pl.Int64), pl.col("round_num").cast(pl.Int64))
            .with_columns(pl.struct(["round_num", "steamid"]).map_elements(
                lambda r: _lado(r["round_num"], r["steamid"]), return_dtype=pl.Utf8).alias("lado"))
            .drop_nulls("lado").group_by("steamid", "lado", maintain_order=True).agg(pl.len().alias("mortes_trocadas"))
        )
    else:
        trocadas_lado = pl.DataFrame(schema={"steamid": pl.Int64, "lado": pl.Utf8, "mortes_trocadas": pl.UInt32})

    for parte in (kills_lado, multi_lado, dano_lado, mortes_lado, swing_lado, kast_lado, trocadas_lado):
        base = base.join(parte, on=["steamid", "lado"], how="left")
    return base.fill_null(0).with_columns(
        (pl.col("kills_ponderadas") / pl.col("rounds_lado")).alias("sub_kills"),
        (pl.col("kills_limpas_ponderadas") / pl.col("rounds_lado")).alias("sub_kills_limpas"),
        (pl.col("kills_assistidas_ponderadas") / pl.col("rounds_lado")).alias("sub_kills_assistidas"),
        (pl.col("dano_ponderado") / pl.col("rounds_lado")).alias("sub_dano"),
        (1.0 - pl.col("mortes") / pl.col("rounds_lado")).alias("sub_sobrevivencia"),
        (pl.col("mortes_trocadas") / pl.col("rounds_lado")).alias("sub_mortes_trocadas"),
        (pl.col("kast_pct") / 100.0).alias("sub_kast"),
        (pl.col("multikills_ponderados") / pl.col("rounds_lado")).alias("sub_multikills"),
        (pl.col("swing_total") / pl.col("rounds_lado")).alias("sub_round_swing"),
    )


def dispersao_de_referencia(medias: dict, desvios: dict) -> float:
    """Dispersao relativa tipica dos cinco sub-ratings de razao.

    E ela que da a escala do Round Swing normalizado. Mediana e nao media porque
    um componente com dispersao muito alta (multikills, 0,70) puxaria a conta.
    """
    relativos = [
        desvios[n] / abs(medias[n])
        for n in SUB_RATINGS_RAZAO
        if desvios.get(n) and abs(medias.get(n, 0)) > 1e-9
    ]
    if not relativos:
        return 0.35
    return float(np.median(relativos))


def rating(
    tables: dict[str, pl.DataFrame], team_of: dict[int, str],
    vencedor_por_round: dict[int, str], kast: pl.DataFrame, tickrate: int,
    referencia: dict | None = None, modelo: ModeloDeRound | None = None,
) -> tuple[pl.DataFrame, dict]:
    """Contrato do projeto: `(per_round, summary)`.

    `per_round` e o Round Swing por (round, jogador) -- e nele que a validacao
    manual acontece, porque e o unico componente que nao se confere de cabeca.
    O resumo traz os seis sub-ratings e o agregado por jogador.
    """
    kills, rounds = tables["kills"], tables["rounds"]
    damages, ticks = tables["damages"], tables["ticks"]
    blinds = tables.get("player_blind")

    grupos = grupo_do_round(ticks, rounds)
    # Economia pelo CORPUS (metrics/economia.py): classe = arma mais cara +
    # colete, lida da compra; taxas estimadas nas 52 partidas. Sem a compra ou
    # sem a tabela, cai na estimativa dentro da partida (a versão antiga).
    from metrics.economia import carrega_tabela, celulas_para_o_rating, classe, compra_por_jogador

    tabela_eco = carrega_tabela()
    compra = tables.get("compra")
    if tabela_eco is not None and compra is not None and compra.height:
        classes = compra_por_jogador(compra).with_columns(
            pl.struct(["grupo", "colete"]).map_elements(lambda r: classe(r["grupo"], r["colete"]),
                                                         return_dtype=pl.Utf8).alias("classe")
        ).select("round_num", "steamid", "classe")
        grupos = (
            grupos.with_columns(pl.col("round_num").cast(pl.Int64), pl.col("steamid").cast(pl.UInt64))
            .join(classes, on=["round_num", "steamid"], how="left")
            .with_columns(pl.coalesce(["classe", "grupo"]).alias("grupo")).drop("classe")
        )
        celulas = CelulasComFallback(celulas_para_o_rating(tabela_eco))
        base_lado = tabela_eco["taxa_base_por_lado"]
        fonte_economia = "corpus"
    else:
        celulas, base_lado = taxas_por_confronto(grupos, rounds, team_of, vencedor_por_round)
        fonte_economia = "partida"

    if modelo is None:
        X, y = amostras_de_round(kills, rounds, grupos, team_of, vencedor_por_round)
        modelo = ModeloDeRound().treina(X, y)

    swing = swing_por_evento(
        kills, damages, blinds, rounds, grupos, modelo,
        team_of, vencedor_por_round, tickrate,
    )
    componentes = sub_ratings(
        kills, damages, rounds, grupos, swing, kast, celulas, team_of, tickrate
    )

    # --- escala: media 1,00 -----------------------------------------------
    # As estatisticas vem da REFERENCIA do conjunto. Sem ela (primeira execucao,
    # antes de `scripts/fit_rating.py`), caem para as da propria partida -- e o
    # resumo avisa, porque nesse modo o numero nao compara partidas diferentes.
    nomes = list(PESOS_PROVISORIOS)
    medias, desvios = {}, {}
    for nome in nomes:
        col = f"sub_{nome}"
        if referencia and nome in referencia.get("medias", {}):
            medias[nome] = float(referencia["medias"][nome])
            desvios[nome] = float(referencia.get("desvios", {}).get(nome) or 0.0)
        else:
            m, sd = componentes[col].mean(), componentes[col].std()
            medias[nome] = float(m or 0.0)
            desvios[nome] = float(sd) if sd else 0.0
        # Média ~0 só é problema onde se DIVIDE pela média (os de razão). O
        # Round Swing é centrado, e a média dele é zero por construção (soma zero
        # por partida). REGRESSÃO: a proteção valia para os seis, trocava a média
        # zero do Swing por 1,0 e deslocava cada partida por um valor diferente --
        # o peso do Swing caiu de 0,38 para 0,006 na regressão.
        if nome in SUB_RATINGS_RAZAO and abs(medias[nome]) < 1e-9:
            medias[nome] = 1.0

    dispersao_alvo = (
        float(referencia["dispersao_alvo"])
        if referencia and referencia.get("dispersao_alvo")
        else dispersao_de_referencia(medias, desvios)
    )

    def _normalizado(col: str, nome: str, m: float, sd: float) -> pl.Expr:
        """Um sub-rating na escala do rating: 1,00 e a media.

        Os de razao dividem pela media; o Round Swing e centrado e escalado pelo
        desvio, porque tem sinal e media zero (ver o comentario da constante).
        """
        if nome in SUB_RATINGS_RAZAO:
            return pl.col(col) / (m if abs(m) > 1e-9 else 1.0)
        if sd > 1e-9:
            return 1.0 + (pl.col(col) - m) / sd * dispersao_alvo
        return pl.lit(1.0)

    # --- por LADO, quando a referencia tem as medias de cada lado -----------
    # Metodologia do Rating 2.0 (dez sub-ratings, cinco por lado): CT e TR sao
    # trabalhos diferentes e tem escalas diferentes. Cada lado e normalizado
    # contra a media DAQUELE lado, e os dois entram no agregado pesados pelos
    # rounds jogados em cada um -- quem jogou 12 de CT e 9 de TR nao pode ter os
    # dois lados valendo igual.
    por_lado = (referencia or {}).get("medias_por_lado") or {}
    tem_colunas = all(f"sub_{n}_{l}" in componentes.columns for n in nomes for l in ("ct", "t"))
    usa_lados = bool(por_lado) and tem_colunas

    expressoes = []
    for nome in nomes:
        if usa_lados:
            partes = []
            for lado in ("ct", "t"):
                m = float(por_lado[lado]["medias"][nome])
                sd = float(por_lado[lado].get("desvios", {}).get(nome) or 0.0)
                partes.append(
                    pl.col(f"rounds_{lado}").fill_null(0)
                    * _normalizado(f"sub_{nome}_{lado}", nome, m, sd).fill_nan(1.0).fill_null(1.0)
                )
            total = pl.col("rounds_ct").fill_null(0) + pl.col("rounds_t").fill_null(0)
            expressoes.append(
                pl.when(total > 0).then((partes[0] + partes[1]) / total)
                .otherwise(_normalizado(f"sub_{nome}", nome, medias[nome], desvios.get(nome) or 0.0))
                .alias(f"norm_{nome}")
            )
        else:
            expressoes.append(
                _normalizado(f"sub_{nome}", nome, medias[nome], desvios.get(nome) or 0.0).alias(f"norm_{nome}")
            )

    normalizados = componentes.with_columns(expressoes)
    ajuste = carrega_pesos()
    agregado = ajuste["intercepto"] + sum(
        ajuste["pesos"][nome] * pl.col(f"norm_{nome}") for nome in nomes
    )
    # Pesos ajustados sobre outra referência de escala: o número continua
    # saindo, mas marcado -- refaça `fit_rating --fit-pesos --gravar`.
    medias_do_ajuste = ajuste["medias_da_referencia"]
    desatualizados = bool(
        medias_do_ajuste and referencia
        and any(abs(float(medias_do_ajuste.get(n, 0)) - float(referencia["medias"].get(n, 0)))
                > 1e-6 * max(1.0, abs(float(referencia["medias"].get(n, 0)))) for n in nomes)
    )
    resultado = normalizados.with_columns(
        agregado.alias("rating"),
        (pl.col("rounds") < MIN_ROUNDS_CONFIAVEL).alias("amostra_fraca"),
    ).sort("rating", descending=True)

    return swing.sort(["round_num", "steamid"]), {
        "jogadores": resultado.to_dicts(),
        "media": float(resultado["rating"].mean() or 0),
        "modelo_de_round": modelo.metricas,
        "taxa_base_por_lado": base_lado,
        "confrontos_estimados": len(celulas),
        "fonte_da_economia": fonte_economia,
        "referencia_ajustada": referencia is not None,
        "normalizado_por_lado": usa_lados,
        "pesos": ajuste["pesos"],
        "intercepto": ajuste["intercepto"],
        "origem_dos_pesos": ajuste["origem"],
        "pesos_desatualizados": desatualizados,
        # Rotulo obrigatorio: em nenhum lugar este numero pode passar por
        # Rating 3.0 oficial da HLTV.
        "rotulo": "implementacao propria da metodologia do Rating 3.0 (HLTV)",
    }
