"""Prancheta na direção "Sala de demo" (design-E, entrega-sala-de-demo §14, parte de forma): topo do site,
"PRANCHETA ·" com o mapa num select de dois grupos, aviso de mapa sem partidas, anel duplo e rótulos da §4.2
nas peças, alvos de 44 px e o mapa cabendo na janela com a linha do tempo."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from tests.test_tactics_browser import (abre, arrasta_do_banco, contexto, interno, navegador,  # noqa: E402,F401
                                        pagina, pagina_do_mapa)


def test_cabecalho_com_topo_do_site_e_o_mapa_em_dois_grupos(contexto, pagina):
    pg = abre(contexto, pagina)
    try:
        assert pg.get_attribute('.site-nav a[aria-current="page"]', "href").startswith("prancheta_")
        grupos = pg.eval_on_selector_all("#pr-mapa-sel optgroup", "gs => gs.map(g => [g.label, g.children.length])")
        assert [g[0] for g in grupos] == ["Com partidas no corpus", "Sem partidas no corpus"]
        sem = pg.eval_on_selector_all('#pr-mapa-sel optgroup[label="Sem partidas no corpus"] option', "os => os.map(o => o.textContent)")
        assert sem and all(o.endswith("(sem partidas)") for o in sem)
        assert pg.eval_on_selector("#pr-mapa-sel", "s => s.options[s.selectedIndex].textContent") == "Mirage"
        assert pg.is_hidden("#pr-aviso-mapa")                          # a Mirage tem partidas
    finally:
        pg.close()


def test_mapa_sem_partidas_mostra_o_aviso_e_desliga_a_busca(contexto, tmp_path_factory):
    pg = abre(contexto, pagina_do_mapa(tmp_path_factory, "de_cache"))
    try:
        aviso = pg.inner_text("#pr-aviso-mapa")
        assert pg.is_visible("#pr-aviso-mapa") and aviso.startswith("Cache não tem partidas no corpus. Dá para montar a tática")
        assert pg.locator('aside [data-ferramenta="buscar"]').is_disabled()
    finally:
        pg.close()


def test_peca_com_anel_duplo_e_nome_na_camada_de_rotulos(contexto, pagina):
    pg = abre(contexto, pagina)
    try:
        arrasta_do_banco(pg, "t", "1", 0.5, 0.5)
        pg.keyboard.press("Escape")
        caixas = pg.evaluate("window.__medicaoRotulos.caixas()")
        assert any(c["txt"] == "TR 1" for c in caixas), caixas
        assert all(c["alt"] >= 7.5 for c in caixas)                    # 12,5 px de tela, não escala com o mapa
        r = pg.evaluate("""() => {
            const c = document.createElement('canvas'); c.width = c.height = 80;
            const g = c.getContext('2d');
            MapCore.desenhaJogador(g, 40, 40, {cor: '#e0a23a', estado: 'vivo', hp: 100, nome: '', escala: 15 / 8.2});
            const px = x => Array.from(g.getImageData(x, 40, 1, 1).data.slice(0, 3));
            return [px(40), px(40 + 12)]; }""")   # miolo de 6 x 15/8,2 = 11 px; contorno até 13,5
        assert tuple(r[0]) == (0xE0, 0xA2, 0x3A)                       # o miolo na cor do lado
        assert max(r[1]) < 40                                          # logo fora do miolo, o contorno escuro
    finally:
        pg.close()


def test_todo_controle_tem_alvo_de_44_px_menos_as_marcas_de_acao(contexto, pagina):
    pg = abre(contexto, pagina)
    try:
        pequenos = pg.evaluate("""() => [...document.querySelectorAll('a,button,select,input,summary,[role=tab],[role=slider]')]
            .filter(e => { const b = e.getBoundingClientRect(), s = getComputedStyle(e);
                           return b.width && b.height && s.visibility !== 'hidden' && s.display !== 'none'
                                  && (b.width < 44 || b.height < 44) && !e.classList.contains('pr-marca')
                                  && !(e.type === 'checkbox' || e.type === 'radio'); })
            .map(e => (e.id || e.className || e.tagName) + ' ' + Math.round(e.getBoundingClientRect().width) + 'x' +
                      Math.round(e.getBoundingClientRect().height))""")
        assert pequenos == [], pequenos
    finally:
        pg.close()


def test_mapa_e_linha_do_tempo_cabem_na_janela(contexto, pagina):
    pg = abre(contexto, pagina)
    try:
        r = pg.evaluate("""() => { const m = document.getElementById('pr-mapa').getBoundingClientRect(),
            l = document.getElementById('pr-linha'); return [m.top, m.bottom, l && !l.hidden ? l.getBoundingClientRect().bottom : m.bottom, innerHeight]; }""")
        assert r[0] >= 0 and r[2] <= r[3] + 1, r
    finally:
        pg.close()


def test_o_painel_tem_tres_abas_com_teclado_e_so_uma_visivel(contexto, pagina):
    """§14: Jogadores · Granadas · Tática, role=tablist, setas/Home/End, tabindex móvel."""
    pg = abre(contexto, pagina)
    try:
        assert pg.eval_on_selector_all("#pr-abas [role=tab]", "ts => ts.map(t => t.textContent)") == ["Jogadores", "Granadas", "Tática"]
        visiveis = lambda: pg.eval_on_selector_all("aside [role=tabpanel]", "ps => ps.filter(p => !p.hidden).map(p => p.dataset.aba)")  # noqa: E731
        assert visiveis() == ["jogadores"]
        assert pg.eval_on_selector_all("#pr-abas [role=tab]", "ts => ts.map(t => t.tabIndex)") == [0, -1, -1]
        pg.focus("#pr-aba-jogadores")
        pg.keyboard.press("ArrowRight")
        assert visiveis() == ["granadas"] and pg.evaluate("document.activeElement.dataset.aba") == "granadas"
        pg.keyboard.press("End")
        assert visiveis() == ["tatica"]
        pg.keyboard.press("ArrowRight")                                    # volta ao começo
        assert visiveis() == ["jogadores"]
        # escolher a granada (atalho 1) mostra a aba onde ela está
        pg.keyboard.press("1")
        assert visiveis() == ["granadas"]
        # cada aba tem 44 px de alto
        assert all(c["h"] >= 44 for c in pg.eval_on_selector_all("#pr-abas [role=tab]", "ts => ts.map(t => ({h: t.getBoundingClientRect().height}))"))
    finally:
        pg.close()


def test_o_fantasma_do_round_real_e_so_o_anel_tracejado_com_nome_em_itálico(contexto, pagina):
    """§14: sem preenchimento (o miolo é o radar), contorno tracejado na cor do lado, nome "· real" em itálico."""
    pg = abre(contexto, pagina)
    try:
        r = pg.evaluate("""() => {
            const c = document.createElement('canvas'); c.width = c.height = 80;
            const g = c.getContext('2d');
            g.fillStyle = '#336699'; g.fillRect(0, 0, 80, 80);                    // o "radar" por baixo
            MapCore.desenhaJogador(g, 40, 40, {cor: '#e0a23a', estado: 'fantasma', hp: 100, nome: '', escala: 15 / 8.2});
            const px = (x, y) => Array.from(g.getImageData(x, y, 1, 1).data.slice(0, 3));
            // o miolo (centro) segue sendo o radar; ao redor há pixels do traço
            let tracos = 0; for (let a = 0; a < 360; a += 10) { const p = px(Math.round(40 + 11 * Math.cos(a * Math.PI / 180)), Math.round(40 + 11 * Math.sin(a * Math.PI / 180)));
              if (p[0] !== 0x33 || p[2] !== 0x99) tracos++; }
            return {centro: px(40, 40), tracos}; }""")
        assert r["centro"] == [0x33, 0x66, 0x99], r                    # sem preenchimento
        assert r["tracos"] > 10, r                                      # e há traço em volta do raio
    finally:
        pg.close()
