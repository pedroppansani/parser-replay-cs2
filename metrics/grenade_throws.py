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


def aplica_tick_oficial(
    ancorados: list[dict], oficial: pl.DataFrame | None, tickrate: int
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
            "em_transicao_de_agachar": bool(e.get("user_ducking")),
            "atraso_animacao_ticks": (None if a.get("tick_clique") is None
                                      else int(e["tick"]) - int(a["tick_clique"])),
            "fonte_tick": "oficial",
        }
    return saida, (float(np.median(avancos)) if avancos else None)


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
    ancorados, offset_oficial = aplica_tick_oficial(ancorados, tables.get("grenade_thrown"), tickrate)

    linhas = []
    for a in ancorados:
        estado = (
            _estado_do_jogador(tk, a["steamid"], a["tick_soltura"], tickrate)
            if a["tick_soltura"] is not None
            else {}
        )
        vel = velocidade_de_arremesso(a["traj"], a["ticks"], estado, tickrate) or {}
        bate = colisoes(a["traj"], a["ticks"], tickrate)
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
            "postura": classifica_postura(a["altura_olhos"]),
            "pitch": a.get("pitch"),
            "yaw": a.get("yaw"),
            "x": None if a.get("pos_soltura") is None else float(a["pos_soltura"][0]),
            "y": None if a.get("pos_soltura") is None else float(a["pos_soltura"][1]),
            "z": None if a.get("pos_soltura") is None else float(a["pos_soltura"][2]),
            "velocidade_jogador": estado.get("velocidade"),
            "velocidade_vertical": estado.get("velocidade_vertical"),
            "giro_na_soltura": estado.get("giro"),
            "movimento": classifica_movimento(estado),
            "no_ar": (
                None if estado.get("velocidade_vertical") is None
                else abs(estado["velocidade_vertical"]) >= VELOCIDADE_VERTICAL_NO_AR
            ),
            "tick_primeiro": a["tick_primeiro"],
            "velocidade_bruta": vel.get("bruta"),
            "velocidade_arremesso": vel.get("relativa"),
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
