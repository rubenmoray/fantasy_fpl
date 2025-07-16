import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# === Configuración inicial ===
st.set_page_config(page_title="FPL Fantasy Tracker", layout="wide")

st.title("📊 FPL Fantasy Tracker 2025/26")
st.markdown("Make smarter picks with real-time data from the official FPL API.")

# === Cargar el Excel ===
@st.cache_data
def load_data():
    return pd.read_excel("fpl_fantasy_dashboard.xlsx")

df = load_data()

# === Sidebar: filtros ===
st.sidebar.header("🔎 Filter Players")

position = st.sidebar.multiselect(
    "Position", options=sorted(df["Position"].unique()), default=df["Position"].unique()
)

team = st.sidebar.multiselect(
    "Team", options=sorted(df["Team"].unique()), default=df["Team"].unique()
)

max_price = st.sidebar.slider("Max Price (£M)", min_value=3.5, max_value=13.0, value=13.0, step=0.5)

# === Aplicar filtros ===
filtered_df = df[
    (df["Position"].isin(position)) &
    (df["Team"].isin(team)) &
    (df["Price (£m)"] <= max_price)
]

# === Mostrar métricas rápidas ===
st.subheader(f"📋 {len(filtered_df)} Players Found")
st.dataframe(filtered_df.style.format({
    "Price (£m)": "{:.1f}",
    "Points/Game": "{:.1f}",
    "Points per Million": "{:.1f}",
    "% Selected": "{:.1f}"
}), use_container_width=True)

# === Top 10 por valor fantasy ===
st.subheader("🔥 Top 10 Players by Points per Million")
top_df = filtered_df.sort_values(by="Points per Million", ascending=False).head(10)
st.table(top_df[["Player", "Team", "Position", "Points/Game", "Points per Million", "Price (£m)"]])

# === Top 10 por puntos totales (si disponible) ===
if "Total Points" in filtered_df.columns:
    st.subheader("🏅 Top 10 Players by Total Points")
    top_total = filtered_df.sort_values(by="Total Points", ascending=False).head(10)

    fig, ax = plt.subplots()
    ax.barh(top_total["Player"], top_total["Total Points"])
    ax.invert_yaxis()
    ax.set_xlabel("Total Points")
    ax.set_title("Top 10 Players - Total Points")
    st.pyplot(fig)

# === Comparador de jugadores ===
st.subheader("⚔️ Compare Two Players")

players = filtered_df["Player"].unique()
player1 = st.selectbox("Player 1", players)
player2 = st.selectbox("Player 2", players, index=1 if len(players) > 1 else 0)

if player1 and player2 and player1 != player2:
    p1 = filtered_df[filtered_df["Player"] == player1].iloc[0]
    p2 = filtered_df[filtered_df["Player"] == player2].iloc[0]

    metrics = ["Price (£m)", "Points/Game", "Points per Million", "% Selected"]
    comparison = pd.DataFrame({
        "Metric": metrics,
        player1: [p1[m] for m in metrics],
        player2: [p2[m] for m in metrics]
    })

    st.table(comparison.set_index("Metric"))

# === Footer ===
st.markdown("""
---
Built by a Data Scientist & FPL addict • [GitHub](https://github.com/) • [Buy Me a Coffee](https://buymeacoffee.com/)
""")
