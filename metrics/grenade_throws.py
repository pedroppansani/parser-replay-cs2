"""
Ficha de execução de cada arremesso de granada.

O que este módulo responde: COMO aquele arremesso foi feito, com detalhe
suficiente para alguém reproduzir dentro do jogo. Posição, ângulo, postura,
força, trajetória e onde a granada parou.

O que ele deliberadamente NÃO faz: separar "lineup decorado" de "arremesso
qualquer". Essa informação não existe na demo -- não há nada que distinga quem
alinhou pelo canto da parede de quem jogou no olho -- e inferir isso seria
inventar precisão. Todos os arremessos entram.

O problema central: o tick da soltura
-------------------------------------
O `weapon_fire` marca o CLIQUE. Entre o clique e a granada sair da mão roda uma
animação, e o ângulo que importa é o da SOLTURA. Pegar o tick errado leva o
ângulo errado, e a ficha inteira vira lixo -- pior que lixo, porque parece certa.

O atraso da animação não é chutado aqui. Ele é ancorado na geometria, no mesmo
espírito da detecção de tickrate em `metrics/timing.py`: o primeiro ponto
observado do projétil nasce na posição dos OLHOS do arremessador, deslocada um
tanto na direção da mira. Então varre-se a janela de ticks entre o clique e o
primeiro sample do projétil, e vence o tick cuja geometria melhor reproduz o
ponto observado.

A separação que faz isso funcionar: o deslocamento da mão (`d`) e a altura dos
olhos (`h`) entram em eixos diferentes. `d` age no plano horizontal e `h` age só
na vertical. Então o ajuste horizontal determina `d` e o tick SEM precisar saber
`h`, e `h` cai depois como MEDIÇÃO por arremesso -- não como parâmetro ajustado.
É isso que mantém o resíduo horizontal honesto como medida de confiança: nenhum
parâmetro livre por arremesso foi absorvido nele.

O tick OFICIAL (Fase G, decisão do Pedro)
-----------------------------------------
Quando a demo traz o evento `grenade_thrown`, o tick dele É a soltura, e a
ancoragem vira VALIDAÇÃO: roda em paralelo e a diferença fica gravada
(`tick_soltura_ancoragem`, `delta_ancoragem_ticks`). Isso mede o método para o
dia em que um dado não trouxer o evento -- que é exatamente o que aconteceu com a
cegueira (decisão 8h). Medido em 20.863 arremessos de 43 partidas: o primeiro
sample do projétil cai no MESMO tick do evento em 100% deles, e a ancoragem
acerta o tick exato em 39,7%, a +-1 tick em 87,9% e a +-4 em 94,8%, com viés de
+1 (escolhe um tick depois mais vezes que o exato).
Com o tick fixado, a altura dos olhos deixa de ser degenerada e sai medida.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import polars as pl

# ---------------------------------------------------------------------------
# Classes de entidade
#
# SÓ projéteis. A tabela `grenades` do awpy mistura duas coisas de nome quase
# igual: CFlashbangProjectile é a flash ARREMESSADA, voando; CFlashbang é a
# flash parada no INVENTÁRIO, cuja posição é a do jogador que a carrega, do
# começo do round até ele jogar.
#
# Esta é a definição canônica do projeto; `scripts/export_replay.py` importa
# daqui em vez de manter uma cópia.
# ---------------------------------------------------------------------------
GRENADE_KIND = {
    "CHEGrenadeProjectile": "he",
    "CFlashbangProjectile": "flash",
    "CSmokeGrenadeProjectile": "smoke",
    "CMolotovProjectile": "molotov",
    "CDecoyProjectile": "decoy",
}

# Nome da arma na tabela de tiros (`weapon_fire`) para cada tipo. O molotov e a
# incendiária são a MESMA entidade de projétil (CMolotovProjectile) e só se
# distinguem pela arma disparada -- é daqui que sai qual dos dois foi.
ARMA_DE_ARREMESSO = {
    "weapon_hegrenade": "he",
    "weapon_flashbang": "flash",
    "weapon_smokegrenade": "smoke",
    "weapon_molotov": "molotov",
    "weapon_incgrenade": "molotov",
    "weapon_decoy": "decoy",
}

# ---------------------------------------------------------------------------
# Limiares
# ---------------------------------------------------------------------------

# Folga, em ticks, em torno da janela clique->primeiro sample do projétil. O
# `weapon_fire` pode chegar um tick depois do que deveria, e o projétil pode ter
# o primeiro sample um tick atrasado; sem folga a janela exclui o tick certo
# justamente nos casos de borda.
FOLGA_JANELA_TICKS = 3

# Teto da janela de busca, em segundos. A animação de arremesso do CS2 é da
# ordem de meio segundo; 1,5s cobre com muita sobra e evita que um `weapon_fire`
# perdido faça a busca varrer o round inteiro.
MAX_JANELA_SEGUNDOS = 1.5

# Grade de busca do deslocamento da mão (unidades do jogo), do centro dos olhos
# até onde a granada nasce. Derivado, não decorado: o valor escolhido é o que
# minimiza o resíduo horizontal MEDIANO de todo o corpus.
GRADE_OFFSET_MAO = np.arange(0.0, 40.5, 0.5)

# Resíduo horizontal (unidades) acima do qual a ancoragem não convergiu para
# aquele arremesso. Calibrado olhando a distribuição do corpus -- ver o resumo
# que `resumo_de_ancoragem` imprime. Arremesso acima disso continua na ficha,
# mas NÃO pode apresentar reprodução exata.
MAX_RESIDUO_ANCORAGEM = 8.0

# Giro de mira (graus/segundo) acima do qual o ângulo da soltura é incerto mesmo
# com resíduo baixo: se a mira está varrendo, um tick de erro é muitos graus de
# erro, e o lineup não se reproduz. 200°/s é meia tela por segundo.
MAX_GIRO_NA_SOLTURA = 200.0

# Altura dos olhos do CS2, para conferência. O projeto já supunha 64 em pé;
# 46 agachado é o valor correspondente do jogo.
ALTURA_OLHOS_EM_PE = 64.0
ALTURA_OLHOS_AGACHADO = 46.0

# Deslocamento VERTICAL do ponto de nascimento da granada acima dos olhos.
#
# Este valor não estava modelado e apareceu na medição: as alturas derivadas
# davam 67,30u em pé e 49,09u agachado, ou seja +3,30 e +3,09 sobre 64 e 46 --
# o MESMO deslocamento nas duas posturas. Dois grupos independentes errando pela
# mesma constante não é coincidência: é um offset vertical real da soltura, e
# não o 64 do projeto estar errado. Com ele modelado, a altura derivada volta a
# ser diretamente comparável com as 64 unidades que o projeto usa.
OFFSET_VERTICAL_SOLTURA = 3.2

# Faixa fisicamente plausível da altura de olhos derivada. Serve de sanidade --
# valor fora daqui é erro de ancoragem, não jogador excêntrico.
ALTURA_OLHOS_MIN = 30.0
ALTURA_OLHOS_MAX = 80.0

# Fronteira entre agachado e em pé, na altura de olhos derivada. É o ponto médio
# entre os dois valores do jogo (64 e 46), não um limiar escolhido a dedo.
ALTURA_OLHOS_AGACHADO_MAX = (ALTURA_OLHOS_EM_PE + ALTURA_OLHOS_AGACHADO) / 2

# Velocidade horizontal (u/s) abaixo da qual o jogador estava parado. Mesmo
# valor de `metrics/awp_metrics.SLOW_SPEED_THRESHOLD`, para não haver duas
# definições de "parado" no projeto.
VELOCIDADE_PARADO = 70.0

# Velocidade vertical (u/s) acima da qual o jogador estava no ar na soltura --
# jump throw. O pulo do CS2 sai com cerca de 300 u/s; 60 pega também a fase
# final da subida e a queda, sem confundir com rampa.
VELOCIDADE_VERTICAL_NO_AR = 60.0

# Colisão: mudança de direção do vetor velocidade entre samples consecutivos.
# Uma granada em voo livre curva suavemente pela gravidade (poucos graus por
# tick); 25° num tick só acontece batendo em alguma coisa.
ANGULO_COLISAO_GRAUS = 25.0
# Abaixo desta velocidade o projétil já está rolando no chão, e cada tremida
# vira uma "colisão". Colisão só conta enquanto ele está de fato voando.
VELOCIDADE_MINIMA_COLISAO = 50.0

# Agrupamento por moda das velocidades de arremesso (u/s). Raio do grupo, e
# mínimo de arremessos para um grupo existir. Moda e não bin de largura fixa
# pelo motivo registrado na decisão 5 do CLAUDE.md: velocidade caindo na borda
# de um bin se divide entre dois e o grupo some.
RAIO_GRUPO_FORCA = 60.0
MIN_ARREMESSOS_POR_FORCA = 20

# Quanto da velocidade do JOGADOR a granada herda, na escala em que este módulo
# MEDE a velocidade do jogador (diferença central de posição entre dois ticks).
#
# Não é 1,0 por decreto. O critério é objetivo: a velocidade relativa não pode
# depender da velocidade de quem arremessou -- se depender, o desconto está
# errado e um run-throw curto vira arremesso longo.
#
# Medido varrendo k no corpus de 3.020 arremessos, com DOIS critérios
# independentes que caem no mesmo lugar:
#   - a inclinação de (v_relativa ~ v_jogador) cruza zero em k = 1,250
#     (-0,006, contra +0,17 em k = 1,0);
#   - o IQR do grupo dominante é MÍNIMO em k = 1,250 (8,8 u/s, contra 41,6 em
#     k = 1,0).
#
# Dois critérios independentes coincidindo em 1,25 redondo dizem que isto é a
# constante do próprio jogo -- o CS soma um múltiplo da velocidade do jogador,
# não a velocidade dela pura --, e não um fator de correção do estimador.
FATOR_HERANCA = 1.25

# Tolerância (unidades) para considerar dois ticks igualmente bons na ancoragem.
#
# Existe por um motivo concreto: com o jogador parado e a mira quieta, o resíduo
# é praticamente o mesmo em toda a janela, e o `argmin` escolhia a BORDA por
# ruído -- 312 dos 3.020 arremessos saíam com a soltura 9 a 17 ticks antes do
# primeiro sample do projétil, o que é fisicamente impossível. Entre empates,
# vence o tick mais próximo do primeiro sample do projétil, que é onde a soltura
# tem que estar.
TOLERANCIA_EMPATE_TICK = 0.5


# ---------------------------------------------------------------------------
# Geometria
# ---------------------------------------------------------------------------

def direcao_da_mira(pitch: np.ndarray, yaw: np.ndarray) -> np.ndarray:
    """Vetor unitário da direção de visão, na convenção do CS2.

    Decisão 9 do CLAUDE.md: **pitch positivo é olhar para BAIXO**. É por isso
    que a componente Z leva sinal negativo. Inverter isto faz a ancoragem
    procurar a granada no lugar espelhado na vertical.
    """
    p = np.radians(np.asarray(pitch, dtype=float))
    y = np.radians(np.asarray(yaw, dtype=float))
    return np.stack([np.cos(p) * np.cos(y), np.cos(p) * np.sin(y), -np.sin(p)], axis=-1)


# ---------------------------------------------------------------------------
# Extração dos arremessos
# ---------------------------------------------------------------------------

def trajetorias(grenades: pl.DataFrame, rounds: pl.DataFrame) -> pl.DataFrame:
    """Um projétil por (round, entity_id), com a trajetória ordenada.

    Filtra warmup e tempo parado pelo mesmo critério do resto do projeto: só
    conta o que aconteceu entre o fim do freeze e o fim do round (decisão 8b).
    """
    if grenades is None or grenades.height == 0:
        return pl.DataFrame()

    janela = rounds.select(["round_num", "freeze_end", "end"])
    return (
        grenades.filter(pl.col("grenade_type").is_in(list(GRENADE_KIND)))
        .filter(pl.col("X").is_not_null() & pl.col("Y").is_not_null() & pl.col("Z").is_not_null())
        .join(janela, on="round_num", how="inner")
        .filter((pl.col("tick") >= pl.col("freeze_end")) & (pl.col("tick") <= pl.col("end")))
        .sort(["round_num", "entity_id", "tick"])
    )


def _eventos_de_arremesso(shots: pl.DataFrame, rounds: pl.DataFrame) -> pl.DataFrame:
    """Os `weapon_fire` que são arremesso de granada -- o tick do CLIQUE."""
    if shots is None or shots.height == 0:
        return pl.DataFrame(
            schema={"round_num": pl.UInt32, "tick": pl.Int64,
                    "steamid": pl.UInt64, "kind": pl.String}
        )
    janela = rounds.select(["round_num", "freeze_end", "end"])
    return (
        shots.filter(pl.col("weapon").is_in(list(ARMA_DE_ARREMESSO)))
        .join(janela, on="round_num", how="inner")
        .filter((pl.col("tick") >= pl.col("freeze_end")) & (pl.col("tick") <= pl.col("end")))
        .select(
            pl.col("round_num"),
            pl.col("tick").cast(pl.Int64),
            pl.col("player_steamid").alias("steamid"),
            pl.col("weapon").replace_strict(ARMA_DE_ARREMESSO, default=None).alias("kind"),
        )
        .sort("tick")
    )


class _Ticks:
    """Acesso rápido a (posição, mira) de um jogador num tick.

    A tabela de ticks tem mais de um milhão de linhas e a ancoragem consulta
    dezenas de ticks por arremesso. Um filtro Polars por consulta seria lento o
    bastante para inviabilizar a varredura, então os dados de cada jogador vão
    para arrays contíguos indexados por deslocamento de tick.
    """

    def __init__(self, ticks: pl.DataFrame):
        self.por_jogador: dict[int, dict] = {}
        cols = ["tick", "X", "Y", "Z", "pitch", "yaw"]
        tem_walking = "is_walking" in ticks.columns
        if tem_walking:
            cols.append("is_walking")
        for (sid,), g in ticks.select(["steamid"] + cols).sort("tick").group_by(
            ["steamid"], maintain_order=True
        ):
            t = g["tick"].to_numpy()
            self.por_jogador[int(sid)] = {
                "t0": int(t[0]),
                "tick": t,
                "pos": np.stack([g["X"].to_numpy(), g["Y"].to_numpy(), g["Z"].to_numpy()], axis=-1).astype(float),
                "pitch": g["pitch"].to_numpy().astype(float),
                "yaw": g["yaw"].to_numpy().astype(float),
                "walking": g["is_walking"].to_numpy() if tem_walking else None,
                # os ticks de um jogador são contínuos (medido: diferença 1 em
                # todos), então o índice é o deslocamento direto
                "continuo": bool(np.all(np.diff(t) == 1)),
            }

    def indices(self, steamid: int, ticks: np.ndarray) -> np.ndarray | None:
        d = self.por_jogador.get(int(steamid))
        if d is None:
            return None
        if d["continuo"]:
            idx = ticks - d["t0"]
        else:
            idx = np.searchsorted(d["tick"], ticks)
            idx = np.clip(idx, 0, len(d["tick"]) - 1)
            if not np.all(d["tick"][idx] == ticks):
                return None
        if idx.size and (idx.min() < 0 or idx.max() >= len(d["tick"])):
            return None
        return idx


# ---------------------------------------------------------------------------
# A) Ancoragem do tick de soltura
# ---------------------------------------------------------------------------

def _candidatos_de_um_arremesso(
    tk: _Ticks, steamid: int, t_clique: int | None, t_primeiro: int, tickrate: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None:
    """Ticks candidatos e a geometria de cada um: posição dos pés e direção."""
    teto = int(MAX_JANELA_SEGUNDOS * tickrate)
    inicio = t_primeiro - teto if t_clique is None else max(t_clique - FOLGA_JANELA_TICKS, t_primeiro - teto)
    fim = t_primeiro + FOLGA_JANELA_TICKS
    if fim < inicio:
        return None

    ticks = np.arange(inicio, fim + 1, dtype=np.int64)
    idx = tk.indices(steamid, ticks)
    if idx is None:
        return None
    d = tk.por_jogador[int(steamid)]
    return ticks, d["pos"][idx], d["pitch"][idx], d["yaw"][idx]


def ancora_arremessos(
    lancamentos: list[dict], tk: _Ticks, tickrate: int, offset_mao: float | None = None
) -> tuple[list[dict], float]:
    """Acha o tick da soltura de cada arremesso e mede a altura dos olhos.

    Devolve os arremessos enriquecidos e o deslocamento da mão usado.

    O ajuste é feito em DOIS eixos separados, e a separação é o que torna o
    resíduo uma medida honesta de confiança:

    - **horizontal**: `(P0 - pés)_xy` tem que ser `d * direção_xy`. Aqui não
      entra a altura dos olhos, então o tick e `d` saem daqui sozinhos, sem
      nenhum parâmetro livre por arremesso. O resíduo horizontal é o que sobra.
    - **vertical**: com o tick já decidido, a altura dos olhos é o que resta,
      `(P0 - pés).z - d * direção_z`. Isso é MEDIÇÃO, não ajuste -- e é por isso
      que ela pode ser comparada com as 64 unidades que o projeto supõe.
    """
    grade = GRADE_OFFSET_MAO if offset_mao is None else np.array([float(offset_mao)])

    # pré-computa, por arremesso, o resíduo horizontal de cada (tick, offset)
    matrizes = []
    for a in lancamentos:
        cand = _candidatos_de_um_arremesso(
            tk, a["steamid"], a.get("tick_clique"), a["tick_primeiro"], tickrate
        )
        if cand is None:
            matrizes.append(None)
            continue
        ticks, pos, pitch, yaw = cand
        u = direcao_da_mira(pitch, yaw)
        # (P0 - pés) no plano, por tick
        w = a["p0"][None, :2] - pos[:, :2]
        # resíduo de cada combinação (tick, offset): |w - d*u_xy|
        dif = w[:, None, :] - grade[None, :, None] * u[:, None, :2]
        matrizes.append((ticks, pos, pitch, yaw, u, np.linalg.norm(dif, axis=2)))

    # o deslocamento da mão é GLOBAL: escolhe-se o que minimiza a mediana dos
    # melhores resíduos. Um valor por arremesso seria ajustar ruído.
    if offset_mao is None:
        medianas = []
        for m in matrizes:
            if m is None:
                continue
            medianas.append(m[5].min(axis=0))
        if medianas:
            melhor = np.median(np.stack(medianas), axis=0)
            offset = float(grade[int(np.argmin(melhor))])
            col = int(np.argmin(melhor))
        else:
            offset, col = 16.0, 0
    else:
        offset, col = float(grade[0]), 0

    saida = []
    for a, m in zip(lancamentos, matrizes):
        if m is None:
            saida.append({**a, "tick_soltura": None, "residuo": None, "altura_olhos": None})
            continue
        ticks, pos, pitch, yaw, u, res = m
        coluna = res[:, col]
        # Empate: quando o jogador está parado e a mira quieta, o resíduo é
        # plano na janela inteira e o argmin cai na borda por ruído. Entre os
        # ticks igualmente bons vence o mais próximo do primeiro sample do
        # projétil -- é lá que a soltura tem que estar.
        empatados = np.flatnonzero(coluna <= coluna.min() + TOLERANCIA_EMPATE_TICK)
        i = int(empatados[np.argmin(np.abs(ticks[empatados] - a["tick_primeiro"]))])
        t_sol = int(ticks[i])
        altura = float(
            a["p0"][2] - pos[i, 2] - offset * u[i, 2] - OFFSET_VERTICAL_SOLTURA
        )
        saida.append({
            **a,
            "tick_soltura": t_sol,
            "residuo": float(res[i, col]),
            "altura_olhos": altura,
            "pos_soltura": pos[i].copy(),
            "pitch": float(pitch[i]),
            "yaw": float(yaw[i]),
            "atraso_animacao_ticks": (
                None if a.get("tick_clique") is None else t_sol - int(a["tick_clique"])
            ),
        })
    return saida, offset


# ---------------------------------------------------------------------------
# C) Postura, movimento e giro de mira
# ---------------------------------------------------------------------------

def _estado_do_jogador(tk: _Ticks, steamid: int, tick: int, tickrate: int) -> dict:
    """Velocidade, estado no ar e giro de mira em torno do tick da soltura."""
    d = tk.por_jogador.get(int(steamid))
    vazio = {"velocidade": None, "velocidade_vertical": None, "giro": None, "andando": None}
    if d is None:
        return vazio
    idx = tk.indices(steamid, np.array([tick - 1, tick, tick + 1], dtype=np.int64))
    if idx is None:
        return vazio

    # diferença central: menos sensível a um tick de ruído que a diferença
    # para frente, e o projeto tem ticks contínuos, então ela sempre existe
    p_ant, p_pos = d["pos"][idx[0]], d["pos"][idx[2]]
    v = (p_pos - p_ant) / 2.0 * tickrate
    giro_yaw = abs(((d["yaw"][idx[2]] - d["yaw"][idx[0]] + 180) % 360) - 180) / 2.0 * tickrate
    giro_pitch = abs(d["pitch"][idx[2]] - d["pitch"][idx[0]]) / 2.0 * tickrate
    return {
        # o VETOR, e não só o módulo: a subtração da velocidade do jogador em
        # `velocidade_de_arremesso` é vetorial, e projetar o módulo na direção
        # do projétil superestima a correção de quem corria de lado
        "velocidade_vetor": v,
        "velocidade": float(np.linalg.norm(v[:2])),
        "velocidade_vertical": float(v[2]),
        "giro": float(np.hypot(giro_yaw, giro_pitch)),
        "andando": (None if d["walking"] is None else bool(d["walking"][idx[1]])),
    }


def classifica_postura(altura_olhos: float | None) -> str | None:
    """Agachado ou em pé, pela altura dos olhos MEDIDA.

    Por que não a flag do evento oficial: `user_ducking` do `grenade_thrown` é a
    TRANSIÇÃO de agachar, não a postura. Medido no corpus, ela fica ligada em
    trechos de ~12 ticks (190 ms) e não se correlaciona com a altura (66,3u com
    ela, 66,2u sem). Os campos de postura de verdade (`ducked`, `duck_amount`)
    existem na demo, mas o parser não os grava hoje -- em match_23 eles
    confirmam o agachado a 46u. Até lá, a postura vem da altura MEDIDA.
    """
    if altura_olhos is None or not (ALTURA_OLHOS_MIN <= altura_olhos <= ALTURA_OLHOS_MAX):
        return None
    return "agachado" if altura_olhos <= ALTURA_OLHOS_AGACHADO_MAX else "em pé"


def classifica_movimento(estado: dict) -> str | None:
    """Parado, andando ou correndo, com o mesmo limiar de 'parado' do projeto."""
    v = estado.get("velocidade")
    if v is None:
        return None
    if v < VELOCIDADE_PARADO:
        return "parado"
    if estado.get("andando"):
        return "andando"
    return "correndo"


# ---------------------------------------------------------------------------
# B) Força do arremesso
# ---------------------------------------------------------------------------

def velocidade_de_arremesso(
    traj: np.ndarray, ticks: np.ndarray, estado: dict, tickrate: int
) -> dict | None:
    """Velocidade inicial do projétil, bruta e RELATIVA ao jogador.

    Descontar a velocidade do jogador não é detalhe: a granada sai com a
    velocidade do arremesso MAIS a de quem arremessou, então o mesmo arremesso
    curto feito correndo mede mais rápido que feito parado. Sem o desconto, todo
    run-throw curto é classificado como arremesso longo.
    """
    if traj.shape[0] < 2:
        return None
    dt = (ticks[1] - ticks[0]) / tickrate
    if dt <= 0:
        return None
    v_projetil = (traj[1] - traj[0]) / dt

    # Subtração VETORIAL. Projetar o módulo da velocidade do jogador na direção
    # do projétil (o que uma primeira versão fazia) superestima a correção
    # sempre que o jogador não corria exatamente na direção do arremesso -- e
    # correr de lado enquanto joga a smoke é comum. A vertical entra junto:
    # granada jogada pulando herda também o impulso do pulo.
    v_jogador = estado.get("velocidade_vetor")
    if v_jogador is None:
        v_jogador = np.zeros(3)
    v_jogador = np.asarray(v_jogador, dtype=float)
    return {
        # a bruta fica guardada porque é ela que permite recalibrar o fator de
        # herança sem reprocessar tudo
        "bruta": float(np.linalg.norm(v_projetil)),
        "relativa": float(np.linalg.norm(v_projetil - FATOR_HERANCA * v_jogador)),
    }


def grupos_de_forca(velocidades: np.ndarray) -> list[tuple[float, int]]:
    """Agrupa as velocidades por moda e devolve (centro, tamanho), do menor ao maior.

    Moda e não bin de largura fixa, pelo motivo da decisão 5 do CLAUDE.md: uma
    velocidade caindo na borda de um bin tem os arremessos que a sustentam
    divididos entre dois bins e o grupo simplesmente some. Cada candidato aqui é
    centrado numa velocidade observada de verdade, então não existe borda
    artificial.

    Os grupos NÃO são rotulados aqui. Rotular "longo/médio/curto" é leitura de
    jogo e cabe ao Pedro conferir na distribuição -- mesmo princípio da decisão
    8 (o KMeans não nomeia os grupos).
    """
    restante = np.sort(np.asarray(velocidades, dtype=float))
    restante = restante[np.isfinite(restante)]
    grupos: list[tuple[float, int]] = []

    while restante.size >= MIN_ARREMESSOS_POR_FORCA:
        contagens = np.array([int((np.abs(restante - v) <= RAIO_GRUPO_FORCA).sum()) for v in restante])
        melhor = int(np.argmax(contagens))
        if contagens[melhor] < MIN_ARREMESSOS_POR_FORCA:
            break
        membros_mask = np.abs(restante - restante[melhor]) <= RAIO_GRUPO_FORCA
        membros = restante[membros_mask]
        grupos.append((float(membros.mean()), int(membros.size)))
        restante = restante[~membros_mask]

    return sorted(grupos)


# Rótulos dos grupos de força, do mais fraco para o mais forte. A ordem não é
# ambígua (menor velocidade = arremesso curto) e bate com os três jeitos de soltar
# a granada no CS2: botão direito (lob), os dois botões (médio), botão esquerdo
# (cheio). Confirmado pelo Pedro em 2026-09-26 (decisão 21a).
ROTULOS_FORCA = ("curto", "médio", "longo")
FORCA_CONFIRMADA = True

# Como soltar cada força no CS2 -- a correspondência do comentário acima, na
# forma que vai para a ficha do arremesso.
BOTAO_DA_FORCA = {"curto": "botão direito", "médio": "os dois botões", "longo": "botão esquerdo"}

# Decisão 21b: o comando de console só é afirmado depois que o Pedro rodar o
# teste no jogo (setpos + setang + soltar, e a granada cair onde a ficha diz).
# Até lá, toda ficha sai com o aviso de comando não conferido.
COMANDO_CONFERIDO_NO_JOGO = False


def comando_de_console(x: float, y: float, z: float, pitch: float, yaw: float) -> str:
    """O comando que põe o jogador na posição e no ângulo da soltura.

    `setpos` recebe a posição dos PÉS (a origem do jogador, que é o que a demo
    grava) e `setang` recebe pitch e yaw na convenção do jogo (decisão 9). Duas
    casas decimais: um centésimo de unidade e de grau está muito abaixo do que
    muda onde a granada cai.
    """
    return f"setpos {x:.2f} {y:.2f} {z:.2f}; setang {pitch:.2f} {yaw:.2f} 0"


def rotula_forca(velocidade: float | None, grupos: list[tuple[float, int]]) -> str | None:
    """Qual grupo de força aquela velocidade pertence.

    Com exatamente três grupos, o rótulo é curto/médio/longo pela ordem
    (ROTULOS_FORCA), marcado "(a confirmar)" enquanto FORCA_CONFIRMADA for falso.
    Com outro número de grupos a leitura por ordem não vale, e o rótulo continua
    NEUTRO ("força A/B/...", do mais fraco para o mais forte) -- chamar um grupo
    de "curto" sem essa correspondência seria inventar o dado.
    """
    if velocidade is None or not grupos:
        return None
    i = int(np.argmin([abs(velocidade - c) for c, _ in grupos]))
    if len(grupos) == len(ROTULOS_FORCA):
        return ROTULOS_FORCA[i] + ("" if FORCA_CONFIRMADA else " (a confirmar)")
    return f"força {chr(ord('A') + i)}"


# ---------------------------------------------------------------------------
# B2) A rotina de arremesso do jogo, medida no gabarito (item 7, rota A)
#
# Todas as constantes abaixo saem do GABARITO: propriedades que o jogo grava na
# demo (m_vInitialVelocity e m_vInitialPosition do projétil, m_flThrowStrength
# da arma, duck_amount, m_hGroundEntity, m_nLastJumpTick e
# m_flLastJumpVelocityZ do jogador), extraídas da match_23 -- a única demo que
# sobrou -- para `tests/fixtures/gabarito_arremessos_match_23.json.gz` (n = 434); desde
# 2026-09-27 o gabarito tem 12 partidas (tests/fixtures/gabarito_arremessos_*.json.gz).
# Nada aqui é encaixado nos grupos de velocidade: cada número é a medida direta
# de uma propriedade gravada. Decisão 21a do CLAUDE.md.
#
# O que é AFIRMADO (passou na própria meta no gabarito): o botão, "no ar" e a
# postura. O que NÃO é afirmado: a posição de saída (a cauda vertical depois de
# subir degrau não é explicada) e a velocidade calculada (entra só pelo botão,
# e só dentro da tolerância).
# ---------------------------------------------------------------------------

# Velocidade do lançamento por botão (m_flThrowStrength 0 / 0,5 / 1), |v0 - 1,25
# vj| no chão, IQR < 1 u/s. n = 11 / 30 / 289, match_23.
VELOCIDADE_BOTAO = {0.0: 202.5, 0.5: 438.7, 1.0: 675.0}
# Rótulo de cada botão: o botão direito lança curto, os dois botões médio, o
# esquerdo longo (a mesma correspondência de BOTAO_DA_FORCA).
ROTULO_DO_BOTAO = {0.0: "curto", 0.5: "médio", 1.0: "longo"}

# Constantes CALCULADAS do gabarito (nunca digitadas): `gabarito_constantes.json`,
# gerado por `py -3.12 -m scripts.constantes_do_gabarito`; um teste confere que o
# arquivo bate com o recálculo a partir de tests/fixtures/gabarito_arremessos_*.json.
_CONSTANTES_DO_GABARITO = json.loads(
    (Path(__file__).with_name("gabarito_constantes.json")).read_text(encoding="utf-8"))

# Tolerância do rótulo de botão: ceil(2 × p99) do erro da velocidade calculada
# contra m_vInitialVelocity, nos arremessos em que o modelo se aplica (origem e n
# no JSON; 21 u/s com a match_23, p99 10,06, n = 431). É a distância máxima da
# velocidade calculada ao CENTRO do botão para ele ser dado; fora dela o rótulo
# é NEUTRO. O erro do modelo é outra coisa: fica na catraca dos testes.
TOLERANCIA_BOTAO = float(_CONSTANTES_DO_GABARITO["tolerancia_botao"])

# Guarda do voo: o vetor inicial previsto (botão + herança) tem de explicar o
# primeiro segmento observado do projétil. Medido no gabarito, o primeiro
# segmento é a velocidade inicial gravada mais um deslocamento vertical fixo
# (a gravidade do primeiro tick: -7,51 u/s, mediana, n = 6.846). O resíduo
# |vp - (previsto + deslocamento)| acompanha o erro do vetor (correlação 0,999);
# acima do limiar o arremesso fica NEUTRO ("vetor incoerente com o voo"). O
# limiar é o meio do vão entre o maior resíduo dos vetores certos (erro < 5
# u/s) e o menor dos grosseiramente errados (erro acima da tolerância antes da
# guarda) -- calculado do gabarito, no JSON.
DESLOCAMENTO_PRIMEIRO_SEGMENTO = np.array([0.0, 0.0, float(_CONSTANTES_DO_GABARITO["deslocamento_primeiro_segmento_z"])])
LIMIAR_GUARDA_VOO = float(_CONSTANTES_DO_GABARITO["limiar_guarda_voo"])

# Direção do lançamento: o pitch da mira é remapeado POR TRECHOS. Parado, o
# resíduo contra o gabarito é 0,000° nos dois trechos (n = 92 parados).
FATOR_PITCH_NEGATIVO = 80.0 / 90.0
FATOR_PITCH_POSITIVO = 100.0 / 90.0
DESLOCAMENTO_PITCH = -10.0

# Ponto de saída: 16 u à frente na direção do lançamento (parado: 16,00 [15,99;
# 16,03], n = 74), a partir dos pés da tabela no tick da soltura.
AVANCO_SAIDA = 16.0
# Altura de saída acima dos pés, no chão: em pé 63,31 (botão 1, n = 272),
# agachado 45,55 (n = 16); cada meio botão abaixo tira 6 u (12 × (botão - 1):
# botão 0,5 mede 57,50, n = 30; botão 0 mede 51,21, n = 11).
ALTURA_SAIDA_EM_PE = 63.31
ALTURA_SAIDA_AGACHADO = 45.55
ALTURA_SAIDA_POR_BOTAO = 12.0
CORTE_POSTURA = (ALTURA_SAIDA_EM_PE + ALTURA_SAIDA_AGACHADO) / 2
# Faixa em torno do corte onde a postura NÃO é afirmada: da margem do agachado
# correto mais alto à do em pé correto mais baixo, calculadas do gabarito (JSON;
# com a match_23 ficam perto de -2,4 e +1,1 u). Só os agachamentos parciais
# caem nela. A hipótese "subida recente" foi testada e não é o que aproxima
# os casos do corte (decisão 21c).
FAIXA_POSTURA_NEUTRA = tuple(float(x) for x in _CONSTANTES_DO_GABARITO["faixa_postura_neutra"])

# "No ar": a segunda diferença da altura dos pés é a gravidade (-800 u/s², ou
# -0,1953 u/tick² a 64 tick) -- o resíduo de uma parábola com g fixo em três
# ticks. Tolerância 0,05 u/tick²: acerta m_hGroundEntity em 433/434 e os 9 de
# escada/rampa; 0,01 perde 10 casos e 0,1 marca chão plano como ar.
GRAVIDADE = 800.0
TOL_SEGUNDA_DIFERENCA = 0.05
# Janela de posição usada para achar a decolagem (a mesma do gabarito).
JANELA_DECOLAGEM_TICKS = 64

# Decolagem: velocidade vertical do pulo, moda de m_flLastJumpVelocityZ (298,868
# em pé; 301,993 no pulo agachado, 8% dos pulos, que a posição não separa: o
# erro máximo por usar 298,868 é 3,1 u/s na vertical, 3,9 na granada).
VZ_PULO = 298.868
# A parábola ajustada dá a vz de decolagem meio passo de gravidade abaixo da
# gravada (800/128 = 6,25; medido -6,22 na mediana, n = 95).
MEIO_PASSO_GRAVIDADE = 800.0 / 128.0
# Estimada + meio passo tem de ficar a até isto de VZ_PULO para ser um pulo
# limpo: p99 dos arremessos cuja velocidade o modelo acerta = 8,57 (n = 93),
# arredondado para cima. As parábolas quebradas ficam ~158 abaixo.
LIMITE_VZ_DECOLAGEM = 9.0
# Janela do jump-throw, em ticks entre decolagem e soltura:
#   0-5    neutro (sem gabarito; inclui soltar no tick do pulo)
#   6-13   vz herdada FIXA = decolagem - 0,1 s de gravidade (gabarito: 95 de 95)
#   14-18  neutro (sem gabarito; no corpus a vz fixa acerta 140 de 147)
#   19+    vz REAL (gabarito: 1 caso, 16:81; corpus: a vz real acerta todos os
#          arremessos com 20 ou mais ticks)
# Com a vz fixa, posição e velocidade horizontal são as do instante decolagem +
# 0,1 s (altura de saída 62,25 acima da parábola nesse instante, n = 88).
JANELA_REGRA_FIXA = (6, 13)
JANELA_VZ_REAL_MIN = 19
TEMPO_FIXO_DO_PULO = 0.1
# Subindo sem parábola formada (soltura no tick da decolagem, o caso r17 da
# match_09): vz de subida acima da maior medida no chão do gabarito (113,9 u/s,
# escada, n = 335) é estado vertical AMBÍGUO, neutro -- nunca tratado como chão.
VZ_SUBIDA_AMBIGUA = 114.0


def direcao_do_lancamento(pitch: float, yaw: float) -> np.ndarray:
    """Direção em que o jogo lança a granada (pitch remapeado por trechos)."""
    fator = FATOR_PITCH_NEGATIVO if pitch < 0 else FATOR_PITCH_POSITIVO
    p = np.radians(DESLOCAMENTO_PITCH + pitch * fator)
    y = np.radians(yaw)
    return np.array([np.cos(p) * np.cos(y), np.cos(p) * np.sin(y), -np.sin(p)])


def estado_vertical(z: np.ndarray, xy: np.ndarray, tickrate: int) -> dict:
    """O estado vertical do jogador na soltura, só com a posição dos pés.

    `z` e `xy`: pés na tabela de ticks de soltura-N até soltura+1 (o penúltimo
    é a soltura). Devolve `regra` (chão, regra fixa, vz real, ou o motivo de
    neutro), `no_ar` (None quando ambíguo), `vz` herdada (None = neutro), `vh`
    herdada, os ticks desde a decolagem e `z_ref`, a altura dos pés de
    referência para a saída, relativa aos pés na soltura.
    """
    z = np.asarray(z, dtype=float)
    xy = np.asarray(xy, dtype=float)
    n_pts = len(z)
    s = n_pts - 2
    v = np.array([(xy[s + 1, 0] - xy[s - 1, 0]) * tickrate / 2,
                  (xy[s + 1, 1] - xy[s - 1, 1]) * tickrate / 2,
                  (z[s + 1] - z[s - 1]) * tickrate / 2])
    base = {"vz_derivada": float(v[2]), "vh": v[:2], "ticks_desde_decolagem": None, "z_ref": 0.0}
    g_tick = -GRAVIDADE / tickrate ** 2
    d2 = z[2:] - 2 * z[1:-1] + z[:-2]          # d2[i] centrado em z[i+1]
    # a contagem começa na segunda diferença centrada em t-1 (i = s - 2): é a
    # convenção medida no gabarito -- com ela a decolagem estimada bate com a
    # gravada a < 0,003 tick e "no ar" acerta 433/434; começando em t, a
    # decolagem sai até 0,7 tick adiantada
    i = s - 2
    n = 0
    while i >= 0 and abs(d2[i] - g_tick) < TOL_SEGUNDA_DIFERENCA:
        n += 1
        i -= 1
    # soltura no tick de um pouso ou de uma decolagem: a mudança de estado
    # acontece dentro do tick (subtick) e a posição por tick não diz de que
    # lado ela caiu -- "no ar" INDETERMINADO por construção. A assinatura é a
    # TROCA entre queda livre e chão em volta da soltura: entre as segundas
    # diferenças centradas em t-2, t-1 e t, pelo menos uma é a gravidade e pelo
    # menos uma é anômala (nem chão ~0 nem gravidade). Degrau e chão irregular
    # dão anomalia sem a gravidade ao lado e continuam "chão".
    vizinhas = [d2[k] for k in (s - 3, s - 2, s - 1) if 0 <= k < len(d2)]
    tem_gravidade = any(abs(x - g_tick) < TOL_SEGUNDA_DIFERENCA for x in vizinhas)
    tem_anomalia = any(abs(x) >= TOL_SEGUNDA_DIFERENCA and abs(x - g_tick) >= TOL_SEGUNDA_DIFERENCA for x in vizinhas)
    transicao = tem_gravidade and tem_anomalia
    if n == 0:
        if v[2] > VZ_SUBIDA_AMBIGUA:
            return {**base, "regra": "ambíguo: subindo sem parábola", "no_ar": None, "vz": None}
        return {**base, "regra": "chão", "no_ar": None if transicao else False, "vz": 0.0}
    k0 = s - n                                  # primeiro ponto da parábola
    tau = (np.arange(k0, n_pts) - s) / tickrate
    b, c = np.polyfit(tau, z[k0:] + GRAVIDADE / 2 * tau ** 2, 1)
    disc = None if k0 < 1 else b * b - 2 * GRAVIDADE * (z[k0 - 1] - c)
    if disc is None or disc < 0:
        return {**base, "regra": "ambíguo: queda sem decolagem na janela", "no_ar": None, "vz": None}
    tau_dec = (b - np.sqrt(disc)) / GRAVIDADE
    vz_dec = b - GRAVIDADE * tau_dec
    base = {**base, "ticks_desde_decolagem": float(-tau_dec * tickrate)}
    if abs(vz_dec + MEIO_PASSO_GRAVIDADE - VZ_PULO) > LIMITE_VZ_DECOLAGEM:
        return {**base, "regra": "ambíguo: parábola sem pulo limpo", "no_ar": None, "vz": None}
    t = round(-tau_dec * tickrate)
    if t < JANELA_REGRA_FIXA[0]:
        return {**base, "regra": "janela 0-5 (sem gabarito)", "no_ar": True, "vz": None}
    if t <= JANELA_REGRA_FIXA[1]:
        t01 = tau_dec + TEMPO_FIXO_DO_PULO
        # velocidade horizontal e altura dos pés no instante decolagem + 0,1 s
        k = s + t01 * tickrate - 0.5
        i0 = int(np.floor(k))
        f = k - i0
        vh = v[:2]
        if 1 <= i0 < n_pts - 2:
            va = (xy[i0 + 1] - xy[i0 - 1]) * tickrate / 2
            vb = (xy[i0 + 2] - xy[i0]) * tickrate / 2
            vh = va * (1 - f) + vb * f
        z_ref = (c + b * t01 - GRAVIDADE / 2 * t01 ** 2) - z[s]
        return {**base, "regra": "regra fixa 6-13", "no_ar": True,
                "vz": VZ_PULO - GRAVIDADE * TEMPO_FIXO_DO_PULO, "vh": vh, "z_ref": float(z_ref)}
    if t < JANELA_VZ_REAL_MIN:
        return {**base, "regra": "janela 14-18 (sem gabarito)", "no_ar": True, "vz": None}
    return {**base, "regra": "vz real 19+", "no_ar": True, "vz": float(v[2])}


def botao_da_velocidade(velocidade: float | None, tolerancia: float | None = None) -> float | None:
    """O botão (0, 0,5 ou 1) cuja velocidade medida está a até a tolerância."""
    if velocidade is None or not np.isfinite(velocidade):
        return None
    tol = TOLERANCIA_BOTAO if tolerancia is None else tolerancia
    b = min(VELOCIDADE_BOTAO, key=lambda k: abs(VELOCIDADE_BOTAO[k] - velocidade))
    return b if abs(VELOCIDADE_BOTAO[b] - velocidade) <= tol else None


def altura_de_saida(z_saida: float, z_pes_ref: float, u_z: float, botao: float) -> float:
    """Altura do ponto de saída acima dos pés de referência, sem o avanço de 16 u
    e corrigida para o botão 1 -- comparável direto com em pé e agachado."""
    return float(z_saida - z_pes_ref - AVANCO_SAIDA * u_z - ALTURA_SAIDA_POR_BOTAO * (botao - 1.0))


def postura_da_altura(h: float | None, faixa: tuple[float, float] | None = None) -> str | None:
    """Em pé ou agachado pela altura de saída; None na faixa sem afirmação."""
    if h is None or not np.isfinite(h):
        return None
    lo, hi = FAIXA_POSTURA_NEUTRA if faixa is None else faixa
    d = h - CORTE_POSTURA
    if lo <= d <= hi and (lo, hi) != (0.0, 0.0):
        return None
    return "em pé" if d > 0 else "agachado"


def rotina_do_jogo(z: np.ndarray, xy: np.ndarray, vp: np.ndarray, z_saida: float,
                   pitch: float, yaw: float, tickrate: int,
                   tolerancia: float | None = None, faixa_postura: tuple[float, float] | None = None,
                   limiar_voo: float | None = None) -> dict:
    """Botão, "no ar" e postura de UM arremesso pela rotina medida.

    `vp` é a velocidade do projétil pelos dois primeiros pontos e `z_saida` a
    altura do primeiro ponto levado ao tick da soltura. Postura só onde a
    altura de saída foi medida: no chão e na janela da vz fixa.
    """
    ev = estado_vertical(z, xy, tickrate)
    out = {"estado_vertical": ev["regra"], "no_ar": ev["no_ar"],
           "ticks_desde_decolagem": ev["ticks_desde_decolagem"],
           "velocidade_arremesso": None, "botao": None, "altura_saida": None, "postura": None,
           "residuo_voo": None}
    if ev["vz"] is None:
        return out
    vj = np.array([ev["vh"][0], ev["vh"][1], ev["vz"]])
    rel = float(np.linalg.norm(np.asarray(vp, dtype=float) - FATOR_HERANCA * vj))
    b = botao_da_velocidade(rel, tolerancia)
    if b is not None:
        u = direcao_do_lancamento(pitch, yaw)
        previsto = VELOCIDADE_BOTAO[b] * u + FATOR_HERANCA * vj + DESLOCAMENTO_PRIMEIRO_SEGMENTO
        residuo = float(np.linalg.norm(np.asarray(vp, dtype=float) - previsto))
        out["residuo_voo"] = residuo
        if residuo > (LIMIAR_GUARDA_VOO if limiar_voo is None else limiar_voo):
            out["estado_vertical"] = "vetor incoerente com o voo"
            return out
    out.update(velocidade_arremesso=rel, botao=b)
    if b is not None and ev["regra"] in ("chão", "regra fixa 6-13"):
        u = direcao_do_lancamento(pitch, yaw)
        z_pes = np.asarray(z, dtype=float)[-2] + ev["z_ref"]
        h = altura_de_saida(z_saida, z_pes, u[2], b)
        out.update(altura_saida=h, postura=postura_da_altura(h, faixa_postura))
    return out


# ---------------------------------------------------------------------------
# D) Colisões na trajetória
# ---------------------------------------------------------------------------

def colisoes(traj: np.ndarray, ticks: np.ndarray, tickrate: int) -> list[int]:
    """Índices dos samples em que a granada bateu em alguma coisa.

    Critério: mudança brusca de direção do vetor velocidade entre samples
    consecutivos. Em voo livre a gravidade curva a trajetória poucos graus por
    tick; uma virada de dezenas de graus num tick é parede, chão ou caixote.

    Vale o esforço porque é o que separa arremessos que de cima parecem iguais, e
    porque uma trajetória com três colisões avisa na hora que aquele arremesso é
    sensível à posição de origem -- errar 20 unidades muda tudo.
    """
    if traj.shape[0] < 3:
        return []
    dt = np.diff(ticks) / tickrate
    dt[dt == 0] = 1.0 / tickrate
    v = np.diff(traj, axis=0) / dt[:, None]
    normas = np.linalg.norm(v, axis=1)

    out = []
    for i in range(len(v) - 1):
        if normas[i] < VELOCIDADE_MINIMA_COLISAO or normas[i + 1] < VELOCIDADE_MINIMA_COLISAO:
            continue
        cos = float(np.dot(v[i], v[i + 1]) / (normas[i] * normas[i + 1]))
        if np.degrees(np.arccos(np.clip(cos, -1.0, 1.0))) >= ANGULO_COLISAO_GRAUS:
            out.append(i + 1)
    return out


# ---------------------------------------------------------------------------
# Montagem
# ---------------------------------------------------------------------------

def _lancamentos_crus(traj: pl.DataFrame, eventos: pl.DataFrame) -> list[dict]:
    """Um dicionário por projétil, já casado com o clique que o originou."""
    fogo: dict[tuple[int, int], list[int]] = {}
    for e in eventos.iter_rows(named=True):
        fogo.setdefault((int(e["round_num"]), int(e["steamid"])), []).append(int(e["tick"]))

    out = []
    for (rn, eid), g in traj.group_by(["round_num", "entity_id"], maintain_order=True):
        ticks = g["tick"].to_numpy().astype(np.int64)
        pontos = np.stack(
            [g["X"].to_numpy(), g["Y"].to_numpy(), g["Z"].to_numpy()], axis=-1
        ).astype(float)
        sid = int(g["thrower_steamid"][0])

        # o clique é o último `weapon_fire` daquele jogador antes do primeiro
        # sample do projétil
        candidatos = [t for t in fogo.get((int(rn), sid), []) if t <= int(ticks[0])]
        out.append({
            "round_num": int(rn),
            "entity_id": int(eid),
            "steamid": sid,
            "thrower": g["thrower"][0],
            "kind": GRENADE_KIND[g["grenade_type"][0]],
            "tick_clique": max(candidatos) if candidatos else None,
            "tick_primeiro": int(ticks[0]),
            "ticks": ticks,
            "traj": pontos,
            "p0": pontos[0],
        })
    return out


# Janela para casar um projétil com o evento oficial de arremesso: o evento vem
# antes (ou no mesmo tick) do primeiro sample. 1,5 s é a mesma janela máxima da
# ancoragem; medido, o evento cai no tick do primeiro sample em 100% dos casos.
JANELA_EVENTO_OFICIAL_S = 1.5

# Nome da arma no evento oficial -> tipo de granada do projeto.
ARMA_DO_EVENTO = {"smokegrenade": "smoke", "flashbang": "flash", "hegrenade": "he",
                  "molotov": "molotov", "incgrenade": "molotov", "decoy": "decoy"}


# Demo SEM o evento `grenade_thrown` (as de FACEIT): o evento é RECONSTRUÍDO do
# projétil. Medido nas 43 partidas que têm o evento (20.863 solturas): o tick do
# evento é o do primeiro ponto do projétil em 100%, e a mira e os pés do evento
# são os da tabela de ticks em t-1 em 100% (20.862; 1 sem o tick). A ancoragem,
# que era a fonte do tick nessas demos, acerta o tick em só 41%.
# `scripts/investiga_faceit.py` e `tests/test_tick_pelo_projetil.py`.
# DESLIGADA até o Pedro aprovar: ligá-la muda o que dois testes existentes de
# test_grenade_throws.py afirmam ("sem evento, a ancoragem continua valendo" e
# "a ancoragem acha o tick da soltura"), e exige subir VERSAO_DAS_METRICAS,
# reprocessar e regerar a biblioteca (medido: piora 0, 447 botões a mais, 2.390
# comandos da FACEIT mudam).
TICK_PELO_PROJETIL_SEM_EVENTO = False


def evento_pelo_projetil(ancorados: list[dict], tk: "_Ticks") -> pl.DataFrame:
    """O `grenade_thrown` que a demo teria gravado, reconstruído das tabelas."""
    nome = {}
    for arma, kind in ARMA_DO_EVENTO.items():
        nome.setdefault(kind, arma)
    linhas = []
    for a in ancorados:
        t = int(a["tick_primeiro"])
        i = tk.indices(a["steamid"], np.array([t - 1], dtype=np.int64))
        d = tk.por_jogador.get(int(a["steamid"]))
        if i is None or d is None or a["kind"] not in nome:
            continue
        linhas.append({"tick": t, "user_steamid": int(a["steamid"]), "weapon": nome[a["kind"]],
                       "user_X": float(d["pos"][i[0]][0]), "user_Y": float(d["pos"][i[0]][1]),
                       "user_Z": float(d["pos"][i[0]][2]), "user_pitch": float(d["pitch"][i[0]]),
                       "user_yaw": float(d["yaw"][i[0]]), "user_ducking": None})
    esquema = {"tick": pl.Int64, "user_steamid": pl.UInt64, "weapon": pl.Utf8, "user_X": pl.Float64,
               "user_Y": pl.Float64, "user_Z": pl.Float64, "user_pitch": pl.Float64, "user_yaw": pl.Float64,
               "user_ducking": pl.Boolean}
    return pl.DataFrame(linhas, schema=esquema)


def aplica_tick_oficial(
    ancorados: list[dict], oficial: pl.DataFrame | None, tickrate: int, fonte: str = "oficial"
) -> tuple[list[dict], float | None]:
    """Troca o tick da ancoragem pelo tick do evento `grenade_thrown`, quando há.

    A geometria da soltura (posição dos pés, pitch e yaw) sai do PRÓPRIO evento,
    que a grava no tick oficial.

    Com o tick fixado, o deslocamento entre olhos e primeiro ponto do projétil é
    medido POR ARREMESSO (`avanco_na_mira`), não global. Medido no corpus: no
    tick oficial o deslocamento fica TODO na direção da mira (resíduo
    perpendicular mediano de 0,01u, p90 0,28u) e o tamanho dele cresce com a
    força do arremesso (17u a 100 u/s, 34u a 900 u/s) -- a granada já andou um
    pedaço quando aparece. Um offset global transformava essa variação em
    "resíduo" e em erro de altura. Não é parâmetro livre escondendo erro: a
    ancoragem precisava do offset global porque o tick era a incógnita; aqui o
    tick é dado, e a direção é a verificação.

    Por isso, com tick oficial, `residuo` é a distância PERPENDICULAR à mira: é
    ela que diz se pitch/yaw do evento explicam o ponto observado.

    Devolve os arremessos e a mediana do avanço na mira (None se a demo não tem o
    evento), que substitui o offset global no resumo.
    """
    if oficial is None or oficial.height == 0 or "user_steamid" not in oficial.columns:
        return [{**a, "fonte_tick": "ancoragem"} for a in ancorados], None

    ofi = oficial.with_columns(
        pl.col("weapon").replace_strict(ARMA_DO_EVENTO, default=None).alias("kind"))
    por_jog: dict[tuple[int, str], list[dict]] = {}
    for e in ofi.iter_rows(named=True):
        if e["kind"] is not None and e["user_steamid"] is not None:
            por_jog.setdefault((int(e["user_steamid"]), e["kind"]), []).append(e)

    janela = int(JANELA_EVENTO_OFICIAL_S * tickrate)
    usados: set[int] = set()
    casados = []  # (índice do arremesso, evento, w, u)
    for i, a in enumerate(ancorados):
        cands = [e for e in por_jog.get((int(a["steamid"]), a["kind"]), [])
                 if 0 <= a["tick_primeiro"] - int(e["tick"]) <= janela and id(e) not in usados]
        if not cands:
            continue
        e = max(cands, key=lambda x: int(x["tick"]))  # o último arremesso antes do projétil
        usados.add(id(e))
        # o projétil é levado de volta até o tick oficial pela velocidade inicial
        # (medido: 0 tick de distância em 100% dos casos, então isto é seguro, não
        # uma correção que muda número)
        dt = (a["tick_primeiro"] - int(e["tick"])) / tickrate
        p0 = a["p0"]
        if dt and len(a["ticks"]) >= 2:
            v0 = (a["traj"][1] - a["traj"][0]) / ((a["ticks"][1] - a["ticks"][0]) / tickrate)
            p0 = p0 - v0 * dt
        pes = np.array([e["user_X"], e["user_Y"], e["user_Z"]], dtype=float)
        u = direcao_da_mira(np.array([float(e["user_pitch"])]), np.array([float(e["user_yaw"])]))[0]
        casados.append((i, e, p0 - pes, u, pes))

    if not casados:
        return [{**a, "fonte_tick": "ancoragem"} for a in ancorados], None

    saida = [{**a, "fonte_tick": "ancoragem"} for a in ancorados]
    avancos = []
    for i, e, w, u, pes in casados:
        a = saida[i]
        norma = float(np.linalg.norm(u[:2]))
        if norma < 1e-6:  # mira na vertical: a projeção horizontal não diz nada
            continue
        avanco = float(w[:2] @ u[:2]) / norma ** 2
        avancos.append(avanco)
        residuo = float(np.linalg.norm(w[:2] - avanco * u[:2]))
        saida[i] = {
            **a,
            "tick_soltura_ancoragem": a.get("tick_soltura"),
            "delta_ancoragem_ticks": (None if a.get("tick_soltura") is None
                                      else int(a["tick_soltura"]) - int(e["tick"])),
            "tick_soltura": int(e["tick"]),
            "residuo": residuo,
            "altura_olhos": float(w[2] - avanco * u[2] - OFFSET_VERTICAL_SOLTURA),
            "avanco_na_mira": avanco,
            "pos_soltura": pes,
            "pitch": float(e["user_pitch"]),
            "yaw": float(e["user_yaw"]),
            # a flag `ducking` do evento marca a TRANSIÇÃO de agachar (dura
            # ~190 ms), não a postura: medido, fica ligada em 6-9% dos arremessos
            # em qualquer faixa de altura. Vai para a tabela como informação, e a
            # postura continua saindo da altura medida.
            "em_transicao_de_agachar": (None if e.get("user_ducking") is None and fonte != "oficial"
                                        else bool(e.get("user_ducking"))),
            "atraso_animacao_ticks": (None if a.get("tick_clique") is None
                                      else int(e["tick"]) - int(a["tick_clique"])),
            "fonte_tick": fonte,
        }
    return saida, (float(np.median(avancos)) if avancos else None)


def _janela_de_pes(tk: _Ticks, steamid: int, tick: int) -> tuple[np.ndarray, np.ndarray] | None:
    """Pés do jogador na tabela de ticks de soltura-64 (ou do primeiro tick dele)
    até soltura+1: (z, xy). None se não há o tick seguinte ou pontos mínimos."""
    d = tk.por_jogador.get(int(steamid))
    if d is None:
        return None
    ini = max(int(tick) - JANELA_DECOLAGEM_TICKS, int(d["tick"][0]))
    idx = tk.indices(steamid, np.arange(ini, int(tick) + 2, dtype=np.int64))
    if idx is None or len(idx) < 3:
        return None
    pos = d["pos"][idx]
    return pos[:, 2], pos[:, :2]


def botao_da_forca_lida(forca: float | None) -> float | None:
    """O botão (0, 0,5 ou 1) de uma m_flThrowStrength lida: o mais próximo.

    A força lida não é sempre 0 / 0,5 / 1: há valores de transição entre
    botões (0,48, 0,52, 0,59...). É a mesma convenção do gabarito da rota A
    (round(2·força)/2). Medido nos parados do gabarito (n = 1.200): 29 das 30
    forças intermediárias saíram EXATAMENTE na velocidade do botão mais
    próximo; 1 (0,6141) saiu a 492,65 u/s, entre dois botões -- a força crua
    vai junto na saída (`forca_lida`) para isso ficar visível.
    """
    if forca is None or not np.isfinite(forca):
        return None
    return float(round(float(forca) * 2) / 2)


def postura_lida(ducked: bool | None, duck_amount: float | None) -> str | None:
    """Postura pelo que a demo grava: m_bDucked = agachado, duck_amount 0 = em
    pé; agachamento parcial (entre os dois, sem m_bDucked) não é afirmado."""
    if ducked is None and duck_amount is None:
        return None
    if ducked:
        return "agachado"
    if duck_amount is not None and float(duck_amount) == 0.0:
        return "em pé"
    return None


def _verdade_da_demo(tables: dict[str, pl.DataFrame], chaves: list[tuple[int, int]]) -> tuple[dict, dict]:
    """(arremessos lidos por (entity_id, tick), movimento por (tick, steamid)).

    Vazio quando o interim não tem as tabelas da rota B (partidas sem .dem): aí
    tudo sai INFERIDO, e a saída diz isso."""
    arr, mov = tables.get("arremessos_demo"), tables.get("movimento")
    lidos = {} if arr is None else {(int(r["entity_id"]), int(r["tick"])): r for r in arr.iter_rows(named=True)}
    movs = {}
    if mov is not None and chaves:
        alvo = pl.DataFrame(chaves, schema={"tick": pl.Int64, "steamid": pl.UInt64}, orient="row")
        sub = mov.with_columns(pl.col("tick").cast(pl.Int64), pl.col("steamid").cast(pl.UInt64)).join(
            alvo, on=["tick", "steamid"], how="semi")
        movs = {(int(r["tick"]), int(r["steamid"])): r for r in sub.iter_rows(named=True)}
    return lidos, movs


def grenade_throws(
    tables: dict[str, pl.DataFrame], tickrate: int
) -> tuple[pl.DataFrame, dict]:
    """Contrato do projeto: `(per_round, summary)`.

    `per_round` tem uma linha por arremesso; `summary` traz o que a ancoragem
    mediu no corpus daquela partida (offset da mão, resíduos, alturas de olho,
    grupos de força) -- é o que sustenta ou derruba a confiança na ficha.
    """
    rounds = tables["rounds"]
    traj = trajetorias(tables.get("grenades"), rounds)
    if traj.height == 0:
        return pl.DataFrame(), {"arremessos": 0}

    eventos = _eventos_de_arremesso(tables.get("shots"), rounds)
    tk = _Ticks(tables["ticks"])
    crus = _lancamentos_crus(traj, eventos)
    ancorados, offset = ancora_arremessos(crus, tk, tickrate)
    oficial, fonte = tables.get("grenade_thrown"), "oficial"
    if TICK_PELO_PROJETIL_SEM_EVENTO and (oficial is None or oficial.height == 0):
        oficial, fonte = evento_pelo_projetil(ancorados, tk), "projetil"
    ancorados, offset_oficial = aplica_tick_oficial(ancorados, oficial, tickrate, fonte)

    lidos, movs = _verdade_da_demo(tables, [(int(a["tick_soltura"]), int(a["steamid"]))
                                            for a in ancorados if a["tick_soltura"] is not None])
    linhas = []
    for a in ancorados:
        estado = (
            _estado_do_jogador(tk, a["steamid"], a["tick_soltura"], tickrate)
            if a["tick_soltura"] is not None
            else {}
        )
        vel = velocidade_de_arremesso(a["traj"], a["ticks"], estado, tickrate) or {}
        bate = colisoes(a["traj"], a["ticks"], tickrate)
        # a rotina do jogo (rota A): botão, "no ar" e postura medidos no gabarito
        rotina = {"estado_vertical": None, "no_ar": None, "ticks_desde_decolagem": None,
                  "velocidade_arremesso": None, "botao": None, "altura_saida": None, "postura": None}
        pes_t = None
        saida = None
        janela = None if a["tick_soltura"] is None else _janela_de_pes(tk, a["steamid"], a["tick_soltura"])
        if janela is not None and a["traj"].shape[0] >= 2 and a.get("pitch") is not None:
            z, xy = janela
            # os pés no TICK DA SOLTURA na tabela (o jogo usa esses; os do evento
            # oficial são os do tick anterior -- decisão 5 do item 7)
            pes_t = np.array([xy[-2, 0], xy[-2, 1], z[-2]], dtype=float)
            dt = (a["ticks"][1] - a["ticks"][0]) / tickrate
            vp = (a["traj"][1] - a["traj"][0]) / dt
            z_saida = float(a["traj"][0][2] - vp[2] * (a["tick_primeiro"] - a["tick_soltura"]) / tickrate)
            rotina = rotina_do_jogo(z, xy, vp, z_saida, a["pitch"], a["yaw"], tickrate)
            # ponto de nascimento INFERIDO: o primeiro ponto do projétil já é o
            # nascimento + UM tick de voo (medido contra m_vInitialPosition: o
            # resto de traj[0] - v0/64 é 0,04 u, n = 1.370, match_23 e
            # match_42). A rotina acima segue com o z_saida da rota A, sem
            # esse recuo: as constantes dela foram medidas nessa convenção.
            saida = a["traj"][0] - vp * (a["tick_primeiro"] - a["tick_soltura"] + 1) / tickrate
        elif a["tick_soltura"] is not None and a.get("pos_soltura") is not None:
            # sem janela CONTÍNUA de ticks (a demo às vezes pula um tick: match_16,
            # round 5) a rotina não se aplica -- neutro com o motivo declarado.
            # Os pés ficam os da tabela no tick da soltura, se ele existe; senão,
            # os do evento (tick anterior).
            rotina["estado_vertical"] = "neutro: ticks faltando na janela"
            um = tk.indices(a["steamid"], np.array([int(a["tick_soltura"])], dtype=np.int64))
            d_ = tk.por_jogador.get(int(a["steamid"]))
            pes_t = (d_["pos"][um[0]].astype(float) if um is not None and d_ is not None
                     else np.asarray(a["pos_soltura"], dtype=float))
        # ROTA B: o que a demo grava vence o inferido, arremesso a arremesso e
        # campo a campo, e cada campo DIZ de onde veio (nunca misturar em silêncio)
        ts = a["tick_soltura"]
        lido = None if ts is None else lidos.get((int(a["entity_id"]), int(ts)))
        mv = None if ts is None else movs.get((int(ts), int(a["steamid"])))
        forca_lida = None if lido is None else lido["forca"]
        b_lido = botao_da_forca_lida(forca_lida)
        botao, fonte_botao = (b_lido, "lido") if b_lido is not None else (rotina["botao"], "inferido")
        p_lida = None if mv is None else postura_lida(mv["ducked"], mv["duck_amount"])
        tem_postura = mv is not None and (mv["ducked"] is not None or mv["duck_amount"] is not None)
        postura, fonte_postura = (p_lida, "lido") if tem_postura else (rotina["postura"], "inferido")
        tem_chao = mv is not None and mv["no_chao"] is not None
        no_ar, fonte_no_ar = (not mv["no_chao"], "lido") if tem_chao else (rotina["no_ar"], "inferido")
        tem_p0 = lido is not None and lido["p0_x"] is not None
        if tem_p0:
            saida, fonte_origem = np.array([lido["p0_x"], lido["p0_y"], lido["p0_z"]], dtype=float), "lido"
        else:
            fonte_origem = "inferido" if saida is not None else None
        linhas.append({
            "round_num": a["round_num"],
            "entity_id": a["entity_id"],
            "steamid": a["steamid"],
            "thrower": a["thrower"],
            "kind": a["kind"],
            "tick_clique": a["tick_clique"],
            "tick_soltura": a["tick_soltura"],
            "fonte_tick": a.get("fonte_tick"),
            "tick_soltura_ancoragem": a.get("tick_soltura_ancoragem"),
            "delta_ancoragem_ticks": a.get("delta_ancoragem_ticks"),
            "avanco_na_mira": a.get("avanco_na_mira"),
            "em_transicao_de_agachar": a.get("em_transicao_de_agachar"),
            "atraso_animacao_ticks": a.get("atraso_animacao_ticks"),
            "residuo": a["residuo"],
            "altura_olhos": a["altura_olhos"],
            # AFIRMADOS pela rotina do jogo (None = neutro, com o motivo em
            # estado_vertical ou pela tolerância / faixa de postura)
            "postura": postura,
            "botao": botao,
            "forca": None if botao is None else ROTULO_DO_BOTAO[botao],
            "forca_lida": None if forca_lida is None else float(forca_lida),
            "fonte_do_botao": fonte_botao,
            "fonte_da_postura": fonte_postura,
            "fonte_do_no_ar": fonte_no_ar,
            "fonte_da_origem": fonte_origem,
            # ponto de nascimento da granada: m_vInitialPosition (lido) ou o
            # primeiro ponto do projétil levado ao tick da soltura (inferido)
            "x_saida": None if saida is None else float(saida[0]),
            "y_saida": None if saida is None else float(saida[1]),
            "z_saida": None if saida is None else float(saida[2]),
            "estado_vertical": rotina["estado_vertical"],
            "ticks_desde_decolagem": rotina["ticks_desde_decolagem"],
            "altura_saida": rotina["altura_saida"],
            "pitch": a.get("pitch"),
            "yaw": a.get("yaw"),
            "x": None if pes_t is None else float(pes_t[0]),
            "y": None if pes_t is None else float(pes_t[1]),
            "z": None if pes_t is None else float(pes_t[2]),
            "velocidade_jogador": estado.get("velocidade"),
            "velocidade_vertical": estado.get("velocidade_vertical"),
            "giro_na_soltura": estado.get("giro"),
            "movimento": classifica_movimento(estado),
            "no_ar": no_ar,
            "tick_primeiro": a["tick_primeiro"],
            "velocidade_bruta": vel.get("bruta"),
            # ESTIMADA: a velocidade relativa pela rotina do jogo (None quando o
            # estado vertical é neutro). Não é afirmada; entra só pelo botão.
            "velocidade_arremesso": rotina["velocidade_arremesso"],
            "n_colisoes": len(bate),
            "colisoes": bate,
            "n_samples": int(a["traj"].shape[0]),
            # onde o projétil parou de ser observado: é onde a smoke abre, a
            # molotov queima e a flash/HE explode (o projétil some na detonação)
            "x_final": float(a["traj"][-1][0]),
            "y_final": float(a["traj"][-1][1]),
            "z_final": float(a["traj"][-1][2]),
        })

    for linha in linhas:
        motivo = motivo_aproximado(linha)
        linha["motivo_aproximado"] = motivo
        linha["reproducao_exata"] = motivo is None

    per_round = pl.DataFrame(linhas, infer_schema_length=None).sort(["round_num", "tick_soltura"])
    return per_round, resumo_de_ancoragem(per_round, offset, offset_oficial)


def motivo_aproximado(linha: dict) -> str | None:
    """Por que aquele arremesso NÃO pode afirmar reprodução exata -- ou None.

    Existe porque um lineup errado é pior que nenhum lineup: o cara treina o
    arremesso errado e leva para o jogo. Então o que não fecha é declarado, com
    o motivo, em vez de sair um `setpos` silenciosamente impreciso.
    """
    if linha.get("tick_soltura") is None:
        return "não foi possível ancorar o tick da soltura"
    r = linha.get("residuo")
    if r is not None and r > MAX_RESIDUO_ANCORAGEM:
        if linha.get("fonte_tick") == "oficial":
            return f"a mira do evento oficial passa a {r:.1f}u do ponto observado da granada"
        if linha.get("fonte_tick") == "projetil":
            return f"a mira no tick do projétil passa a {r:.1f}u do ponto observado da granada"
        return f"a ancoragem ficou a {r:.1f}u do ponto observado da granada"
    g = linha.get("giro_na_soltura")
    if g is not None and g > MAX_GIRO_NA_SOLTURA:
        return f"a mira girava a {g:.0f}°/s na soltura, e um tick de erro vira muitos graus"
    h = linha.get("altura_olhos")
    if h is not None and not (ALTURA_OLHOS_MIN <= h <= ALTURA_OLHOS_MAX):
        return f"a altura de olhos derivada ({h:.0f}u) está fora do fisicamente plausível"
    return None


def resumo_de_ancoragem(per_round: pl.DataFrame, offset_mao: float,
                        offset_mao_oficial: float | None = None) -> dict:
    """O que a ancoragem mediu -- é este resumo que decide se dá para confiar.

    Com o evento oficial, inclui a qualidade da ancoragem CONTRA ele: é a medida
    do método para o dia em que uma demo não trouxer o evento.
    """
    if per_round.height == 0:
        return {"arremessos": 0}

    res = per_round["residuo"].drop_nulls().to_numpy()
    alt = per_round["altura_olhos"].drop_nulls().to_numpy()
    alt = alt[(alt >= ALTURA_OLHOS_MIN) & (alt <= ALTURA_OLHOS_MAX)]
    vel = per_round["velocidade_arremesso"].drop_nulls().to_numpy()
    atraso = per_round["atraso_animacao_ticks"].drop_nulls().to_numpy()

    em_pe = alt[alt > ALTURA_OLHOS_AGACHADO_MAX]
    agachado = alt[alt <= ALTURA_OLHOS_AGACHADO_MAX]

    return {
        "arremessos": per_round.height,
        "offset_mao": offset_mao,
        "residuo_mediano": float(np.median(res)) if res.size else None,
        "residuo_p90": float(np.percentile(res, 90)) if res.size else None,
        "convergiram": int((res <= MAX_RESIDUO_ANCORAGEM).sum()),
        "taxa_convergencia": float((res <= MAX_RESIDUO_ANCORAGEM).mean()) if res.size else None,
        "altura_olhos_em_pe": float(np.median(em_pe)) if em_pe.size else None,
        "altura_olhos_agachado": float(np.median(agachado)) if agachado.size else None,
        "n_em_pe": int(em_pe.size),
        "n_agachado": int(agachado.size),
        "atraso_animacao_mediano": float(np.median(atraso)) if atraso.size else None,
        "grupos_de_forca": grupos_de_forca(vel),
        "reproducao_exata": int(per_round["reproducao_exata"].sum()),
        "aproximados": int((~per_round["reproducao_exata"]).sum()),
        "avanco_na_mira_mediano": offset_mao_oficial,
        "ancoragem_vs_oficial": _ancoragem_vs_oficial(per_round),
    }


def _ancoragem_vs_oficial(per_round: pl.DataFrame) -> dict | None:
    """Quantos ticks a ancoragem erra, onde há tick oficial para comparar."""
    if "delta_ancoragem_ticks" not in per_round.columns:
        return None
    d = per_round["delta_ancoragem_ticks"].drop_nulls().to_numpy()
    if d.size == 0:
        return None
    return {
        "n": int(d.size),
        "exato": float((d == 0).mean()),
        "ate_1_tick": float((np.abs(d) <= 1).mean()),
        "ate_4_ticks": float((np.abs(d) <= 4).mean()),
        "mediana": float(np.median(d)),
    }
