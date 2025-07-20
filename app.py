
import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import os
import datetime
import plotly.graph_objects as go


st.set_page_config(page_title="FPL Fantasy Tracker", layout="wide")
st.title("📊 FPL Fantasy Tracker 2025/26")

# === Load Excel ===
@st.cache_data
def load_data():
    return pd.read_excel("fpl_fantasy_dashboard.xlsx")

df = load_data()

df = df.apply(pd.to_numeric, errors='ignore')

def safe_get(row, col, default=0):
    value = row.get(col, default)
    try:
        return float(value) if pd.notna(value) else default
    except:
        return default

def calculate_value_score(row):
    pos = row.get("Position", "")
    
    if pos == "GKP":
        score = (
            0.25 * safe_get(row, "Points/Game") +
            0.20 * safe_get(row, "saves_per_90") +
            0.20 * safe_get(row, "clean_sheets_per_90") +
            0.15 * (1 / (safe_get(row, "expected_goals_conceded_per_90") + 0.01)) +
            0.10 * safe_get(row, "form") -
            0.10 * safe_get(row, "Price (£m)")
        )
    elif pos == "DEF":
        score = (
            0.25 * safe_get(row, "Points/Game") +
            0.15 * safe_get(row, "expected_goal_involvements_per_90") +
            0.15 * (1 / (safe_get(row, "expected_goals_conceded_per_90") + 0.01)) +
            0.15 * safe_get(row, "clean_sheets_per_90") +
            0.10 * safe_get(row, "form") +
            0.10 * safe_get(row, "minutes") / 3000 -
            0.05 * safe_get(row, "Price (£m)")
        )
    elif pos == "MID":
        score = (
            0.25 * safe_get(row, "Points/Game") +
            0.20 * safe_get(row, "expected_goals_per_90") +
            0.20 * safe_get(row, "expected_assists_per_90") +
            0.10 * safe_get(row, "expected_goal_involvements_per_90") +
            0.10 * (1 / (safe_get(row, "creativity_rank") + 0.01)) +
            0.10 * safe_get(row, "form") -
            0.05 * safe_get(row, "Price (£m)")
        )
    elif pos == "FWD":
        score = (
            0.30 * safe_get(row, "Points/Game") +
            0.30 * safe_get(row, "expected_goals_per_90") +
            0.15 * safe_get(row, "expected_goal_involvements_per_90") +
            0.10 * safe_get(row, "form") +
            0.10 * safe_get(row, "minutes") / 3000 -
            0.05 * safe_get(row, "Price (£m)")
        )
    else:
        score = 0

    return round(score, 3)

df["Value Score"] = df.apply(calculate_value_score, axis=1)

# === Premium Access ===
st.sidebar.markdown("---")
st.sidebar.subheader("🔐 Premium Access")
access_code = st.sidebar.text_input("Enter access code", type="password")
has_access = access_code == "FPL2025-PRO-ACCESS"

# ==== Alertas visuales de status ====
def status_emoji(status):
    if status == 'a':
        return "✅"
    elif status == 'd':
        return "❓"
    elif status == 'i':
        return "🚑"
    elif status == 's':
        return "⛔"
    else:
        return "🔍"

df["Status"] = df["status"].apply(status_emoji) if "status" in df.columns else ""
df["News"] = df["news"].fillna("").str[:60] if "news" in df.columns else ""

with st.sidebar.expander("ℹ️ Metrics explained"):
    st.markdown("""
    - **Points/Game**: Average points per match  
    - **Points per Million**: Total points divided by price in £m  
    - **value_season**: Total points / price  
    - **form**: Recent FPL form  
    - **expected_goals_per_90**: xG per 90 mins  
    - **Status**: ✅ Available / ❓ Doubtful / 🚑 Injured / ⛔ Suspended  
    """)

st.sidebar.markdown("---")
if os.path.exists("fpl_fantasy_dashboard.xlsx"):
    last_modified = datetime.datetime.fromtimestamp(os.path.getmtime("fpl_fantasy_dashboard.xlsx"))
    st.sidebar.write(f"📅 Data updated: {last_modified.strftime('%Y-%m-%d %H:%M')}")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 Player List", "🔥 Top Picks", "📈 Performance", "⚔️ Comparison", "⚽️ Set Pieces"
])

# ==== TAB 1 ====
with tab1:
    st.sidebar.header("🔎 Filter Players")
    position = st.sidebar.multiselect("Position", sorted(df["Position"].unique()), default=df["Position"].unique())
    team = st.sidebar.multiselect("Team", sorted(df["Team"].unique()), default=df["Team"].unique())
    max_price = st.sidebar.slider("Max Price (£m)", float(df["Price (£m)"].min()), float(df["Price (£m)"].max()), float(df["Price (£m)"].max()), step=0.5)
    min_minutes = st.sidebar.slider("Min Minutes Played", 0, int(df["minutes"].max()) if not df["minutes"].isna().all() else 0, 0, step=90)
    form_min = float(df["form"].min())
    form_max = float(df["form"].max())
    min_form = st.sidebar.slider("Min Form", form_min, form_max, form_min) if form_min != form_max else form_min
    value_min = float(df["value_season"].min())
    value_max = float(df["value_season"].max())
    min_value = st.sidebar.slider("Min Value/Season", value_min, value_max, value_min) if value_min != value_max else value_min
    max_selected = st.sidebar.slider("Max % Selected", 0.0, 100.0, 100.0, step=1.0)

    filtered_df = df[
        (df["Position"].isin(position)) &
        (df["Team"].isin(team)) &
        (df["Price (£m)"] <= max_price) &
        (df["minutes"] >= min_minutes) &
        (df["form"] >= min_form) &
        (df["value_season"] >= min_value) &
        (df["% Selected"] <= max_selected)
    ]

    if st.sidebar.button("Reset Filters"):
        st.experimental_rerun()

    st.subheader(f"📋 {len(filtered_df)} Players Found")
    all_cols = list(filtered_df.columns)
    selected_cols = st.multiselect("Columns to display", all_cols, default=[
        "Player", "Team", "Position", "Price (£m)", "Total Points", "Points/Game",
        "Points per Million", "% Selected", "Status", "News"
    ])
    st.dataframe(filtered_df[selected_cols], use_container_width=True)
    st.download_button("📥 Download table as CSV", data=filtered_df[selected_cols].to_csv(index=False).encode('utf-8'), file_name='filtered_players.csv', mime='text/csv')

# ==== TAB 2 ====
with tab2:
    st.subheader("🎯 Top 10 by Value Score")
    top_value = df.sort_values("Value Score", ascending=False).head(10)
    st.table(top_value[["Player", "Team", "Position", "Value Score", "Price (£m)", "Points/Game", "Status"]])

    st.subheader("🔥 Top 10 by Points per Million")
    top_df = df.sort_values("Points per Million", ascending=False).head(10)
    st.table(top_df[["Player", "Team", "Position", "Points/Game", "Points per Million", "Price (£m)", "Status"]])
    if "Total Points" in df.columns:
        st.subheader("🏅 Top 10 by Total Points")
        top_total = df.sort_values("Total Points", ascending=False).head(10)
        fig = px.bar(top_total, x="Total Points", y="Player", color="Position", orientation="h")
        st.plotly_chart(fig)
    st.subheader("💎 Differential Picks (<10% selected & high value)")
    diff_df = df[(df["% Selected"] < 10) & (df["value_season"] >= df["value_season"].median())]
    st.table(diff_df[["Player", "Team", "Position", "Points/Game", "value_season", "% Selected", "Status"]].sort_values("value_season", ascending=False).head(10))
    st.download_button("📥 Download Top Picks CSV", data=top_df.to_csv(index=False).encode('utf-8'), file_name='top_10_points_per_million.csv', mime='text/csv')

# ==== TAB 3 ====
# ==== TAB 3: Performance ====
with tab3:
    if has_access:
        st.subheader("📈 Gameweek Performance Comparison")

        selected_names = st.multiselect(
            "Select players to compare", 
            sorted(df["Player"].dropna().unique()), 
            default=sorted(df["Player"].dropna().unique())[:2]
        )

        @st.cache_data
        def get_history(player_id):
            url = f"https://fantasy.premierleague.com/api/element-summary/{int(player_id)}/"
            res = requests.get(url)
            return pd.DataFrame(res.json()["history"]) if res.status_code == 200 else pd.DataFrame()

        if len(selected_names) < 1:
            st.info("Please select at least one player.")
        else:
            all_histories = []
            for name in selected_names:
                player_id = df[df["Player"] == name]["Player ID"].values[0]
                history = get_history(player_id)
                if not history.empty:
                    history["Player"] = name
                    all_histories.append(history)

            if all_histories:
                combined = pd.concat(all_histories)
                fig = px.line(
                    combined, 
                    x="round", 
                    y="total_points", 
                    color="Player",
                    markers=True,
                    title="Points per Gameweek"
                )
                fig.update_layout(xaxis_title="Gameweek", yaxis_title="Points")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No gameweek data available yet.")

    else:
        st.warning("🔐 Premium feature. Enter access code in sidebar to unlock.")
        st.markdown("👉 [Buy your access code on Gumroad](https://moray5.gumroad.com/l/rejrzq?wanted=true)")

# ==== TAB 4 ====
import plotly.graph_objects as go  # Asegúrate de tener esto arriba si no está

# ==== TAB 4 ====
with tab4:
    if has_access:
        st.subheader("⚔️ Custom Radar Chart Comparison")

        # 1. Selección de jugadores
        selected_players = st.multiselect(
            "Select players to compare",
            df["Player"].dropna().unique(),
            default=df["Player"].dropna().unique()[:2]
        )

        # 2. Selección de métricas
        numeric_cols = df.select_dtypes(include='number').columns.tolist()
        available_metrics = [col for col in numeric_cols if col not in ["Player ID"]]

        selected_metrics = st.multiselect(
            "Select metrics to compare",
            available_metrics,
            default=["Points/Game", "expected_goals_per_90", "expected_assists_per_90", "Total Points", "Price (£m)"]
        )
        st.warning(
        "⚠️ The radar charts show each stat **on a scale from 0 to 1**, so you can easily compare players even if the original numbers are very different. "
        "If a player has no data for a selected stat, they won’t show up properly on the chart. "
        "For best results, choose stats with consistent data and select **at least 4 players**."
    )


        if len(selected_players) < 2:
            st.info("Please select at least 2 players.")
        elif len(selected_metrics) < 2:
            st.info("Please select at least 2 metrics.")
        else:
            compare_df = df[df["Player"].isin(selected_players)][["Player"] + selected_metrics].dropna()
            compare_df.set_index("Player", inplace=True)

            # Filtrar columnas con al menos 2 valores numéricos > 0
            non_zero = compare_df.loc[:, (compare_df > 0).sum() >= 2]

            if non_zero.shape[1] < 2 or compare_df.shape[0] < 2:
                st.warning("Not enough valid data across players and metrics to build radar.")
            else:
                # Normalizar
                norm = (non_zero - non_zero.min()) / (non_zero.max() - non_zero.min())
                categories = norm.columns.tolist()

                fig = go.Figure()
                for player in norm.index:
                    fig.add_trace(go.Scatterpolar(
                        r=norm.loc[player].values,
                        theta=categories,
                        fill='toself',
                        name=player,
                        opacity=0.6
                    ))

                fig.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
                    showlegend=True,
                    title="🔄 Player Comparison Radar"
                )
                st.plotly_chart(fig, use_container_width=True)

                # Descarga CSV
                st.download_button(
                    label="📥 Download Comparison Data",
                    data=compare_df.reset_index().to_csv(index=False).encode('utf-8'),
                    file_name="custom_player_comparison.csv",
                    mime="text/csv"
                )
    else:
        st.warning("🔐 Premium feature. Enter access code in sidebar to unlock.")
        st.markdown("👉 [Buy your access code on Gumroad](https://moray5.gumroad.com/l/rejrzq?wanted=true)")

# ==== TAB 5 ====
with tab5:
    if has_access:
        st.subheader("⚽️ Set Piece Takers by Team")
        if {"corners_and_indirect_freekicks_order", "direct_freekicks_order", "penalties_order"}.issubset(df.columns):
            st.dataframe(
                df[["Player", "Team", "Position",
                    "corners_and_indirect_freekicks_order", "direct_freekicks_order", "penalties_order", "Status"]]
                .dropna(how="all", subset=["corners_and_indirect_freekicks_order", "direct_freekicks_order", "penalties_order"])
                .sort_values(["Team", "Position"])
            )
        else:
            st.info("Set piece data not available yet.")
    else:
        st.warning("🔐 Premium feature. Enter access code in sidebar to unlock.")
        st.markdown("👉 [Buy your access code on Gumroad](https://moray5.gumroad.com/l/rejrzq?wanted=true)")
