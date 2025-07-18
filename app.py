import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
import os
import datetime

st.set_page_config(page_title="FPL Fantasy Tracker", layout="wide")
st.title("📊 FPL Fantasy Tracker 2025/26")

# === Load Excel ===
@st.cache_data
def load_data():
    return pd.read_excel("fpl_fantasy_dashboard.xlsx")

df = load_data()

# ==== Alertas visuales de status ====
def status_emoji(status):
    if status == 'a':  # available
        return "✅"
    elif status == 'd':  # doubtful
        return "❓"
    elif status == 'i':  # injured
        return "🚑"
    elif status == 's':  # suspended
        return "⛔"
    else:
        return "🔍"

df["Status"] = df["status"].apply(status_emoji) if "status" in df.columns else ""
df["News"] = df["news"].fillna("").str[:60] if "news" in df.columns else ""

# ==== Sidebar: info y tooltips ====
with st.sidebar.expander("ℹ️ Metrics explained"):
    st.markdown("""
    - **Points/Game**: Average points per match  
    - **Points per Million**: Total points divided by price in £m  
    - **value_season**: Total points / price  
    - **form**: Recent FPL form  
    - **expected_goals_per_90**: xG per 90 mins  
    - **Status**: ✅ Available / ❓ Doubtful / 🚑 Injured / ⛔ Suspended  
    """)

# ==== Sidebar: fecha de actualización ====
st.sidebar.markdown("---")
if os.path.exists("fpl_fantasy_dashboard.xlsx"):
    last_modified = datetime.datetime.fromtimestamp(os.path.getmtime("fpl_fantasy_dashboard.xlsx"))
    st.sidebar.write(f"📅 Data updated: {last_modified.strftime('%Y-%m-%d %H:%M')}")


# ==== Tabs principales ====
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 Player List", "🔥 Top Picks", "📈 Performance", "⚔️ Comparison", "⚽️ Set Pieces"
])

# ==== TAB 1: Filters + Table ====
with tab1:
    st.sidebar.header("🔎 Filter Players")

    # Posición y equipo
    position = st.sidebar.multiselect("Position", sorted(df["Position"].unique()), default=df["Position"].unique())
    team = st.sidebar.multiselect("Team", sorted(df["Team"].unique()), default=df["Team"].unique())

    # Precio máximo
    max_price = st.sidebar.slider(
        "Max Price (£m)",
        float(df["Price (£m)"].min()),
        float(df["Price (£m)"].max()),
        float(df["Price (£m)"].max()),
        step=0.5
    )

    # Minutos jugados
    min_minutes = st.sidebar.slider(
        "Min Minutes Played",
        0,
        int(df["minutes"].max()) if not df["minutes"].isna().all() else 0,
        0,
        step=90
    )

    # Form (protección si min == max)
    form_min = float(df["form"].min())
    form_max = float(df["form"].max())
    if form_min == form_max:
        st.sidebar.info("Form data not available yet.")
        min_form = form_min
    else:
        min_form = st.sidebar.slider("Min Form", form_min, form_max, form_min)

    # Value/Season (protección si min == max)
    value_min = float(df["value_season"].min())
    value_max = float(df["value_season"].max())
    if value_min == value_max:
        st.sidebar.info("Value/Season data not available yet.")
        min_value = value_min
    else:
        min_value = st.sidebar.slider("Min Value/Season", value_min, value_max, value_min)

    # % seleccionados
    max_selected = st.sidebar.slider("Max % Selected", 0.0, 100.0, 100.0, step=1.0)

    # === Aplicar filtros
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

    # === Tabla y selección de columnas
    st.subheader(f"📋 {len(filtered_df)} Players Found")

    all_cols = list(filtered_df.columns)
    selected_cols = st.multiselect("Columns to display", all_cols, default=[
        "Player", "Team", "Position", "Price (£m)", "Total Points", "Points/Game",
        "Points per Million", "% Selected", "Status", "News"
    ])
    st.dataframe(filtered_df[selected_cols], use_container_width=True)

    # === Botón de descarga
    st.download_button(
        label="📥 Download table as CSV",
        data=filtered_df[selected_cols].to_csv(index=False).encode('utf-8'),
        file_name='filtered_players.csv',
        mime='text/csv'
    )

# ==== TAB 2: Top Picks y Diferenciales ====
with tab2:
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

    # Descarga
    st.download_button(
        label="📥 Download Top Picks CSV",
        data=top_df.to_csv(index=False).encode('utf-8'),
        file_name='top_10_points_per_million.csv',
        mime='text/csv'
    )

# ==== TAB 3: Player Performance por Gameweek ====
with tab3:
    st.subheader("📈 Gameweek Performance")
    player_name = st.selectbox("Choose a player", df["Player"].unique())
    player_id = df[df["Player"] == player_name]["Player ID"].values[0]

    @st.cache_data
    def get_history(player_id):
        url = f"https://fantasy.premierleague.com/api/element-summary/{int(player_id)}/"
        res = requests.get(url)
        if res.status_code != 200:
            return pd.DataFrame()
        return pd.DataFrame(res.json()["history"])

    history_df = get_history(player_id)

    if not history_df.empty:
        fig = px.line(history_df, x="round", y="total_points", title=f"{player_name} - Points per Gameweek")
        st.plotly_chart(fig)
    else:
        st.info("No gameweek data yet.")

# ==== TAB 4: Radar Chart + Bar Chart (Comparador) ====
with tab4:
    st.subheader("⚔️ Compare Players (Radar Chart)")

    radar_metrics = [
        "Points/Game", "Points per Million", "Price (£m)", 
        "form", "value_season", "expected_goals_per_90", "expected_assists_per_90"
    ]

    player_options = df["Player"].dropna().unique()
    selected = st.multiselect("Select players", player_options, default=player_options[:2])

    if len(selected) >= 2:
        # Extraer y limpiar datos
        compare_df = df[df["Player"].isin(selected)][["Player"] + radar_metrics].copy()
        compare_df.dropna(subset=radar_metrics, inplace=True)
        compare_df.set_index("Player", inplace=True)

        if compare_df.empty:
            st.warning("Selected players have missing or incomplete metric data.")
        else:
            # Filtrar columnas con al menos 2 valores no cero para que sean visualmente útiles
            non_zero_cols = compare_df.loc[:, (compare_df != 0).sum() > 1]

            if non_zero_cols.shape[1] <= 1:
                st.warning("Not enough comparable metrics. Try different players.")
            else:
                # Normalizar
                normalized_df = (non_zero_cols - non_zero_cols.min()) / (non_zero_cols.max() - non_zero_cols.min())
                melted = normalized_df.reset_index().melt(id_vars="Player", var_name="Metric", value_name="Value")

                import plotly.express as px
                fig = px.line_polar(
                    melted,
                    r="Value",
                    theta="Metric",
                    color="Player",
                    line_close=True,
                    title="🔄 Player Radar Comparison"
                )
                fig.update_traces(fill='toself', opacity=0.6)
                fig.update_layout(legend_title_text='Player')
                st.plotly_chart(fig, use_container_width=True)

                # Descarga
                st.download_button(
                    label="📥 Download Comparison Data (Normalized)",
                    data=normalized_df.reset_index().to_csv(index=False).encode('utf-8'),
                    file_name="player_radar_comparison.csv",
                    mime="text/csv"
                )
    else:
        st.info("Select at least 2 players to compare.")


# ==== TAB 5: Set Piece Takers (Corners, Freekicks, Penalties) ====
with tab5:
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

