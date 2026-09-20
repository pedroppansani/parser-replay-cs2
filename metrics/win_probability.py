"""
Probabilidade de vitória da partida, round a round.

Por que este módulo existe
--------------------------
A pergunta "qual foi o round decisivo" era respondida por uma soma de pontos
(ponto sem retorno 40, clutch 20, defuse 8...). Os pesos eram inventados: não
havia resposta para "por que clutch vale 20 e defuse vale 8", e a decisão 6 do
CLAUDE.md chama isso pelo nome -- chute disfarçado de métrica.

Aqui a decisividade sai de UMA conta, sem peso nenhum: o quanto o round moveu a
chance de o time vencer a PARTIDA. Três coisas que antes eram componentes com
peso saem de graça da matemática:

- **ponto sem retorno**: um round que leva de 40% para 8% tem variação enorme
  por construção, ninguém precisa premiá-lo;
- **déficit**: estados desequilibrados movem pouca probabilidade, porque quase
  nada muda o desfecho de um 12-3;
- **placar apertado**: 11-11 é o pico natural da curva, é onde um round vale
  mais. Não é um bônus, é o formato do jogo.

O modelo
--------
Programação dinâmica sobre os estados de placar até o fim da partida. O valor de
um estado é a chance de o time A vencer a partida a partir dali.

A probabilidade de ganhar um round individual é NEUTRA (0,5) de propósito.
Alavancagem é propriedade do ESTADO DO PLACAR, não de qual time é melhor. Usar a
taxa de vitória observada na própria partida seria circular: o time que venceu
teve taxa alta justamente porque venceu, e todo round dele pareceria mais
provável do que era no momento em que foi jogado.

Limitação conhecida: o modelo supõe INDEPENDÊNCIA entre rounds. Momentum e
economia violam isso -- depois de perder um round o time perde também a compra
do seguinte, e a chance real do round seguinte não é mais 0,5. Modelar economia
exigiria um estado (placar, dinheiro, armas) grande demais para o corpus de 9
partidas, então a independência fica registrada como simplificação e não como
descuido.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import polars as pl

# ---------------------------------------------------------------------------
# Constantes de calibração
# ---------------------------------------------------------------------------

# Probabilidade de um time ganhar um round isolado. Neutra por decisão de
# modelagem -- ver o cabeçalho.
P_ROUND_NEUTRA = 0.5

# Ajuste por lado: CT e TR não ganham a mesma fração dos rounds, e com uma
# estimativa confiável dá para usar p != 0,5 conforme o lado que cada time joga.
#
# DESLIGADO (None) de propósito. Ligar isto exige estimar a taxa de vitória por
# lado num corpus grande o bastante para a estimativa não ser ruído: com 9
# partidas, a "taxa de CT" seria a taxa de CT DESTAS partidas, e voltaríamos ao
# problema circular que o modelo neutro evita. Quando houver corpus, o valor é a
# probabilidade de o lado CT ganhar um round (ex.: 0.52).
PROB_ROUND_CT: float | None = None

# Quanto um round precisa mover, em múltiplos do round MAIS BARATO possível,
# para contar como decisivo.
#
# O piso não é um número solto: ele sai do próprio formato. Um round jogado em
# 0-0 move `P(1,0) - P(0,0)` -- 0,081 no MR12 -- e esse é o MENOR salto que
# qualquer round pode dar, o valor de um round genérico antes de o placar
# significar coisa alguma. Round decisivo tem que valer visivelmente mais que
# isso, e 1,5x é o mesmo fator que o projeto já usa para ancorar o piso de entry
# ao acaso (ver CLAUDE.md, pontos de calibração).
#
# Medido nas 9 partidas: com 1,5x, ficam SEM round decisivo exatamente as
# partidas de placar largo (13-5, 13-6, 13-7, 13-8, 4-13) e ficam COM as
# apertadas (dois 13-9 e dois 11-13). É o resultado que se quer -- numa 13-3 a
# diferença se construiu ao longo do jogo, e eleger "o" round inventaria uma
# história que a partida não teve.
FATOR_MINIMO_DECISIVO = 1.5

# Distância abaixo da qual o primeiro e o segundo colocado são considerados
# equivalentes. Existe porque 0,181 contra 0,179 não é uma escolha, é um empate,
# e a interface tem que dizer isso em vez de fingir que a ordenação foi óbvia.
LIMIAR_EMPATE_WPA = 0.02

# Quantos rounds de maior variação a saída sempre expõe.
TOP_ROUNDS = 3


# ---------------------------------------------------------------------------
# Formato da partida
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Formato:
    """Formato detectado da partida.

    `rounds_para_vencer` é o alvo (13 no MR12, 16 no MR15) e `intervalo` é o
    último round da primeira metade (12 ou 15). Os dois andam juntos, mas são
    usados em lugares diferentes: o alvo termina a recursão, o intervalo diz que
    lado cada time joga num round.
    """
    nome: str
    rounds_para_vencer: int
    intervalo: int

    @property
    def max_rounds_regulamentares(self) -> int:
        return 2 * self.intervalo

    def lado_de_a(self, round_num: int) -> str:
        """Lado do time A num round. Convenção do projeto: A começa de TR."""
        return "t" if round_num <= self.intervalo else "ct"


MR12 = Formato("MR12", rounds_para_vencer=13, intervalo=12)
MR15 = Formato("MR15", rounds_para_vencer=16, intervalo=15)


def detecta_formato(rounds: pl.DataFrame, ticks: pl.DataFrame | None = None) -> Formato:
    """Descobre o formato pela própria demo, em vez de assumir MR12.

    O sinal mais direto é a TROCA DE LADO: ela acontece depois do round 12 no
    MR12 e depois do 15 no MR15. É melhor que inferir pelo placar porque não
    depende de a partida ter terminado, e porque MR12 com prorrogação termina em
    16-14 exatamente como um MR15 sem prorrogação -- pelo placar os dois são
    indistinguíveis, pela troca de lado não.
    """
    if ticks is not None and ticks.height:
        troca = _round_da_troca_de_lado(ticks)
        if troca is not None:
            return MR12 if troca - 1 <= MR12.intervalo else MR15

    # Sem ticks, ou sem troca observada numa partida que acabou antes do
    # intervalo: sobra o número de rounds. Mais que 24 rounds não cabe no tempo
    # regulamentar de um MR12.
    if rounds.height > MR12.max_rounds_regulamentares:
        return MR15
    return MR12


def _round_da_troca_de_lado(ticks: pl.DataFrame) -> int | None:
    """Primeiro round em que o time que começou de TR aparece de CT."""
    primeiro = (
        ticks.filter(pl.col("round_num") == 1)
        .sort("tick")
        .group_by("steamid")
        .agg(pl.col("side").first())
    )
    comecaram_t = primeiro.filter(pl.col("side") == "t")["steamid"].to_list()
    if not comecaram_t:
        return None

    # A moda entre os cinco, e não o lado de um jogador só: um steamid pode
    # simplesmente não ter amostra num round.
    por_round = (
        ticks.filter(pl.col("steamid").is_in(comecaram_t))
        .group_by("round_num")
        .agg(pl.col("side").mode().first().alias("lado"))
        .sort("round_num")
    )
    for linha in por_round.iter_rows(named=True):
        if linha["lado"] == "ct":
            return int(linha["round_num"])
    return None


# ---------------------------------------------------------------------------
# O modelo
# ---------------------------------------------------------------------------

# Rounds que a prorrogação acrescenta ao alvo (MR3: seis rounds, vence quem
# fizer quatro). No MR12, o alvo sai de 13 para 16; um novo empate em 15-15 leva
# a outra prorrogação, com alvo 19.
ROUNDS_PARA_VENCER_A_PRORROGACAO = 4
ROUNDS_PARA_EMPATAR_A_PRORROGACAO = 3


# Quantas prorrogações seguidas a conta modela antes de parar em 0,5. A cadeia
# de prorrogações é INFINITA por construção (todo empate abre a próxima), então
# a recursão precisa de um fundo -- sem ele, estoura RecursionError. O fundo é
# 0,5 porque chegar ao começo da 5ª prorrogação exige quatro empates seguidos,
# e nesse estado os dois times estão a no máximo 3 rounds um do outro: o erro
# que isso introduz é multiplicado por uma probabilidade da ordem de 1e-3 de
# sequer chegar lá. Cortar em 0,5 num empate é honesto; era cortar em 1,0 para
# o time errado que não era (ver a regressão abaixo).
MAX_PRORROGACOES_MODELADAS = 5


def _alvo_efetivo(a: int, b: int, alvo: int) -> tuple[int, int]:
    """(rounds que vencem a partida a partir deste placar, prorrogações abertas).

    Fora da prorrogação é o alvo do formato. Dentro dela, cada prorrogação sobe
    o alvo em ROUNDS_PARA_VENCER_A_PRORROGACAO, e uma nova prorrogação começa
    sempre que os dois times chegam a um round do alvo anterior.

    Recebe SEMPRE o alvo do formato, nunca um alvo já ajustado: quem chama
    perde a base se reaproveitar o retorno, e aí não dá mais para saber quantas
    prorrogações já aconteceram.
    """
    prorrogacoes = 0
    limite = alvo - 1  # empatar aqui leva à prorrogação (12-12 no MR12)
    while min(a, b) >= limite:
        alvo = limite + ROUNDS_PARA_VENCER_A_PRORROGACAO
        limite = alvo - 1
        prorrogacoes += 1
    return alvo, prorrogacoes


@lru_cache(maxsize=None)
def _valor(a: int, b: int, alvo: int, intervalo: int, p_ct: float | None) -> float:
    """Chance de o time A vencer a partida a partir do placar (a, b).

    O alvo NÃO é fixo: a partir de (alvo-1, alvo-1) a partida vai para
    prorrogação, e quem vence é quem chega a `alvo - 1 + 4` (16 no MR12). Um
    novo empate em 15-15 leva a outra prorrogação, com alvo 19, e assim por
    diante -- é o que `_alvo_efetivo` calcula.

    REGRESSÃO (2026-09-20, pega pelo invariante do corpus): com o alvo fixo em
    13, a curva de uma partida de prorrogação terminava afirmando 100% para o
    time ERRADO -- 4 partidas do corpus (16, 20, 32 e 42) fecharam 13-16 e
    14-16 com o gráfico dando a vitória a quem perdeu. O comentário antigo
    chamava isso de simplificação aceita ("o empate vale 0,5 e para por ali"),
    mas afirmar certeza sobre o time errado não é simplificar, é errar.
    """
    alvo_agora, prorrogacoes = _alvo_efetivo(a, b, alvo)
    if a >= alvo_agora:
        return 1.0
    if b >= alvo_agora:
        return 0.0
    if prorrogacoes >= MAX_PRORROGACOES_MODELADAS:
        return 0.5

    p = P_ROUND_NEUTRA
    if p_ct is not None:
        # O round que está para ser jogado é o (a + b + 1). O time A o joga de
        # TR na primeira metade e de CT na segunda.
        lado_de_a = "t" if (a + b + 1) <= intervalo else "ct"
        p = p_ct if lado_de_a == "ct" else 1.0 - p_ct

    return (
        p * _valor(a + 1, b, alvo, intervalo, p_ct)
        + (1 - p) * _valor(a, b + 1, alvo, intervalo, p_ct)
    )


def probabilidade_de_vitoria(a: int, b: int, formato: Formato = MR12) -> float:
    """Chance de o time A vencer a partida estando no placar (a, b)."""
    return _valor(a, b, formato.rounds_para_vencer, formato.intervalo, PROB_ROUND_CT)


def wpa_minimo(formato: Formato = MR12) -> float:
    """Variação mínima para um round ser decisivo, derivada do formato.

    A referência é o round de 0-0: o mais barato que existe, porque é o estado em
    que o placar ainda não significa nada. Ver `FATOR_MINIMO_DECISIVO`.
    """
    base = probabilidade_de_vitoria(1, 0, formato) - probabilidade_de_vitoria(0, 0, formato)
    return FATOR_MINIMO_DECISIVO * base


# ---------------------------------------------------------------------------
# A curva da partida
# ---------------------------------------------------------------------------

def curva_da_partida(progressao: list[dict], formato: Formato = MR12) -> pl.DataFrame:
    """Uma linha por round com a probabilidade antes, depois e a variação.

    `progressao` é a saída de `scripts.build_insights.score_progression`: placar
    acumulado por TIME (não por lado) round a round.

    A variação sai com SINAL para os dois times, porque a mesma jogada é ganho
    para um e perda para o outro, e o card precisa dizer de quem.
    """
    linhas = []
    for p in progressao:
        # O placar ANTES do round é o de depois menos o ponto que acabou de sair.
        antes_a = p["score_a"] - (1 if p["winner_team"] == "A" else 0)
        antes_b = p["score_b"] - (1 if p["winner_team"] == "B" else 0)

        wp_antes = probabilidade_de_vitoria(antes_a, antes_b, formato)
        wp_depois = probabilidade_de_vitoria(p["score_a"], p["score_b"], formato)
        delta = wp_depois - wp_antes

        linhas.append(
            {
                "round": int(p["round"]),
                "winner_team": p["winner_team"],
                "score_a": int(p["score_a"]),
                "score_b": int(p["score_b"]),
                "wp_a_antes": wp_antes,
                "wp_a_depois": wp_depois,
                "wpa_a": delta,
                "wpa_b": -delta,
                "wpa_abs": abs(delta),
                # Do ponto de vista de quem GANHOU o round -- sempre positivo, e
                # é este o par de números que a frase do card usa.
                "wp_vencedor_antes": wp_antes if p["winner_team"] == "A" else 1.0 - wp_antes,
                "wp_vencedor_depois": wp_depois if p["winner_team"] == "A" else 1.0 - wp_depois,
                "wp_perdedor_antes": 1.0 - wp_antes if p["winner_team"] == "A" else wp_antes,
                "wp_perdedor_depois": 1.0 - wp_depois if p["winner_team"] == "A" else wp_depois,
            }
        )
    return pl.DataFrame(linhas)


def round_decisivo(curva: pl.DataFrame, formato: Formato = MR12) -> dict:
    """O round que mais moveu a partida -- ou a constatação de que não houve um.

    Devolve sempre os `TOP_ROUNDS` maiores, porque mostrar só o primeiro esconde
    que a escolha saiu de uma ordenação. Quando o primeiro e o segundo estão
    dentro de `LIMIAR_EMPATE_WPA`, `empate_no_topo` fica verdadeiro e a interface
    diz que houve mais de um round de peso equivalente.
    """
    minimo = wpa_minimo(formato)
    vazio = {
        "decisivo": None, "top": [], "empate_no_topo": False,
        "maior_wpa": None, "minimo_exigido": minimo,
    }
    if curva.height == 0:
        return vazio

    # Desempate por round: com |wpa| idêntico, o critério passa a ser a ordem da
    # partida, que é estável entre execuções. `sort` sozinho não garante isso.
    ordenada = curva.sort(["wpa_abs", "round"], descending=[True, False])
    top = ordenada.head(TOP_ROUNDS).to_dicts()
    maior = float(top[0]["wpa_abs"])

    if maior < minimo:
        return {**vazio, "top": top, "maior_wpa": maior}

    empate = len(top) > 1 and (maior - float(top[1]["wpa_abs"])) < LIMIAR_EMPATE_WPA
    return {
        "decisivo": top[0], "top": top, "empate_no_topo": empate,
        "maior_wpa": maior, "minimo_exigido": minimo,
    }


def win_probability(
    progressao: list[dict], formato: Formato = MR12
) -> tuple[pl.DataFrame, dict]:
    """Contrato do projeto: `(per_round, summary)`."""
    curva = curva_da_partida(progressao, formato)
    resumo = round_decisivo(curva, formato)
    resumo["formato"] = formato.nome
    resumo["wp_inicial"] = probabilidade_de_vitoria(0, 0, formato)
    return curva, resumo
