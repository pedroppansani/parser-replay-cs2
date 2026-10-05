"""Prancheta no tempo (fase 8): interação, funções, granadas, linha do tempo e reprodução."""
from __future__ import annotations

import math

import pytest

pytest.importorskip("playwright.sync_api")

from tests.test_tactics_browser import (abre, arrasta_do_banco, contexto, interno, navegador, no_mapa,  # noqa: E402,F401
                                        pagina)


def _ops(pg, tipo=None):
    ops = interno(pg, "S.doc.operacoes")
    return [o for o in ops if tipo is None or o["tipo"] == tipo]


def _pixel_da_peca(pg, pid):
    q = interno(pg, f"I.quadroNoTempo(S.e3, S.t, I.centro()).pecas['{pid}']")
    px = interno(pg, f"I.jogoParaPixel({q['x']}, {q['y']})")
    c = pg.locator("#pr-mapa").bounding_box()
    w = interno(pg, "I.radar().width")
    return c["x"] + px[0] * c["width"] / w, c["y"] + px[1] * c["height"] / w


def _com_peca(pg):
    # o caminho por clique está pronto e desligado (CAMINHO_POR_CLIQUE): liga aqui
    interno(pg, "(I.ligaCaminhoPorClique(true), 0)")
    arrasta_do_banco(pg, "ct", "1", 0.5, 0.5)
    pid = interno(pg, "Object.keys(S.estado.pecas)[0]")
    pg.keyboard.press("Escape"); pg.keyboard.press("Escape")
    return pid


def test_arrastar_grava_ponto_no_horario_do_cabecote_e_nao_entra_em_caminho(contexto, pagina):
    pg = abre(contexto, pagina)
    pid = _com_peca(pg)
    interno(pg, "(I.defineTempo(20), 0)")
    x, y = _pixel_da_peca(pg, pid)
    pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(x + 60, y - 40, steps=6); pg.mouse.up()
    (op,) = _ops(pg, "cria_caminho")
    assert op["peca"] == pid and len(op["pontos"]) == 1 and op["pontos"][0]["t"] == 20
    assert interno(pg, "I.estadoDaInteracao()") != "tracando_caminho"
    # no horário de um marco, arrastar é o move_peca de sempre
    interno(pg, "(I.defineTempo(0), 0)")
    x, y = _pixel_da_peca(pg, pid)
    pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(x - 30, y + 30, steps=6); pg.mouse.up()
    assert len(_ops(pg, "move_peca")) == 1 and len(_ops(pg, "cria_caminho")) == 1


def test_clicar_na_peca_traca_caminho_e_enter_emite_um_cria_caminho(contexto, pagina):
    pg = abre(contexto, pagina)
    pid = _com_peca(pg)
    pg.mouse.click(*_pixel_da_peca(pg, pid))
    assert interno(pg, "I.estadoDaInteracao()") == "tracando_caminho"
    assert "Enter conclui" in pg.text_content("#pr-dica-estado")
    for fx, fy in ((0.55, 0.5), (0.6, 0.45), (0.6, 0.38)):
        pg.mouse.click(*no_mapa(pg, fx, fy))
    pg.keyboard.press("Enter")
    (op,) = _ops(pg, "cria_caminho")
    pts = op["pontos"]
    assert len(pts) == 3 and pts[0]["t"] < pts[1]["t"] < pts[2]["t"]
    # horários pela velocidade medida (rifle, correndo)
    v = interno(pg, "I.velocidade(null, 'correndo')")
    inicio = interno(pg, f"S.e3.pecas['{pid}'].pontos[0]")
    d = math.hypot(pts[0]["x"] - inicio["x"], pts[0]["y"] - inicio["y"])
    assert pts[0]["t"] == pytest.approx(d / v, abs=0.01)
    # a peça segue selecionada e o cabeçote foi para o fim do caminho
    assert interno(pg, "S.t") == pts[-1]["t"] and interno(pg, "S.sel.id") == pid
    # Ctrl+Z desfaz o caminho inteiro
    pg.keyboard.press("Control+z")
    assert interno(pg, f"S.e3.pecas['{pid}'].pontos.filter(p => p.caminho).length") == 0


def test_backspace_tira_o_ultimo_e_esc_cancela_o_trecho(contexto, pagina):
    pg = abre(contexto, pagina)
    pid = _com_peca(pg)
    pg.mouse.click(*_pixel_da_peca(pg, pid))
    pg.mouse.click(*no_mapa(pg, 0.55, 0.5)); pg.mouse.click(*no_mapa(pg, 0.6, 0.45))
    pg.keyboard.press("Backspace")
    assert interno(pg, "S.caminho.pontos.length") == 1
    assert interno(pg, f"!!S.estado.pecas['{pid}']")            # Backspace não apagou a peça
    pg.keyboard.press("Escape")
    assert interno(pg, "S.caminho") is None and _ops(pg, "cria_caminho") == []


def test_arrastar_no_modo_caminho_desenha_a_mao_e_simplifica(contexto, pagina):
    pg = abre(contexto, pagina)
    pid = _com_peca(pg)
    pg.mouse.click(*_pixel_da_peca(pg, pid))
    pg.mouse.move(*no_mapa(pg, 0.55, 0.55)); pg.mouse.down()
    for i in range(1, 30):
        pg.mouse.move(*no_mapa(pg, 0.55 + 0.004 * i, 0.55 + 0.0001 * (i % 2)))   # reta com tremor
    pg.mouse.up()
    n = interno(pg, "S.caminho.pontos.length")
    assert 1 <= n <= 3                              # Douglas-Peucker tirou o tremor
    pg.keyboard.press("Enter")
    assert len(_ops(pg, "cria_caminho")) == 1


def test_esperar_aqui_empurra_os_pontos_seguintes_numa_acao(contexto, pagina):
    pg = abre(contexto, pagina)
    pid = _com_peca(pg)
    pg.mouse.click(*_pixel_da_peca(pg, pid))
    for fx, fy in ((0.55, 0.5), (0.6, 0.45), (0.65, 0.4)):
        pg.mouse.click(*no_mapa(pg, fx, fy))
    pg.keyboard.press("Enter")
    antes = interno(pg, f"S.e3.pecas['{pid}'].pontos.filter(p => p.caminho).map(p => p.t)")
    primeiro = interno(pg, f"S.e3.pecas['{pid}'].pontos.filter(p => p.caminho)[0].id")
    pg.fill(f'[data-espera="{primeiro}"]', "3"); pg.press(f'[data-espera="{primeiro}"]', "Tab")
    depois = interno(pg, f"S.e3.pecas['{pid}'].pontos.filter(p => p.caminho).map(p => p.t)")
    assert depois[0] == antes[0] and depois[1:] == [round(t + 3, 2) for t in antes[1:]]
    pg.keyboard.press("Control+z")
    assert interno(pg, f"S.e3.pecas['{pid}'].pontos.filter(p => p.caminho).map(p => p.t)") == antes


def test_botao_direito_fora_do_marco_grava_yaw_no_horario(contexto, pagina):
    pg = abre(contexto, pagina)
    pid = _com_peca(pg)
    interno(pg, f"(S.sel = {{tipo: 'peca', id: '{pid}'}}, I.defineTempo(12), 0)")
    pg.mouse.click(*no_mapa(pg, 0.5, 0.2), button="right")
    (op,) = _ops(pg, "cria_caminho")
    assert op["pontos"][0]["t"] == 12 and op["pontos"][0]["yaw"] is not None
    assert _ops(pg, "gira_peca") == []


def test_desligado_o_clique_continua_movendo_no_horario_do_cabecote(contexto, pagina):
    pg = abre(contexto, pagina)
    arrasta_do_banco(pg, "ct", "1", 0.5, 0.5)
    pid = interno(pg, "S.sel.id")
    assert "tracando_caminho" not in interno(pg, "Object.keys(I.ESTADOS)")
    interno(pg, "(I.defineTempo(15), 0)")
    interno(pg, f"(S.sel = {{tipo: 'peca', id: '{pid}'}}, 0)")
    pg.mouse.click(*no_mapa(pg, 0.6, 0.55))
    (op,) = _ops(pg, "cria_caminho")
    assert op["pontos"][0]["t"] == 15 and interno(pg, "S.caminho") is None


def test_funcao_muda_o_rotulo_e_a_velocidade_padrao_do_caminho(contexto, pagina):
    pg = abre(contexto, pagina)
    pid = _com_peca(pg)
    pg.mouse.click(*_pixel_da_peca(pg, pid))               # seleciona (e entra em caminho)
    pg.select_option("#pr-funcao", "AWPer")
    (op,) = _ops(pg, "define_funcao")
    assert op["peca"] == pid and op["funcao"] == "AWPer"
    assert interno(pg, f"I.quadroNoTempo(S.e3, S.t, I.centro()).pecas['{pid}'].funcao") == "AWPer"
    # o banco mostra o mesmo campo, já com a função
    assert pg.locator(f'#pr-funcoes-banco select[data-peca="{pid}"]').input_value() == "AWPer"
    # a velocidade padrão do caminho passa a ser a da AWP
    pg.mouse.click(*no_mapa(pg, 0.6, 0.5))
    pt = interno(pg, "S.caminho.pontos[0]")
    ini = interno(pg, "S.caminho.inicio")
    v_awp = interno(pg, "I.velocidade('AWPer', 'correndo')")
    assert pt["t"] == pytest.approx(ini["t"] + math.hypot(pt["x"] - ini["x"], pt["y"] - ini["y"]) / v_awp, abs=0.01)
    assert v_awp < interno(pg, "I.velocidade(null, 'correndo')")


def _no_radar(pg, px, py):
    c = pg.locator("#pr-mapa").bounding_box()
    w = interno(pg, "I.radar().width")
    return c["x"] + px * c["width"] / w, c["y"] + py * c["height"] / w


def test_granada_real_no_horario_do_cabecote_poe_o_ponto_no_caminho_e_avisa_o_atraso(contexto, pagina):
    pg = abre(contexto, pagina)
    arrasta_do_banco(pg, "ct", "1", 0.15, 0.85)            # longe de onde se joga a smoke
    pid = interno(pg, "S.sel.id")
    interno(pg, f"(S.sel = {{tipo: 'peca', id: '{pid}'}}, I.defineTempo(10), 0)")
    pg.evaluate("() => document.activeElement && document.activeElement.blur()")
    pg.keyboard.press("1")
    assert interno(pg, "I.estadoDaInteracao()") == "granada_destino"
    r = interno(pg, "I.biblioteca().arremessos.filter(a => a.arma === 'smoke')[0]")
    px = interno(pg, f"I.jogoParaPixel({r['destino'][0]}, {r['destino'][1]})")
    pg.mouse.click(*_no_radar(pg, *px))
    # a lista abre; a primeira opção é manter a desenhada, a escolhida é o arremesso real
    itens = pg.locator(".pr-lista li")
    assert itens.count() >= 2
    itens.nth(1).click()
    reais = [g for g in interno(pg, "S.e3.granadas").values() if g["arremesso"]]
    assert len(reais) == 1 and reais[0]["t"] == 10 and reais[0]["jogador"] == pid
    real = reais[0]["arremesso"]
    pts = [p for p in interno(pg, f"S.e3.pecas['{pid}'].pontos") if not p["fora"] and abs(p["t"] - 10) < 1e-6]
    assert len(pts) == 1 and (pts[0]["x"], pts[0]["y"]) == (real["origem"][0], real["origem"][1])
    # ele não chega lá em 10 s: o aviso diz quanto atrasa, e adiar move granada e ponto
    assert "s depois do arremesso" in pg.text_content("#pr-atraso")
    novo = interno(pg, "S.atraso.t")
    pg.click("#pr-adiar")
    g = [g for g in interno(pg, "S.e3.granadas").values() if g["arremesso"]][0]
    assert g["t"] == novo and g["jogador"] == pid
    assert any(abs(p["t"] - novo) < 1e-6 and p["x"] == real["origem"][0] for p in interno(pg, f"S.e3.pecas['{pid}'].pontos"))
    # cada ação é UM Ctrl+Z: desfaz o adiar e depois a escolha do arremesso inteira
    pg.keyboard.press("Control+z")
    assert [g for g in interno(pg, "S.e3.granadas").values() if g["arremesso"]][0]["t"] == 10
    pg.keyboard.press("Control+z")
    assert not [g for g in interno(pg, "S.e3.granadas").values() if g["arremesso"]]
    assert not [p for p in interno(pg, f"S.e3.pecas['{pid}'].pontos") if abs(p["t"] - 10) < 1e-6]


def test_botoes_de_granada_ficam_no_painel_da_direita_e_nao_na_barra(contexto, pagina):
    pg = abre(contexto, pagina)
    assert pg.locator("#pr-barra [data-arma]").count() == 0
    assert pg.locator("aside [data-arma]").count() == 4
    assert pg.locator("aside #pr-granadas canvas.pr-glifo").count() == 4
    assert pg.locator('aside [data-ferramenta="buscar"]').count() == 1
    # cor e espessura só com um pincel ativo
    assert not pg.locator("#pr-contexto-desenho").is_visible()
    pg.click('#pr-barra [data-ferramenta="caneta"]')
    assert pg.locator("#pr-contexto-desenho").is_visible()


# --- 8.5: linha do tempo, relógio grande, reprodução no relógio e roteiro ---------

def _tatica_no_tempo(pg):
    """Uma peça com caminho (0 s, 5 s, 12 s), uma smoke jogada por ela aos 8 s e
    o plant aos 30 s: a tática tem horário, então toca no relógio."""
    import json

    def op(seq, tipo, **d):
        return {"id": f"q{seq:04d}", "seq": seq, "autor": "pedro", "em": "2026-10-04T00:00:00Z", "tipo": tipo, **d}
    ops = [
        op(1, "renomeia", titulo="No tempo"),
        op(2, "cria_passo", passo="p1", titulo="saída"),
        op(3, "cria_peca", peca="a", lado="t", rotulo="1", passo="p1", x=-1200.0, y=300.0, yaw=0.0),
        op(4, "cria_caminho", peca="a", pontos=[{"t": 5.0, "x": -1000.0, "y": 100.0},
                                                {"t": 12.0, "x": -800.0, "y": -100.0}]),
        op(5, "cria_granada", granada="s", arma="smoke", passo="p1", t=8.0, jogador="a",
           origem=[-914.0, 14.0], destino=[-500.0, -400.0]),
        op(6, "planta_bomba", t=30.0, x=-400.0, y=-500.0),
    ]
    doc = interno(pg, "S.doc")
    doc.update({"id": "notempo00001", "versao": 3, "contador": 6, "operacoes": ops})
    assert interno(pg, f"I.importaTexto({json.dumps(json.dumps(doc))})") is True
    return doc


def _x_do_horario(pg, t):
    """x da tela do horário t (a régua vai até o fim da bomba: plant + 40 s)."""
    pg.locator("#pr-linha").scroll_into_view_if_needed()
    tr = pg.locator("#pr-faixas .pr-trilho").first.bounding_box()
    return tr["x"] + tr["width"] * t / interno(pg, "I.M3().SEGUNDOS_DA_BOMBA + S.e3.bomba.t")


def _arrasta_marca(pg, seletor, t):
    pg.locator("#pr-linha").scroll_into_view_if_needed()
    m = pg.locator(seletor).bounding_box()
    y = m["y"] + m["height"] / 2
    pg.mouse.move(m["x"] + m["width"] / 2, y); pg.mouse.down()
    pg.mouse.move(_x_do_horario(pg, t), y, steps=8); pg.mouse.up()


def test_linha_do_tempo_tem_uma_faixa_por_jogador_com_pontos_e_granadas(contexto, pagina):
    pg = abre(contexto, pagina)
    _tatica_no_tempo(pg)
    assert pg.locator("#pr-linha").is_visible()
    assert pg.locator('#pr-faixas [data-faixa="a"]').count() == 1
    assert pg.locator('[data-faixa="a"] .pr-marca[data-ponto]').count() == 3
    assert pg.locator('[data-faixa="a"] .pr-marca[data-granada="s"]').count() == 1
    assert pg.locator('.pr-marco[data-marco="p1"]').count() == 1
    m = pg.locator('[data-faixa="a"] .pr-marca[data-ponto]').nth(2).bounding_box()
    assert abs(m["x"] + m["width"] / 2 - _x_do_horario(pg, 12)) < 2
    assert not pg._erros


def test_arrastar_uma_marca_muda_o_horario_numa_acao(contexto, pagina):
    pg = abre(contexto, pagina)
    _tatica_no_tempo(pg)
    ponto = interno(pg, "S.e3.pecas.a.pontos[2].id")
    n = len(_ops(pg))
    _arrasta_marca(pg, f'.pr-marca[data-ponto="{ponto}"]', 20)
    novas = _ops(pg)[n:]
    assert [o["tipo"] for o in novas] == ["move_ponto"] and novas[0]["peca"] == "a"
    assert abs(novas[0]["t"] - 20) < 0.2
    assert interno(pg, "S.e3.pecas.a.pontos[2].x") == -800.0          # só o horário mudou
    interno(pg, "I.desfaz()")
    assert interno(pg, "S.e3.pecas.a.pontos[2].t") == 12.0
    # a granada: um lote, um desfazer
    _arrasta_marca(pg, '.pr-marca[data-granada="s"]', 10)
    assert abs(interno(pg, "S.e3.granadas.s.t") - 10) < 0.2
    interno(pg, "I.desfaz()")
    assert interno(pg, "S.e3.granadas.s.t") == 8.0


def test_clicar_na_regua_leva_o_cabecote_e_o_relogio_grande_mostra_o_round(contexto, pagina):
    pg = abre(contexto, pagina)
    _tatica_no_tempo(pg)
    x = _x_do_horario(pg, 15)
    r = pg.locator("#pr-regua").bounding_box()
    pg.mouse.click(x, r["y"] + r["height"] / 2)
    assert abs(interno(pg, "S.t") - 15) < 0.2
    interno(pg, "(I.defineTempo(15), 0)")
    assert pg.text_content("#pr-relogio-grande") == "1:40"
    interno(pg, "(I.defineTempo(40), 0)")                               # 10 s depois do plant
    assert pg.text_content("#pr-relogio-grande") == "0:30"
    assert "bomba" in pg.get_attribute("#pr-relogio-grande", "class")


def test_reproducao_no_relogio_voa_a_granada_e_vira_o_arremessador(contexto, pagina):
    pg = abre(contexto, pagina)
    _tatica_no_tempo(pg)
    assert interno(pg, "I.tocaNoRelogio()") is True
    pg.click("#pr-reproduzir")
    assert interno(pg, "S.reproducao.modo") == "relogio"
    pg.click("#pr-toca")                                               # pausa
    voo = interno(pg, "S.e3.granadas.s.voo_s")
    t = 8 + voo / 2
    interno(pg, f"(I.reproduzAte({t}), 0)")
    cena = interno(pg, "S.reproducao.cena")
    g = cena["granadas"]["s"]
    assert g["voando"] is True and g["efeito"] == 0 and abs(g["linha"] - 0.5) < 1e-9
    rumo = math.degrees(math.atan2(-400.0 - 14.0, -500.0 + 914.0)) % 360
    assert abs(cena["pecas"]["a"]["yaw"] - rumo) < 1e-9
    # depois de cair: efeito aberto e a peça volta à direção do caminho
    interno(pg, f"(I.reproduzAte({8 + voo + 1}), 0)")
    cena = interno(pg, "S.reproducao.cena")
    assert cena["granadas"]["s"]["efeito"] == 1 and "jogando" not in cena["pecas"]["a"]
    # pureza: arrastar a barra até t dá o mesmo quadro que a função em t
    barra = pg.locator("#pr-tempo")
    barra.evaluate("(b, v) => { b.value = v; b.dispatchEvent(new Event('input')); }", str(round(t * 1000)))
    assert interno(pg, "S.reproducao.cena") == interno(pg, f"I.cenaNoRelogio({round(t * 1000) / 1000})")
    # velocidades de 0,25x a 4x
    vistas = set()
    for _ in range(5):
        pg.click("#pr-velocidade")
        vistas.add(interno(pg, "S.reproducao.velocidade"))
    assert vistas == {0.25, 0.5, 1, 2, 4}
    # a seta vai ao próximo evento do roteiro
    interno(pg, "(I.reproduzAte(6), 0)")
    interno(pg, "(document.activeElement && document.activeElement.blur && document.activeElement.blur(), 0)")
    pg.keyboard.press("ArrowRight")
    assert interno(pg, "S.reproducao.t") == 8.0
    assert not pg._erros


def test_tatica_so_com_passos_continua_tocando_por_passos(contexto, pagina):
    from tests.test_tactics_browser import _tatica_de_reproducao
    pg = abre(contexto, pagina)
    _tatica_de_reproducao(pg)
    assert interno(pg, "I.tocaNoRelogio()") is False
    pg.click("#pr-reproduzir")
    assert interno(pg, "S.reproducao.modo") == "passos"
    assert not pg.locator("#pr-linha").is_visible()


def test_roteiro_acende_o_evento_e_a_nota_vira_operacao(contexto, pagina):
    pg = abre(contexto, pagina)
    _tatica_no_tempo(pg)
    ev = interno(pg, "I.eventosDe(S.e3)")
    ts = [e["t"] for e in ev]
    primeiro = interno(pg, "S.e3.pecas.a.pontos[0].id")
    assert ts == sorted(ts) and [e["alvo"] for e in ev][:2] == ["marco:p1", "a/" + primeiro]
    interno(pg, "(I.defineTempo(9), 0)")
    aceso = pg.locator("#pr-roteiro .pr-evento.aceso")
    assert aceso.count() == 1 and aceso.get_attribute("data-evento") == "s"
    nota = pg.locator('#pr-roteiro [data-nota="s"]')
    nota.fill("cobre a janela"); nota.press("Enter"); nota.evaluate("n => n.blur()")
    (op,) = _ops(pg, "nota_de_evento")
    assert op["alvo"] == "s" and op["texto"] == "cobre a janela"
    # na reprodução, o balão no mapa diz o evento aceso, com a nota
    pg.click("#pr-reproduzir"); pg.click("#pr-toca")
    interno(pg, "(I.reproduzAte(9), 0)")
    balao = interno(pg, "S.ultimoBalao")
    assert balao["alvo"] == "s" and balao["texto"].endswith("cobre a janela")
    assert pg.locator("#pr-roteiro .pr-evento.aceso").get_attribute("data-evento") == "s"


def test_nome_do_lugar_e_o_mesmo_no_python_e_no_navegador(contexto, pagina):
    import json
    from pathlib import Path

    from metrics.lugares import lugar
    raiz = Path(__file__).resolve().parents[1]
    pg = abre(contexto, pagina)
    mapa = interno(pg, "I.radar().map")
    caminho = raiz / "data" / "lugares" / f"{mapa}.json"
    if not caminho.exists():
        pytest.skip("tabela de lugares não gerada (scripts/build_lugares.py)")
    tabela = json.loads(caminho.read_text(encoding="utf-8"))
    radar = json.loads((raiz / "assets" / "radars" / f"{mapa}.json").read_text(encoding="utf-8"))
    pontos = [(x, y) for x in range(-3000, 1500, 137) for y in range(-2500, 1700, 151)]
    js = interno(pg, f"{json.dumps(pontos)}.map(p => I.lugarDe(p[0], p[1], 0))")
    py = [lugar(tabela, (x - radar["origin_x"]) * radar["scale_px_per_unit"],
                (radar["origin_y"] - y) * radar["scale_px_per_unit"], 0) for x, y in pontos]
    assert js == py and sum(1 for v in py if v) > 50
    # e o roteiro usa o nome: o destino da smoke tem nome na tabela
    _tatica_no_tempo(pg)
    ev = {e["alvo"]: e for e in interno(pg, "I.eventosDe(S.e3)")}
    nome = interno(pg, "I.lugarDe(-500, -400, 0)")
    assert nome and ev["s"]["texto"].endswith("em " + nome)
