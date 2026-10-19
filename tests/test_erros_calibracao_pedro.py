"""As respostas do Pedro à seção 7 do material de calibração (2026-10-16, decisão 46).

- "Flash no time": a flash que cegou o time menos de `MIN_CEGUEIRA_FLASH_ALIADO` (2,0 s) não é ocorrência,
  mesmo com a soma do lado acima do limiar; a soma continua contando todas as flashes.
"""
from __future__ import annotations

from metrics import erros as E
from tests.test_erros import cegueira, partida


def test_min_cegueira_flash_aliado_e_2_segundos():
    assert E.MIN_CEGUEIRA_FLASH_ALIADO == 2.0
    assert not E.cegou_o_bastante(1.99) and E.cegou_o_bastante(2.0) and not E.cegou_o_bastante(None)


def test_flash_de_1_99_s_nao_e_ocorrencia_mesmo_com_a_soma_acima_do_limiar():
    # 14 flashes de 2,0 s (28 s) e uma de 1,99 s: a soma do lado (29,99 s) passa do limiar de 27 s
    cegos = [cegueira(100 * i, 2, 3, 2.0) for i in range(1, 15)] + [cegueira(5000, 2, 4, 1.99)]
    oc = E.flash_no_time(partida([], {}, cegos=cegos))
    curta = [o for o in oc if o["tick"] == 5000]
    assert len(curta) == 1 and curta[0]["filtro"] == E.FILTRO_CEGUEIRA_CURTA
    # a de exatamente 2,0 s é ocorrência
    assert all(o["filtro"] is None for o in oc if o["tick"] != 5000) and len(oc) == 15
    # a soma conta todas, inclusive a curta (ela mede o padrão)
    assert all(o["valor_soma_lado"] == 29.99 for o in oc)


def test_a_soma_com_a_flash_curta_ainda_tira_as_outras_do_limiar():
    # sem a de 1,5 s a soma (26 s) ficaria abaixo de 27 s; com ela (27,5 s) as de 2,0 s contam
    cegos = [cegueira(100 * i, 2, 3, 2.0) for i in range(1, 14)] + [cegueira(5000, 2, 4, 1.5)]
    oc = E.flash_no_time(partida([], {}, cegos=cegos))
    assert [o["filtro"] for o in oc] == [None] * 13 + [E.FILTRO_CEGUEIRA_CURTA]


def test_flash_curta_acima_do_limiar_de_uma_flash_nao_existe_e_a_longa_continua():
    # a regra de uma flash só (acima de 4,8 s) não muda: com a soma abaixo do limiar, a longa conta
    oc = E.flash_no_time(partida([], {}, cegos=[cegueira(100, 2, 3, 5.3), cegueira(200, 2, 4, 1.0)]))
    assert [o["filtro"] for o in oc] == [None, E.FILTRO_ABAIXO_DO_LIMIAR]
