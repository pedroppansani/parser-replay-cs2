"""C3: a aba Comandos com o tempo REAL de corrida do corpus: entre pontos do Pedro, entre áreas da demo, o estimado corrigido pelo fator do mapa, a troca de andar
com tempo real, o carregamento do arquivo, e a peça que ainda anda quando outro comando começa (o caso que ficou da C2)."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")

from tests.test_comandos_aba import _aplica, _sem_arremesso_real  # noqa: E402
from tests.test_tactics_browser import (  # noqa: E402,F401  (fixtures e ajudas)
    abre, aba_do_painel, contexto, interno, navegador, pagina_do_mapa)

RAIZ = Path(__file__).resolve().parents[1]


def _tabela(mapa):
    return json.loads((RAIZ / "data" / "tempos" / f"{mapa}.json").read_text(encoding="utf-8"))


def _pagina(contexto, tmp_path_factory, mapa="de_mirage"):
    pg = abre(contexto, pagina_do_mapa(tmp_path_factory, mapa))
    pg.set_viewport_size({"width": 1440, "height": 900})
    return pg


def _peca(pg, x, y, nivel=0, lado="t", rotulo="2"):
    pg.evaluate("""([x, y, nivel, lado, rotulo]) => { const I = Prancheta._interno, S = I.S;
        I.emiteLote([["cria_peca", { peca: "demo-" + lado + rotulo, lado: lado, rotulo: rotulo, passo: S.estado.passos[0].passo, x: x, y: y, nivel: nivel }]]); }""", [x, y, nivel, lado, rotulo])


def _escreve(pg, frase):
    aba_do_painel(pg, "comandos")
    pg.fill("#pr-cmd-texto", frase)
    pg.click("#pr-cmd-entender")


def _ponto(mapa, nome):
    from scripts.comandos_contexto import contexto as c
    return next(p for p in c(mapa, so_conferidos=True)["pontos"] if p["nome"] == nome)


def _linha_dos_pontos(mapa, nome_a, nome_b):
    """A linha da tabela entre dois pontos de nome único (o nó de A é o que está nas coordenadas do ponto)."""
    t = _tabela(mapa)
    a, b = _ponto(mapa, nome_a), _ponto(mapa, nome_b)
    chave = {(x, y): k for k, x, y, _ in t["nos"]}
    return t, chave[(a["x"], a["y"])], next(r for r in t["pontos"] if r[0] == chave[(a["x"], a["y"])] and r[1] == chave[(b["x"], b["y"])]), a


def _caminho_do_ultimo_comando(pg):
    return interno(pg, "Object.values(S.e3.pecas).flatMap(p => p.pontos).filter(pt => pt.caminho).map(pt => [pt.t, Math.round(pt.x), Math.round(pt.y)])")


def test_entre_pontos_do_pedro_mostra_a_faixa_os_casos_e_aplica_a_mediana(contexto, tmp_path_factory):
    t, ka, linha, a = _linha_dos_pontos("de_mirage", "Base TR", "Meio")
    pg = _pagina(contexto, tmp_path_factory)
    _peca(pg, a["x"], a["y"])
    _escreve(pg, "tr 2 corre pro meio aos 1:30")
    texto = pg.locator("#pr-cmd-entendi li").all_inner_texts()[0]
    assert "tempo real entre os pontos" in texto and f"{linha[5]} casos em {linha[6]} partidas" in texto and "estimado" not in texto
    assert " entre " in texto and "por volta de" in texto
    _aplica(pg)
    ultimo = _caminho_do_ultimo_comando(pg)[-1]
    assert abs(ultimo[0] - (115 - 90 + linha[3])) < 0.011                                    # o Aplicar usa a MEDIANA como chegada
    assert interno(pg, "I.problemas(JSON.parse(JSON.stringify(S.doc)), 1)") == []


def test_faixa_que_cabe_num_segundo_nao_diz_entre_1_24_e_1_24(contexto, tmp_path_factory):
    import re
    from scripts.comandos_contexto import contexto as c
    t = _tabela("de_dust2")
    pts = c("de_dust2", so_conferidos=True)["pontos"]
    a, b = next(p for p in pts if p["nome"] == "Base TR"), next(p for p in pts if p["nome"] == "Fora do Escuro")
    chave = {(x, y): k for k, x, y, _ in t["nos"]}
    linha = next(r for r in t["pontos"] if r[0] == chave[(a["x"], a["y"])] and r[1] == chave[(b["x"], b["y"])])
    assert linha[5] >= 200 and linha[4] - linha[2] < 1.0                                     # 243 casos, faixa de meio segundo: o exemplo de números da Dust2
    pg = _pagina(contexto, tmp_path_factory, "de_dust2")
    _peca(pg, a["x"], a["y"])
    _escreve(pg, "tr 2 corre pro fora do escuro aos 1:30")
    texto = pg.locator("#pr-cmd-entendi li").all_inner_texts()[0]
    assert f"{linha[5]} casos em {linha[6]} partidas" in texto and not re.search(r"entre (\S+) e ", texto) and "por volta de" in texto, texto


def test_entre_areas_da_demo_quando_nao_ha_par_de_pontos(contexto, tmp_path_factory):
    from scripts.comandos_contexto import contexto as c
    ctx = c("de_mirage")
    t = _tabela("de_mirage")
    area = {a["nome"]: a for a in ctx["areas"]}
    par = next(r for r in t["areas"] if r[0] == "TSpawn" and r[1] == "TopofMid")
    pg = _pagina(contexto, tmp_path_factory)
    _peca(pg, area["TSpawn"]["x"], area["TSpawn"]["y"])
    _escreve(pg, "tr 2 corre pro top of mid aos 1:30")
    texto = pg.locator("#pr-cmd-entendi li").all_inner_texts()[0]
    assert "tempo real entre as áreas da demo" in texto and f"{par[5]} casos em {par[6]} partidas" in texto, texto
    _aplica(pg)
    assert abs(_caminho_do_ultimo_comando(pg)[-1][0] - (25 + par[3])) < 0.011


def test_troca_de_andar_com_tempo_real_nao_pergunta_a_chegada(contexto, tmp_path_factory):
    from scripts.comandos_contexto import contexto as c
    t = _tabela("de_nuke")
    ar = {a["nome"]: a for a in c("de_nuke")["areas"]}
    par = next(r for r in t["areas"] if ar[r[0]]["andar"] in ("cima", "baixo") and ar[r[1]]["andar"] in ("cima", "baixo") and ar[r[0]]["andar"] != ar[r[1]]["andar"])
    pg = _pagina(contexto, tmp_path_factory, "de_nuke")
    _peca(pg, ar[par[0]]["x"], ar[par[0]]["y"], 1 if ar[par[0]]["andar"] == "baixo" else 0)
    _escreve(pg, f"tr 2 corre pro {ar[par[1]]['nome']} aos 1:30")
    assert pg.locator(".pr-cmd-pergunta").count() == 0, pg.inner_text("#pr-cmd-resultado")      # nada de "Quando chega?"
    texto = pg.locator("#pr-cmd-entendi li").all_inner_texts()[0]
    assert "tempo real entre as áreas da demo" in texto and f"{par[5]} casos em {par[6]} partidas" in texto
    assert pg.is_enabled("#pr-cmd-aplicar")


def test_a_peca_que_ainda_anda_parte_do_ponto_por_onde_passava(contexto, tmp_path_factory):
    t, ka, linha, a = _linha_dos_pontos("de_mirage", "Base TR", "Meio")
    meio = _ponto("de_mirage", "Meio")
    pg = _pagina(contexto, tmp_path_factory)
    _peca(pg, a["x"], a["y"])
    # a corrida começa em 1:30 (t = 25) e dura `mediana` s; a smoke sai em 1:25 (t = 30), 5 s depois, no meio da corrida
    _escreve(pg, "tr 2 corre pro meio aos 1:30 e joga smoke na b aos 1:25")
    _aplica(pg)
    g = interno(pg, "Object.values(S.e3.granadas)[0]")
    f = 5 / linha[3]
    esperado = [a["x"] + (meio["x"] - a["x"]) * f, a["y"] + (meio["y"] - a["y"]) * f]
    assert abs(g["t"] - 30) < 0.011 and abs(g["origem"][0] - esperado[0]) < 2 and abs(g["origem"][1] - esperado[1]) < 2, (g["origem"], esperado)


def test_um_segundo_comando_no_meio_da_corrida_corta_o_caminho_e_segue_dali(contexto, tmp_path_factory):
    t, ka, linha, a = _linha_dos_pontos("de_mirage", "Base TR", "Meio")
    meio = _ponto("de_mirage", "Meio")
    pg = _pagina(contexto, tmp_path_factory)
    _peca(pg, a["x"], a["y"])
    _escreve(pg, "tr 2 corre pro meio aos 1:30 e tr 2 corre pra b aos 1:25")
    _aplica(pg)
    pts = _caminho_do_ultimo_comando(pg)
    assert [p[0] for p in pts] == sorted(p[0] for p in pts)                                  # uma linha do tempo só, sem volta
    f = 5 / linha[3]
    corte = next(p for p in pts if abs(p[0] - 30) < 0.011)                                   # o ponto por onde ela passava aos 1:25
    assert abs(corte[1] - (a["x"] + (meio["x"] - a["x"]) * f)) < 2
    assert not any(abs(p[1] - meio["x"]) < 2 and abs(p[2] - meio["y"]) < 2 for p in pts)     # ela não chegou ao meio: o caminho foi cortado
    assert interno(pg, "I.problemas(JSON.parse(JSON.stringify(S.doc)), 1)") == []


def test_o_arquivo_dos_tempos_carrega_so_ao_abrir_a_aba_e_a_falha_cai_para_o_estimado(contexto, tmp_path_factory):
    from scripts.build_tactics_page import arquivo_da_pagina, arquivo_dos_tempos, build_html, tempos_js
    pasta = tmp_path_factory.mktemp("externo")
    (pasta / arquivo_da_pagina("de_mirage")).write_text(build_html("de_mirage", biblioteca_externa=True), encoding="utf-8")
    pg = abre(contexto, pasta / arquivo_da_pagina("de_mirage"))                              # sem o arquivo ao lado: a falha
    recursos = "() => performance.getEntriesByType('resource').map(r => r.name).filter(n => n.includes('tempos/'))"
    assert pg.evaluate(recursos) == []                                                        # nada pedido antes de abrir a aba
    t, ka, linha, a = _linha_dos_pontos("de_mirage", "Base TR", "Meio")
    _peca(pg, a["x"], a["y"])
    _escreve(pg, "tr 2 corre pro meio aos 1:30")
    pg.wait_for_selector("#pr-cmd-sem-tempos")
    assert "estimado" in pg.locator("#pr-cmd-entendi li").all_inner_texts()[0] and pg.is_enabled("#pr-cmd-aplicar")
    # com o arquivo ao lado: o tempo real
    (pasta / arquivo_dos_tempos("de_mirage")).parent.mkdir(exist_ok=True)
    (pasta / arquivo_dos_tempos("de_mirage")).write_text(tempos_js("de_mirage"), encoding="utf-8")
    pg2 = abre(contexto, pasta / arquivo_da_pagina("de_mirage"))
    _peca(pg2, a["x"], a["y"])
    _escreve(pg2, "tr 2 corre pro meio aos 1:30")
    pg2.wait_for_function("() => document.querySelector('#pr-cmd-entendi li') && /tempo real/.test(document.querySelector('#pr-cmd-entendi li').textContent)")
    assert not pg2.locator("#pr-cmd-carregando").count()


def test_o_estimado_e_um_piso_andando_usa_a_velocidade_do_jeito_e_correndo_o_teto(contexto, tmp_path_factory):
    import math
    t, ka, linha, a = _linha_dos_pontos("de_mirage", "Base TR", "Meio")
    meio = _ponto("de_mirage", "Meio")
    reta = math.hypot(meio["x"] - a["x"], meio["y"] - a["y"])
    pg = _pagina(contexto, tmp_path_factory)
    _peca(pg, a["x"], a["y"])
    _escreve(pg, "tr 2 anda até o meio aos 1:30")                                           # o corpus só mede quem corre: andando é estimado
    texto = pg.locator("#pr-cmd-entendi li").all_inner_texts()[0]
    assert "chega não antes de" in texto and "estimado: linha reta; o caminho real costuma ser mais longo" in texto and "tempo real" not in texto
    assert "fator" not in texto and "sem correção" not in texto and "0,96" not in texto
    _aplica(pg)
    assert abs(_caminho_do_ultimo_comando(pg)[-1][0] - (25 + reta / interno(pg, "I.velocidade(null, 'andando')"))) < 0.02     # a velocidade constante de andar


def test_correndo_sem_par_com_amostra_o_piso_usa_o_teto_de_250(contexto, tmp_path_factory):
    import math
    from scripts.comandos_contexto import contexto as c
    areas = c("de_overpass")["areas"]
    assert not (RAIZ / "data" / "tempos" / "de_overpass.json").exists()                     # 2 partidas: sem tempo real nenhum
    pg = _pagina(contexto, tmp_path_factory, "de_overpass")
    _peca(pg, areas[0]["x"], areas[0]["y"])
    _escreve(pg, f"tr 2 corre pro {areas[1]['nome']} aos 1:30")
    texto = pg.locator("#pr-cmd-entendi li").all_inner_texts()[0]
    assert "chega não antes de" in texto and "bem mais quando contorna paredes" in texto and "poucos dados" not in texto
    _aplica(pg)
    reta = math.hypot(areas[1]["x"] - areas[0]["x"], areas[1]["y"] - areas[0]["y"])
    assert abs(_caminho_do_ultimo_comando(pg)[-1][0] - (25 + reta / 250.0)) < 0.02


def _ops_sem_ids(pg):
    """As operações do que foi aplicado, sem ids e em ordem estável: o que importa é o roteiro, não a ordem em que as frases foram escritas."""
    ops = interno(pg, "S.doc.operacoes.filter(o => o.tipo === 'cria_granada' || o.tipo === 'cria_caminho').map(o => o.tipo === 'cria_granada' ? ['g', o.arma, o.t, o.origem.map(Math.round), o.destino.map(Math.round)] : ['c', o.pontos.map(p => [p.t, Math.round(p.x), Math.round(p.y)])])")
    return sorted(json.dumps(o) for o in ops)


def test_a_ordem_do_relogio_vale_nao_a_da_escrita(contexto, tmp_path_factory):
    t, ka, linha, a = _linha_dos_pontos("de_mirage", "Base TR", "Meio")
    resultados = []
    for frase in ("tr 2 corre pro meio aos 1:30 e joga smoke na b aos 1:25", "tr 2 joga smoke na b aos 1:25 e corre pro meio aos 1:30"):
        pg = _pagina(contexto, tmp_path_factory)
        _peca(pg, a["x"], a["y"])
        _escreve(pg, frase)
        _aplica(pg)
        resultados.append(_ops_sem_ids(pg))
        pg.close()
    assert resultados[0] == resultados[1]
    g = next(json.loads(o) for o in resultados[0] if json.loads(o)[0] == "g")
    assert g[2] == 30 and g[3] != [round(a["x"]), round(a["y"])]                             # a smoke saiu de onde a peça estava no meio da corrida, não da base


def test_sem_horario_o_comando_fica_preso_ao_anterior_na_escrita_e_empate_vale_a_escrita(contexto, tmp_path_factory):
    t, ka, linha, a = _linha_dos_pontos("de_mirage", "Base TR", "Meio")
    pg = _pagina(contexto, tmp_path_factory)
    _peca(pg, a["x"], a["y"])
    _peca(pg, a["x"] + 100, a["y"], rotulo="3")
    # o "depois" é da smoke do TR 3 (o comando anterior na escrita), mesmo que o do TR 2 seja mais cedo no relógio
    _escreve(pg, "tr 3 joga smoke na b aos 1:10 depois tr 3 corre pro meio, tr 2 corre pro meio aos 1:30")
    _aplica(pg)
    ops = interno(pg, "S.doc.operacoes.filter(o => o.tipo === 'cria_caminho').map(o => [o.peca, o.pontos[o.pontos.length - 1].t])")
    por_peca = {p: t_ for p, t_ in ops}
    assert abs(por_peca["demo-t2"] - (25 + linha[3])) < 0.011                               # TR 2: 1:30, o horário dele
    assert por_peca["demo-t3"] > 45 + 5                                                      # TR 3: só depois da smoke das 1:10 (t = 45), não colado ao TR 2
    pg.close()
    # no MESMO horário vale a ordem da escrita: o mesmo roteiro com as frases trocadas troca só quem vem primeiro, e o resultado por peça não muda
    resultados = []
    for frase in ("tr 2 joga smoke na b aos 1:30 e tr 3 joga flash na b aos 1:30", "tr 3 joga flash na b aos 1:30 e tr 2 joga smoke na b aos 1:30"):
        pg = _pagina(contexto, tmp_path_factory)
        _peca(pg, a["x"], a["y"])
        _peca(pg, a["x"] + 100, a["y"], rotulo="3")
        _escreve(pg, frase)
        _aplica(pg)
        resultados.append(interno(pg, "S.doc.operacoes.filter(o => o.tipo === 'cria_granada').map(o => o.arma)"))
        pg.close()
    assert resultados[0] == ["smoke", "flash"] and resultados[1] == ["flash", "smoke"]


def test_a_mediana_mostrada_nunca_fica_fora_da_faixa_mostrada_e_a_duracao_aparece(contexto, tmp_path_factory):
    import re
    pg = _pagina(contexto, tmp_path_factory)
    aba_do_painel(pg, "comandos")
    assert pg.evaluate("() => [Prancheta._interno.cmdRelogio(119.6), Prancheta._interno.cmdRelogio(59.6), Prancheta._interno.cmdRelogio(60.4), Prancheta._interno.cmdRelogio(0.4)]") == ["2:00", "1:00", "1:00", "0:00"]
    def segundos(h):
        m, s = h.split(":")
        return int(m) * 60 + int(s)
    for mapa in ("de_mirage", "de_dust2", "de_nuke"):
        for fonte in ("pontos", "areas"):
            for a_, b_, p25, med, p75, n, partidas in _tabela(mapa)[fonte][::7]:
                for t0 in (25.0, 25.37, 40.5):
                    c = {"tipo": "real", "fonte": fonte, "t": t0 + med, "t25": t0 + p25, "t75": t0 + p75, "casos": n, "partidas": partidas, "duracao": med}
                    texto = pg.evaluate("c => Prancheta._interno.cmdChegada(c)", c)
                    m = re.search(r"chega (?:entre (\d+:\d\d) e (\d+:\d\d), )?por volta de (\d+:\d\d)", texto)
                    assert m, texto
                    h1, h2, h = m.groups()
                    if h1:
                        assert segundos(h1) >= segundos(h) >= segundos(h2), texto            # o relógio desce: a ponta mais cedo, a mediana no meio, a mais tarde
                    assert f"cerca de {int(med + 0.5)} s" in texto and f"{n} casos em {partidas} partidas" in texto, texto


def test_ponto_do_pedro_tem_o_nome_dele_e_area_da_demo_o_nome_do_jogo_legivel_em_todos_os_mapas(contexto, tmp_path_factory):
    from scripts.comandos_contexto import contexto as c
    # a ÁREA se escreve com o nome do jogo, igual ao do botão "Lugares", conferida ou não: nenhum apelido do Pedro ("Esquina", "L", "Caixa Verde") vira o nome de uma área
    for mapa in ("de_mirage", "de_dust2", "de_overpass"):
        for a in c(mapa, so_conferidos=True)["areas"]:
            assert a["exibe"].upper() == a["texto"], (mapa, a["nome"], a["exibe"])
    ar = {a["nome"]: a for a in c("de_mirage", so_conferidos=True)["areas"]}
    assert ar["TSpawn"]["exibe"] == "T Spawn" and ar["TopofMid"]["exibe"] == "Top of Mid" and ar["Catwalk"]["exibe"] == "Catwalk"
    base = _ponto("de_mirage", "Base TR")
    pg = _pagina(contexto, tmp_path_factory)
    _peca(pg, base["x"], base["y"])                                                          # o início é um ponto do Pedro: aparece o nome dele
    textos = []
    for frase in ("tr 2 corre pro top of mid aos 1:30", "tr 2 corre pro TopofMid aos 1:30", "tr 2 corre pro meio aos 1:30"):
        _escreve(pg, frase)
        textos.append(pg.locator("#pr-cmd-entendi li").all_inner_texts()[0].split(" · ")[1])
    assert textos[0] == textos[1] == "correndo até Top of Mid" and textos[2] == "correndo até Meio", textos      # área: o nome do jogo; ponto: o do Pedro
    _escreve(pg, "tr 2 corre pro top of mid aos 1:30")
    _aplica(pg)
    roteiro = " | ".join(pg.locator("#pr-roteiro .pr-evento-texto").all_inner_texts())
    assert "começa em Base TR" in roteiro and "TSpawn" not in roteiro and "TopofMid" not in roteiro, roteiro
    # Overpass (nenhum ponto conferido): o nome do jogo, legível, também no roteiro
    ov = {a["nome"]: a for a in c("de_overpass", so_conferidos=True)["areas"]}
    assert ov["BackofA"]["exibe"] == "Back of A" and ov["TSpawn"]["exibe"] == "T Spawn"
    pg2 = _pagina(contexto, tmp_path_factory, "de_overpass")
    _peca(pg2, ov["TSpawn"]["x"], ov["TSpawn"]["y"])
    _escreve(pg2, "tr 2 corre pro BackofA aos 1:30")
    assert pg2.locator("#pr-cmd-entendi li").all_inner_texts()[0].startswith("TR 2 · correndo até Back of A")
    _aplica(pg2)
    roteiro2 = " | ".join(pg2.locator("#pr-roteiro .pr-evento-texto").all_inner_texts())
    assert "começa em T Spawn" in roteiro2 and "chega em Back of A" in roteiro2 and "BackofA" not in roteiro2, roteiro2


def test_na_mirage_top_of_mid_aparece_como_top_of_mid_e_nao_como_esquina(contexto, tmp_path_factory):
    base = _ponto("de_mirage", "Base TR")
    pg = _pagina(contexto, tmp_path_factory)
    _peca(pg, base["x"], base["y"])
    _escreve(pg, "tr 2 corre pro top of mid")
    assert "Top of Mid" in pg.inner_text("#pr-cmd-entendi") and "Esquina" not in pg.inner_text("#pr-cmd-entendi")


def test_a_granada_que_sobra_depois_do_corte_e_mantida_e_o_cartao_avisa(contexto, tmp_path_factory):
    t, ka, linha, a = _linha_dos_pontos("de_mirage", "Base TR", "Meio")
    pg = _pagina(contexto, tmp_path_factory)
    _peca(pg, a["x"], a["y"])
    # comando 1: corre ao meio (chega em t = 25 + mediana); comando 2: a smoke, depois de chegar; comando 3 (1:25, t = 30): corta a corrida no meio do caminho
    _escreve(pg, "tr 2 corre pro meio aos 1:30 e depois joga smoke na b, tr 2 corre pra b aos 1:25")
    _sem_arremesso_real(pg)
    avisos = pg.locator("#pr-cmd-resultado [data-aviso=corte]").all_inner_texts()
    assert len(avisos) == 1 and re.fullmatch(r"O comando 3 corta o caminho do comando 1\. A smoke das \d+:\d\d foi mantida: confira se ainda faz sentido\.", avisos[0]), avisos
    assert pg.is_enabled("#pr-cmd-aplicar")                                                  # só avisa: quem decide é a pessoa
    _aplica(pg)
    assert interno(pg, "Object.keys(S.e3.granadas).length") == 1                             # nada foi apagado
    # sem granada depois do corte, nenhum aviso
    _escreve(pg, "tr 3 corre pro meio aos 1:30 e tr 3 corre pra b aos 1:25")
    _sem_arremesso_real(pg)
    assert pg.locator("#pr-cmd-resultado [data-aviso=corte]").count() == 0
