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
    rounds 28-30   T         e troca no meio dela
    rounds 31-33   T         a 2ª prorrogação começa no lado em que a 1ª
    rounds 34-36   CT        TERMINOU -- não há troca entre prorrogações
    rounds 37-39   CT        (3ª: de novo sem troca na virada, e assim por diante)

Ou seja: nunca se troca de lado na virada de uma metade para a prorrogação
seguinte, só no meio de cada prorrogação. Em blocos de 3 a partir do 25, o
Time A fica CT, T, T, CT, CT, T, T, ...

Medido em match_16 e match_20 (uma prorrogação) e em match_31, match_32 e
match_42 (duas). Registro de um erro meu: a linha 31-33 desta tabela já
estava aqui dizendo CT "e assim por diante", escrita quando o corpus só tinha
prorrogação simples -- extrapolação, não medição. As três partidas com
prorrogação dupla mostraram o contrário. O código antigo, antes deste módulo,
acertava 25-27 por coincidência e errava a partir do 28. tests/test_sides.py confere a regra contra o
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
    # Prorrogação, em blocos de OT_HALF rounds: CT, T | T, CT | CT, T | ...
    # A troca acontece só DENTRO de cada prorrogação; na virada de uma para a
    # outra o lado se mantém. Por isso o padrão repete a cada 4 blocos.
    bloco = (round_num - 2 * REGULATION_HALF - 1) // OT_HALF
    return bloco % 4 in (1, 2)


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


def placar_valido(a: int, b: int, n_rounds: int) -> bool:
    """O placar final é possível no MR12 com prorrogação MR3?

    Vence quem chega a 13; no 12-12, cada prorrogação começa empatada e acaba
    em 4-0, 4-1 ou 4-2, então o vencedor fecha em 16, 19, 22... com o perdedor
    2 a 4 atrás. Partida de FACEIT pode acabar antes por desistência, e aí
    ninguém chega a 13. Um placar impossível denuncia lado trocado, round a mais
    (faca, warmup) ou demo dividida sem fundir -- foi assim que o round de faca
    da Vitality x Spirit apareceu (15-9 em 24 rounds).
    """
    alto, baixo = max(a, b), min(a, b)
    if a + b != n_rounds:
        return False
    if alto <= REGULATION_HALF:            # desistência antes do fim
        return True
    if alto == REGULATION_HALF + 1:
        return baixo <= REGULATION_HALF - 1
    return (alto - REGULATION_HALF - 1) % OT_HALF == 0 and alto - 4 <= baixo <= alto - 2
