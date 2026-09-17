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


def historia_round_decisivo(info: dict, ponto_sem_volta: int | None = None) -> str:
    """A frase do card do round decisivo, montada só com o que a partida tem."""
    pedacos: list[str] = []

    contexto = contexto_placar(info)
    if contexto:
        pedacos.append(contexto)

    evento = manchete(info)
    if evento:
        pedacos.append(evento)

    motivo = MOTIVO_FRASE.get(info.get("reason", ""))
    if motivo:
        pedacos.append(f"e o round terminou {motivo}")

    if not pedacos:
        # Nem placar, nem evento, nem motivo reconhecido: o honesto é dizer só o
        # que se sabe, que é qual round foi.
        return f"Round {info['round']} — o de maior peso na partida."

    frase = ", ".join(pedacos[:-1])
    frase = f"{frase}, {pedacos[-1]}" if frase else pedacos[-1]
    frase = frase.replace(", e o round", " e o round")

    if ponto_sem_volta is not None and info.get("round") == ponto_sem_volta:
        frase += ". A liderança que sai daqui não é mais devolvida"
    return frase + "."


def criterio_e_vice(rounds_scored: list[dict], decisivo: dict) -> str:
    """Explica o critério e cita o segundo colocado, se houver um.

    O segundo colocado existe pra mostrar que o "decisivo" saiu de uma ordenação,
    não de uma escolha. Se a partida tem um round só, a menção simplesmente não
    aparece.
    """
    base = (
        "Critério: virada de placar não devolvida (peso maior), desvantagem "
        "numérica superada, multikill, clutch e proximidade no placar"
    )
    outros = [
        r for r in rounds_scored
        if r.get("round") != decisivo.get("round") and r.get("importance") is not None
    ]
    if not outros:
        return base + "."

    vice = max(outros, key=lambda r: r["importance"])
    evento = manchete_sintagma(vice)
    if evento:
        return f"{base}. O round {vice['round']} vem em segundo, com {evento}."
    return f"{base}. O round {vice['round']} vem em segundo."


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
