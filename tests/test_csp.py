"""CSP por <meta> (L-6 da revisão de segurança dos grupos, fase 16b) e a cadeia de entrega.

- toda página do site (landing, partida, jogadores, prancheta) tem a meta CSP, com as fontes do Google Fonts;
- o `connect-src` tem o host do projeto Supabase SÓ na prancheta e só com a configuração do grupo; sem ela
  (e com `GRUPOS_ATIVOS = False`), nenhum host além de 'self';
- a CSP não quebra a página aberta como arquivo local: a landing, uma partida e a prancheta abrem em `file://`
  sem nenhuma violação no console nem evento `securitypolicyviolation`;
- as Actions do CI ficam fixadas por SHA, o `.gitignore` cobre `.env.*` e há Dependabot para Actions e pip.
"""
from __future__ import annotations

import html as _html
import json
import re
from pathlib import Path

import pytest

from scripts import csp
from scripts.build_site import build_index, match_summary
from scripts.grupos_config import GRUPOS_ATIVOS

RAIZ = Path(__file__).resolve().parent.parent
MAPA = "de_mirage"
PARTIDA = "match_02"
HOST = "https://abcdefghijklmnop.supabase.co"
GRUPO_SUPABASE = {"modo": "supabase", "url": HOST, "chave": "sb_publishable_" + "x" * 20,
                  "biblioteca": "vendor/supabase-js-2.117.2.js", "site": None, "pagina": "p.html", "arquivoLocal": False}


def _csp_da(html: str) -> str:
    m = re.search(r'<meta http-equiv="Content-Security-Policy" content="([^"]*)">', html)
    assert m, "a página não tem a meta CSP"
    return _html.unescape(m.group(1))


def _diretivas(politica: str) -> dict[str, str]:
    return {p.split(" ", 1)[0]: (p.split(" ", 1)[1] if " " in p else "") for p in politica.split("; ")}


def _paginas() -> dict[str, str]:
    from scripts.build_jogadores import build_html as jogadores
    from scripts.build_tactics_page import build_html as prancheta
    from scripts.build_web_page import build_html as partida
    out = {"prancheta": prancheta(MAPA)}
    if (RAIZ / "data" / "processed" / PARTIDA / "web_payload.json").exists():
        out["partida"] = partida(PARTIDA)
    ids = sorted(d.name for d in (RAIZ / "data" / "processed").glob("match_*"))[:6]
    partidas = [m for m in (match_summary(i) for i in ids) if m]
    if partidas:
        numeros = json.loads((RAIZ / "data" / "processed" / "numeros_citaveis.json").read_text(encoding="utf-8"))
        out["landing"] = build_index(partidas, "https://example.invalid/repo",
                                     [{"mapa": p["map"], "file": f"prancheta_{p['map']}.html", "label": p["map"]} for p in partidas[:1]],
                                     numeros=numeros, imagem="replay.png")
    out["jogadores"] = jogadores()
    return out


@pytest.fixture(scope="module")
def paginas():
    return _paginas()


def test_toda_pagina_do_site_tem_a_meta_csp_com_as_fontes_do_google(paginas):
    assert "prancheta" in paginas
    for nome, html in paginas.items():
        d = _diretivas(_csp_da(html))
        assert d["default-src"] == "'self'", nome
        assert d["script-src"] == "'self' 'unsafe-inline'", nome
        assert d["style-src"] == "'self' 'unsafe-inline'", nome
        assert d["font-src"] == "'self'", nome
        assert "data:" in d["img-src"] and "'self'" in d["img-src"], nome
        assert d["object-src"] == "'none'" and d["base-uri"] == "'none'", nome
        # a meta vem antes de qualquer script e estilo: só vale para o que vem depois dela
        assert html.index("Content-Security-Policy") < min(i for i in (html.find("<script"), html.find("<style")) if i >= 0), nome


def test_sem_configuracao_do_grupo_o_connect_src_e_so_o_proprio_site(paginas):
    assert GRUPOS_ATIVOS is False
    for nome, html in paginas.items():
        assert _diretivas(_csp_da(html))["connect-src"] == "'self'", nome
        assert "supabase" not in _csp_da(html), nome


def test_o_host_do_projeto_so_entra_no_connect_src_da_prancheta_com_grupo():
    from scripts.build_tactics_page import build_html as prancheta
    d = _diretivas(_csp_da(prancheta(MAPA, grupo=GRUPO_SUPABASE)))
    assert d["connect-src"] == f"'self' {HOST} wss://abcdefghijklmnop.supabase.co"
    # nenhuma outra diretiva ganha o host
    assert all("supabase" not in v for k, v in d.items() if k != "connect-src")
    # a prancheta com a sala falsa dos testes (sem rede) segue só com 'self'
    falsa = prancheta(MAPA, grupo={"modo": "falsa", "falsa": {}})
    assert _diretivas(_csp_da(falsa))["connect-src"] == "'self'"
    # as outras páginas nunca recebem o host, nem com o grupo configurado
    from scripts.meta_da_pagina import meta_tags
    assert "supabase" not in meta_tags("t", "d")


@pytest.mark.parametrize("url", ["http://abc.supabase.co", "https://exemplo.com", "https://abc.supabase.co/rest/v1",
                                 "https://abc.supabase.co:8443", "https://abc.supabase.co.atacante.com", "https://-.supabase.co",
                                 "https://a b.supabase.co", "https://abc.supabase.co;script-src *"])
def test_url_que_nao_e_de_um_projeto_supabase_para_o_build(url):
    with pytest.raises(SystemExit):
        csp.hosts_do_projeto(url)


def test_url_do_projeto_vira_https_e_wss_e_sem_url_nao_ha_host():
    assert csp.hosts_do_projeto("https://abc123.supabase.co/") == ["https://abc123.supabase.co", "wss://abc123.supabase.co"]
    assert csp.hosts_do_projeto(None) == [] and csp.hosts_do_projeto("") == []


# --- a página aberta como arquivo local -----------------------------------------------------------------------

sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_tactics_browser import contexto, navegador  # noqa: E402,F401

OBSERVA = r"""
window.__violacoes = [];
document.addEventListener('securitypolicyviolation', (e) => window.__violacoes.push(e.violatedDirective + ' ' + e.blockedURI));
"""


def _abre(ctx, caminho, espera, hash_=""):
    pg = ctx.new_page()
    consoles, erros = [], []
    pg.on("console", lambda m: consoles.append(m.type + ": " + m.text))
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.add_init_script(OBSERVA)
    pg.goto(caminho.as_uri() + hash_)
    pg.wait_for_selector(espera, state="attached")
    pg.wait_for_timeout(500)
    return pg, consoles, erros


def _sem_violacao(pg, consoles, erros, nome):
    assert not erros, (nome, erros)
    assert pg.evaluate("() => window.__violacoes") == [], nome
    ruins = [c for c in consoles if re.search(r"Content.Security.Policy|Refused to", c)]
    assert not ruins, (nome, ruins)


def test_a_prancheta_a_partida_e_a_landing_abrem_em_file_sem_violacao_de_csp(contexto, paginas, tmp_path):
    destino = {"prancheta": ("[role=tabpanel]", "#pr-mapa"), "partida": ("[role=tab][data-tab]", "#play"),
               "landing": ("#partidas", None), "jogadores": ("body", None)}
    visitadas = []
    for nome, html in paginas.items():
        arq = tmp_path / f"{nome}.html"
        arq.write_text(html, encoding="utf-8")
        pg, consoles, erros = _abre(contexto, arq, destino[nome][0], "#replay" if nome == "partida" else "")
        visitadas.append(nome)
        if nome == "prancheta":
            # mexe nela: abas do painel, exportar (blob de download), um clique no mapa
            for aba in pg.evaluate("() => Array.from(document.querySelectorAll('[role=tab][data-aba]')).map((t) => t.dataset.aba)"):
                pg.evaluate("(a) => Prancheta._interno.abaDoPainel(a)", aba)
            pg.evaluate("() => Prancheta._interno.gravaAgora()")
            with pg.expect_download():
                pg.evaluate("() => document.getElementById('pr-exporta').click()")
        if nome == "partida":
            pg.click("#play")
            pg.wait_for_timeout(800)
            for aba in pg.evaluate("() => Array.from(document.querySelectorAll('[role=tab][data-tab]')).map((t) => t.dataset.tab)"):
                pg.evaluate("(a) => document.querySelector('[role=tab][data-tab=\"' + a + '\"]').click()", aba)
        _sem_violacao(pg, consoles, erros, nome)
        pg.close()
    assert {"prancheta", "partida", "landing", "jogadores"} <= set(visitadas)


def test_a_csp_bloqueia_de_verdade_um_pedido_de_rede_que_nao_e_do_site(contexto, paginas, tmp_path):
    """Contraprova: a política está valendo (um fetch para fora é bloqueado com a violação registrada)."""
    arq = tmp_path / "prancheta.html"
    arq.write_text(paginas["prancheta"], encoding="utf-8")
    pg, consoles, erros = _abre(contexto, arq, "#pr-mapa")
    r = pg.evaluate("""async () => { try { await fetch('https://exemplo.invalid/x'); return 'passou'; } catch (e) { return 'bloqueado'; } }""")
    assert r == "bloqueado"
    pg.wait_for_timeout(100)
    assert any("connect-src" in v for v in pg.evaluate("() => window.__violacoes"))


# --- a cadeia de entrega: Actions por SHA, .gitignore, Dependabot ----------------------------------------------

def test_as_actions_estao_fixadas_por_sha_com_a_versao_em_comentario():
    usos = []
    for wf in sorted((RAIZ / ".github" / "workflows").glob("*.yml")):
        for n, linha in enumerate(wf.read_text(encoding="utf-8").splitlines(), 1):
            m = re.match(r"\s*-?\s*uses:\s*(\S+)(.*)$", linha)
            if m:
                usos.append((wf.name, n, m.group(1), m.group(2)))
    assert usos
    for arq, n, ref, resto in usos:
        assert re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", ref), f"{arq}:{n} {ref}: fixe por SHA de 40 caracteres"
        assert re.search(r"#\s*v\d+(\.\d+){0,2}\b", resto), f"{arq}:{n}: falta a versão em comentário (# v4.2.2)"


def test_gitignore_cobre_env_e_as_variacoes():
    linhas = {l.strip() for l in (RAIZ / ".gitignore").read_text(encoding="utf-8").splitlines()}
    assert ".env" in linhas and ".env.*" in linhas


def test_dependabot_cobre_as_actions_e_o_pip():
    texto = (RAIZ / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    assert "version: 2" in texto
    assert 'package-ecosystem: "github-actions"' in texto and 'package-ecosystem: "pip"' in texto
    assert texto.count("schedule:") == 2
