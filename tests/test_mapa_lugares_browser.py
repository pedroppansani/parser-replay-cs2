"""Fase M (decisão 52): radar mais nítido, nomes de lugar, bombsites e a peça do outro andar, no navegador.

O que se trava, em ordem:
- o radar é reduzido com `imageSmoothingQuality = "high"` (replay e prancheta);
- o nome de lugar é o que o dado traz, em caixa alta, e só aparece onde não cobre peça, nome de jogador, bombsite nem outro nome
  de lugar; o botão "Lugares" liga e desliga (lembrado), e as letras A e B dos bombsites ficam;
- nenhum nome de jogador some, mesmo com peças empilhadas; o que sai de cima da peça ganha a linha fina;
- a peça do outro andar é um disco cinza com anel na cor do lado e seta, e o nome dela vai em itálico;
- mapa sem tabela (Train): sem nome de lugar e sem botão.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_tactics_browser import navegador  # noqa: E402,F401  (fixture)

RAIZ = Path(__file__).resolve().parent.parent
MIRAGE, NUKE, TRAIN = "match_02", "match_05", "match_31"

REGISTRA_PEDIDOS = """
document.addEventListener("DOMContentLoaded", () => {
  const f = MapCore.desenhaJogador; window.__pedidos = [];
  MapCore.desenhaJogador = function (c, x, y, o) { window.__pedidos.push({ estado: o.estado, nome: o.nome || "" }); return f.apply(this, arguments); };
});
"""
REGISTRA_SUAVIZACAO = """
(() => { window.__suavizacao = []; const f = CanvasRenderingContext2D.prototype.drawImage;
  CanvasRenderingContext2D.prototype.drawImage = function (img) {
    const w = img.naturalWidth || img.width || 0;
    // só a redução do radar (com tamanho de destino); a cópia 1:1 que detecta a moldura não redimensiona nada
    if (w >= 512 && arguments.length >= 5) window.__suavizacao.push(this.imageSmoothingQuality);
    return f.apply(this, arguments);
  }; })();
"""


def _paginas(tmp_path_factory):
    from scripts.build_tactics_page import build_html as prancheta
    from scripts.build_web_page import build_html
    pasta = tmp_path_factory.mktemp("fase_m")
    for mid in (MIRAGE, NUKE, TRAIN):
        if not (RAIZ / "data" / "processed" / mid / "web_payload.json").exists():
            pytest.skip("sem o processado")
        (pasta / f"{mid}.html").write_text(build_html(mid), encoding="utf-8")
    for mapa in ("de_mirage", "de_train"):
        (pasta / f"prancheta_{mapa}.html").write_text(prancheta(mapa), encoding="utf-8")
    return pasta


@pytest.fixture(scope="module")
def paginas(tmp_path_factory):
    return _paginas(tmp_path_factory)


def _abre_replay(navegador, pasta, mid, rnd=6, frac=0.45, andar=None, w=1440, h=900, init=()):
    ctx = navegador.new_context(viewport={"width": w, "height": h})
    for s in init:
        ctx.add_init_script(s)
    pg = ctx.new_page()
    erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto((pasta / f"{mid}.html").as_uri())
    pg.locator('[data-tab="replay"]').first.click()
    pg.wait_for_function("() => window.MapAnnotations && MapAnnotations._interno.S.reprojecoes > 0")
    pg.locator("#strip button", has_text=str(rnd)).first.click()
    if andar is not None:
        pg.locator(f'.levelpick button[data-lv="{andar}"]').click()
    _scrub(pg, frac)
    pg._erros = erros
    return ctx, pg


def _scrub(pg, frac):
    pg.evaluate("""f => { const s = document.getElementById('scrub'); s.value = Math.floor(s.max * f);
                          s.dispatchEvent(new Event('input')); }""", frac)
    pg.wait_for_timeout(500)


def _caixas(pg):
    return pg.evaluate("""() => { const m = window.__medicaoRotulos;
        return { nomes: m.caixas(), lugares: m.lugares(), sitios: m.sitios(), pecas: m.pecas() }; }""")


def _bate(a, b):
    return min(a["x"] + a["w"], b["x"] + b["w"]) > max(a["x"], b["x"]) and min(a["y"] + a["h"], b["y"] + b["h"]) > max(a["y"], b["y"])


def _nomes_da_tabela(mapa):
    from metrics.lugares import texto_do_lugar
    tab = json.loads((RAIZ / "data" / "lugares" / f"{mapa}.json").read_text(encoding="utf-8"))
    return {texto_do_lugar(n) for n in tab["nomes"]}


# --- o radar ---------------------------------------------------------------------------------------------------------------

def test_o_radar_e_reduzido_com_a_suavizacao_alta_no_replay_e_na_prancheta(navegador, paginas):
    ctx, pg = _abre_replay(navegador, paginas, MIRAGE, init=(REGISTRA_SUAVIZACAO,))
    usos = pg.evaluate("() => window.__suavizacao")
    assert usos and set(usos) == {"high"}, usos
    ctx.close()
    ctx = navegador.new_context(viewport={"width": 1300, "height": 950})
    ctx.add_init_script(REGISTRA_SUAVIZACAO)
    pg = ctx.new_page()
    pg.goto((paginas / "prancheta_de_mirage.html").as_uri())
    pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
    pg.wait_for_timeout(500)
    usos = pg.evaluate("() => window.__suavizacao")
    assert usos and set(usos) == {"high"}, usos
    ctx.close()


# --- os nomes de lugar e os bombsites ------------------------------------------------------------------------------------

def test_nomes_de_lugar_e_bombsites_aparecem_sem_cobrir_nada(navegador, paginas):
    ctx, pg = _abre_replay(navegador, paginas, MIRAGE)
    c = _caixas(pg)
    assert not pg._erros
    assert {s["txt"] for s in c["sitios"]} == {"A", "B"}
    assert len(c["lugares"]) >= 5
    permitido = _nomes_da_tabela("de_mirage")
    for l in c["lugares"]:
        assert l["txt"] in permitido and l["txt"] == l["txt"].upper()      # o nome do dado, em caixa alta, nada inventado
        assert not l["txt"].startswith("BOMBSITE")                          # o bombsite é só a letra
    assert all("CTSPAWN" != l["txt"] and "TSPAWN" != l["txt"] and "SNIPERSNEST" != l["txt"] for l in c["lugares"])
    todos = c["pecas"] + c["nomes"] + c["sitios"]
    for i, l in enumerate(c["lugares"]):
        assert not any(_bate(l, o) for o in todos), ("nome de lugar cobre peça, nome ou bombsite", l)
        assert not any(_bate(l, o) for o in c["lugares"][i + 1:]), ("dois nomes de lugar se cobrem", l)
    ctx.close()


def test_o_botao_lugares_liga_e_desliga_so_os_nomes_e_lembra_a_escolha(navegador, paginas):
    ctx, pg = _abre_replay(navegador, paginas, MIRAGE)
    botao = pg.locator("#lugares-botao")
    assert botao.get_attribute("aria-pressed") == "true" and len(_caixas(pg)["lugares"]) >= 5
    botao.click(); pg.wait_for_timeout(300)
    c = _caixas(pg)
    assert botao.get_attribute("aria-pressed") == "false"
    assert c["lugares"] == [] and {s["txt"] for s in c["sitios"]} == {"A", "B"}      # os bombsites ficam
    assert pg.evaluate("() => localStorage.getItem('mapa:lugares')") == "0"
    pg.reload(); pg.locator('[data-tab="replay"]').first.click()
    pg.wait_for_function("() => window.MapAnnotations && MapAnnotations._interno.S.reprojecoes > 0")
    pg.wait_for_timeout(400)
    assert pg.locator("#lugares-botao").get_attribute("aria-pressed") == "false"
    assert _caixas(pg)["lugares"] == []
    pg.locator("#lugares-botao").click(); pg.wait_for_timeout(300)
    assert len(_caixas(pg)["lugares"]) >= 5
    ctx.close()


def test_a_prancheta_tem_os_nomes_de_lugar_e_o_botao(navegador, paginas):
    ctx = navegador.new_context(viewport={"width": 1300, "height": 950})
    pg = ctx.new_page()
    pg.goto((paginas / "prancheta_de_mirage.html").as_uri())
    pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
    pg.wait_for_timeout(500)
    c = _caixas(pg)
    assert {s["txt"] for s in c["sitios"]} == {"A", "B"} and len(c["lugares"]) >= 5
    assert not any(_bate(l, o) for l in c["lugares"] for o in c["pecas"] + c["nomes"] + c["sitios"])
    pg.locator("#pr-lugares").click(); pg.wait_for_timeout(300)
    assert _caixas(pg)["lugares"] == [] and pg.locator("#pr-lugares").get_attribute("aria-pressed") == "false"
    ctx.close()


def test_mapa_sem_tabela_nao_tem_nome_de_lugar_nem_botao(navegador, paginas):
    ctx, pg = _abre_replay(navegador, paginas, TRAIN, rnd=3)
    c = _caixas(pg)
    assert c["lugares"] == [] and c["sitios"] == [] and pg.locator("#lugares-botao").count() == 0
    ctx.close()
    ctx = navegador.new_context(viewport={"width": 1300, "height": 950})
    pg = ctx.new_page()
    pg.goto((paginas / "prancheta_de_train.html").as_uri())
    pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
    pg.wait_for_timeout(400)
    assert _caixas(pg)["lugares"] == [] and pg.locator("#pr-lugares").count() == 0
    ctx.close()


# --- os nomes dos jogadores ----------------------------------------------------------------------------------------------

def test_nenhum_nome_de_jogador_some_numa_cena_apertada_da_nuke(navegador, paginas):
    for andar in (0, 1):
        ctx, pg = _abre_replay(navegador, paginas, NUKE, rnd=9, frac=0.40, andar=andar, init=(REGISTRA_PEDIDOS,))
        pg.evaluate("() => { window.__pedidos = []; }")
        _scrub(pg, 0.40)
        pedidos = pg.evaluate("() => window.__pedidos")
        pedidos_nomes = {p["nome"][:9] for p in pedidos if p["estado"] != "morto" and p["nome"]}
        desenhados = {c["txt"] for c in _caixas(pg)["nomes"]}
        assert pedidos_nomes and pedidos_nomes <= desenhados, (andar, pedidos_nomes - desenhados)
        ctx.close()


def test_nomes_de_outro_andar_vao_em_italico_e_so_eles(navegador, paginas):
    ctx, pg = _abre_replay(navegador, paginas, NUKE, rnd=9, frac=0.40, andar=1, init=(REGISTRA_PEDIDOS,))
    pg.evaluate("() => { window.__pedidos = []; }")
    _scrub(pg, 0.40)
    pedidos = pg.evaluate("() => window.__pedidos")
    outro = {p["nome"][:9] for p in pedidos if p["estado"] == "outro_andar" and p["nome"]}
    vivos = {p["nome"][:9] for p in pedidos if p["estado"] == "vivo" and p["nome"]}
    italicos = {c["txt"] for c in _caixas(pg)["nomes"] if c["italico"]}
    assert outro, "a cena de controle precisa ter jogador no outro andar"
    assert italicos == outro and not (italicos & vivos)
    ctx.close()


def test_peças_empilhadas_mantem_todos_os_nomes_e_o_que_sai_de_cima_ganha_a_linha(navegador, paginas):
    """A regra sozinha, sem depender de um round: cinco peças no mesmo ponto."""
    ctx, pg = _abre_replay(navegador, paginas, MIRAGE)
    r = pg.evaluate("""() => {
      const cv = document.createElement('canvas'); cv.width = 600; cv.height = 400; cv.style.cssText = 'position:fixed;left:0;top:0;width:600px;height:400px';
      document.body.appendChild(cv);
      const g = cv.getContext('2d'); g.setTransform(1, 0, 0, 1, 0, 0);
      let redesenhou = 0; MapCore.rotulosInicia(g, cv, () => { redesenhou++; });
      ['alfa', 'bravo', 'charlie', 'delta', 'eco'].forEach((n, i) => MapCore.desenhaJogador(g, 300 + i * 3, 200, { cor: '#4a90e2', estado: 'vivo', hp: 100, nome: n }));
      MapCore.rotulosDesenha();
      const caixas = window.__medicaoRotulos.caixas(); cv.remove();
      return caixas.map(c => ({ txt: c.txt, x: c.x, y: c.y, w: c.w, h: c.h, linha: c.linha }));
    }""")
    assert sorted(c["txt"] for c in r) == ["alfa", "bravo", "charlie", "delta", "eco"]        # nenhum some
    assert sum(1 for c in r if c["linha"]) >= 3                                                # os que saíram de cima: linha fina
    for i, a in enumerate(r):
        assert not any(_bate(a, b) for b in r[i + 1:]), ("dois nomes se cobrem", a)
    ctx.close()


def test_o_nome_de_lugar_nao_fica_sobre_uma_peca_posta_na_ancora(navegador, paginas):
    ctx, pg = _abre_replay(navegador, paginas, MIRAGE)
    r = pg.evaluate("""() => {
      const rad = window.__RADAR__, ancora = rad.lugares.rotulos[0].find(p => !/^Bombsite/.test(rad.lugares.nomes[p[0]]));
      const nome = rad.lugares.nomes[ancora[0]].toUpperCase(), [x, y] = ancora[1][0];
      const cv = document.getElementById('map'); const g = cv.getContext('2d');
      const k = cv.width / cv.getBoundingClientRect().width;
      const roda = (comPeca) => {
        g.setTransform(cv.width / rad.width, 0, 0, cv.height / rad.height, 0, 0);   // como o replay: radar -> canvas
        MapCore.rotulosInicia(g, cv, () => {});
        MapCore.lugaresRegistra(rad.lugares, 0);
        if (comPeca) MapCore.desenhaJogador(g, x, y, { cor: '#4a90e2', estado: 'vivo', hp: 100, nome: '' });
        MapCore.rotulosDesenha();
        return window.__medicaoRotulos.lugares().filter(c => c.txt === nome);
      };
      return { sem: roda(false), com: roda(true), nome, k };
    }""")
    assert len(r["sem"]) == 1                                  # sem a peça, o nome está na primeira âncora
    assert len(r["com"]) <= 1
    if r["com"]:                                               # com a peça na âncora, ele foi para outra âncora (ou sumiu)
        assert r["com"][0] != r["sem"][0]
    ctx.close()


# --- a peça do outro andar -----------------------------------------------------------------------------------------------

def test_a_peca_do_outro_andar_e_um_disco_cinza_com_anel_do_lado_e_seta(navegador, paginas):
    ctx, pg = _abre_replay(navegador, paginas, MIRAGE)
    px = pg.evaluate("""() => {
      const cv = document.createElement('canvas'); cv.width = 120; cv.height = 120; const g = cv.getContext('2d');
      MapCore.defineAnelDuplo(true);
      const e = 4; g.fillStyle = '#000'; g.fillRect(0, 0, 120, 120);
      MapCore.desenhaJogador(g, 60, 60, { cor: '#4a90e2', estado: 'outro_andar', acima: true, hp: 100, nome: '', escala: e });
      const pega = (dx, dy) => Array.from(g.getImageData(60 + dx, 60 + dy, 1, 1).data.slice(0, 3));
      let escuro = false;
      for (let dx = -8; dx <= 8; dx++) for (let dy = -8; dy <= 8; dy++) { const c = pega(dx, dy); if (c[0] + c[1] + c[2] < 120) escuro = true; }
      return { cinza: pega(0, -15), anel: pega(0, -22), escuro };
    }""")
    cinza, anel = px["cinza"], px["anel"]
    assert max(cinza) - min(cinza) < 40 and 100 < sum(cinza) / 3 < 190, cinza                 # o disco é cinza (apagado-mapa)
    assert anel[2] > anel[0] + 40, anel                                                       # o anel é azul (a cor do lado)
    assert px["escuro"]                                                                       # a seta escura no meio
    ctx.close()


# --- o celular -------------------------------------------------------------------------------------------------------------

def test_no_celular_os_lugares_comecam_desligados_e_a_escolha_e_lembrada_so_ali(navegador, paginas):
    ctx, pg = _abre_replay(navegador, paginas, MIRAGE, w=375, h=800)
    botao = pg.locator("#lugares-botao")
    c = _caixas(pg)
    assert botao.get_attribute("aria-pressed") == "false" and c["lugares"] == []
    assert {s["txt"] for s in c["sitios"]} == {"A", "B"}                  # as letras dos bombsites ficam
    botao.click(); pg.wait_for_timeout(300)
    assert botao.get_attribute("aria-pressed") == "true"
    assert pg.evaluate("() => [localStorage.getItem('mapa:lugares:celular'), localStorage.getItem('mapa:lugares')]") == ["1", None]
    pg.reload(); pg.locator('[data-tab="replay"]').first.click()
    pg.wait_for_function("() => window.MapAnnotations && MapAnnotations._interno.S.reprojecoes > 0")
    pg.wait_for_timeout(400)
    assert pg.locator("#lugares-botao").get_attribute("aria-pressed") == "true"      # lembrado
    ctx.close()


def test_no_computador_os_lugares_continuam_comecando_ligados(navegador, paginas):
    ctx, pg = _abre_replay(navegador, paginas, MIRAGE, w=1440, h=900)
    assert pg.locator("#lugares-botao").get_attribute("aria-pressed") == "true"
    assert pg.evaluate("() => [localStorage.getItem('mapa:lugares:celular'), localStorage.getItem('mapa:lugares')]") == [None, None]
    ctx.close()


# --- a moldura do radar da Nuke ------------------------------------------------------------------------------------------

def test_a_borda_visivel_do_radar_e_apagada_numa_copia_e_a_transparente_fica_como_esta(navegador, paginas):
    ctx, pg = _abre_replay(navegador, paginas, MIRAGE)
    r = pg.evaluate("""async () => {
      const carrega = (fn) => new Promise(ok => {
        const c = document.createElement('canvas'); c.width = 128; c.height = 128; fn(c.getContext('2d'));
        const im = new Image(); im.onload = () => ok(im); im.src = c.toDataURL();
      });
      const comMoldura = await carrega(g => { g.fillStyle = 'rgba(200,200,200,0.4)'; g.fillRect(127, 0, 1, 128); g.fillStyle = '#fff'; g.fillRect(60, 60, 8, 8); });
      const limpa = await carrega(g => { g.fillStyle = '#fff'; g.fillRect(60, 60, 8, 8); });
      const miuda = await new Promise(ok => { const c = document.createElement('canvas'); c.width = 4; c.height = 1; c.getContext('2d').fillRect(0, 0, 4, 1); const im = new Image(); im.onload = () => ok(im); im.src = c.toDataURL(); });
      const a = MapCore.radarSemBorda(comMoldura), b = MapCore.radarSemBorda(limpa);
      const alfa = (cv, x, y) => cv.getContext('2d').getImageData(x, y, 1, 1).data[3];
      return { copia: a !== comMoldura, moldura: alfa(a, 127, 5), miolo: alfa(a, 63, 63), mesmaImagem: b === limpa, miudaIntacta: MapCore.radarSemBorda(miuda) === miuda, de_novo: MapCore.radarSemBorda(comMoldura) === a };
    }""")
    assert r == {"copia": True, "moldura": 0, "miolo": 255, "mesmaImagem": True, "miudaIntacta": True, "de_novo": True}, r
    ctx.close()


def test_o_mapa_de_baixo_da_nuke_nao_ganha_linha_clara_na_borda_com_a_suavizacao_alta(navegador, paginas):
    """REGRESSÃO da Fase M: a moldura de 1 px da arte do Nuke aparecia como uma linha clara na última coluna do mapa."""
    import io
    from PIL import Image
    ctx, pg = _abre_replay(navegador, paginas, NUKE, rnd=9, frac=0.40, andar=1)
    box = pg.locator("#map").bounding_box()
    img = Image.open(io.BytesIO(pg.screenshot())).convert("RGB")
    x1, y0, y1 = int(round(box["x"] + box["width"])), int(box["y"]) + 5, int(box["y"] + box["height"]) - 5
    soma = lambda x: sum(sum(img.getpixel((x, y))) for y in range(y0, y1)) / (y1 - y0)
    assert soma(x1) - soma(x1 - 3) < 6, (soma(x1), soma(x1 - 3))      # antes da correção: +42
    ctx.close()
