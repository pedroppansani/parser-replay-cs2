"""
Os dois cards de jogador da aba de leitura da partida.

A seção tem estrutura FIXA em toda partida: round decisivo em cima, MVP embaixo
à esquerda, outro destaque embaixo à direita. Estrutura fixa é o que torna duas
partidas comparáveis de relance -- se o layout mudasse conforme o que a partida
teve, cada página ensinaria a ser lida de novo.

O card da esquerda mostra os COMPONENTES do MVP e não só o índice: um número
agregado sozinho não deixa conferir nada. Quem lê tem que ver se ele venceu por
ADR, por abertura ou por clutch, e quanto isso foi acima do segundo colocado.

O card da direita é o jogador mais notável ENTRE OS OUTROS, e "notável" inclui
destaque negativo. A regra de tom é fato com número: "terminou com 38 de ADR
contra 71 do segundo pior, e o time venceu mesmo assim" é análise; adjetivo sem
número atrás é xingamento.

Comparabilidade entre funções
-----------------------------
Funções diferentes só disputam o mesmo card se as pontuações quiserem dizer a
mesma coisa. Aqui todas significam "o quanto isto está acima do normal", em
[0, 1]:

- **papéis comportamentais** (`metrics/archetypes.py`) já vêm como percentil
  contra a distribuição do CONJUNTO das partidas. Decisão 16 do CLAUDE.md, e ela
  é mais forte que padronizar dentro da partida: normalizar dentro da partida
  faria alguém ficar em 1,0 mesmo quando ninguém se destacou;
- **funções estruturais** usam a concentração PONDERADA pela fração de
  companheiros que ela supera. A concentração crua não serve: "coringa em 12 de
  12 rounds" dá 1,0 e é o caso COMUM, não um destaque -- medido, isso elegia o
  card da direita em 6 das 9 partidas e afogava destaques de verdade. Ponderada,
  um jogador só pontua quando é mais fixo na função que os outros, e quando
  todos são igualmente fixos a pontuação vai a zero, como deve;
- **bottom frag** usa a distância até o penúltimo em unidades da dispersão
  normal da partida. É a única que se mede dentro da partida, e pode: ela não
  sofre o problema da decisão 16, porque numa partida equilibrada ela dá zero em
  vez de eleger alguém à força.
"""
from __future__ import annotations

import numpy as np
import polars as pl

from metrics.archetypes import PAPEIS
from metrics.structural_roles import FUNCOES

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# Pesos do índice de MVP. Ficam aqui, e não espalhados, porque são a DEFINIÇÃO
# de impacto que decide round: dano constante primeiro, presença no round
# depois, e os dois eventos raros que viram round sozinhos por último.
PESOS_MVP = {
    "adr": 0.40,
    "kast_pct": 0.30,
    "opening_kills": 0.20,
    "clutches": 0.10,
}

# Rótulo, unidade e como o componente entra numa frase corrida. O terceiro
# campo existe porque `rotulo.lower()` produzia "126,1 de adr" -- sigla não se
# minúscula, e "5 de aberturas" não é português.
COMPONENTES_MVP = {
    "adr": ("ADR", "de dano por round", "de ADR"),
    "kast_pct": ("KAST", "% dos rounds com contribuição", "de KAST"),
    "opening_kills": ("Aberturas", "rounds em que abriu o placar", "aberturas de round"),
    "clutches": ("Clutches", "rounds fechados sozinho", "clutches fechados"),
}

# Piso de evidência: abaixo disso nenhuma função é forte o bastante para virar
# card. O card ainda mostra a mais próxima, marcada como amostra fraca -- é
# melhor dizer "ninguém se destacou" que promover um jogador mediano a retrato
# da partida (mesmo motivo da decisão 16).
PISO_EVIDENCIA = 0.70

# Distância abaixo da qual o primeiro e o segundo destaque são equivalentes. Se
# 0,81 e 0,79 virassem uma escolha, o card fingiria uma certeza que a conta não
# tem. Mesma regra do round decisivo (`metrics/win_probability`).
LIMIAR_EMPATE_DESTAQUE = 0.05

# Bottom frag: quantas dispersões abaixo do PENÚLTIMO o jogador precisa estar.
#
# A trava existe porque "o último do placar" é aritmética, não observação --
# alguém sempre é o último. Para virar card ele tem que estar destacadamente
# abaixo, e "destacadamente" só significa alguma coisa em relação ao quanto os
# jogadores daquela partida normalmente se espalham. 1,5 dispersão é o piso de
# entrada; a partir de 3,0 a pontuação satura.
MIN_DISPERSOES_BOTTOM_FRAG = 1.5
MAX_DISPERSOES_BOTTOM_FRAG = 3.0

# Funções comportamentais que NÃO disputam o card da direita.
#
# `carry` sai porque é o mesmo recorte do MVP e a aba contaria a mesma coisa
# duas vezes.
PAPEIS_FORA_DO_DESTAQUE = ("carry",)

# Funções negativas. Elas precisam do número e da referência para renderizar --
# ver `_evidencia_obrigatoria`.
PAPEIS_NEGATIVOS = ("mochila", "baiter", "rei_do_nt", "bottom_frag")

# Rótulo e significado das funções que este módulo acrescenta ao pool.
FUNCOES_EXTRAS = {
    "bottom_frag": ("Bottom frag", "afundou bem abaixo do resto da partida"),
}


# ---------------------------------------------------------------------------
# Card da esquerda: MVP
# ---------------------------------------------------------------------------

# Plural -> singular dos sintagmas que contam coisas. Tabela pequena e explícita
# em vez de regra de derivação: são quatro casos e nenhum deles é regular.
SINGULARES = {
    "aberturas de round": "abertura de round",
    "clutches fechados": "clutch fechado",
}


def _singular(sintagma: str) -> str:
    return SINGULARES.get(sintagma, sintagma)


def _texto_numero(chave: str, valor: float | None) -> str:
    """Número do componente já formatado, com a vírgula decimal brasileira."""
    if valor is None:
        return "—"
    if chave == "kast_pct":
        return f"{valor:.0f}%".replace(".", ",")
    if chave in ("opening_kills", "clutches"):
        return str(int(valor))
    return f"{valor:.1f}".replace(".", ",")


def mvp_da_partida(players: pl.DataFrame, funcao_por_steamid: dict[int, str]) -> dict | None:
    """O MVP, os componentes que o elegeram e a comparação com o segundo.

    Cada componente sai com o valor dele E com o melhor valor entre os OUTROS
    jogadores -- é o que permite dizer "94 de ADR contra 81 do segundo", que
    informa muito mais que "94 de ADR". `lidera` diz em quais componentes ele
    realmente ganhou, que é a resposta para "ele venceu por quê".
    """
    if players.height == 0:
        return None

    ordenado = players.sort("mvp_index", descending=True)
    primeiro = ordenado.row(0, named=True)
    vice = ordenado.row(1, named=True) if ordenado.height > 1 else None

    componentes = []
    for chave, peso in PESOS_MVP.items():
        if chave not in players.columns:
            continue
        rotulo, unidade, sintagma = COMPONENTES_MVP[chave]
        meu = primeiro.get(chave)
        outros = ordenado.filter(pl.col("steamid") != primeiro["steamid"])
        melhor_outro = outros.sort(chave, descending=True).row(0, named=True) if outros.height else None

        componentes.append({
            "chave": chave,
            "rotulo": rotulo,
            "unidade": unidade,
            # concordância: "1 clutch fechado" e não "1 clutches fechados"
            "sintagma": _singular(sintagma) if meu == 1 else sintagma,
            "peso": peso,
            "valor": None if meu is None else float(meu),
            "texto": _texto_numero(chave, meu),
            "melhor_dos_outros": (
                None if melhor_outro is None else float(melhor_outro.get(chave) or 0)
            ),
            "melhor_dos_outros_texto": (
                "—" if melhor_outro is None else _texto_numero(chave, melhor_outro.get(chave))
            ),
            "melhor_dos_outros_nome": None if melhor_outro is None else melhor_outro["name"],
            "lidera": bool(
                melhor_outro is not None
                and meu is not None
                and float(meu) > float(melhor_outro.get(chave) or 0)
            ),
        })

    return {
        "steamid": primeiro["steamid"],
        "name": primeiro["name"],
        "team": primeiro.get("team"),
        "funcao": funcao_por_steamid.get(int(primeiro["steamid"])),
        "indice": float(primeiro["mvp_index"]),
        "vice_nome": None if vice is None else vice["name"],
        "vice_indice": None if vice is None else float(vice["mvp_index"]),
        "componentes": componentes,
    }


# ---------------------------------------------------------------------------
# Card da direita: o outro destaque
# ---------------------------------------------------------------------------

def _dispersao(valores: np.ndarray) -> float:
    """Espalhamento típico entre jogadores, robusto a um ponto fora da curva.

    Desvio absoluto mediano e não desvio padrão: o próprio bottom frag puxaria o
    desvio padrão para cima e esconderia o afundamento que se quer detectar --
    ele viraria parte da 'dispersão normal'.
    """
    if valores.size < 2:
        return 0.0
    mad = float(np.median(np.abs(valores - np.median(valores))))
    # 1,4826 põe o MAD na mesma escala de um desvio padrão sob normalidade, que
    # é o que torna "1,5 dispersões" uma frase com sentido conhecido.
    return mad * 1.4826


def candidato_bottom_frag(players: pl.DataFrame) -> dict | None:
    """O último do placar, SE ele estiver destacadamente abaixo do penúltimo.

    Numa partida em que os cinco piores estão dentro do espalhamento comum, esta
    função devolve None -- e isso é o certo. Alguém sempre é o último.
    """
    if players.height < 3 or "adr" not in players.columns:
        return None

    ordenado = players.sort("adr")
    pior = ordenado.row(0, named=True)
    penultimo = ordenado.row(1, named=True)

    outros = ordenado["adr"].to_numpy()[1:]
    disp = _dispersao(outros)
    if disp <= 0:
        return None

    gap = float(penultimo["adr"]) - float(pior["adr"])
    dispersoes = gap / disp
    if dispersoes < MIN_DISPERSOES_BOTTOM_FRAG:
        return None

    # A pontuação entra JÁ no piso quando passa da trava, e cresce dali até
    # saturar: passar da trava é o que qualifica; o quanto passa só ordena.
    excedente = (dispersoes - MIN_DISPERSOES_BOTTOM_FRAG) / (
        MAX_DISPERSOES_BOTTOM_FRAG - MIN_DISPERSOES_BOTTOM_FRAG
    )
    pontuacao = PISO_EVIDENCIA + (1.0 - PISO_EVIDENCIA) * min(1.0, max(0.0, excedente))

    return {
        "funcao": "bottom_frag",
        "steamid": pior["steamid"],
        "name": pior["name"],
        "team": pior.get("team"),
        "pontuacao": pontuacao,
        "negativo": True,
        "valor": float(pior["adr"]),
        "valor_texto": _texto_numero("adr", pior["adr"]),
        "referencia": float(penultimo["adr"]),
        "referencia_texto": _texto_numero("adr", penultimo["adr"]),
        "referencia_nome": penultimo["name"],
        "metrica": "ADR",
        "dispersoes": dispersoes,
    }


def _candidatos_comportamentais(
    archetypes: pl.DataFrame, time_vencedor: str | None
) -> list[dict]:
    """Papéis de `metrics/archetypes.py`, já em escala de percentil global."""
    out = []
    for row in archetypes.iter_rows(named=True):
        for papel in PAPEIS:
            if papel in PAPEIS_FORA_DO_DESTAQUE:
                continue
            idx = row.get(f"idx_{papel}")
            if idx is None:
                continue

            # Mochila EXIGE vitória do time. Jogador com número ruim em time que
            # perdeu não é mochila: é jogador ruim em time que perdeu, e isso não
            # é destaque nenhum. Sem a trava, toda derrota elegeria um "mochila".
            if papel == "mochila" and row.get("team") != time_vencedor:
                continue

            out.append({
                "funcao": papel,
                "steamid": row["steamid"],
                "name": row["name"],
                "team": row.get("team"),
                "pontuacao": float(idx),
                "negativo": papel in PAPEIS_NEGATIVOS,
                "linha": row,
            })
    return out


def _candidatos_estruturais(structural: pl.DataFrame) -> list[dict]:
    """Funções estruturais, pontuadas pela DISTINÇÃO e não pela consistência.

    A pontuação é a concentração multiplicada pela fração de companheiros do
    mesmo lado que ela supera. O motivo é concreto: com a concentração crua,
    "coringa em 12 de 12 rounds" vale 1,0 -- mas isso é o caso comum, não um
    destaque, e afogava carrega piano e AWPer legítimos em 6 das 9 partidas.

    Com a ponderação, ser fixo na função só conta quando os OUTROS não são. Se
    todo o time é igualmente fixo, ninguém se destaca e a pontuação vai a zero,
    que é a resposta certa -- é a mesma lógica do bottom frag, e por isso não
    recai no problema da decisão 16.
    """
    if structural is None or structural.height == 0:
        return []
    out = []
    for row in structural.iter_rows(named=True):
        if row.get("funcao") is None or row.get("amostra_fraca"):
            continue
        conc = row.get("concentracao")
        if conc is None:
            continue

        pares = structural.filter(
            (pl.col("side") == row["side"]) & (pl.col("steamid") != row["steamid"])
        )["concentracao"].drop_nulls().to_list()
        if not pares:
            continue
        supera = sum(1 for c in pares if conc > c) / len(pares)

        out.append({
            "funcao": f"estrutural_{row['funcao']}",
            "rotulo": FUNCOES[row["funcao"]][0],
            "steamid": row["steamid"],
            "name": row["name"],
            "team": None,
            "pontuacao": float(conc) * supera,
            "concentracao": float(conc),
            "supera": supera,
            "negativo": False,
            "lado": row["side"],
            "rounds_na_funcao": int(row["rounds_na_funcao"]),
            "rounds_no_lado": int(row["rounds_no_lado"]),
        })
    return out


def _evidencia_obrigatoria(cand: dict, archetypes: pl.DataFrame) -> dict | None:
    """Número e referência que sustentam a função. Sem os dois, não renderiza.

    Vale especialmente para os negativos: "jogou mal" não é análise. A regra vale
    para todos porque um card positivo sem número tem o mesmo defeito.
    """
    if cand["funcao"] == "bottom_frag":
        return {
            "metrica": f"de {cand['metrica']}", "valor": cand["valor_texto"],
            "referencia": cand["referencia_texto"], "referencia_nome": cand["referencia_nome"],
            "referencia_rotulo": "segundo pior",
        }

    if cand["funcao"].startswith("estrutural_"):
        return {
            "metrica": f"como {cand['rotulo']} no lado {cand['lado'].upper()}",
            "valor": f"{cand['rounds_na_funcao']} de {cand['rounds_no_lado']} rounds",
            "referencia": None, "referencia_nome": None,
            "referencia_rotulo": None,
        }

    # Papéis comportamentais: a métrica bruta que sustenta o índice, comparada à
    # mediana dos OUTROS jogadores da partida.
    # (coluna, rótulo). O rótulo entra depois do número numa frase corrida, e
    # por isso já traz ou não o "de": "23% de brigas no mesmo ângulo" está certo,
    # "8 de rounds com AWP na mão" não.
    metricas = {
        "mochila": ("damage_share", "de fatia do dano do time"),
        "baiter": ("bait_no_trade_share", "de mortes por perto sem troca"),
        "rei_do_nt": ("clutch_attempts", "tentativas de clutch"),
        "carrega_piano": ("sacrificio_share", "de rounds pagando a conta com retorno ao time"),
        "awper": ("awp_rounds", "rounds com AWP na mão"),
        "camper": ("distinct_places_mean", "regiões por round"),
        "repick": ("repick_share", "de brigas no mesmo ângulo"),
    }
    par = metricas.get(cand["funcao"])
    if par is None:
        return None
    coluna, rotulo = par
    linha = cand.get("linha") or {}
    valor = linha.get(coluna)
    if valor is None:
        return None

    outros = archetypes.filter(pl.col("steamid") != cand["steamid"])[coluna].drop_nulls()
    if outros.len() == 0:
        return None
    ref = float(outros.median())

    def fmt(v: float) -> str:
        if coluna.endswith("_share") or coluna == "damage_share":
            return f"{v * 100:.0f}%".replace(".", ",")
        if coluna in ("awp_rounds", "clutch_attempts"):
            return str(int(round(v)))
        return f"{v:.1f}".replace(".", ",")

    return {
        "metrica": rotulo,
        "valor": fmt(float(valor)),
        "referencia": fmt(ref),
        "referencia_nome": None,
        "referencia_rotulo": "mediana dos outros",
    }


def outro_destaque(
    players: pl.DataFrame,
    archetypes: pl.DataFrame,
    structural: pl.DataFrame | None,
    mvp_steamid: int | None,
    time_vencedor: str | None,
) -> dict | None:
    """O jogador mais notável entre todos os OUTROS, positivo ou negativo.

    Nunca o MVP: o card da direita é sempre outra pessoa, e se o vencedor da
    segunda pontuação for ele, pula-se para o próximo.
    """
    candidatos = _candidatos_comportamentais(archetypes, time_vencedor)
    candidatos += _candidatos_estruturais(structural)
    bf = candidato_bottom_frag(players)
    if bf is not None:
        candidatos.append(bf)

    candidatos = [c for c in candidatos if c["steamid"] != mvp_steamid]
    if not candidatos:
        return None

    # Ordenação em três chaves, e as duas últimas existem por um motivo medido.
    #
    # O percentil satura: vários candidatos empatam em 0,99-1,00 e a pontuação
    # perde resolução justamente no topo. Medido no corpus, o match_03 tinha um
    # bottom frag em 1,00 EMPATADO em primeiro com um repick em 1,00, e quem
    # vencia era simplesmente quem tinha sido inserido antes na lista. Isso não
    # é um critério, é um acidente.
    #
    # No empate, vence o NEGATIVO. Não é preferência por más notícias: é que o
    # card da esquerda já é um destaque positivo, então um segundo positivo
    # repete o tipo de informação que a seção acabou de dar, enquanto um
    # negativo acrescenta. E o negativo continua tendo que passar pelas travas
    # dele (distância do bottom frag, vitória da mochila, evidência com número),
    # que não foram afrouxadas -- o desempate não abre exceção para ninguém.
    #
    # A terceira chave é só determinismo: sem ela, duas execuções iguais podiam
    # devolver cards diferentes.
    candidatos.sort(
        key=lambda c: (c["pontuacao"], 1 if c["negativo"] else 0, c["funcao"]),
        reverse=True,
    )
    melhor = candidatos[0]

    # Empate declarado: o candidato mais próximo que seja de OUTRO jogador. Tem
    # que ser outro jogador -- dizer que o mesmo sujeito também pontuou alto numa
    # segunda função não informa que a escolha foi disputada.
    equivalente = None
    for c in candidatos[1:]:
        if c["steamid"] == melhor["steamid"]:
            continue
        if melhor["pontuacao"] - c["pontuacao"] < LIMIAR_EMPATE_DESTAQUE:
            equivalente = c
        break

    evidencia = _evidencia_obrigatoria(melhor, archetypes)
    # Card negativo sem número e sem referência não renderiza. Se a evidência não
    # existe, o candidato é descartado e a vez passa para o próximo.
    if melhor["negativo"] and (evidencia is None or evidencia.get("referencia") is None):
        # descarta o negativo sem evidência E todos os outros candidatos do
        # mesmo jogador: se o número não sustenta um rótulo dele, promovê-lo por
        # outro rótulo é contornar a própria trava
        restantes = [
            c for c in candidatos[1:]
            if not c["negativo"] and c["steamid"] != melhor["steamid"]
        ]
        if not restantes:
            return None
        melhor = restantes[0]
        evidencia = _evidencia_obrigatoria(melhor, archetypes)
        equivalente = None

    rotulo, significado = _rotulo_de(melhor)
    return {
        "funcao": melhor["funcao"],
        "label": rotulo,
        "meaning": significado,
        "steamid": melhor["steamid"],
        "name": melhor["name"],
        "team": melhor.get("team"),
        "index": melhor["pontuacao"],
        "negativo": melhor["negativo"],
        "evidencia": evidencia,
        "amostra_fraca": melhor["pontuacao"] < PISO_EVIDENCIA,
        "equivalente": (
            None if equivalente is None
            else {
                "name": equivalente["name"],
                "label": _rotulo_de(equivalente)[0],
                "index": equivalente["pontuacao"],
            }
        ),
    }


def _rotulo_de(cand: dict) -> tuple[str, str]:
    """Rótulo visível e significado de um candidato, venha ele de onde vier."""
    f = cand["funcao"]
    if f.startswith("estrutural_"):
        chave = f.removeprefix("estrutural_")
        lado = "CT" if cand.get("lado") == "ct" else "TR"
        return FUNCOES[chave][0], f"função dele nos rounds de {lado}"
    if f in FUNCOES_EXTRAS:
        return FUNCOES_EXTRAS[f]
    if f in PAPEIS:
        return PAPEIS[f]
    return f, ""


def match_highlights(
    players: pl.DataFrame,
    archetypes: pl.DataFrame,
    structural: pl.DataFrame | None,
    funcao_por_steamid: dict[int, str],
    time_vencedor: str | None,
) -> tuple[pl.DataFrame, dict]:
    """Contrato do projeto: `(per_round, summary)`.

    Aqui não existe recorte por round -- os dois cards são da PARTIDA --, então
    o `per_round` é a tabela de candidatos com a pontuação de cada um. Ela é o
    que permite auditar por que um destaque venceu o outro, que é a mesma razão
    de o round decisivo expor os três maiores.
    """
    mvp = mvp_da_partida(players, funcao_por_steamid)
    destaque = outro_destaque(
        players, archetypes, structural,
        None if mvp is None else int(mvp["steamid"]), time_vencedor,
    )

    candidatos = _candidatos_comportamentais(archetypes, time_vencedor)
    candidatos += _candidatos_estruturais(structural)
    bf = candidato_bottom_frag(players)
    if bf is not None:
        candidatos.append(bf)

    tabela = pl.DataFrame(
        [
            {"funcao": c["funcao"], "steamid": c["steamid"], "name": c["name"],
             "pontuacao": c["pontuacao"], "negativo": c["negativo"]}
            for c in candidatos
        ],
        schema={"funcao": pl.String, "steamid": pl.UInt64, "name": pl.String,
                "pontuacao": pl.Float64, "negativo": pl.Boolean},
    ).sort("pontuacao", descending=True)

    return tabela, {"mvp": mvp, "destaque": destaque, "piso": PISO_EVIDENCIA}
