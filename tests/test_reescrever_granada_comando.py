"""Reescrever CR3: a granada por comando ("FalleN joga smoke no janelão aos 0:57"), em cima do round 23 da match_43 com "Reescrever daqui" em 1:20 (o quadro 140).

A decisão (a) da CR0: o comando só TROCA uma granada que o jogador jogou de verdade neste round (o dado não tem inventário, então o site nunca cria uma granada nova) por um
arremesso real da biblioteca (o mesmo tipo e o mesmo lado, que cai a até 150 u do destino). Os casos que a biblioteca real não tem (só arremessos do outro lado, nenhum perto do
destino, voo desconhecido) usam uma biblioteca sintética, escrita ao lado da página como no site.

As granadas reais do round 23 depois de 1:20: apEX flash (1:19), molodoy smoke (1:21), FalleN smoke (0:57) e HE (0:37), mezii flash (0:55 e 0:50) e molotov (0:44), ZywOo smoke (0:54),
KSCERATO flash (0:37) e HE (0:34). ropz jogou uma smoke às 1:55, antes do instante; mezii não jogou smoke."""
from __future__ import annotations

import json
import math

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_reescrever_comandos import (  # noqa: E402,F401  (fixtures e ajudas)
    CLS_TOTAL, _abre_no_instante, _abre_secao, _aplica, _cartao, _escreve, _opcao, _pecas, _sem_tela)
from tests.test_reescrever_modo import PARTIDA, RAIZ, RECT, _estado, navegador  # noqa: E402,F401

MAPA = "de_mirage"
PRONTA = "() => window.__reescrever().trocas.biblioteca === 'pronta'"
SEM_ARREMESSO = "Pôr a granada sem arremesso real"      # isso só existe na prancheta


def _pagina(tmp_path_factory, nome, modifica=None):
    """A página da partida com os arquivos dos comandos e a biblioteca de arremessos ao lado, como no site; `modifica(dados)` muda a biblioteca (a sintética)."""
    from scripts.build_reescrever_comandos import escreve
    from scripts.build_site import match_summary, times_das_partidas
    from scripts.build_tactics_page import arquivo_da_biblioteca
    from scripts.build_web_page import build_html
    d = tmp_path_factory.mktemp(nome)
    arq = d / f"{PARTIDA}.html"
    arq.write_text(build_html(PARTIDA), encoding="utf-8")
    escreve(d, [MAPA])
    dados = json.loads((RAIZ / "data" / "lineups" / f"{MAPA}.json").read_text(encoding="utf-8"))
    ids = sorted({a["partida"] for a in dados["arremessos"]})
    dados["partidas_times"] = {p: t for p, t in times_das_partidas([s for s in (match_summary(i) for i in ids) if s]).items() if p in ids}
    if modifica:
        modifica(dados)
    destino = d / arquivo_da_biblioteca(MAPA)
    destino.parent.mkdir(exist_ok=True)
    destino.write_text("Prancheta.recebeBiblioteca(" + json.dumps(dados, ensure_ascii=False) + ");\n", encoding="utf-8")
    return arq


def _janelao():
    from scripts.comandos_contexto import _pontos
    return [p for p in _pontos(MAPA, True) if p["nome"] == "Janelão"]


def _perto_do_janelao(a, raio):
    return any(math.hypot(a["destino"][0] - p["x"], a["destino"][1] - p["y"]) <= raio for p in _janelao())


@pytest.fixture(scope="module")
def pagina_gr(tmp_path_factory):
    if not (RAIZ / "data" / "processed" / PARTIDA / "web_payload.json").exists():
        pytest.skip("sem o processado")
    return _pagina(tmp_path_factory, "gr")


@pytest.fixture(scope="module")
def pagina_so_tr(tmp_path_factory):
    """Só arremessos de TR: quem é CT não tem nenhum do lado certo."""
    return _pagina(tmp_path_factory, "so_tr", lambda d: d.update(arremessos=[a for a in d["arremessos"] if a["lado"] == "t"]))


@pytest.fixture(scope="module")
def pagina_sem_destino(tmp_path_factory):
    """Nenhum arremesso cai a menos de 700 u do Janelão."""
    return _pagina(tmp_path_factory, "sem_destino", lambda d: d.update(arremessos=[a for a in d["arremessos"] if not _perto_do_janelao(a, 700)]))


@pytest.fixture(scope="module")
def pagina_voo_nulo(tmp_path_factory):
    """Os arremessos que caem no Janelão perdem o tempo de voo (e o de efeito): o voo é desconhecido."""
    def sem_voo(d):
        for a in d["arremessos"]:
            if _perto_do_janelao(a, 700):
                a["voo_s"] = None
                a["efeito_s"] = None
    return _pagina(tmp_path_factory, "voo_nulo", sem_voo)


@pytest.fixture(scope="module")
def biblioteca():
    return {a["id"]: a for a in json.loads((RAIZ / "data" / "lineups" / f"{MAPA}.json").read_text(encoding="utf-8"))["arremessos"]}


def _espera_biblioteca(pg):
    pg.wait_for_function(PRONTA)
    pg.wait_for_timeout(250)


def _foto(pg):
    """Tudo que um comando que não aplica não pode mexer: peças (sem a posição na tela), trocas, o que está no ar, o Desfazer e o texto de "O que mudou"."""
    e = _estado(pg)
    return {"pecas": _sem_tela(e["pecas"]), "trocas": e["trocas"]["trocas"], "virtuais": e["trocas"]["virtuais"], "desfazer": e["comandos"]["desfazer"], "mudou": pg.inner_text("#rw-mudou")}


def _forca_aplicar(pg):
    pg.evaluate("() => document.getElementById('rw-cmd-aplicar').click()")      # nem à força (o botão está desligado)
    pg.wait_for_timeout(150)


def _decide(pg):
    """Responde às perguntas da saída ([Levar até lá], [Jogar às H]) até o Aplicar ligar."""
    for rotulo in ("Levar o", "Jogar às"):
        while pg.locator("#rw-cmd-cartao button", has_text=rotulo).count():
            _opcao(pg, rotulo)


def _frase_aplicada(pg, frase):
    _escreve(pg, frase)
    _espera_biblioteca(pg)
    _decide(pg)
    _aplica(pg)
    return _estado(pg)


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# qual granada é trocada: só uma que o jogador jogou de verdade
# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def test_nenhuma_granada_e_criada_sem_uma_real_do_mesmo_tipo_e_do_mesmo_jogador(navegador, pagina_gr):
    ctx, pg, erros = _abre_no_instante(navegador, pagina_gr)
    try:
        _abre_secao(pg)
        antes = _foto(pg)
        _escreve(pg, "YEKINDAR joga smoke no janelão aos 1:10")                  # YEKINDAR não jogou nenhuma smoke neste round
        assert "No real, YEKINDAR não jogou smoke neste round. O site não sabe se ele tinha uma." in _cartao(pg)
        assert pg.locator("#rw-cmd-cartao [data-codigo='gr_nao_jogou'] button").all_inner_texts() == ["Corrigir"]
        assert pg.is_disabled("#rw-cmd-aplicar")
        _forca_aplicar(pg)
        assert _foto(pg) == antes and SEM_ARREMESSO not in _cartao(pg) and "ainda não está pronto" not in _cartao(pg)
        _escreve(pg, "molodoy joga flash no meio aos 1:10")                      # molodoy jogou smoke, nenhuma flash: o tipo conta
        assert "No real, molodoy não jogou flash neste round. O site não sabe se ele tinha uma." in _cartao(pg)
        _escreve(pg, "ropz joga smoke no meio aos 1:10 e corre pro B")           # nem a parte que seria só de movimento
        assert pg.is_disabled("#rw-cmd-aplicar")
        _forca_aplicar(pg)
        assert _foto(pg) == antes
        pg.click("#rw-cmd-cartao [data-codigo='gr_antes'] button")               # [Corrigir] devolve o campo
        assert pg.evaluate("document.activeElement.id") == "rw-cmd-texto"
        assert erros == []
    finally:
        ctx.close()


def test_a_granada_real_que_saiu_antes_do_instante_e_recusada_dizendo_o_horario(navegador, pagina_gr):
    ctx, pg, _ = _abre_no_instante(navegador, pagina_gr)
    try:
        _abre_secao(pg)
        antes = _foto(pg)
        _escreve(pg, "ropz joga smoke no meio aos 1:05")                         # a smoke do ropz foi às 1:55, antes de 1:20 (já faz parte do real)
        assert ("No real, ropz jogou smoke às 1:55, antes de 1:20, onde a sua versão começa. Ela já faz parte do real: o comando não a troca.") in _cartao(pg)
        assert pg.locator("#rw-cmd-cartao [data-codigo='gr_antes'] button").all_inner_texts() == ["Corrigir"]
        assert pg.is_disabled("#rw-cmd-aplicar")
        _forca_aplicar(pg)
        assert _foto(pg) == antes
    finally:
        ctx.close()


def test_quando_ele_jogou_mais_de_uma_o_cartao_pergunta_qual_com_o_horario_e_o_lugar_reais(navegador, pagina_gr):
    ctx, pg, _ = _abre_no_instante(navegador, pagina_gr)
    try:
        _abre_secao(pg)
        _escreve(pg, "mezii joga flash no meio aos 1:10")
        assert "mezii jogou 2 flash depois de 1:20. Qual delas o comando troca?" in _cartao(pg)
        botoes = pg.locator("#rw-cmd-cartao [data-codigo='gr_qual'] button").all_inner_texts()
        assert len(botoes) == 2 and botoes[0].startswith("flash das 0:55 em ") and botoes[1].startswith("flash das 0:50 em ")      # um botão por granada: o horário e o lugar reais, na ordem em que saíram
        assert pg.is_disabled("#rw-cmd-aplicar") and pg.evaluate("document.activeElement.classList.contains('rw-cmd-opcao')")
        _opcao(pg, "flash das 0:50")
        _espera_biblioteca(pg)
        assert "Qual delas" not in _cartao(pg)
        _decide(pg)
        _aplica(pg)
        e = _estado(pg)
        assert [(t["by"], t["k"], t["f0"]) for t in e["trocas"]["trocas"]] == [("mezii", "flash", 260)]      # a segunda (0:50 = 65 s = quadro 260), não a primeira
    finally:
        ctx.close()


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# o arremesso novo: o mesmo tipo, o mesmo lado, a até 150 u do destino; sem arremesso real, recusa (e nada de "pôr a granada sem arremesso real")
# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def test_o_arremesso_novo_e_do_mesmo_tipo_e_do_mesmo_lado_e_cai_a_ate_150_u_do_destino(navegador, pagina_gr, biblioteca):
    ctx, pg, _ = _abre_no_instante(navegador, pagina_gr)
    try:
        _abre_secao(pg)
        e = _frase_aplicada(pg, "FalleN joga smoke no janelão aos 0:57")         # FalleN é CT
        t = e["trocas"]["trocas"][0]
        a = biblioteca[t["alt"]]
        assert a["arma"] == "smoke" and a["lado"] == "ct" and t["cmd"] and t["lado"] == "ct"
        assert min(math.hypot(a["destino"][0] - p["x"], a["destino"][1] - p["y"]) for p in _janelao()) <= 150
        assert (t["by"], t["k"], t["f0"]) == ("FalleN", "smoke", 232)            # a smoke dele das 0:57 (58 s = quadro 232) é a que se troca
        pg.click("#rw-desfazer")
        e = _frase_aplicada(pg, "apEX joga flash no meio aos 1:10")              # apEX é TR
        t = e["trocas"]["trocas"][0]
        a = biblioteca[t["alt"]]
        assert a["arma"] == "flash" and a["lado"] == "t" and (t["by"], t["k"]) == ("apEX", "flash")
    finally:
        ctx.close()


def test_so_ha_arremesso_do_outro_lado_o_comando_e_recusado_e_nada_muda(navegador, pagina_so_tr):
    ctx, pg, _ = _abre_no_instante(navegador, pagina_so_tr)
    try:
        _abre_secao(pg)
        antes = _foto(pg)
        _escreve(pg, "FalleN joga smoke no janelão aos 0:57")                    # FalleN é CT e a biblioteca só tem TR
        _espera_biblioteca(pg)
        assert "Não achei arremesso real de CT com smoke que caia em Janelão. O Reescrever só troca a granada por um arremesso real, então nada muda." in _cartao(pg)
        assert pg.locator("#rw-cmd-cartao [data-codigo='gr_sem_real'] button").all_inner_texts() == ["Corrigir"]
        assert SEM_ARREMESSO not in _cartao(pg) and pg.is_disabled("#rw-cmd-aplicar")
        _forca_aplicar(pg)
        assert _foto(pg) == antes
    finally:
        ctx.close()


def test_sem_arremesso_real_para_o_destino_o_comando_e_recusado_e_nada_muda(navegador, pagina_sem_destino):
    ctx, pg, _ = _abre_no_instante(navegador, pagina_sem_destino)
    try:
        _abre_secao(pg)
        antes = _foto(pg)
        _escreve(pg, "FalleN joga smoke no janelão aos 0:57")
        _espera_biblioteca(pg)
        assert "Não achei arremesso real de CT com smoke que caia em Janelão." in _cartao(pg) and SEM_ARREMESSO not in _cartao(pg)
        assert pg.is_disabled("#rw-cmd-aplicar")
        _forca_aplicar(pg)
        assert _foto(pg) == antes
        _escreve(pg, "FalleN joga he na poltrona aos 1:20")                      # a HE dele vai para outro destino, que tem arremesso real: o comando segue
        _espera_biblioteca(pg)
        assert "Não achei arremesso real" not in _cartao(pg)
    finally:
        ctx.close()


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# a hora, a saída longe, a chegada tardia, a morte real, o Desfazer e a frase mista
# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def test_levar_ate_la_e_desfazer_volta_exatamente_ao_estado_de_antes(navegador, pagina_gr):
    ctx, pg, _ = _abre_no_instante(navegador, pagina_gr)
    try:
        _abre_secao(pg)
        antes = _foto(pg)
        _escreve(pg, "FalleN joga smoke no janelão aos 0:57")
        _espera_biblioteca(pg)
        assert "FalleN (CT 2) está a cerca de 3 s correndo (663 u) do lugar de saída 1 de 3 (Snipers Nest). O que fazer?" in _cartao(pg)      # o lugar de saída é longe da peça
        assert pg.locator("#rw-cmd-cartao [data-codigo='gr_longe'] button").all_inner_texts() == ["Levar o FalleN até lá", "Usar outro arremesso"]      # sem "pôr a granada sem arremesso real"
        assert pg.is_disabled("#rw-cmd-aplicar")
        _opcao(pg, "Levar o FalleN até lá")
        assert not pg.is_disabled("#rw-cmd-aplicar") and "lugar de saída 1 de 3 (CT)" in _cartao(pg)
        _aplica(pg)
        e = _estado(pg)
        assert e["comandos"]["desfazer"] == 1 and len(e["trocas"]["trocas"]) == 1 and _pecas(pg)["FalleN"]["editada"]      # a peça foi até o lugar de saída e a granada foi trocada
        mudou = pg.inner_text("#rw-mudou")
        assert "FalleN troca a smoke das 0:57 em " in mudou and " por smoke em Janelão às 0:57 (lugar de saída 1 de 3, " in mudou and ", round 23)" in mudou
        assert "Antes disso, FalleN corre até o lugar de saída, chegando às 0:57" in mudou
        pg.click("#rw-desfazer")
        assert _foto(pg) == antes
    finally:
        ctx.close()


def test_a_chegada_tardia_pergunta_jogar_as_h_e_a_granada_sai_nessa_hora(navegador, pagina_gr):
    ctx, pg, _ = _abre_no_instante(navegador, pagina_gr)
    try:
        _abre_secao(pg)
        _escreve(pg, "FalleN joga smoke no janelão aos 1:19")                    # 1 s depois do instante: ele não chega ao lugar de saída a tempo
        _espera_biblioteca(pg)
        _opcao(pg, "Levar o FalleN até lá")
        assert "FalleN (CT 2) só chega ao lugar de saída 1 de 3 (Snipers Nest) não antes de 1:12 (estimado: linha reta). Jogar às 1:12?" in _cartao(pg)
        assert pg.locator("#rw-cmd-cartao [data-codigo='gr_tarde'] button").all_inner_texts() == ["Jogar às 1:12", "Usar outro arremesso"]
        assert pg.is_disabled("#rw-cmd-aplicar")
        _opcao(pg, "Jogar às 1:12")
        _aplica(pg)
        t = _estado(pg)["trocas"]["trocas"][0]
        assert 168 <= t["sai"] <= 172 and "FalleN troca a smoke das 0:57" in pg.inner_text("#rw-mudou") and " às 1:12 (lugar de saída 1 de 3" in pg.inner_text("#rw-mudou")      # o relógio mostra 1:12 de 72,0 a 72,99 s que faltam: os quadros 168 a 172
    finally:
        ctx.close()


def test_a_hora_do_arremesso_vale_para_a_morte_real(navegador, pagina_gr):
    ctx, pg, _ = _abre_no_instante(navegador, pagina_gr)
    try:
        _abre_secao(pg)
        antes = _foto(pg)
        _escreve(pg, "ZywOo segura o meio até 0:50. ZywOo joga smoke no janelão aos 0:56")      # ZywOo morre às 0:52: ocupado até 0:50, só joga depois de morrer
        _espera_biblioteca(pg)
        _decide(pg)
        assert pg.locator("#rw-cmd-cartao [data-codigo='gr_depois_da_morte']").count() == 1
        assert "O arremesso sairia às " in _cartao(pg) and "No real, ZywOo morreu para " in _cartao(pg) and pg.is_disabled("#rw-cmd-aplicar")
        _forca_aplicar(pg)
        assert _foto(pg) == antes
    finally:
        ctx.close()


def test_a_frase_mista_aplica_as_duas_partes_e_um_desfazer_desfaz_as_duas(navegador, pagina_gr):
    ctx, pg, _ = _abre_no_instante(navegador, pagina_gr)
    try:
        _abre_secao(pg)
        antes = _foto(pg)
        _escreve(pg, "apEX corre pro meio aos 1:10 e depois joga flash no meio")
        _espera_biblioteca(pg)
        assert pg.is_disabled("#rw-cmd-aplicar")                                  # falta dizer o que fazer com a saída longe
        _decide(pg)
        _aplica(pg)
        e = _estado(pg)
        ap = _pecas(pg)["apEX"]
        assert ap["editada"] and len(ap["trilha"]) >= 2                           # a corrida até o meio e a ida até o lugar de saída
        assert [(t["by"], t["k"]) for t in e["trocas"]["trocas"]] == [("apEX", "flash")]
        assert e["comandos"]["desfazer"] == 1                                     # um comando continua sendo UM item do Desfazer
        assert len(e["comandos"]["linhas"]) == 1 and "apEX troca a flash das " in pg.inner_text("#rw-mudou")      # a corrida tem a sua linha; a troca, a dela
        pg.click("#rw-desfazer")
        assert _foto(pg) == antes
    finally:
        ctx.close()


def test_o_voo_desconhecido_nunca_vira_horario_de_queda(navegador, pagina_voo_nulo):
    ctx, pg, erros = _abre_no_instante(navegador, pagina_voo_nulo)
    try:
        _abre_secao(pg)
        _escreve(pg, "FalleN joga smoke no janelão aos 0:57")
        _espera_biblioteca(pg)
        _opcao(pg, "Levar o FalleN até lá")
        assert "não sei quando ela cai" in _cartao(pg)                            # o cartão diz, antes de aplicar
        _aplica(pg)
        t = _estado(pg)["trocas"]["trocas"][0]
        assert t["voo_s"] is None and t["cai"] is None and t["cmd"]               # nenhum horário de queda inventado
        mudou = pg.inner_text("#rw-mudou")
        assert "não sei quando ela cai" in mudou and " cai às " not in mudou
        pg.click("#play"); pg.wait_for_timeout(300); pg.click("#play")
        for q in (t["sai"] + 1, t["sai"] + 40, 600):
            pg.evaluate("q => { const s = document.getElementById('scrub'); s.disabled = false; s.value = q; s.dispatchEvent(new Event('input')); }", q)
            e = _estado(pg)
            assert e["soNoReal"] >= 1 and e["trocas"]["virtuais"] == {"nades": 0, "smokes": 0, "fires": 0, "pops": 0} and e["trocas"]["zonas"] == []      # a real some; a nova não voa, não cai e não faz fumaça
        assert erros == []
    finally:
        ctx.close()


def test_tocando_a_sua_versao_a_granada_nova_sai_na_hora_do_comando_e_cai_depois_do_voo(navegador, pagina_gr, biblioteca):
    ctx, pg, erros = _abre_no_instante(navegador, pagina_gr)
    try:
        _abre_secao(pg)
        t = _frase_aplicada(pg, "FalleN joga smoke no janelão aos 0:57")["trocas"]["trocas"][0]
        assert t["cai"] == t["sai"] + max(1, round(biblioteca[t["alt"]]["voo_s"] * 4))      # a saída do comando mais o voo do arremesso real (quadros de 4 por segundo)
        pg.click("#play"); pg.wait_for_timeout(300); pg.click("#play")

        def mostra(q):
            pg.evaluate("q => { const s = document.getElementById('scrub'); s.disabled = false; s.value = q; s.dispatchEvent(new Event('input')); }", q)
            return _estado(pg)
        e = mostra(t["sai"] + 1)
        assert e["soNoReal"] >= 1 and e["trocas"]["virtuais"]["nades"] == 1       # a real só no fantasma; a nova em voo
        e = mostra(t["cai"] + 1)
        z = e["trocas"]["zonas"]
        assert len(z) == 1 and z[0]["k"] == "smoke" and z[0]["f0"] == t["cai"] and abs(z[0]["x"] - t["destino"][0]) < 1 and abs(z[0]["y"] - t["destino"][1]) < 1
        assert erros == []
    finally:
        ctx.close()


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# rede, mapa e CLS
# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def test_a_biblioteca_so_e_pedida_por_uma_frase_de_granada_completa(navegador, pagina_gr):
    ctx, pg, _ = _abre_no_instante(navegador, pagina_gr)
    try:
        pedidos = []
        pg.on("request", lambda r: pedidos.append(r.url) if "arremessos/" in r.url else None)
        _abre_secao(pg)
        _escreve(pg, "ropz corre pro meio aos 1:10")                              # movimento: não pede
        _escreve(pg, "o 4 joga smoke no janelão aos 1:05")                        # a pergunta "quem?" ainda aberta: não pede
        pg.wait_for_timeout(300)
        assert pedidos == []
        _opcao(pg, "yuurih · CT 4")                                               # a frase ficou completa (com granada): pede, uma vez só
        pg.wait_for_function(PRONTA)
        _escreve(pg, "FalleN joga smoke no janelão aos 0:57")
        pg.wait_for_timeout(300)
        assert len(pedidos) == 1 and pedidos[0].endswith("arremessos/de_mirage.js")
    finally:
        ctx.close()


def test_o_mapa_nao_muda_e_o_cls_e_zero_ao_entender_perguntar_e_recusar_a_granada(navegador, pagina_gr):
    ctx, pg, _ = _abre_no_instante(navegador, pagina_gr)
    try:
        _abre_secao(pg)
        pg.evaluate(CLS_TOTAL)
        mapa = pg.evaluate(RECT)
        for frase, acao in [("FalleN joga smoke no janelão aos 0:57", None), ("mezii joga flash no meio aos 1:10", None), ("mezii joga smoke no meio aos 1:10", None),
                            ("ropz joga smoke no meio aos 1:05", None), ("FalleN joga smoke no janelão aos 1:19", "Levar o")]:
            _escreve(pg, frase)
            _espera_biblioteca(pg)
            if acao:
                _opcao(pg, acao)
            assert pg.evaluate(RECT) == mapa
        assert pg.evaluate("window.__cls_total") == 0
    finally:
        ctx.close()
