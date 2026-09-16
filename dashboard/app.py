"""
Dashboard do projeto (Fases 1 a 3).

Roda em cima de data/processed/<match_id>/*.parquet -- NÃO reparseia o .dem, só
lê os números já calculados por scripts/process_demo.py. Isso é proposital (ver
README, "Estratégia de hospedagem"): o dashboard público serve só esses parquet
leves, nunca o .dem cru de 200MB+.

Uso local:
    streamlit run dashboard/app.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import plotly.graph_objects as go
import polars as pl
import streamlit as st

# `streamlit run dashboard/app.py` coloca a pasta do script no sys.path, não a
# raiz do projeto -- sem isso o import de dashboard.theme quebra.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.theme import (  # noqa: E402
    CONTEXT_POINT,
    INK_MUTED,
    SEQUENTIAL_BLUE,
    SERIES,
    base_layout,
)
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CLUSTER_NAMES_FILE = PROJECT_ROOT / "clustering" / "cluster_names.json"


# ---------------------------------------------------------------------------
# Carga de dados
# ---------------------------------------------------------------------------

def list_matches() -> list[str]:
    if not PROCESSED_DIR.exists():
        return []
    return sorted(p.name for p in PROCESSED_DIR.iterdir() if p.is_dir())


@st.cache_data(show_spinner=False)
def load_match(match_id: str) -> dict:
    match_dir = PROCESSED_DIR / match_id
    tables = {p.stem: pl.read_parquet(p) for p in match_dir.glob("*.parquet")}
    meta_path = match_dir / "match_meta.json"
    tables["_meta"] = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    return tables


def load_cluster_names() -> dict[str, str]:
    if not CLUSTER_NAMES_FILE.exists():
        return {}
    try:
        return json.loads(CLUSTER_NAMES_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def show_table(df: pl.DataFrame, **kwargs) -> None:
    st.dataframe(df.to_pandas(), use_container_width=True, hide_index=True, **kwargs)


def bar_chart(df: pl.DataFrame, label_col: str, value_col: str, value_title: str, height: int = 380) -> None:
    """Barra horizontal de série única: rótulo direto no fim da barra, sem legenda
    (uma série só -- o título já diz o que é), grid recessivo.
    """
    d = df.sort(value_col, descending=False)
    labels = d[label_col].to_list()
    values = [float(v) if v is not None else 0.0 for v in d[value_col].to_list()]

    fig = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker={"color": SERIES[0], "line": {"width": 0}},
            text=[f"{v:.1f}" for v in values],
            textposition="outside",
            textfont={"color": INK_MUTED, "size": 11},
            hovertemplate=f"%{{y}}<br>{value_title}: %{{x:.1f}}<extra></extra>",
            cliponaxis=False,
        )
    )
    layout = base_layout(height=height)
    layout["xaxis"]["title"] = {"text": value_title, "font": {"color": INK_MUTED, "size": 11}}
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

st.set_page_config(page_title="CS2 Replay Stats", layout="wide")
st.title("CS2 Replay Stats")
st.caption(
    "Métricas de replay (.dem) do CS2 — estatística básica, métricas autorais de "
    "AWP/mira/posicionamento e clustering de estilos de jogo."
)

matches = list_matches()
if not matches:
    st.warning(
        "Nenhuma partida processada ainda. Rode "
        "`python -m scripts.process_demo data/raw/sua_demo.dem` primeiro."
    )
    st.stop()

match_id = st.sidebar.selectbox("Partida", matches)
data = load_match(match_id)
meta = data.get("_meta", {})

c1, c2, c3 = st.columns(3)
c1.metric("Mapa", meta.get("map_name", "?"))
c2.metric("Rounds", meta.get("n_rounds", "?"))
c3.metric("Partida", match_id)

st.divider()

tabs = st.tabs(
    [
        "Visão geral",
        "AWP",
        "Crosshair",
        "Posicionamento",
        "Estilos de jogo",
        "Detalhe por round",
    ]
)

# --- Visão geral (Fase 1) --------------------------------------------------
with tabs[0]:
    st.subheader("Métricas básicas")
    left, right = st.columns(2)

    with left:
        st.markdown("**ADR** — dano médio por round (só a inimigos, sem overkill)")
        adr = data["adr_summary"].select(["name", "adr", "total_damage", "rounds_played"]).sort(
            "adr", descending=True
        )
        bar_chart(adr, "name", "adr", "ADR")
        show_table(adr)

    with right:
        st.markdown("**KAST%** — rounds com Kill, Assist, Survived ou Traded")
        kast = data["kast_summary"].select(["name", "kast_pct", "kast_rounds", "rounds_played"]).sort(
            "kast_pct", descending=True
        )
        bar_chart(kast, "name", "kast_pct", "KAST %")
        show_table(kast)

    st.divider()
    left2, right2 = st.columns(2)
    with left2:
        st.markdown("**Trade kills** — kills que vingaram um companheiro (janela de 5s)")
        show_table(
            data["trade_kills_summary"]
            .select(["name", "total_kills", "total_trade_kills", "trade_kill_pct"])
            .sort("total_trade_kills", descending=True)
        )
    with right2:
        st.markdown("**Utility damage** — dano de granada (HE + fogo) por round")
        show_table(
            data["utility_damage_summary"]
            .select(["name", "utility_damage_per_round", "total_utility_damage"])
            .sort("utility_damage_per_round", descending=True)
        )

# --- AWP (Fase 2) ----------------------------------------------------------
with tabs[1]:
    st.subheader("Uso de AWP")
    st.caption(
        "Peek e hold não são certo e errado — são estilos válidos e situacionais. "
        "A tabela descreve a distribuição, não dá nota."
    )

    awp = data.get("awp_summary")
    if awp is None or awp.height == 0:
        st.info("Nenhum jogador usou AWP nessa partida.")
    else:
        show_table(
            awp.select(
                [
                    "name",
                    "awp_rounds",
                    "rounds_with_engagement",
                    "engagements_won",
                    "engagements_lost",
                    "engagements_no_trade",
                    "engagement_conversion_pct",
                    "opening_picks",
                    "median_time_to_first_shot_s",
                    "style_hold",
                    "style_peek",
                    "style_intermediate",
                ]
            )
        )
        st.markdown(
            "**Como ler:** `engagement_conversion_pct` é sobre as brigas que tiveram "
            "resolução (ganhou ou perdeu). Tiro sem resolução (`no_trade`) fica fora do "
            "denominador de propósito — com AWP, muito tiro é de informação ou pra negar "
            "espaço, e jogar isso no mesmo balde de 'errou' infla a taxa de erro."
        )

        st.markdown("**Briga a briga**")
        show_table(
            data["awp_per_round"]
            .filter(pl.col("engagement_tick").is_not_null())
            .select(
                [
                    "round_num",
                    "name",
                    "side",
                    "time_to_first_shot_s",
                    "net_displacement",
                    "slow_fraction",
                    "style",
                    "outcome",
                    "shot_place",
                ]
            )
            .sort(["round_num"])
        )
        st.caption(
            "`net_displacement` é o deslocamento nos 3s antes do tiro (a base da "
            "classificação); `slow_fraction` é quanto desse tempo foi parado. A flag de "
            "scope do demo não é confiável e por isso não entra na classificação — ver "
            "nota no topo de metrics/awp_metrics.py."
        )

# --- Crosshair (Fase 2) ----------------------------------------------------
with tabs[2]:
    st.subheader("Crosshair placement")
    st.caption(
        "O score combina altura da mira (linha da cabeça) com direção. A direção só é "
        "cobrada nos momentos que antecedem contato real — e, quando não há briga, "
        "pré-mirar um ângulo de entrada conhecido conta como acerto, não como erro."
    )

    ch = data.get("crosshair_summary")
    if ch is None:
        st.info("Métricas de crosshair não disponíveis nessa partida.")
    else:
        bar_chart(
            ch.select(["name", "crosshair_score"]).sort("crosshair_score", descending=True),
            "name",
            "crosshair_score",
            "Score de crosshair (0-100)",
        )
        show_table(
            ch.select(
                [
                    "name",
                    "crosshair_score",
                    "height_score",
                    "direction_score",
                    "median_pitch_error_deg",
                    "median_enemy_aim_error_deg",
                    "median_prefire_match_deg",
                    "n_fight_samples",
                    "n_samples",
                ]
            )
        )
        st.markdown(
            "**Atenção na leitura:** `median_prefire_match_deg` mede distância até os "
            "ângulos de entrada *derivados dos dados* — ou seja, os ângulos de consenso. "
            "Um jogador que joga off-angle de propósito aparece com número alto aqui sem "
            "estar errado. É um dos pontos que pede calibração manual "
            "(`metrics/map_angles.py`)."
        )

# --- Posicionamento (Fase 2) ----------------------------------------------
with tabs[3]:
    st.subheader("Posicionamento")

    heat = data.get("heatmap_bins")
    if heat is None:
        st.info("Dados de posição não disponíveis.")
    else:
        side = st.radio("Lado", ["ct", "t"], horizontal=True, key="heat_side")
        h = heat.filter(pl.col("side") == side)

        # A maioria dos bins é de passagem (poucas amostras) e uns poucos são
        # posições de parada. Numa escala 0..máximo, esses poucos esticam a rampa
        # e o mapa inteiro fica pálido. Cortar a escala no percentil 95 faz os
        # pontos de permanência aparecerem; o hover continua mostrando o valor real.
        samples = h["samples"].to_list()
        cmax = float(h["samples"].quantile(0.95) or max(samples, default=1))

        fig = go.Figure(
            go.Scatter(
                x=h["x"].to_list(),
                y=h["y"].to_list(),
                mode="markers",
                marker={
                    "size": 9,
                    "color": samples,
                    "colorscale": SEQUENTIAL_BLUE,
                    "cmin": 0,
                    "cmax": cmax,
                    "showscale": True,
                    "colorbar": {
                        "title": {"text": "amostras", "font": {"size": 11}},
                        "thickness": 12,
                    },
                    "line": {"width": 0},
                },
                hovertemplate="x %{x:.0f} · y %{y:.0f}<br>amostras: %{marker.color}<extra></extra>",
            )
        )
        layout = base_layout(height=560)
        layout["xaxis"]["title"] = {"text": "X (coordenadas do mapa)", "font": {"size": 11}}
        layout["yaxis"]["title"] = {"text": "Y (coordenadas do mapa)", "font": {"size": 11}}
        layout["yaxis"]["scaleanchor"] = "x"  # mantém a proporção real do mapa
        fig.update_layout(**layout)
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "Densidade de presença em coordenadas de jogo. O overlay do radar do mapa "
            "depende dos assets do awpy (`awpy get maps`), que precisam de rede liberada — "
            "sem eles a leitura é a mesma, só sem a imagem de fundo."
        )

        st.divider()
        cA, cB = st.columns(2)
        with cA:
            st.markdown("**Setup padrão do time** (média de jogadores por região)")
            show_table(data["standard_setup"].filter(pl.col("side") == side).head(12))
        with cB:
            st.markdown("**Rounds mais fora do padrão**")
            st.caption(
                "`deviation_index` 1.0 = tão típico quanto a mediana do próprio time; "
                "2.0 = duas vezes mais fora do padrão."
            )
            show_table(
                data["setup_deviation"]
                .filter(pl.col("side") == side)
                .sort("deviation_index", descending=True)
                .head(10)
            )

# --- Clusters (Fase 3) -----------------------------------------------------
with tabs[4]:
    st.subheader("Clustering de estilos de jogo")

    assignments = data.get("cluster_assignments")
    profiles = data.get("cluster_profiles")

    if assignments is None or profiles is None:
        st.info("Clustering não disponível nessa partida.")
    else:
        names = load_cluster_names()
        unnamed = [c for c in profiles["cluster"].to_list() if not names.get(str(c))]
        if unnamed:
            st.warning(
                f"Clusters ainda sem nome: {', '.join(str(c) for c in unnamed)}. "
                "O KMeans agrupa, mas quem interpreta e nomeia é você — edite "
                "`clustering/cluster_names.json` olhando o perfil abaixo e os rounds de exemplo."
            )

        pca_meta = meta.get("pca", {})
        var = pca_meta.get("explained_variance_ratio", [])
        if var:
            st.caption(
                f"Os dois eixos explicam {100 * sum(var[:2]):.0f}% da variação total. "
                "PCA1 é dominado por impacto (dano, kills, trades); PCA2 por separação do "
                "time e sobrevivência."
            )

        # Scatter facetado: um painel por cluster. A paleta validada só garante
        # separação segura até 3 cores num gráfico que compara todos os pares, então
        # em vez de 4 cores disputando legibilidade, cada cluster aparece sozinho
        # em destaque sobre os demais pontos em cinza.
        clusters = sorted(profiles["cluster"].to_list())
        cols = st.columns(min(len(clusters), 4))
        for i, cl in enumerate(clusters):
            with cols[i % len(cols)]:
                others = assignments.filter(pl.col("cluster") != cl)
                focus = assignments.filter(pl.col("cluster") == cl)
                label = names.get(str(cl)) or f"Cluster {cl}"

                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(
                        x=others["pca_1"].to_list(),
                        y=others["pca_2"].to_list(),
                        mode="markers",
                        marker={"size": 6, "color": CONTEXT_POINT, "line": {"width": 0}},
                        hoverinfo="skip",
                        showlegend=False,
                    )
                )
                fig.add_trace(
                    go.Scatter(
                        x=focus["pca_1"].to_list(),
                        y=focus["pca_2"].to_list(),
                        mode="markers",
                        marker={
                            "size": 9,
                            "color": SERIES[0],
                            "line": {"width": 2, "color": "rgba(0,0,0,0.35)"},
                        },
                        customdata=list(
                            zip(
                                focus["name"].to_list(),
                                focus["round_num"].to_list(),
                                focus["damage"].to_list(),
                            )
                        ),
                        hovertemplate=(
                            "%{customdata[0]} · round %{customdata[1]}"
                            "<br>dano: %{customdata[2]}<extra></extra>"
                        ),
                        showlegend=False,
                    )
                )
                layout = base_layout(height=260)
                layout["margin"] = {"l": 32, "r": 12, "t": 32, "b": 28}
                layout["title"] = {
                    "text": f"{label} · {focus.height} rounds",
                    "font": {"size": 12, "color": INK_MUTED},
                    "x": 0,
                }
                fig.update_layout(**layout)
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Perfil de cada cluster** (médias em unidades originais)")
        prof = profiles.with_columns(
            pl.col("cluster")
            .map_elements(lambda c: names.get(str(c)) or f"Cluster {c}", return_dtype=pl.String)
            .alias("nome")
        )
        show_table(
            prof.select(
                [
                    "cluster",
                    "nome",
                    "n_rounds",
                    "damage",
                    "kills",
                    "trade_kills",
                    "utility_damage",
                    "avg_distance_from_team",
                    "distinct_places",
                    "time_of_first_contact_s",
                    "survived",
                    "crosshair_score",
                ]
            )
        )

        st.markdown("**Rounds representativos** (os mais próximos do centro de cada cluster)")
        st.caption("São esses os rounds pra assistir na demo na hora de dar nome ao cluster.")
        show_table(data["cluster_examples"])

        with st.expander("Quantos clusters usar? (silhueta)"):
            st.caption(
                "Silhueta mede o quanto cada ponto está mais perto do próprio grupo que do "
                "vizinho. Maior é melhor, mas um k com silhueta um pouco pior pode ser "
                "preferível se os grupos fizerem mais sentido de jogo."
            )
            show_table(data["cluster_silhouettes"])

# --- Detalhe por round -----------------------------------------------------
with tabs[5]:
    st.subheader("Detalhe round a round — para validação manual")
    st.caption(
        "Escolhe jogador e métrica pra ver o valor calculado round a round e comparar "
        "com o que você sabe que aconteceu naquele round."
    )

    players = data["adr_summary"]["name"].sort().to_list()
    player = st.selectbox("Jogador", players)

    metric_tables = {
        "ADR (dano por round)": "adr_per_round",
        "KAST (flags por round)": "kast_per_round",
        "Trade kills (por round)": "trade_kills_per_round",
        "Utility damage (por round)": "utility_damage_per_round",
        "AWP (briga do round)": "awp_per_round",
        "Crosshair (por round)": "crosshair_per_round",
        "Posicionamento (por round)": "position_profile",
        "Cluster atribuído (por round)": "cluster_assignments",
    }
    metric_label = st.selectbox("Métrica", list(metric_tables.keys()))
    table_name = metric_tables[metric_label]

    df = data.get(table_name)
    if df is None:
        st.info("Essa métrica não está disponível nessa partida.")
    else:
        if "name" in df.columns:
            round_df = df.filter(pl.col("name") == player)
        else:
            steamid = data["adr_summary"].filter(pl.col("name") == player)["steamid"][0]
            round_df = df.filter(pl.col("steamid") == steamid)
        show_table(round_df.sort("round_num"))
