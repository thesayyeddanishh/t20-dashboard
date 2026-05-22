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
    # Create 4 columns side-by-side for your filters and criteria threshold
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
                    df_filtered = df_raw[df_raw["BounceX"] < 0.5]
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
            # Group by your exact column name: 'BatsmanName'
            leaderboard = df_filtered.groupby("BatsmanName").agg(
                Runs=("Runs", "sum"),
                Balls_Faced=("Wicket", "count"),
                Dismissals=("Wicket", lambda x: sorted(x).count(True))
            ).reset_index()

            # Filter data using the input box criteria
            leaderboard = leaderboard[leaderboard["Balls_Faced"] >= min_balls]

            if not leaderboard.empty:
                # Calculate Strike Rate (Runs / Balls * 100)
                leaderboard["Strike Rate"] = (leaderboard["Runs"] / leaderboard["Balls_Faced"]) * 100
                
                # Sort by Strike Rate descending and get top 10 rows
                leaderboard = leaderboard.sort_values(by="Strike Rate", ascending=False).head(10)
                
                # Format columns neatly
                leaderboard["Strike Rate"] = leaderboard["Strike Rate"].round(1)
                leaderboard["Runs"] = leaderboard["Runs"].astype(int)
                
                # Assign precise column titles requested
                leaderboard.columns = ["Batter", "Runs", "Balls faced", "Dismissals", "Strike Rate"]
                
                st.subheader(f"Top 10 Batters by Strike Rate  vs {filter_label} (Min {min_balls} Balls)")
                
                # --- EXPLICIT COLUMN & HEADER CONFIGURATION ---
                column_configuration = {
                    "Batter": st.column_config.TextColumn(width=200),
                    "Runs": st.column_config.NumberColumn(alignment="center", width=50),
                    "Balls faced": st.column_config.NumberColumn(alignment="center", width=75),
                    "Dismissals": st.column_config.NumberColumn(alignment="center", width=75),
                    "Strike Rate": st.column_config.NumberColumn(alignment="center", width=100),
                }
                
                # Render the dataframe cleanly at its true pixel dimensions without stretching
                st.dataframe(
                    leaderboard.set_index("Batter"), 
                    use_container_width=False, 
                    column_config=column_configuration
                )
            else:
                st.info(f"No batters met the threshold rules of facing at least {min_balls} balls in this selection.")
        else:
            st.info("No delivery records found matching this filter combo in your data.")

    # ==================================================================
    # BRANCH 2 & 3: PACERS / SPINNERS PLACEHOLDERS
    # ==================================================================
    elif f1 in ["PACERS", "SPINNERS"]:
        st.subheader(f"🛠️ {f1} Performance Comparison Rules")
        st.info(f"This section is ready. Next, we will drop the exact filter combinations and grouping paths for your bowlers here.")
