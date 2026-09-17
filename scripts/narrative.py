"""
Frases dos cards de destaque, geradas a partir do dado da partida.

Por que existe: as frases dos três cards da aba Insights foram escritas à mão
para a match_01 e ficaram fixas no template. Toda partida renderizava o texto da
primeira -- "Empate em 9-9... _AmadeuS mata os quatro no retake", com os nicks e
o placar de outra partida. É o tipo de erro que não quebra nada e mente em todas
as páginas.

Regra inegociável deste módulo: **campo que não existe naquela partida some da
frase**. Nada de "None", nada de "0 clutches", nada de frase armada com buraco.
Frase curta e verdadeira vale mais que frase completa e inventada. Toda função
aqui monta uma lista de pedaços e junta só os que existem.

Está em Python, e não em JavaScript no template, porque assim a regra acima vira
teste: monta-se um round decisivo sem clutch, sem multikill e sem virada, e
verifica-se que a frase sai curta em vez de citar campo vazio.
"""
from __future__ import annotations

from metrics.formatting import format_money, format_pct

# Como cada final de round é dito em português. O demo entrega códigos.
MOTIVO = {
    "bomb_defused": "bomba desarmada",
    "bomb_exploded": "bomba explodiu",
    "ct_killed": "CTs eliminados",
    "t_killed": "TRs eliminados",
    "time_ran_out": "tempo esgotado",
}

# Como cada final de round entra numa frase corrida ("o round terminou ...").
MOTIVO_FRASE = {
    "bomb_defused": "no desarme",
    "bomb_exploded": "com a bomba explodindo",
    "ct_killed": "com os CTs eliminados",
    "t_killed": "com os TRs eliminados",
    "time_ran_out": "no tempo",
}


def placar_antes(info: dict) -> tuple[int, int]:
    """Placar ANTES do round: o do fim menos o ponto de quem venceu."""
    a, b = int(info.get("score_a", 0)), int(info.get("score_b", 0))
    if info.get("winner_team") == "A":
        return a - 1, b
    return a, b - 1


def contexto_placar(info: dict) -> str | None:
    """"Empate em 9-9", "com o Time A em 10-8". None quando é o primeiro round."""
    a, b = placar_antes(info)
    if a == 0 and b == 0:
        return None
    if a == b:
        return f"Empate em {a}-{b}"
    lider = "A" if a > b else "B"
    return f"Time {lider} na frente por {max(a, b)}-{min(a, b)}"


# Contração de "de" com artigo definido. Existe porque as frases são montadas
# por pedaços: "a partir de" + "o Time B na frente" saía "a partir de o Time B".
CONTRACOES_DE = {"o ": "do ", "a ": "da ", "os ": "dos ", "as ": "das "}


def com_de(sintagma: str) -> str:
    """"o Time B..." vira "do Time B..."; "um empate..." vira "de um empate..."."""
    for artigo, contraido in CONTRACOES_DE.items():
        if sintagma.startswith(artigo):
            return contraido + sintagma[len(artigo):]
    return "de " + sintagma


def contexto_placar_sintagma(info: dict) -> str | None:
    """O mesmo contexto de placar, mas para encaixar depois de "a partir de".

    Existe porque `.lower()` na frase inteira transformava "Time B na frente" em
    "time b na frente" -- nome de time não é texto corrido. Aqui o artigo vem
    junto e a capitalização do nome fica intacta.
    """
    a, b = placar_antes(info)
    if a == 0 and b == 0:
        return None
    if a == b:
        return f"um empate em {a}-{b}"
    lider = "A" if a > b else "B"
    # Quando quem liderava é quem venceu o round, nomear o time de novo repete o
    # sujeito da frase ("Levou o Time B ... a partir do Time B na frente").
    if lider == info.get("winner_team"):
        return f"a própria liderança por {max(a, b)}-{min(a, b)}"
    return f"o Time {lider} na frente por {max(a, b)}-{min(a, b)}"


def manchete(info: dict) -> str | None:
    """O maior acontecimento do round, em ordem de quanto explica o resultado.

    Mesma ordem usada no placar do painel: clutch e multikill primeiro porque são
    o round inteiro decidido por uma pessoa; virada numérica depois porque é
    coletiva; abertura por último porque acontece em todo round -- só vira
    manchete quando não houve nada mais forte.
    """
    if info.get("clutch_player"):
        return f"{info['clutch_player']} fechou o 1v{info['clutch_against']}"
    if info.get("multikill_player") and int(info.get("multikill_count", 0)) >= 3:
        return f"{info['multikill_player']} fez {info['multikill_count']} kills"
    if int(info.get("worst_deficit_overcome", 0)) >= 2:
        return (
            f"o Time {info['winner_team']} virou com "
            f"{info['worst_deficit_overcome']} jogadores a menos"
        )
    abertura = info.get("opening")
    if abertura and abertura.get("player"):
        return f"{abertura['player']} abriu matando {abertura['victim']}"
    return None


def manchete_sintagma(info: dict) -> str | None:
    """A mesma manchete, mas como sintagma nominal, pra caber depois de "com".

    Existe porque a forma verbal ("donk666 fechou o 1v4") lida depois de "com"
    vira "com donk666 fechou o 1v4". Mesma informação, encaixe diferente.
    """
    if info.get("clutch_player"):
        return f"o 1v{info['clutch_against']} de {info['clutch_player']}"
    if info.get("multikill_player") and int(info.get("multikill_count", 0)) >= 3:
        return f"os {info['multikill_count']} kills de {info['multikill_player']}"
    if int(info.get("worst_deficit_overcome", 0)) >= 2:
        return (
            f"a virada do Time {info['winner_team']} com "
            f"{info['worst_deficit_overcome']} jogadores a menos"
        )
    abertura = info.get("opening")
    if abertura and abertura.get("player"):
        return f"a abertura de {abertura['player']} sobre {abertura['victim']}"
    return None


def historia_round_decisivo(info: dict, wp: dict) -> str:
    """A frase do card do round decisivo, ancorada nos DOIS números.

    A frase começa pelo que a conta diz -- de quanto para quanto foi a chance de
    vitória -- porque é isso que responde "por que este round". O acontecimento
    do round (clutch, multikill, virada) entra depois, como o COMO. Antes era o
    contrário, e o card descrevia uma jogada bonita sem dizer o que ela mudou.

    `wp` é a linha da curva daquele round (metrics/win_probability.curva_da_partida).
    """
    antes = format_pct(wp.get("wp_vencedor_antes"))
    depois = format_pct(wp.get("wp_vencedor_depois"))
    time = info.get("winner_team")

    pedacos = [f"Levou o Time {time} de {antes} para {depois} de chance de vencer a partida"]

    contexto = contexto_placar_sintagma(info)
    if contexto:
        pedacos.append(f"a partir {com_de(contexto)}")

    evento = manchete_sintagma(info)
    if evento:
        pedacos.append(f"com {evento}")

    motivo = MOTIVO_FRASE.get(info.get("reason", ""))
    if motivo:
        pedacos.append(f"e o round terminou {motivo}")

    frase = ", ".join(pedacos[:-1])
    frase = f"{frase}, {pedacos[-1]}" if frase else pedacos[-1]
    return frase.replace(", e o round", " e o round") + "."


def historia_sem_round_decisivo(resumo: dict, placar: tuple[int, int]) -> str:
    """O caso em que NENHUM round decidiu a partida.

    Não é um caso de borda a esconder: numa partida de placar largo a diferença
    se construiu ao longo do jogo, e eleger um round à força inventa uma virada
    que não houve. A frase diz isso com o número que sustenta a afirmação.
    """
    maior = resumo.get("maior_wpa")
    minimo = resumo.get("minimo_exigido")
    a, b = placar
    frase = (
        f"Partida sem round decisivo: a diferença se construiu ao longo do jogo, "
        f"e o placar terminou em {max(a, b)}-{min(a, b)}"
    )
    if maior is not None and minimo is not None:
        frase += (
            f". O round de maior peso moveu {format_pct(maior)} da chance de vitória, "
            f"abaixo dos {format_pct(minimo)} que o modelo exige para chamar um "
            f"round de decisivo"
        )
    return frase + "."


def criterio_do_decisivo(resumo: dict) -> str:
    """Explica o critério e cita os outros rounds de maior peso.

    Os outros existem para mostrar que o "decisivo" saiu de uma ordenação, não de
    uma escolha -- e quando o primeiro e o segundo empatam, dizer isso é mais
    honesto que fingir que a ordem foi óbvia.
    """
    base = (
        "Critério: variação da probabilidade de vitória da partida, calculada "
        "por programação dinâmica sobre os estados de placar. Sem peso arbitrário"
    )
    top = resumo.get("top") or []
    decisivo = resumo.get("decisivo")
    if not decisivo or len(top) < 2:
        return base + "."

    outros = [t for t in top if t["round"] != decisivo["round"]]
    if not outros:
        return base + "."

    if resumo.get("empate_no_topo"):
        vice = outros[0]
        return (
            f"{base}. O round {vice['round']} moveu praticamente o mesmo "
            f"({format_pct(vice['wpa_abs'])} contra {format_pct(decisivo['wpa_abs'])}): "
            f"houve mais de um round de peso equivalente, e a escolha entre eles "
            f"não é do modelo."
        )
    citados = ", ".join(
        f"round {t['round']} ({format_pct(t['wpa_abs'])})" for t in outros
    )
    return f"{base}. Depois dele vêm {citados}."


def historia_round_impressionante(resumo: dict, round_decisivo: int | None) -> str | None:
    """A frase do card do round mais impressionante.

    Diz explicitamente se foi ou não o mesmo round decisivo. Quando não foi, essa
    diferença é a informação boa do card: o round mais bonito da partida pode não
    ter mudado nada, e vale dizer.
    """
    imp = resumo.get("impressionante")
    if not imp:
        return None

    partes = [c["texto"] for c in imp.get("componentes", [])]
    if not partes:
        return None
    corpo = partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + " e " + partes[-1]
    frase = f"Round {imp['round']}: {corpo}"

    if round_decisivo is None:
        frase += (
            ". Não foi o round decisivo porque esta partida não teve um -- a "
            "diferença se construiu ao longo do jogo"
        )
    elif imp["round"] == round_decisivo:
        frase += ". Foi também o round que mais moveu a partida"
    else:
        frase += (
            f". Não foi o round decisivo -- quem mais moveu a partida foi o "
            f"{round_decisivo}, e o round mais bonito daqui não mudou o resultado"
        )
    return frase + "."


def leitura_economica(equip_vencedor, equip_perdedor, perdedor_estava_melhor: bool) -> str | None:
    """Economia como LEITURA ao lado, nunca como peso no score.

    Round perdido em eco era esperado e não custou nada de extraordinário; round
    perdido com equipamento igual ou superior custou mais do que o placar mostra.
    Isso é contexto para interpretar o round decisivo, e por isso não entra na
    conta que o elege -- entrasse, e a decisividade passaria a depender de quanto
    dinheiro os times tinham, que é outra pergunta.
    """
    if equip_vencedor is None and equip_perdedor is None:
        return None

    frase = (
        f"Equipamento médio no round: {format_money(equip_vencedor)} de quem venceu "
        f"contra {format_money(equip_perdedor)} de quem perdeu"
    )
    if perdedor_estava_melhor:
        frase += (
            ". Quem perdeu estava com o equipamento melhor, então a derrota não "
            "tem desculpa de economia -- custou mais do que um round no placar"
        )
    return frase + "."


def historia_mvp(mvp: dict) -> str:
    """A frase do card do MVP, montada com os componentes que o elegeram.

    A regra é a mesma do resto do módulo: só entra o que existe. O que muda aqui
    é a COMPARAÇÃO -- um número sozinho ("94 de ADR") não deixa conferir nada,
    então cada componente em que ele lidera vem com o melhor dos outros ao lado.
    """
    if not mvp:
        return ""

    lidera = [c for c in mvp.get("componentes", []) if c.get("lidera")]
    partes = []
    for c in lidera[:2]:
        pedaco = f"{c['texto']} {c.get('sintagma') or c['rotulo']}"
        if c.get("melhor_dos_outros_texto") and c.get("melhor_dos_outros_nome"):
            pedaco += f" contra {c['melhor_dos_outros_texto']} de {c['melhor_dos_outros_nome']}"
        partes.append(pedaco)

    nome = mvp["name"]
    if not partes:
        # Ninguém lidera componente nenhum: ele venceu na soma, e dizer isso é
        # mais honesto que escolher um número em que ele não foi o melhor.
        return f"{nome} foi o MVP pela soma dos componentes, sem liderar nenhum deles isoladamente."

    corpo = partes[0] if len(partes) == 1 else f"{partes[0]} e {partes[1]}"
    frase = f"{nome} foi o MVP com {corpo}"

    funcao = mvp.get("funcao")
    if funcao:
        frase += f", jogando de {funcao.lower()}"
    return frase + "."


def historia_destaque(destaque: dict) -> str:
    """A frase do card da direita -- positiva ou negativa, sempre com número.

    Tom do card negativo: FATO, não xingamento. "Terminou com 38 de ADR contra
    71 do segundo pior, e o time venceu mesmo assim" é análise; adjetivo sem
    número atrás não é. Por isso a evidência não é opcional aqui: sem número e
    sem referência, a função devolve string vazia e o card não renderiza.
    """
    if not destaque:
        return ""

    ev = destaque.get("evidencia") or {}
    nome = destaque["name"]
    if destaque.get("negativo") and not ev.get("referencia"):
        return ""

    if ev.get("valor"):
        # o rótulo da métrica já traz o "de" quando precisa dele -- ver
        # `_evidencia_obrigatoria` em metrics/match_highlights.py
        frase = f"{nome}: {ev['valor']} {ev['metrica']}"
        if ev.get("referencia"):
            quem = ev.get("referencia_nome") or ev.get("referencia_rotulo") or "os outros"
            frase += f", contra {ev['referencia']} de {quem}"
    else:
        frase = f"{nome} — {destaque.get('meaning', '')}"

    if destaque.get("amostra_fraca"):
        frase += (
            ". Nenhuma função da partida passou do piso de evidência, então este é "
            "o mais próximo disso e não um destaque firme"
        )
    elif destaque.get("equivalente"):
        eq = destaque["equivalente"]
        frase += (
            f". {eq['name']} pontuou praticamente o mesmo como {eq['label'].lower()}: "
            f"houve mais de um destaque equivalente nesta partida"
        )
    return frase + "."


def historia_papel(label: str, nome: str, evidencia_texto: str, significado: str) -> str:
    """Frase do card de um papel: o que é o papel, e a evidência do jogador.

    O texto é sempre DESCRITIVO, inclusive nos papéis críticos: descreve o
    comportamento medido, não julga quem jogou.
    """
    pedacos = [f"{nome} é o retrato do papel nesta partida: {significado}"]
    if evidencia_texto:
        # a evidência vem de metrics/archetypes.py em minúscula, porque lá ela é
        # um fragmento; aqui ela abre frase
        pedacos.append(evidencia_texto[0].upper() + evidencia_texto[1:])
    return ". ".join(pedacos).replace("..", ".") + "."


# ---------------------------------------------------------------------------
# Como o jogador joga, em português
# ---------------------------------------------------------------------------
#
# A tabela de taxas responde "quanto", mas obriga o leitor a comparar 17 linhas
# com 17 medianas para descobrir o que aquele jogador tem de diferente. Este
# bloco faz essa comparação e diz o resultado.
#
# Nada aqui é interpretação de função: "joga longe do time em 64% dos rounds
# contra 37% dos outros" é releitura da medição. Apelido de papel continua
# vindo de metrics/archetypes.py, que tem definição de jogo por trás.
#
# Cada frase tem versão para taxa ALTA e para taxa BAIXA. Só entram as duas
# direções que fazem sentido de jogo: "quase nunca pega a AWP" descreve alguém,
# mas "quase nunca fica por último" não descreve ninguém -- é consequência do
# round, não escolha do jogador. Onde a direção baixa não diz nada, ela é None.
# (frase para taxa ALTA, frase para taxa BAIXA, unidade do denominador).
#
# A unidade importa porque nem toda taxa é sobre rounds: "mata de AWP em 2 de 13
# kills" e "converte quando sobra em 2 de 5 vezes" têm denominadores próprios, e
# dizer "em 2 rounds" neles seria falso.
FRASES_PERFIL = {
    "pct_rounds_longe_do_time": ("joga longe do time", "joga colado no time", "rounds"),
    "pct_rounds_isolado": ("fica sozinho no mapa", None, "rounds"),
    "pct_rounds_ancorado": ("ancora num lugar só", "não para quieto", "rounds"),
    "pct_rounds_rotacionando": ("roda o mapa", None, "rounds"),
    "pct_rounds_com_awp": ("puxa a AWP", None, "rounds"),
    "pct_kills_de_awp": ("mata de AWP", None, "kills"),
    "pct_rounds_abertura_awp": ("abre o round de AWP", None, "rounds"),
    "pct_rounds_smg_ou_pistola_com_time_de_rifle": (
        "fica com a arma pior que a do time", None, "rounds"
    ),
    "pct_rounds_contato_cedo": ("encosta cedo no adversário", "demora a encostar", "rounds"),
    "pct_rounds_contato_tarde": ("chega ao contato depois do time", None, "rounds"),
    "pct_rounds_primeiro_contato_do_time": ("é quem abre o round pro time", None, "rounds"),
    # "sai vivo" e não "sai vivo dos rounds": a contagem já vem logo depois, e
    # "sai vivo dos rounds em 10 rounds" repete a palavra na mesma frase.
    "pct_rounds_sobreviveu": ("sai vivo", "morre", "rounds"),
    "pct_mortes_trocadas": ("morre trocado pelo time", "morre sem o time trocar", "mortes"),
    "pct_rounds_trade_kill": ("troca a morte do companheiro", None, "rounds"),
    "pct_rounds_em_clutch": ("sobra por último", None, "rounds"),
    "taxa_conversao_clutch": (
        "fecha o round sozinho", "não fecha o round sozinho", "vezes"
    ),
    "pct_rounds_lurk": ("faz lurk", None, "rounds"),
}

# Singular de cada unidade, para "em 1 round" não sair "em 1 rounds".
SINGULAR = {"rounds": "round", "kills": "kill", "mortes": "morte", "vezes": "vez"}

# O quanto a taxa precisa se afastar da mediana dos outros para virar
# característica. 15 pontos é o mesmo limiar que o painel usa para destacar a
# linha -- abaixo disso, com 20 rounds, a diferença cabe em três rounds.
MARGEM_CARACTERISTICA = 0.15

# Quantas características entram no resumo. Quatro descrevem um jogador; a lista
# inteira vira a própria tabela de novo, que é o que este bloco existe pra evitar.
MAX_CARACTERISTICAS = 4


def descreve_jogador(perfil: dict) -> dict:
    """Como o jogador joga: o que ele tem de diferente dos outros.

    Devolve `titulo` (a característica mais forte), `resumo` (uma frase com as
    principais) e `caracteristicas` (a lista, cada uma com o bruto e a mediana
    dos outros, pra dar pra discordar da frase olhando o número).

    Regras, as mesmas do resto da narrativa do projeto:
    - característica sem denominador suficiente não entra (amostra fraca não
      vira afirmação);
    - jogador sem nada fora da curva devolve lista vazia e um resumo que diz
      isso, em vez de inventar um traço.
    """
    achados = []

    for chave, (alto, baixo, unidade) in FRASES_PERFIL.items():
        taxa, ref = perfil.get(chave), perfil.get(f"{chave}_ref")
        n, d = perfil.get(f"{chave}_n"), perfil.get(f"{chave}_d")
        if taxa is None or ref is None or not d:
            continue
        if perfil.get(f"{chave}_fraco"):
            continue

        diferenca = taxa - ref
        if abs(diferenca) < MARGEM_CARACTERISTICA:
            continue
        frase = alto if diferenca > 0 else baixo
        if frase is None:
            continue

        # Característica invertida conta o COMPLEMENTO. "joga colado no time" sai
        # da taxa de LONGE estar baixa, então o número que sustenta a frase é
        # `d - n`, não `n`. Mostrar o `n` ali seria exibir a contagem do
        # comportamento oposto ao que a frase afirma.
        acima = diferenca > 0
        n_frase = int(n) if acima else int(d) - int(n)
        ref_frase = float(ref) if acima else 1.0 - float(ref)

        achados.append(
            {
                "chave": chave,
                "texto": frase,
                "taxa": n_frase / int(d),
                "ref": ref_frase,
                "n": n_frase,
                "d": int(d),
                "unidade": unidade if n_frase != 1 else SINGULAR.get(unidade, unidade),
                "acima": acima,
                "distancia": abs(diferenca),
            }
        )

    achados.sort(key=lambda a: a["distancia"], reverse=True)
    achados = achados[:MAX_CARACTERISTICAS]

    nome = perfil.get("name", "o jogador")
    rounds = perfil.get("rounds_jogados") or 0
    partidas = perfil.get("partidas") or 1
    base = f"{rounds} rounds em {partidas} partida" + ("s" if partidas > 1 else "")

    if not achados:
        return {
            "titulo": "sem traço fora da curva",
            "resumo": (
                f"{nome} não se afasta da mediana do time em nenhum dos comportamentos "
                f"medidos ({base}). Isso é resultado, não falta de dado: jogador "
                f"distribuído existe."
            ),
            "caracteristicas": [],
        }

    # Cada característica leva a própria contagem: "faz lurk em 6 rounds" diz
    # mais que "faz lurk", e sem isso o leitor tem que descer até os chips pra
    # saber se são 6 de 18 ou 17 de 18.
    # Quando a unidade é "rounds", o total já foi dito na abertura da frase e
    # repetir vira ruído. Nas outras (kills, mortes, vezes que ficou por último)
    # o denominador é outro e precisa aparecer: "em 5 mortes" não diz de quantas.
    textos = [
        f"{a['texto']} em {a['n']} {a['unidade']}"
        if a["chave"].startswith("pct_rounds_")
        else f"{a['texto']} em {a['n']} de {a['d']} {a['unidade']}"
        for a in achados
    ]
    if len(textos) == 1:
        lista = textos[0]
    else:
        lista = ", ".join(textos[:-1]) + " e " + textos[-1]

    return {
        "titulo": achados[0]["texto"],
        "resumo": f"Em {base}, {nome} {lista}.",
        "caracteristicas": achados,
    }
