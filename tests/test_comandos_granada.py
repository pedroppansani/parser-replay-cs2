"""C4: a aba Comandos puxa UM arremesso real da biblioteca ("joga molotov na Caverna"): do mesmo tipo e do mesmo lado, que caiu perto do destino; a contagem, a pergunta
quando a saída é longe da peça (levar até lá, outro arremesso, sem arremesso real), o voo desconhecido que nunca vira horário de queda, o aviso de lado, e os dois cartões
que ficaram da C3 ("depois, por volta de" e "cortado pelo comando")."""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")

from tests.test_comandos_aba import _aplica  # noqa: E402,F401
from tests.test_comandos_tempos import _escreve, _pagina, _peca, _ponto  # noqa: E402,F401
from tests.test_tactics_browser import abre, aba_do_painel, contexto, interno, navegador, pagina_do_mapa  # noqa: E402,F401

RAIZ = Path(__file__).resolve().parents[1]
RAIO_QUEDA, RAIO_SAIDA = 150.0, 50.0


def _biblioteca(mapa="de_mirage"):
    return json.loads((RAIZ / "data" / "lineups" / f"{mapa}.json").read_text(encoding="utf-8"))["arremessos"]


def _contagem(mapa, arma, lado, pontos):
    """Quantos arremessos do lado e do outro lado caem a até 150 u de algum dos pontos (recontado aqui, sem o código do site)."""
    mesmo = outro = 0
    for r in _biblioteca(mapa):
        if r["arma"] != arma:
            continue
        if min(math.hypot(r["destino"][0] - x, r["destino"][1] - y) for x, y in pontos) <= RAIO_QUEDA:
            if r["lado"] == lado:
                mesmo += 1
            else:
                outro += 1
    return mesmo, outro


def _alvo_do_ponto(nome, mapa="de_mirage"):
    from scripts.comandos_contexto import contexto as c
    ps = [p for p in c(mapa, so_conferidos=True)["pontos"] if p["nome"] == nome]
    return {"tipo": "ponto", "id": ps[0]["id"], "ids": [p["id"] for p in ps], "nome": nome, "x": ps[0]["x"], "y": ps[0]["y"], "andar": "único"}, [(p["x"], p["y"]) for p in ps]


def _busca(pg, arma, alvo, lado, x, y):
    return pg.evaluate("([a, al, l, x, y]) => { const b = Prancheta._interno.cmdBuscaReal(a, al, l, { x: x, y: y }); return { estado: b.estado, mesmo: b.mesmo, outro: b.outro, grupos: b.grupos.map(g => ({ arma: g.r.arma, lado: g.r.lado, id: g.r.id, dist: g.dist, voo: g.voo, origem: g.r.origem, destino: g.r.destino })) }; }",
                       [arma, alvo, lado, x, y])


def _ponto_longe(pg, arma, alvo, lado, minimo):
    """Um ponto do Pedro de onde a saída mais perto do arremesso real fica a pelo menos `minimo` u: a ficha posta ali está LONGE do ponto de saída."""
    from scripts.comandos_contexto import contexto as c
    for p in c("de_mirage", so_conferidos=True)["pontos"]:
        b = _busca(pg, arma, alvo, lado, p["x"], p["y"])
        if b["grupos"] and b["grupos"][0]["dist"] >= minimo:
            return p
    raise AssertionError("nenhum ponto do Pedro fica a %d u da saída mais perto" % minimo)


def _plano(pg, arma, alvo, lado="tr", t=35.0):
    """O plano de uma frase fabricada: o jogador N do lado, `arma` no alvo, no horário t."""
    return pg.evaluate("""([arma, alvo, lado, t]) => { const I = Prancheta._interno;
        const ac = { indice: 0, tipo: "lancar", quem: [{ lado: lado, num: 2 }], granada: arma, alvo: alvo, quando: { tipo: "relogio", t_decorrido: t, segundos_restantes: 115 - t }, modo: null, gr_decisao: "levar", gr_tarde_ok: true };
        const plano = I.cmdPlano({ acoes: [ac] });
        return { granada: plano.granadas[0] ? { sem: !!plano.granadas[0].sem, tCai: plano.granadas[0].tCai === undefined ? null : plano.granadas[0].tCai, tSai: plano.granadas[0].tSai, id: plano.granadas[0].r ? plano.granadas[0].r.id : null,
                                                voo_s: plano.granadas[0].r ? plano.granadas[0].r.voo_s : null } : null,
                 linha: I.cmdLinha(ac, plano), pergunta: plano.pergunta ? plano.pergunta.tipo : null, avisos: plano.avisos }; }""", [arma, alvo, lado, t])


@pytest.mark.parametrize("nome,lado,arma", [("Caverna", "t", "molotov"), ("Caverna", "ct", "molotov"), ("Janelão", "t", "smoke"), ("Liga", "ct", "flash"), ("Banco", "t", "he"), ("Caverna", "ct", "he")])
def test_nenhum_arremesso_sugerido_e_de_outro_lado_ou_de_outro_tipo_e_a_contagem_bate(contexto, tmp_path_factory, nome, lado, arma):
    alvo, pontos = _alvo_do_ponto(nome)
    pg = _pagina(contexto, tmp_path_factory)
    _peca(pg, 0, 0)
    b = _busca(pg, arma, alvo, lado, 0, 0)
    mesmo, outro = _contagem("de_mirage", arma, lado, pontos)
    assert b["estado"] == "ok" and (b["mesmo"], b["outro"]) == (mesmo, outro), (b["mesmo"], b["outro"], mesmo, outro)
    assert b["grupos"] and all(g["arma"] == arma and g["lado"] == lado for g in b["grupos"])
    assert all(min(math.hypot(g["destino"][0] - x, g["destino"][1] - y) for x, y in pontos) <= RAIO_QUEDA for g in b["grupos"])      # todos caem perto do destino
    # a lista vai da saída mais perto da peça para a mais longe (em faixas de 50 u), e as jogadas estão separadas por pelo menos 50 u de saída
    faixas = [math.floor(g["dist"] / 50) for g in b["grupos"]]
    assert faixas == sorted(faixas)
    for i, a in enumerate(b["grupos"]):
        for c in b["grupos"][i + 1:]:
            assert math.hypot(a["origem"][0] - c["origem"][0], a["origem"][1] - c["origem"][1]) > RAIO_SAIDA


def test_voo_conhecido_vem_antes_do_desconhecido_na_mesma_faixa_de_distancia(contexto, tmp_path_factory):
    # uma molotov sem voo na biblioteca, e o ponto do Pedro mais perto da queda dela
    from scripts.comandos_contexto import contexto as c
    pts = c("de_mirage", so_conferidos=True)["pontos"]
    achou = None
    for r in _biblioteca():
        if r["arma"] == "molotov" and r.get("voo_s") is None:
            for p in pts:
                if math.hypot(r["destino"][0] - p["x"], r["destino"][1] - p["y"]) <= RAIO_QUEDA:
                    achou = (r, p); break
        if achou:
            break
    assert achou, "a biblioteca da Mirage tem molotovs sem voo perto de um ponto do Pedro"
    r, p = achou
    alvo, _ = _alvo_do_ponto(p["nome"])
    pg = _pagina(contexto, tmp_path_factory)
    _peca(pg, 0, 0)
    b = _busca(pg, "molotov", alvo, r["lado"], r["origem"][0], r["origem"][1])
    assert any(not g["voo"] for g in b["grupos"])
    for i, g in enumerate(b["grupos"]):
        for h in b["grupos"][i + 1:]:
            if math.floor(g["dist"] / 50) == math.floor(h["dist"] / 50):
                assert g["voo"] or not h["voo"], "na mesma faixa de distância o voo conhecido vem antes do desconhecido"


def test_o_voo_desconhecido_nunca_vira_horario_de_queda(contexto, tmp_path_factory):
    from scripts.comandos_contexto import contexto as c
    pts = c("de_mirage", so_conferidos=True)["pontos"]
    pg = _pagina(contexto, tmp_path_factory)
    _peca(pg, 0, 0)
    _peca(pg, 100, 0, lado="ct")
    vistos = 0
    for r in [x for x in _biblioteca() if x["arma"] == "molotov" and x.get("voo_s") is None][:30]:
        alvo = {"tipo": "ponto", "id": "x:0", "ids": ["x:0"], "nome": "alvo", "x": r["destino"][0], "y": r["destino"][1], "andar": "único"}
        p = _plano(pg, "molotov", alvo, "tr" if r["lado"] == "t" else "ct")
        if p["granada"] and not p["granada"]["sem"] and p["granada"]["voo_s"] is None:
            vistos += 1
            assert p["granada"]["tCai"] is None and "não sei quando ela cai" in p["linha"] and "cai por volta de" not in p["linha"], p["linha"]
    assert vistos >= 1
    # com voo conhecido, o cartão diz quando cai: o horário de saída menos o voo, no relógio que desce
    alvo, _ = _alvo_do_ponto("Janelão")
    q = _plano(pg, "smoke", alvo, "tr")
    if q["granada"] and not q["granada"]["sem"]:
        assert q["granada"]["tCai"] is not None and q["granada"]["tCai"] > q["granada"]["tSai"] and "cai por volta de" in q["linha"]


def test_a_contagem_aparece_sempre_com_a_partida_e_o_round_e_a_saida_perto_nao_pergunta(contexto, tmp_path_factory):
    alvo, pontos = _alvo_do_ponto("Janelão")
    pg = _pagina(contexto, tmp_path_factory)
    _peca(pg, 0, 0)
    b = _busca(pg, "smoke", alvo, "t", 0, 0)
    g = b["grupos"][2]                                                                      # uma saída qualquer da lista
    pg.close()
    pg = _pagina(contexto, tmp_path_factory)
    _peca(pg, g["origem"][0], g["origem"][1])                                               # a ficha já está no ponto de saída: nada a perguntar
    _escreve(pg, "tr 2 joga smoke no janelão aos 1:20")
    assert pg.locator("#pr-cmd-pergunta-granada").count() == 0
    texto = pg.locator("#pr-cmd-entendi li").all_inner_texts()[0]
    n = len(b["grupos"])
    assert f"lugar de saída 1 de {n} (TR), " in texto and ", round " in texto and "cai por volta de" in texto, texto
    assert "match_" not in texto and " × " in texto, texto                                   # a partida pelo nome da lista de Partidas (os times), nunca pelo id
    assert pg.is_enabled("#pr-cmd-aplicar")
    _aplica(pg)
    gr = interno(pg, "Object.values(S.e3.granadas)[0]")
    assert gr["arremesso"] is not None and gr["arremesso"]["arma"] == "smoke" and gr["arremesso"]["lado"] == "t" and abs(gr["t"] - 35) < 0.011


def test_saida_longe_pergunta_levar_ate_la_e_o_desfazer_volta_exatamente_ao_estado_de_antes(contexto, tmp_path_factory):
    pg = _pagina(contexto, tmp_path_factory)
    base = _ponto_longe(pg, "smoke", _alvo_do_ponto("Janelão")[0], "t", 400)
    _peca(pg, base["x"], base["y"])
    antes = interno(pg, "JSON.stringify({ p: S.e3.pecas, g: S.e3.granadas })")
    _escreve(pg, "tr 2 joga smoke no janelão aos 1:20")
    assert pg.is_disabled("#pr-cmd-aplicar")
    pergunta = pg.inner_text("#pr-cmd-pergunta-granada")
    m = re.search(r"O TR 2 está a cerca de (\d+) s correndo \((\d+) u\) do lugar de saída 1 de", pergunta)
    assert m, pergunta
    assert int(m.group(1)) == max(1, round(int(m.group(2)) / 250))                          # a distância em segundos, na mesma velocidade de 250 u/s da corrida até a saída
    botoes = pg.locator("#pr-cmd-pergunta-granada .pr-cmd-opcao").all_inner_texts()
    assert botoes[0] == "Levar o TR 2 até lá" and "Usar outro arremesso" in botoes and botoes[-1] == "Pôr a granada sem arremesso real"
    ops_pergunta = interno(pg, "S.doc.operacoes.length")
    pg.click("[data-escolha=levar]")
    assert interno(pg, "S.doc.operacoes.length") == ops_pergunta                                              # escolher não muda a tática: só o Aplicar
    assert pg.locator("#pr-cmd-pergunta-granada").count() == 0 or "só chega" in pg.inner_text("#pr-cmd-pergunta-granada")
    if pg.locator("#pr-cmd-pergunta-granada").count():
        pg.click("[data-escolha=tarde]")
    assert pg.is_enabled("#pr-cmd-aplicar")
    ops_antes = interno(pg, "S.doc.operacoes.length")
    pg.click("#pr-cmd-aplicar")
    novas = interno(pg, "S.doc.operacoes.slice(%d).map(o => o.tipo)" % ops_antes)
    assert novas.count("cria_granada") == 1 and "cria_caminho" in novas                                      # a corrida até o ponto de saída e a granada, num lote só
    assert interno(pg, "I.problemas(JSON.parse(JSON.stringify(S.doc)), 1)") == []
    pg.evaluate("() => Prancheta._interno.desfaz()")                                                          # UM desfazer
    assert interno(pg, "JSON.stringify({ p: S.e3.pecas, g: S.e3.granadas })") == antes


def test_corrida_que_chega_depois_do_horario_pede_confirmacao_e_a_granada_sai_quando_ele_chega(contexto, tmp_path_factory):
    pg = _pagina(contexto, tmp_path_factory)
    base = _ponto_longe(pg, "smoke", _alvo_do_ponto("Janelão")[0], "t", 900)
    _peca(pg, base["x"], base["y"])
    _escreve(pg, "tr 2 joga smoke no janelão aos 1:52")                                                      # 3 s depois do início: ninguém chega ao ponto de saída
    pg.click("[data-escolha=levar]")
    texto = pg.inner_text("#pr-cmd-pergunta-granada")
    assert "só chega ao lugar de saída" in texto and "não antes de" in texto and "Jogar às " in texto, texto
    assert pg.is_disabled("#pr-cmd-aplicar")
    pg.click("[data-escolha=tarde]")
    assert pg.is_enabled("#pr-cmd-aplicar")
    _aplica(pg)
    g = interno(pg, "Object.values(S.e3.granadas)[0]")
    assert g["t"] > 3.5 + 0.3 and g["arremesso"] is not None                                                 # saiu quando o jogador chegou, não às 1:52


def test_usar_outro_arremesso_passa_para_o_proximo_da_lista(contexto, tmp_path_factory):
    pg = _pagina(contexto, tmp_path_factory)
    base = _ponto_longe(pg, "smoke", _alvo_do_ponto("Janelão")[0], "t", 400)
    _peca(pg, base["x"], base["y"])
    _escreve(pg, "tr 2 joga smoke no janelão aos 1:20")
    assert "lugar de saída 1 de" in pg.inner_text("#pr-cmd-pergunta-granada")
    primeiro = pg.inner_text("#pr-cmd-pergunta-granada")
    pg.click("[data-escolha=outro]")
    segundo = pg.inner_text("#pr-cmd-pergunta-granada")
    assert "lugar de saída 2 de" in segundo and segundo != primeiro
    pg.click("[data-escolha=levar]")
    if pg.locator("[data-escolha=tarde]").count():
        pg.click("[data-escolha=tarde]")
    assert "lugar de saída 2 de" in pg.inner_text("#pr-cmd-entendi")


def test_sem_arremesso_real_para_o_destino_a_granada_vai_como_antes_com_o_aviso(contexto, tmp_path_factory):
    alvo, pontos = _alvo_do_ponto("TV")
    assert _contagem("de_mirage", "smoke", "t", pontos) == (0, 1)                                           # nenhuma smoke de TR cai nas TVs
    base = _ponto("de_mirage", "Base TR")
    pg = _pagina(contexto, tmp_path_factory)
    _peca(pg, base["x"], base["y"])
    _escreve(pg, "tr 2 joga smoke na tv aos 1:20")
    assert pg.locator("#pr-cmd-pergunta-granada").count() == 0
    assert "Não achei arremesso real de TR para este lugar" in pg.inner_text("#pr-cmd-origem")
    _aplica(pg)
    g = interno(pg, "Object.values(S.e3.granadas)[0]")
    assert g["arremesso"] is None and abs(g["origem"][0] - base["x"]) < 1


def test_poucos_do_lado_e_muitos_do_outro_avisa_e_nunca_usa_o_outro_lado_as_duas_frases(contexto, tmp_path_factory):
    alvo, pontos = _alvo_do_ponto("Caverna")
    mesmo_t, outro_t = _contagem("de_mirage", "molotov", "t", pontos)
    mesmo_ct, outro_ct = _contagem("de_mirage", "molotov", "ct", pontos)
    assert mesmo_t < 5 and outro_t >= 20 and mesmo_ct >= 20                                                 # o caso que motivou: a Caverna recebe molotov de CT
    base = _ponto("de_mirage", "Base TR")
    pg = _pagina(contexto, tmp_path_factory)
    _peca(pg, base["x"], base["y"])
    _escreve(pg, "tr 2 joga molotov na caverna aos 1:20")
    aviso = " ".join(pg.locator("#pr-cmd-resultado .pr-cmd-aviso").all_inner_texts())
    arremessos = "arremesso real" if mesmo_t == 1 else "arremessos reais"
    assert f"Achei {mesmo_t} {arremessos} de TR aqui. Este lugar recebe muita molotov de CT ({outro_t}): confira se o jogador é do lado certo." in aviso, aviso
    b = _busca(pg, "molotov", alvo, "t", base["x"], base["y"])
    assert b["grupos"] and all(g["lado"] == "t" for g in b["grupos"])                                       # só do lado da peça
    pg.close()
    # "ct 2 joga molotov na caverna": a lista vem com os arremessos de CT, sem aviso
    pg = _pagina(contexto, tmp_path_factory)
    _peca(pg, 0, 0, lado="ct")
    b = _busca(pg, "molotov", alvo, "ct", 0, 0)
    assert b["mesmo"] == mesmo_ct and b["grupos"] and all(g["lado"] == "ct" for g in b["grupos"])
    _escreve(pg, "ct 2 joga molotov na caverna aos 1:20")
    assert "recebe muita" not in " ".join(pg.locator("#pr-cmd-resultado .pr-cmd-aviso").all_inner_texts())
    assert "lugar de saída 1 de" in (pg.inner_text("#pr-cmd-pergunta-granada") if pg.locator("#pr-cmd-pergunta-granada").count() else pg.inner_text("#pr-cmd-entendi"))


def test_cartoes_que_ficaram_da_c3_o_depois_mostra_o_horario_e_o_cortado_diz_que_foi_cortado(contexto, tmp_path_factory):
    base = _ponto("de_mirage", "Base TR")
    pg = _pagina(contexto, tmp_path_factory)
    _peca(pg, base["x"], base["y"])
    _escreve(pg, "tr 2 corre pro meio aos 1:30 e depois corre pra b")
    linhas = pg.locator("#pr-cmd-entendi li").all_inner_texts()
    assert linhas[0].startswith("TR 2 · correndo até Meio · aos 1:30 · chega") and " · depois, por volta de " in linhas[1], linhas
    import re
    assert re.search(r"depois, por volta de \d+:\d\d", linhas[1])
    _escreve(pg, "tr 2 corre pro meio aos 1:30 e tr 2 corre pra b aos 1:25")
    linhas = pg.locator("#pr-cmd-entendi li").all_inner_texts()
    assert linhas[0] == "TR 2 · correndo até Meio · aos 1:30 · cortado pelo comando 2", linhas            # a chegada que ele dizia não vale mais


def test_pagina_do_site_a_biblioteca_externa_que_nao_carrega_cai_para_sem_arremesso_real(contexto, tmp_path_factory):
    from scripts.build_tactics_page import arquivo_da_pagina, build_html
    pasta = tmp_path_factory.mktemp("externo_c4")
    (pasta / arquivo_da_pagina("de_mirage")).write_text(build_html("de_mirage", biblioteca_externa=True), encoding="utf-8")
    pg = abre(contexto, pasta / arquivo_da_pagina("de_mirage"))                                              # sem o arquivo ao lado
    base = _ponto("de_mirage", "Base TR")
    _peca(pg, base["x"], base["y"])
    _escreve(pg, "tr 2 joga smoke no janelão aos 1:20")
    pg.wait_for_function("() => /Este mapa não tem arremessos reais/.test(document.getElementById('pr-cmd-resultado').textContent)", timeout=15000)
    assert pg.is_enabled("#pr-cmd-aplicar")


def test_o_corte_marca_todos_os_comandos_cortados_mesmo_com_um_depois_no_meio_e_o_caminho_continua_valido(contexto, tmp_path_factory):
    base = _ponto("de_mirage", "Base TR")
    pg = _pagina(contexto, tmp_path_factory)
    _peca(pg, base["x"], base["y"])
    # comando 1 (1:30) corre ao meio; o 2 vem "depois" e corre à B; o 3 (1:25) parte no meio da corrida do 1 e corta os dois
    _escreve(pg, "tr 2 corre pro meio aos 1:30 e depois corre pra b, tr 2 corre pro top of mid aos 1:25")
    linhas = pg.locator("#pr-cmd-entendi li").all_inner_texts()
    assert linhas[0].endswith("cortado pelo comando 3") and "depois, por volta de" in linhas[1] and linhas[1].endswith("cortado pelo comando 3"), linhas
    assert linhas[2].startswith("TR 2 · correndo até Top of Mid · aos 1:25 · chega")                       # o último comando segue valendo
    _aplica(pg)
    pts = interno(pg, "Object.values(S.e3.pecas).flatMap(p => p.pontos).filter(pt => pt.caminho).map(pt => pt.t)")
    assert pts == sorted(pts) and interno(pg, "I.problemas(JSON.parse(JSON.stringify(S.doc)), 1)") == []
    assert interno(pg, "S.doc.operacoes.filter(o => o.tipo === 'cria_caminho').length") == 1                # um caminho só por peça


def test_o_horario_fixo_diz_de_qual_comando_fala_e_quais_ele_corta(contexto, tmp_path_factory):
    a = _ponto("de_mirage", "Base TR")
    pg = _pagina(contexto, tmp_path_factory)
    _peca(pg, a["x"], a["y"])
    # o comando 3 (1:25) vem depois do 2 (corre ao meio, 1:30) e começa no meio da corrida do 1: corta os comandos 1 e 2
    _escreve(pg, "tr 2 corre pro meio aos 1:30 e depois corre pra b, tr 2 corre pro top of mid aos 1:25")
    avisos = pg.locator("#pr-cmd-resultado .pr-cmd-aviso").all_inner_texts()
    assert any(re.fullmatch(r"O comando 3 tem horário fixo \(1:25\): ele corta os comandos 1 e 2, mesmo que o TR 2 ainda não tenha chegado\.", t) for t in avisos), avisos
    _escreve(pg, "tr 2 corre pro meio aos 1:30 e tr 2 corre pra b aos 1:10")
    avisos = pg.locator("#pr-cmd-resultado .pr-cmd-aviso").all_inner_texts()
    assert not any("desta ação" in t for t in avisos), avisos                                # o texto genérico, sem dizer o comando, não existe mais


def test_a_peca_fora_de_qualquer_area_comeca_perto_do_lugar_mais_perto(contexto, tmp_path_factory):
    pg = _pagina(contexto, tmp_path_factory)
    _peca(pg, 4000, 4000)                                                                    # longe de tudo: nenhuma área, nenhum ponto a 150 u
    assert interno(pg, "I.lugarExibido(4000, 4000, 0)") is None
    roteiro = " | ".join(pg.locator("#pr-roteiro .pr-evento-texto").all_inner_texts())
    assert re.search(r"TR 2 começa perto de \S", roteiro), roteiro
    # o mais perto vem do dado: o ponto do Pedro ou a âncora de área de menor distância
    from scripts.comandos_contexto import contexto as c
    cx = c("de_mirage", so_conferidos=True)
    cands = [(math.hypot(q["x"] - 4000, q["y"] - 4000), q["nome"]) for q in cx["pontos"]] + [(math.hypot(q["x"] - 4000, q["y"] - 4000), q["exibe"]) for q in cx["areas"]]
    esperado = min(cands)[1]
    assert f"TR 2 começa perto de {esperado}" in roteiro, (roteiro, esperado)


def test_corrida_seguida_de_granada_parte_de_onde_a_peca_termina_o_comando_anterior(contexto, tmp_path_factory):
    # "corre pro meio ... e depois joga": a corrida até o lugar de saída parte do MEIO (o fim do comando anterior), e a granada só sai quando a peça chega (a 250 u/s)
    pg = _pagina(contexto, tmp_path_factory)
    base = _ponto("de_mirage", "Base TR")
    _peca(pg, base["x"], base["y"])
    _escreve(pg, "tr 2 corre pro meio aos 1:50 e depois joga smoke na Areia")
    for escolha in ("levar", "tarde"):
        if pg.locator("[data-escolha=%s]" % escolha).count():
            pg.click("[data-escolha=%s]" % escolha)
    assert pg.is_enabled("#pr-cmd-aplicar")
    _aplica(pg)
    ops = interno(pg, "S.doc.operacoes.filter(o => o.tipo === 'cria_granada' || o.tipo === 'cria_caminho').map(o => o.tipo === 'cria_granada' ? { g: true, t: o.t, origem: o.origem } : { pts: o.pontos.map(p => [p.t, p.x, p.y]) })")
    g = next(o for o in ops if o.get("g"))
    pts = next(o for o in ops if not o.get("g"))["pts"]
    (t0, x0, y0), (t1, x1, y1) = pts[-2], pts[-1]
    assert abs(t1 - g["t"]) < 0.02 and math.hypot(x1 - g["origem"][0], y1 - g["origem"][1]) < 1      # a corrida termina no lugar de saída, na hora em que a granada sai
    assert math.hypot(x1 - x0, y1 - y0) / (t1 - t0) <= 250.5                                         # e o último trecho não passa da velocidade da corrida (antes saía de um ponto do meio da corrida anterior)
