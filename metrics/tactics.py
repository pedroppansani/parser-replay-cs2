"""
Prancheta tática: o modelo do arquivo de tática, as operações e a mescla.

O QUE É UMA TÁTICA AQUI
-----------------------
Um mapa vazio com peças (os cinco de cada lado), granadas com ORIGEM e DESTINO,
desenho livre e passos numerados. Tudo em coordenada de JOGO, pelo mesmo motivo
das anotações (`metrics/annotations.py`): o tamanho da tela muda, o ponto do
mapa não.

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

DESFAZER É UMA OPERAÇÃO, NÃO UMA REMOÇÃO (formato 2)
----------------------------------------------------
`anula` e `reativa` miram uma operação do MESMO autor. Antes de aplicar, vale a
última delas sobre cada alvo, na ordem (seq, autor, id): se for `anula`, o alvo
é ignorado. Nada sai do log, então a mescla por união continua convergindo; e um
mecanismo só serve para toda operação -- anular um `remove_peca` devolve a peça
com todo o histórico, anular um `move_granada` devolve o arremesso real.

A persistência fica atrás de uma interface no lado da página (`Armazem` em
`dashboard/web/tactics.js`): hoje o navegador, amanhã um servidor, sem a
interface mudar. Este módulo é o espelho em Python do mesmo modelo -- valida um
arquivo exportado e é a referência dos testes de que o JS aplica igual.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

from metrics.annotations import ESPESSURAS, problemas_do_traco

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RADARS_DIR = PROJECT_ROOT / "assets" / "radars"

# Diretório das táticas gravadas em disco (exportadas da página). Trabalho
# humano, fora de data/processed/, pelo mesmo motivo das anotações.
TACTICS_DIR = PROJECT_ROOT / "data" / "taticas"

# Identificação do arquivo e versão do formato. Sobe quando o esquema muda de
# forma incompatível. O leitor aceita as versões que sabe migrar e recusa as
# outras em vez de adivinhar.
IDENTIFICADOR = "prancheta-cs2"
FORMATO = 2
# A versão 1 é migrada EM MEMÓRIA: nenhuma operação muda, só valem os padrões
# dos campos novos. Exportar grava sempre a versão atual.
VERSOES_ACEITAS = (1, 2)

LADOS = ("ct", "t")
TIPOS_DE_GRANADA = ("smoke", "flash", "he", "molotov", "decoy")

# Peças por lado no banco. Cinco é o time; peça a mais ou a menos é operação
# explícita, não padrão.
PECAS_POR_LADO = 5

# --- Padrões do formato 2 -- CONVENÇÃO DE INTERFACE, não dado de jogo --------
# Duração de um passo na reprodução, em segundos.
DURACAO_PADRAO_S = 2.0
# Por quantos passos uma granada fica no mapa (None = até o fim). A smoke dura o
# bastante para atravessar a jogada; flash, HE, molotov e decoy são momentos.
VIDA_PADRAO_GRANADA = {"smoke": None, "molotov": 1, "flash": 1, "he": 1, "decoy": 1}
# Um traço vale para o passo em que foi feito.
VIDA_PADRAO_TRACO = 1
# Casas decimais da direção PADRÃO (peça apontando para o centro do radar). É
# convenção de tela, e arredondar faz Python e JS darem o mesmo número mesmo
# quando o último bit do atan2 difere entre as duas bibliotecas.
CASAS_DIRECAO_PADRAO = 1

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
    # formato 2
    "gira_peca": ("peca", "passo", "yaw"),
    "tira_peca": ("peca", "passo"),
    "cria_traco": ("traco", "passo", "ferramenta", "cor", "espessura", "pontos"),
    "remove_traco": ("traco",),
    "define_duracao": ("passo", "segundos"),
    "define_vida": ("alvo", "dura_passos"),
    "anula": ("alvo",),
    "reativa": ("alvo",),
}
# Campos OPCIONAIS do formato 2 (ausente = padrão). Só documentação e conferência.
OPCIONAIS = {
    "cria_peca": ("nivel", "yaw"),
    "move_peca": ("nivel",),
    # origem_desconhecida: granada vinda de um instante do replay cujo efeito
    # não se liga a arremesso nenhum -- só o efeito é conhecido
    "cria_granada": ("nivel", "dura_passos", "arremesso", "origem_desconhecida"),
    "move_granada": ("nivel",),
    "cria_traco": ("nivel", "dura_passos", "texto"),
}
DESFAZER = ("anula", "reativa")

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


def _ordem(op: dict) -> list:
    """A chave de ordem em forma de JSON: é ela que diz a ordem de criação."""
    return [int(op["seq"]), str(op["autor"]), str(op["id"])]


def anuladas(operacoes: list[dict]) -> set[str]:
    """Ids das operações que estão desfeitas agora.

    Para cada alvo, vale a ÚLTIMA anula/reativa sobre ele, na ordem do log.
    Anula/reativa inválida (sobre operação de outro autor, sobre outra
    anula/reativa ou sobre id que não está no log) não vale -- `problemas`
    aponta cada uma.
    """
    por_id = {op["id"]: op for op in operacoes}
    ultima: dict[str, str] = {}
    for op in sorted(operacoes, key=chave_de_ordem):
        if op["tipo"] not in DESFAZER:
            continue
        alvo = por_id.get(op.get("alvo"))
        if alvo is None or alvo["tipo"] in DESFAZER or alvo["autor"] != op["autor"]:
            continue
        ultima[alvo["id"]] = op["tipo"]
    return {k for k, v in ultima.items() if v == "anula"}


def aplica(operacoes: list[dict]) -> dict:
    """Estado da prancheta a partir do log (formato 1 ou 2, a mesma função).

    O estado é:
      titulo;
      passos: lista ordenada de {passo, titulo, duracao_s} -- o NÚMERO mostrado é
        a posição na lista (1, 2, 3...), então remover um passo renumera os
        seguintes;
      pecas: {peca: {lado, rotulo, criada_em_ordem,
                     posicoes: {passo: [x, y] | None},   None = tirada naquele passo
                     niveis: {passo: nivel},             andar de cada posição definida
                     direcoes: {passo: yaw}}};           só o que foi definido
      granadas: {granada: {arma, passo, origem, destino, nivel, arremesso,
                           dura_passos, criada_em_ordem}};
      tracos: {traco: {passo, ferramenta, cor, espessura, pontos, texto, nivel,
                       dura_passos, criada_em_ordem}}.
    `criada_em_ordem` é o (seq, autor, id) da operação que criou o elemento.

    Operação sobre coisa que não existe (peça removida, passo apagado) é
    ignorada: numa mescla ela pode ter chegado depois da remoção, e aplicar
    pela metade seria pior. Operação anulada também (ver `anuladas`).
    """
    fora = anuladas(operacoes)
    estado: dict = {"titulo": "", "passos": [], "pecas": {}, "granadas": {}, "tracos": {}}
    passos: dict[str, dict] = {}
    ordem_passos: list[str] = []
    for op in sorted(operacoes, key=chave_de_ordem):
        if op["id"] in fora:
            continue
        t = op["tipo"]
        if t == "renomeia":
            estado["titulo"] = op["titulo"]
        elif t == "cria_passo":
            if op["passo"] not in passos:
                passos[op["passo"]] = {"passo": op["passo"], "titulo": op["titulo"],
                                       "duracao_s": DURACAO_PADRAO_S}
                ordem_passos.append(op["passo"])
        elif t == "renomeia_passo":
            if op["passo"] in passos:
                passos[op["passo"]]["titulo"] = op["titulo"]
        elif t == "define_duracao":
            if op["passo"] in passos:
                passos[op["passo"]]["duracao_s"] = float(op["segundos"])
        elif t == "remove_passo":
            if op["passo"] in passos:
                del passos[op["passo"]]
                ordem_passos.remove(op["passo"])
        elif t == "cria_peca":
            if op["peca"] not in estado["pecas"] and op["passo"] in passos:
                p = {"lado": op["lado"], "rotulo": op["rotulo"], "criada_em_ordem": _ordem(op),
                     "posicoes": {op["passo"]: [float(op["x"]), float(op["y"])]},
                     "niveis": {op["passo"]: int(op.get("nivel", 0))},
                     "direcoes": {}}
                if op.get("yaw") is not None:
                    p["direcoes"][op["passo"]] = float(op["yaw"])
                estado["pecas"][op["peca"]] = p
        elif t == "move_peca":
            p = estado["pecas"].get(op["peca"])
            if p is not None and op["passo"] in passos:
                p["posicoes"][op["passo"]] = [float(op["x"]), float(op["y"])]
                p["niveis"][op["passo"]] = int(op.get("nivel", 0))
        elif t == "gira_peca":
            p = estado["pecas"].get(op["peca"])
            if p is not None and op["passo"] in passos:
                p["direcoes"][op["passo"]] = float(op["yaw"])
        elif t == "tira_peca":
            p = estado["pecas"].get(op["peca"])
            if p is not None and op["passo"] in passos:
                p["posicoes"][op["passo"]] = None
                p["niveis"].pop(op["passo"], None)
        elif t == "remove_peca":
            estado["pecas"].pop(op["peca"], None)
        elif t == "cria_granada":
            if op["granada"] not in estado["granadas"] and op["passo"] in passos:
                estado["granadas"][op["granada"]] = {
                    "arma": op["arma"], "passo": op["passo"],
                    "origem": [float(v) for v in op["origem"]],
                    "destino": [float(v) for v in op["destino"]],
                    "nivel": int(op.get("nivel", 0)),
                    "arremesso": op.get("arremesso"),
                    "dura_passos": op["dura_passos"] if "dura_passos" in op
                    else VIDA_PADRAO_GRANADA[op["arma"]],
                    "criada_em_ordem": _ordem(op),
                }
                # o campo só existe quando é verdade: ausente = origem conhecida
                if op.get("origem_desconhecida") is True:
                    estado["granadas"][op["granada"]]["origem_desconhecida"] = True
        elif t == "move_granada":
            g = estado["granadas"].get(op["granada"])
            if g is not None:
                g["origem"] = [float(v) for v in op["origem"]]
                g["destino"] = [float(v) for v in op["destino"]]
                g["nivel"] = int(op.get("nivel", 0))
                # granada arrastada à mão deixou de ser o arremesso real: manter o
                # comando de console seria afirmar um lineup que não é mais aquele
                g["arremesso"] = None
                # e a origem passou a ser a que a pessoa desenhou
                g.pop("origem_desconhecida", None)
        elif t == "remove_granada":
            estado["granadas"].pop(op["granada"], None)
        elif t == "cria_traco":
            if op["traco"] not in estado["tracos"] and op["passo"] in passos:
                estado["tracos"][op["traco"]] = {
                    "passo": op["passo"], "ferramenta": op["ferramenta"], "cor": op["cor"],
                    "espessura": op["espessura"],
                    "pontos": [[float(a), float(b)] for a, b in op["pontos"]],
                    "texto": op.get("texto"),
                    "nivel": int(op.get("nivel", 0)),
                    "dura_passos": op["dura_passos"] if "dura_passos" in op else VIDA_PADRAO_TRACO,
                    "criada_em_ordem": _ordem(op),
                }
        elif t == "remove_traco":
            estado["tracos"].pop(op["traco"], None)
        elif t == "define_vida":
            alvo = estado["granadas"].get(op["alvo"]) or estado["tracos"].get(op["alvo"])
            if alvo is not None:
                alvo["dura_passos"] = op["dura_passos"]

    estado["passos"] = [passos[p] for p in ordem_passos]
    vivos = set(ordem_passos)
    # o que pertencia a passo removido sai do estado
    for p in estado["pecas"].values():
        for campo in ("posicoes", "niveis", "direcoes"):
            p[campo] = {k: v for k, v in p[campo].items() if k in vivos}
    estado["granadas"] = {k: g for k, g in estado["granadas"].items() if g["passo"] in vivos}
    estado["tracos"] = {k: t for k, t in estado["tracos"].items() if t["passo"] in vivos}
    return estado


def posicao_no_passo(peca: dict, passos: list[dict], indice: int) -> list[float] | None:
    """Onde a peça está no passo de posição `indice` (0 = primeiro): a última
    posição definida até ele. Peça que ainda não entrou, ou que foi tirada e não
    voltou, fica None."""
    pos = None
    for p in passos[: indice + 1]:
        pos = peca["posicoes"].get(p["passo"], pos)
    return pos


def centro_do_radar(radar: dict) -> list[float]:
    """Centro da imagem do radar em unidade de jogo: para onde a peça sem
    direção definida aponta."""
    s = float(radar["scale_px_per_unit"])
    return [float(radar["width"]) / 2 / s + float(radar["origin_x"]),
            float(radar["origin_y"]) - float(radar["height"]) / 2 / s]


def direcao_padrao(x: float, y: float, centro: list[float]) -> float:
    """Da peça para o centro do radar, em graus na convenção do CS2 (0° = +X,
    anti-horário), em [0, 360). Convenção de interface: calculada, nunca gravada
    no log."""
    ang = math.degrees(math.atan2(centro[1] - y, centro[0] - x)) % 360.0
    # arredonda "meio para cima", a mesma conta do Math.round do JS -- o round()
    # do Python arredonda meio para o par, e os dois divergiriam nos empates
    k = 10 ** CASAS_DIRECAO_PADRAO
    return (math.floor(ang * k + 0.5) / k) % 360.0


def _visivel(indice_nascimento: int, dura: int | None, i: int) -> bool:
    return indice_nascimento <= i and (dura is None or i < indice_nascimento + dura)


def quadro_do_passo(estado: dict, i: int, centro: list[float]) -> dict:
    """O que está visível no passo de índice `i`, já resolvidos herança,
    ausência, direção padrão e vida útil. É o que o editor e a reprodução
    desenham.

    pecas: só as que estão no mapa naquele passo, com x, y, nivel, yaw e
      `direcao_padrao` (True quando o yaw é o calculado, não um definido);
    granadas e tracos: os vivos naquele passo, com `nasceu_neste_passo` -- a
      linha do arremesso só aparece no passo de criação; depois, só o efeito.
    """
    passos = estado["passos"]
    indice = {p["passo"]: k for k, p in enumerate(passos)}
    pecas = {}
    for pid, p in estado["pecas"].items():
        pos, nivel, yaw = None, 0, None
        for q in passos[: i + 1]:
            k = q["passo"]
            if k in p["posicoes"]:
                pos = p["posicoes"][k]
                nivel = p["niveis"].get(k, 0)
            if k in p["direcoes"]:
                yaw = p["direcoes"][k]
        if pos is None:
            continue
        padrao = yaw is None
        pecas[pid] = {"lado": p["lado"], "rotulo": p["rotulo"], "x": pos[0], "y": pos[1],
                      "nivel": nivel,
                      "yaw": direcao_padrao(pos[0], pos[1], centro) if padrao else yaw,
                      "direcao_padrao": padrao}
    granadas = {gid: {**g, "nasceu_neste_passo": indice[g["passo"]] == i}
                for gid, g in estado["granadas"].items()
                if _visivel(indice[g["passo"]], g["dura_passos"], i)}
    tracos = {tid: {**t, "nasceu_neste_passo": indice[t["passo"]] == i}
              for tid, t in estado["tracos"].items()
              if _visivel(indice[t["passo"]], t["dura_passos"], i)}
    return {"indice": i, "passo": passos[i]["passo"], "titulo": passos[i]["titulo"],
            "duracao_s": passos[i]["duracao_s"], "pecas": pecas, "granadas": granadas, "tracos": tracos}


def ordem_de_criacao(estado: dict) -> list[dict]:
    """Granadas e traços na ordem em que foram criados: [{tipo, id, passo}].

    A ordem é o (seq, autor, id) da operação de criação. Não há contador
    próprio: o log já tem a ordem total, e um segundo contador divergiria na
    primeira mescla."""
    itens = [("granada", k, g) for k, g in estado["granadas"].items()] + \
            [("traco", k, t) for k, t in estado["tracos"].items()]
    itens.sort(key=lambda x: tuple(x[2]["criada_em_ordem"]))
    return [{"tipo": tipo, "id": k, "passo": e["passo"]} for tipo, k, e in itens]


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


def migra(doc: dict) -> dict:
    """Formato 1 -> atual, em memória: nenhuma operação muda, só a versão. Os
    campos novos saem com os padrões na aplicação."""
    if doc.get("versao") not in VERSOES_ACEITAS:
        raise TaticaInvalida(f"versão {doc.get('versao')} do formato; este código lê {VERSOES_ACEITAS}")
    return {**doc, "versao": FORMATO}


def andares_do_mapa(mapa: str) -> int:
    """Quantos andares o radar do mapa tem (Nuke, Vertigo e Train: 2)."""
    caminho = RADARS_DIR / f"{mapa}.json"
    if not caminho.exists():
        return 1
    secoes = json.loads(caminho.read_text(encoding="utf-8")).get("vertical_sections")
    return max(1, len(secoes or {}))


def _eh_inteiro(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _eh_numero(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def problemas(doc: dict, calibracoes: dict[str, str] | None = None) -> list[str]:
    """TODOS os problemas do arquivo de uma vez (lista vazia = está bom), como
    `metrics/annotations.valida`: quem confere um arquivo quer a lista inteira,
    não uma descoberta por execução.

    Arquivo que não é de tática, ou de versão que este código não sabe ler, para
    no primeiro item: o resto não teria como ser interpretado.
    """
    if doc.get("formato") != IDENTIFICADOR:
        return ["não é um arquivo de tática da prancheta"]
    if doc.get("versao") not in VERSOES_ACEITAS:
        return [f"versão {doc.get('versao')} do formato; este código lê as versões "
                f"{', '.join(str(v) for v in VERSOES_ACEITAS)}"]
    erros = []
    for campo in ("id", "mapa", "criada_por", "criada_em", "contador", "operacoes", "calibracao"):
        if campo not in doc:
            erros.append(f"falta o campo '{campo}'")
    if "id" in doc and not _ID.match(str(doc["id"])):
        erros.append("id da tática fora do formato")
    if calibracoes is not None and "mapa" in doc and calibracoes.get(doc["mapa"]) != doc.get("calibracao"):
        erros.append("a tática foi feita sobre outra calibração do radar deste mapa: precisa ser reprojetada")
    if doc.get("origem") is not None:
        erros += problemas_da_origem(doc["origem"])
    ops = doc.get("operacoes")
    if not isinstance(ops, list):
        return erros
    andares = andares_do_mapa(doc["mapa"]) if "mapa" in doc else 1

    completas = [op for op in ops if isinstance(op, dict) and all(c in op for c in CAMPOS_COMUNS)]
    por_id = {op["id"]: op for op in completas}
    vistos: set = set()
    maior = 0
    for n, op in enumerate(ops):
        onde = f"operação {n}"
        faltam = [c for c in CAMPOS_COMUNS if not (isinstance(op, dict) and c in op)]
        if faltam:
            erros.append(f"{onde} sem '{faltam[0]}'")
            continue
        onde = f"operação {n} ({op['tipo']})"
        if op["tipo"] not in OPERACOES:
            erros.append(f"operação desconhecida: {op['tipo']}")
            continue
        sem = [c for c in OPERACOES[op["tipo"]] if c not in op]
        for c in sem:
            erros.append(f"'{op['tipo']}' sem '{c}'")
        if op["id"] in vistos:
            erros.append(f"operação repetida: {op['id']}")
        vistos.add(op["id"])
        if not _eh_inteiro(op["seq"]) or op["seq"] < 1:
            erros.append(f"{onde}: número de ordem inválido")
        else:
            maior = max(maior, op["seq"])
        if sem:
            continue
        erros += _problemas_da_operacao(op, onde, andares, por_id)
    if _eh_inteiro(doc.get("contador")) and doc["contador"] < maior:
        erros.append("o contador está abaixo do maior número de ordem do log")
    return erros


def problemas_da_origem(origem) -> list[str]:
    """O metadado `origem` de uma tática criada a partir de um instante do
    replay: {partida, round, quadro, relogio, elenco, mortos?}. Como `mapa` e
    `calibracao`, é da criação e não muda -- não é operação. O banco da
    prancheta lê o elenco dele (nomes reais em vez de "TR 1..5")."""
    if not isinstance(origem, dict):
        return ["origem: não é um objeto"]
    erros = []
    if not isinstance(origem.get("partida"), str):
        erros.append("origem: partida ausente")
    if not _eh_inteiro(origem.get("round")) or origem["round"] < 1:
        erros.append("origem: round inválido")
    if not _eh_inteiro(origem.get("quadro")) or origem["quadro"] < 0:
        erros.append("origem: quadro inválido")
    if not isinstance(origem.get("relogio"), str):
        erros.append("origem: relógio ausente")
    elenco = origem.get("elenco")
    if not isinstance(elenco, list) or not elenco:
        return erros + ["origem: elenco ausente"]
    nomes = {}
    for j in elenco:
        if not isinstance(j, dict) or not isinstance(j.get("nome"), str) or not j["nome"] or j.get("lado") not in LADOS:
            erros.append(f"origem: jogador do elenco inválido: {j!r}")
            continue
        if j["nome"] in nomes:
            erros.append(f"origem: {j['nome']} repetido no elenco")
        nomes[j["nome"]] = j["lado"]
    for lado in LADOS:
        if sum(1 for v in nomes.values() if v == lado) > PECAS_POR_LADO:
            erros.append(f"origem: mais de {PECAS_POR_LADO} jogadores de {lado} no elenco")
    mortos = origem.get("mortos", [])
    if not isinstance(mortos, list):
        return erros + ["origem: mortos não é uma lista"]
    ordens = set()
    for m in mortos:
        if not isinstance(m, dict) or nomes.get(m.get("nome")) != m.get("lado"):
            erros.append(f"origem: morto fora do elenco: {m!r}")
            continue
        if not _eh_inteiro(m.get("ordem")) or m["ordem"] < 1 or m["ordem"] in ordens:
            erros.append(f"origem: ordem de morte inválida para {m['nome']}")
        else:
            ordens.add(m["ordem"])
    return erros


def _problemas_da_operacao(op: dict, onde: str, andares: int, por_id: dict) -> list[str]:
    erros = []
    t = op["tipo"]
    if t == "cria_peca" and op["lado"] not in LADOS:
        erros.append(f"{onde}: lado desconhecido: {op['lado']}")
    if t in ("cria_peca", "gira_peca") and op.get("yaw") is not None:
        if not _eh_numero(op["yaw"]) or not (0 <= op["yaw"] < 360):
            erros.append(f"{onde}: yaw {op['yaw']!r} fora de [0, 360)")
    if "nivel" in op:
        if not _eh_inteiro(op["nivel"]) or op["nivel"] < 0:
            erros.append(f"{onde}: nivel {op['nivel']!r} não é um andar")
        elif andares == 1 and op["nivel"] != 0:
            erros.append(f"{onde}: nivel {op['nivel']} num mapa de um andar só")
        elif op["nivel"] >= andares:
            erros.append(f"{onde}: nivel {op['nivel']} num mapa de {andares} andares")
    if "dura_passos" in op and op["dura_passos"] is not None:
        if not _eh_inteiro(op["dura_passos"]) or op["dura_passos"] < 1:
            erros.append(f"{onde}: dura_passos {op['dura_passos']!r} não é inteiro >= 1 nem null")
    if t == "define_duracao" and (not _eh_numero(op["segundos"]) or op["segundos"] <= 0):
        erros.append(f"{onde}: duração {op['segundos']!r} s não é positiva")
    if t == "cria_granada":
        erros += _problemas_da_granada(op, onde)
    if t == "cria_traco":
        erros += problemas_do_traco(op, onde)
        if op["espessura"] not in ESPESSURAS:
            erros.append(f"{onde}: espessura {op['espessura']!r} fora de {list(ESPESSURAS)}")
    if t in DESFAZER:
        alvo = por_id.get(op["alvo"])
        if alvo is None:
            erros.append(f"{onde}: mira a operação {op['alvo']}, que não está no log")
        elif alvo["tipo"] in DESFAZER:
            erros.append(f"{onde}: mira outra {alvo['tipo']} -- desfazer só mira operação de efeito")
        elif alvo["autor"] != op["autor"]:
            erros.append(f"{onde}: {op['autor']} mira operação de {alvo['autor']} -- "
                         "cada um só desfaz o que é seu")
    return erros


def _problemas_da_granada(op: dict, onde: str) -> list[str]:
    erros = []
    if op["arma"] not in TIPOS_DE_GRANADA:
        erros.append(f"{onde}: granada desconhecida: {op['arma']}")
    if len(op["origem"]) < 2 or len(op["destino"]) < 2:
        erros.append(f"{onde}: granada sem origem ou destino completos")
    arr = op.get("arremesso")
    if "origem_desconhecida" in op:
        if not isinstance(op["origem_desconhecida"], bool):
            erros.append(f"{onde}: origem_desconhecida não é verdadeiro/falso")
        elif op["origem_desconhecida"]:
            # sem origem, o único valor honesto é origem == destino: a linha some
            # e nada passa por arremesso de verdade
            if list(op["origem"][:2]) != list(op["destino"][:2]):
                erros.append(f"{onde}: origem desconhecida exige origem igual ao destino")
            if arr is not None:
                erros.append(f"{onde}: origem desconhecida não combina com arremesso real")
    if arr is not None:
        # o arremesso real é o que carrega o comando de console: sem os campos
        # que o reproduzem, ele não é um arremesso real, é um desenho
        for campo in ("id", "comando", "origem", "destino", "pitch", "yaw"):
            if campo not in arr:
                erros.append(f"{onde}: arremesso real sem '{campo}'")
    return erros


def valida(doc: dict, calibracoes: dict[str, str] | None = None) -> dict:
    """Confere um arquivo de tática e devolve o estado aplicado.

    Levanta `TaticaInvalida` com TODOS os itens de `problemas` na mensagem.
    `calibracoes` (mapa -> impressão da calibração do radar) é opcional: com
    ela, uma tática feita sobre um radar calibrado de outro jeito é recusada --
    cairia alguns pixels fora sem ninguém perceber.
    """
    erros = problemas(doc, calibracoes)
    if erros:
        raise TaticaInvalida("; ".join(erros))
    return aplica(doc["operacoes"])


def carrega(caminho: Path, calibracoes: dict[str, str] | None = None) -> tuple[dict, dict]:
    doc = json.loads(Path(caminho).read_text(encoding="utf-8"))
    return doc, valida(doc, calibracoes)
