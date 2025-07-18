
import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import os
import datetime

st.set_page_config(page_title="FPL Fantasy Tracker", layout="wide")
st.title("📊 FPL Fantasy Tracker 2025/26")

# === Load Excel ===
@st.cache_data
def load_data():
    return pd.read_excel("fpl_fantasy_dashboard.xlsx")

df = load_data()

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
with tab3:
    if has_access:
        st.subheader("📈 Gameweek Performance")
        player_name = st.selectbox("Choose a player", df["Player"].unique())
        player_id = df[df["Player"] == player_name]["Player ID"].values[0]

        @st.cache_data
        def get_history(player_id):
            url = f"https://fantasy.premierleague.com/api/element-summary/{int(player_id)}/"
            res = requests.get(url)
            return pd.DataFrame(res.json()["history"]) if res.status_code == 200 else pd.DataFrame()

        history_df = get_history(player_id)
        if not history_df.empty:
            fig = px.line(history_df, x="round", y="total_points", title=f"{player_name} - Points per Gameweek")
            st.plotly_chart(fig)
        else:
            st.info("No gameweek data yet.")
    else:
        st.warning("🔐 Premium feature. Enter access code in sidebar to unlock.")
        st.markdown("👉 [Buy your access code on Gumroad](https://youruser.gumroad.com/l/fpl-premium-access)")

# ==== TAB 4 ====
with tab4:
    if has_access:
        st.subheader("⚔️ Compare Players (Radar Chart)")
        # Aquí va tu radar chart y comparador completo
        st.info("Radar comparison visible here.")
    else:
        st.warning("🔐 Premium feature. Enter access code in sidebar to unlock.")
        st.markdown("👉 [Buy your access code on Gumroad](https://youruser.gumroad.com/l/fpl-premium-access)")

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
        st.markdown("👉 [Buy your access code on Gumroad](https://youruser.gumroad.com/l/fpl-premium-access)")
