import streamlit as st
import pandas as pd
import numpy as np

# Set page configuration to match your wide layout preference
st.set_page_config(layout="wide")

# --- CUSTOM CSS TO FORCE HEADER CENTERING ---
st.markdown(
    """
    <style>
        /* Force both standard and containerized table headers to align center */
        th[data-testid="stTableHeadCell"] {
            text-align: center !important;
        }
        th {
            text-align: center !important;
        }
        div[data-testid="stTableHeadCellContent"] {
            justify-content: center !important;
            text-align: center !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("🏆 Player Performance Comparison")
st.markdown("Instantly rank players based on custom situational criteria and thresholds.")

# --- 1. SESSION STATE DATA CHECK ---
if 'data_df' not in st.session_state or st.session_state['data_df'] is None:
    st.warning("⚠️ No data found! Please go back to the HOME page and upload your CSV file first.")
else:
    # Safely extract and copy the dataframe
    df_raw = st.session_state['data_df'].copy()
    
    # Clean and explicitly prepare data types for accurate filtering
    df_raw["ReleaseSpeed"] = pd.to_numeric(df_raw["ReleaseSpeed"], errors="coerce")
    df_raw["BounceX"] = pd.to_numeric(df_raw["BounceX"], errors="coerce")
    df_raw["Wicket"] = df_raw["Wicket"].astype(bool)
    df_raw["Runs"] = pd.to_numeric(df_raw["Runs"], errors="coerce").fillna(0)

    # ------------------------------------------------------------------
    # --- DYNAMIC HORIZONTAL FILTER ROW ---
    # ------------------------------------------------------------------
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        f1 = st.selectbox("Select Player Role", ["BATTERS", "PACERS", "SPINNERS"])
    
    # Objects to hold our conditional data slice
    df_filtered = pd.DataFrame()
    filter_label = ""

    # ==================================================================
    # BRANCH 1: BATTERS SELECTION
    # ==================================================================
    if f1 == "BATTERS":
        
        with col2:
            f2 = st.selectbox("SR by Length / Pace", ["LENGTH", "PACE"])
        
        with col3:
            if f2 == "LENGTH":
                f3 = st.selectbox(
                    "Select Length", 
                    ["FULL TOSS", "YORKER", "THE SLOT", "LENGTH", "SHORT", "BOUNCER"]
                )
                filter_label = f3
                
                # Map selection to your pitch data ranges (BounceX)
                if f3 == "FULL TOSS":
                    df_filtered = df_raw[df_raw["BounceX"] < 2.5]
                elif f3 == "YORKER":
                    df_filtered = df_raw[df_raw["BounceX"] < 2.5]
                elif f3 == "THE SLOT":
                    df_filtered = df_raw[(df_raw["BounceX"] >= 2.5) & (df_raw["BounceX"] < 5.8)]
                elif f3 == "LENGTH":
                    df_filtered = df_raw[(df_raw["BounceX"] >= 5.8) & (df_raw["BounceX"] < 8.0)]
                elif f3 == "SHORT":
                    df_filtered = df_raw[(df_raw["BounceX"] >= 8.0) & (df_raw["BounceX"] < 10.0)]
                elif f3 == "BOUNCER":
                    df_filtered = df_raw[df_raw["BounceX"] >= 10.0]

            elif f2 == "PACE":
                f3 = st.selectbox("Select Pace", ["Above 140", "Below 125"])
                filter_label = f"Pace ({f3} kph)"
                
                if f3 == "Above 140":
                    df_filtered = df_raw[df_raw["ReleaseSpeed"] > 140]
                elif f3 == "Below 125":
                    df_filtered = df_raw[df_raw["ReleaseSpeed"] < 125]

        with col4:
            min_balls = st.number_input("Minimum balls faced", min_value=1, value=10, step=1)

        # --- GENERATE DATA TABLE LEADERBOARD ---
        if not df_filtered.empty:
            batter_col = "Batter" if "Batter" in df_filtered.columns else "BatsmanName
        
