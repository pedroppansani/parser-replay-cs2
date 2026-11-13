"""CR1a: o plano dos comandos saiu da prancheta para `dashboard/web/comandos/plano.js` (puro, carregado só quando a aba Comandos abre).

O que a extração PROMETE e este arquivo confere: (1) o módulo é puro (nada de DOM, rede nem armazenamento); (2) a página gerada sozinha o traz embutido e a do site pede o
arquivo só quando a aba abre; (3) o arquivo que não carrega vira um aviso e o "Aplicar" desligado, nunca um plano pela metade; (4) a política de segurança (CSP) é a mesma;
(5) o plano faz o mesmo de antes (a prova byte a byte está em `scripts/design/prova_plano_dos_comandos.py`, que precisa do código de antes e por isso não é teste)."""
from __future__ import annotations

import html
import re
import shutil
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")

from tests.test_comandos_tempos import _escreve, _peca, _ponto  # noqa: E402,F401
from tests.test_tactics_browser import abre, contexto, interno, navegador  # noqa: E402,F401

RAIZ = Path(__file__).resolve().parent.parent
PLANO = RAIZ / "dashboard" / "web" / "comandos" / "plano.js"
MAPA = "de_mirage"


def _site(tmp_path_factory, com_arquivo=True):
    """A prancheta como o site a gera (biblioteca e plano externos), numa pasta com `comandos/plano.js` ao lado (ou sem ele)."""
    from scripts.build_tactics_page import ARQUIVO_DO_PLANO, arquivo_da_pagina, build_html
    pasta = tmp_path_factory.mktemp("site_plano")
    (pasta / arquivo_da_pagina(MAPA)).write_text(build_html(MAPA, biblioteca_externa=True, plano_externo=True), encoding="utf-8")
    if com_arquivo:
        (pasta / ARQUIVO_DO_PLANO).parent.mkdir(exist_ok=True)
        shutil.copyfile(PLANO, pasta / ARQUIVO_DO_PLANO)
    return pasta / arquivo_da_pagina(MAPA)


def test_o_modulo_e_puro_sem_dom_rede_nem_armazenamento():
    texto = PLANO.read_text(encoding="utf-8")
    codigo = re.sub(r"/\*.*?\*/", "", texto, flags=re.S)
    codigo = re.sub(r"//[^\n]*", "", codigo)
    for proibido in ("document.", "localStorage", "sessionStorage", "fetch(", "XMLHttpRequest", "navigator.", "setTimeout", "alert(", "console."):
        assert proibido not in codigo, f"o plano é puro: {proibido!r} não pode aparecer"
    ultima = [l for l in codigo.splitlines() if l.strip()][-1]
    assert codigo.count("window") == 2 and ultima.count("window") == 2     # só a última linha, que escolhe o global onde pendurar `PlanoDeComandos`


def test_a_pagina_gerada_sozinha_traz_o_plano_embutido_e_a_do_site_so_o_caminho():
    from scripts.build_tactics_page import ARQUIVO_DO_PLANO, build_html
    sozinha = build_html(MAPA)
    site = build_html(MAPA, biblioteca_externa=True, plano_externo=True)
    chave = re.compile(r'"plano_arquivo"\s*:\s*"' + re.escape(ARQUIVO_DO_PLANO) + '"')      # a chave dos dados (o JS da prancheta lê `cfg.comandos.plano_arquivo` sempre)
    assert "function cria(W)" in sozinha and not chave.search(sozinha)
    assert "function cria(W)" not in site and chave.search(site)
    # o parâmetro da biblioteca NÃO liga o plano externo (os testes da C1 a C4 constroem a página assim, sem o arquivo ao lado)
    assert "function cria(W)" in build_html(MAPA, biblioteca_externa=True)


def test_a_politica_de_seguranca_e_a_mesma_com_o_plano_dentro_ou_fora():
    from scripts.build_tactics_page import build_html
    csp = lambda h: html.unescape(re.search(r'<meta http-equiv="Content-Security-Policy" content="([^"]*)"', h).group(1))
    assert csp(build_html(MAPA)) == csp(build_html(MAPA, plano_externo=True))
    assert "script-src 'self' 'unsafe-inline'" in csp(build_html(MAPA))          # o arquivo é do próprio site: nenhuma origem nova


def test_no_site_o_plano_so_e_pedido_quando_a_aba_abre_e_depois_funciona(contexto, tmp_path_factory):
    pagina = _site(tmp_path_factory)
    ctx_pg = contexto.new_page()
    pedidos = []
    ctx_pg.on("request", lambda r: pedidos.append(r.url))
    ctx_pg.goto(pagina.as_uri())
    ctx_pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
    ctx_pg.wait_for_timeout(400)
    assert not any(u.endswith("comandos/plano.js") for u in pedidos), "o plano não pode carregar com a página"
    assert ctx_pg.evaluate("() => typeof PlanoDeComandos") == "undefined"
    base = _ponto(MAPA, "Base TR")
    _peca(ctx_pg, base["x"], base["y"])
    _escreve(ctx_pg, "tr 2 corre pro meio aos 1:30")                               # abre a aba e escreve
    ctx_pg.wait_for_function("() => document.querySelectorAll('#pr-cmd-entendi li').length === 1 && !document.getElementById('pr-cmd-carregando-plano')", timeout=15000)
    assert any(u.endswith("comandos/plano.js") for u in pedidos)
    assert "chega" in ctx_pg.inner_text("#pr-cmd-entendi")                         # o plano calculou a chegada
    assert ctx_pg.is_enabled("#pr-cmd-aplicar")
    ctx_pg.close()


def test_o_arquivo_do_plano_que_nao_carrega_vira_aviso_e_o_aplicar_fica_desligado(contexto, tmp_path_factory):
    pagina = _site(tmp_path_factory, com_arquivo=False)
    pg = abre(contexto, pagina)
    base = _ponto(MAPA, "Base TR")
    _peca(pg, base["x"], base["y"])
    _escreve(pg, "tr 2 corre pro meio aos 1:30")
    pg.wait_for_function("() => !!document.getElementById('pr-cmd-sem-plano')", timeout=15000)
    assert "Recarregue a página" in pg.inner_text("#pr-cmd-sem-plano")
    assert pg.is_disabled("#pr-cmd-aplicar")                                       # nada é aplicado sem o plano
    assert interno(pg, "S.doc.operacoes.filter(o => o.tipo === 'cria_caminho').length") == 0


def test_o_modulo_cria_funcoes_so_com_o_mundo_que_a_prancheta_entrega(contexto):
    """`PlanoDeComandos.cria(W)` não lê nada fora de W: com um mundo mínimo ele devolve as quatro funções e um plano vazio para nenhuma ação."""
    pg = contexto.new_page()
    pg.set_content("<!doctype html><meta charset=utf-8>")
    pg.add_script_tag(content=PLANO.read_text(encoding="utf-8"))
    r = pg.evaluate("""() => {
      const t = { dados: null, pontos: {}, areas: {}, nos: [], areaDoTexto: {} };
      const W = { S: () => ({ estado: { pecas: {}, passos: [{ passo: "p" }] }, e3: null }), cfg: () => ({ biblioteca: null, comandos: { granada: {}, textos: {}, velocidade_piso_correndo: 250 } }),
                  M3: () => ({ SEGUNDOS_DO_ROUND: 115 }), ANDARES: () => [], CENTRO: () => null, Tempos: t, t: (k) => k, doRelogio: (x) => String(x), bibliotecaPronta: () => true };
      const P = PlanoDeComandos.cria(W);
      return { funcoes: Object.keys(P).sort(), plano: P.plano({ acoes: [] }), estado: P.estadoDaBiblioteca() };
    }""")
    assert r["funcoes"] == ["buscaReal", "estadoDaBiblioteca", "plano", "tempoReal"]
    assert r["plano"]["ops"] == [] and r["plano"]["problemas"] == [] and r["plano"]["espera"] is False
    assert r["estado"] == "sem"                                                    # sem biblioteca e sem aviso de "carregando": o mapa não tem
    pg.close()
