"""Operações malformadas e boas, para os testes da validação ÚNICA de operação (B-1 da revisão de segurança).

Usada pelo teste de espelho JS<->Python (tests/test_tactics_browser.py), pelo do Python (tests/test_tactics.py)
e pelos do grupo ao vivo (tests/test_grupos_validacao.py). Toda malformada passa pela forma mínima que o
SERVIDOR confere (id, tipo, autor e seq) ou quase: é o que um atacante com a API direta consegue inserir (os
testes do grupo injetam a linha sem passar pela forma mínima, como a API faria com id, tipo, autor e seq de
verdade). As de forma mínima quebrada estão em `SEM_A_FORMA_MINIMA`.
"""
from __future__ import annotations

PASSO = "passo0001"
EM = "2026-10-14T00:00:00Z"


def op(tipo: str, seq: int = 50, **campos) -> dict:
    return {"id": f"m{seq:04d}{tipo[:6]}", "seq": seq, "autor": "atacante", "em": EM, "tipo": tipo, **campos}


def _boas() -> list[dict]:
    """Uma operação boa de cada tipo (o contraste: a validação não recusa o que o app emite)."""
    real = {"id": "match_02:6:901", "comando": "setpos 1 2 3; setang 4 5 0", "origem": [1, 2, 3],
            "destino": [9, 9, 9], "pitch": 4.0, "yaw": 5.0}
    return [
        op("renomeia", 51, titulo="Mirage A"),
        op("cria_passo", 52, passo="p2", titulo=""),
        op("renomeia_passo", 53, passo=PASSO, titulo="a"),
        op("define_duracao", 54, passo=PASSO, segundos=3.5),
        op("remove_passo", 80, passo="p2"),
        op("cria_peca", 55, peca="pc1", lado="ct", rotulo="1", passo=PASSO, x=-500.0, y=-600.0),
        op("cria_peca", 56, peca="pc2", lado="t", rotulo="2", passo=PASSO, x=1.0, y=2.0, yaw=270.0, nivel=0),
        op("move_peca", 57, peca="pc1", passo=PASSO, x=3.0, y=4.0),
        op("gira_peca", 58, peca="pc1", passo=PASSO, yaw=33.0),
        op("tira_peca", 59, peca="pc2", passo=PASSO),
        op("remove_peca", 60, peca="pc2"),
        op("cria_granada", 61, granada="g1", arma="smoke", passo=PASSO, origem=[0.0, 0.0], destino=[5.0, 5.0]),
        op("cria_granada", 62, granada="g2", arma="flash", passo=PASSO, origem=[1.0, 1.0], destino=[2.0, 2.0],
           arremesso=real, t=1.5, jogador="pc1", voo_s=1.0, efeito_s=0.0),
        op("move_granada", 63, granada="g1", origem=[0.0, 0.0], destino=[6.0, 6.0]),
        op("remove_granada", 64, granada="g1"),
        op("cria_traco", 65, traco="t1", passo=PASSO, ferramenta="seta", cor="#eb6834", espessura=4,
           pontos=[[0, 0], [50, 50]]),
        op("cria_traco", 66, traco="t2", passo=PASSO, ferramenta="texto", cor="#2a78d6", espessura=2,
           pontos=[[1, 1]], texto="olá"),
        op("remove_traco", 67, traco="t1"),
        op("define_vida", 68, alvo="g2", dura_passos=None),
        op("cria_caminho", 69, peca="pc1", pontos=[{"t": 1.0, "x": 1.0, "y": 2.0, "nivel": 0, "yaw": 10.0}]),
        op("move_ponto", 70, peca="pc1", ponto="op69:0", t=1.0, x=1.0, y=2.0),
        op("remove_ponto", 71, peca="pc1", ponto="op69:0"),
        op("define_funcao", 72, peca="pc1", funcao="AWPer"),
        op("define_funcao", 73, peca="pc1", funcao=None),
        op("planta_bomba", 74, t=30.0, x=1.0, y=2.0),
        op("nota_de_evento", 75, alvo="granada:g2", texto="smoke do A"),
        op("desenha_granada", 76, traco="d1", passo=PASSO, arma="smoke", x=1.0, y=2.0, area=True),
        op("define_area_desenho", 77, traco="d1", area=False),
        op("anula", 78, alvo="m0051renomei"),
        op("reativa", 79, alvo="m0051renomei"),
    ]


BOAS = _boas()


def _malformadas() -> list[tuple[str, dict]]:
    """(rótulo, operação). Cada uma é uma operação que o servidor aceita e que o cliente tem de recusar."""
    base_granada = dict(granada="gx", arma="smoke", passo=PASSO, origem=[0.0, 0.0], destino=[1.0, 1.0])
    base_traco = dict(traco="tx", passo=PASSO, ferramenta="seta", cor="#eb6834", espessura=4, pontos=[[0, 0], [1, 1]])
    base_peca = dict(peca="px", lado="t", rotulo="1", passo=PASSO, x=1.0, y=2.0)
    return [
        # o exemplo do relatório: origem que não é lista derrubava o `op.origem.map`
        ("granada com origem texto", op("cria_granada", **{**base_granada, "origem": "x"})),
        ("granada com origem número", op("cria_granada", **{**base_granada, "origem": 7})),
        ("granada com destino de um número só", op("cria_granada", **{**base_granada, "destino": [0.0]})),
        ("granada com destino de texto dentro", op("cria_granada", **{**base_granada, "destino": ["a", "b"]})),
        ("granada com origem objeto", op("cria_granada", **{**base_granada, "origem": {"0": 1, "1": 2, "length": 2}})),
        ("granada com arma desconhecida", op("cria_granada", **{**base_granada, "arma": "tnt"})),
        ("granada com arremesso texto", op("cria_granada", **{**base_granada, "arremesso": "real"})),
        ("granada com arremesso lista", op("cria_granada", **{**base_granada, "arremesso": [1, 2]})),
        ("granada com jogador número", op("cria_granada", **{**base_granada, "jogador": 5})),
        ("granada com horário texto", op("cria_granada", **{**base_granada, "t": "1"})),
        ("granada sem origem", op("cria_granada", **{k: v for k, v in base_granada.items() if k != "origem"})),
        ("move_granada com destino texto", op("move_granada", granada="gx", origem=[0.0, 0.0], destino="y")),
        ("traço com pontos número", op("cria_traco", **{**base_traco, "pontos": 5})),
        ("traço com pontos texto", op("cria_traco", **{**base_traco, "pontos": "abc"})),
        ("traço com ponto texto", op("cria_traco", **{**base_traco, "pontos": ["ab", "cd"]})),
        ("traço sem pontos", op("cria_traco", **{**base_traco, "pontos": []})),
        ("traço com cor número", op("cria_traco", **{**base_traco, "cor": 16711680})),
        ("traço com ferramenta desconhecida", op("cria_traco", **{**base_traco, "ferramenta": "laser"})),
        ("traço com texto objeto", op("cria_traco", **{**base_traco, "texto": {"a": 1}})),
        ("peça com x texto", op("cria_peca", **{**base_peca, "x": "1"})),
        ("peça com y nulo", op("cria_peca", **{**base_peca, "y": None})),
        ("peça sem x", op("cria_peca", **{k: v for k, v in base_peca.items() if k != "x"})),
        ("peça com lado desconhecido", op("cria_peca", **{**base_peca, "lado": "zz"})),
        ("peça com rótulo número", op("cria_peca", **{**base_peca, "rotulo": 1})),
        ("peça com id de peça __proto__", op("cria_peca", **{**base_peca, "peca": "__proto__"})),
        ("peça com id de peça constructor", op("cria_peca", **{**base_peca, "peca": "constructor"})),
        ("peça com id de peça vazio", op("cria_peca", **{**base_peca, "peca": ""})),
        ("peça com id de peça lista", op("cria_peca", **{**base_peca, "peca": ["a"]})),
        ("peça com passo objeto", op("cria_peca", **{**base_peca, "passo": {"a": 1}})),
        ("peça com yaw fora de 0 a 360", op("cria_peca", **{**base_peca, "yaw": 400})),
        ("peça com nivel texto", op("cria_peca", **{**base_peca, "nivel": "0"})),
        ("peça com nivel negativo", op("cria_peca", **{**base_peca, "nivel": -1})),
        ("peça com nivel acima dos andares", op("cria_peca", **{**base_peca, "nivel": 5})),
        ("move_peca com x texto", op("move_peca", peca="pc1", passo=PASSO, x="a", y=1.0)),
        ("gira_peca com yaw texto", op("gira_peca", peca="pc1", passo=PASSO, yaw="norte")),
        ("renomeia com título número", op("renomeia", titulo=12)),
        ("renomeia com título nulo", op("renomeia", titulo=None)),
        ("renomeia sem título", op("renomeia")),
        ("passo com título lista", op("cria_passo", passo="p9", titulo=["a"])),
        ("define_duracao com segundos texto", op("define_duracao", passo=PASSO, segundos="3")),
        ("define_duracao negativa", op("define_duracao", passo=PASSO, segundos=-1)),
        ("define_vida com dura_passos texto", op("define_vida", alvo="g2", dura_passos="1")),
        ("define_funcao com função número", op("define_funcao", peca="pc1", funcao=3)),
        ("caminho com pontos número", op("cria_caminho", peca="pc1", pontos=9)),
        ("caminho com pontos vazios", op("cria_caminho", peca="pc1", pontos=[])),
        ("caminho com ponto texto", op("cria_caminho", peca="pc1", pontos=["a"])),
        ("caminho com t texto", op("cria_caminho", peca="pc1", pontos=[{"t": "1", "x": 1.0, "y": 2.0}])),
        ("caminho com modo desconhecido", op("cria_caminho", peca="pc1", pontos=[{"t": 1.0, "x": 1.0, "y": 2.0, "modo": "voando"}])),
        ("caminho com yaw texto", op("cria_caminho", peca="pc1", pontos=[{"t": 1.0, "x": 1.0, "y": 2.0, "yaw": "a"}])),
        ("caminho com nivel texto", op("cria_caminho", peca="pc1", pontos=[{"t": 1.0, "x": 1.0, "y": 2.0, "nivel": "a"}])),
        ("move_ponto com t texto", op("move_ponto", peca="pc1", ponto="a:0", t="x", y=1.0, x=2.0)),
        ("move_ponto com ponto número", op("move_ponto", peca="pc1", ponto=0, t=1.0, x=1.0, y=2.0)),
        ("planta_bomba com x texto", op("planta_bomba", t=1.0, x="a", y=2.0)),
        ("nota com texto número", op("nota_de_evento", alvo="g", texto=5)),
        ("granada desenhada com x texto", op("desenha_granada", traco="d", passo=PASSO, arma="smoke", x="1", y=2.0)),
        ("granada desenhada com arma desconhecida", op("desenha_granada", traco="d", passo=PASSO, arma="decoy", x=1.0, y=2.0)),
        ("área com texto", op("define_area_desenho", traco="d", area="sim")),
        ("anula com alvo número", op("anula", alvo=3)),
        ("anula com alvo objeto", op("anula", alvo={"a": 1})),
        # tipo e campos comuns
        ("tipo desconhecido", op("explode")),
        ("tipo constructor", op("constructor")),
        ("tipo __proto__", op("__proto__")),
        ("tipo número", {**op("renomeia", titulo="a"), "tipo": 7}),
        ("tipo lista", {**op("renomeia", titulo="a"), "tipo": ["renomeia"]}),
        ("autor número", {**op("renomeia", titulo="a"), "autor": 7}),
        ("autor objeto", {**op("renomeia", titulo="a"), "autor": {"a": 1}}),
        ("autor vazio", {**op("renomeia", titulo="a"), "autor": ""}),
        ("autor de 65 caracteres", {**op("renomeia", titulo="a"), "autor": "a" * 65}),
        ("em número", {**op("renomeia", titulo="a"), "em": 5}),
        ("em ausente", {k: v for k, v in op("renomeia", titulo="a").items() if k != "em"}),
        ("id __proto__", {**op("renomeia", titulo="a"), "id": "__proto__"}),
        ("id com espaço", {**op("renomeia", titulo="a"), "id": "a b"}),
        ("id de 65 caracteres", {**op("renomeia", titulo="a"), "id": "a" * 65}),
        ("id número", {**op("renomeia", titulo="a"), "id": 5}),
        ("seq gigante", {**op("renomeia", titulo="a"), "seq": 10 ** 300}),
        ("seq acima de 15 dígitos", {**op("renomeia", titulo="a"), "seq": 10 ** 15}),
        ("seq texto", {**op("renomeia", titulo="a"), "seq": "50"}),
        ("seq fracionário", {**op("renomeia", titulo="a"), "seq": 50.5}),
        ("seq zero", {**op("renomeia", titulo="a"), "seq": 0}),
        ("seq negativo", {**op("renomeia", titulo="a"), "seq": -3}),
        ("seq verdadeiro", {**op("renomeia", titulo="a"), "seq": True}),
    ]


MALFORMADAS = _malformadas()

# Não passam nem pela forma mínima do servidor (o gatilho as recusa); só a validação de arquivo/carga as vê.
SEM_A_FORMA_MINIMA: list[tuple[str, object]] = [
    ("operação nula", None),
    ("operação número", 5),
    ("operação texto", "renomeia"),
    ("operação lista", [1, 2]),
    ("operação vazia", {}),
]
