"""
Prancheta tática: o modelo do arquivo de tática, as operações e a mescla.

O QUE É UMA TÁTICA AQUI
-----------------------
Um mapa vazio com peças (os cinco de cada lado), granadas com ORIGEM e DESTINO e
passos numerados. Tudo em coordenada de JOGO, pelo mesmo motivo das anotações
(`metrics/annotations.py`): o tamanho da tela muda, o ponto do mapa não.

A granada pode carregar um ARREMESSO REAL da biblioteca (`scripts/build_lineups.py`):
posição, ângulo e o comando de console que o reproduz. É a parte que mais importa
-- uma smoke desenhada à mão diz ONDE ela cai; a que vem de um arremesso real
diz também COMO chegar lá.

A DECISÃO QUE SUSTENTA TUDO: A TÁTICA É UM LOG DE OPERAÇÕES
-----------------------------------------------------------
O arquivo não guarda "o estado da prancheta". Guarda a LISTA de operações que o
produziu (criar peça, mover peça no passo 2, criar granada...), e o estado é
DERIVADO aplicando as operações em ordem. Isso é o que deixa o formato pronto
para mais de um usuário sem precisar de servidor hoje:

- cada operação tem **id estável** (uuid) -- a mesma operação chegando por dois
  caminhos é a mesma, não duas;
- cada operação tem **autor**;
- cada operação tem um **número de ordem** (`seq`), de um contador que só sobe e
  que, ao receber operações de outro, pula para acima do maior visto (relógio de
  Lamport). A ordem de aplicação é (seq, autor, id) -- total e igual em qualquer
  máquina;
- mesclar duas cópias editadas em paralelo é a UNIÃO dos logs por id. As duas
  pontas aplicam o mesmo conjunto na mesma ordem e chegam ao mesmo estado. Não
  existe "a versão de quem salvou por último".

Conflito de verdade (os dois moveram a mesma peça no mesmo passo) é resolvido
pela ordem: vale a operação de maior (seq, autor, id). É determinístico, e as
duas operações continuam no log -- nada some em silêncio.

A persistência fica atrás de uma interface no lado da página (`Armazem` em
`dashboard/web/tactics.js`): hoje o navegador, amanhã um servidor, sem a
interface mudar. Este módulo é o espelho em Python do mesmo modelo -- valida um
arquivo exportado e é a referência dos testes de que o JS aplica igual.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Diretório das táticas gravadas em disco (exportadas da página). Trabalho
# humano, fora de data/processed/, pelo mesmo motivo das anotações.
TACTICS_DIR = PROJECT_ROOT / "data" / "taticas"

# Identificação do arquivo e versão do formato. Sobe quando o esquema muda de
# forma incompatível; o leitor recusa versão que não conhece em vez de adivinhar.
IDENTIFICADOR = "prancheta-cs2"
FORMATO = 1

LADOS = ("ct", "t")
TIPOS_DE_GRANADA = ("smoke", "flash", "he", "molotov", "decoy")

# Peças por lado ao criar uma tática. Cinco é o time; peça a mais ou a menos é
# operação explícita, não padrão.
PECAS_POR_LADO = 5

# Operações conhecidas e os campos obrigatórios de cada uma (além de id, seq,
# autor, em e tipo, que toda operação tem).
OPERACOES = {
    "renomeia": ("titulo",),
    "cria_passo": ("passo", "titulo"),
    "renomeia_passo": ("passo", "titulo"),
    "remove_passo": ("passo",),
    "cria_peca": ("peca", "lado", "rotulo", "passo", "x", "y"),
    "move_peca": ("peca", "passo", "x", "y"),
    "remove_peca": ("peca",),
    # `arma` é o tipo da GRANADA (smoke, flash...); `tipo` é sempre o da operação
    "cria_granada": ("granada", "arma", "passo", "origem", "destino"),
    "move_granada": ("granada", "origem", "destino"),
    "remove_granada": ("granada",),
}

CAMPOS_COMUNS = ("id", "seq", "autor", "em", "tipo")

_ID = re.compile(r"^[A-Za-z0-9_-]{6,64}$")


class TaticaInvalida(ValueError):
    """Arquivo de tática que não pode ser lido sem inventar dado."""


def chave_de_ordem(op: dict) -> tuple:
    """A ordem TOTAL de aplicação: igual em qualquer máquina, para qualquer
    conjunto de operações. Sem o autor e o id no desempate, duas operações com o
    mesmo seq (feitas em paralelo) sairiam em ordem de chegada, e cada ponta
    chegaria a um estado diferente."""
    return (int(op["seq"]), str(op["autor"]), str(op["id"]))


def aplica(operacoes: list[dict]) -> dict:
    """Estado da prancheta a partir do log.

    O estado é:
      titulo;
      passos: lista ordenada de {passo, titulo} -- o NÚMERO mostrado é a posição
        na lista (1, 2, 3...), então remover um passo renumera os seguintes;
      pecas: {peca: {lado, rotulo, posicoes: {passo: [x, y]}}};
      granadas: {granada: {arma, passo, origem, destino, arremesso}}.
    Operação sobre coisa que não existe (peça removida, passo apagado) é
    ignorada: numa mescla ela pode ter chegado depois da remoção, e aplicar
    pela metade seria pior.
    """
    estado = {"titulo": "", "passos": [], "pecas": {}, "granadas": {}}
    passos: dict[str, dict] = {}
    ordem_passos: list[str] = []
    for op in sorted(operacoes, key=chave_de_ordem):
        t = op["tipo"]
        if t == "renomeia":
            estado["titulo"] = op["titulo"]
        elif t == "cria_passo":
            if op["passo"] not in passos:
                passos[op["passo"]] = {"passo": op["passo"], "titulo": op["titulo"]}
                ordem_passos.append(op["passo"])
        elif t == "renomeia_passo":
            if op["passo"] in passos:
                passos[op["passo"]]["titulo"] = op["titulo"]
        elif t == "remove_passo":
            if op["passo"] in passos:
                del passos[op["passo"]]
                ordem_passos.remove(op["passo"])
        elif t == "cria_peca":
            if op["peca"] not in estado["pecas"] and op["passo"] in passos:
                estado["pecas"][op["peca"]] = {
                    "lado": op["lado"], "rotulo": op["rotulo"],
                    "posicoes": {op["passo"]: [float(op["x"]), float(op["y"])]},
                }
        elif t == "move_peca":
            p = estado["pecas"].get(op["peca"])
            if p is not None and op["passo"] in passos:
                p["posicoes"][op["passo"]] = [float(op["x"]), float(op["y"])]
        elif t == "remove_peca":
            estado["pecas"].pop(op["peca"], None)
        elif t == "cria_granada":
            if op["granada"] not in estado["granadas"] and op["passo"] in passos:
                estado["granadas"][op["granada"]] = {
                    "arma": op["arma"], "passo": op["passo"],
                    "origem": [float(v) for v in op["origem"]],
                    "destino": [float(v) for v in op["destino"]],
                    "arremesso": op.get("arremesso"),
                }
        elif t == "move_granada":
            g = estado["granadas"].get(op["granada"])
            if g is not None:
                g["origem"] = [float(v) for v in op["origem"]]
                g["destino"] = [float(v) for v in op["destino"]]
                # granada arrastada à mão deixou de ser o arremesso real: manter o
                # comando de console seria afirmar um lineup que não é mais aquele
                g["arremesso"] = None
        elif t == "remove_granada":
            estado["granadas"].pop(op["granada"], None)

    estado["passos"] = [passos[p] for p in ordem_passos]
    vivos = set(ordem_passos)
    # posições e granadas de passo removido saem do estado
    for p in estado["pecas"].values():
        p["posicoes"] = {k: v for k, v in p["posicoes"].items() if k in vivos}
    estado["granadas"] = {k: g for k, g in estado["granadas"].items() if g["passo"] in vivos}
    return estado


def posicao_no_passo(peca: dict, passos: list[dict], indice: int) -> list[float] | None:
    """Onde a peça está no passo de posição `indice` (0 = primeiro): a última
    posição definida até ele. Peça que ainda não entrou fica None."""
    pos = None
    for p in passos[: indice + 1]:
        pos = peca["posicoes"].get(p["passo"], pos)
    return pos


def mescla(a: dict, b: dict) -> dict:
    """Une duas cópias da MESMA tática editadas em paralelo.

    União dos logs por id; o contador fica no maior dos dois. As duas pontas
    chamando `mescla` uma com a outra chegam ao mesmo documento.
    """
    if a["id"] != b["id"]:
        raise TaticaInvalida("mesclar táticas diferentes não faz sentido: ids distintos")
    ops = {op["id"]: op for op in a["operacoes"]}
    for op in b["operacoes"]:
        ops.setdefault(op["id"], op)
    unidas = sorted(ops.values(), key=chave_de_ordem)
    # os metadados (mapa, quem criou, quando, calibração) não mudam depois da
    # criação -- tudo que muda é operação --, então tanto faz de qual cópia vêm
    return {**a, "operacoes": unidas, "contador": max(a["contador"], b["contador"])}


def valida(doc: dict, calibracoes: dict[str, str] | None = None) -> dict:
    """Confere um arquivo de tática e devolve o estado aplicado.

    `calibracoes` (mapa -> impressão da calibração do radar) é opcional: com
    ela, uma tática feita sobre um radar calibrado de outro jeito é recusada --
    cairia alguns pixels fora sem ninguém perceber.
    """
    if doc.get("formato") != IDENTIFICADOR:
        raise TaticaInvalida("não é um arquivo de tática da prancheta")
    if doc.get("versao") != FORMATO:
        raise TaticaInvalida(f"versão {doc.get('versao')} do formato; este código lê a {FORMATO}")
    for campo in ("id", "mapa", "criada_por", "criada_em", "contador", "operacoes", "calibracao"):
        if campo not in doc:
            raise TaticaInvalida(f"falta o campo '{campo}'")
    if not _ID.match(str(doc["id"])):
        raise TaticaInvalida("id da tática fora do formato")
    if calibracoes is not None and calibracoes.get(doc["mapa"]) != doc["calibracao"]:
        raise TaticaInvalida("a tática foi feita sobre outra calibração do radar deste mapa")

    vistos = set()
    maior = 0
    for op in doc["operacoes"]:
        for campo in CAMPOS_COMUNS:
            if campo not in op:
                raise TaticaInvalida(f"operação sem '{campo}'")
        if op["tipo"] not in OPERACOES:
            raise TaticaInvalida(f"operação desconhecida: {op['tipo']}")
        for campo in OPERACOES[op["tipo"]]:
            if campo not in op:
                raise TaticaInvalida(f"'{op['tipo']}' sem '{campo}'")
        if op["id"] in vistos:
            raise TaticaInvalida(f"operação repetida: {op['id']}")
        vistos.add(op["id"])
        if not isinstance(op["seq"], int) or op["seq"] < 1:
            raise TaticaInvalida("número de ordem inválido")
        maior = max(maior, op["seq"])
        if op["tipo"] == "cria_peca" and op["lado"] not in LADOS:
            raise TaticaInvalida(f"lado desconhecido: {op['lado']}")
        if op["tipo"] == "cria_granada":
            _valida_granada(op)
    if doc["contador"] < maior:
        raise TaticaInvalida("o contador está abaixo do maior número de ordem do log")
    return aplica(doc["operacoes"])


def _valida_granada(op: dict) -> None:
    if op["arma"] not in TIPOS_DE_GRANADA:
        raise TaticaInvalida(f"granada desconhecida: {op['arma']}")
    if len(op["origem"]) < 2 or len(op["destino"]) < 2:
        raise TaticaInvalida("granada sem origem ou destino completos")
    arr = op.get("arremesso")
    if arr is not None:
        # o arremesso real é o que carrega o comando de console: sem os campos
        # que o reproduzem, ele não é um arremesso real, é um desenho
        for campo in ("id", "comando", "origem", "destino", "pitch", "yaw"):
            if campo not in arr:
                raise TaticaInvalida(f"arremesso real sem '{campo}'")


def carrega(caminho: Path, calibracoes: dict[str, str] | None = None) -> tuple[dict, dict]:
    doc = json.loads(Path(caminho).read_text(encoding="utf-8"))
    return doc, valida(doc, calibracoes)
