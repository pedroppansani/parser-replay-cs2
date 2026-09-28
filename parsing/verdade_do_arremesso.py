"""
A verdade do arremesso gravada na demo (rota B, decisão 21a).

POR QUE EXISTE
--------------
A rota A INFERE o botão, a postura e o ponto de saída de cada granada pela
rotina do jogo medida no gabarito. A demo grava esses valores diretamente --
é de onde o gabarito saiu --, e toda partida com .dem passa a guardá-los no
interim em duas tabelas novas:

  arremessos_demo  uma linha por projétil lançado: a velocidade e o ponto de
                   nascimento que o JOGO deu à granada (m_vInitialVelocity,
                   m_vInitialPosition), o botão (m_flThrowStrength, 0 / 0,5 /
                   1) e a flag de jump-throw (m_bJumpThrow);
  movimento        por (tick, steamid), nas mesmas linhas da tabela de ticks:
                   duck_amount, ducked, duck_view_offset, se o jogador está no
                   chão (m_hGroundEntity) e o tick do último pulo
                   (m_nLastJumpTick).

A métrica usa o valor LIDO quando a tabela existe e o INFERIDO quando não
existe, e declara qual (fonte_do_botao, fonte_da_postura, fonte_da_origem).

A FORÇA É DA GRANADA QUE SAIU, NÃO DA QUE ESTÁ NA MÃO
-----------------------------------------------------
O projétil não carrega m_flThrowStrength (vem nulo); ela está na entidade da
ARMA. No tick da soltura a entidade de arma daquele tipo já é a PRÓXIMA granada,
com força 0 -- foi o que fez quatro botões do gabarito saírem "errados" na
validação (match_16:19:147, match_20:27:255, match_41:21:172, match_42:4:375).
A força é lida em t-1 (o tick anterior ao nascimento do projétil), na entidade
de arma do mesmo tipo e do mesmo jogador. Com mais de uma ali (a próxima granada
já no inventário), vale a que deixa de existir no nascimento: a ARMA CONSUMIDA.
Ela nem sempre some (muitas vezes segue alguns ticks com a mesma força), por
isso "sumir" é desempate, não a regra. Medido nas 13 partidas com demo: ver
`tests/test_verdade_do_arremesso.py` e o histórico de VERSAO_DO_PARSER.
"""
from __future__ import annotations

import polars as pl

MS = "CCSPlayerPawn.CCSPlayer_MovementServices."

# nome na demo -> coluna no interim. Nem toda build grava todo campo
# (m_flDuckViewOffset falta nas demos mais antigas): o que faltar vem nulo,
# declarado, nunca inventado.
PROPS_MOVIMENTO = {
    MS + "m_flDuckAmount": "duck_amount",
    MS + "m_bDucked": "ducked",
    MS + "m_flDuckViewOffset": "duck_view_offset",
    "CCSPlayerPawn.m_hGroundEntity": "chao",
    MS + "m_nLastJumpTick": "ultimo_pulo",
}
# handle de entidade inválido em m_hGroundEntity: o jogador está no ar
SEM_CHAO = 16777215

PROPS_GRANADA = ["Grenade.m_vInitialVelocity", "Grenade.m_vInitialPosition",
                 "Grenade.m_flThrowStrength", "Grenade.m_bJumpThrow"]

# classe do projétil -> classes da arma que o gera (a molotov e a incendiária
# viram o mesmo projétil)
ARMA_DO_PROJETIL = {
    "CSmokeGrenadeProjectile": ("CSmokeGrenade",),
    "CFlashbangProjectile": ("CFlashbang",),
    "CHEGrenadeProjectile": ("CHEGrenade",),
    "CMolotovProjectile": ("CMolotovGrenade", "CIncendiaryGrenade"),
    "CDecoyProjectile": ("CDecoyGrenade",),
}

COLUNAS_MOVIMENTO = ["tick", "steamid", "duck_amount", "ducked", "duck_view_offset",
                     "no_chao", "tick_do_ultimo_pulo"]


def base_do_ultimo_pulo(parser) -> tuple[int | None, float, int]:
    """A constante c de m_nLastJumpTick = 2·tick + c, medida na própria demo.

    O campo não está na base de tick da demo: muda no tick da decolagem com
    valor 2·tick + c (meio-tick), c fixo por demo. c é a moda sobre todas as
    mudanças do campo; devolve (c, fração das mudanças que batem, n).
    """
    try:
        df = pl.from_pandas(parser.parse_ticks([MS + "m_nLastJumpTick"]))
    except Exception:
        return None, 0.0, 0
    if MS + "m_nLastJumpTick" not in df.columns:
        return None, 0.0, 0
    return _base_da_tabela(df.rename({MS + "m_nLastJumpTick": "ultimo_pulo"}))


def _base_da_tabela(df: pl.DataFrame) -> tuple[int | None, float, int]:
    """`base_do_ultimo_pulo` sobre uma tabela já lida (coluna `ultimo_pulo`)."""
    if df["ultimo_pulo"].null_count() == df.height:
        return None, 0.0, 0
    mud = (df.select("tick", "steamid", pl.col("ultimo_pulo").alias("lj")).sort("steamid", "tick")
           .with_columns(pl.col("lj").cast(pl.Int64).diff().over("steamid").alias("d"))
           .filter(pl.col("d").is_not_null() & (pl.col("d") != 0) & (pl.col("lj") > 0)))
    if mud.height == 0:
        return None, 0.0, 0
    c = mud["lj"].cast(pl.Int64) - 2 * mud["tick"].cast(pl.Int64)
    base = int(c.mode().sort()[0])
    return base, float((c == base).mean()), mud.height


def movimento(parser, ticks: list[int] | None = None) -> pl.DataFrame:
    """As propriedades de movimento por (tick, steamid), com X, Y, Z para conferência.

    X, Y, Z NÃO vão para o interim (já estão na tabela de ticks): servem para
    quem chama conferir que as linhas casam com a tabela de ticks existente.
    """
    df = pl.from_pandas(parser.parse_ticks(list(PROPS_MOVIMENTO) + ["X", "Y", "Z"], ticks=ticks))
    for longo, curto in PROPS_MOVIMENTO.items():
        df = df.rename({longo: curto}) if longo in df.columns else df.with_columns(pl.lit(None).alias(curto))
    base, _, _ = _base_da_tabela(df) if ticks is None else base_do_ultimo_pulo(parser)
    ultimo = (pl.lit(None, dtype=pl.Float64) if base is None else
              pl.when(pl.col("ultimo_pulo").cast(pl.Int64) > 0)
              .then((pl.col("ultimo_pulo").cast(pl.Int64) - base) / 2.0).otherwise(None))
    return df.select(
        pl.col("tick").cast(pl.Int32), pl.col("steamid").cast(pl.UInt64),
        pl.col("duck_amount").cast(pl.Float32), pl.col("ducked").cast(pl.Boolean),
        pl.col("duck_view_offset").cast(pl.Float32),
        pl.when(pl.col("chao").is_null()).then(None)
        .otherwise(pl.col("chao").cast(pl.Int64) != SEM_CHAO).alias("no_chao"),
        ultimo.cast(pl.Float64).alias("tick_do_ultimo_pulo"),
        pl.col("X"), pl.col("Y"), pl.col("Z"),
    )


def arremessos_demo(parser) -> tuple[pl.DataFrame, dict]:
    """Lê as granadas da demo e devolve `tabela_de_arremessos` delas."""
    return tabela_de_arremessos(pl.from_pandas(parser.parse_grenades(extra=PROPS_GRANADA)))


def tabela_de_arremessos(g: pl.DataFrame) -> tuple[pl.DataFrame, dict]:
    """Uma linha por projétil lançado, com a força da granada que SAIU.

    `g` é a saída de `parse_grenades(extra=PROPS_GRANADA)`: uma linha por
    entidade de granada (arma no inventário ou projétil) por tick.

    Devolve (tabela, contagem da ligação). `ligacao` diz de onde veio a força:
      "t-1"             exatamente uma entidade de arma do tipo, do jogador, no
                        tick anterior ao nascimento do projétil;
      "tick_anterior"   idem, mas a demo pulou ticks e o anterior GRAVADO não
                        é t-1;
      "arma_consumida"  mais de uma ali, e exatamente uma delas deixa de
                        existir no nascimento (a que saiu da mão);
      "sem_arma"        nenhuma -- força nula, declarada;
      "ambigua"         o desempate não resolve -- força nula, declarada.
    """
    for c in PROPS_GRANADA:
        if c not in g.columns:
            g = g.with_columns(pl.lit(None).alias(c))
    proj = (g.filter(pl.col("grenade_type").is_in(list(ARMA_DO_PROJETIL))
                     & pl.col("Grenade.m_vInitialVelocity").is_not_null())
            .sort("grenade_entity_id", "tick"))
    # o id de entidade é reaproveitado: um projétil novo começa onde o mesmo id
    # tem um buraco de tick
    proj = proj.with_columns(
        (pl.col("tick").diff().over("grenade_entity_id").fill_null(2) > 1).cum_sum()
        .over("grenade_entity_id").alias("_seg"))
    nasc = (proj.group_by("grenade_entity_id", "_seg", maintain_order=True)
            .agg(pl.all().first()).drop("_seg"))

    armas = g.filter(~pl.col("grenade_type").is_in(list(ARMA_DO_PROJETIL))).select(
        pl.col("grenade_entity_id").alias("entidade_arma"), pl.col("steamid").cast(pl.UInt64),
        pl.col("grenade_type").alias("classe_arma"), pl.col("tick"),
        pl.col("Grenade.m_flThrowStrength").cast(pl.Float32).alias("forca"),
        pl.col("Grenade.m_bJumpThrow").cast(pl.Boolean).alias("jump_throw"))
    classes = pl.DataFrame([(pr, a) for pr, arm in ARMA_DO_PROJETIL.items() for a in arm],
                           schema=["grenade_type", "classe_arma"], orient="row")

    # a demo às vezes pula ticks: o "tick anterior" é o último GRAVADO antes do
    # nascimento, não t-1 literal
    gravados = g.select(pl.col("tick").unique(maintain_order=True).sort().cast(pl.Int64).alias("anterior"))
    nasc = (nasc.with_columns(pl.col("tick").cast(pl.Int64), pl.col("steamid").cast(pl.UInt64))
            .with_row_index("_i").sort("tick")
            .join_asof(gravados.with_columns(pl.col("anterior").alias("_k")), left_on="tick", right_on="_k",
                       strategy="backward", allow_exact_matches=False)
            .drop("_k"))
    cands = (nasc.select("_i", "tick", "steamid", "anterior", "grenade_type")
             .join(classes, on="grenade_type")
             .join(armas.with_columns(pl.col("tick").cast(pl.Int64).alias("anterior")).drop("tick"),
                   on=["steamid", "anterior", "classe_arma"]))
    # consumida = a entidade tem linha no tick anterior e NÃO tem no nascimento.
    # Muitas vezes a entidade arremessada CONTINUA existindo alguns ticks, com a
    # mesma força; por isso "sumir" só desempata quando há duas candidatas
    vivas = armas.select("entidade_arma", "steamid", pl.col("tick").cast(pl.Int64)).unique(maintain_order=True, keep="first")
    cands = cands.join(vivas.with_columns(pl.lit(True).alias("viva")), on=["entidade_arma", "steamid", "tick"],
                       how="left").with_columns(pl.col("viva").fill_null(False))
    n = cands.group_by("_i", maintain_order=True).agg(pl.len().alias("n"), (~pl.col("viva")).sum().alias("n_consumidas"))
    escolha = (cands.join(n, on="_i")
               .filter((pl.col("n") == 1) | ((pl.col("n_consumidas") == 1) & ~pl.col("viva")))
               .select("_i", "forca", "jump_throw", "entidade_arma", "n"))
    out = (nasc.join(n, on="_i", how="left").drop("n")
           .join(escolha, on="_i", how="left")
           .join(n.select("_i", pl.col("n").alias("n_cand")), on="_i", how="left")
           .with_columns(pl.col("n_cand").fill_null(0)))
    out = out.with_columns(
        pl.when(pl.col("n_cand") == 0).then(pl.lit("sem_arma"))
        .when((pl.col("n_cand") > 1) & pl.col("entidade_arma").is_null()).then(pl.lit("ambigua"))
        .when(pl.col("n_cand") > 1).then(pl.lit("arma_consumida"))
        .when(pl.col("anterior") == pl.col("tick") - 1).then(pl.lit("t-1"))
        .otherwise(pl.lit("tick_anterior")).alias("ligacao"))
    v0, p0 = pl.col("Grenade.m_vInitialVelocity"), pl.col("Grenade.m_vInitialPosition")
    tabela = out.select(
        pl.col("tick").cast(pl.Int32), pl.col("grenade_entity_id").cast(pl.Int32).alias("entity_id"),
        pl.col("steamid"), pl.col("grenade_type"),
        *[v0.list.get(k).cast(pl.Float32).alias(f"v0_{e}") for k, e in enumerate("xyz")],
        *[p0.list.get(k, null_on_oob=True).cast(pl.Float32).alias(f"p0_{e}") for k, e in enumerate("xyz")],
        pl.col("forca").cast(pl.Float32), pl.col("jump_throw").cast(pl.Boolean),
        pl.col("entidade_arma").cast(pl.Int32), pl.col("ligacao"),
    ).sort("tick", "entity_id")
    cont = {k: 0 for k in ("t-1", "tick_anterior", "arma_consumida", "sem_arma", "ambigua")}
    for k, v in tabela["ligacao"].value_counts().iter_rows():
        cont[k] = int(v)
    return tabela, cont


def grava_movimento(df: pl.DataFrame, caminho) -> None:
    """Grava a tabela `movimento` com o tick em codificação DELTA.

    O tick é a chave e cresce de 1 em 1 (dez linhas por tick): no formato
    padrão ele sozinho pesava 0,78 MB por partida, com delta 0,01 MB. Medido na
    match_23 (1.622.870 linhas): tabela inteira 1,20 -> 0,56 MB; lê de volta
    idêntica.
    """
    import pyarrow.parquet as pq

    pq.write_table(df.to_arrow(), str(caminho), compression="zstd",
                   use_dictionary=[c for c in df.columns if c != "tick"],
                   column_encoding={"tick": "DELTA_BINARY_PACKED"})
