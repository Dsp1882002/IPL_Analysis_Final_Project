from pathlib import Path

import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Resolve paths relative to this script's own location, not the process's
# working directory — this is what breaks on Streamlit Cloud when the app
# is deployed from a subfolder or the cwd doesn't match local assumptions.
# CSVs live alongside app.py at the repo root (not in a data/ subfolder).
DATA_DIR = Path(__file__).resolve().parent

# ------------------------------------------------------------------
# Page config & shared style
# ------------------------------------------------------------------
st.set_page_config(
    page_title="IPL Analytics Dashboard",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="expanded",
)

PALETTE = {
    "highlight": "#E69F00",  # orange — draws the eye to the takeaway
    "context": "#B3B3B3",    # muted grey — background/comparison series
    "blue": "#0072B2",
    "teal": "#009E73",
    "text": "#333333",
}
TEMPLATE = "simple_white"

CUSTOM_CSS = """
<style>
    .block-container {padding-top: 2rem;}
    div[data-testid="stMetric"] {
        background-color: #FAFAFA;
        border: 1px solid #EAEAEA;
        border-radius: 8px;
        padding: 12px 16px;
    }
    div[data-testid="stMetricLabel"] {font-size: 0.85rem; color: #666;}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ------------------------------------------------------------------
# Data loading
# ------------------------------------------------------------------
@st.cache_data
def load_data():
    required = ["deliveries.csv", "matches.csv", "players.csv", "seasons.csv"]
    missing = [f for f in required if not (DATA_DIR / f).exists()]
    if missing:
        st.error(
            f"Missing data file(s) in `{DATA_DIR}`: {', '.join(missing)}. "
            "Check that the `data/` folder was committed and pushed to your "
            "GitHub repo — it's a common miss when zipping/uploading a project."
        )
        st.stop()

    deliveries = pd.read_csv(DATA_DIR / "deliveries.csv")
    matches = pd.read_csv(DATA_DIR / "matches.csv")
    players = pd.read_csv(DATA_DIR / "players.csv")
    seasons = pd.read_csv(DATA_DIR / "seasons.csv")
    matches["date"] = pd.to_datetime(matches["date"])

    # --- derived fields used across tabs ---
    def batting_first(row):
        if row["toss_decision"] == "bat":
            return row["toss_winner"]
        return row["team1"] if row["toss_winner"] == row["team2"] else row["team2"]

    matches["batting_first_team"] = matches.apply(batting_first, axis=1)
    matches["bat_first_won"] = matches["winner"] == matches["batting_first_team"]
    matches["toss_won_match"] = matches["toss_winner"] == matches["winner"]
    matches["match_total"] = matches["first_innings_score"] + matches["second_innings_score"]

    return deliveries, matches, players, seasons


deliveries, matches, players, seasons = load_data()

ALL_TEAMS = sorted(set(matches["team1"]) | set(matches["team2"]))
MIN_SEASON, MAX_SEASON = int(matches["season"].min()), int(matches["season"].max())

# ------------------------------------------------------------------
# Sidebar filters
# ------------------------------------------------------------------
st.sidebar.title("🏏 IPL Analytics")
st.sidebar.caption("Filters apply across every tab")

season_range = st.sidebar.slider(
    "Season range",
    min_value=MIN_SEASON, max_value=MAX_SEASON,
    value=(MIN_SEASON, MAX_SEASON),
)

team_filter = st.sidebar.multiselect(
    "Teams (leave empty = all)", options=ALL_TEAMS, default=[],
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Data: IPL ball-by-ball deliveries, matches, players & season "
    "summaries. Built with Plotly + Streamlit."
)

# --- apply filters ---
m = matches[(matches["season"] >= season_range[0]) & (matches["season"] <= season_range[1])]
if team_filter:
    m = m[m["team1"].isin(team_filter) | m["team2"].isin(team_filter)]

d = deliveries[deliveries["match_id"].isin(m["match_id"])]

if len(m) == 0:
    st.warning("No matches for the current filter selection — widen your filters.")
    st.stop()

# ------------------------------------------------------------------
# Header + KPIs
# ------------------------------------------------------------------
st.title("IPL Analytics Dashboard")
st.caption(
    f"Showing {season_range[0]}–{season_range[1]}"
    + (f" · Teams: {', '.join(team_filter)}" if team_filter else " · All teams")
)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Matches", f"{len(m):,}")
k2.metric("Seasons covered", f"{m['season'].nunique()}")
k3.metric("Avg match total", f"{m['match_total'].mean():.0f} runs")
k4.metric("Sixes hit", f"{d[d['batsman_runs'] == 6].shape[0]:,}")

tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 Overview", "🎯 Toss & Venue", "🏏 Player Performance", "🎳 Bowling Matchups"]
)

# ==================================================================
# TAB 1 — Overview
# ==================================================================
with tab1:
    st.subheader("Has chasing overtaken batting first as the winning strategy?")

    q1 = m.groupby("season")["bat_first_won"].mean().reset_index()
    q1["pct"] = q1["bat_first_won"] * 100

    fig1 = px.line(q1, x="season", y="pct", markers=True, template=TEMPLATE)
    fig1.update_traces(line_color=PALETTE["highlight"], marker_color=PALETTE["highlight"])
    fig1.add_hline(y=50, line_dash="dot", line_color=PALETTE["context"],
                    annotation_text="50% — even odds", annotation_position="bottom right")
    fig1.update_layout(
        title="Batting-first win rate has trended down as chasing became the stronger strategy",
        xaxis_title="Season", yaxis_title="Win rate batting first (%)",
        margin=dict(t=60),
    )
    st.plotly_chart(fig1, use_container_width=True)

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Outcomes by tournament stage")
        stage_outcome = (
            m.dropna(subset=["win_by"])
            .groupby(["stage", "win_by"]).size().reset_index(name="count")
        )
        if stage_outcome.empty:
            st.info("Not enough matches in the current filter to build this view.")
        else:
            stage_totals = stage_outcome.groupby("stage")["count"].transform("sum")
            stage_outcome["pct"] = stage_outcome["count"] / stage_totals * 100

            fig8 = px.bar(
                stage_outcome, x="stage", y="pct", color="win_by", barmode="stack",
                template=TEMPLATE,
                color_discrete_sequence=[PALETTE["highlight"], PALETTE["blue"], PALETTE["teal"]],
                title="Knockout matches skew toward tighter, wicket-based finishes",
            )
            fig8.update_layout(xaxis_title="", yaxis_title="Share of matches (%)", legend_title="")
            st.plotly_chart(fig8, use_container_width=True)

    with col_b:
        st.subheader("Average winning margin by city")
        runs_wins = m[m["win_by"] == "runs"]
        city_counts = runs_wins["city"].value_counts()
        top_cities = city_counts[city_counts >= min(5, city_counts.max() if len(city_counts) else 0)].index
        city_margins = (
            runs_wins[runs_wins["city"].isin(top_cities)]
            .groupby("city")["win_margin"].mean().reset_index()
            .sort_values("win_margin", ascending=False).head(10)
        )
        if city_margins.empty:
            st.info("Not enough matches in the current filter to build this view.")
        else:
            fig12 = px.bar(
                city_margins, x="win_margin", y="city", orientation="h", template=TEMPLATE,
                title="Winning margins (by runs) differ notably by host city",
            )
            fig12.update_traces(marker_color=PALETTE["blue"])
            fig12.update_layout(xaxis_title="Avg win margin (runs)", yaxis_title="")
            st.plotly_chart(fig12, use_container_width=True)

# ==================================================================
# TAB 2 — Toss & Venue
# ==================================================================
with tab2:
    st.subheader("Does winning the toss predict winning the match — and by how much per venue?")

    min_matches = st.slider("Minimum matches played at venue", 3, 30, 10, key="venue_min")
    venue_toss = m.groupby("venue")["toss_won_match"].agg(["mean", "count"]).reset_index()
    venue_toss = venue_toss[venue_toss["count"] >= min_matches].sort_values("mean", ascending=False)
    venue_toss["pct"] = venue_toss["mean"] * 100

    if venue_toss.empty:
        st.info("No venue meets this minimum with the current filters — lower the threshold or widen filters.")
    else:
        fig2 = px.bar(
            venue_toss, x="pct", y="venue", orientation="h", template=TEMPLATE,
            title=f"Toss advantage varies sharply by venue (min. {min_matches} matches)",
        )
        fig2.update_traces(marker_color=PALETTE["blue"])
        fig2.add_vline(x=50, line_dash="dot", line_color=PALETTE["context"])
        fig2.update_layout(xaxis_title="Toss winner also won the match (%)", yaxis_title="")
        st.plotly_chart(fig2, use_container_width=True)

    col_c, col_d = st.columns(2)

    with col_c:
        st.subheader("Which teams' wins lean most on winning the toss?")
        team_toss = m.groupby("winner")["toss_won_match"].mean().reset_index(name="share")
        team_toss = team_toss.dropna(subset=["winner"]).sort_values("share", ascending=False)
        if team_toss.empty:
            st.info("Not enough decided matches in the current filter to build this view.")
        else:
            fig9 = px.bar(
                team_toss, x="share", y="winner", orientation="h", template=TEMPLATE,
                title="Toss-dependency varies widely across teams",
            )
            fig9.update_traces(marker_color=PALETTE["teal"])
            fig9.update_layout(
                xaxis_title="Share of wins where team also won the toss",
                xaxis_tickformat=".0%", yaxis_title="",
            )
            st.plotly_chart(fig9, use_container_width=True)

    with col_d:
        st.subheader("Highest-scoring venues, day vs. night")
        venue_stats = m.groupby(["venue", "is_day_night"])["match_total"].mean().reset_index()
        v_counts = m["venue"].value_counts()
        top_v = v_counts[v_counts >= min_matches].index
        venue_stats = venue_stats[venue_stats["venue"].isin(top_v)]
        if venue_stats.empty:
            st.info("No venue meets this minimum with the current filters — lower the threshold or widen filters.")
        else:
            fig7 = px.bar(
                venue_stats, x="match_total", y="venue", color="is_day_night", barmode="group",
                orientation="h", template=TEMPLATE,
                color_discrete_map={True: PALETTE["highlight"], False: PALETTE["blue"]},
                title="Some venues consistently produce higher-scoring matches",
            )
            fig7.update_layout(xaxis_title="Avg combined match total", yaxis_title="", legend_title="Day/Night")
            st.plotly_chart(fig7, use_container_width=True)

# ==================================================================
# TAB 3 — Player Performance
# ==================================================================
with tab3:
    st.subheader("Does auction price relate to actual on-field output?")

    runs_by_player = d.groupby("striker")["batsman_runs"].sum().reset_index()
    runs_by_player.columns = ["player_name", "total_runs"]
    perf = players.merge(runs_by_player, on="player_name", how="left").fillna({"total_runs": 0})
    perf = perf[perf["total_runs"] > 0]

    if perf.empty:
        st.info("Not enough player data in the current filter to build this view.")
    else:
        fig5 = px.scatter(
            perf, x="highest_auction_price_lakh", y="total_runs", color="playing_role",
            hover_name="player_name", template=TEMPLATE,
            color_discrete_sequence=px.colors.qualitative.Safe,
            title="Auction price is a weak predictor of runs scored in this filtered window",
        )
        fig5.update_layout(xaxis_title="Highest auction price (lakh)", yaxis_title="Total runs (filtered)")
        st.plotly_chart(fig5, use_container_width=True)

    st.subheader("Has the strike-rate gap between capped and uncapped players narrowed?")

    min_balls = st.slider("Minimum balls faced (per season)", 10, 60, 30, key="sr_min_balls")
    d_season = d.merge(m[["match_id", "season"]], on="match_id")
    batter_season = d_season.groupby(["season", "striker"])["batsman_runs"].sum().reset_index()
    balls_faced = d_season.groupby(["season", "striker"]).size().reset_index(name="balls")
    batter_season = batter_season.merge(balls_faced, on=["season", "striker"])
    batter_season["strike_rate"] = batter_season["batsman_runs"] / batter_season["balls"] * 100
    batter_season = batter_season.merge(
        players[["player_name", "is_capped_international"]],
        left_on="striker", right_on="player_name", how="left",
    )
    batter_season = batter_season[batter_season["balls"] >= min_balls]

    sr_trend = (
        batter_season.groupby(["season", "is_capped_international"])["strike_rate"]
        .mean().reset_index()
    )
    if sr_trend.empty:
        st.info("No batters meet this minimum-balls threshold with the current filters — lower it or widen filters.")
    else:
        fig6 = px.line(
            sr_trend, x="season", y="strike_rate", color="is_capped_international", markers=True,
            template=TEMPLATE,
            color_discrete_map={True: PALETTE["highlight"], False: PALETTE["context"]},
            title="Capped vs. uncapped average strike rate over time",
        )
        fig6.for_each_trace(lambda t: t.update(name="Capped" if t.name == "True" else "Uncapped"))
        fig6.update_layout(xaxis_title="Season", yaxis_title="Avg strike rate", legend_title="")
        st.plotly_chart(fig6, use_container_width=True)

# ==================================================================
# TAB 4 — Bowling Matchups
# ==================================================================
with tab4:
    st.subheader("Which bowlers are most effective against which opposition?")

    top_n = st.slider("Number of top wicket-takers to show", 5, 25, 15, key="top_bowlers")
    wickets = d[d["is_wicket"] == True]
    bowler_vs_team = wickets.groupby(["bowler", "batting_team"]).size().reset_index(name="wickets")
    top_bowlers = wickets["bowler"].value_counts().head(top_n).index
    heat_data = bowler_vs_team[bowler_vs_team["bowler"].isin(top_bowlers)]

    if heat_data.empty:
        st.info("Not enough wickets in the current filter to build this view — widen your filters.")
    else:
        heat_pivot = heat_data.pivot(index="bowler", columns="batting_team", values="wickets").fillna(0)
        fig10 = px.imshow(
            heat_pivot, template=TEMPLATE, color_continuous_scale="Oranges", aspect="auto",
            title="Top wicket-takers' effectiveness varies sharply by opposition",
        )
        fig10.update_layout(xaxis_title="Batting team (opposition)", yaxis_title="Bowler")
        st.plotly_chart(fig10, use_container_width=True)

    st.subheader("Death-over economy vs. wickets — pace vs. spin")

    death = d[d["over"] >= 16]
    death_stats = death.groupby("bowler").agg(
        runs_conceded=("total_runs", "sum"),
        balls=("delivery_id", "count"),
        wickets=("is_wicket", "sum"),
    ).reset_index()
    death_stats["economy"] = death_stats["runs_conceded"] / (death_stats["balls"] / 6)
    death_stats = death_stats[death_stats["balls"] >= 12]
    death_stats = death_stats.merge(
        players[["player_name", "bowling_style"]], left_on="bowler", right_on="player_name", how="left"
    )
    death_stats["style_group"] = death_stats["bowling_style"].apply(
        lambda x: "Spin" if isinstance(x, str) and "spin" in x.lower() else "Pace/Other"
    )

    if death_stats.empty:
        st.info("Not enough death-over data in the current filter — widen your filters.")
    else:
        fig11 = px.scatter(
            death_stats, x="economy", y="wickets", color="style_group", hover_name="bowler",
            template=TEMPLATE,
            color_discrete_map={"Spin": PALETTE["highlight"], "Pace/Other": PALETTE["blue"]},
            title="Spin bowlers trade runs for strikes differently than pace at the death",
        )
        fig11.update_layout(
            xaxis_title="Economy rate (overs 16-20)", yaxis_title="Wickets taken (overs 16-20)",
            legend_title="",
        )
        st.plotly_chart(fig11, use_container_width=True)

st.markdown("---")
st.caption("Final Individual Project · Data Visualization · Summer 2026")
