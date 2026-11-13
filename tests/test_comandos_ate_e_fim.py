"""CR1d: "até" é o FIM. "segura o meio até 0:45" = fica no meio desde agora (ou desde o fim do comando anterior) até 0:45; "segura o meio aos 0:45" continua sendo o INÍCIO.
Vale para o leitor (`comandos/leitor.js`), a prancheta (o plano e o cartão) e o Reescrever (`comandos/real.js`: os vereditos). `esperar` já lia "até" como fim e `mover` ("corre pro
meio até 0:45") não muda: só o `segurar` (segura, fica, holda...)."""
from __future__ import annotations

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_comandos_aba import _aplica  # noqa: E402,F401
from tests.test_comandos_do_real import le, pg, ver  # noqa: E402,F401  (o leitor com os dados do round 23 da match_43)
from tests.test_comandos_tempos import _escreve, _peca, _ponto  # noqa: E402,F401
from tests.test_comandos_tempos import _pagina as _pagina_da_prancheta  # noqa: E402,F401
from tests.test_tactics_browser import contexto, interno, navegador  # noqa: E402,F401


def _acao(x, i=0):
    return x["r"]["acoes"][i]


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# o leitor
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def _fim(pg, frase):
    return pg.evaluate("""f => { const l = ComandosDoReal.le(f, window.ctx); return l.acoes.map(a => ({ tipo: a.tipo, quando: a.quando, fim: a.fim || null })); }""", frase)


def test_ate_e_o_fim_do_segurar_e_aos_continua_sendo_o_inicio(pg):
    a = _fim(pg, "tr 2 segura o meio até 0:45")[0]
    assert a["tipo"] == "segurar" and a["quando"] == {"tipo": "agora"} and a["fim"] == {"tipo": "relogio", "segundos_restantes": 45, "t_decorrido": 70}
    b = _fim(pg, "tr 2 segura o meio aos 0:45")[0]
    assert b["quando"] == {"tipo": "relogio", "segundos_restantes": 45, "t_decorrido": 70} and b["fim"] is None                  # "aos" é o início, como sempre
    c = _fim(pg, "tr 2 segura o meio aos 1:30 até 0:45")[0]
    assert c["quando"] == {"tipo": "relogio", "segundos_restantes": 90, "t_decorrido": 25} and c["fim"]["t_decorrido"] == 70      # início e fim na mesma frase
    assert _fim(pg, "tr 2 segura o meio até 0:45 aos 1:30")[0] == c                                                               # em qualquer ordem


@pytest.mark.parametrize("frase", ["tr 2 fica no meio até 0:45", "tr 2 holda o meio até 0:45", "tr 2 seguram o meio até 0:45", "TR 2 SEGURA O MEIO ATÉ 0:45", "tr 2 segurar o meio ate 0:45"])
def test_todos_os_jeitos_de_segurar_leem_o_ate_como_fim(pg, frase):
    a = _fim(pg, frase)[0]
    assert a["tipo"] == "segurar" and a["quando"] == {"tipo": "agora"} and a["fim"]["t_decorrido"] == 70


def test_segura_ate_nao_pergunta_o_inicio_e_o_comando_seguinte_parte_do_fim(pg):
    x = le(pg, "tr 2 segura o meio até 0:45")
    assert x["r"]["perguntas"] == []                                                                                              # o início é "agora": sem "Quando começa?"
    ac = _fim(pg, "tr 2 segura o meio até 0:45 e depois corre pra B")
    assert [a["tipo"] for a in ac] == ["segurar", "mover"] and ac[0]["quando"] == {"tipo": "agora"} and ac[1]["quando"] == {"tipo": "depois"}
    outra = _fim(pg, "tr 2 corre pra b aos 1:30 e depois segura o meio até 0:45")
    assert outra[0]["quando"]["t_decorrido"] == 25 and outra[1]["quando"] == {"tipo": "depois"} and outra[1]["fim"]["t_decorrido"] == 70   # depois do 1:30, até 0:45


def test_o_que_nao_e_segurar_nao_muda_esperar_ja_era_fim_e_mover_continua_inicio(pg):
    assert _fim(pg, "tr 2 espera até 0:45")[0]["quando"] == {"tipo": "espera_ate", "segundos_restantes": 45} and _fim(pg, "tr 2 espera até 0:45")[0]["fim"] is None
    m = _fim(pg, "tr 2 corre pro meio até 0:45")[0]
    assert m["tipo"] == "mover" and m["quando"]["t_decorrido"] == 70 and m["fim"] is None                                         # "corre até 0:45" é o início, como antes
    assert _fim(pg, "tr 2 anda até o meio aos 1:30")[0]["fim"] is None                                                           # "até o meio" é lugar


def test_o_fim_que_nao_existe_no_round_vira_pergunta_e_a_resposta_vale_como_fim(pg):
    r = pg.evaluate("""() => { const x = window.ctx; let l = ComandosDoReal.le("tr 2 segura o meio até 9:99", x); const antes = resumo(l);
        const h = LeitorDeComandos.horario("0:45", x); l = ComandosDoReal.responde(l, 0, { quando: h }, x); return { antes: antes, depois: resumo(l), fim: l.acoes[0].fim }; }""")
    assert [p["codigo"] for p in r["antes"]["perguntas"]] == ["horario_invalido"] and "não existe" in r["antes"]["perguntas"][0]["texto"]
    assert r["depois"]["perguntas"] == [] and r["fim"]["t_decorrido"] == 70


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# o Reescrever: os vereditos (o round 23 da match_43, "Reescrever daqui" em 1:20 = 35 s)
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def test_no_reescrever_o_inicio_e_o_instante_e_o_fim_decide_a_morte(pg):
    ok = ver(le(pg, "mezii segura a caverna até 0:45"))                                    # mezii morre aos 80,8 s; o fim é 70 s
    assert ok["codigo"] == "ok" and ok["aplica"] is True
    termina = ver(le(pg, "tr 5 segura o meio até 0:50"))                                   # ZywOo morre aos 62,3 s; o fim é 65 s: termina depois da morte
    assert termina["codigo"] == "termina_depois_da_morte" and termina["aplica"] is True and termina["botoes"] == []
    assert termina["esmaece_em_s"] == pytest.approx(62.3125, abs=0.001) and "termina depois disso" in termina["texto"]
    assert ver(le(pg, "tr 5 segura o meio até 0:56"))["codigo"] == "ok"                      # o fim, 59 s, vem antes da morte
    # "aos": o início, a regra de sempre
    assert ver(le(pg, "tr 5 segura o meio aos 0:50"))["codigo"] == "comeca_depois_da_morte"


def test_no_reescrever_o_fim_antes_do_instante_e_o_morto_ou_o_comeco_depois_da_morte_seguem_as_regras(pg):
    fim = ver(le(pg, "YEKINDAR segura o meio até 1:30"))                                   # o fim, 25 s, é antes do instante (35 s)
    assert fim["codigo"] == "fim_antes_do_instante" and fim["aplica"] is False and fim["botoes"] == ["Corrigir"]
    assert fim["texto"] == "O fim, 1:30, é antes de 1:20, onde a sua versão começa. Antes disso o real não muda."
    assert ver(le(pg, "flameZ segura o meio até 0:50"))["codigo"] == "ja_morto"             # já estava morto no instante
    assert ver(le(pg, "molodoy segura B aos 0:40"))["codigo"] == "comeca_depois_da_morte"   # começa depois da morte (aos = início)
    depois = pg.evaluate("""() => { const x = window.ctx, l = ComandosDoReal.le("mezii segura o meio até 0:45 e depois corre pra B", x); return vers(l, x).map(v => [v.acao, v.codigo]); }""")
    assert depois == [[0, "ok"], [1, "pendente"]]                                           # o segundo parte do fim do primeiro: o plano calcula
    ropz = pg.evaluate("""() => { const x = window.ctx, l = ComandosDoReal.le("ropz segura o meio até 0:45", x); return vers(l, x)[0].codigo; }""")
    assert ropz == "termina_depois_da_morte"                                                 # o ropz morre aos 0:49 (65,7 s): o fim, 0:45 (70 s), vem depois da morte dele


def test_no_reescrever_o_fim_depois_do_plant_pergunta_bomba_ou_round(pg):
    x = le(pg, "KSCERATO segura o meio até 0:30")
    p = x["r"]["perguntas"]
    assert len(p) == 1 and p[0]["codigo"] == "fim_relogio" and p[0]["texto"] == "0:30 é o relógio da bomba ou o do round?" and len(p[0]["opcoes"]) == 2
    for i, esperado in ((0, 89.55), (1, 85)):
        r = pg.evaluate("""(i) => { const x = window.ctx; let l = ComandosDoReal.le("KSCERATO segura o meio até 0:30", x); l = ComandosDoReal.responde(l, 0, l.perguntas[0].opcoes[i].valor, x);
            return { r: resumo(l), v: vers(l, x), fim: l.acoes[0].fim }; }""", i)
        assert r["r"]["perguntas"] == [] and r["fim"]["t_decorrido"] == pytest.approx(esperado, abs=0.001) and r["v"][0]["codigo"] == "ok"


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# a prancheta: o plano e o cartão
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def _caminho(pg):
    """Os pontos (t, x, y) do caminho da peça depois de aplicar, e o roteiro do cartão."""
    return interno(pg, "S.doc.operacoes.filter(o => o.tipo === 'cria_caminho').flatMap(o => (o.pontos || []).map(p => [p.t, p.x, p.y]))")


def _linhas(pg):
    return pg.locator("#pr-cmd-entendi li").all_inner_texts()


def test_na_prancheta_segura_ate_chega_e_fica_ate_H_e_o_cartao_diz_desde_quando(contexto, tmp_path_factory):
    base = _ponto("de_mirage", "Base TR")
    meio = _ponto("de_mirage", "Meio")
    pg = _pagina_da_prancheta(contexto, tmp_path_factory)
    _peca(pg, base["x"], base["y"])
    _escreve(pg, "tr 2 segura o meio até 0:45")
    linha = _linhas(pg)[0]
    assert linha.startswith("TR 2 · segura Meio · desde 1:55 · até 0:45"), linha                        # o marcador do tempo está em 0: "desde agora" = o início do round
    _aplica(pg)
    pts = _caminho(pg)
    assert pts[-1][0] == 70 and (pts[-1][1], pts[-1][2]) == (meio["x"], meio["y"])                   # a última parada é o fim, no meio
    assert pts[-2][0] < 70 and (pts[-2][1], pts[-2][2]) == (meio["x"], meio["y"])                    # a anterior é a chegada, no mesmo lugar: a peça fica


def test_na_prancheta_desde_agora_e_o_marcador_do_tempo(contexto, tmp_path_factory):
    base = _ponto("de_mirage", "Base TR")
    pg = _pagina_da_prancheta(contexto, tmp_path_factory)
    _peca(pg, base["x"], base["y"])
    interno(pg, "I.defineTempo(20)")                                                                  # o marcador em 20 s do início (1:35 no relógio)
    _escreve(pg, "tr 2 segura o meio até 0:45")
    assert _linhas(pg)[0].startswith("TR 2 · segura Meio · desde 1:35 · até 0:45"), _linhas(pg)


def test_na_prancheta_aos_continua_sendo_o_inicio_e_o_ate_pode_vir_junto(contexto, tmp_path_factory):
    base = _ponto("de_mirage", "Base TR")
    pg = _pagina_da_prancheta(contexto, tmp_path_factory)
    _peca(pg, base["x"], base["y"])
    _escreve(pg, "tr 2 segura o meio aos 0:45")
    assert _linhas(pg)[0].startswith("TR 2 · segura Meio · aos 0:45") and "até" not in _linhas(pg)[0].split("aos 0:45")[0], _linhas(pg)       # o início é 0:45
    _aplica(pg)
    assert min(t for t, _, _ in _caminho(pg) if t > 0) >= 70                                          # a peça só sai às 0:45 (70 s)
    pg2 = _pagina_da_prancheta(contexto, tmp_path_factory)
    _peca(pg2, base["x"], base["y"])
    _escreve(pg2, "tr 2 segura o meio aos 1:30 até 0:45")
    assert _linhas(pg2)[0].startswith("TR 2 · segura Meio · aos 1:30 · chega") or "aos 1:30" in _linhas(pg2)[0]
    assert "até 0:45" in _linhas(pg2)[0]
    _aplica(pg2)
    assert _caminho(pg2)[-1][0] == 70 and _caminho(pg2)[0][0] >= 24.9                                  # parte aos 25 s (1:30) e fica até 70 s (0:45)


def test_na_prancheta_o_comando_seguinte_parte_do_fim_da_espera(contexto, tmp_path_factory):
    base = _ponto("de_mirage", "Base TR")
    pg = _pagina_da_prancheta(contexto, tmp_path_factory)
    _peca(pg, base["x"], base["y"])
    _escreve(pg, "tr 2 segura o meio até 0:45 e depois corre pra B")
    linhas = _linhas(pg)
    assert linhas[0].startswith("TR 2 · segura Meio · desde 1:55 · até 0:45") and "depois, por volta de 0:45" in linhas[1], linhas      # o segundo parte de 0:45
    _aplica(pg)
    pts = _caminho(pg)
    assert any(abs(t - 70) < 0.01 for t, _, _ in pts) and pts[-1][0] > 70                              # fica até 70 s e então segue para o B


def test_na_prancheta_o_fim_que_vem_antes_da_chegada_avisa_e_nao_segura(contexto, tmp_path_factory):
    base = _ponto("de_mirage", "Base TR")
    pg = _pagina_da_prancheta(contexto, tmp_path_factory)
    _peca(pg, base["x"], base["y"])
    _escreve(pg, "tr 2 segura o meio aos 1:50 até 1:49")                                              # começa aos 5 s e o "até" vem 1 s depois: não dá tempo de chegar
    avisos = pg.locator(".pr-cmd-aviso").all_inner_texts()
    assert any("não deixa tempo de segurar" in a for a in avisos), avisos
    _aplica(pg)
    assert _caminho(pg)[-1][0] < 71                                                                    # nenhum ponto de espera até 1:49 foi criado


def test_no_reescrever_inicio_e_fim_depois_do_plant_perguntam_bomba_ou_round_uma_vez_so(pg):
    frase = "KSCERATO segura o meio aos 0:35 até 0:30"
    x = le(pg, frase)
    assert len(x["r"]["perguntas"]) == 1 and x["r"]["perguntas"][0]["codigo"] == "quando"
    for i in (0, 1):
        r = pg.evaluate("""([f, i]) => { const x = window.ctx; let l = ComandosDoReal.le(f, x); l = ComandosDoReal.responde(l, 0, l.perguntas[0].opcoes[i].valor, x);
            return { perguntas: l.perguntas.length, q: l.acoes[0].quando, f: l.acoes[0].fim }; }""", [frase, i])
        assert r["perguntas"] == 0 and r["q"]["base"] == r["f"]["base"] == ("bomba", "round")[i]                      # a mesma base para os dois
        assert r["f"]["t_decorrido"] > r["q"]["t_decorrido"]


def test_na_prancheta_agora_e_o_fim_do_comando_anterior_da_mesma_peca(contexto, tmp_path_factory):
    base = _ponto("de_mirage", "Base TR")
    pg = _pagina_da_prancheta(contexto, tmp_path_factory)
    _peca(pg, base["x"], base["y"])
    _escreve(pg, "tr 2 corre pro meio aos 1:30. tr 2 segura o meio até 0:45")
    linhas = _linhas(pg)
    assert len(linhas) == 2 and "aos 1:30" in linhas[0] and "desde 1:30" not in linhas[1] and "até 0:45" in linhas[1], linhas
    import re
    chegada = re.search(r"por volta de (\d+:\d\d)", linhas[0]).group(1)                           # onde o primeiro comando termina
    assert f"desde {chegada}" in linhas[1], linhas                                                           # o segundo começa aí, não no marcador (1:55)
    _aplica(pg)
    assert _caminho(pg)[-1][0] == 70 and len({(x, y) for t, x, y in _caminho(pg) if t > 30}) == 1                  # chega ao meio, fica lá até 70 s: um lugar só
    # outra peça no meio: o "agora" continua sendo o fim do comando da MESMA peça
    _escreve(pg, "tr 2 corre pro meio aos 1:30. tr 3 corre pra b aos 1:00. tr 2 segura o meio até 0:45")
    l3 = _linhas(pg)
    assert len(l3) == 3 and f"desde {chegada}" in l3[2], l3
