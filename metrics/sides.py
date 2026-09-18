"""
De que lado cada time joga em cada round — a regra num lugar só.

POR QUE ESTE MÓDULO EXISTE (bug real, pego cruzando com a HLTV):
a regra "os lados trocam depois do round 12" estava copiada em três arquivos, e
nenhuma cópia conhecia a prorrogação. FURIA x Falcons (PGL Cluj-Napoca 2026,
Mirage) terminou 16-14 na HLTV e saía 17-13 aqui -- placar impossível no CS2,
porque na prorrogação quem chega a 16 vence. Os rounds 28-30 iam para o time
errado, e com eles o placar, o MVP, o clutch, o replay e o rating.

A REGRA, MEDIDA NAS DEMOS (não assumida), com o lado do time que começou de T:

    rounds  1-12   T
    rounds 13-24   CT        troca no intervalo
    rounds 25-27   CT        a prorrogação COMEÇA no lado do 2º tempo
    rounds 28-30   T         e troca a cada 3 rounds
    rounds 31-33   CT        (segunda prorrogação, e assim por diante)

Observado em match_16 e match_20 (as duas prorrogações do corpus). O código
antigo acertava 25-27 por coincidência — tratava tudo acima de 12 como segundo
tempo — e errava a partir do 28. tests/test_sides.py confere a regra contra o
lado real de cada jogador em TODAS as partidas processadas: se uma demo um dia
fugir disso (outro formato de prorrogação), o teste falha em vez de o número
sair errado em silêncio.

Convenção do projeto: Time A = quem começou de T; Time B = quem começou de CT.
"""
from __future__ import annotations

# MR12: 12 rounds por metade no tempo regulamentar.
REGULATION_HALF = 12
# Prorrogação MR3: 3 rounds por metade (6 por prorrogação).
OT_HALF = 3


def _team_a_on_t(round_num: int) -> bool:
    """O Time A (que começou de T) está de T neste round?"""
    if round_num <= REGULATION_HALF:
        return True
    if round_num <= 2 * REGULATION_HALF:
        return False
    # Prorrogação: a primeira metade repete o lado do 2º tempo (CT para o A) e
    # depois alterna a cada OT_HALF rounds.
    metade_da_prorrogacao = (round_num - 2 * REGULATION_HALF - 1) // OT_HALF
    return metade_da_prorrogacao % 2 == 1


def side_of_team(team: str, round_num: int) -> str:
    """Lado ("t" ou "ct") que o time joga no round."""
    a_on_t = _team_a_on_t(round_num)
    if team == "A":
        return "t" if a_on_t else "ct"
    return "ct" if a_on_t else "t"


def team_of_side(side: str, round_num: int) -> str:
    """Time ("A" ou "B") que está no lado dado, no round."""
    a_on_t = _team_a_on_t(round_num)
    if side == "t":
        return "A" if a_on_t else "B"
    return "B" if a_on_t else "A"
