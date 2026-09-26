"""
Testes de NAVEGADOR da direção do olhar no replay (etapa 1): a conversão
yaw -> tela, a interpolação angular, a ponta do matador apontando para a vítima
no dado real, os casos sem ponta e o botão.

Sem Playwright ou sem Chrome, são pulados com o motivo no relatório.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from scripts.build_web_page import build_html  # noqa: E402

PARTIDA = "match_02"

# Tolerância da ponta do matador contra a direção da vítima. O replay é
# amostrado a 4 Hz (um quadro a cada 16 ticks) e a mira pode girar dentro desse
# intervalo; no tick exato o erro mediano é 0,46° (tests/test_replay_direcao.py).
TOLERANCIA_KILL_GRAUS = 20.0
# Fração mínima das kills da partida dentro da tolerância. Não é 100% porque o
# quadro mais próximo pode cair até 8 ticks depois da kill, e há kill de flick.
MIN_FRACAO_KILLS = 0.85

# Registra cada chamada de desenhaJogador do último quadro desenhado.
REGISTRA = """
(() => {
  document.addEventListener("DOMContentLoaded", () => {
    const f = MapCore.desenhaJogador;
    window.__quadro = [];
    MapCore.desenhaJogador = function (c, x, y, o) {
      window.__quadro.push({ x: x, y: y, nome: o.nome, estado: o.estado, yaw: o.yaw });
      return f.apply(this, arguments);
    };
  });
})();
"""


@pytest.fixture(scope="module")
def pagina(tmp_path_factory):
    if not (Path("data/processed") / PARTIDA / "replay.json").exists():
        pytest.skip(f"{PARTIDA} sem replay exportado")
    html = tmp_path_factory.mktemp("direcao") / f"{PARTIDA}.html"
    html.write_text(build_html(PARTIDA), encoding="utf-8")
    return html


@pytest.fixture(scope="module")
def navegador():
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch(channel="chrome")
        except Exception:
            try:
                b = p.chromium.launch()
            except Exception as err:  # pragma: no cover - depende da máquina
                pytest.skip(f"sem Chrome para o Playwright: {err}")
        yield b
        b.close()


def abre(navegador, pagina, direcao=None):
    ctx = navegador.new_context(viewport={"width": 1400, "height": 1000})
    if direcao is not None:
        ctx.add_init_script(f"try {{ localStorage.setItem('replay:direcao', '{direcao}'); }} catch (e) {{}}")
    ctx.add_init_script(REGISTRA)
    pg = ctx.new_page()
    pg.goto(pagina.as_uri())
    pg.locator('[data-tab="replay"]').first.click()
    pg.wait_for_function("() => window.MapAnnotations && MapAnnotations._interno.S.reprojecoes > 0")
    return ctx, pg


def vai(pg, rodada, quadro, trocar_round=True):
    if trocar_round:
        pg.locator("#strip button", has_text=str(rodada)).first.click()
    pg.evaluate(f"""() => {{ window.__quadro = []; const s = document.getElementById('scrub');
        s.value = {quadro}; s.dispatchEvent(new Event('input')); }}""")
    return pg.evaluate("() => window.__quadro")


def test_angulo_de_tela_segue_a_convencao(navegador, pagina):
    """0° para a direita, 90° para CIMA na tela (o canvas cresce para baixo) e
    180° para a esquerda: θ = -yaw."""
    ctx, pg = abre(navegador, pagina)
    try:
        for yaw, esperado in ((0, (1, 0)), (90, (0, -1)), (180, (-1, 0)), (270, (0, 1))):
            dx, dy = pg.evaluate(f"() => {{ const t = MapCore.anguloDeTela({yaw}); return [Math.cos(t), Math.sin(t)]; }}")
            assert abs(dx - esperado[0]) < 1e-9 and abs(dy - esperado[1]) < 1e-9, (yaw, dx, dy)
    finally:
        ctx.close()


def test_interpolacao_angular_vai_pelo_caminho_mais_curto(navegador, pagina):
    ctx, pg = abre(navegador, pagina)
    try:
        assert pg.evaluate("() => MapCore.interpolaAngulo(359, 1, 0.5)") == 0
        amostras = pg.evaluate("() => Array.from({length: 101}, (_, i) => MapCore.interpolaAngulo(359, 1, i / 100))")
        # todo ponto do caminho fica a no máximo 1° de 0°, nunca perto de 180°
        assert all(min(v, 360 - v) <= 1 + 1e-9 for v in amostras), amostras
        assert all(0 <= v < 360 for v in amostras)
        assert pg.evaluate("() => MapCore.interpolaAngulo(350, 10, 0.5)") == 0
        assert pg.evaluate("() => MapCore.interpolaAngulo(10, 350, 0.25)") == 5
    finally:
        ctx.close()


def test_a_ponta_do_matador_aponta_para_a_vitima(navegador, pagina):
    """No quadro mais próximo de cada kill da partida, o yaw que foi para o
    desenho, convertido por anguloDeTela, aponta do matador para a vítima."""
    rep = json.loads((Path("data/processed") / PARTIDA / "replay.json").read_text(encoding="utf-8"))
    ctx, pg = abre(navegador, pagina)
    try:
        erros = []
        for r in rep["rounds"]:
            primeira = True
            for ev in (e for e in r["events"] if e["type"] == "kill"):
                quadro = min(r["frames"] - 1, round(ev["f"]))
                desenhados = {j["nome"]: j for j in vai(pg, r["round"], quadro, trocar_round=primeira)}
                primeira = False
                mat, vit = desenhados.get(ev["attacker"]), desenhados.get(ev["victim"])
                if not mat or not vit or mat["yaw"] is None or mat["estado"] != "vivo":
                    continue
                alvo = math.atan2(vit["y"] - mat["y"], vit["x"] - mat["x"])
                ponta = pg.evaluate(f"() => MapCore.anguloDeTela({mat['yaw']})")
                d = abs((math.degrees(ponta - alvo) + 180) % 360 - 180)
                erros.append(d)
        assert len(erros) > 50, f"só {len(erros)} kills conferidas"
        dentro = sum(e <= TOLERANCIA_KILL_GRAUS for e in erros) / len(erros)
        erros.sort()
        print(f"kills conferidas {len(erros)}; dentro de {TOLERANCIA_KILL_GRAUS}°: {dentro:.1%}; "
              f"mediana {erros[len(erros) // 2]:.1f}°; p90 {erros[int(len(erros) * 0.9)]:.1f}°")
        assert dentro >= MIN_FRACAO_KILLS, (
            f"{dentro:.0%} das {len(erros)} kills dentro de {TOLERANCIA_KILL_GRAUS}°; mediana {erros[len(erros) // 2]:.1f}°")
    finally:
        ctx.close()


def test_morto_e_outro_andar_nao_desenham_ponta(navegador, pagina):
    """Com yaw ou sem yaw, o morto e o jogador de outro andar saem iguais pixel
    a pixel. O vivo com yaw sai diferente -- é o controle de que o teste vê a
    ponta quando ela existe."""
    ctx, pg = abre(navegador, pagina)
    try:
        iguais = pg.evaluate("""() => {
          const pinta = (o) => {
            const c = document.createElement('canvas'); c.width = 80; c.height = 80;
            const g = c.getContext('2d');
            MapCore.desenhaJogador(g, 40, 40, Object.assign({ cor: '#2a78d6', hp: 100, nome: 'x', cego: false }, o));
            return c.toDataURL();
          };
          const r = {};
          for (const estado of ['morto', 'outro_andar', 'vivo']) {
            r[estado] = pinta({ estado: estado, yaw: 90 }) === pinta({ estado: estado, yaw: null });
          }
          return r;
        }""")
        assert iguais["morto"] and iguais["outro_andar"]
        assert not iguais["vivo"], "o vivo com yaw deveria ganhar a ponta"
    finally:
        ctx.close()


def test_o_botao_desliga_a_direcao_e_lembra(navegador, pagina):
    ctx, pg = abre(navegador, pagina)
    try:
        botao = pg.locator("#anot-direcao")
        assert botao.get_attribute("aria-pressed") == "true"       # ligado por padrão
        assert any(j["yaw"] is not None for j in vai(pg, 1, 10) if j["estado"] == "vivo")
        botao.click()
        assert botao.get_attribute("aria-pressed") == "false"
        assert all(j["yaw"] is None for j in vai(pg, 1, 10))
        assert pg.evaluate("() => localStorage.getItem('replay:direcao')") == "0"
        pg.reload()
        pg.locator('[data-tab="replay"]').first.click()
        pg.wait_for_function("() => MapAnnotations._interno.S.reprojecoes > 0")
        assert pg.locator("#anot-direcao").get_attribute("aria-pressed") == "false"
        assert all(j["yaw"] is None for j in vai(pg, 1, 10))
    finally:
        ctx.close()
