"""C3: a aba Comandos com o tempo REAL de corrida do corpus: entre pontos do Pedro, entre áreas da demo, o estimado corrigido pelo fator do mapa, a troca de andar
com tempo real, o carregamento do arquivo, e a peça que ainda anda quando outro comando começa (o caso que ficou da C2)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")

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
    pg.click("#pr-cmd-aplicar")
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
    pg.click("#pr-cmd-aplicar")
    assert abs(_caminho_do_ultimo_comando(pg)[-1][0] - (25 + par[3])) < 0.011


def test_andando_ou_agachado_continua_estimado_e_com_o_fator_do_mapa(contexto, tmp_path_factory):
    t, ka, linha, a = _linha_dos_pontos("de_mirage", "Base TR", "Meio")
    fator = f"{t['fator']['valor']:.2f}".replace(".", ",")
    pg = _pagina(contexto, tmp_path_factory)
    _peca(pg, a["x"], a["y"])
    _escreve(pg, "tr 2 anda até o meio aos 1:30")                                           # o corpus só mede quem corre
    texto = pg.locator("#pr-cmd-entendi li").all_inner_texts()[0]
    assert "estimado: linha reta corrigida pelo desvio medido no mapa" in texto and f"{fator}×" in texto and "tempo real" not in texto


def test_mapa_sem_fator_diz_que_e_linha_reta_pura(contexto, tmp_path_factory):
    assert not (RAIZ / "data" / "tempos" / "de_overpass.json").exists()                     # 2 partidas: sem par com amostra, sem fator
    pg = _pagina(contexto, tmp_path_factory, "de_overpass")
    from scripts.comandos_contexto import contexto as c
    areas = c("de_overpass")["areas"]
    assert len(areas) >= 2
    _peca(pg, areas[0]["x"], areas[0]["y"])
    _escreve(pg, f"tr 2 corre pro {areas[1]['nome']} aos 1:30")
    texto = pg.locator("#pr-cmd-entendi li").all_inner_texts()[0]
    assert "estimado: linha reta, sem correção" in texto and "poucos dados neste mapa" in texto


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
    pg.click("#pr-cmd-aplicar")
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
    pg.click("#pr-cmd-aplicar")
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
