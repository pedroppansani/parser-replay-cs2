"""A guarda dos números das fases design-* (scripts/design/impressao_numeros.py)."""
from __future__ import annotations

from scripts.design.impressao_numeros import (LIMITE_DE_ITENS, achata, blobs_da_pagina, compara,
                                              impressao_da_landing, le, para_texto)


def test_achata_so_guarda_numero_e_resume_lista_numerica_e_lista_longa_de_objetos():
    saida: dict[str, str] = {}
    achata({"a": 1, "b": 2.5, "c": "texto", "d": True, "e": None, "f": [1, 2, 3], "g": ["x", "y"],
            "h": {"i": 7}, "j": [{"k": 1}, {"k": 2}]}, "p", saida)
    assert saida["p.a"] == "1" and saida["p.b"] == "2.5" and saida["p.h.i"] == "7"
    assert saida["p.f"].startswith("lista n=3 sha256:") and saida["p.j[0].k"] == "1" and saida["p.j[1].k"] == "2"
    assert "p.c" not in saida and "p.d" not in saida and "p.e" not in saida and "p.g" not in saida
    longa = {"l": [{"k": i} for i in range(LIMITE_DE_ITENS + 1)]}
    resumida, fina = {}, {}
    achata(longa, "p", resumida)
    achata(longa, "p", fina, fina=True)
    assert list(resumida) == ["p.l"] and resumida["p.l"].startswith("itens n=13 sha256:")
    assert len(fina) == LIMITE_DE_ITENS + 1


def test_o_hash_muda_quando_um_so_numero_muda_e_a_comparacao_diz_o_que_mudou():
    a, b = {}, {}
    achata({"v": [1, 2, 3, 4]}, "p", a)
    achata({"v": [1, 2, 3, 5]}, "p", b)
    assert a != b
    dif = compara({**a, "x": "1", "y": "2"}, {**b, "x": "9", "z": "3"})
    assert [d.split()[0] for d in dif] == ["mudou", "mudou", "sumiu", "apareceu"]
    assert para_texto({"b": "2", "a": "1"}) == "a = 1\nb = 2\n"


def test_blobs_da_pagina_acha_json_embutido_e_ignora_constante_de_codigo():
    grande = '{"k": [' + ", ".join(str(i) for i in range(60)) + "]}"
    html = (f'<script type="application/json" id="payload">{grande}</script>'
            f"<script>var C = [0.25, 0.5, 1, 2, 4]; var DADOS = {grande}; var x = {{a: 1}};</script>")
    nomes = [n for n, _ in blobs_da_pagina(html)]
    assert nomes == ["payload", "DADOS"]


def test_a_landing_so_conta_placar_e_rounds_do_card_e_ignora_a_frase():
    html = ('<p class="corpus" id="corpus">52 partidas em 8 mapas</p>'
            '<section class="nums" id="tres-numeros"><div class="num"><b>0,079</b></div></section>'
            '<a class="mcard" href="match_01.html"><div class="mtop"><span class="mscore">13<em>x</em>9</span></div>'
            '<div class="mfoot"><span>22 rounds</span><span>X impôs 74s de cegueira</span></div></a>')
    saida: dict[str, str] = {}
    impressao_da_landing(html, saida)
    assert saida["index.html::corpus"] == "52 8"
    assert saida["index.html::card[match_01.html]"] == "placar 13 9 | rounds 22"
    assert all("74" not in v for v in saida.values())


def test_o_arquivo_gravado_do_main_existe_e_nao_tem_linha_de_testes():
    from scripts.design.impressao_numeros import ANTES
    assert ANTES.exists()
    antes = le(ANTES)
    assert len(antes) > 1000 and not any(k.endswith("testes.coletados") for k in antes)
