"""P2c (visual): a prancheta volta à navbar e os 10 mapas viram links; arrastar várias vezes no Reescrever; "Ver no mapa ↑" no celular; o nome do time; a peça sob o relógio."""
from __future__ import annotations

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_reescrever_r1 import paginas_html, partidas  # noqa: E402,F401  (as páginas geradas)
from tests.test_reescrever_modo import navegador  # noqa: E402,F401


@pytest.mark.parametrize("largura", [375, 1440])
@pytest.mark.parametrize("pagina", ["landing", "jogadores", "reescrever", "partida", "prancheta"])
def test_os_quatro_links_da_navbar_cabem_sem_rolagem_lateral_e_em_uma_linha(navegador, paginas_html, pagina, largura):
    pasta, _ = paginas_html
    ctx = navegador.new_context(viewport={"width": largura, "height": 812})
    pg = ctx.new_page()
    try:
        pg.goto((pasta / f"{pagina}.html").as_uri())
        r = pg.evaluate("""() => { const n = document.querySelector('.site-nav'), as = [...n.querySelectorAll('a')], nb = n.getBoundingClientRect();
          return { textos: as.map(a => a.textContent), sobra: n.scrollWidth - n.clientWidth, topos: [...new Set(as.map(a => Math.round(a.getBoundingClientRect().top)))].length,
                   dentro: as.every(a => { const b = a.getBoundingClientRect(); return b.left >= nb.left - 0.5 && b.right <= nb.right + 0.5; }),
                   pagina: document.documentElement.scrollWidth - document.documentElement.clientWidth }; }""")
        assert r["textos"] == ["Partidas", "Jogadores", "Reescrever", "Prancheta"]
        assert r["sobra"] <= 0 and r["dentro"] and r["topos"] == 1 and r["pagina"] <= 0        # nenhuma rolagem lateral (nem a da navbar nem a da página) e os 4 na mesma linha
    finally:
        ctx.close()


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# arrastar várias vezes no Reescrever (0b): avançar o tempo, pausar e arrastar de novo põe uma parada nova que parte daquele quadro
# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------

from tests.test_reescrever_comandos import _abre_no_instante  # noqa: E402
from tests.test_reescrever_modo import _estado  # noqa: E402
from tests.test_reescrever_r3 import XY  # noqa: E402


@pytest.fixture(scope="module")
def pagina_cmd(tmp_path_factory):
    from scripts.build_reescrever_comandos import escreve
    from scripts.build_web_page import build_html
    from tests.test_reescrever_modo import PARTIDA
    d = tmp_path_factory.mktemp("arrasta")
    arq = d / f"{PARTIDA}.html"
    arq.write_text(build_html(PARTIDA), encoding="utf-8")
    escreve(d, ["de_mirage"])
    return arq


def _arrasta(pg, nome, dx=70, dy=-50):
    """Pega a peça ONDE ELA ESTÁ na tela agora (no quadro em que a sua versão está pausada, não na última parada) e a solta `dx`, `dy` px adiante."""
    xy = pg.evaluate("n => window.__reescrever().pecas.find(p => p.nome === n).tela", nome)
    pg.mouse.move(*xy); pg.mouse.down(); pg.mouse.move(xy[0] + dx, xy[1] + dy, steps=5); pg.mouse.up()
    pg.wait_for_timeout(150)


def _trilha(pg, nome):
    return next(p for p in _estado(pg)["pecas"] if p["nome"] == nome)["trilha"]


def _avanca(pg, quadros):
    """Toca a sua versão e pausa `quadros` quadros depois (o quadro atual é o do scrub)."""
    alvo = int(_estado(pg)["quadro"]) + quadros
    pg.click("#play")
    pg.wait_for_function("q => window.__reescrever().quadro >= q", arg=alvo, timeout=20000)
    pg.click("#play")
    pg.wait_for_timeout(120)


def test_arrastar_de_novo_com_o_tempo_avancado_poe_uma_parada_nova_e_o_desfazer_tira_uma_por_vez(navegador, pagina_cmd):
    ctx, pg, erros = _abre_no_instante(navegador, pagina_cmd)
    try:
        pg.click("#rw-entrar")
        t0 = _estado(pg)["instante"]
        _arrasta(pg, "ropz", dx=60, dy=-40)                                                     # a primeira parada: no instante, como sempre
        _avanca(pg, 12)
        assert _estado(pg)["sua"] and pg.is_enabled("#rw-desfazer") and "avance o tempo e arraste outra vez" in pg.inner_text("#rw-dica")
        _arrasta(pg, "ropz", dx=-50, dy=60)                                                     # pausada: arrastar de novo = uma parada nova, daquele quadro
        _avanca(pg, 12)
        _arrasta(pg, "ropz", dx=40, dy=40)
        fs = [pa["f"] for pa in _trilha(pg, "ropz")]
        assert len(fs) == 3 and fs[0] == t0 and t0 < fs[1] < fs[2] and fs == sorted(fs)          # três paradas, em ordem, cada uma no quadro em que foi arrastada
        assert _estado(pg)["comandos"]["desfazer"] == 3
        mudou = pg.inner_text("#rw-mudou")
        assert mudou.count("ropz") >= 3                                                         # cada arrasto é uma linha, com o nick e o horário
        # o corte: volta o tempo para antes da segunda parada e arrasta: o que vinha depois some
        pg.evaluate("f => { const s = document.getElementById('scrub'); s.value = f; s.dispatchEvent(new Event('input')); }", fs[1] - 2)
        pg.wait_for_timeout(150)
        _arrasta(pg, "ropz", dx=20, dy=-80)
        novo = [pa["f"] for pa in _trilha(pg, "ropz")]
        assert novo[0] == t0 and len(novo) == 2 and novo[1] == fs[1] - 2                         # a primeira fica; a segunda e a terceira foram cortadas e entrou a nova
        assert _estado(pg)["comandos"]["desfazer"] == 4
        pg.click("#rw-desfazer"); pg.click("#rw-desfazer")                                      # dois Desfazer tiram uma parada por vez: o corte volta, depois a terceira
        assert [pa["f"] for pa in _trilha(pg, "ropz")] == fs[:2] and _estado(pg)["comandos"]["desfazer"] == 2
        assert erros == []
    finally:
        ctx.close()


def test_nao_arrasta_tocando_nem_antes_do_instante_nem_depois_da_morte_real(navegador, pagina_cmd):
    ctx, pg, erros = _abre_no_instante(navegador, pagina_cmd)
    try:
        pg.click("#rw-entrar")
        t0 = _estado(pg)["instante"]
        _arrasta(pg, "ZywOo", dx=60, dy=-40)                                                    # ZywOo morre no real depois do instante (quadro 249, 0:52)
        _avanca(pg, 8)
        pg.click("#play")                                                                       # tocando: nada é editável
        antes = _trilha(pg, "ZywOo")
        _arrasta(pg, "ZywOo", dx=-50, dy=50)
        assert _trilha(pg, "ZywOo") == antes and pg.is_disabled("#rw-desfazer")
        pg.click("#play")
        scrub = "f => { const s = document.getElementById('scrub'); s.value = f; s.dispatchEvent(new Event('input')); }"
        pg.evaluate(scrub, t0 - 6)                                                              # antes do instante do "Reescrever daqui"
        pg.wait_for_timeout(150)
        _arrasta(pg, "ZywOo", dx=-50, dy=50)
        assert _trilha(pg, "ZywOo") == antes
        pg.evaluate(scrub, 252)                                                                 # depois da morte real (249): só existe no real
        pg.wait_for_timeout(150)
        _arrasta(pg, "ZywOo", dx=-50, dy=50)
        assert _trilha(pg, "ZywOo") == antes and _estado(pg)["comandos"]["desfazer"] == 1
        pg.evaluate(scrub, 200)                                                                 # antes da morte: volta a valer
        pg.wait_for_timeout(150)
        _arrasta(pg, "ZywOo", dx=-50, dy=50)
        assert len(_trilha(pg, "ZywOo")) == 2 and erros == []
    finally:
        ctx.close()


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# "Ver no mapa ↑" no celular, depois do Aplicar (Reescrever e prancheta)
# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def _dentro_da_janela(pg, seletor):
    return pg.evaluate("s => { const r = document.querySelector(s).getBoundingClientRect(); return r.top >= 0 && r.top < innerHeight && r.bottom > 0; }", seletor)


def test_ver_no_mapa_no_reescrever_leva_a_pagina_ao_mapa_poe_o_foco_nele_e_anuncia(navegador, pagina_cmd):
    from tests.test_reescrever_comandos import _abre_secao, _aplica, _escreve
    ctx, pg, erros = _abre_no_instante(navegador, pagina_cmd, 375, 812)
    try:
        _abre_secao(pg)
        assert pg.locator("#rw-cmd-ver-mapa").count() == 0                                      # antes do Aplicar não há botão
        _escreve(pg, "ropz corre pro meio aos 1:10"); _aplica(pg)
        assert pg.locator("#rw-cmd-ver-mapa").count() == 1 and pg.inner_text("#rw-cmd-ver-mapa") == "Ver no mapa ↑"
        pg.locator("#rw-cmd-ver-mapa").scroll_into_view_if_needed()
        assert not _dentro_da_janela(pg, "#palco")                                              # no celular o mapa ficou para cima
        y = pg.evaluate("scrollY")
        pg.click("#rw-cmd-ver-mapa")
        assert pg.evaluate("scrollY") < y and _dentro_da_janela(pg, "#map")                      # a página subiu ao mapa, de uma vez
        assert pg.evaluate("document.activeElement.id") == "map"                                 # o foco está no mapa (canvas com rótulo "Mapa do round")
        assert "O mapa está à vista." in pg.inner_text("#rw-cmd-cartao") and pg.locator("#rw-cmd-ver-mapa").count() == 0
        assert pg.get_attribute("#rw-cmd-cartao", "aria-live") == "polite" and erros == []       # o aviso vai pela região viva do cartão
    finally:
        ctx.close()


def test_ver_no_mapa_so_aparece_no_celular_e_nunca_no_computador(navegador, pagina_cmd):
    from tests.test_reescrever_comandos import _abre_secao, _aplica, _escreve
    ctx, pg, _ = _abre_no_instante(navegador, pagina_cmd, 1440, 900)
    try:
        _abre_secao(pg); _escreve(pg, "ropz corre pro meio aos 1:10"); _aplica(pg)
        assert pg.locator("#rw-cmd-ver-mapa").count() == 1 and not pg.is_visible("#rw-cmd-ver-mapa")      # existe, mas o CSS o esconde: o mapa já está ao lado
    finally:
        ctx.close()


def test_ver_no_mapa_na_prancheta_leva_a_pagina_ao_mapa_poe_o_foco_nele_e_anuncia(navegador, tmp_path_factory):
    from scripts.build_tactics_page import arquivo_da_pagina, build_html
    from tests.test_comandos_tempos import _peca, _ponto
    d = tmp_path_factory.mktemp("pr_vermapa")
    arq = d / arquivo_da_pagina("de_mirage")
    arq.write_text(build_html("de_mirage"), encoding="utf-8")
    ctx = navegador.new_context(viewport={"width": 375, "height": 812})
    pg = ctx.new_page(); erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    try:
        pg.goto(arq.as_uri())
        pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
        base = _ponto("de_mirage", "Base TR")
        _peca(pg, base["x"], base["y"])
        pg.evaluate("() => Prancheta._interno.abaDoPainel('comandos')")
        pg.fill("#pr-cmd-texto", "tr 2 corre pro meio aos 1:30"); pg.click("#pr-cmd-entender")
        pg.wait_for_function("() => document.querySelectorAll('#pr-cmd-entendi li').length === 1")
        assert pg.locator("#pr-cmd-ver-mapa").count() == 0
        pg.click("#pr-cmd-aplicar")
        pg.wait_for_selector("#pr-cmd-ver-mapa")
        assert pg.inner_text("#pr-cmd-ver-mapa") == "Ver no mapa ↑"
        pg.locator("#pr-cmd-ver-mapa").scroll_into_view_if_needed()
        assert not _dentro_da_janela(pg, "#pr-palco")
        y = pg.evaluate("scrollY")
        pg.click("#pr-cmd-ver-mapa")
        assert pg.evaluate("scrollY") < y and _dentro_da_janela(pg, "#pr-mapa")
        assert pg.evaluate("document.activeElement.id") == "pr-mapa"
        assert "O mapa está à vista." in pg.inner_text("#pr-cmd-resultado") and pg.locator("#pr-cmd-ver-mapa").count() == 0 and erros == []
        pg.set_viewport_size({"width": 1440, "height": 900})                                    # no computador o botão fica escondido
        pg.fill("#pr-cmd-texto", "tr 2 corre pro meio aos 1:20"); pg.click("#pr-cmd-entender")
        pg.wait_for_function("() => document.querySelectorAll('#pr-cmd-entendi li').length === 1")
        pg.click("#pr-cmd-aplicar")
        assert pg.locator("#pr-cmd-ver-mapa").count() == 1 and not pg.is_visible("#pr-cmd-ver-mapa")
    finally:
        ctx.close()


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# o nome do time no cabeçalho da partida: "Time de <nick>" mantém a grafia do nick; os times profissionais continuam em maiúsculas
# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("partida,esperado,transforma", [("match_01", ["Time de t1ltedbot", "Time de HLEB"], "none"), ("match_43", ["FURIA", "Vitality"], "uppercase")])
def test_o_nome_do_time_faceit_mantem_a_grafia_do_nick_e_o_profissional_segue_em_maiusculas(navegador, tmp_path_factory, partida, esperado, transforma):
    from pathlib import Path
    from scripts.build_web_page import build_html
    if not (Path(__file__).resolve().parent.parent / "data" / "processed" / partida / "web_payload.json").exists():
        pytest.skip("sem o processado")
    arq = tmp_path_factory.mktemp("cab") / f"{partida}.html"
    arq.write_text(build_html(partida), encoding="utf-8")
    ctx = navegador.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page()
    try:
        pg.goto(arq.as_uri())
        r = pg.eval_on_selector_all(".placar .nome", "ns => ns.map(n => [n.textContent, getComputedStyle(n).textTransform, n.innerText])")
        assert sorted(t for t, _, _ in r) == sorted(esperado) and all(tt == transforma for _, tt, _ in r)
        assert sorted(i for _, _, i in r) == sorted(esperado if transforma == "none" else [e.upper() for e in esperado])      # o que se VÊ: a grafia do nick, ou o nome em maiúsculas
    finally:
        ctx.close()


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# a peça embaixo do relógio grande da prancheta: o fundo do relógio fica translúcido (instantâneo), os números seguem legíveis (>= 3:1 contra o mapa)
# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------

from tests.test_tactics_browser import abre, contexto, interno, pagina_do_mapa  # noqa: E402,F401

ALFA_DO_FUNDO = "rgba(8, 10, 36, 0.5)"
CENTRO_DO_RELOGIO = "() => { const r = document.getElementById('pr-relogio-grande').getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }"


def _prancheta(contexto, tmp_path_factory, largura=375):
    pg = abre(contexto, pagina_do_mapa(tmp_path_factory, "de_mirage"))
    pg.set_viewport_size({"width": largura, "height": 812})      # o relógio só passa por cima do mapa onde o mapa o alcança: no celular (no computador ele fica na margem)
    pg.locator("#pr-mapa").scroll_into_view_if_needed()
    return pg


def _fundo(pg):
    return pg.evaluate("() => { const r = document.getElementById('pr-relogio-grande'); const s = getComputedStyle(r); return { fundo: s.backgroundColor, sob: r.classList.contains('sob-peca'), ponteiro: s.pointerEvents, transicao: s.transitionDuration, oculto: r.hidden }; }")


def _poe_a_peca_sob_o_relogio(pg):
    """Muda a vista (zoom 1) para que a peça `demo-t2` fique no centro do relógio grande, sem mexer na tática."""
    pg.evaluate("""() => { const I = Prancheta._interno, S = I.S, cv = document.getElementById('pr-mapa'), r = document.getElementById('pr-relogio-grande').getBoundingClientRect(), c = cv.getBoundingClientRect();
      const p = S.ultimoDesenho.find(d => d.tipo === 'peca'), k = cv.width / c.width, a = cv.getContext('2d').getTransform().a / S.view.zoom;
      S.view.zoom = 1; S.view.panX = ((r.left + r.width / 2 - c.left) * k) / a - p.x; S.view.panY = ((r.top + r.height / 2 - c.top) * k) / a - p.y; I.atualizaTudo(); }""")


def test_a_peca_arrastada_para_baixo_do_relogio_deixa_so_o_fundo_translucido_e_volta_ao_sair(contexto, tmp_path_factory):
    pg = _prancheta(contexto, tmp_path_factory)
    try:
        from tests.test_comandos_tempos import _peca, _ponto
        base = _ponto("de_mirage", "Base TR")
        _peca(pg, base["x"], base["y"])
        pg.wait_for_timeout(100)
        antes = _fundo(pg)
        assert not antes["oculto"] and not antes["sob"] and antes["fundo"] != ALFA_DO_FUNDO and antes["ponteiro"] == "none"
        cx, cy = pg.evaluate(CENTRO_DO_RELOGIO)
        # a ficha está no mapa: pega-a e leva até o centro do relógio (o relógio não recebe o ponteiro: o soltar cai no mapa)
        xy = pg.evaluate("""() => { const I = Prancheta._interno, S = I.S, cv = document.getElementById('pr-mapa'), c = cv.getBoundingClientRect(), p = S.ultimoDesenho.find(d => d.tipo === 'peca'),
          k = cv.width / c.width, t = cv.getContext('2d').getTransform(); return [c.left + (t.a * p.x + t.e) / k, c.top + (t.d * p.y + t.f) / k]; }""")
        pg.mouse.move(*xy); pg.mouse.down(); pg.mouse.move(cx, cy, steps=8); pg.mouse.up()
        pg.wait_for_timeout(150)
        dentro = _fundo(pg)
        assert dentro["sob"] and dentro["fundo"] == ALFA_DO_FUNDO and dentro["transicao"] in ("0s", "") and dentro["ponteiro"] == "none"      # translúcido, sem transição, sem ponteiro
        pg.evaluate("() => { const I = Prancheta._interno; I.S.view.panX += 600; I.atualizaTudo(); }")                        # a peça sai de baixo do relógio (a vista anda)
        pg.wait_for_timeout(150)
        fora = _fundo(pg)
        assert not fora["sob"] and fora["fundo"] == antes["fundo"] and pg._erros == []
    finally:
        pg.close()


def test_a_peca_posta_por_comando_fica_sob_o_relogio_e_na_reproducao_o_relogio_acompanha(contexto, tmp_path_factory):
    from tests.test_comandos_tempos import _escreve, _peca, _ponto
    from tests.test_comandos_aba import _aplica
    pg = _prancheta(contexto, tmp_path_factory)
    try:
        base = _ponto("de_mirage", "Base TR")
        _peca(pg, base["x"], base["y"])
        _escreve(pg, "tr 2 corre pro meio aos 1:50")                                            # por comando: a peça anda até o meio
        pg.wait_for_function("() => document.querySelectorAll('#pr-cmd-entendi li').length === 1")
        _aplica(pg)
        fim = interno(pg, "I.fimDaTatica(S.e3)")
        pg.evaluate("t => Prancheta._interno.defineTempo(t)", fim)
        pg.wait_for_timeout(150)
        assert not _fundo(pg)["sob"]
        _poe_a_peca_sob_o_relogio(pg)                                                           # a vista leva o meio (onde a peça chegou) até o relógio
        assert _fundo(pg)["sob"] and _fundo(pg)["fundo"] == ALFA_DO_FUNDO
        # na reprodução: a peça sai de onde estava, passa por baixo do relógio e segue; o fundo acompanha quadro a quadro
        pg.evaluate("() => { const I = Prancheta._interno; I.comecaReproducao(); }")
        quando = []
        for f in (0.0, 0.5, 1.0):
            pg.evaluate("t => Prancheta._interno.reproduzAte(t)", fim * f)
            pg.wait_for_timeout(60)
            quando.append(_fundo(pg)["sob"])
        assert quando[-1] is True and quando[0] is False                                        # no fim ela está sob o relógio; no começo, não
        assert pg._erros == []
    finally:
        pg.close()


def test_com_o_fundo_translucido_os_numeros_do_relogio_tem_3_para_1_contra_o_mapa_nos_mapas_com_radar(contexto, tmp_path_factory):
    """Pior caso por mapa: o pixel mais claro do radar desenhado (percentil 99,9) e as cores das peças (CT e TR), sob o fundo translúcido do relógio, contra a cor dos números."""
    from scripts.build_tactics_page import arquivo_da_pagina, build_html, mapas_disponiveis
    from tests.test_comandos_tempos import _peca
    medidas = {}
    for mapa in mapas_disponiveis():
        arq = tmp_path_factory.mktemp("rel_" + mapa) / arquivo_da_pagina(mapa)
        arq.write_text(build_html(mapa), encoding="utf-8")
        pg = abre(contexto, arq)
        try:
            pg.set_viewport_size({"width": 1440, "height": 900})
            _peca(pg, 0, 0)
            pg.wait_for_timeout(300)
            r = pg.evaluate("""() => {
              const rel = document.getElementById('pr-relogio-grande'), cv = document.getElementById('pr-mapa'); rel.classList.add('sob-peca');
              const num = s => (s.match(/[\d.]+/g) || []).map(Number), lin = c => { const v = c / 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
              const lum = (r, g, b) => 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
              const st = getComputedStyle(rel), texto = num(st.color), fundo = num(st.backgroundColor), a = fundo.length > 3 ? fundo[3] : 1;
              const d = cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data, ls = [];
              for (let i = 0; i < d.length; i += 4 * 7) if (d[i + 3] > 200) ls.push(lum(d[i], d[i + 1], d[i + 2]));
              ls.sort((x, y) => x - y); const brilho = ls[Math.floor(0.999 * (ls.length - 1))];
              const raiz = getComputedStyle(document.documentElement), cor = n => { const t = document.createElement('i'); t.style.color = raiz.getPropertyValue(n); document.body.appendChild(t); const v = num(getComputedStyle(t).color); t.remove(); return v; };
              const amostras = { radar: null, ct: cor('--ct-mapa'), tr: cor('--tr-mapa') };
              const mistura = (v) => v.slice(0, 3).map((c, i) => a * fundo[i] + (1 - a) * c);       // o navegador mistura em sRGB
              const lt = lum(texto[0], texto[1], texto[2]), out = { alfa: a, lt: lt, brilho: brilho };
              const lradar = brilho;      // a luminância do pixel mais claro já está em linear: mistura o fundo (em sRGB) com um cinza dessa luminância
              const cinza = 255 * (lradar <= 0.0031308 ? lradar * 12.92 : 1.055 * Math.pow(lradar, 1 / 2.4) - 0.055);
              const comp = { radar: mistura([cinza, cinza, cinza]), ct: mistura(amostras.ct), tr: mistura(amostras.tr) };
              Object.keys(comp).forEach(k => { out[k] = (lt + 0.05) / (lum(comp[k][0], comp[k][1], comp[k][2]) + 0.05); });
              return out; }""")
            medidas[mapa] = r
        finally:
            pg.close()
    print("\ncontraste dos números do relógio translúcido (>= 3:1):", {m: {k: round(v, 2) for k, v in r.items() if k in ("radar", "ct", "tr")} for m, r in medidas.items()})
    assert len(medidas) >= 8
    for mapa, r in medidas.items():
        assert r["alfa"] == 0.5 and min(r["radar"], r["ct"], r["tr"]) >= 3.0, (mapa, r)


def test_no_computador_o_relogio_fica_na_margem_do_mapa_e_nunca_fica_translucido(contexto, tmp_path_factory):
    from tests.test_comandos_tempos import _peca, _ponto
    pg = _prancheta(contexto, tmp_path_factory, largura=1440)
    try:
        base = _ponto("de_mirage", "Base TR")
        _peca(pg, base["x"], base["y"])
        pg.wait_for_timeout(100)
        cv, rel = pg.evaluate("() => [document.getElementById('pr-mapa').getBoundingClientRect().toJSON(), document.getElementById('pr-relogio-grande').getBoundingClientRect().toJSON()]")
        assert rel["right"] < cv["left"]                                                         # a 1440 o relógio está na margem, fora do canvas
        pg.evaluate("() => { const S = Prancheta._interno.S; S.view.panX += 300; Prancheta._interno.atualizaTudo(); }")      # mexe a vista: nada passa por baixo dele
        assert not _fundo(pg)["sob"] and _fundo(pg)["fundo"] != ALFA_DO_FUNDO
    finally:
        pg.close()


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# "O que mudou": o lugar de saída e o destino de cada arrasto seguem a regra de nomes da C3
# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------

CRUS = ("TRamp", "PalaceAlley", "CTSpawn", "TopofMid", "BombsiteA", "BombsiteB")      # o nome do jogo como a demo grava (sem espaço)


def _nomes_da_c3_mirage():
    """Os nomes que a regra da C3 escreve: o ponto do Pedro ou o nome legível da área (o do botão Lugares)."""
    from scripts.comandos_contexto import contexto
    c = contexto("de_mirage", so_conferidos=True)
    return {p["nome"] for p in c["pontos"]} | {a.get("exibe") or a["texto"] for a in c["areas"]}


def test_as_linhas_de_arrasto_de_o_que_mudou_dizem_de_onde_e_ate_onde_pelo_nome_da_c3(navegador, pagina_cmd):
    import re
    nomes = _nomes_da_c3_mirage()
    ctx, pg, erros = _abre_no_instante(navegador, pagina_cmd)
    try:
        pg.click("#rw-entrar")
        _arrasta(pg, "ropz", dx=60, dy=-40)
        _avanca(pg, 12)
        _arrasta(pg, "ropz", dx=-50, dy=60)
        linhas = [l for l in pg.locator("#rw-mudou li").all_inner_texts() if l.startswith("ropz sai")]
        assert len(linhas) == 2
        for l in linhas:
            m = re.match(r"ropz sai (?:de (.+) )?às \d:\d\d e vai até (.+): chega às ", l)
            assert m, l
            de, para = m.group(1), m.group(2)
            assert (de is None or de in nomes) and para in nomes, (l, sorted(nomes)[:6])      # nomes legíveis, os mesmos do botão Lugares
            assert not any(c in l for c in CRUS) and "o ponto marcado" not in l
        assert linhas[0].startswith("ropz sai de ")                                          # a primeira parte de um lugar conhecido
    finally:
        ctx.close()


def test_sem_a_tabela_de_lugares_a_linha_volta_a_dizer_o_ponto_marcado(navegador, tmp_path_factory, monkeypatch):
    import scripts.build_web_page as bw
    from tests.test_reescrever_modo import PARTIDA
    monkeypatch.setattr(bw, "_lugares_do_reescrever", lambda base, match_id: None)
    arq = tmp_path_factory.mktemp("sem_lugares") / f"{PARTIDA}.html"
    arq.write_text(bw.build_html(PARTIDA), encoding="utf-8")
    ctx, pg, erros = _abre_no_instante(navegador, arq)
    try:
        pg.click("#rw-entrar")
        _arrasta(pg, "ropz", dx=60, dy=-40)
        linha = next(l for l in pg.locator("#rw-mudou li").all_inner_texts() if l.startswith("ropz sai"))
        assert " e vai até o ponto marcado: chega às " in linha and erros == []
    finally:
        ctx.close()
