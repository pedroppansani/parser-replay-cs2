"""
Identidade de jogador: é o `steamid`, sempre. Nome é rótulo de exibição.

Por que este módulo existe: o nick muda entre partidas -- inclusive só de caixa.
Medido no corpus (520 jogador-partidas, 116 steamids): quatro jogadores
aparecem com mais de um nome, e um deles com quatro.

    sh1ro / SH1R0          donk / donk666
    magixx / lilpeepfan-   Olajida / Etaliqe / Ahun... (smurf)

Qualquer agrupamento por nome quebra nesses casos. O efeito é diferente conforme
onde acontece, e os dois foram medidos:

- **Dentro de uma partida** não há risco hoje: toda partida tem exatamente 10
  steamids distintos e nenhum nome repetido (há invariante travando isso).
- **Entre partidas** o agrupamento por nome parte o jogador em dois -- foi o que
  acontecia nos relatórios (tabela de funções, "quem mais concentra",
  candidatos a IGL).
- As REFERÊNCIAS do corpus (escala do rating, quantis dos papéis, centros dos
  clusters, isca por função) não são afetadas: elas agregam linhas por
  (partida, steamid), e um nick a mais não cria linha nenhuma.

O risco inverso -- dois jogadores DIFERENTES com o mesmo nome de exibição
fundidos num só -- não acontece neste corpus (nenhum nome aponta para dois
steamids), e é justamente o que não aparece como duplicata: apareceria como um
jogador com estatística estranha. Por isso existe invariante para ele também.
"""
from __future__ import annotations

import polars as pl


def nome_de_exibicao(df: pl.DataFrame, coluna_partida: str = "match_id") -> pl.DataFrame:
    """steamid -> o nome que a interface mostra.

    Escolhe o nick MAIS FREQUENTE do jogador no corpus; no empate, o da partida
    mais recente (a ordem de `match_id` é cronológica no projeto). Não é uma
    tabela de renomeação à mão: sai do próprio dado e não precisa de manutenção
    quando alguém trocar de nick.
    """
    if df.height == 0 or not {"steamid", "name"} <= set(df.columns):
        return pl.DataFrame(schema={"steamid": pl.UInt64, "nome": pl.Utf8})
    chaves = ["steamid", "name"]
    contagem = df.group_by(chaves).agg(
        pl.len().alias("n"),
        (pl.col(coluna_partida).max() if coluna_partida in df.columns else pl.lit("")).alias("ultima"),
    )
    return (
        contagem.sort(["n", "ultima"], descending=[True, True])
        .group_by("steamid", maintain_order=True)
        .first()
        .select("steamid", pl.col("name").alias("nome"))
    )


def com_nome_de_exibicao(df: pl.DataFrame, coluna_partida: str = "match_id") -> pl.DataFrame:
    """Troca a coluna `name` pelo nome de exibição do steamid.

    É isso que todo relatório ENTRE PARTIDAS deve usar antes de agrupar -- e o
    agrupamento em si continua sendo por steamid.
    """
    nomes = nome_de_exibicao(df, coluna_partida)
    if nomes.height == 0:
        return df
    return (
        df.join(nomes.with_columns(pl.col("steamid").cast(df.schema["steamid"])), on="steamid", how="left")
        .with_columns(pl.coalesce(["nome", "name"]).alias("name"))
        .drop("nome")
    )
