
import streamlit as st
import pandas as pd
import numpy as np

# --- 1. CONFIGURATION & SESSION STATE DATA CHECK ---
st.set_page_config(layout="wide")

st.title("🏆 Player Performance Comparison")
st.markdown("Instantly rank players based on custom situational criteria and thresholds.")

# Check if your main data file is loaded in Session State from your HOME page
if "df_all" not in st.session_state or st.session_state["df_all"] is None:
    st.warning("⚠️ No data found! Please go back to the HOME page and upload your data CSV/text file first.")
else:
    # Use the shared data frame
    df_raw = st.session_state["df_all"].copy()
    
    # Clean and explicitly prepare types for calculations
    df_raw["ReleaseSpeed"] = pd.to_numeric(df_raw["ReleaseSpeed"], errors="coerce")
    df_raw["BounceX"] = pd.to_numeric(df_raw["BounceX"], errors="coerce")
    df_raw["Wicket"] = df_raw["Wicket"].astype(bool)
    df_raw["Runs"] = pd.to_numeric(df_raw["Runs"], errors="coerce").fillna(0)

    # ------------------------------------------------------------------
    # --- FILTER 1: PRIMARY ROLE ---
    # ------------------------------------------------------------------
    f1 = st.selectbox("Select Role Category (FILTER 1)", ["BATTERS", "PACERS", "SPINNERS"])
    
    # Initialize our filtered data carrier
    df_filtered = pd.DataFrame()
    filter_context_name = ""

    # ==================================================================
    # BRANCH A: BATTERS
    # ==================================================================
    if f1 == "BATTERS":
        # --- FILTER 2: VIEW TYPE ---
        f2 = st.selectbox("Select View Type (FILTER 2)", ["LENGTH", "PACE"])
        
        # --- FILTER 3: SITUATIONAL CRITERIA ---
        if f2 == "LENGTH":
            f3 = st.selectbox(
                "Select Length Category (FILTER 3)", 
                ["FULL TOSS", "YORKER", "THE SLOT", "LENGTH", "SHORT", "BOUNCER"]
            )
            filter_context_name = f3
            
            # Grouping parameters based on typical pitch map dimensions
            if f3 == "FULL TOSS":
                df_filtered = df_raw[df_raw["BounceX"].isnull()]
            elif f3 == "YORKER":
                df_filtered = df_raw[df_raw["BounceX"] < 2.5]
            elif f3 == "THE SLOT":
                df_filtered = df_raw[(df_raw["BounceX"] >= 2.5) & (df_raw["BounceX"] < 4.0)]
            elif f3 == "LENGTH":
                df_filtered = df_raw[(df_raw["BounceX"] >= 4.0) & (df_raw["BounceX"] < 7.0)]
            elif f3 == "SHORT":
                df_filtered = df_raw[(df_raw["BounceX"] >= 7.0) & (df_raw["BounceX"] < 10.0)]
            elif f3 == "BOUNCER":
                df_filtered = df_raw[df_raw["BounceX"] >= 10.0]

        elif f2 == "PACE":
            f3 = st.selectbox("Select Pace Category (FILTER 3)", ["Above 140", "Below 125"])
            filter_context_name = f"Bowling Speed ({f3} kph)"
            
            if f3 == "Above 140":
                df_filtered = df_raw[df_raw["ReleaseSpeed"] > 140]
            elif f3 == "Below 125":
                df_filtered = df_raw[df_raw["ReleaseSpeed"] < 125]

        # --- USER INPUT THRESHOLD RULE ---
        min_balls = st.number_input("Minimum Balls Faced Threshold Rule", min_value=1, value=10, step=5)

        # --- PROCESS LEADERBOARD AND RENDER TABLE ---
        if not df_filtered.empty:
            # Group data explicitly by the batsman column name matching your pacers file
            leaderboard = df_filtered.groupby("BatsmanName").agg(
                Runs=("Runs", "sum"),
                Balls_Faced=("Wicket", "count"),
                Dismissals=("Wicket", lambda x: sorted(x).count(True))
            ).reset_index()

            # Filter rows based on your threshold criteria box
            leaderboard = leaderboard[leaderboard["Balls_Faced"] >= min_balls]

            if not leaderboard.empty:
                # Calculate Strike Rate (Runs / Balls * 100)
                leaderboard["Strike Rate"] = (leaderboard["Runs"] / leaderboard["Balls_Faced"]) * 100
                
                # Sort cleanly by Strike Rate descending, pull top 10 rows
                leaderboard = leaderboard.sort_values(by="Strike Rate", ascending=False).head(10)
                
                # Polish formats
                leaderboard["Strike Rate"] = leaderboard["Strike Rate"].round(1)
                leaderboard["Runs"] = leaderboard["Runs"].astype(int)
                
                # Clean up display titles for presentation layout
                leaderboard.columns = ["Batter Name", "Runs", "Balls Faced", "Dismissals", "Strike Rate"]
                
                st.subheader(f"📊 Top 10 Batters vs {filter_context_name} (Min {min_balls} Balls)")
                st.dataframe(leaderboard.set_index("Batter Name"), use_container_width=True)
            else:
                st.info(f"No batters met your custom cutoff criteria of facing at least {min_balls} deliveries in this zone.")
        else:
            st.info("No delivery logs match this specific situational criteria mix in the uploaded data.")

    # ==================================================================
    # BRANCH B & C: PACERS / SPINNERS (PLACEHOLDERS)
    # ==================================================================
    elif f1 in ["PACERS", "SPINNERS"]:
        st.subheader(f"🛠️ {f1} Filtering Rules Pipeline")
        st.info(f"Ready! Drop your filter architecture layouts for {f1} here. We will apply the exact same grouping gates using BowlerName splits.")
