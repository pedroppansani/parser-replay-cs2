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
