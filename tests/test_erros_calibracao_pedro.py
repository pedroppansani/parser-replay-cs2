"""As respostas do Pedro à seção 7 do material de calibração (2026-10-16, decisão 46).

- "Flash no time": a flash que cegou o time menos de `MIN_CEGUEIRA_FLASH_ALIADO` (2,0 s) não é ocorrência,
  mesmo com a soma do lado acima do limiar; a soma continua contando todas as flashes.
"""
from __future__ import annotations

from metrics import erros as E
from tests.test_erros import cegueira, partida


def test_min_cegueira_flash_aliado_e_2_segundos():
    assert E.MIN_CEGUEIRA_FLASH_ALIADO == 2.0
    assert not E.cegou_o_bastante(1.99) and E.cegou_o_bastante(2.0) and not E.cegou_o_bastante(None)


def test_flash_de_1_99_s_nao_e_ocorrencia_mesmo_com_a_soma_acima_do_limiar():
    # 14 flashes de 2,0 s (28 s) e uma de 1,99 s: a soma do lado (29,99 s) passa do limiar de 27 s
    cegos = [cegueira(100 * i, 2, 3, 2.0) for i in range(1, 15)] + [cegueira(5000, 2, 4, 1.99)]
    oc = E.flash_no_time(partida([], {}, cegos=cegos))
    curta = [o for o in oc if o["tick"] == 5000]
    assert len(curta) == 1 and curta[0]["filtro"] == E.FILTRO_CEGUEIRA_CURTA
    # a de exatamente 2,0 s é ocorrência
    assert all(o["filtro"] is None for o in oc if o["tick"] != 5000) and len(oc) == 15
    # a soma conta todas, inclusive a curta (ela mede o padrão)
    assert all(o["valor_soma_lado"] == 29.99 for o in oc)


def test_a_soma_com_a_flash_curta_ainda_tira_as_outras_do_limiar():
    # sem a de 1,5 s a soma (26 s) ficaria abaixo de 27 s; com ela (27,5 s) as de 2,0 s contam
    cegos = [cegueira(100 * i, 2, 3, 2.0) for i in range(1, 14)] + [cegueira(5000, 2, 4, 1.5)]
    oc = E.flash_no_time(partida([], {}, cegos=cegos))
    assert [o["filtro"] for o in oc] == [None] * 13 + [E.FILTRO_CEGUEIRA_CURTA]


def test_flash_curta_acima_do_limiar_de_uma_flash_nao_existe_e_a_longa_continua():
    # a regra de uma flash só (acima de 4,8 s) não muda: com a soma abaixo do limiar, a longa conta
    oc = E.flash_no_time(partida([], {}, cegos=[cegueira(100, 2, 3, 5.3), cegueira(200, 2, 4, 1.0)]))
    assert [o["filtro"] for o in oc] == [None, E.FILTRO_ABAIXO_DO_LIMIAR]


# --- Os tipos validados aparecem no Perfil publicado ----------------------------------------------------------

import json  # noqa: E402
from pathlib import Path  # noqa: E402

import polars as pl  # noqa: E402
import pytest  # noqa: E402

from scripts.calibracao import erros_do_jogador as G  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent


def test_os_validados_sao_tipos_conhecidos_sem_flash_nem_bait():
    assert E.TIPOS_DE_ERRO_VALIDADOS <= set(E.TIPOS)
    assert E.FLASH_NO_TIME not in E.TIPOS_DE_ERRO_VALIDADOS and E.POSSIVEL_BAIT not in E.TIPOS_DE_ERRO_VALIDADOS
    assert len(E.TIPOS_DE_ERRO_VALIDADOS) == 5


def test_os_tipos_validados_aparecem_no_perfil_publicado():
    from leitura import perfil_erros as PE
    from scripts.build_web_page import build_html, cabecalho_da_partida
    base = RAIZ / "data" / "processed" / "match_32"
    if not (base / E.ARQUIVO).exists() or not (base / "web_payload.json").exists():
        pytest.skip("sem as ocorrências gravadas da partida")
    payload = json.loads((base / "web_payload.json").read_text(encoding="utf-8"))
    b = PE.bloco_da_partida(base, payload, cabecalho_da_partida("match_32", base))
    assert b["estado"] == "normal"
    assert [t["id"] for t in b["tipos"]] == [t for t in E.TIPOS if t in E.TIPOS_DE_ERRO_VALIDADOS]
    melhorar = [m for j in b["jogadores"] for m in j["melhorar"]]
    assert melhorar and all(m["tipo"] in E.TIPOS_DE_ERRO_VALIDADOS and not m["em_validacao"] for m in melhorar)
    assert all(len(j["melhorar"]) <= E.MAX_PONTOS_A_MELHORAR for j in b["jogadores"])
    assert all(len(m["chips"]) >= E.MIN_OCORRENCIAS_PARA_PONTO for m in melhorar)
    html = build_html("match_32")
    assert any(E.TITULOS[m["tipo"]] in html for m in melhorar)
    assert E.TITULOS[E.FLASH_NO_TIME] not in html and E.TITULOS[E.POSSIVEL_BAIT] not in html


# --- As respostas gravadas não voltam como pergunta ----------------------------------------------------------

def _oc(n: int, filtrados: tuple = ()) -> pl.DataFrame:
    linhas = []
    for i in range(n):
        x = {c: None for c in E.ESQUEMA}
        x.update(tipo=E.FLASH_NO_TIME, match_id=f"match_{i:02d}", round_num=1, tick=100 + i, steamid=i + 1,
                 aliado_steamid=99, name=f"j{i}", aliado="a", vivos_time=5, vivos_adversario=5, valor=3.0,
                 valor_soma_lado=30.0, segundos=10.0, nivel=E.EXPLICITO, motivo="m",
                 filtro=E.FILTRO_CEGUEIRA_CURTA if i in filtrados else None)
        linhas.append(x)
    return pl.DataFrame(linhas, schema=E.ESQUEMA, orient="row")


def _reg(i: int) -> dict:
    return {"tipo": E.FLASH_NO_TIME, "partida": f"match_{i:02d}", "round": 1, "tick": 100 + i, "jogador": f"j{i}",
            "steamid": str(i + 1), "aliado_steamid": "99", "semente": G.SEMENTE_DOS_EXEMPLOS, "data_do_sorteio": "d"}


def test_exemplo_respondido_nunca_e_sorteado_como_substituto():
    oc = _oc(30, filtrados=(3, 6))                          # os exemplos #4 e #7 deixaram de ser ocorrência
    fix = {"exemplos": {E.FLASH_NO_TIME: [_reg(i) for i in range(10)]}}
    # respondidos: os 10 fixados e mais 15 casos que já foram respondidos numa rodada antiga
    respondidos = {G._chave_do_registro(_reg(i)) for i in range(25)}
    novo = G.escolhe_exemplos(oc, fix, "2026-10-19", validaveis=(E.FLASH_NO_TIME,), respondidos=respondidos)
    ex = novo[E.FLASH_NO_TIME]
    assert len(ex) == 10
    subst = [r for r in ex if r.get("substituido_em")]
    assert len(subst) == 2 and all(G._chave_do_registro(r) not in respondidos for r in subst)
    assert {r["substitui"]["partida"] for r in subst} == {"match_03", "match_06"}
    assert all(r["motivo_da_substituicao"] == E.FILTRO_CEGUEIRA_CURTA for r in subst)


def test_o_material_mostra_a_resposta_ja_dada_e_so_pergunta_o_novo(tmp_path):
    oc = _oc(12)
    ex = {E.FLASH_NO_TIME: [_reg(i) for i in range(10)]}
    arq = tmp_path / "respostas.json"
    exemplos = [{**{k: _reg(i)[k] for k in ("partida", "round", "tick", "jogador", "steamid", "aliado_steamid")},
                 "resposta": "sim" if i else "não"} for i in range(9)]            # o #10 não foi respondido
    arq.write_text(json.dumps({"rodadas": [{"data": "2026-10-16", "tipos": {E.FLASH_NO_TIME: {
        "frase_serve": True, "confirmados": 8, "de": 9, "resultado": "r", "exemplos": exemplos}}}]}), encoding="utf-8")
    resp = G.le_respostas(arq)
    linhas = "\n".join(G.secao_exemplos(oc, ex, validaveis=(E.FLASH_NO_TIME,), respostas=resp))
    tabela = [x for x in linhas.splitlines() if x.startswith("| ") and x[2].isdigit()]
    assert len(tabela) == 10
    assert tabela[0].endswith("| **não** (respondido em 2026-10-16) |")
    assert all(x.endswith("| **sim** (respondido em 2026-10-16) |") for x in tabela[1:9])
    assert tabela[9].endswith(f"| {G.PERGUNTA} |")
    assert "**A frase serve?** **sim** (respondido em 2026-10-16)" in linhas
    assert "Falta responder: #10" in linhas


def test_as_respostas_de_2026_10_16_estao_gravadas_por_exemplo():
    resp = G.le_respostas()
    tipos = resp["tipos"]
    assert {t: (v["confirmados"], v["de"]) for t, v in tipos.items()} == {
        E.NAO_TROCOU: (8, 10), E.POSSIVEL_BAIT: (8, 9), E.PERDEU_A_TROCA: (9, 10), E.MORREU_SOZINHO: (8, 10),
        E.PRIMEIRA_MORTE_SEM_TROCA: (10, 10), E.FLASH_NO_TIME: (7, 10), E.DANO_DE_UTILIDADE_NO_TIME: (10, 10)}
    assert all(v["data"] == "2026-10-16" and "não assistindo aos replays" in v["como"] for v in tipos.values())
    assert len(resp["exemplos"]) == 69
    # um tipo validado tem pelo menos 8 de 10 confirmados
    for t in E.TIPOS_DE_ERRO_VALIDADOS:
        assert tipos[t]["confirmados"] >= 8 and tipos[t]["de"] == 10
    # nenhum exemplo fixado hoje é um respondido que deixou de ser ocorrência: os respondidos que estão nos
    # fixados continuam lá; os outros (os 3 de flash reprovados) só aparecem como "substitui"
    fix = G.le_fixados()["exemplos"]
    fixados = {G._chave_do_registro(r) for t, rs in fix.items() for r in rs}
    fora = [k for k in resp["exemplos"] if k[0] != E.POSSIVEL_BAIT and k not in fixados]
    assert len(fora) <= 3 and all(k[0] == E.FLASH_NO_TIME for k in fora)
