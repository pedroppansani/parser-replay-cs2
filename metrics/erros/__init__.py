"""Onde cada jogador custou rounds ao time nesta partida (fase 12, aba Perfil; definições da fase 18).

JUSTIFICATIVA DE JOGO. A aba Perfil passa a responder "onde ele mais custou
rounds e como melhorar". Cada TIPO de erro é uma função pura e determinística
que recebe a partida processada (`Partida`) e devolve as OCORRÊNCIAS: o round,
o tick, quem estava envolvido, as distâncias, a situação numérica e o ΔWPA (a
queda da chance de vitória do time naquele evento, pela estimativa do modelo).

Princípio do projeto que manda aqui: a tela nunca acusa mais do que o dado
sustenta. Por isso cada ocorrência carrega:
- `filtro`: o motivo de ficar de fora (round de economia, jogador cego, em duelo
  próprio...) ou None quando passa. "Antes dos filtros" e "depois dos filtros"
  saem da mesma tabela;
- `nivel` ("explicito" ou "depende") e o `motivo` escrito, pela ordem de regras
  do pedido (12.2, "Explícito ou depende da tática"; a primeira que se aplica
  decide).

FASE 18 (definições do Pedro, que valem como definição e não sugestão):
- **morte trocada não é erro de ninguém, em nenhum tipo**, qualquer que seja a
  distância: a troca é decidida pelo FATO (o matador morreu por um aliado dentro
  da janela, `_pares_de_trade`), nunca pela distância. Cada morte do corpus grava
  se foi trocada e por quem (`mortes_trocadas`, arquivo `mortes.parquet`);
- **round decidido fica fora** de todos os tipos: a chance de o time vencer o
  round logo antes do evento (o modelo de round do rating) acima de
  `LIMIAR_ROUND_GANHO` ou abaixo de `LIMIAR_ROUND_PERDIDO`;
- quem estava vendo quem vem de `metrics.erros.visao` (linha de visão pelo mapa +
  campo de visão + não estar cego). "Não trocou" e "possível bait" exigem o
  matador visível para o jogador na janela; "perdeu a troca" exige ter ido
  trocar (engajado o matador) e sai quando dois ou mais inimigos estavam
  visíveis ao mesmo tempo ("enfrentou dois ou mais", registrado, nunca erro);
  "morreu isolado" passa a ser "morreu sozinho": nenhum aliado vivo tinha o
  matador à vista nem estava a até `DIST_TROCA`;
- a situação numérica conta os vivos pelas mortes (antes vinha das posições
  gravadas só nos ticks das kills, e um evento antes da primeira morte do round
  saía "0 contra 0").

FONTE ÚNICA DE CADA CONCEITO (nada é redefinido aqui):
- troca e janela de troca: `metrics.basic_metrics._pares_de_trade` com
  `metrics.constantes.JANELA_DE_TRADE_S` (decisões 40 e 41, fase 7);
- classes de economia: `metrics.economia.grupos_de_compra` (regra 8i; eco e
  round de pistola pela agregação da fase 7);
- funções: o resumo por lado de `metrics.structural_roles`, com a marca de
  tendência da decisão 39 (`structural_roles.estabilidade_da_funcao`);
- AWPer do time: `metrics.player_roles.awpers_do_time`;
- ΔWPA: a variação da chance de vencer o ROUND na kill (o modelo de round do
  rating, `rating.variacao_por_kill`, o mesmo do Round Swing) vezes a alavanca
  do round na partida (`win_probability`: chance de vencer a partida se o time
  vence o round menos se perde). Ver a nota de decisão 46;
- chance de vencer o round antes do evento (round decidido): o mesmo modelo e o
  mesmo estado (`rating._estado_completo`).

"Utilidade no bolso" NÃO existe: o inventário só é lido no fim do freeze time
(`parsing.parser.PROPS_DA_COMPRA`), não na hora da morte. O pedido manda não
criar o tipo nem estimar (decisão 46).

Toda distância é no MESMO ANDAR (`metrics.map_areas.floor_split_z`), em
unidades do jogo, no plano (X, Y) como o resto do projeto (raio de apoio do
perfil). Jogadores em andares diferentes nunca estão "perto".
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import polars as pl

from metrics.basic_metrics import _pares_de_trade
from metrics.constantes import JANELA_DE_TRADE_S
from metrics.grenades import EFFECTIVE_BLIND_SECONDS, FIRE_WEAPONS, HE_WEAPONS
from metrics.rating import ARMA_PARA_GRUPO
from metrics.tactics import relogio as relogio_do_jogo

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# --- Constantes (fase 12). Cada uma está no material de calibração, seção 7 ----------------------

# Distância de troca: até aqui um aliado vivo ainda consegue trocar a morte dentro da janela.
# Origem: o raio de apoio que o projeto já usa para "companheiro por perto" (player_profile e
# structural_roles, RAIO_COMPANHEIRO = 600, "o alcance em que uma troca ainda acontece"); conferido
# na distribuição do corpus (MATERIAL_DE_CALIBRACAO.md, seção 7). Fase 18: só entra em "morreu
# sozinho" (um aliado a até isto não deixa a morte ser "sozinho"); nos outros tipos a distância é
# contexto, não critério (a troca é decidida pelo fato).
DIST_TROCA = 600.0

# Duelo próprio: o jogador que levou ou causou dano nestes segundos antes da morte do aliado estava
# na briga dele, não deixou de trocar. Origem: um duelo de rifle (tempo de reação de ~0,25 s mais o
# tempo para matar de 0,3 a 1 s) cabe com folga em 2 s; a faixa de 1 a 4 s está no material.
S_DUELO = 2.0

# Cegueira imposta ao próprio time. Origem: o percentil 90 do corpus (52 partidas, fora eco e
# pós-plant perdido): da soma por jogador-partida (520 valores; mediana 8,7 s, p90 27,1 s) e da
# cegueira nos aliados por flash (2.814 flashes; mediana 1,6 s, p90 4,8 s). Histogramas e varredura
# no material de calibração, seção 7.
SEG_CEGUEIRA_ALIADO = 27.0        # soma no lado, segundos
SEG_CEGUEIRA_ALIADO_UMA = 4.8     # numa flash só, segundos

# Cegueira mínima de UMA flash para ela ser ocorrência de "flash no time": abaixo disto (a cegueira desta flash
# nos aliados, a coluna "cegueira desta flash" do material) a flash não é ocorrência, mesmo com a soma do lado
# acima de SEG_CEGUEIRA_ALIADO. A soma continua contando TODAS as flashes (ela mede o padrão). Em segundos do
# evento do jogo (`blind_duration`, que não passa por conversão de tick). Origem: calibração do Pedro
# (2026-10-16, decisão 46): os 3 exemplos reprovados cegavam ~1 s (0,98, 1,21 e 1,43 s).
MIN_CEGUEIRA_FLASH_ALIADO = 2.0

# Dano de HE ou molotov no próprio time, soma no lado. Origem: o percentil 95 do corpus por
# jogador-partida (520 valores; mediana 0, p75 1, p90 10, p95 19). O p90 não serve: mais da metade
# não feriu ninguém do time, e 10 de dano é um tique de molotov. Material de calibração, seção 7.
DANO_UTILIDADE_ALIADO = 20.0

# --- Constantes novas (fase 18). Cada uma está no material de calibração, seção 7 --------------

# --- Calibração do Pedro (fase 18b, decisão 46) ---------------------------------------------------

# Recuo mínimo do bait: o deslocamento LÍQUIDO do jogador para longe do matador, do primeiro tick (amostra)
# em que ele vê o matador até o fim da janela, com o matador parado onde estava nesse primeiro tick, tem de
# ser de pelo menos isto. Abaixo (o passo de lado do jiggle) não é bait, nem saindo da linha de visão.
# O mesmo valor, ao contrário (o deslocamento líquido NA DIREÇÃO do matador visível), é o "andou na
# direção dele" que conta como engajar em "perdeu a troca" e tira o caso de "não trocou". Origem: decisão
# do Pedro na fase 18b (64 u; substitui o RECUO_MINIMO = 120 da fase 18, que era a mesma medida pelo máximo
# e não pelo líquido).
MIN_RECUO_BAIT = 64.0

# Tempo mínimo de visão: o matador precisa ter ficado visível pelo menos isto, SOMANDO as amostras visíveis
# da janela (não precisa ser contínuo: o jiggle e o peek repetido também dão chance de troca, e a soma é o
# tempo de exposição que o jogador teve). Vale para o matador visível em "não trocou" e no bait, e para o
# aliado que tem o matador à vista e por isso tira um caso de "morreu sozinho"; NÃO vale para os "dois ou
# mais inimigos visíveis" de "perdeu a troca" (ali qualquer amostra visível conta). Origem: decisão do
# Pedro na fase 18b (0,5 s).
MIN_TEMPO_VISIVEL = 0.5

# Round decidido: a chance de vitória do time (o modelo de round do rating), logo antes do evento,
# acima de LIMIAR_ROUND_GANHO ou abaixo de LIMIAR_ROUND_PERDIDO. Origem: os valores propostos pelo
# Pedro na fase 18 (0,95 e 0,05), simétricos: fora fica o que acontece quando a chance já é de 19
# contra 1 (o 4 contra 1 caçando o último, o 1 contra 4 tentando salvar). Histograma no material.
LIMIAR_ROUND_GANHO = 0.95
LIMIAR_ROUND_PERDIDO = 0.05

# "Atirou no matador": um tiro (weapon_fire) com o matador visível e a mira a menos disto da direção
# até ele, no plano. Origem: o percentil 99 do mesmo ângulo nos tiros que ACERTARAM um inimigo no
# corpus (23.502 acertos com o tiro no mesmo tick, 52 partidas: mediana 0,5°, p95 2,8°, p99 5,7°),
# arredondado para cima: um tiro que erra perto do alvo ainda é um tiro nele.
CONE_DO_TIRO_GRAUS = 6.0

# Um tipo com menos ocorrências que isto não vira "ponto a melhorar": vai para "Detalhes" (pedido 12.5).
MIN_OCORRENCIAS_PARA_PONTO = 2
MAX_PONTOS_A_MELHORAR = 3         # pedido 12.5
MAX_PONTOS_FORTES = 2             # pedido 12.5
# Ponto forte: ficar pelo menos esta fração acima da referência da função. É a mesma margem de
# destaque que a aba Perfil já usa (MARGEM_DESTAQUE = 0,15 no template), lida como fração da régua
# porque as métricas têm escalas diferentes (porcentagem, dano, segundos).
MARGEM_PONTO_FORTE = 0.15

# Tipos publicados no site. Começou vazia (pedido 12.4): um tipo só entra depois que o Pedro confirmar pelo
# menos 8 dos 10 exemplos do material de calibração (seção 7). Respostas de 2026-10-16 (decisão 46; gravadas em
# scripts/calibracao/respostas_do_pedro.json): não trocou 8/10, perdeu a troca 9/10, morreu sozinho 8/10, primeira
# morte sem troca 10/10, dano de utilidade no time 10/10. Flash no time: 7/10 em 2026-10-16 e, com os 3 exemplos
# novos da regra MIN_CEGUEIRA_FLASH_ALIADO confirmados em 2026-10-21, 10/10. O bait fica de fora (amostra insuficiente).
TIPOS_DE_ERRO_VALIDADOS: frozenset[str] = frozenset({
    "nao_trocou", "perdeu_a_troca", "morreu_sozinho", "primeira_morte_sem_troca", "flash_no_time",
    "dano_de_utilidade_no_time"})

# Um tipo com menos ocorrências que isto no CORPUS (depois dos filtros) não entra na validação nem pode entrar
# em TIPOS_DE_ERRO_VALIDADOS: com menos de 10 não dá para sortear os 10 exemplos da regra dos 8 de 10. A
# contagem é calculada dos dados (`casos_no_corpus`), nunca uma lista escrita à mão: quando o corpus crescer e o
# tipo passar do mínimo, ele volta à validação sem mudar código. O tipo continua calculado e gravado. Origem:
# decisão do Pedro na fase 18b (o bait ficou com 9 casos).
MIN_CASOS_PARA_VALIDAR = 10


def casos_no_corpus(processed_root: Path | None = None) -> dict[str, int]:
    """{tipo: ocorrências que passaram nos filtros} somadas nas partidas processadas (erros_do_jogador.parquet)."""
    raiz = processed_root or PROJECT_ROOT / "data" / "processed"
    tot = {t: 0 for t in TIPOS}
    for arq in sorted(raiz.glob("match_*/erros_do_jogador.parquet")):
        oc = pl.read_parquet(arq, columns=["tipo", "filtro"]).filter(pl.col("filtro").is_null())
        for t, n in oc.group_by("tipo", maintain_order=True).len().iter_rows():
            if t in tot:
                tot[t] += int(n)
    return tot


def tipos_validaveis(casos: dict[str, int] | None = None) -> tuple[str, ...]:
    """Os tipos com pelo menos MIN_CASOS_PARA_VALIDAR casos no corpus, na ordem de TIPOS."""
    casos = casos_no_corpus() if casos is None else casos
    return tuple(t for t in TIPOS if casos.get(t, 0) >= MIN_CASOS_PARA_VALIDAR)

# --- Os tipos ---------------------------------------------------------------------------------

NAO_TROCOU = "nao_trocou"
POSSIVEL_BAIT = "possivel_bait"
PERDEU_A_TROCA = "perdeu_a_troca"
MORREU_SOZINHO = "morreu_sozinho"            # fase 18: era "morreu_isolado"
PRIMEIRA_MORTE_SEM_TROCA = "primeira_morte_sem_troca"
FLASH_NO_TIME = "flash_no_time"
DANO_DE_UTILIDADE_NO_TIME = "dano_de_utilidade_no_time"

# Ordem fixa: é a ordem das tabelas, do material e o desempate da tela.
TIPOS = (NAO_TROCOU, POSSIVEL_BAIT, PERDEU_A_TROCA, MORREU_SOZINHO, PRIMEIRA_MORTE_SEM_TROCA,
         FLASH_NO_TIME, DANO_DE_UTILIDADE_NO_TIME)

TITULOS = {
    NAO_TROCOU: "Não trocou o aliado",
    POSSIVEL_BAIT: "Possível bait",              # sempre com "possível": o dado mostra posição e tempo
    PERDEU_A_TROCA: "Perdeu a troca",
    MORREU_SOZINHO: "Morreu sozinho",
    PRIMEIRA_MORTE_SEM_TROCA: "Primeira morte sem troca",
    FLASH_NO_TIME: "Flash no time",
    DANO_DE_UTILIDADE_NO_TIME: "Dano de utilidade no time",
}

# "Como melhorar": uma frase por tipo, fixa (decisão 18; propostas do pedido 12.3, a aprovar pelo
# Pedro no material de calibração; a de "morreu sozinho" é a da fase 18).
COMO_MELHORAR = {
    NAO_TROCOU: ("Jogue a uma distância de troca do parceiro e mirando o mesmo ponto que ele. Se ele cair, o "
                 "matador está exposto por alguns segundos: é a sua janela."),
    POSSIVEL_BAIT: ("Se você é o segundo a entrar, entre logo atrás e ao lado, não atrás de parede. Combinem "
                    "antes quem entra e quem troca."),
    PERDEU_A_TROCA: ("Na troca, não pique o mesmo ângulo que acabou de matar o aliado. Mude o ângulo ou jogue "
                     "uma flash no matador antes."),
    MORREU_SOZINHO: ("Se não é o lurker, jogue onde um aliado consiga te trocar e avise a posição. Morrer sem "
                     "troca dá vantagem numérica de graça."),
    PRIMEIRA_MORTE_SEM_TROCA: ("Sem ser o entry, evite o primeiro contato sozinho. Espere a informação ou alguém "
                               "para trocar."),
    FLASH_NO_TIME: "Avise antes de soltar e prefira a pop flash por cima do ângulo do aliado, não na frente dele.",
    DANO_DE_UTILIDADE_NO_TIME: "Confira onde o time está antes de soltar HE ou molotov num ponto de passagem.",
}
# Quando o nível é "depende da tática", a frase de como melhorar é trocada pelo motivo seguido disto.
CONFERIR_COM_O_TIME = "Vale conferir com o time se era o plano."

# Motivos (pedido 12.2, regras 2 a 7), na forma em que a tela escreve.
MOTIVO_LURKER = "jogar longe do time é a função do lurker"
MOTIVO_ENTRY = "abrir o round é a função do entry; o que pesa é se o time trocou"
# "Ângulo de abertura" = a morte que abre o round (a primeira kill de inimigo do round; `_Indice.abertura`).
MOTIVO_AWPER = "segurar sozinho um ângulo de abertura é o trabalho do AWPer"
MOTIVO_TENDENCIA = "a função não é firme nesta partida"
MOTIVO_GERAL = "o dado mostra posição e tempo, não o que o time pediu"
MOTIVO_EXPLICITO = {
    NAO_TROCOU: "o aliado morreu, o matador ficou visível para ele e saiu vivo da janela de troca",
    POSSIVEL_BAIT: ("o matador ficou visível para ele, ele não atirou nem causou dano e recuou ou saiu da linha "
                    "de visão; o dado mostra posição e tempo, não intenção"),
    PERDEU_A_TROCA: "foi para a troca (engajou o matador) e morreu sem matá-lo, com no máximo um inimigo à vista",
    FLASH_NO_TIME: "a flash dele cegou o próprio time",
    DANO_DE_UTILIDADE_NO_TIME: "a granada dele feriu o próprio time",
}
TIPOS_EXPLICITOS = tuple(MOTIVO_EXPLICITO)       # regra 6

EXPLICITO = "explicito"
DEPENDE = "depende"
ROTULO_DO_NIVEL = {EXPLICITO: "explícito", DEPENDE: "depende da tática"}

# Filtros (motivo de ficar de fora), na ordem em que são conferidos.
FILTRO_ECONOMIA = "round de economia do time"
FILTRO_GUARDANDO_ARMA = "time guardando arma (pós-plant perdido)"
FILTRO_FIM_DO_ROUND = "depois do fim do round"
FILTRO_ROUND_DECIDIDO = "round decidido"                          # fase 18
FILTRO_MORTE_TROCADA = "morte trocada"                            # fase 18
FILTRO_CEGO = "cego no momento"
FILTRO_DUELO = "em duelo próprio"
FILTRO_SEM_ARMA = "sem arma de fogo"
FILTRO_MATADOR_FORA_DA_VISAO = "o matador não ficou visível para ele"          # fase 18
FILTRO_POUCO_TEMPO_VISIVEL = "o matador ficou visível menos de 0,5 s"       # fase 18b
FILTRO_ENGAJOU = "engajou o matador"                              # fase 18b: conta só em "perdeu a troca"
FILTRO_NAO_RECUOU = "recuou menos de 64 unidades"                 # fase 18b (bait)
FILTRO_SEM_ENGAJAMENTO = "não engajou o matador"                  # fase 18 (perdeu a troca)
FILTRO_DOIS_OU_MAIS = "enfrentou dois ou mais ao mesmo tempo"     # fase 18: registrado, nunca erro
FILTRO_ALIADO_COM_O_MATADOR = "um aliado tinha o matador à vista ou estava perto"   # fase 18 (morreu sozinho)
FILTRO_1_CONTRA_N = "sem aliado vivo (1 contra N)"
FILTRO_EVENTO_ZERADO = "evento sem dano ou sem cegueira"          # fase 18: evento com 0 não é ocorrência
FILTRO_ABAIXO_DO_LIMIAR = "abaixo do limiar da partida"
FILTRO_CEGUEIRA_CURTA = "a flash cegou o time menos de 2,0 s"   # calibração do Pedro (MIN_CEGUEIRA_FLASH_ALIADO)

FIREARMS = frozenset(ARMA_PARA_GRUPO)            # nomes de exibição das armas de fogo (rating)


@dataclass
class Partida:
    """O que os tipos de erro leem de uma partida processada. Montada por `carrega_partida` (do
    interim e do processado) ou à mão nos testes, com situações sintéticas."""
    match_id: str
    tickrate: int
    rounds: pl.DataFrame          # round_num, freeze_end, end, winner, bomb_plant
    kills: pl.DataFrame           # round_num, tick, attacker/victim steamid e side, X/Y/Z, weapon
    damages: pl.DataFrame         # round_num, tick, attacker/victim steamid, weapon, dmg_health_real
    blinds: pl.DataFrame | None   # player_blind: round_num, tick, attacker/user steamid, blind_duration
    posicoes: pl.DataFrame        # round_num, tick, steamid, side, X, Y, Z, is_alive (ticks dos eventos)
    primeira_arma: dict           # (round, steamid) -> primeiro tick com arma de fogo na mão no round
    team_of: dict                 # steamid -> "A"/"B"
    nomes: dict                   # steamid -> nome
    corte_de_andar: float | None = None     # Z que separa os andares (None: um andar só)
    rounds_de_economia: set | None = None   # {(round, time)} eco ou pistola; None = sem dado de compra
    funcoes: dict = field(default_factory=dict)   # (steamid, side) -> {"funcao", "tendencia"}
    awpers: set = field(default_factory=set)
    variacao: dict = field(default_factory=dict)  # (round, tick, vítima) -> {"delta", "vivos_antes"}
    alavanca: dict = field(default_factory=dict)  # (round, time) -> WP(vence) - WP(perde)
    rounds_jogados: dict = field(default_factory=dict)   # steamid -> rounds jogados
    lados: dict = field(default_factory=dict)     # (round, steamid) -> "ct"/"t", de todos os ticks (completa quem não aparece nas kills)
    degradado: list = field(default_factory=list)
    # fase 18
    visao: object | None = None   # metrics.erros.visao.Visao: quem vê quem em cada tick (None: tipos de visão não calculados)
    tiros: pl.DataFrame | None = None   # shots: round_num, tick, player_steamid, player_yaw
    chance: Callable | None = None      # (round, time, tick, vivos do time, vivos do adversário) -> P(vencer o round)


# --- Ajudantes (a mesma leitura para todos os tipos) ------------------------------------------

def _andar(z: float | None, corte: float | None) -> int:
    if corte is None or z is None:
        return 0
    return 0 if z >= corte else 1


def distancia(a: dict, b: dict, corte: float | None) -> float:
    """Distância no plano entre dois pontos {X, Y, Z}; infinita quando estão em andares diferentes."""
    if _andar(a.get("Z"), corte) != _andar(b.get("Z"), corte):
        return math.inf
    return math.hypot(float(a["X"]) - float(b["X"]), float(a["Y"]) - float(b["Y"]))


def _ponto(e) -> dict:
    """{X, Y, Z} de um estado da visão (x, y, z, yaw, agachado)."""
    return {"X": e[0], "Y": e[1], "Z": e[2]}


class _Indice:
    """Índices da partida para as perguntas que todo tipo faz (quem está vivo, onde, cego, em duelo)."""

    def __init__(self, p: Partida):
        import bisect
        self._bisect = bisect
        self.p = p
        self.janela = int(JANELA_DE_TRADE_S * p.tickrate)
        k = p.kills.sort(["round_num", "tick"], maintain_order=True)
        self.kills = k.to_dicts()
        # primeira morte de cada (round, jogador)
        self.morte: dict = {}
        for r in self.kills:
            if r["victim_steamid"] is not None:
                self.morte.setdefault((int(r["round_num"]), int(r["victim_steamid"])), int(r["tick"]))
        # mortes trocadas: (round, tick da morte, vítima) -> (quem trocou, tick da troca) -- a definição da fase 7
        pares = _pares_de_trade(p.kills, JANELA_DE_TRADE_S, p.tickrate) if p.kills.height else None
        self.troca: dict = {}
        if pares is not None:
            for r in (pares.sort(["round_num", "tick_prev", "tick"], maintain_order=True)
                      .select("round_num", "tick_prev", "victim_steamid_prev", "attacker_steamid", "tick").iter_rows()):
                self.troca.setdefault((int(r[0]), int(r[1]), int(r[2])), (int(r[3]), int(r[4])))
        self.trocadas = set(self.troca)
        # posições por (round, tick)
        self.pos: dict = {}
        for r in p.posicoes.sort(["round_num", "tick", "steamid"]).iter_rows(named=True):
            self.pos.setdefault((int(r["round_num"]), int(r["tick"])), []).append(r)
        self.ticks_do_round: dict = {}
        for (rn, t) in sorted(self.pos):
            self.ticks_do_round.setdefault(rn, []).append(t)
        self.dano = p.damages.sort(["round_num", "tick"], maintain_order=True).to_dicts()
        self.cegueira: dict = {}
        if p.blinds is not None and p.blinds.height:
            for r in p.blinds.sort(["round_num", "tick"], maintain_order=True).iter_rows(named=True):
                if r["user_steamid"] is None or (r["blind_duration"] or 0) < EFFECTIVE_BLIND_SECONDS:
                    continue
                self.cegueira.setdefault((int(r["round_num"]), int(r["user_steamid"])), []).append(
                    (int(r["tick"]), int(r["tick"]) + float(r["blind_duration"]) * p.tickrate))
        self.rounds = {int(r["round_num"]): r for r in p.rounds.iter_rows(named=True)}
        # primeira morte de inimigo de cada round (a abertura, como em impacto._aberturas_por_round)
        self.abertura: dict = {}
        for r in self.kills:
            if self.eh_kill_inimiga(r):
                self.abertura.setdefault(int(r["round_num"]), (int(r["tick"]), int(r["victim_steamid"])))
        # quem jogou cada round (para contar os vivos): os lados de todos os ticks; sem eles, o time inteiro
        self.do_round: dict = {}
        for (rn, sid) in sorted(p.lados):
            self.do_round.setdefault(int(rn), []).append(int(sid))
        # tiros por jogador e round, em ordem de tick
        self.tiros: dict = {}
        if p.tiros is not None and p.tiros.height:
            for r in p.tiros.sort(["round_num", "tick"], maintain_order=True).select(
                    "round_num", "tick", "player_steamid", "player_yaw").iter_rows():
                if r[2] is not None:
                    self.tiros.setdefault((int(r[0]), int(r[2])), []).append((int(r[1]), r[3]))

    def time(self, sid) -> str | None:
        return self.p.team_of.get(int(sid)) if sid is not None else None

    def eh_kill_inimiga(self, k: dict) -> bool:
        a, v = k.get("attacker_steamid"), k.get("victim_steamid")
        return a is not None and v is not None and self.time(a) is not None and self.time(a) != self.time(v)

    def jogadores_em(self, rn: int, t: int) -> list[dict]:
        """As linhas de posição do tick mais próximo ANTES ou NO instante t (o tick exato, se houver)."""
        ticks = self.ticks_do_round.get(rn) or []
        i = self._bisect.bisect_right(ticks, t) - 1
        if i < 0:
            return []
        return self.pos.get((rn, ticks[i]), [])

    def vivo(self, rn: int, sid: int, t: int) -> bool:
        m = self.morte.get((rn, int(sid)))
        return m is None or m > t

    def aliados_vivos(self, rn: int, sid: int, t: int) -> list[dict]:
        """Companheiros de `sid` vivos no instante t (sem ele), com a posição."""
        meu = self.time(sid)
        return [r for r in self.jogadores_em(rn, t)
                if int(r["steamid"]) != int(sid) and self.time(r["steamid"]) == meu
                and r.get("is_alive", True) and self.vivo(rn, int(r["steamid"]), t)]

    def cego(self, rn: int, sid: int, t: int) -> bool:
        return any(a <= t <= b for a, b in self.cegueira.get((rn, int(sid)), []))

    def em_duelo(self, rn: int, sid: int, t: int, s_duelo: float) -> bool:
        ini = t - s_duelo * self.p.tickrate
        for d in self.dano:
            if int(d["round_num"]) != rn or d["tick"] > t:
                continue
            if d["tick"] < ini:
                continue
            a, v = d["attacker_steamid"], d["victim_steamid"]
            if a is None or v is None or self.time(a) == self.time(v):
                continue
            if int(a) == int(sid) or int(v) == int(sid):
                return True
        return False

    def tem_arma(self, rn: int, sid: int, t: int) -> bool:
        primeira = self.p.primeira_arma.get((rn, int(sid)))
        return primeira is not None and primeira <= t

    def segundos(self, rn: int, t: int) -> float:
        fe = (self.rounds.get(rn) or {}).get("freeze_end")
        return round((t - int(fe)) / self.p.tickrate, 2) if fe is not None else None

    def filtro_do_round(self, rn: int, sid: int, t: int) -> str | None:
        """Regra 1 do pedido (e o fim do round): eco/pistola do time, time guardando arma, ou depois do fim;
        fase 18: e o round decidido (a chance de vitória do time logo antes do evento fora da faixa)."""
        meu = self.time(sid)
        eco = self.p.rounds_de_economia
        if eco is not None and (rn, meu) in eco:
            return FILTRO_ECONOMIA
        r = self.rounds.get(rn) or {}
        lado = self.lado(rn, sid)
        if (r.get("bomb_plant") is not None and t >= int(r["bomb_plant"]) and r.get("winner") is not None
                and lado is not None and r["winner"] != lado):
            return FILTRO_GUARDANDO_ARMA
        if r.get("end") is not None and t > int(r["end"]):
            return FILTRO_FIM_DO_ROUND
        c = self.chance(rn, sid, t)
        if c is not None and (c > LIMIAR_ROUND_GANHO or c < LIMIAR_ROUND_PERDIDO):
            return FILTRO_ROUND_DECIDIDO
        return None

    def lado(self, rn: int, sid: int) -> str | None:
        for r in self.jogadores_em(rn, 10 ** 12):
            if int(r["steamid"]) == int(sid):
                return r["side"]
        for k in self.kills:
            if int(k["round_num"]) != rn:
                continue
            if k["victim_steamid"] is not None and int(k["victim_steamid"]) == int(sid):
                return k["victim_side"]
            if k["attacker_steamid"] is not None and int(k["attacker_steamid"]) == int(sid):
                return k["attacker_side"]
        # round sem kill (ou sem o jogador nelas): o lado vem da tabela de ticks inteira (fase 15: todo erro tem lado)
        return self.p.lados.get((int(rn), int(sid)))

    def relogio(self, rn: int, t: int) -> str | None:
        """O relógio do jogo no tick t ("1:14": desce de 1:55 e, depois do plant, os 40 s da bomba): o mesmo
        que o replay mostra no instante do chip (`metrics.tactics.relogio`, espelho de `MapCore.relogio`)."""
        r = self.rounds.get(rn) or {}
        fe = r.get("freeze_end")
        if fe is None:
            return None

        def seg(tick):
            return None if tick is None else (int(tick) - int(fe)) / self.p.tickrate
        return relogio_do_jogo(seg(t), seg(r.get("bomb_plant")), seg(r.get("end")))

    def vivos_dos_times(self, rn: int, sid: int, t: int) -> tuple[int, int]:
        """(vivos do time de sid, vivos do adversário) logo ANTES do evento do tick t, contados pelas mortes:
        quem jogou o round (os lados dos ticks; sem eles, o time inteiro) e ainda não tinha morrido.

        Fase 18: antes vinham das posições gravadas, que só existem nos ticks das kills; um evento antes da
        primeira morte do round (a flash dos 0:08) não achava posição nenhuma e saía "0 contra 0"."""
        meu = self.time(sid)
        quem = self.do_round.get(int(rn)) or sorted(self.p.team_of)
        meus = sum(1 for s in quem if self.time(s) == meu and self.vivo(rn, s, t - 1))
        deles = sum(1 for s in quem if self.time(s) not in (None, meu) and self.vivo(rn, s, t - 1))
        return meus, deles

    def chance(self, rn: int, sid: int, t: int) -> float | None:
        """P(o time de `sid` vencer o round) logo antes do evento do tick t, pelo modelo de round do rating."""
        if self.p.chance is None:
            return None
        meus, deles = self.vivos_dos_times(rn, sid, t)
        return self.p.chance(int(rn), self.time(sid), int(t), meus, deles)

    def dwpa(self, rn: int, t: int, vitima: int, time: str | None) -> float | None:
        """Queda da chance de o `time` vencer a PARTIDA na kill de `vitima` (negativa = queda)."""
        v = self.p.variacao.get((rn, int(t), int(vitima)))
        alav = self.p.alavanca.get((rn, time))
        if v is None or alav is None:
            return None
        delta = v["delta"] if self.time(vitima) == time else -v["delta"]
        return delta * alav

    # --- fase 18: troca pelo fato e visão --------------------------------------------------------

    def trocada(self, rn: int, t: int, vitima: int, pos_vitima: dict | None = None) -> tuple:
        """(foi trocada, quem trocou, distância de quem trocou até a vítima na hora da morte)."""
        tr = self.troca.get((int(rn), int(t), int(vitima)))
        if tr is None:
            return False, None, None
        quem = tr[0]
        d = None
        if pos_vitima is not None and self.p.visao is not None:
            e = self.p.visao.estado(rn, quem, t)
            if e is not None:
                d = distancia(_ponto(e), pos_vitima, self.p.corte_de_andar)
        return True, quem, d

    def fim_da_janela(self, rn: int, t: int, *quem) -> int:
        """Último tick da janela de troca que começa em t: o fim da janela, o tick antes da morte de cada um de
        `quem` (morto não vê nem é visto) e o fim do round."""
        fim = t + self.janela
        for s in quem:
            m = self.morte.get((rn, int(s)))
            if m is not None and m > t:
                fim = min(fim, m - 1)
        end = (self.rounds.get(rn) or {}).get("end")
        if end is not None:
            fim = min(fim, int(end))
        return fim

    def visao_do_matador(self, rn: int, t: int, fim: int, obs: int, matador: int) -> list[tuple[int, bool]]:
        """[(tick, o matador estava visível para `obs`)] nas amostras de t a fim."""
        v = self.p.visao
        if v is None or fim < t:
            return []
        return [(s, v.visivel(rn, s, obs, matador)) for s in v.amostras(t, fim)]

    def ticks_visivel(self, amostras: list[tuple[int, bool]]) -> int:
        """Ticks em que o matador ficou visível, SOMADOS na janela: cada amostra visível vale até a próxima
        amostra (a última, 1 tick)."""
        tot = 0
        for i, (s, vis) in enumerate(amostras):
            if vis:
                prox = amostras[i + 1][0] if i + 1 < len(amostras) else s + 1
                tot += prox - s
        return tot

    def segundos_visivel(self, amostras: list[tuple[int, bool]]) -> float:
        """Tempo (s) em que o matador ficou visível na janela (a soma de `ticks_visivel`)."""
        return round(self.ticks_visivel(amostras) / self.p.tickrate, 2)

    def visto_o_bastante(self, amostras: list[tuple[int, bool]]) -> bool:
        """O matador ficou visível pelo menos MIN_TEMPO_VISIVEL (somado) na janela (fase 18b)."""
        return visto_o_bastante(self.ticks_visivel(amostras) / self.p.tickrate)

    def deu_dano(self, rn: int, de: int, em: int, t0: int, t1: int) -> float:
        return float(sum(float(d["dmg_health_real"] or 0) for d in self.dano
                         if int(d["round_num"]) == rn and t0 <= d["tick"] <= t1 and d["attacker_steamid"] is not None
                         and int(d["attacker_steamid"]) == de and d["victim_steamid"] is not None
                         and int(d["victim_steamid"]) == em))

    def atirou_nele(self, rn: int, de: int, em: int, t0: int, t1: int) -> bool:
        """Um tiro de `de` entre t0 e t1 com `em` visível e a mira a menos de CONE_DO_TIRO_GRAUS dele."""
        from metrics.erros.visao import angulo_horizontal
        v = self.p.visao
        if v is None:
            return False
        for tk, yaw in self.tiros.get((int(rn), int(de)), []):
            if tk < t0 or tk > t1 or yaw is None:
                continue
            eo, ea = v.estado(rn, de, tk), v.estado(rn, em, tk)
            if eo is None or ea is None:
                continue
            if angulo_horizontal(float(yaw), eo, ea) < CONE_DO_TIRO_GRAUS and v.visivel(rn, tk, de, em):
                return True
        return False

    def movimento(self, rn: int, obs: int, matador: int, amostras: list[tuple[int, bool]]) -> tuple:
        """Com o matador PARADO onde estava na primeira amostra em que ficou visível: (o deslocamento LÍQUIDO do
        jogador para longe dele, da primeira amostra visível até a última amostra da janela, negativo quando
        se aproximou; se saiu da linha de visão andando, que fica só como contexto desde a fase 18b).

        "Saiu da linha de visão andando": numa amostra posterior o matador deixou de estar visível E, da
        posição nova do jogador, a linha até a última posição em que o matador foi visto também está fechada
        (foi o jogador que se mexeu, não o matador)."""
        v = self.p.visao
        vis = [s for s, ok in amostras if ok]
        if v is None or not vis:
            return 0.0, False
        s0 = vis[0]
        e_m0, e_j0 = v.estado(rn, matador, s0), v.estado(rn, obs, s0)
        if e_m0 is None or e_j0 is None:
            return 0.0, False
        d0 = math.hypot(e_j0[0] - e_m0[0], e_j0[1] - e_m0[1])
        longe = perto = 0.0
        saiu = False
        ultimo_visto = s0
        d = d0
        for s, ok in amostras:
            if s <= s0:
                continue
            e_j = v.estado(rn, obs, s)
            if e_j is None:
                continue
            d = math.hypot(e_j[0] - e_m0[0], e_j[1] - e_m0[1])
            if ok:
                ultimo_visto = s
            elif not saiu:
                e_mv = v.estado(rn, matador, ultimo_visto)
                if e_mv is not None and not v.linha_de_visao(rn, s, obs, matador, pos_obs=e_j, pos_alvo=e_mv):
                    saiu = True
        # fase 18b: o deslocamento LÍQUIDO (positivo = para longe), da primeira amostra visível até a última
        return round(d - d0, 1), saiu

    def inimigos_visiveis(self, rn: int, obs: int, t0: int, t1: int) -> int:
        """O maior número de inimigos vivos visíveis para `obs` AO MESMO TEMPO numa amostra de t0 a t1."""
        v = self.p.visao
        if v is None or t1 < t0:
            return 0
        meu = self.time(obs)
        inimigos = [s for s in (self.do_round.get(int(rn)) or sorted(self.p.team_of))
                    if self.time(s) not in (None, meu)]
        maior = 0
        for s in v.amostras(t0, t1):
            n = sum(1 for x in inimigos if self.vivo(rn, x, s) and v.visivel(rn, s, obs, x))
            maior = max(maior, n)
        return maior


def visto_o_bastante(segundos: float) -> bool:
    """Fase 18b: o tempo somado de visão chega a MIN_TEMPO_VISIVEL (0,49 s não chega; 0,50 s chega)."""
    return segundos + 1e-9 >= MIN_TEMPO_VISIVEL


def recuou_o_bastante(recuo: float | None) -> bool:
    """Fase 18b: o deslocamento líquido para longe do matador chega a MIN_RECUO_BAIT (63 u não; 64 u sim)."""
    return recuo is not None and recuo + 1e-9 >= MIN_RECUO_BAIT


def _base(ix: _Indice, tipo: str, rn: int, t: int, sid: int) -> dict:
    nome = ix.p.nomes.get(int(sid), str(sid))
    meus, deles = ix.vivos_dos_times(rn, sid, t)
    c = ix.chance(rn, sid, t)
    return {"tipo": tipo, "match_id": ix.p.match_id, "round_num": rn, "tick": int(t), "segundos": ix.segundos(rn, t),
            "relogio": ix.relogio(rn, t), "steamid": int(sid), "name": nome, "side": ix.lado(rn, sid), "aliado_steamid": None, "aliado": None,
            "matador_steamid": None, "matador": None, "dist_aliado": None, "dist_matador_jogador": None,
            "dist_matador_aliado": None, "vivos_time": meus, "vivos_adversario": deles, "dwpa": None,
            "valor": None, "filtro": None,
            # fase 18: as colunas para julgar o lance
            "chance_vitoria": None if c is None else round(float(c), 4), "matador_visivel": None,
            "seg_matador_visivel": None, "atirou_no_matador": None, "dano_no_matador": None, "recuo": None,
            "saiu_da_linha": None, "inimigos_visiveis": None, "trocada": None, "trocada_por_steamid": None,
            "trocada_por": None, "dist_de_quem_trocou": None, "valor_soma_lado": None}


def _r(x: float | None) -> float | None:
    return None if x is None or math.isinf(x) else round(float(x), 1)


def _pos(k: dict, quem: str) -> dict:
    return {"X": k[f"{quem}_X"], "Y": k[f"{quem}_Y"], "Z": k[f"{quem}_Z"]}


# --- Tipos 1 e 2: não trocou o aliado e possível bait ----------------------------------------

def _mortes_de_aliado(ix: _Indice):
    """Cada morte por inimigo, com o matador: (kill, round, tick, vítima, matador)."""
    for k in ix.kills:
        if ix.eh_kill_inimiga(k):
            yield k, int(k["round_num"]), int(k["tick"]), int(k["victim_steamid"]), int(k["attacker_steamid"])


def _candidatos_nao_trocou(p: Partida, s_duelo: float, ix: _Indice) -> list[dict]:
    """Toda morte de aliado NÃO trocada, para cada companheiro vivo: a ocorrência com as colunas de visão, o
    engajamento e o recuo já medidos e o filtro dos que não contam (fase 18). Base de "não trocou" e de
    "possível bait"."""
    out = []
    for k, rn, t, v, a in _mortes_de_aliado(ix):
        if (rn, t, v) in ix.trocadas:
            continue                          # morte trocada não é erro de ninguém (e não é candidata)
        pos_v, pos_a = _pos(k, "victim"), _pos(k, "attacker")
        for r in ix.aliados_vivos(rn, v, t):
            sid = int(r["steamid"])
            fim = ix.fim_da_janela(rn, t, sid, a)
            amostras = ix.visao_do_matador(rn, t, fim, sid, a)
            algum = any(ok for _, ok in amostras)
            visto = ix.visto_o_bastante(amostras)
            # o tiro e o dano contam até a morte dele, se ele morreu na janela (o mesmo recorte de "perdeu a troca")
            morte_j = ix.morte.get((rn, sid))
            ate = morte_j if morte_j is not None and t < morte_j <= t + ix.janela else fim
            atirou = ix.atirou_nele(rn, sid, a, t, ate)
            dano = ix.deu_dano(rn, sid, a, t, ate)
            liquido, saiu = ix.movimento(rn, sid, a, amostras)
            # engajar = a mesma regra de "perdeu a troca": atirou nele, deu dano, ou andou na direção dele visível
            engajou = atirou or dano > 0 or (algum and recuou_o_bastante(-liquido))
            oc = _base(ix, NAO_TROCOU, rn, t, sid)
            oc.update(aliado_steamid=v, aliado=p.nomes.get(v, str(v)), matador_steamid=a,
                      matador=p.nomes.get(a, str(a)), dist_aliado=_r(distancia(r, pos_v, p.corte_de_andar)),
                      dist_matador_jogador=_r(distancia(r, pos_a, p.corte_de_andar)),
                      dist_matador_aliado=_r(distancia(pos_v, pos_a, p.corte_de_andar)),
                      dwpa=ix.dwpa(rn, t, v, ix.time(sid)), matador_visivel=visto,
                      seg_matador_visivel=ix.segundos_visivel(amostras), atirou_no_matador=atirou,
                      dano_no_matador=round(dano, 1), recuo=liquido, saiu_da_linha=saiu, trocada=False)
            oc["filtro"] = (ix.filtro_do_round(rn, sid, t)
                            or (FILTRO_CEGO if ix.cego(rn, sid, t) else None)
                            or (FILTRO_DUELO if ix.em_duelo(rn, sid, t, s_duelo) else None)
                            or (None if ix.tem_arma(rn, sid, t) else FILTRO_SEM_ARMA)
                            or (None if algum else FILTRO_MATADOR_FORA_DA_VISAO)
                            or (None if visto else FILTRO_POUCO_TEMPO_VISIVEL)
                            or (FILTRO_ENGAJOU if engajou else None))
            out.append(oc)
    return out


def nao_trocou(p: Partida, dist_troca: float = DIST_TROCA, s_duelo: float = S_DUELO,
               _ix: _Indice | None = None, _cand: list | None = None) -> list[dict]:
    """Um aliado morre, a morte NÃO é trocada (o matador não morre por um aliado dentro da janela: o fato, não a
    distância), e o matador ficou VISÍVEL para o jogador na janela (fase 18), por pelo menos MIN_TEMPO_VISIVEL
    somados (fase 18b), e o jogador NÃO engajou o matador (fase 18b: quem atirou nele, deu dano ou andou na
    direção dele visível conta só em "perdeu a troca", se morreu). Fica de fora: o
    matador nunca visível para ele (abriu pela lateral, matou e recuou), o jogador cego no momento, em duelo
    próprio (levou ou causou dano nos `s_duelo` segundos antes), sem arma de fogo, e os filtros do round
    (eco, time guardando arma, depois do fim, round decidido). `dist_troca` não é mais critério (fica no
    argumento para a varredura do material, que mostra que ele não muda nada)."""
    ix = _ix or _Indice(p)
    return [dict(oc) for oc in (_cand if _cand is not None else _candidatos_nao_trocou(p, s_duelo, ix))]


def possivel_bait(p: Partida, dist_troca: float = DIST_TROCA, s_duelo: float = S_DUELO,
                  recuo_minimo: float | None = None, _ix: _Indice | None = None,
                  _cand: list | None = None) -> list[dict]:
    """Subconjunto de "não trocou" (que já exige o matador visível por MIN_TEMPO_VISIVEL e o jogador sem
    engajar): o jogador RECUOU, isto é, o deslocamento líquido dele para longe do matador (parado onde estava na
    primeira amostra visível), da primeira amostra visível até o fim da janela, é de pelo menos MIN_RECUO_BAIT
    (fase 18b). Sair da linha de visão com menos que isso (o passo de lado do jiggle) não é bait.
    O critério antigo de "estar atrás do aliado" saiu (o empate de distância nunca conta como atrás). Os
    filtros de "não trocou" valem aqui; os que não engajaram mas não recuaram ficam com o motivo."""
    ix = _ix or _Indice(p)
    out = []
    for oc in (_cand if _cand is not None else _candidatos_nao_trocou(p, s_duelo, ix)):
        b = {**oc, "tipo": POSSIVEL_BAIT}
        minimo = MIN_RECUO_BAIT if recuo_minimo is None else recuo_minimo
        if b["filtro"] is None and not ((b["recuo"] or 0) + 1e-9 >= minimo):
            b["filtro"] = FILTRO_NAO_RECUOU
        out.append(b)
    return out


# --- Tipo 3: perdeu a troca --------------------------------------------------------------------

def perdeu_a_troca(p: Partida, recuo_minimo: float | None = None, _ix: _Indice | None = None) -> list[dict]:
    """Um aliado morre; o jogador ENGAJA o matador dentro da janela (atira nele, causa dano, ou anda mais que
    `recuo_minimo` na direção dele com ele visível) e morre dentro da janela sem matá-lo, com no máximo UM
    inimigo visível para ele ao mesmo tempo (fase 18). Dois ou mais visíveis: "enfrentou dois ou mais ao mesmo
    tempo" (registrado com esse filtro, nunca erro). Sem engajamento não é tentativa de troca (morrer para o
    mesmo inimigo num duelo separado é morrer sozinho). A morte do jogador trocada: fora."""
    ix = _ix or _Indice(p)
    out = []
    for k, rn, t, v, a in _mortes_de_aliado(ix):
        fim = t + ix.janela
        for r in ix.aliados_vivos(rn, v, t):
            sid = int(r["steamid"])
            morte = ix.morte.get((rn, sid))
            if morte is None or not (t < morte <= fim):
                continue
            matou = any(int(x["round_num"]) == rn and t < x["tick"] <= fim and x["attacker_steamid"] is not None
                        and int(x["attacker_steamid"]) == sid and int(x["victim_steamid"]) == a for x in ix.kills)
            if matou:
                continue
            fim_j = ix.fim_da_janela(rn, t, sid, a)
            amostras = ix.visao_do_matador(rn, t, fim_j, sid, a)
            visto = any(ok for _, ok in amostras)
            dano = ix.deu_dano(rn, sid, a, t, morte)
            atirou = ix.atirou_nele(rn, sid, a, t, morte)
            liquido, saiu = ix.movimento(rn, sid, a, amostras)
            minimo = MIN_RECUO_BAIT if recuo_minimo is None else recuo_minimo
            andou = visto and -liquido + 1e-9 >= minimo
            n_vis = ix.inimigos_visiveis(rn, sid, t, fim_j)
            pos_v, pos_a = _pos(k, "victim"), _pos(k, "attacker")
            k_morte = next((x for x in ix.kills if int(x["round_num"]) == rn and int(x["tick"]) == morte
                            and x["victim_steamid"] is not None and int(x["victim_steamid"]) == sid), None)
            pos_j = _pos(k_morte, "victim") if k_morte is not None else r
            foi, quem, d_quem = ix.trocada(rn, morte, sid, pos_j)
            oc = _base(ix, PERDEU_A_TROCA, rn, morte, sid)
            oc.update(aliado_steamid=v, aliado=p.nomes.get(v, str(v)), matador_steamid=a,
                      matador=p.nomes.get(a, str(a)), dist_aliado=_r(distancia(r, pos_v, p.corte_de_andar)),
                      dist_matador_jogador=_r(distancia(r, pos_a, p.corte_de_andar)),
                      dist_matador_aliado=_r(distancia(pos_v, pos_a, p.corte_de_andar)),
                      dwpa=ix.dwpa(rn, morte, sid, ix.time(sid)), matador_visivel=visto,
                      seg_matador_visivel=ix.segundos_visivel(amostras), atirou_no_matador=atirou,
                      dano_no_matador=round(dano, 1), recuo=liquido, saiu_da_linha=saiu, inimigos_visiveis=n_vis,
                      trocada=foi, trocada_por_steamid=quem, trocada_por=None if quem is None else p.nomes.get(quem, str(quem)),
                      dist_de_quem_trocou=_r(d_quem))
            engajou = atirou or dano > 0 or andou
            oc["filtro"] = (ix.filtro_do_round(rn, sid, morte)
                            or (FILTRO_MORTE_TROCADA if foi else None)
                            or (None if engajou else FILTRO_SEM_ENGAJAMENTO)
                            or (FILTRO_DOIS_OU_MAIS if n_vis >= 2 else None))
            out.append(oc)
    return out


# --- Tipos 4 e 5: morreu sozinho e primeira morte sem troca ---------------------------------------

def morreu_sozinho(p: Partida, dist_troca: float = DIST_TROCA, _ix: _Indice | None = None) -> list[dict]:
    """A morte do jogador NÃO é trocada (pelo fato, qualquer distância) e nenhum aliado vivo tinha o matador
    visível na janela nem estava a até `dist_troca` dele (fase 18; era "morreu isolado", só pela distância).
    Fica de fora a situação de 1 contra N (sem aliado vivo para ajudar) e o round decidido."""
    ix = _ix or _Indice(p)
    out = []
    for k, rn, t, v, a in _mortes_de_aliado(ix):
        if (rn, t, v) in ix.trocadas:
            continue
        pos_v = _pos(k, "victim")
        vivos = ix.aliados_vivos(rn, v, t)
        dists = [distancia(r, pos_v, p.corte_de_andar) for r in vivos]
        mais_perto = min(dists) if dists else None
        perto = mais_perto is not None and mais_perto <= dist_troca
        viu = False
        for r in vivos:
            fim = ix.fim_da_janela(rn, t, int(r["steamid"]), a)
            if ix.visto_o_bastante(ix.visao_do_matador(rn, t, fim, int(r["steamid"]), a)):     # fase 18b: 0,5 s
                viu = True
                break
        oc = _base(ix, MORREU_SOZINHO, rn, t, v)
        oc.update(matador_steamid=a, matador=p.nomes.get(a, str(a)), dist_aliado=_r(mais_perto),
                  dist_matador_jogador=_r(distancia(pos_v, _pos(k, "attacker"), p.corte_de_andar)),
                  dwpa=ix.dwpa(rn, t, v, ix.time(v)), matador_visivel=viu, trocada=False)
        oc["filtro"] = (ix.filtro_do_round(rn, v, t) or (FILTRO_1_CONTRA_N if not vivos else None)
                        or (FILTRO_ALIADO_COM_O_MATADOR if (perto or viu) else None))
        out.append(oc)
    return out


def primeira_morte_sem_troca(p: Partida, _ix: _Indice | None = None) -> list[dict]:
    """O jogador sofre a primeira morte do round (a primeira kill de inimigo, a mesma abertura de
    metrics/impacto) e ela não é trocada (pelo fato: o matador não morreu por um aliado na janela)."""
    ix = _ix or _Indice(p)
    out = []
    for k, rn, t, v, a in _mortes_de_aliado(ix):
        if ix.abertura.get(rn) != (t, v) or (rn, t, v) in ix.trocadas:
            continue
        oc = _base(ix, PRIMEIRA_MORTE_SEM_TROCA, rn, t, v)
        oc.update(matador_steamid=a, matador=p.nomes.get(a, str(a)),
                  dist_matador_jogador=_r(distancia(_pos(k, "victim"), _pos(k, "attacker"), p.corte_de_andar)),
                  dwpa=ix.dwpa(rn, t, v, ix.time(v)), trocada=False)
        vivos = ix.aliados_vivos(rn, v, t)
        if vivos:
            pos_v = _pos(k, "victim")
            oc["dist_aliado"] = _r(min(distancia(r, pos_v, p.corte_de_andar) for r in vivos))
        oc["filtro"] = ix.filtro_do_round(rn, v, t)
        out.append(oc)
    return out


# --- Tipos 6 e 7: flash no time e dano de utilidade no time --------------------------------------

def flash_no_time(p: Partida, seg_aliado: float = SEG_CEGUEIRA_ALIADO, seg_uma: float = SEG_CEGUEIRA_ALIADO_UMA,
                  _ix: _Indice | None = None, min_cegueira: float | None = None) -> list[dict]:
    """A cegueira imposta a aliados passa de `seg_aliado` no lado (soma) ou de `seg_uma` numa flash só.
    Uma ocorrência por flash que cegou companheiro (a mesma detonação: mesmo arremessador e mesmo tick);
    `valor` é a soma dos segundos de cegueira nos aliados daquela flash e `valor_soma_lado` a soma do
    jogador naquele lado. Com a soma abaixo do limiar, só a flash acima de `seg_uma` conta; as outras ficam
    de fora com o motivo. Uma flash com 0 s de cegueira não é ocorrência (fase 18). Calibração do Pedro: a flash
    que cegou o time menos de MIN_CEGUEIRA_FLASH_ALIADO também não é (`FILTRO_CEGUEIRA_CURTA`), mesmo com a soma
    acima do limiar; ela continua na soma do lado, que é aplicada ANTES desse corte."""
    ix = _ix or _Indice(p)
    if p.blinds is None or p.blinds.height == 0:
        return []
    flashes: dict = {}
    for r in p.blinds.sort(["round_num", "tick"], maintain_order=True).iter_rows(named=True):
        a, u = r["attacker_steamid"], r["user_steamid"]
        if a is None or u is None or int(a) == int(u) or ix.time(a) is None or ix.time(a) != ix.time(u):
            continue
        chave = (int(r["round_num"]), int(r["tick"]), int(a))
        flashes.setdefault(chave, []).append((int(u), float(r["blind_duration"] or 0.0)))
    out = []
    for (rn, t, a), cegos in sorted(flashes.items()):
        oc = _base(ix, FLASH_NO_TIME, rn, t, a)
        maior = max(cegos, key=lambda c: (c[1], -c[0]))
        oc.update(aliado_steamid=maior[0], aliado=p.nomes.get(maior[0], str(maior[0])),
                  valor=round(sum(d for _, d in cegos), 2))
        oc["filtro"] = ix.filtro_do_round(rn, a, t) or (FILTRO_EVENTO_ZERADO if not oc["valor"] > 0 else None)
        out.append(oc)
    _aplica_limiar(out, seg_aliado, seg_uma)
    for oc in out:                     # depois da soma: a flash curta conta no padrão, mas não é ocorrência
        if oc["filtro"] is None and not cegou_o_bastante(oc["valor"], min_cegueira):
            oc["filtro"] = FILTRO_CEGUEIRA_CURTA
    return out


def cegou_o_bastante(segundos: float | None, minimo: float | None = None) -> bool:
    """A flash cegou o time pelo menos MIN_CEGUEIRA_FLASH_ALIADO (1,99 s não chega; 2,00 s chega). `minimo` troca o
    valor (a varredura do material de calibração)."""
    minimo = MIN_CEGUEIRA_FLASH_ALIADO if minimo is None else minimo
    return segundos is not None and segundos + 1e-9 >= minimo


def _aplica_limiar(out: list[dict], limiar_partida: float, limiar_um: float | None) -> None:
    """Soma por (jogador, LADO) nas ocorrências que passaram nos filtros; abaixo do limiar, só o evento
    acima do limiar de um evento (se houver) continua. Fase 15 (decisão 46): todo erro é de um lado só,
    então a soma e o limiar valem para cada lado (antes a soma era da partida, juntando CT e TR).
    Fase 18: a soma vai para `valor_soma_lado` em cada evento (o material mostra o evento e a soma)."""
    soma: dict = {}
    for oc in out:
        if oc["filtro"] is None:
            chave = (oc["steamid"], oc["side"])
            soma[chave] = soma.get(chave, 0.0) + oc["valor"]
    for oc in out:
        oc["valor_soma_lado"] = round(soma.get((oc["steamid"], oc["side"]), 0.0), 2)
        if oc["filtro"] is not None or soma.get((oc["steamid"], oc["side"]), 0.0) > limiar_partida:
            continue
        if limiar_um is not None and oc["valor"] > limiar_um:
            continue
        oc["filtro"] = FILTRO_ABAIXO_DO_LIMIAR


def dano_de_utilidade_no_time(p: Partida, dano_aliado: float = DANO_UTILIDADE_ALIADO,
                              _ix: _Indice | None = None) -> list[dict]:
    """O dano de HE ou molotov em aliados passa de `dano_aliado` no lado. Uma ocorrência por (round,
    granada): HE pelo tick da explosão, o fogo da molotov junto no round; `valor` é o dano no próprio time e
    `valor_soma_lado` a soma do jogador naquele lado. O ΔWPA existe quando a granada matou o aliado (a kill
    tem variação no modelo); sem morte, é nulo.

    Fase 18: um evento com 0 de dano não é ocorrência (`FILTRO_EVENTO_ZERADO`). O 0 vem do próprio jogo: o
    `player_hurt` de granada em companheiro chega com `dmg_health` 0 e `dmg_armor` 0 (o aliado na borda da
    explosão); antes, esse evento entrava se a SOMA do jogador no lado passasse do limiar."""
    ix = _ix or _Indice(p)
    grupos: dict = {}
    for d in ix.dano:
        a, v = d["attacker_steamid"], d["victim_steamid"]
        if a is None or v is None or int(a) == int(v) or ix.time(a) is None or ix.time(a) != ix.time(v):
            continue
        arma = d["weapon"]
        if arma in HE_WEAPONS:
            chave = (int(d["round_num"]), int(a), "he", int(d["tick"]))
        elif arma in FIRE_WEAPONS:
            chave = (int(d["round_num"]), int(a), "fogo", None)
        else:
            continue
        g = grupos.setdefault(chave, {"tick": int(d["tick"]), "dano": 0.0, "vitimas": {}})
        g["dano"] += float(d["dmg_health_real"] or 0)
        g["vitimas"][int(v)] = g["vitimas"].get(int(v), 0.0) + float(d["dmg_health_real"] or 0)
    out = []
    for chave in sorted(grupos, key=lambda c: (c[0], grupos[c]["tick"], c[1], c[2])):
        rn, a, tipo_gr, _ = chave
        g = grupos[chave]
        oc = _base(ix, DANO_DE_UTILIDADE_NO_TIME, rn, g["tick"], a)
        alvo = max(g["vitimas"].items(), key=lambda kv: (kv[1], -kv[0]))[0]
        oc.update(aliado_steamid=alvo, aliado=p.nomes.get(alvo, str(alvo)), valor=round(g["dano"], 1))
        # a granada matou o aliado? a queda da chance é a daquela kill
        for k in ix.kills:
            if (int(k["round_num"]) == rn and k["attacker_steamid"] is not None and int(k["attacker_steamid"]) == a
                    and k["victim_steamid"] is not None and int(k["victim_steamid"]) in g["vitimas"]
                    and (k["weapon"] in HE_WEAPONS or k["weapon"] in FIRE_WEAPONS)):
                oc["dwpa"] = ix.dwpa(rn, int(k["tick"]), int(k["victim_steamid"]), ix.time(a))
                break
        oc["filtro"] = ix.filtro_do_round(rn, a, g["tick"]) or (FILTRO_EVENTO_ZERADO if not oc["valor"] > 0 else None)
        out.append(oc)
    _aplica_limiar(out, dano_aliado, None)
    return out


# --- Nível e motivo (pedido 12.2, "Explícito ou depende da tática") --------------------------------

def nivel_e_motivo(oc: dict, p: Partida, abertura: tuple | None = None) -> tuple[str | None, str | None]:
    """(nível, motivo) de uma ocorrência, pela ordem de regras do pedido; a primeira que se aplica decide.
    Ocorrência com filtro (regra 1 e os filtros do tipo) fica de fora: (None, None). Fase 18: "não trocou" e
    "possível bait" só existem com o matador visível (é condição de entrada), então saem sempre explícitos."""
    if oc.get("filtro") is not None:
        return None, None                                                     # regra 1 e filtros do tipo
    tipo = oc["tipo"]
    f = p.funcoes.get((oc["steamid"], oc["side"])) or {}
    funcao, tendencia = f.get("funcao"), bool(f.get("tendencia"))

    def com_tendencia(motivo: str) -> str:                                   # regra 5
        return f"{motivo}; {MOTIVO_TENDENCIA}" if tendencia else motivo

    if tipo == MORREU_SOZINHO and funcao == "lurker":
        return DEPENDE, com_tendencia(MOTIVO_LURKER)                         # regra 2
    if tipo == PRIMEIRA_MORTE_SEM_TROCA and funcao == "entry":
        return DEPENDE, com_tendencia(MOTIVO_ENTRY)                          # regra 3
    if tipo in (MORREU_SOZINHO, PRIMEIRA_MORTE_SEM_TROCA):
        eh_awper = funcao == "awper" or oc["steamid"] in p.awpers
        abriu = tipo == PRIMEIRA_MORTE_SEM_TROCA or abertura == (oc["tick"], oc["steamid"])
        if eh_awper and abriu:
            return DEPENDE, com_tendencia(MOTIVO_AWPER) if funcao == "awper" else MOTIVO_AWPER   # regra 4
    if tipo in TIPOS_EXPLICITOS:
        return EXPLICITO, MOTIVO_EXPLICITO[tipo]                              # regra 6
    return DEPENDE, MOTIVO_GERAL                                              # regra 7


def ocorrencias(p: Partida, **constantes) -> pl.DataFrame:
    """Todas as ocorrências de todos os tipos, com filtro, nível e motivo. Ordem determinística:
    tipo (na ordem de TIPOS), round, tick, jogador.

    `constantes` troca DIST_TROCA, S_DUELO, MIN_RECUO_BAIT, MIN_CEGUEIRA_FLASH_ALIADO e os limiares (o material de calibração varre as
    faixas). LIMIAR_ROUND_GANHO e LIMIAR_ROUND_PERDIDO são lidos do módulo (a varredura os troca nele)."""
    ix = _Indice(p)
    dist = constantes.get("dist_troca", DIST_TROCA)
    s_duelo = constantes.get("s_duelo", S_DUELO)
    recuo = constantes.get("recuo_minimo", MIN_RECUO_BAIT)
    cand = _candidatos_nao_trocou(p, s_duelo, ix)
    linhas = (nao_trocou(p, dist, s_duelo, _ix=ix, _cand=cand)
              + possivel_bait(p, dist, s_duelo, recuo, _ix=ix, _cand=cand)
              + perdeu_a_troca(p, recuo, _ix=ix) + morreu_sozinho(p, dist, _ix=ix) + primeira_morte_sem_troca(p, _ix=ix)
              + flash_no_time(p, constantes.get("seg_aliado", SEG_CEGUEIRA_ALIADO),
                              constantes.get("seg_uma", SEG_CEGUEIRA_ALIADO_UMA), _ix=ix,
                              min_cegueira=constantes.get("min_cegueira"))
              + dano_de_utilidade_no_time(p, constantes.get("dano_aliado", DANO_UTILIDADE_ALIADO), _ix=ix))
    for oc in linhas:
        oc["nivel"], oc["motivo"] = nivel_e_motivo(oc, p, ix.abertura.get(oc["round_num"]))
    ordem = {t: i for i, t in enumerate(TIPOS)}
    linhas.sort(key=lambda o: (ordem[o["tipo"]], o["round_num"], o["tick"], o["steamid"],
                               o["aliado_steamid"] or 0))
    return pl.DataFrame(linhas, schema=ESQUEMA, orient="row") if linhas else pl.DataFrame(schema=ESQUEMA)


ESQUEMA = {
    "tipo": pl.String, "match_id": pl.String, "round_num": pl.Int64, "tick": pl.Int64, "segundos": pl.Float64,
    "relogio": pl.String,
    "steamid": pl.UInt64, "name": pl.String, "side": pl.String, "aliado_steamid": pl.UInt64, "aliado": pl.String,
    "matador_steamid": pl.UInt64, "matador": pl.String, "dist_aliado": pl.Float64,
    "dist_matador_jogador": pl.Float64, "dist_matador_aliado": pl.Float64, "vivos_time": pl.Int64,
    "vivos_adversario": pl.Int64, "dwpa": pl.Float64, "valor": pl.Float64, "filtro": pl.String,
    # fase 18
    "chance_vitoria": pl.Float64, "matador_visivel": pl.Boolean, "seg_matador_visivel": pl.Float64,
    "atirou_no_matador": pl.Boolean, "dano_no_matador": pl.Float64, "recuo": pl.Float64,
    "saiu_da_linha": pl.Boolean, "inimigos_visiveis": pl.Int64, "trocada": pl.Boolean,
    "trocada_por_steamid": pl.UInt64, "trocada_por": pl.String, "dist_de_quem_trocou": pl.Float64,
    "valor_soma_lado": pl.Float64,
    "nivel": pl.String, "motivo": pl.String,
}


def por_jogador(tabela: pl.DataFrame) -> dict[int, list[dict]]:
    """{steamid: [ocorrências que passaram nos filtros]}, na ordem da tabela."""
    out: dict[int, list[dict]] = {}
    for oc in tabela.filter(pl.col("filtro").is_null()).iter_rows(named=True):
        out.setdefault(int(oc["steamid"]), []).append(oc)
    return out


# --- Toda morte do corpus: trocada ou não, e por quem (fase 18) ------------------------------------

ARQUIVO_MORTES = "mortes.parquet"
ESQUEMA_MORTES = {"match_id": pl.String, "round_num": pl.Int64, "tick": pl.Int64, "victim_steamid": pl.UInt64,
                  "vitima": pl.String, "attacker_steamid": pl.UInt64, "matador": pl.String, "trocada": pl.Boolean,
                  "trocada_por_steamid": pl.UInt64, "trocada_por": pl.String, "tick_da_troca": pl.Int64,
                  "dist_de_quem_trocou": pl.Float64}


def mortes_trocadas(p: Partida) -> pl.DataFrame:
    """Uma linha por morte por inimigo: se foi trocada (o matador morreu por um aliado da vítima dentro da
    janela de troca, a definição da fase 7) e por quem, com a distância de quem trocou até a vítima na hora
    da morte (no mesmo andar; vazia em andares diferentes ou sem posição)."""
    ix = _Indice(p)
    linhas = []
    for k, rn, t, v, a in _mortes_de_aliado(ix):
        foi, quem, d = ix.trocada(rn, t, v, _pos(k, "victim"))
        tr = ix.troca.get((rn, t, v))
        linhas.append({"match_id": p.match_id, "round_num": rn, "tick": t, "victim_steamid": v,
                       "vitima": p.nomes.get(v, str(v)), "attacker_steamid": a, "matador": p.nomes.get(a, str(a)),
                       "trocada": foi, "trocada_por_steamid": quem,
                       "trocada_por": None if quem is None else p.nomes.get(quem, str(quem)),
                       "tick_da_troca": None if tr is None else tr[1], "dist_de_quem_trocou": _r(d)})
    return pl.DataFrame(linhas, schema=ESQUEMA_MORTES, orient="row") if linhas else pl.DataFrame(schema=ESQUEMA_MORTES)


# --- Montagem a partir do processado e do interim ------------------------------------------------

def _primeira_arma(ticks: pl.DataFrame, rounds: pl.DataFrame) -> dict:
    janela = rounds.select("round_num", "freeze_end")
    com_arma = (ticks.select("round_num", "tick", "steamid", "active_weapon_name")
                .filter(pl.col("active_weapon_name").is_in(sorted(FIREARMS)))
                .join(janela, on="round_num", how="inner")
                .filter(pl.col("tick") >= pl.col("freeze_end"))
                .group_by(["round_num", "steamid"], maintain_order=True).agg(pl.col("tick").min()))
    return {(int(r[0]), int(r[1])): int(r[2]) for r in com_arma.iter_rows()}


def _funcao_de_chance(kills, rounds, grupos, modelo, team_of, tickrate) -> Callable:
    """P(time vencer o round) num tick, com os vivos dados: o mesmo modelo de round do rating e o mesmo
    estado completo (`rating._estado_completo`: vivos, equipamento, bomba, lado e tempo)."""
    import numpy as np

    from metrics.rating import _equip_do_time, _equip_por_round, _estado_completo, _inicio_dos_rounds, _tempos
    equip = _equip_por_round(grupos, team_of)
    plant = {int(r["round_num"]): r["bomb_plant"] for r in rounds.select(["round_num", "bomb_plant"]).iter_rows(named=True)}
    inicio = _inicio_dos_rounds(rounds)

    def chance(rn: int, time: str | None, tick: int, vivos_meu: int, vivos_dele: int) -> float | None:
        if time is None:
            return None
        outro = "B" if time == "A" else "A"
        eq_meu, lado = _equip_do_time(equip, rn, time)
        eq_dele, _ = _equip_do_time(equip, rn, outro)
        t_plant = plant.get(rn)
        antes = int(tick) - 1
        bomba = t_plant is not None and antes >= int(t_plant)
        x = _estado_completo(vivos_meu, vivos_dele, eq_meu - eq_dele, bomba, lado == "ct",
                             *_tempos(antes, inicio.get(rn), t_plant, tickrate))
        return float(modelo.prob(np.array([x]))[0])
    return chance


def carrega_partida(match_id: str, processed_root: Path | None = None, interim_root: Path | None = None) -> Partida:
    """A partida processada como os tipos de erro a leem (interim + processado + modelos do projeto)."""
    from leitura.insights import resolve_teams, score_progression
    from metrics.economia import grupos_de_compra
    from metrics.map_areas import floor_split_z
    from metrics.player_roles import awpers_do_time
    from metrics.rating import ModeloDeRound, carrega_referencia, grupo_do_round, variacao_por_kill
    from metrics.structural_roles import estabilidade_da_funcao
    from metrics.timing import detect_tickrate
    from metrics.erros.visao import visao_da_partida
    from metrics.win_probability import detecta_formato, probabilidade_de_vitoria
    from parsing.parser import load_interim

    processed = (processed_root or PROJECT_ROOT / "data" / "processed") / match_id
    interim_root = interim_root or PROJECT_ROOT / "data" / "interim"
    tabelas = load_interim(interim_root, match_id)
    rounds = pl.read_parquet(processed / "rounds.parquet")
    ticks = tabelas["ticks"]
    tickrate = int(detect_tickrate(rounds, ticks)["tickrate"])
    team_of, _ = resolve_teams(ticks)
    nomes = {int(s): n for s, n in ticks.select("steamid", "name").unique(subset=["steamid"], maintain_order=True,
                                                                           keep="first").iter_rows()}
    kills, damages = tabelas["kills"], tabelas["damages"]
    instantes = kills.select("round_num", "tick").unique(maintain_order=True)
    lados = {(int(r), int(s)): lado for r, s, lado in ticks.select("round_num", "steamid", "side")
             .unique(maintain_order=True).iter_rows() if lado is not None}
    posicoes = (ticks.select("round_num", "tick", "steamid", "side", "X", "Y", "Z", "is_alive")
                .join(instantes, on=["round_num", "tick"], how="inner"))
    # um tick antes de cada kill também: a situação numérica é contada antes do evento
    antes = instantes.with_columns((pl.col("tick") - 1).alias("tick"))
    posicoes = pl.concat([posicoes, ticks.select("round_num", "tick", "steamid", "side", "X", "Y", "Z", "is_alive")
                          .join(antes, on=["round_num", "tick"], how="inner")]).unique(maintain_order=True)
    meta = {}
    meta_path = processed / "match_meta.json"
    if meta_path.exists():
        import json
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    degradado = []
    eco = None
    if tabelas.get("compra") is not None and tabelas["compra"].height:
        g = grupos_de_compra(tabelas["compra"], team_of)
        eco = {(int(r["round_num"]), r["time"]) for r in g.filter(
            pl.col("grupo_compra").is_in(["eco", "pistola"]) & (pl.col("peso") > 0)).iter_rows(named=True)}
    else:
        degradado.append("sem a compra do round: o filtro de economia não pôde ser aplicado")
    # funções por lado, com a tendência da decisão 39
    funcoes = {}
    awpers: set = set()
    traits = processed / "player_traits.parquet"
    if traits.exists():
        awpers = awpers_do_time(pl.read_parquet(traits))
    if (processed / "structural_roles.parquet").exists():
        por_round = pl.read_parquet(processed / "structural_roles.parquet")
        resumo = pl.read_parquet(processed / "structural_roles_summary.parquet")
        estab = {(int(r["steamid"]), r["side"]): r for r in estabilidade_da_funcao(por_round, awpers).iter_rows(named=True)}
        for r in resumo.iter_rows(named=True):
            chave = (int(r["steamid"]), r["side"])
            funcoes[chave] = {"funcao": r["funcao"],
                              "tendencia": bool(r["funcao"] is not None and (estab.get(chave) or {}).get("tendencia"))}
    # ΔWPA: o modelo de round global (o do rating) e a alavanca do round na partida
    referencia = carrega_referencia()
    modelo = ModeloDeRound.da_referencia((referencia or {}).get("modelo_de_round"))
    variacao = {}
    grupos = grupo_do_round(ticks, rounds)
    for linha in variacao_por_kill(kills, rounds, grupos, modelo, team_of, tickrate):
        variacao[(linha["round_num"], linha["tick"], int(linha["victim_steamid"]))] = {
            "delta": linha["delta_vitima"], "vivos_antes": linha["vivos_antes"]}
    formato = detecta_formato(rounds, ticks)
    alavanca = {}
    for pr in score_progression(rounds):
        a0 = pr["score_a"] - (1 if pr["winner_team"] == "A" else 0)
        b0 = pr["score_b"] - (1 if pr["winner_team"] == "B" else 0)
        vence_a = probabilidade_de_vitoria(a0 + 1, b0, formato) - probabilidade_de_vitoria(a0, b0 + 1, formato)
        alavanca[(int(pr["round"]), "A")] = vence_a
        alavanca[(int(pr["round"]), "B")] = vence_a    # simétrico: o que A ganha vencendo, B ganha vencendo
    rounds_jogados = {}
    perfil = processed / "player_profile.parquet"
    if perfil.exists():
        rounds_jogados = {int(s): int(n) for s, n in pl.read_parquet(perfil).select("steamid", "rounds_jogados").iter_rows()}
    return Partida(
        match_id=match_id, tickrate=tickrate,
        rounds=rounds.select("round_num", "freeze_end", "end", "winner", "bomb_plant"),
        kills=kills, damages=damages, blinds=tabelas.get("player_blind"), posicoes=posicoes,
        primeira_arma=_primeira_arma(ticks, rounds), team_of={int(k): v for k, v in team_of.items()}, nomes=nomes,
        corte_de_andar=floor_split_z(meta.get("map_name") or ""), rounds_de_economia=eco, funcoes=funcoes,
        awpers={int(s) for s in awpers}, variacao=variacao, alavanca=alavanca, rounds_jogados=rounds_jogados,
        lados=lados, degradado=degradado,
        # fase 18: quem vê quem (linha de visão pelo mapa + campo de visão), os tiros e a chance do round
        visao=visao_da_partida(ticks, meta.get("map_name") or "", tabelas.get("smokes"), tabelas.get("player_blind"),
                               tickrate),
        tiros=tabelas.get("shots"),
        chance=_funcao_de_chance(kills, rounds, grupos, modelo, {int(k): v for k, v in team_of.items()}, tickrate))


ARQUIVO = "erros_do_jogador.parquet"
REFERENCIA_FILE = Path(__file__).resolve().parent.parent / "erros_reference.json"

# --- Pontos fortes: métricas que já existem no perfil, em que MAIS é melhor --------------------------
# (chave do perfil, formato, o que o denominador conta). Ficam de fora as que não têm direção de jogo
# (joga longe do time, pega a AWP: dependem da função) e as que contam contra (cegueira nos
# companheiros). O rótulo vem da fonte de cada uma (player_profile.ROTULOS_DAS_TAXAS e impacto.ROTULOS).
METRICAS_DE_PONTO_FORTE = (
    ("pct_rounds_sobreviveu", "pct", "rounds"),
    ("pct_rounds_trade_kill", "pct", "rounds"),
    ("taxa_conversao_clutch", "pct", "vezes por último"),
    ("dano_por_he", "num1", "HEs"),
    ("dano_por_molotov", "num1", "molotovs"),
    ("inimigos_cegos_por_flash", "num2", "flashes"),
    ("segundos_de_cegueira_por_flash", "num1", "flashes"),
    ("kills_de_flash_por_flash", "num2", "flashes"),
    ("pct_pos_plant_vencidos", "pct", "rounds vivo no plant (TR)"),
    ("kills_por_pos_plant", "num2", "rounds vivo no plant (TR)"),
    ("pct_retakes_vencidos", "pct", "rounds vivo no plant (CT)"),
    ("kills_por_retake", "num2", "rounds vivo no plant (CT)"),
    ("pct_aberturas_vencidas_tr", "pct", "duelos de abertura (TR)"),
    ("pct_aberturas_vencidas_ct", "pct", "duelos de abertura (CT)"),
    ("adr_cheia", "num1", "rounds em compra cheia"),
    ("kast_cheia", "pct", "rounds em compra cheia"),
    ("kills_contra_compra_cheia", "num2", "rounds contra compra cheia"),
)

# Régua por (lado, função): a célula é o conjunto de jogador-lados do corpus com a mesma função no
# mesmo lado (um jogador-lado = um jogador numa partida, num dos lados). Com menos jogador-lados que
# isto, a referência passa a ser o lado inteiro (todas as funções daquele lado); os lados nunca se
# misturam (pedido 12b). Origem: o piso de função da fase 12 (MIN_JOGADOR_PARTIDAS_POR_FUNCAO = 20),
# que vinha do mesmo raciocínio do MIN_JOGADOR_PARTIDAS do perfil (50): 20 é o mínimo para um
# percentil de contagem não ser um jogador só. Com os 1.040 jogador-lados do corpus de 52 partidas,
# só a célula Suporte do TR (17) cai no lado inteiro.
MIN_REF_LADO_FUNCAO = 20
# Percentil da referência acima do qual a contagem do jogador vira "ponto a melhorar". Fase 16a: 90 (decisão
# do Pedro; era 75 na 12b). Origem: com 7 tipos em 2 lados são 14 células por jogador, e no p75 cada uma tem 25%
# de chance de passar só por acaso (77% dos jogadores com algum ponto); no p90 são 47%. O material de calibração
# (seção 7.1b) mostra o efeito de 50, 75 e 90. Percentil por interpolação linear, como numpy.percentile.
PERCENTIL_PONTO_A_MELHORAR = 90
TODAS = "__todas__"
LADOS = ("ct", "t")
ROTULO_DO_LADO = {"ct": "CT", "t": "TR"}


def percentil_do_histograma(hist: dict, q: float) -> float | None:
    """Percentil `q` (0 a 100, interpolação linear) de {contagem: quantos jogador-lados}. A régua guarda o
    histograma das contagens (anônimo) e não só um percentil, para o material de calibração e a página
    usarem qualquer percentil."""
    valores: list[int] = []
    for k in sorted(hist, key=lambda x: int(x)):
        valores += [int(k)] * int(hist[k])
    if not valores:
        return None
    pos = (len(valores) - 1) * q / 100.0
    i = int(math.floor(pos))
    j = min(i + 1, len(valores) - 1)
    return valores[i] + (valores[j] - valores[i]) * (pos - i)



def acima_do_normal(contagem: int, celula: dict | None, percentil: float | None = None) -> bool:
    """O par (tipo, lado) vira "ponto a melhorar" quando a contagem do jogador fica ACIMA do percentil da
    referência (`PERCENTIL_PONTO_A_MELHORAR`) e tem pelo menos `MIN_OCORRENCIAS_PARA_PONTO` ocorrências. Igual ou
    abaixo do percentil, é "dentro do normal". Sem referência, só vale o mínimo de ocorrências."""
    if contagem < MIN_OCORRENCIAS_PARA_PONTO:
        return False
    if not celula:
        return True
    p = percentil_do_histograma(celula["hist"], PERCENTIL_PONTO_A_MELHORAR if percentil is None else percentil)
    return p is None or contagem > p


# Taxas por round (denominador = rounds do lado) usam o piso de rounds do perfil; as demais, o de eventos.
METRICAS_POR_ROUND = ("pct_rounds_sobreviveu", "pct_rounds_trade_kill")


def amostra_fraca(chave: str, denominador: float) -> bool:
    """A mesma marca de amostra fraca do perfil (decisão 7a), aplicada ao denominador DO LADO."""
    from metrics.player_profile import MIN_EVENTOS_PARA_TAXA, MIN_ROUNDS_PARA_TAXA
    return denominador < (MIN_ROUNDS_PARA_TAXA if chave in METRICAS_POR_ROUND else MIN_EVENTOS_PARA_TAXA)


def escolhe_celula(ref: dict | None, grupo: str, chave: str, lado: str, funcao: str | None) -> tuple:
    """(entrada da régua, escopo): o escopo é "funcao" (a célula (lado, função) tem jogador-lados
    suficientes), "lado" (poucos na célula: o lado inteiro) ou None (sem régua). Nunca olha o outro lado."""
    tabela = (((ref or {}).get(grupo) or {}).get(chave) or {}).get(lado) or {}
    minimo = int((ref or {}).get("min_ref_lado_funcao", MIN_REF_LADO_FUNCAO))
    if funcao and funcao in tabela and int(tabela[funcao].get("n", 0)) >= minimo:
        return tabela[funcao], "funcao"
    if tabela.get(TODAS) is not None:
        return tabela[TODAS], "lado"
    return None, None


def _soma(df: pl.DataFrame, col: str) -> float:
    return float(df[col].cast(pl.Float64).fill_null(0).sum()) if col in df.columns and df.height else 0.0


def metricas_por_lado(perfil_rounds: pl.DataFrame, impacto_rounds: pl.DataFrame) -> dict:
    """{(steamid, lado): {chave: (valor, n, d)}} das métricas de ponto forte, recalculadas SÓ com os rounds
    daquele lado (a referência é por lado e nunca mistura os dois). Mesmos numeradores e denominadores do
    resumo da partida (`impacto.TAXAS_DE_IMPACTO` e `player_profile.TAXAS_POR_ROUND`), só filtrados por
    lado; as de pós-plant e aberturas já são de um lado só (TR ou CT) pela definição. O valor é None sem
    denominador, como no perfil."""
    from metrics.impacto import TAXAS_DE_IMPACTO

    out: dict = {}

    def grava(sid, lado, chave, n, d):
        out.setdefault((int(sid), lado), {})[chave] = (n / d if d > 0 else None, n, d)

    for (sid, lado), g in perfil_rounds.group_by(["steamid", "side"], maintain_order=True):
        grava(sid, lado, "pct_rounds_sobreviveu", _soma(g, "survived"), float(g.height))
        grava(sid, lado, "pct_rounds_trade_kill", _soma(g, "fez_trade_kill"), float(g.height))
        em = g.filter(pl.col("em_clutch"))
        grava(sid, lado, "taxa_conversao_clutch", float(em.filter(pl.col("clutch_convertido")).height),
              float(em.height))
    chaves = {c for c, _, _ in METRICAS_DE_PONTO_FORTE}
    for (sid, lado), g in impacto_rounds.group_by(["steamid", "side"], maintain_order=True):
        for chave, n_col, d_col in TAXAS_DE_IMPACTO:
            if chave not in chaves:
                continue
            if (chave.endswith("_tr") or "pos_plant" in chave) and lado != "t":
                continue                                                  # situação de TR
            if (chave.endswith("_ct") or "retake" in chave) and lado != "ct":
                continue                                                  # situação de CT
            grava(sid, lado, chave, *_n_d_do_impacto(g, n_col, d_col))
    return out


def _n_d_do_impacto(g: pl.DataFrame, n_col: str, d_col: str) -> tuple[float, float]:
    """Numerador e denominador de uma taxa de impacto, a partir das colunas por round (o `impacto()` soma as
    mesmas colunas por jogador; aqui por jogador e lado)."""
    def ponderado(peso: str, col: str) -> float:
        return float((g[peso] * g[col]).fill_null(0).sum())

    if d_col in ("hes_jogadas", "molotovs_jogados", "flashes_jogadas"):         # utilidade: colunas diretas
        return _soma(g, n_col), _soma(g, d_col)
    if d_col.startswith("rounds_vivo_no_plant"):                                 # só os rounds vivo no plant
        vivo = g.filter(pl.col("venceu").is_not_null())
        coluna = {"pos_plant_vencidos": "venceu", "retakes_vencidos": "venceu",
                  "kills_pos_plant_tr": "kills_depois_do_plant", "kills_pos_plant_ct": "kills_depois_do_plant",
                  "pos_plant_sobreviveu": "sobreviveu", "retake_sobreviveu": "sobreviveu"}[n_col]
        return _soma(vivo, coluna), float(vivo.height)
    if d_col.startswith("duelos_de_abertura"):
        duelos = g.filter(pl.col("venceu_abertura").is_not_null())
        return _soma(duelos, "venceu_abertura"), float(duelos.height)
    if n_col.startswith("dano_"):                                                # ADR com o time em cada compra
        return ponderado(f"peso_{n_col[5:]}", "dano"), _soma(g, f"peso_{n_col[5:]}")
    if n_col.startswith("kast_rounds_"):
        return ponderado(f"peso_{n_col[12:]}", "kast"), _soma(g, f"peso_{n_col[12:]}")
    if n_col == "kills_contra_cheia":
        return ponderado("peso_contra_cheia", "kills"), _soma(g, "peso_contra_cheia")
    raise KeyError((n_col, d_col))


# Pontos fortes por (lado, função), a mesma regra dos pontos a melhorar, também no site publicado (decisão 46;
# o Pedro aprovou na fase 16a). O cálculo antigo da fase 12 (por função principal) foi removido.
FORTES_POR_LADO_PUBLICADOS = True


def carrega_referencia(caminho: Path = REFERENCIA_FILE) -> dict | None:
    import json
    if not caminho.exists():
        return None
    return json.loads(caminho.read_text(encoding="utf-8"))


def build(match_id: str, processed_root: Path | None = None) -> Path:
    """Grava data/processed/<partida>/erros_do_jogador.parquet: TODAS as ocorrências (com o filtro de cada
    uma), para a página, a régua do corpus e o material de calibração lerem a mesma tabela; e (fase 18)
    mortes.parquet: cada morte por inimigo, trocada ou não e por quem."""
    p = carrega_partida(match_id, processed_root)
    pasta = (processed_root or PROJECT_ROOT / "data" / "processed") / match_id
    ocorrencias(p).write_parquet(pasta / ARQUIVO)
    mortes_trocadas(p).write_parquet(pasta / ARQUIVO_MORTES)       # fase 18: toda morte, trocada ou não
    return pasta / ARQUIVO
