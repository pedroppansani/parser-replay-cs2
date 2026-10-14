"""Grupos na prancheta (fase 13, item 13.3): a forma da aba "Grupo" (entrega-sala-de-demo §8 e §14).

Sem cor nova (o CSS da aba só usa os tokens), alvos de 44 px, a chave com role=switch e aria-checked, o erro do
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
    # --erro só no erro de campo e no erro do sistema (§19.0); --aviso só na alteração desfeita pelo servidor
    erro = {x.strip() for x in re.findall(r"([^{}]+)\{[^}]*var\(--erro\)", sem_comentarios)}
    assert erro == {'.gr-campo input[aria-invalid="true"]', ".gr-campo .erro-campo", ".gr-aviso.erro", ".gr-aviso.erro b, .gr-aviso.erro span"}, erro
    aviso = [x.strip() for x in re.findall(r"([^{}]+)\{[^}]*var\(--aviso\)", sem_comentarios)]
    assert aviso == [".pr-dica-estado.recusa-desfeita", ".pr-dica-estado.recusa-desfeita .dica-texto::before"], aviso


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
        assert pg.get_attribute('[data-acao="seguir"]', "aria-checked") == "true"
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
        assert pg.get_attribute('[data-acao="todos"]', "aria-checked") == "false"
        assert pg.get_attribute('.gr-membro[data-usuario="u-ana"] [data-acao="permite"]', "aria-checked") == "false"
        assert pg.locator('[data-acao="sair"]').count() == 0          # a líder transfere ou encerra
        assert pg.evaluate(PEQUENOS_NO_PAINEL) == []
    finally:
        ctx.close()


def test_no_celular_a_aba_fica_numa_coluna_sem_rolar_de_lado(navegador, pagina_grupo):
    # vista da líder: tem as linhas de botões (.gr-linha), que quebram linha em vez de estourar o painel
    ctx, pg = _lider_com_ana(navegador, pagina_grupo, 375, 812)
    try:
        r = pg.evaluate("""() => { const p = document.getElementById('pr-painel-grupo').getBoundingClientRect();
            const filhos = [...document.querySelectorAll('#pr-painel-grupo .gr-linha > *')].map((c) => c.getBoundingClientRect()).filter((b) => b.width);
            return { n: filhos.length, rolagem: document.documentElement.scrollWidth - innerWidth,
                     dentro: filhos.every((b) => b.left >= p.left - 1 && b.right <= p.right + 1) }; }""")
        assert r["n"] > 0, r                                   # o conjunto não está vazio
        assert r["rolagem"] <= 0 and r["dentro"], r
        assert pg.evaluate(PEQUENOS_NO_PAINEL) == []
    finally:
        ctx.close()
    # vista do membro: a mesma coluna, sem rolar de lado
    ctx, pg, _ = _membro(navegador, pagina_grupo, 375, 812)
    try:
        assert pg.evaluate("() => document.documentElement.scrollWidth - innerWidth") <= 0
        assert pg.evaluate(PEQUENOS_NO_PAINEL) == []
    finally:
        ctx.close()


# --- fase 15: a forma da §19.6 e o "Expulsar" com confirmação em linha ------------------------------------------

def _lider_com_ana(navegador, pagina, largura=1440, altura=900):
    """A tela é a líder (cria o grupo); a ana entra como cliente sem tela."""
    ctx = navegador.new_context(viewport={"width": largura, "height": altura})
    pg = abre_grupo(ctx, pagina)
    pg.evaluate("() => Prancheta._interno.abaDoPainel('grupo')")
    pg.fill("#gr-nick", "nomad")
    pg.click('[data-acao="criar"]')
    pg.wait_for_function("() => Grupo._interno.G().fase === 'dentro'")
    codigo = pg.inner_text("#gr-codigo-sala")
    pg.evaluate(f"""async () => {{ const c = window.__cliente('u-ana', 'ana'); await c.s.prepara();
        await c.s.entrar('{codigo}', 'ana'); await c.liga(); window.__ana = c; }}""")
    pg.wait_for_selector('.gr-membro[data-usuario="u-ana"] [data-acao="expulsa"]')
    return ctx, pg


def _ana_esta_no_grupo(pg):
    return pg.evaluate("() => Grupo._interno.G().membros.some((m) => m.usuario === 'u-ana')")


def test_expulsar_pede_confirmacao_em_linha_e_o_foco_vai_para_cancelar(navegador, pagina_grupo):
    ctx, pg = _lider_com_ana(navegador, pagina_grupo)
    try:
        # o confirm() do navegador nunca é chamado (nem qualquer diálogo)
        pg.evaluate("() => { window.__confirms = 0; window.confirm = () => { window.__confirms++; return true; }; }")
        dialogos = []
        pg.on("dialog", lambda d: (dialogos.append(d.message), d.dismiss()))
        pg.click('.gr-membro[data-usuario="u-ana"] [data-acao="expulsa"]')
        linha = pg.locator('.gr-membro[data-usuario="u-ana"]')
        assert "Expulsar ana?" in linha.inner_text() and "Confirmar" in linha.inner_text() and "Cancelar" in linha.inner_text()
        assert pg.evaluate("() => document.activeElement.id") == "gr-cancela-expulsa"
        assert _ana_esta_no_grupo(pg)                                   # ainda não expulsou
        # Cancelar: não expulsa, e o foco volta para o "Expulsar" da linha
        pg.click("#gr-cancela-expulsa")
        assert pg.locator(".gr-confirma-expulsa").count() == 0 and _ana_esta_no_grupo(pg)
        assert pg.evaluate("() => document.activeElement.getAttribute('data-acao')") == "expulsa"
        # Esc: cancela
        pg.click('.gr-membro[data-usuario="u-ana"] [data-acao="expulsa"]')
        pg.keyboard.press("Escape")
        assert pg.locator(".gr-confirma-expulsa").count() == 0 and _ana_esta_no_grupo(pg)
        # clique fora: cancela
        pg.click('.gr-membro[data-usuario="u-ana"] [data-acao="expulsa"]')
        pg.click("#pr-painel-grupo h2")
        assert pg.locator(".gr-confirma-expulsa").count() == 0 and _ana_esta_no_grupo(pg)
        # Confirmar: expulsa de verdade
        pg.click('.gr-membro[data-usuario="u-ana"] [data-acao="expulsa"]')
        pg.click('[data-acao="confirma-expulsa"]')
        pg.wait_for_function("() => !Grupo._interno.G().membros.some((m) => m.usuario === 'u-ana')")
        assert pg.evaluate("() => window.__confirms") == 0 and dialogos == []
        assert not pg._erros
    finally:
        ctx.close()


def test_a_chave_diz_o_estado_por_escrito_e_o_contador_conta_os_online(navegador, pagina_grupo):
    ctx, pg = _lider_com_ana(navegador, pagina_grupo)
    try:
        chave = pg.locator('[data-acao="todos"]')
        assert chave.get_attribute("role") == "switch" and "Desligado" in chave.text_content()
        chave.click()
        pg.wait_for_function("() => Grupo._interno.G().todos === true")
        assert "Ligado" in pg.text_content('[data-acao="todos"]')
        # o contador da aba: só com grupo, com o aria-label "N online"
        c = pg.locator("#pr-aba-grupo .aba-contador")
        assert c.count() == 1 and c.get_attribute("aria-label").endswith(" online") and c.inner_text().isdigit()
        assert not pg._erros
    finally:
        ctx.close()


def test_sem_permissao_a_dica_fixa_diz_o_motivo_e_a_aba_tem_contador(navegador, pagina_grupo):
    ctx, pg, _ = _membro(navegador, pagina_grupo, 1440, 900)
    try:
        pg.wait_for_function("() => document.getElementById('pr-dica-estado').textContent.includes('Você acompanha a tática')")
        texto = pg.inner_text("#pr-dica-estado")
        assert "só a líder desenha agora" in texto and "mover o cabeçote e dar play" in texto
        assert "bloqueado" in pg.get_attribute("#pr-dica-estado", "class")
        assert pg.locator("#pr-aba-grupo .aba-contador").count() == 1
        assert pg.locator("#pr-reproduzir").is_enabled()          # Reproduzir segue ligado
        assert not pg._erros
    finally:
        ctx.close()


def test_codigo_invalido_marca_o_campo_e_removido_nao_e_erro(navegador, pagina_grupo):
    ctx = navegador.new_context(viewport={"width": 375, "height": 812})
    pg = abre_grupo(ctx, pagina_grupo)
    try:
        pg.evaluate("() => Prancheta._interno.abaDoPainel('grupo')")
        pg.fill("#gr-nick", "spinx")
        pg.fill("#gr-codigo", "ABCDEFGH")
        pg.click('[data-acao="entrar"]')
        pg.wait_for_selector("#gr-e-codigo")
        assert pg.get_attribute("#gr-codigo", "aria-invalid") == "true"
        assert pg.get_attribute("#gr-codigo", "aria-describedby") == "gr-e-codigo"
        assert pg.inner_text("#gr-e-codigo") == "✕ Erro: Nenhum grupo com esse código."
        # "removido" é aviso informativo, sem --erro: nada de "Erro:" no bloco
        pg.evaluate("() => { Grupo._interno.G().info = 'A líder tirou você deste grupo. A tática continua salva neste navegador.'; Grupo._interno.renderiza(); }")
        assert "Erro" not in pg.inner_text("#gr-info") and "gr-aviso info" in pg.get_attribute("#gr-info", "class")
        assert pg.evaluate("() => document.documentElement.scrollWidth - innerWidth") <= 0
        assert pg.evaluate(PEQUENOS_NO_PAINEL) == []
        assert not pg._erros
    finally:
        ctx.close()
