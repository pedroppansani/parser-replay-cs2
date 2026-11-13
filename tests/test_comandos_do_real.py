"""CR1c: o leitor com os nicks e as regras do round real (`comandos/leitor.js` + `comandos/real.js`), SEM tela. Os 10 exemplos do round 23 da match_43 (Mirage; "Reescrever daqui"
em 1:20, o quadro 140), as duas mortes (começa depois = recusado; termina depois = aplicado e a peça esmaece), as regras de nick (caixa e acento, parcial com 4 letras ou mais e
sem ambiguidade, parcial ambíguo pergunta, nick que também é lugar pergunta) e a pergunta "bomba ou round?" só depois do plant."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_tactics_browser import navegador  # noqa: E402,F401  (fixture)

RAIZ = Path(__file__).resolve().parent.parent
WEB = RAIZ / "dashboard" / "web"
PARTIDA, ROUND, T0 = "match_43", 23, 140          # 1:20 no relógio do round (35 s do início)

# o que o teste lê de uma leitura: o suficiente para conferir, sem os objetos internos
AJUDAS = """
window.resumo = (l) => ({ ok: l.ok, perguntas: l.perguntas.map(p => ({ codigo: p.codigo, texto: p.texto, acao: p.acao, opcoes: (p.opcoes || []).map(o => o.rotulo) })),
  acoes: l.acoes.map(a => ({ tipo: a.tipo, granada: a.granada, alvo: a.alvo ? (a.alvo.nome || a.alvo.tipo) : null, quando: a.quando, duracao_s: a.duracao_s, espera_s: a.espera_s,
    quem: a.quem.map(q => ({ lado: q.lado, num: q.num, nick: q.nick || null, resolvido: !!q.resolvido, candidatos: (q.candidatos || []).length })) })),
  naoEntendido: l.naoEntendido.map(x => x.trecho) });
window.vers = (l, ctx, fins) => ComandosDoReal.veredictos(l, ctx, fins).map(v => ({ acao: v.acao, nick: v.nick || null, codigo: v.codigo, aplica: v.aplica, texto: v.texto, botoes: v.botoes.map(b => b.rotulo), botoesCodigo: v.botoes.map(b => b.codigo),
  esmaece_em_s: v.esmaece_em_s === undefined ? null : v.esmaece_em_s, morte: v.morte || null }));
window.comNicks = (trocas) => { const c = JSON.parse(JSON.stringify(window.ctx)); c.jogadores.forEach(j => { if (trocas[j.nick]) j.nick = trocas[j.nick]; }); return c; };
"""


def _dados(mapa="de_mirage"):
    from scripts.comandos_contexto import contexto_do_real
    R = json.loads((RAIZ / "data" / "processed" / PARTIDA / "replay.json").read_text(encoding="utf-8"))
    r = next(x for x in R["rounds"] if x["round"] == ROUND)
    fino = {"players": [{"name": p["name"], "side": p["side"], "alive": p["alive"]} for p in r["players"]], "events": r["events"]}
    return {"ctx": contexto_do_real(mapa), "round": fino, "R": {"sample_hz": R["sample_hz"], "clock": R["clock"]}, "t0": T0}


@pytest.fixture(scope="module")
def pg(navegador):
    if not (RAIZ / "data" / "processed" / PARTIDA / "replay.json").exists():
        pytest.skip("sem o processado")
    pg = navegador.new_page()
    pg.set_content("<!doctype html><meta charset=utf-8>")
    for f in ("map_core.js", "comandos/leitor.js", "comandos/real.js"):
        pg.add_script_tag(path=str(WEB / f))
    pg.add_script_tag(content=AJUDAS)
    pg.evaluate("d => { window.D = d; window.ctx = ComandosDoReal.contexto(d.ctx, d.round, d.t0, d.R); }", _dados())
    yield pg
    pg.close()


def le(pg, frase, ctx="ctx", fins=None):
    """A leitura, o resumo dela e os vereditos (`fins`: o fim de cada ação, em s do início, que o plano calcularia)."""
    return pg.evaluate("([f, c, fins]) => { const x = window[c]; const l = ComandosDoReal.le(f, x); return { r: resumo(l), v: vers(l, x, fins || {}) }; }", [frase, ctx, fins])


def ver(r):
    return r["v"][0]


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# os 10 exemplos do round 23 (a CR0, item 10)
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def test_o_elenco_vem_do_round_na_ordem_das_colunas_e_marca_quem_ja_morreu(pg):
    j = pg.evaluate("window.ctx.jogadores.map(j => [j.lado + j.num, j.nick, j.vivo, j.morreu_s === null ? null : Math.round(j.morreu_s * 100) / 100, j.matador])")
    por = {x[0]: x for x in j}
    assert [por[f"tr{i}"][1] for i in range(1, 6)] == ["mezii", "ropz", "apEX", "flameZ", "ZywOo"]
    assert [por[f"ct{i}"][1] for i in range(1, 6)] == ["molodoy", "FalleN", "KSCERATO", "yuurih", "YEKINDAR"]
    assert por["tr4"][2] is False and por["tr4"][4] == "YEKINDAR" and abs(por["tr4"][3] - 12.55) < 0.01        # flameZ já estava morto no instante
    assert por["tr5"][2] is True and por["tr5"][4] == "molodoy" and abs(por["tr5"][3] - 62.31) < 0.01          # ZywOo morre depois, para molodoy
    assert por["ct2"][2] is True and por["ct2"][3] is None                                                      # FalleN vive o round inteiro
    assert pg.evaluate("window.ctx.real") == {"t0_f": 140, "t0_s": 35, "hz": 4, "segundos_do_round": 115, "bomba_s": 40, "plant_s": pytest.approx(79.547, abs=0.001)}


def test_exemplo_1_zywoo_roda_pra_b_aos_0_50_e_recusado_porque_a_morte_dele_vem_antes(pg):
    x = le(pg, "ZywOo roda pra B aos 0:50")
    a = x["r"]["acoes"][0]
    assert a["tipo"] == "mover" and a["alvo"] == "B" and a["quando"]["t_decorrido"] == 65 and a["quem"] == [{"lado": "tr", "num": 5, "nick": "ZywOo", "resolvido": True, "candidatos": 1}]
    v = ver(x)
    assert v["codigo"] == "comeca_depois_da_morte" and v["aplica"] is False
    assert "morreu para molodoy às 0:52" in v["texto"] and "começa às 0:50" in v["texto"] and "o site não refaz esse duelo" in v["texto"]
    assert v["botoes"] == ["Escolher outro jogador", "Corrigir"] and v["botoesCodigo"] == ["outro_jogador", "corrigir"]       # e não "Usar a hora da morte"


def test_exemplo_2_o_4_sem_lado_sempre_pergunta_com_nick_e_vida_nos_botoes(pg):
    x = le(pg, "o 4 joga smoke no janelão aos 1:05")
    p = x["r"]["perguntas"]
    assert len(p) == 1 and p[0]["codigo"] == "quem_lado" and p[0]["texto"] == 'De qual time é "o 4"?'
    assert p[0]["opcoes"] == ["yuurih · CT 4", "flameZ · TR 4, morto às 1:42, antes de 1:20"]                              # o morto aparece, com a vida; escolher é com o jogador
    assert ver(x)["codigo"] == "pendente"                                                                                   # nada se decide enquanto há pergunta
    # respondendo yuurih (vivo até 0:56): o horário 1:05 é antes da morte dele: nenhuma regra do real o impede (a granada que ele não jogou é a CR3)
    r = pg.evaluate("""() => { const x = window.ctx; let l = ComandosDoReal.le("o 4 joga smoke no janelão aos 1:05", x);
        l = ComandosDoReal.responde(l, 0, { lado: "ct", num: 4 }, x); return { r: resumo(l), v: vers(l, x) }; }""")
    assert r["r"]["perguntas"] == [] and r["v"][0]["codigo"] == "ok" and r["v"][0]["nick"] == "yuurih"
    r = pg.evaluate("""() => { const x = window.ctx; let l = ComandosDoReal.le("o 4 joga smoke no janelão aos 1:05", x);
        l = ComandosDoReal.responde(l, 0, { lado: "t", num: 4 }, x); return { r: resumo(l), v: vers(l, x) }; }""")
    assert r["v"][0]["codigo"] == "pendente"                                                                                  # "t" não é um lado do leitor: a resposta tem que ser tr
    r = pg.evaluate("""() => { const x = window.ctx; let l = ComandosDoReal.le("o 4 joga smoke no janelão aos 1:05", x);
        l = ComandosDoReal.responde(l, 0, { lado: "tr", num: 4 }, x); return { v: vers(l, x) }; }""")
    assert r["v"][0]["codigo"] == "ja_morto" and r["v"][0]["nick"] == "flameZ"                                               # flameZ já estava morto no instante


def test_exemplo_3_fallen_joga_smoke_no_janelao_e_lido_sem_pergunta_no_mirage(pg):
    x = le(pg, "FalleN joga smoke no janelão aos 0:57")
    a = x["r"]["acoes"][0]
    assert x["r"]["perguntas"] == [] and a["tipo"] == "lancar" and a["granada"] == "smoke" and a["alvo"] == "Janelão" and a["quando"]["t_decorrido"] == 58
    assert a["quem"] == [{"lado": "ct", "num": 2, "nick": "FalleN", "resolvido": True, "candidatos": 1}]                      # no Mirage "FalleN" não é lugar: sem pergunta
    assert ver(x)["codigo"] == "ok"                                                                                          # a granada (só trocar uma que ele jogou) é a CR3


def test_exemplo_4_ropz_e_apex_correm_pro_meio_aos_1_10(pg):
    x = le(pg, "ropz e apEX correm pro meio aos 1:10")
    a = x["r"]["acoes"][0]
    assert a["tipo"] == "mover" and a["alvo"] == "Meio" and a["quando"]["t_decorrido"] == 45
    assert [(q["lado"], q["num"], q["nick"]) for q in a["quem"]] == [("tr", 2, "ropz"), ("tr", 3, "apEX")]
    assert [(v["nick"], v["codigo"]) for v in x["v"]] == [("ropz", "ok"), ("apEX", "ok")]


def test_exemplo_5_mezii_segura_a_caverna_ate_0_45(pg):
    # CR1d (decisão do Pedro): "até" é o FIM. Antes: o horário 0:45 (70 s) era o INÍCIO do comando (`quando` = relógio 70). Agora: o início é "agora" (o instante, 1:20) e o fim é 0:45.
    x = le(pg, "mezii segura a caverna até 0:45")
    a = x["r"]["acoes"][0]
    assert a["tipo"] == "segurar" and a["alvo"] == "Caverna" and a["quando"] == {"tipo": "agora"}
    assert pg.evaluate("""() => ComandosDoReal.le("mezii segura a caverna até 0:45", window.ctx).acoes[0].fim.t_decorrido""") == 70
    assert ver(x)["codigo"] == "ok" and ver(x)["nick"] == "mezii"                                                              # o fim, 70 s, vem antes da morte dele (80,8 s)


def test_exemplo_6_ropz_vai_pro_b_e_depois_pro_meio_pergunta_o_horario_com_o_botao_no_instante(pg):
    x = le(pg, "ropz vai pro B e depois pro meio")
    assert [p["codigo"] for p in x["r"]["perguntas"]] == ["quando", "acao"]
    assert x["r"]["perguntas"][0]["opcoes"] == ["No instante (1:20)"] and x["r"]["perguntas"][0]["texto"] == 'Quando começa "ropz vai pro B"?'
    assert x["r"]["perguntas"][1]["opcoes"] == ["Mover até Meio", "Segurar Meio"]                                              # "pro meio" sem verbo: limite do leitor, pergunta
    r = pg.evaluate("""() => { const x = window.ctx; let l = ComandosDoReal.le("ropz vai pro B e depois pro meio", x);
        l = ComandosDoReal.responde(l, 0, l.perguntas[0].opcoes[0].valor, x); l = ComandosDoReal.responde(l, 0, { tipo: "mover" }, x);
        return { r: resumo(l), v: vers(l, x) }; }""")
    assert r["r"]["perguntas"] == [] and r["r"]["acoes"][0]["quando"]["t_decorrido"] == 35                                      # no instante: 35 s do início
    assert r["v"][0]["codigo"] == "ok"


def test_exemplo_7_yekindar_aos_1_30_vem_antes_do_instante_e_o_botao_comeca_em_1_20(pg):
    x = le(pg, "YEKINDAR corre pro meio aos 1:30")
    v = ver(x)
    assert v["codigo"] == "antes_do_instante" and v["aplica"] is False and v["nick"] == "YEKINDAR"
    assert v["texto"] == "1:30 é antes de 1:20, onde a sua versão começa. Antes disso o real não muda."
    assert v["botoes"] == ["Começar em 1:20", "Corrigir"] and v["botoesCodigo"] == ["comecar_em", "corrigir"]
    r = pg.evaluate("""() => { const x = window.ctx; let l = ComandosDoReal.le("YEKINDAR corre pro meio aos 1:30", x);
        l = ComandosDoReal.comecarNoInstante(l, 0, x); return { r: resumo(l), v: vers(l, x) }; }""")
    assert r["r"]["acoes"][0]["quando"]["t_decorrido"] == 35 and r["v"][0]["codigo"] == "ok"                                    # [Começar em 1:20]


def test_exemplo_8_flamez_ja_estava_morto_no_instante_so_existe_no_real(pg):
    x = le(pg, "flameZ roda pra A aos 1:15")
    v = ver(x)
    assert v["codigo"] == "ja_morto" and v["aplica"] is False and v["botoes"] == ["Escolher outro jogador", "Corrigir"]
    assert "morreu para YEKINDAR às 1:42, antes de 1:20" in v["texto"] and "o site não refaz esse duelo" in v["texto"]
    # [Escolher outro jogador]: o flameZ sai do comando e a pergunta "quem?" volta com todos os rótulos
    r = pg.evaluate("""() => { const x = window.ctx; let l = ComandosDoReal.le("flameZ roda pra A aos 1:15", x);
        l = ComandosDoReal.escolherOutro(l, 0, { lado: "tr", num: 4 }, x);
        const antes = { r: resumo(l), v: vers(l, x) };
        l = ComandosDoReal.responde(l, 0, { lado: "tr", num: 2 }, x);
        return { antes: antes, v: vers(l, x), r: resumo(l) }; }""")
    assert r["antes"]["r"]["perguntas"][0]["codigo"] == "quem" and len(r["antes"]["r"]["perguntas"][0]["opcoes"]) == 10
    assert "flameZ · TR 4, morto às 1:42, antes de 1:20" in r["antes"]["r"]["perguntas"][0]["opcoes"] and r["antes"]["v"][0]["codigo"] == "pendente"
    assert r["r"]["perguntas"] == [] and r["v"][0]["nick"] == "ropz" and r["v"][0]["codigo"] == "ok"


def test_exemplo_9_molodoy_aos_0_40_comeca_depois_da_morte_dele(pg):
    x = le(pg, "molodoy corre pro B aos 0:40")
    v = ver(x)
    assert v["codigo"] == "comeca_depois_da_morte" and v["aplica"] is False and v["botoes"] == ["Escolher outro jogador", "Corrigir"]
    assert "morreu para apEX às 0:47" in v["texto"] and "começa às 0:40" in v["texto"]


def test_exemplo_10_kscerato_aos_0_30_depois_do_plant_pergunta_bomba_ou_round(pg):
    x = le(pg, "KSCERATO corre pro meio aos 0:30")
    p = x["r"]["perguntas"]
    assert len(p) == 1 and p[0]["texto"] == "0:30 é o relógio da bomba ou o do round?"
    assert p[0]["opcoes"] == ["Relógio da bomba: 0:30, 10 s depois do plant (89,6 s do início)", "Relógio do round: 0:30 (85 s do início)"]
    assert ver(x)["codigo"] == "pendente"
    for i, esperado, base in ((0, 89.55, "bomba"), (1, 85, "round")):
        r = pg.evaluate("""(i) => { const x = window.ctx; let l = ComandosDoReal.le("KSCERATO corre pro meio aos 0:30", x);
            l = ComandosDoReal.responde(l, 0, l.perguntas[0].opcoes[i].valor, x); return { r: resumo(l), v: vers(l, x), base: l.acoes[0].quando.base }; }""", i)
        assert r["r"]["perguntas"] == [] and r["r"]["acoes"][0]["quando"]["t_decorrido"] == pytest.approx(esperado, abs=0.001) and r["base"] == base and r["v"][0]["codigo"] == "ok"


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# a pergunta "bomba ou round?" só depois do plant
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("horario,pergunta", [
    ("1:10", False), ("0:50", False), ("0:38", False),     # antes do plant (o plant foi aos 79,5 s: 0:35 no relógio do round): o horário é o do round
    ("0:35", False),                                       # 80 s do início: o relógio do round dá 0:35 e ainda é depois do plant? 115 - 35 = 80 > 79,55: pergunta
    ("0:30", True), ("0:10", True), ("0:00", True),
])
def test_a_pergunta_so_aparece_quando_o_horario_escrito_cai_depois_do_plant(pg, horario, pergunta):
    if horario == "0:35":
        pergunta = True          # 115 - 35 = 80 s > 79,547 s do plant: já é depois dele
    x = le(pg, f"KSCERATO corre pro meio aos {horario}")
    assert any(p["texto"].endswith("é o relógio da bomba ou o do round?") for p in x["r"]["perguntas"]) is pergunta, (horario, x["r"]["perguntas"])


def test_horario_digitado_sozinho_pergunta_do_mesmo_jeito_e_segundos_do_inicio_nao(pg):
    r = pg.evaluate("""() => { const x = window.ctx; return [ComandosDoReal.horario("0:30", x), ComandosDoReal.horario("1:10", x), ComandosDoReal.horario("85 s do início", x)]; }""")
    assert r[0]["ambiguo_relogio"] is True and [o["valor"]["quando"]["base"] for o in r[0]["pergunta"]["opcoes"]] == ["bomba", "round"]
    assert r[1] == {"tipo": "relogio", "segundos_restantes": 70, "t_decorrido": 45}
    assert r[2] == {"tipo": "inicio", "segundos": 85, "t_decorrido": 85}                                                      # "do início" já diz a base: sem pergunta


def test_o_relogio_do_real_js_e_o_do_map_core_em_todo_o_round(pg):
    dif = pg.evaluate("""() => { const x = window.ctx, r = x.real, ruins = [];
        for (let t = 0; t <= 110; t += 0.37) { const a = ComandosDoReal.relogioNa(r, t), b = MapCore.relogio(t, r.plant_s, null, r.segundos_do_round, r.bomba_s); if (a !== b) ruins.push([t, a, b]); }
        return ruins; }""")
    assert dif == [], dif[:5]


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# as duas mortes: "começa depois" (recusado) e "termina depois" (aplicado, a peça esmaece na hora da morte real)
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def test_comeca_depois_da_morte_e_recusado_e_o_de_antes_da_morte_nao(pg):
    antes = ver(le(pg, "ZywOo corre pro B aos 0:56"))             # 59 s: ZywOo morre aos 62,3 s
    assert antes["codigo"] == "ok" and antes["aplica"] is True
    depois = ver(le(pg, "ZywOo corre pro B aos 0:52"))            # 63 s, depois dos 62,3 s
    assert depois["codigo"] == "comeca_depois_da_morte" and depois["aplica"] is False and depois["botoesCodigo"] == ["outro_jogador", "corrigir"]
    assert depois["morte"]["h"] == "0:52" and depois["morte"]["matador"] == "molodoy"


def test_termina_depois_da_morte_e_aplicado_a_peca_esmaece_na_hora_da_morte_com_o_aviso(pg):
    # o plano entrega o fim do comando: ZywOo começa aos 0:56 (59 s) e só chega aos 66 s, depois dos 62,3 s da morte dele no real
    v = ver(le(pg, "ZywOo corre pro B aos 0:56", fins={"0": 66}))
    assert v["codigo"] == "termina_depois_da_morte" and v["aplica"] is True and v["botoes"] == []                              # aplicado: nenhum botão de recusa
    assert v["esmaece_em_s"] == pytest.approx(62.3125, abs=0.001) and v["morte"]["matador"] == "molodoy"
    assert "termina depois disso" in v["texto"] and "anda até a hora da morte e esmaece ali" in v["texto"] and "o site não refaz esse duelo" in v["texto"]
    assert "começa" not in v["texto"]                                                                                          # não se confunde com a recusa
    # se o comando termina ANTES da morte, é só ok
    assert ver(le(pg, "ZywOo corre pro B aos 0:56", fins={"0": 61}))["codigo"] == "ok"


def test_os_dois_vereditos_de_morte_sao_inconfundiveis(pg):
    recusa = ver(le(pg, "ZywOo corre pro B aos 0:52"))
    aviso = ver(le(pg, "ZywOo corre pro B aos 0:56", fins={"0": 66}))
    assert (recusa["codigo"], recusa["aplica"], recusa["botoes"]) == ("comeca_depois_da_morte", False, ["Escolher outro jogador", "Corrigir"])
    assert (aviso["codigo"], aviso["aplica"], aviso["botoes"]) == ("termina_depois_da_morte", True, [])
    assert recusa["texto"] != aviso["texto"] and recusa["esmaece_em_s"] is None and aviso["esmaece_em_s"] is not None
    sem_matador = pg.evaluate("""() => { const x = JSON.parse(JSON.stringify(window.ctx)); x.jogadores.find(j => j.nick === "ZywOo").matador = null;
        return [vers(ComandosDoReal.le("ZywOo corre pro B aos 0:52", x), x), vers(ComandosDoReal.le("ZywOo corre pro B aos 0:56", x), x, { 0: 66 })].map(v => v[0].texto); }""")
    assert "No real, ZywOo morreu às 0:52. O comando começa às 0:52" in sem_matador[0] and "para" not in sem_matador[0].split("morreu")[1].split(".")[0] and "refaz essa morte" in sem_matador[0]
    assert "morreu às 0:52. O comando termina depois disso" in sem_matador[1] and "refaz essa morte" in sem_matador[1]


def test_o_fim_que_o_proprio_comando_diz_decide_o_termina_depois(pg):
    # mezii morre aos 80,8 s (0:34, no relógio da bomba)
    em8 = ver(le(pg, "mezii corre pro meio aos 0:40 em 8 s"))           # 75 + 8 = 83 > 80,8
    em5 = ver(le(pg, "mezii corre pro meio aos 0:40 em 5 s"))           # 75 + 5 = 80 < 80,8
    assert em8["codigo"] == "termina_depois_da_morte" and em8["aplica"] is True and em5["codigo"] == "ok"
    espera = ver(le(pg, "mezii espera 8 segundos aos 0:40"))
    assert espera["codigo"] == "termina_depois_da_morte" and ver(le(pg, "mezii espera 3 segundos aos 0:40"))["codigo"] == "ok"
    assert ver(le(pg, "mezii corre pro meio aos 0:40"))["codigo"] == "ok"                                                       # sem fim conhecido o plano é quem diz (a CR2 repete a conta)


def test_o_comeca_depois_ganha_do_termina_depois_e_o_ja_morto_ganha_do_antes_do_instante(pg):
    assert ver(le(pg, "ZywOo corre pro B aos 0:52", fins={"0": 99}))["codigo"] == "comeca_depois_da_morte"
    assert ver(le(pg, "flameZ roda pra A aos 1:30"))["codigo"] == "ja_morto"                                                    # 1:30 também é antes do instante, mas ele já morreu


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# as regras de nick da CR0
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def _quem(x):
    return [(q["lado"], q["num"], q["nick"]) for q in x["r"]["acoes"][0]["quem"]]


@pytest.mark.parametrize("escrito", ["ZywOo", "zywoo", "ZYWOO", "ZyWoO"])
def test_o_nick_vale_sem_diferenciar_maiuscula_e_minuscula(pg, escrito):
    x = le(pg, f"{escrito} corre pro meio aos 1:10")
    assert x["r"]["perguntas"] == [] and _quem(x) == [("tr", 5, "ZywOo")]


@pytest.mark.parametrize("escrito", ["joao", "JOAO", "João", "JOÃO", "joão"])
def test_o_nick_vale_sem_diferenciar_acento(pg, escrito):
    pg.evaluate("() => { window.ctxA = comNicks({ molodoy: 'João' }); }")
    x = le(pg, f"{escrito} corre pro meio aos 1:10", ctx="ctxA")
    assert x["r"]["perguntas"] == [] and _quem(x) == [("ct", 1, "João")]


@pytest.mark.parametrize("escrito,esperado", [("zywo", "ZywOo"), ("yeki", "YEKINDAR"), ("kscer", "KSCERATO"), ("MODO", None), ("falle", "FalleN"), ("moloD", "molodoy")])
def test_o_nick_parcial_vale_com_4_letras_ou_mais_se_for_unico(pg, escrito, esperado):
    x = le(pg, f"{escrito} corre pro meio aos 1:10")
    if esperado is None:
        assert x["r"]["acoes"][0]["quem"] == [] or all(not q["resolvido"] for q in x["r"]["acoes"][0]["quem"])        # "modo" é prefixo de nenhum nick: não adivinha
    else:
        assert x["r"]["perguntas"] == [] and [q[2] for q in _quem(x)] == [esperado]


@pytest.mark.parametrize("escrito", ["zyw", "mez", "ker", "yek", "fal"])
def test_o_parcial_de_3_letras_ou_menos_nao_vale_nunca(pg, escrito):
    x = le(pg, f"{escrito} corre pro meio aos 1:10")
    assert [p["codigo"] for p in x["r"]["perguntas"]] == ["quem"] and x["r"]["acoes"][0]["quem"] == []                         # pergunta quem; nada foi adivinhado
    assert x["r"]["naoEntendido"] == [escrito]                                                                                  # a palavra fica como "não entendida"


def test_o_nick_parcial_ambiguo_vira_pergunta_com_os_nicks_nos_botoes(pg):
    pg.evaluate("() => { window.ctxB = comNicks({ ropz: 'Spirit1', apEX: 'Spirit2' }); }")
    x = le(pg, "spir corre pro meio aos 1:10", ctx="ctxB")
    p = x["r"]["perguntas"]
    assert len(p) == 1 and p[0]["codigo"] == "quem_lado" and p[0]["opcoes"] == ["Spirit1 · TR 2", "Spirit2 · TR 3"]            # os dois, com o nick: a pessoa escolhe
    assert ver(x)["codigo"] == "pendente"
    r = pg.evaluate("""() => { const x = window.ctxB; let l = ComandosDoReal.le("spir corre pro meio aos 1:10", x); l = ComandosDoReal.responde(l, 0, { lado: "tr", num: 3 }, x); return { v: vers(l, x), r: resumo(l) }; }""")
    assert r["r"]["perguntas"] == [] and (r["v"][0]["nick"], r["v"][0]["codigo"]) == ("Spirit2", "ok")
    # o nick inteiro ganha do parcial: "Spirit1" escrito por inteiro não pergunta
    assert _quem(le(pg, "spirit1 corre pro meio aos 1:10", ctx="ctxB")) == [("tr", 2, "Spirit1")]


def test_o_nick_inteiro_ganha_do_parcial_de_outro_nick(pg):
    pg.evaluate("() => { window.ctxC = comNicks({ ropz: 'Kray', apEX: 'Krayzie' }); }")
    assert _quem(le(pg, "kray corre pro meio aos 1:10", ctx="ctxC")) == [("tr", 2, "Kray")]                                    # "kray" é um nick inteiro: sem pergunta
    x = le(pg, "krayz corre pro meio aos 1:10", ctx="ctxC")
    assert _quem(x) == [("tr", 3, "Krayzie")] and x["r"]["perguntas"] == []                                                      # e "krayz" só pode ser o Krayzie


def test_o_parcial_nao_vale_se_for_palavra_do_leitor_ou_nome_de_lugar(pg):
    pg.evaluate("() => { window.ctxD = comNicks({ ropz: 'MolO11', apEX: 'Meiozin' }); }")
    molo = le(pg, "molo11 corre pro meio aos 1:10", ctx="ctxD")
    assert _quem(molo) == [("tr", 2, "MolO11")] and molo["r"]["perguntas"] == []                                                # o nick inteiro vale (molo11)
    granada = le(pg, "tr 3 joga molo no meio aos 1:10", ctx="ctxD")
    assert granada["r"]["acoes"][0]["granada"] == "molotov" and _quem(granada) == [("tr", 3, "Meiozin")]                       # "molo" sozinho é a granada, não o MolO11
    meio = le(pg, "tr 3 corre pro meio aos 1:10", ctx="ctxD")
    assert meio["r"]["acoes"][0]["alvo"] == "Meio" and _quem(meio) == [("tr", 3, "Meiozin")]                                    # "meio" é o lugar, não o Meiozin


def test_nick_com_numero_e_hifen_vale_com_ou_sem_espaco(pg):
    pg.evaluate("() => { window.ctxE = comNicks({ ropz: 'donk666', apEX: 's-chilla' }); }")
    for frase in ("donk666 corre pro meio aos 1:10", "DONK 666 corre pro meio aos 1:10"):
        assert _quem(le(pg, frase, ctx="ctxE")) == [("tr", 2, "donk666")]
    assert _quem(le(pg, "s-chilla corre pro meio aos 1:10", ctx="ctxE")) == [("tr", 3, "s-chilla")]
    assert _quem(le(pg, "s chilla corre pro meio aos 1:10", ctx="ctxE")) == [("tr", 3, "s-chilla")]


def test_o_4_sem_lado_pergunta_sempre_mesmo_com_nicks(pg):
    for frase in ("o 4 corre pro meio aos 1:10", "jogador 4 corre pro meio aos 1:10"):
        x = le(pg, frase)
        assert [p["codigo"] for p in x["r"]["perguntas"]] == ["quem_lado"], frase
    assert le(pg, "ct 4 corre pro meio aos 1:10")["r"]["perguntas"] == []                                                       # com o lado: sem pergunta
    assert _quem(le(pg, "tr 2 corre pro meio aos 1:10")) == [("tr", 2, "ropz")]                                                 # "TR 2" é a posição na coluna, e o nick aparece na leitura


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# o nick que também é lugar do mapa (Dust2: "Fallen" e "Niko" são pontos do Pedro) SEMPRE pergunta
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def dust2(pg):
    pg.evaluate("d => { window.ctxDust = ComandosDoReal.contexto(d.ctx, d.round, d.t0, d.R); window.ctxDustNiko = (() => { const c = JSON.parse(JSON.stringify(window.ctxDust)); c.jogadores.find(j => j.nick === 'ropz').nick = 'NiKo'; return c; })(); }", _dados("de_dust2"))
    return pg


def test_nick_que_tambem_e_lugar_pergunta_antes_de_ler_o_resto_e_a_decisao_vale(dust2):
    pg = dust2
    x = le(pg, "FalleN corre pro meio aos 1:10", ctx="ctxDust")
    p = x["r"]["perguntas"]
    assert x["r"]["acoes"] == [] and len(p) == 1 and p[0]["codigo"] == "quem_ou_lugar" and p[0]["texto"] == '"FalleN" é o jogador ou o lugar do mapa?'
    assert p[0]["opcoes"] == ["FalleN, o jogador (CT 2)", "FalleN, o lugar do mapa"]
    jogador = pg.evaluate("""() => { const x = window.ctxDust; let l = ComandosDoReal.le("FalleN corre pro meio aos 1:10", x); l = ComandosDoReal.responde(l, 0, l.perguntas[0].opcoes[0].valor, x); return { r: resumo(l), v: vers(l, x) }; }""")
    assert jogador["r"]["perguntas"] == [] and (jogador["v"][0]["nick"], jogador["v"][0]["codigo"]) == ("FalleN", "ok") and jogador["r"]["acoes"][0]["alvo"] == "Meio"
    lugar = pg.evaluate("""() => { const x = window.ctxDust; let l = ComandosDoReal.le("tr 2 corre pro FalleN aos 1:10", x); const q1 = l.perguntas.map(p => p.codigo);
        l = ComandosDoReal.responde(l, 0, l.perguntas[0].opcoes[1].valor, x); return { q1: q1, r: resumo(l), v: vers(l, x) }; }""")
    assert lugar["q1"] == ["quem_ou_lugar"] and lugar["r"]["perguntas"] == [] and lugar["r"]["acoes"][0]["alvo"] == "Fallen"          # "o lugar": é o ponto do Pedro
    assert lugar["r"]["acoes"][0]["quem"][0]["nick"] == "ropz" and lugar["v"][0]["codigo"] == "ok"


def test_niko_tambem_pergunta_e_so_uma_pergunta_por_vez(dust2):
    pg = dust2
    x = le(pg, "niko corre pro Fallen aos 1:10", ctx="ctxDustNiko")
    assert [p["codigo"] for p in x["r"]["perguntas"]] == ["quem_ou_lugar"]                                                       # uma pergunta; a outra vem depois da resposta
    seq = pg.evaluate("""() => { const x = window.ctxDustNiko; let l = ComandosDoReal.le("niko corre pro Fallen aos 1:10", x), qs = [];
        while (l.perguntas.length && l.perguntas[0].codigo === "quem_ou_lugar") { qs.push(l.perguntas[0].opcoes[0].rotulo); l = ComandosDoReal.responde(l, 0, l.perguntas[0].opcoes[0].valor, x); }
        return { qs: qs, r: resumo(l) }; }""")
    assert seq["qs"] == ["NiKo, o jogador (TR 2)", "FalleN, o jogador (CT 2)"]                                                  # as duas menções, uma de cada vez, e a segunda ainda é lida como nick
    assert seq["r"]["acoes"][0]["quem"][0]["nick"] == "NiKo"


def test_no_mirage_fallen_nao_e_lugar_e_nao_pergunta(pg):
    assert le(pg, "FalleN corre pro meio aos 1:10")["r"]["perguntas"] == []


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# o que não pode mudar e o que os dois módulos prometem
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def test_sem_nick_no_contexto_o_leitor_le_como_sempre(pg):
    r = pg.evaluate("""() => { const c = JSON.parse(JSON.stringify(window.ctx)); c.jogadores.forEach(j => { delete j.nick; });
        return resumo(LeitorDeComandos.le("zywoo corre pro meio aos 1:10", c)); }""")
    assert [p["codigo"] for p in r["perguntas"]] == ["quem"] and r["naoEntendido"] == ["zywoo"] and r["acoes"][0]["quem"] == []     # sem nick, "zywoo" é só uma palavra que sobrou


def test_os_textos_do_real_existem_so_no_contexto_do_reescrever_e_o_morto_e_o_do_reescrever():
    from leitura.reescrever import TEXTOS_DO_MODO
    from scripts.comandos_contexto import TEXTOS_DO_REAL, contexto, contexto_do_real
    usados = set()
    for arq in ("leitor.js", "real.js"):
        texto = (WEB / "comandos" / arq).read_text(encoding="utf-8")
        usados |= set(re.findall(r'TX\["([a-z_]+)"\]', texto))
    novos = {k for k in usados if k in TEXTOS_DO_REAL}
    assert {"pergunta_quando_relogio", "opcao_no_instante", "botao_corrigir", "veredicto_ja_morto"} <= novos | set(TEXTOS_DO_REAL)
    faltam = [k for k in usados if k not in contexto_do_real("de_mirage")["textos"]]
    assert faltam == [], faltam
    assert {"pergunta_quem_ou_lugar", "opcao_nick_jogador", "opcao_nick_lugar"} <= set(contexto("de_mirage")["textos"])         # o leitor é o mesmo nas duas telas: seus textos moram no TEXTOS comum
    assert not any(k in contexto("de_mirage")["textos"] for k in TEXTOS_DO_REAL)                                                 # a prancheta não recebe os das regras do real
    assert TEXTOS_DO_REAL["estado_morto"].replace("{h}", "{relogio}") == TEXTOS_DO_MODO["morto"]                                  # o mesmo "morto às ..., antes de ..." do banco


def test_o_modulo_das_regras_e_puro_sem_dom_rede_nem_armazenamento():
    codigo = re.sub(r"/\*.*?\*/", "", (WEB / "comandos" / "real.js").read_text(encoding="utf-8"), flags=re.S)
    codigo = re.sub(r"//[^\n]*", "", codigo)
    for proibido in ("document.", "localStorage", "sessionStorage", "fetch(", "XMLHttpRequest", "navigator.", "setTimeout", "alert(", "console."):
        assert proibido not in codigo, proibido
