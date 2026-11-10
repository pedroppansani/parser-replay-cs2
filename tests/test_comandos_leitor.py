"""C1: o leitor de comandos da prancheta (`dashboard/web/comandos/leitor.js`), sem interface.

As 30 frases do relatório da C1 (15 da C0, 15 com os nomes do Pedro) com o que o leitor entende em cada uma, mais casos de honestidade: nada é aplicado, palavra
desconhecida nunca é aproximada em silêncio, campo que falta vira pergunta, nome repetido pergunta "qual?" (salvo qualificador que resolve) e o tempo de corrida
não é calculado aqui. O módulo é puro: o teste o carrega numa página em branco do Chrome (o mesmo Playwright dos outros testes de navegador)."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from scripts.comandos_contexto import TEXTOS, contexto

RAIZ = Path(__file__).resolve().parent.parent
LEITOR = RAIZ / "dashboard" / "web" / "comandos" / "leitor.js"

# --- guardas sem navegador ------------------------------------------------------------------------------------------------------------------------------

def test_o_leitor_e_puro_sem_dom_rede_nem_armazenamento():
    js = LEITOR.read_text(encoding="utf-8")
    for proibido in ("document.", "fetch(", "XMLHttpRequest", "localStorage", "sessionStorage", "innerHTML", "eval("):
        assert proibido not in js, proibido


def test_a_aba_nao_escreve_html_e_toda_pagina_de_mapa_leva_o_leitor_e_o_contexto():
    aba = (RAIZ / "dashboard" / "web" / "prancheta" / "20-comandos.js").read_text(encoding="utf-8")
    for proibido in ("innerHTML", "insertAdjacentHTML", "document.write", "eval(", "localStorage", "fetch("):
        assert proibido not in aba, proibido
    from scripts.build_tactics_page import build_html
    for mapa in ("de_mirage", "de_cache", "de_nuke"):                                       # com tabela conferida, sem tabela da demo, com dois andares
        html = build_html(mapa)
        assert "LeitorDeComandos" in html and '"textos"' in html and "/*__COMANDOS__*/" not in html, mapa


def test_toda_pergunta_que_o_leitor_pode_fazer_tem_texto_do_python():
    """A frase da tela sai do Python (decisão 18): cada `codigo` de pergunta do JS tem `pergunta_<codigo>` em TEXTOS, e cada opção fixa tem o seu texto."""
    js = LEITOR.read_text(encoding="utf-8")
    for codigo in set(re.findall(r'codigo: "(\w+)"', js)) - {"palavra_sobrando", "ordem_invertida", "duracao_imposta"}:
        assert f"pergunta_{codigo}" in TEXTOS, codigo
    for chave in set(re.findall(r'TX\["(\w+)"\]', js)):
        assert chave in TEXTOS, chave
    for g in ("smoke", "flash", "molotov", "he"):
        assert f"granada_{g}" in TEXTOS


def test_o_contexto_do_mapa_tem_os_pontos_do_pedro_as_areas_da_demo_e_so_conferidos_filtra():
    c = contexto("de_mirage")
    nomes = {p["nome"] for p in c["pontos"]}
    assert {"Caverna", "TV", "Meio", "Default"} <= nomes
    assert sum(1 for p in c["pontos"] if p["nome"] == "TV") == 2 and sum(1 for p in c["pontos"] if p["tipo"] == "bombsite") == 2
    assert {a["nome"] for a in c["areas"]} >= {"Middle", "TopofMid", "BombsiteA", "CTSpawn"}
    assert c["segundos_do_round"] == 115 and len(c["jogadores"]) == 10 and set(c["textos"]) == set(TEXTOS)
    # os apelidos da área não repetem nomes que já são ponto do Pedro (o ponto é o alvo exato, a área é só a chave do corpus)
    nomes_norm = {re.sub(r"[^a-z0-9]", "", n.lower()) for n in nomes}
    for a in c["areas"]:
        assert not [x for x in a["apelidos"] if re.sub(r"[^a-z0-9]", "", x.lower()) in nomes_norm], a
    assert len(contexto("de_mirage", so_conferidos=True)["pontos"]) == len(c["pontos"])            # Mirage e Dust2 estão conferidas
    assert contexto("de_nuke", so_conferidos=True)["pontos"] == []                                  # os outros ainda não
    # os nomes de ponto de um mapa ainda não conferido não entram pela tabela de apelidos das áreas (só os apelidos escritos à mão)
    apelidos = {x.lower() for a in contexto("de_nuke", so_conferidos=True)["areas"] for x in a["apelidos"]}
    assert apelidos == {"bomb a", "site a", "bomb b", "site b", "spawn ct", "spawn tr"}, apelidos
    assert contexto("de_cache")["areas"] == []                                                      # mapa sem tabela da demo: só os pontos do Pedro


# --- o leitor no navegador --------------------------------------------------------------------------------------------------------------------------------
sync_api = pytest.importorskip("playwright.sync_api")
from tests.test_tactics_browser import navegador  # noqa: E402,F401  (fixture)

COM_AWPER = [{"lado": "tr", "num": 1, "funcao": "AWPer"}] + [{"lado": "tr", "num": n} for n in range(2, 6)] + [{"lado": "ct", "num": n} for n in range(1, 6)]


@pytest.fixture(scope="module")
def pagina(navegador):
    ctx = navegador.new_context()
    pg = ctx.new_page()
    erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto("about:blank")
    pg.add_script_tag(path=str(LEITOR))
    yield pg, erros
    ctx.close()
    assert not erros


def le(pagina, mapa, frase, jogadores=None):
    pg, _ = pagina
    return pg.evaluate("([f, c]) => LeitorDeComandos.le(f, c)", [frase, contexto(mapa, jogadores=jogadores)])


def resumo(a):
    quem = "+".join(f"{q['lado'] or '?'}{q['num'] or ''}" + (f"[{q['funcao']}]" if q.get("funcao") else "") for q in a["quem"])
    alvo = (a["alvo"]["nome"] + ("@" + a["alvo"]["lugar"] if a["alvo"]["lugar"] else "")) if a["alvo"] else "-"
    q = a["quando"]
    quando = "-" if not q else f"relogio:{q['segundos_restantes']}" if q["tipo"] == "relogio" else f"inicio:{q['segundos']}" if q["tipo"] == "inicio" else q["tipo"]
    extra = (f" espera={a['espera_s']}" if a["espera_s"] is not None else "") + (f" dur={a['duracao_s']}" if a["duracao_s"] is not None else "") \
        + (" [desloc]" if a["depende_do_deslocamento"] else "")
    return f"{a['tipo']}|{quem}|{a['granada'] or '-'}|{alvo}|{a['modo'] or '-'}|{quando}{extra}"


# (número, mapa, frase, jogadores, ações, perguntas (ação, código), avisos)
Q = lambda *p: list(p)  # noqa: E731
CASOS = [
    # ---- as 15 frases da C0 ----
    (1, "de_mirage", "jogador 2 joga smoke em window aos 1:30", None, ["lancar|?2|smoke|-|-|relogio:90"], [(0, "quem_lado"), (0, "onde_desconhecido")], []),
    (2, "de_mirage", "TR 2 joga smoke em BombsiteA aos 1:30", None, ["lancar|tr2|smoke|A@BOMBSITE A|-|relogio:90"], [], []),
    (3, "de_inferno", "o 2 joga molotov na Banana aos 1:20", None, ["lancar|?2|molotov|Banana@BANANA|-|relogio:80"], [(0, "quem_lado")], []),
    (4, "de_mirage", "ct 3 vai pro meio", None, ["mover|ct3|-|Meio@MIDDLE|correndo|-"], [(0, "quando")], []),
    (5, "de_mirage", "tr 1 corre até o spawn ct aos 1:00", None, ["mover|tr1|-|CTSpawn@CTSpawn|correndo|relogio:60"], [], []),
    (6, "de_nuke", "jogador 2 joga uma molotov na rampa e roda pra o meio correndo", None,
     ["lancar|?2|molotov|-|-|-", "mover|?2|-|-|correndo|depois"], [(0, "quem_lado"), (0, "qual"), (0, "quando"), (1, "onde_desconhecido")], []),
    (7, "de_mirage", "awper segura B", COM_AWPER, ["segurar|tr1[AWPer]|-|B@BOMBSITE B|-|-"], [(0, "quando")], []),
    (8, "de_mirage", "tr 4 espera 5 segundos e depois vai pra b", None, ["esperar|tr4|-|-|-|- espera=5", "mover|tr4|-|B@BOMBSITE B|correndo|depois"], [(0, "quando")], []),
    (9, "de_mirage", "tr 2 e tr 3 jogam flash na b aos 0:50", None, ["lancar|tr2+tr3|flash|B@BOMBSITE B|-|relogio:50"], [], []),
    (10, "de_mirage", "o jogador 2 joga a molotov na caverna aos 1:20 e roda pra tv correndo", None,
     ["lancar|?2|molotov|Caverna@T RAMP|-|relogio:80", "mover|?2|-|TV@HOUSE|correndo|depois"], [(0, "quem_lado")], []),
    (11, "de_mirage", "tr 1 vai até a escada", None, ["mover|tr1|-|-|correndo|-"], [(0, "onde_desconhecido"), (0, "quando")], []),
    (12, "de_mirage", "joga uma smoke", None, ["lancar||smoke|-|-|-"], [(0, "quem"), (0, "onde"), (0, "quando")], []),
    (13, "de_mirage", "tr 3 joga flash e entra na b", None, ["lancar|tr3|flash|-|-|-", "mover|tr3|-|B@BOMBSITE B|correndo|depois"], [(0, "onde"), (0, "quando")], []),
    (14, "de_dust2", "tr 5 corre pro long depois ele joga uma he aos 1:10", None,
     ["mover|tr5|-|-|correndo|-", "lancar|tr5|he|-|-|relogio:70 [desloc]"], [(0, "onde_desconhecido"), (0, "quando"), (1, "onde")], []),
    (15, "de_mirage", "tr 2 corre pra b em 3 segundos", None, ["mover|tr2|-|B@BOMBSITE B|correndo|- dur=3"], [(0, "quando")], ["duracao_imposta"]),
    # ---- as 15 frases com os nomes do Pedro ----
    (16, "de_mirage", "tr 2 joga smoke na janela mercado aos 1:30", None, ["lancar|tr2|smoke|Janela Mercado@SHOP|-|relogio:90"], [], []),
    (17, "de_mirage", "ct 4 vai pro default do A aos 1:50", None, ["mover|ct4|-|Default@BOMBSITE A|correndo|relogio:110"], [], []),
    (18, "de_mirage", "ct 3 joga flash na lixeira do ct aos 1:40", None, ["lancar|ct3|flash|Lixeira@CT SPAWN|-|relogio:100"], [], []),
    (19, "de_mirage", "tr 1 segura banco do meio aos 1:15", None, ["segurar|tr1|-|Banco@MIDDLE|-|relogio:75"], [], []),
    (20, "de_mirage", "tr 5 anda pra caverna tr aos 1:10", None, ["mover|tr5|-|Caverna TR@PALACE ALLEY|andando|relogio:70"], [], []),
    (21, "de_mirage", "o awper agacha na plataforma aos 1:00", COM_AWPER, ["mover|tr1[AWPer]|-|Plataforma@PALACE ALLEY|agachado|relogio:60"], [], []),
    (22, "de_mirage", "tr 2 joga molotov na escada tv e depois vai pra TV", None,
     ["lancar|tr2|molotov|Escada TV@SIDE ALLEY|-|-", "mover|tr2|-|TV@HOUSE|correndo|depois"], [(0, "quando")], []),
    (23, "de_mirage", "tr 3 vai pro tapete a aos 1:05", None, ["mover|tr3|-|Palácio@PALACE INTERIOR|correndo|relogio:65"], [], []),
    (24, "de_mirage", "ct 2 segura o mogi aos 1:45", None, ["segurar|ct2|-|Moddii@BOMBSITE B|-|relogio:105"], [], []),
    (25, "de_mirage", "tr 1 e tr 2 vão pra TV aos 1:35", None, ["mover|tr1+tr2|-|TV@HOUSE|correndo|relogio:95"], [], []),
    (26, "de_mirage", "tr 4 joga smoke na caixa fogo aos 0:55 e ao mesmo tempo tr 5 joga flash na caixa fogo", None,
     ["lancar|tr4|smoke|Caixa Fogo@BOMBSITE A|-|relogio:55", "lancar|tr5|flash|Caixa Fogo@BOMBSITE A|-|junto"], [], []),
    (27, "de_mirage", "ct 1 vai pra base tr em 12 segundos", None, ["mover|ct1|-|Base TR@T SPAWN|correndo|- dur=12"], [(0, "quando")], ["duracao_imposta"]),
    (28, "de_mirage", "tr 2 joga molotov no tetris aos 40 segundos", None, ["lancar|tr2|molotov|Tetris@BOMBSITE A|-|-"], [(0, "quando_segundos")], []),
    (29, "de_mirage", "tr 2 joga molotov no tetris aos 40 segundos do início", None, ["lancar|tr2|molotov|Tetris@BOMBSITE A|-|inicio:40"], [], []),
    (30, "de_nuke", "tr 2 vai pro silo aos 1:00", None, ["mover|tr2|-|-|correndo|relogio:60"], [(0, "qual")], []),
    # ---- honestidade e bordas (além das 30) ----
    (31, "de_mirage", "ct 3 corre pro meio aos 3:20", None, ["mover|ct3|-|Meio@MIDDLE|correndo|-"], [(0, "horario_invalido")], []),
    (32, "de_mirage", "tr 2 vai pra xyzzy aos 1:00", None, ["mover|tr2|-|-|correndo|relogio:60"], [(0, "onde_desconhecido")], []),
    (33, "de_mirage", "tr 2 vai pra caverma aos 1:00", None, ["mover|tr2|-|-|correndo|relogio:60"], [(0, "onde_desconhecido")], []),
    (34, "de_mirage", "joga uma bomba na tv", None, ["lancar||-|TV@HOUSE|-|-"], [(0, "quem"), (0, "granada"), (0, "quando")], ["palavra_sobrando"]),
    (35, "de_mirage", "tr 2 vai pra Bombsite A aos 1:00", None, ["mover|tr2|-|A@BOMBSITE A|correndo|relogio:60"], [], []),
    (36, "de_mirage", "tr 2 vai pra BOMBSITEA aos 1:00", None, ["mover|tr2|-|A@BOMBSITE A|correndo|relogio:60"], [], []),
    (37, "de_mirage", "tr 2 segura TopOfMid aos 1:00", None, ["segurar|tr2|-|TopofMid@TopofMid|-|relogio:60"], [], []),
    (38, "de_mirage", "tr 2 joga a molotov na b aos 1:00", None, ["lancar|tr2|molotov|B@BOMBSITE B|-|relogio:60"], [], []),
    (39, "de_mirage", "tr 2 joga smoke na b aos 1:10 e depois joga flash na b aos 1:30", None,
     ["lancar|tr2|smoke|B@BOMBSITE B|-|relogio:70", "lancar|tr2|flash|B@BOMBSITE B|-|relogio:90"], [], ["ordem_invertida"]),
    (40, "de_mirage", "o lurker vai pra b aos 1:00", None, ["mover|?[Lurker]|-|B@BOMBSITE B|correndo|relogio:60"], [(0, "quem_funcao")], []),
    (41, "de_mirage", "jogador dois joga smoke na b aos 1:30", None, ["lancar|?2|smoke|B@BOMBSITE B|-|relogio:90"], [(0, "quem_lado")], []),                      # número por extenso
    (42, "de_mirage", "tr um joga um smoke na b aos 1:00", None, ["lancar|tr1|smoke|B@BOMBSITE B|-|relogio:60"], [], []),                                    # "um" jogador e "um" artigo
    (43, "de_mirage", "joga um smoke na b aos 1:00", None, ["lancar||smoke|B@BOMBSITE B|-|relogio:60"], [(0, "quem")], []),                                  # o artigo não é o jogador 1
    (44, "de_mirage", "tr 2 entra na b aos 1:00", None, ["mover|tr2|-|B@BOMBSITE B|correndo|relogio:60"], [], []),                                           # entra, sobe, desce, volta e rotaciona valem "vai até"
    (45, "de_mirage", "tr 2 sobe pro meio aos 1:00", None, ["mover|tr2|-|Meio@MIDDLE|correndo|relogio:60"], [], []),
    (46, "de_mirage", "tr 2 desce pra b aos 1:00", None, ["mover|tr2|-|B@BOMBSITE B|correndo|relogio:60"], [], []),
    (47, "de_mirage", "tr 2 volta pro spawn ct aos 1:00", None, ["mover|tr2|-|CTSpawn@CTSpawn|correndo|relogio:60"], [], []),
    (48, "de_mirage", "tr 2 rotaciona pra b aos 1:00", None, ["mover|tr2|-|B@BOMBSITE B|correndo|relogio:60"], [], []),
    (49, "de_inferno", "tr 2 vai pra banana aos 1:00", None, ["mover|tr2|-|Banana@BANANA|correndo|relogio:60"], [], []),                                    # duas Bananas na mesma área: um alvo só
    (50, "de_mirage", "tr 2 vai pro default aos 1:00", None, ["mover|tr2|-|-|correndo|relogio:60"], [(0, "qual")], []),                                  # Default do A e do B: áreas diferentes, pergunta
    (51, "de_mirage", "tr 2 joga smoke na janela aos 1:30", None, ["lancar|tr2|smoke|Janelão@SNIPERS NEST|-|relogio:90"], [], []),                           # "janela" é apelido do Janelão
    (52, "de_mirage", "tr 2 joga smoke na janela mercado aos 1:30", None, ["lancar|tr2|smoke|Janela Mercado@SHOP|-|relogio:90"], [], []),                   # e não leva o "Janela Mercado"
]


@pytest.mark.parametrize("n,mapa,frase,jogadores,acoes,perguntas,avisos", CASOS, ids=[f"{c[0]:02d}" for c in CASOS])
def test_o_que_o_leitor_entende(pagina, n, mapa, frase, jogadores, acoes, perguntas, avisos):
    r = le(pagina, mapa, frase, jogadores)
    assert [resumo(a) for a in r["acoes"]] == acoes, frase
    assert [(p["acao"], p["codigo"]) for p in r["perguntas"]] == perguntas, frase
    assert [a["codigo"] for a in r["avisos"]] == avisos, frase
    assert r["ok"] == (not r["perguntas"] and not r["naoEntendido"] and bool(r["acoes"]))
    for p in r["perguntas"]:
        assert p["texto"] and "{" not in p["texto"], p                                  # nenhuma frase com campo sem preencher


def test_o_exemplo_do_pedro_monta_a_molotov_e_a_corrida_sem_perguntar_a_tv_quando_as_duas_estao_na_mesma_area(pagina):
    r = le(pagina, "de_mirage", "tr 2 joga uma molotov na caverna aos 1:20 e roda pra TV correndo")
    assert [resumo(a) for a in r["acoes"]] == ["lancar|tr2|molotov|Caverna@T RAMP|-|relogio:80", "mover|tr2|-|TV@HOUSE|correndo|depois"]
    assert r["perguntas"] == [] and r["acoes"][0]["quando"]["t_decorrido"] == 35 and not r["acoes"][1]["depende_do_deslocamento"]
    tvs = [p for p in contexto("de_mirage")["pontos"] if p["nome"] == "TV"]
    assert len(tvs) == 2 and tvs[0]["lugar"] == tvs[1]["lugar"] and tvs[0]["andar"] == tvs[1]["andar"]
    alvo = r["acoes"][1]["alvo"]
    assert alvo["ponto_medio"] is True and sorted(alvo["ids"]) == sorted(p["id"] for p in tvs)                           # o alvo é um só: o ponto do meio das duas TVs
    assert abs(alvo["x"] - (tvs[0]["x"] + tvs[1]["x"]) / 2) <= 0.5 and abs(alvo["y"] - (tvs[0]["y"] + tvs[1]["y"]) / 2) <= 0.5


def test_nada_e_aplicado_nem_chutado_a_sugestao_nunca_vira_o_alvo(pagina):
    for frase in ("tr 2 vai pra caverma aos 1:00", "tr 2 vai pra xyzzy aos 1:00"):
        r = le(pagina, "de_mirage", frase)
        assert all(a["alvo"] is None for a in r["acoes"]), frase                        # o nome que não existe fica sem alvo, mesmo com uma sugestão parecida
        assert not r["ok"]
    r = le(pagina, "de_mirage", "tr 2 vai pra caverma aos 1:00")
    (q,) = r["perguntas"]
    assert [o["rotulo"].split(" ·")[0] for o in q["opcoes"]] == ["Caverna", "Caverna TR"]   # sugerida, a pessoa escolhe
    assert le(pagina, "de_mirage", "tr 2 vai pra xyzzy aos 1:00")["perguntas"][0]["opcoes"] == []
    assert [x["trecho"] for x in le(pagina, "de_mirage", "tr 2 vai pra xyzzy aos 1:00")["naoEntendido"]] == ["xyzzy"]
    r = le(pagina, "de_mirage", "joga uma bomba na tv")                                                                  # a palavra "bomba" não vira granada nem lugar
    assert r["acoes"][0]["granada"] is None and [x["trecho"] for x in r["naoEntendido"]] == ["bomba"] and "granada" in [p["codigo"] for p in r["perguntas"]]


def test_as_opcoes_do_nome_repetido_dizem_o_que_distingue_um_do_outro(pagina):
    (q,) = le(pagina, "de_nuke", "tr 2 vai pro silo aos 1:00")["perguntas"]
    rotulos = [o["rotulo"] for o in q["opcoes"]]
    assert len(rotulos) == 2 and any("cima" in r for r in rotulos) and any("baixo" in r for r in rotulos), rotulos     # o andar do ponto vai na opção
    assert {o["valor"]["alvo"]["andar"] for o in q["opcoes"]} == {"cima", "baixo"}                                      # andares diferentes: pergunta
    (q,) = le(pagina, "de_mirage", "tr 2 vai pro default aos 1:00")["perguntas"]
    assert sorted(o["rotulo"] for o in q["opcoes"]) == ["Default · BOMBSITE A", "Default · BOMBSITE B"]                  # áreas diferentes: pergunta, com a área
    (q,) = le(pagina, "de_cache", "tr 2 vai pro miolo aos 1:00")["perguntas"]
    assert q["codigo"] == "qual" and len({o["rotulo"] for o in q["opcoes"]}) == len(q["opcoes"]) >= 2                    # sem área da demo que distinga: as coordenadas


def test_o_nome_em_ingles_do_jogo_vale_sem_diferenca_de_maiuscula_espaco_e_acento(pagina):
    for frase in ("tr 2 segura top of mid aos 1:00", "tr 2 segura TOPOFMID aos 1:00", "tr 2 segura TopOfMid aos 1:00"):
        r = le(pagina, "de_mirage", frase)
        assert [resumo(a) for a in r["acoes"]] == ["segurar|tr2|-|TopofMid@TopofMid|-|relogio:60"] and r["acoes"][0]["origem_do_alvo"] == "area", frase
    r = le(pagina, "de_mirage", "TR 2 VAI PRA CAVERNA TR AOS 1:10")                                                       # maiúsculas e acentos não mudam nada
    assert resumo(r["acoes"][0]).startswith("mover|tr2|-|Caverna TR@")
    r = le(pagina, "de_mirage", "tr 2 vai pra Palacio aos 1:10")                                                          # "Palácio" sem acento
    assert r["acoes"][0]["alvo"]["nome"] == "Palácio" and r["acoes"][0]["origem_do_alvo"] == "ponto"


def test_o_ponto_do_pedro_ganha_da_area_de_mesmo_nome_e_o_horario_so_vale_dentro_do_round(pagina):
    r = le(pagina, "de_mirage", "tr 2 vai pra Bombsite A aos 1:00")
    assert r["acoes"][0]["origem_do_alvo"] == "ponto"
    r = le(pagina, "de_mirage", "tr 2 vai pra b aos 2:30")
    assert [p["codigo"] for p in r["perguntas"]] == ["horario_invalido"] and r["acoes"][0]["quando"] is None


def test_mapa_sem_tabela_da_demo_so_tem_os_pontos_do_pedro_e_o_nome_em_ingles_nao_existe(pagina):
    r = le(pagina, "de_cache", "tr 2 joga molotov no xadrez aos 1:00")
    assert resumo(r["acoes"][0]) == "lancar|tr2|molotov|Xadrez|-|relogio:60"                                              # sem lugar da demo: o alvo é só o ponto
    r = le(pagina, "de_cache", "tr 2 vai pra middle aos 1:00")
    assert r["acoes"][0]["alvo"] is None and [p["codigo"] for p in r["perguntas"]] == ["onde_desconhecido"]


def test_o_leitor_nao_calcula_tempo_de_corrida_nem_muda_o_contexto(pagina):
    pg, _ = pagina
    ctx = contexto("de_mirage")
    antes = pg.evaluate("([f, c]) => { const s = JSON.stringify(c); LeitorDeComandos.le(f, c); return s === JSON.stringify(c); }", ["tr 2 corre pra b aos 1:00", ctx])
    assert antes                                                                                                          # o contexto fica como veio
    r = le(pagina, "de_mirage", "tr 2 corre pra b aos 1:00 e depois joga flash na b aos 0:50")
    assert not any(k in a for a in r["acoes"] for k in ("duracao_estimada", "tempo_de_corrida", "chegada"))
    assert r["acoes"][1]["depende_do_deslocamento"] is True                                                               # só avisa que o horário fixo depende da corrida (C3)
