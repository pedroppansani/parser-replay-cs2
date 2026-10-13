"""Grupos na prancheta (fase 13, item 13.3): a forma da aba "Grupo" (entrega-sala-de-demo §8 e §14).

Sem cor nova (o CSS da aba só usa os tokens), alvos de 44 px, a chave como botão com aria-pressed, o erro do
sistema com ✕ e "Erro:" e, no celular, a mesma aba numa coluna, sem rolagem horizontal.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")

from tests.test_grupos_browser import CLIENTES_JS, abre_grupo, membro_na_sala, pagina_grupo  # noqa: E402,F401
from tests.test_tactics_browser import navegador  # noqa: E402,F401

RAIZ = Path(__file__).resolve().parents[1]

PEQUENOS_NO_PAINEL = """() => [...document.querySelectorAll('#pr-painel-grupo a, #pr-painel-grupo button, #pr-painel-grupo input, #pr-painel-grupo select')]
    .filter(e => { const b = e.getBoundingClientRect(); return b.width && b.height && (b.width < 44 || b.height < 44)
                   && e.tagName !== 'A'; })
    .map(e => (e.id || e.getAttribute('data-acao') || e.tagName) + ' ' + Math.round(e.getBoundingClientRect().width) + 'x' +
              Math.round(e.getBoundingClientRect().height))"""


def test_o_css_da_aba_nao_tem_cor_nova():
    css = (RAIZ / "dashboard" / "web" / "grupo.css").read_text(encoding="utf-8")
    sem_comentarios = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(", sem_comentarios)
    usadas = set(re.findall(r"var\(--([a-z0-9-]+)\)", sem_comentarios))
    tokens = (RAIZ / "dashboard" / "web" / "tokens.css").read_text(encoding="utf-8")
    assert all(f"--{t}:" in tokens for t in usadas), usadas
    # --erro só no erro do sistema; --aviso, nunca (nenhum dado degradado aqui)
    assert [s.strip() for s in re.findall(r"([^{}]+)\{[^}]*var\(--erro\)", sem_comentarios)] == [".gr-erro"]
    assert "--aviso" not in sem_comentarios


def _membro(navegador, pagina, largura, altura):
    ctx = navegador.new_context(viewport={"width": largura, "height": altura})
    pg, codigo = membro_na_sala(ctx, pagina)
    pg.evaluate("() => Prancheta._interno.abaDoPainel('grupo')")
    return ctx, pg, codigo


def test_painel_do_membro_sem_permissao(navegador, pagina_grupo):
    ctx, pg, codigo = _membro(navegador, pagina_grupo, 1440, 900)
    try:
        texto = pg.inner_text("#pr-painel-grupo")
        assert codigo in texto and "Só a líder desenha agora" in texto and "Seguir a líder" in texto
        assert "Sair do grupo" in texto
        assert pg.locator('#pr-painel-grupo [data-acao="permite"]').count() == 0     # membro não tem as chaves
        assert pg.locator('#pr-painel-grupo [data-acao="expulsa"]').count() == 0
        assert pg.get_attribute('[data-acao="seguir"]', "aria-pressed") == "true"
        assert "líder" in pg.inner_text('.gr-membro[data-usuario="u-lider"]')
        assert pg.evaluate(PEQUENOS_NO_PAINEL) == []
    finally:
        ctx.close()


def test_painel_da_lider(navegador, pagina_grupo):
    ctx = navegador.new_context(viewport={"width": 1440, "height": 900})
    pg = abre_grupo(ctx, pagina_grupo)
    try:
        pg.evaluate("() => Prancheta._interno.abaDoPainel('grupo')")
        pg.fill("#gr-nick", "nomad")
        pg.click('[data-acao="criar"]')
        pg.wait_for_function("() => Grupo._interno.G().fase === 'dentro'")
        codigo = pg.inner_text("#gr-codigo-sala")
        pg.evaluate(f"""async () => {{ const c = window.__cliente('u-ana', 'ana'); await c.s.prepara();
            await c.s.entrar('{codigo}', 'ana'); await c.liga(); }}""")
        pg.wait_for_selector('.gr-membro[data-usuario="u-ana"] [data-acao="permite"]')
        for acao in ("copiar", "todos", "transferir", "encerrar"):
            assert pg.locator(f'#pr-painel-grupo [data-acao="{acao}"]').count() == 1, acao
        assert pg.get_attribute('[data-acao="todos"]', "aria-pressed") == "false"
        assert pg.get_attribute('.gr-membro[data-usuario="u-ana"] [data-acao="permite"]', "aria-pressed") == "false"
        assert pg.locator('[data-acao="sair"]').count() == 0          # a líder transfere ou encerra
        assert pg.evaluate(PEQUENOS_NO_PAINEL) == []
    finally:
        ctx.close()


def test_no_celular_a_aba_fica_numa_coluna_sem_rolar_de_lado(navegador, pagina_grupo):
    ctx, pg, _ = _membro(navegador, pagina_grupo, 375, 812)
    try:
        r = pg.evaluate("""() => { const p = document.getElementById('pr-painel-grupo').getBoundingClientRect();
            const linhas = [...document.querySelectorAll('#pr-painel-grupo .linha')].map((l) =>
                [...l.children].map((c) => c.getBoundingClientRect()).filter((b) => b.width));
            return { largura: p.width, rolagem: document.documentElement.scrollWidth - innerWidth,
                     umaPorLinha: linhas.every((bs) => bs.every((b, i) => i === 0 || b.top >= bs[i - 1].bottom - 1)) }; }""")
        assert r["rolagem"] <= 0 and r["umaPorLinha"], r
        assert pg.evaluate(PEQUENOS_NO_PAINEL) == []
    finally:
        ctx.close()
