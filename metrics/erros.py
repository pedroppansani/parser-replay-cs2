"""Onde cada jogador custou rounds ao time nesta partida (fase 12, aba Perfil).

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
  vence o round menos se perde). Ver a nota de decisão 46.

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

import polars as pl

from metrics.basic_metrics import _pares_de_trade
from metrics.constantes import JANELA_DE_TRADE_S
from metrics.grenades import EFFECTIVE_BLIND_SECONDS, FIRE_WEAPONS, HE_WEAPONS
from metrics.rating import ARMA_PARA_GRUPO

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# --- Constantes novas (fase 12). Cada uma está no material de calibração, seção 7 ---------------

# Distância de troca: até aqui um aliado vivo ainda consegue trocar a morte dentro da janela.
# Origem: o raio de apoio que o projeto já usa para "companheiro por perto" (player_profile e
# structural_roles, RAIO_COMPANHEIRO = 600, "o alcance em que uma troca ainda acontece"); conferido
# na distribuição do corpus (MATERIAL_DE_CALIBRACAO.md, seção 7).
DIST_TROCA = 600.0

# Duelo próprio: o jogador que levou ou causou dano nestes segundos antes da morte do aliado estava
# na briga dele, não deixou de trocar. Origem: um duelo de rifle (tempo de reação de ~0,25 s mais o
# tempo para matar de 0,3 a 1 s) cabe com folga em 2 s; a faixa de 1 a 4 s está no material.
S_DUELO = 2.0

# Cegueira imposta ao próprio time. Origem: o percentil 90 do corpus (52 partidas, fora eco e
# pós-plant perdido): da soma por jogador-partida (520 valores; mediana 8,7 s, p90 27,1 s) e da
# cegueira nos aliados por flash (2.814 flashes; mediana 1,6 s, p90 4,8 s). Histogramas e varredura
# no material de calibração, seção 7.
SEG_CEGUEIRA_ALIADO = 27.0        # soma na partida, segundos
SEG_CEGUEIRA_ALIADO_UMA = 4.8     # numa flash só, segundos

# Dano de HE ou molotov no próprio time, soma na partida. Origem: o percentil 95 do corpus por
# jogador-partida (520 valores; mediana 0, p75 1, p90 10, p95 19). O p90 não serve: mais da metade
# não feriu ninguém do time, e 10 de dano é um tique de molotov. Material de calibração, seção 7.
DANO_UTILIDADE_ALIADO = 20.0

# Um tipo com menos ocorrências que isto não vira "ponto a melhorar": vai para "Detalhes" (pedido 12.5).
MIN_OCORRENCIAS_PARA_PONTO = 2
MAX_PONTOS_A_MELHORAR = 3         # pedido 12.5
MAX_PONTOS_FORTES = 2             # pedido 12.5
# Ponto forte: ficar pelo menos esta fração acima da referência da função. É a mesma margem de
# destaque que a aba Perfil já usa (MARGEM_DESTAQUE = 0,15 no template), lida como fração da régua
# porque as métricas têm escalas diferentes (porcentagem, dano, segundos).
MARGEM_PONTO_FORTE = 0.15

# Tipos publicados no site. COMEÇA VAZIA (pedido 12.4): um tipo só entra depois que o Pedro
# confirmar pelo menos 8 dos 10 exemplos do material de calibração (seção 7).
TIPOS_DE_ERRO_VALIDADOS: frozenset[str] = frozenset()

# --- Os tipos ---------------------------------------------------------------------------------

NAO_TROCOU = "nao_trocou"
POSSIVEL_BAIT = "possivel_bait"
PERDEU_A_TROCA = "perdeu_a_troca"
MORREU_ISOLADO = "morreu_isolado"
PRIMEIRA_MORTE_SEM_TROCA = "primeira_morte_sem_troca"
FLASH_NO_TIME = "flash_no_time"
DANO_DE_UTILIDADE_NO_TIME = "dano_de_utilidade_no_time"

# Ordem fixa: é a ordem das tabelas, do material e o desempate da tela.
TIPOS = (NAO_TROCOU, POSSIVEL_BAIT, PERDEU_A_TROCA, MORREU_ISOLADO, PRIMEIRA_MORTE_SEM_TROCA,
         FLASH_NO_TIME, DANO_DE_UTILIDADE_NO_TIME)

TITULOS = {
    NAO_TROCOU: "Não trocou o aliado",
    POSSIVEL_BAIT: "Possível bait",              # sempre com "possível": o dado mostra posição e tempo
    PERDEU_A_TROCA: "Perdeu a troca",
    MORREU_ISOLADO: "Morreu isolado",
    PRIMEIRA_MORTE_SEM_TROCA: "Primeira morte sem troca",
    FLASH_NO_TIME: "Flash no time",
    DANO_DE_UTILIDADE_NO_TIME: "Dano de utilidade no time",
}

# "Como melhorar": uma frase por tipo, fixa (decisão 18; propostas do pedido 12.3, a aprovar pelo
# Pedro no material de calibração).
COMO_MELHORAR = {
    NAO_TROCOU: ("Jogue a uma distância de troca do parceiro e mirando o mesmo ponto que ele. Se ele cair, o "
                 "matador está exposto por alguns segundos: é a sua janela."),
    POSSIVEL_BAIT: ("Se você é o segundo a entrar, entre logo atrás e ao lado, não atrás de parede. Combinem "
                    "antes quem entra e quem troca."),
    PERDEU_A_TROCA: ("Na troca, não pique o mesmo ângulo que acabou de matar o aliado. Mude o ângulo ou jogue "
                     "uma flash no matador antes."),
    MORREU_ISOLADO: ("Se não é o lurker, jogue perto de um aliado e avise a posição. Morrer sozinho dá vantagem "
                     "numérica de graça."),
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
    NAO_TROCOU: "o aliado morreu perto dele e o matador saiu vivo da janela de troca",
    POSSIVEL_BAIT: ("estava atrás do aliado, não atirou no matador e sobreviveu à janela de troca; "
                    "o dado mostra posição e tempo, não intenção"),
    PERDEU_A_TROCA: "foi para a troca e morreu sem matar quem matou o aliado",
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
FILTRO_CEGO = "cego no momento"
FILTRO_DUELO = "em duelo próprio"
FILTRO_SEM_ARMA = "sem arma de fogo"
FILTRO_1_CONTRA_N = "sem aliado vivo (1 contra N)"
FILTRO_ABAIXO_DO_LIMIAR = "abaixo do limiar da partida"

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
    degradado: list = field(default_factory=list)


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


class _Indice:
    """Índices da partida para as perguntas que todo tipo faz (quem está vivo, onde, cego, em duelo)."""

    def __init__(self, p: Partida):
        self.p = p
        self.janela = int(JANELA_DE_TRADE_S * p.tickrate)
        k = p.kills.sort(["round_num", "tick"], maintain_order=True)
        self.kills = k.to_dicts()
        # primeira morte de cada (round, jogador)
        self.morte: dict = {}
        for r in self.kills:
            if r["victim_steamid"] is not None:
                self.morte.setdefault((int(r["round_num"]), int(r["victim_steamid"])), int(r["tick"]))
        # mortes trocadas: (round, tick da morte, vítima) -- a definição da fase 7
        pares = _pares_de_trade(p.kills, JANELA_DE_TRADE_S, p.tickrate) if p.kills.height else None
        self.trocadas = set()
        if pares is not None:
            for r in pares.select("round_num", "tick_prev", "victim_steamid_prev").iter_rows():
                self.trocadas.add((int(r[0]), int(r[1]), int(r[2])))
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

    def time(self, sid) -> str | None:
        return self.p.team_of.get(int(sid)) if sid is not None else None

    def eh_kill_inimiga(self, k: dict) -> bool:
        a, v = k.get("attacker_steamid"), k.get("victim_steamid")
        return a is not None and v is not None and self.time(a) is not None and self.time(a) != self.time(v)

    def jogadores_em(self, rn: int, t: int) -> list[dict]:
        """As linhas de posição do tick mais próximo ANTES ou NO instante t (o tick exato, se houver)."""
        ticks = self.ticks_do_round.get(rn) or []
        import bisect
        i = bisect.bisect_right(ticks, t) - 1
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
        """Regra 1 do pedido (e o fim do round): eco/pistola do time, time guardando arma, ou depois do fim."""
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
        return None

    def vivos_dos_times(self, rn: int, sid: int, t: int) -> tuple[int, int]:
        """(vivos do time de sid, vivos do adversário) no instante t, antes do evento desse tick."""
        meu = self.time(sid)
        linhas = self.jogadores_em(rn, t - 1) or self.jogadores_em(rn, t)
        meus = sum(1 for r in linhas if self.time(r["steamid"]) == meu and self.vivo(rn, int(r["steamid"]), t - 1))
        deles = sum(1 for r in linhas if self.time(r["steamid"]) not in (None, meu)
                    and self.vivo(rn, int(r["steamid"]), t - 1))
        return meus, deles

    def dwpa(self, rn: int, t: int, vitima: int, time: str | None) -> float | None:
        """Queda da chance de o `time` vencer a PARTIDA na kill de `vitima` (negativa = queda)."""
        v = self.p.variacao.get((rn, int(t), int(vitima)))
        alav = self.p.alavanca.get((rn, time))
        if v is None or alav is None:
            return None
        delta = v["delta"] if self.time(vitima) == time else -v["delta"]
        return delta * alav


def _base(ix: _Indice, tipo: str, rn: int, t: int, sid: int) -> dict:
    nome = ix.p.nomes.get(int(sid), str(sid))
    meus, deles = ix.vivos_dos_times(rn, sid, t)
    return {"tipo": tipo, "match_id": ix.p.match_id, "round_num": rn, "tick": int(t), "segundos": ix.segundos(rn, t),
            "steamid": int(sid), "name": nome, "side": ix.lado(rn, sid), "aliado_steamid": None, "aliado": None,
            "matador_steamid": None, "matador": None, "dist_aliado": None, "dist_matador_jogador": None,
            "dist_matador_aliado": None, "vivos_time": meus, "vivos_adversario": deles, "dwpa": None,
            "valor": None, "filtro": None}


def _r(x: float | None) -> float | None:
    return None if x is None or math.isinf(x) else round(float(x), 1)


# --- Tipos 1 e 2: não trocou o aliado e possível bait ----------------------------------------

def _mortes_de_aliado(ix: _Indice):
    """Cada morte por inimigo, com o matador: (kill, round, tick, vítima, matador)."""
    for k in ix.kills:
        if ix.eh_kill_inimiga(k):
            yield k, int(k["round_num"]), int(k["tick"]), int(k["victim_steamid"]), int(k["attacker_steamid"])


def nao_trocou(p: Partida, dist_troca: float = DIST_TROCA, s_duelo: float = S_DUELO,
               _ix: _Indice | None = None) -> list[dict]:
    """Um aliado morre; o jogador estava vivo, a no máximo `dist_troca` do aliado, e o matador NÃO morre
    dentro da janela de troca (a morte não foi trocada, fase 7). Fica de fora: o jogador cego no momento,
    em duelo próprio (levou ou causou dano nos `s_duelo` segundos antes) ou sem arma de fogo."""
    ix = _ix or _Indice(p)
    out = []
    for k, rn, t, v, a in _mortes_de_aliado(ix):
        if (rn, t, v) in ix.trocadas:
            continue
        pos_v = {"X": k["victim_X"], "Y": k["victim_Y"], "Z": k["victim_Z"]}
        pos_a = {"X": k["attacker_X"], "Y": k["attacker_Y"], "Z": k["attacker_Z"]}
        for r in ix.aliados_vivos(rn, v, t):
            d = distancia(r, pos_v, p.corte_de_andar)
            if d > dist_troca:
                continue
            sid = int(r["steamid"])
            oc = _base(ix, NAO_TROCOU, rn, t, sid)
            oc.update(aliado_steamid=v, aliado=p.nomes.get(v, str(v)), matador_steamid=a,
                      matador=p.nomes.get(a, str(a)), dist_aliado=_r(d),
                      dist_matador_jogador=_r(distancia(r, pos_a, p.corte_de_andar)),
                      dist_matador_aliado=_r(distancia(pos_v, pos_a, p.corte_de_andar)),
                      dwpa=ix.dwpa(rn, t, v, ix.time(sid)))
            oc["filtro"] = (ix.filtro_do_round(rn, sid, t)
                            or (FILTRO_CEGO if ix.cego(rn, sid, t) else None)
                            or (FILTRO_DUELO if ix.em_duelo(rn, sid, t, s_duelo) else None)
                            or (None if ix.tem_arma(rn, sid, t) else FILTRO_SEM_ARMA))
            out.append(oc)
    return out


def possivel_bait(p: Partida, dist_troca: float = DIST_TROCA, s_duelo: float = S_DUELO,
                  _ix: _Indice | None = None) -> list[dict]:
    """Subconjunto de "não trocou": o jogador estava ATRÁS do aliado em relação ao matador (mais longe do
    matador do que o aliado), não causou dano ao matador na janela e sobreviveu à janela. Os filtros são os
    mesmos de "não trocou". Sempre "possível": o dado mostra posição e tempo, não intenção."""
    ix = _ix or _Indice(p)
    out = []
    for oc in nao_trocou(p, dist_troca, s_duelo, _ix=ix):
        rn, t, sid, a = oc["round_num"], oc["tick"], oc["steamid"], oc["matador_steamid"]
        dj, da = oc["dist_matador_jogador"], oc["dist_matador_aliado"]
        if dj is None or da is None or not dj > da:
            continue
        fim = t + ix.janela
        atirou = any(int(d["round_num"]) == rn and t < d["tick"] <= fim and d["attacker_steamid"] is not None
                     and int(d["attacker_steamid"]) == sid and d["victim_steamid"] is not None
                     and int(d["victim_steamid"]) == a for d in ix.dano)
        if atirou or not ix.vivo(rn, sid, fim):
            continue
        out.append({**oc, "tipo": POSSIVEL_BAIT})
    return out


# --- Tipo 3: perdeu a troca --------------------------------------------------------------------

def perdeu_a_troca(p: Partida, _ix: _Indice | None = None) -> list[dict]:
    """Um aliado morre; o jogador vai para a troca (causa dano ao matador ou morre para ele dentro da
    janela) e morre dentro da janela sem matar o matador."""
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
            deu_dano = any(int(d["round_num"]) == rn and t < d["tick"] <= fim and d["attacker_steamid"] is not None
                           and int(d["attacker_steamid"]) == sid and d["victim_steamid"] is not None
                           and int(d["victim_steamid"]) == a for d in ix.dano)
            morreu_para_ele = any(int(x["round_num"]) == rn and x["tick"] == morte and int(x["victim_steamid"]) == sid
                                  and x["attacker_steamid"] is not None and int(x["attacker_steamid"]) == a
                                  for x in ix.kills)
            if not (deu_dano or morreu_para_ele):
                continue
            oc = _base(ix, PERDEU_A_TROCA, rn, morte, sid)
            pos_v = {"X": k["victim_X"], "Y": k["victim_Y"], "Z": k["victim_Z"]}
            pos_a = {"X": k["attacker_X"], "Y": k["attacker_Y"], "Z": k["attacker_Z"]}
            oc.update(aliado_steamid=v, aliado=p.nomes.get(v, str(v)), matador_steamid=a,
                      matador=p.nomes.get(a, str(a)), dist_aliado=_r(distancia(r, pos_v, p.corte_de_andar)),
                      dist_matador_jogador=_r(distancia(r, pos_a, p.corte_de_andar)),
                      dist_matador_aliado=_r(distancia(pos_v, pos_a, p.corte_de_andar)),
                      dwpa=ix.dwpa(rn, morte, sid, ix.time(sid)))
            oc["filtro"] = ix.filtro_do_round(rn, sid, morte)
            out.append(oc)
    return out


# --- Tipos 4 e 5: morreu isolado e primeira morte sem troca ---------------------------------------

def morreu_isolado(p: Partida, dist_troca: float = DIST_TROCA, _ix: _Indice | None = None) -> list[dict]:
    """A morte do jogador não é trocada e NENHUM aliado vivo estava a até `dist_troca` dele. Fica de fora
    a situação de 1 contra N (sem aliado vivo para ajudar)."""
    ix = _ix or _Indice(p)
    out = []
    for k, rn, t, v, a in _mortes_de_aliado(ix):
        if (rn, t, v) in ix.trocadas:
            continue
        pos_v = {"X": k["victim_X"], "Y": k["victim_Y"], "Z": k["victim_Z"]}
        vivos = ix.aliados_vivos(rn, v, t)
        dists = [distancia(r, pos_v, p.corte_de_andar) for r in vivos]
        mais_perto = min(dists) if dists else None
        if mais_perto is not None and mais_perto <= dist_troca:
            continue
        oc = _base(ix, MORREU_ISOLADO, rn, t, v)
        oc.update(matador_steamid=a, matador=p.nomes.get(a, str(a)), dist_aliado=_r(mais_perto),
                  dist_matador_jogador=_r(distancia(pos_v, {"X": k["attacker_X"], "Y": k["attacker_Y"],
                                                            "Z": k["attacker_Z"]}, p.corte_de_andar)),
                  dwpa=ix.dwpa(rn, t, v, ix.time(v)))
        oc["filtro"] = ix.filtro_do_round(rn, v, t) or (FILTRO_1_CONTRA_N if not vivos else None)
        out.append(oc)
    return out


def primeira_morte_sem_troca(p: Partida, _ix: _Indice | None = None) -> list[dict]:
    """O jogador sofre a primeira morte do round (a primeira kill de inimigo, a mesma abertura de
    metrics/impacto) e ela não é trocada."""
    ix = _ix or _Indice(p)
    out = []
    for k, rn, t, v, a in _mortes_de_aliado(ix):
        if ix.abertura.get(rn) != (t, v) or (rn, t, v) in ix.trocadas:
            continue
        oc = _base(ix, PRIMEIRA_MORTE_SEM_TROCA, rn, t, v)
        oc.update(matador_steamid=a, matador=p.nomes.get(a, str(a)),
                  dist_matador_jogador=_r(distancia({"X": k["victim_X"], "Y": k["victim_Y"], "Z": k["victim_Z"]},
                                                    {"X": k["attacker_X"], "Y": k["attacker_Y"], "Z": k["attacker_Z"]},
                                                    p.corte_de_andar)),
                  dwpa=ix.dwpa(rn, t, v, ix.time(v)))
        vivos = ix.aliados_vivos(rn, v, t)
        if vivos:
            pos_v = {"X": k["victim_X"], "Y": k["victim_Y"], "Z": k["victim_Z"]}
            oc["dist_aliado"] = _r(min(distancia(r, pos_v, p.corte_de_andar) for r in vivos))
        oc["filtro"] = ix.filtro_do_round(rn, v, t)
        out.append(oc)
    return out


# --- Tipos 7 e 8: flash no time e dano de utilidade no time --------------------------------------

def flash_no_time(p: Partida, seg_aliado: float = SEG_CEGUEIRA_ALIADO, seg_uma: float = SEG_CEGUEIRA_ALIADO_UMA,
                  _ix: _Indice | None = None) -> list[dict]:
    """A cegueira imposta a aliados passa de `seg_aliado` na partida (soma) ou de `seg_uma` numa flash só.
    Uma ocorrência por flash que cegou companheiro (a mesma detonação: mesmo arremessador e mesmo tick);
    `valor` é a soma dos segundos de cegueira nos aliados daquela flash. Com a soma da partida abaixo do
    limiar, só a flash acima de `seg_uma` conta; as outras ficam de fora com o motivo."""
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
        oc["filtro"] = ix.filtro_do_round(rn, a, t)
        out.append(oc)
    _aplica_limiar(out, seg_aliado, seg_uma)
    return out


def _aplica_limiar(out: list[dict], limiar_partida: float, limiar_um: float | None) -> None:
    """Soma por jogador nas ocorrências que passaram nos filtros; abaixo do limiar da partida, só o evento
    acima do limiar de um evento (se houver) continua."""
    soma: dict = {}
    for oc in out:
        if oc["filtro"] is None:
            soma[oc["steamid"]] = soma.get(oc["steamid"], 0.0) + oc["valor"]
    for oc in out:
        if oc["filtro"] is not None or soma.get(oc["steamid"], 0.0) > limiar_partida:
            continue
        if limiar_um is not None and oc["valor"] > limiar_um:
            continue
        oc["filtro"] = FILTRO_ABAIXO_DO_LIMIAR


def dano_de_utilidade_no_time(p: Partida, dano_aliado: float = DANO_UTILIDADE_ALIADO,
                              _ix: _Indice | None = None) -> list[dict]:
    """O dano de HE ou molotov em aliados passa de `dano_aliado` na partida. Uma ocorrência por (round,
    granada): HE pelo tick da explosão, o fogo da molotov junto no round; `valor` é o dano no próprio time.
    O ΔWPA existe quando a granada matou o aliado (a kill tem variação no modelo); sem morte, é nulo."""
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
        oc["filtro"] = ix.filtro_do_round(rn, a, g["tick"])
        out.append(oc)
    _aplica_limiar(out, dano_aliado, None)
    return out


# --- Nível e motivo (pedido 12.2, "Explícito ou depende da tática") --------------------------------

def nivel_e_motivo(oc: dict, p: Partida, abertura: tuple | None = None) -> tuple[str | None, str | None]:
    """(nível, motivo) de uma ocorrência, pela ordem de regras do pedido; a primeira que se aplica decide.
    Ocorrência com filtro (regra 1 e os filtros do tipo) fica de fora: (None, None)."""
    if oc.get("filtro") is not None:
        return None, None                                                     # regra 1 e filtros do tipo
    tipo = oc["tipo"]
    f = p.funcoes.get((oc["steamid"], oc["side"])) or {}
    funcao, tendencia = f.get("funcao"), bool(f.get("tendencia"))

    def com_tendencia(motivo: str) -> str:                                   # regra 5
        return f"{motivo}; {MOTIVO_TENDENCIA}" if tendencia else motivo

    if tipo == MORREU_ISOLADO and funcao == "lurker":
        return DEPENDE, com_tendencia(MOTIVO_LURKER)                         # regra 2
    if tipo == PRIMEIRA_MORTE_SEM_TROCA and funcao == "entry":
        return DEPENDE, com_tendencia(MOTIVO_ENTRY)                          # regra 3
    if tipo in (MORREU_ISOLADO, PRIMEIRA_MORTE_SEM_TROCA):
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

    `constantes` troca DIST_TROCA, S_DUELO e os limiares (o material de calibração varre as faixas)."""
    ix = _Indice(p)
    dist = constantes.get("dist_troca", DIST_TROCA)
    s_duelo = constantes.get("s_duelo", S_DUELO)
    linhas = (nao_trocou(p, dist, s_duelo, _ix=ix) + possivel_bait(p, dist, s_duelo, _ix=ix)
              + perdeu_a_troca(p, _ix=ix) + morreu_isolado(p, dist, _ix=ix) + primeira_morte_sem_troca(p, _ix=ix)
              + flash_no_time(p, constantes.get("seg_aliado", SEG_CEGUEIRA_ALIADO),
                              constantes.get("seg_uma", SEG_CEGUEIRA_ALIADO_UMA), _ix=ix)
              + dano_de_utilidade_no_time(p, constantes.get("dano_aliado", DANO_UTILIDADE_ALIADO), _ix=ix))
    for oc in linhas:
        oc["nivel"], oc["motivo"] = nivel_e_motivo(oc, p, ix.abertura.get(oc["round_num"]))
    ordem = {t: i for i, t in enumerate(TIPOS)}
    linhas.sort(key=lambda o: (ordem[o["tipo"]], o["round_num"], o["tick"], o["steamid"],
                               o["aliado_steamid"] or 0))
    return pl.DataFrame(linhas, schema=ESQUEMA, orient="row") if linhas else pl.DataFrame(schema=ESQUEMA)


ESQUEMA = {
    "tipo": pl.String, "match_id": pl.String, "round_num": pl.Int64, "tick": pl.Int64, "segundos": pl.Float64,
    "steamid": pl.UInt64, "name": pl.String, "side": pl.String, "aliado_steamid": pl.UInt64, "aliado": pl.String,
    "matador_steamid": pl.UInt64, "matador": pl.String, "dist_aliado": pl.Float64,
    "dist_matador_jogador": pl.Float64, "dist_matador_aliado": pl.Float64, "vivos_time": pl.Int64,
    "vivos_adversario": pl.Int64, "dwpa": pl.Float64, "valor": pl.Float64, "filtro": pl.String,
    "nivel": pl.String, "motivo": pl.String,
}


def por_jogador(tabela: pl.DataFrame) -> dict[int, list[dict]]:
    """{steamid: [ocorrências que passaram nos filtros]}, na ordem da tabela."""
    out: dict[int, list[dict]] = {}
    for oc in tabela.filter(pl.col("filtro").is_null()).iter_rows(named=True):
        out.setdefault(int(oc["steamid"]), []).append(oc)
    return out


# --- Montagem a partir do processado e do interim ------------------------------------------------

def _primeira_arma(ticks: pl.DataFrame, rounds: pl.DataFrame) -> dict:
    janela = rounds.select("round_num", "freeze_end")
    com_arma = (ticks.select("round_num", "tick", "steamid", "active_weapon_name")
                .filter(pl.col("active_weapon_name").is_in(sorted(FIREARMS)))
                .join(janela, on="round_num", how="inner")
                .filter(pl.col("tick") >= pl.col("freeze_end"))
                .group_by(["round_num", "steamid"], maintain_order=True).agg(pl.col("tick").min()))
    return {(int(r[0]), int(r[1])): int(r[2]) for r in com_arma.iter_rows()}


def carrega_partida(match_id: str, processed_root: Path | None = None, interim_root: Path | None = None) -> Partida:
    """A partida processada como os tipos de erro a leem (interim + processado + modelos do projeto)."""
    from leitura.insights import resolve_teams, score_progression
    from metrics.economia import grupos_de_compra
    from metrics.map_areas import floor_split_z
    from metrics.player_roles import awpers_do_time
    from metrics.rating import ModeloDeRound, carrega_referencia, grupo_do_round, variacao_por_kill
    from metrics.structural_roles import estabilidade_da_funcao
    from metrics.timing import detect_tickrate
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
    for linha in variacao_por_kill(kills, rounds, grupo_do_round(ticks, rounds), modelo, team_of, tickrate):
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
        degradado=degradado)


ARQUIVO = "erros_do_jogador.parquet"
REFERENCIA_FILE = Path(__file__).resolve().parent / "erros_reference.json"

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


def carrega_referencia(caminho: Path = REFERENCIA_FILE) -> dict | None:
    import json
    if not caminho.exists():
        return None
    return json.loads(caminho.read_text(encoding="utf-8"))


def build(match_id: str, processed_root: Path | None = None) -> Path:
    """Grava data/processed/<partida>/erros_do_jogador.parquet: TODAS as ocorrências (com o filtro de cada
    uma), para a página, a régua do corpus e o material de calibração lerem a mesma tabela."""
    p = carrega_partida(match_id, processed_root)
    out = (processed_root or PROJECT_ROOT / "data" / "processed") / match_id / ARQUIVO
    ocorrencias(p).write_parquet(out)
    return out
