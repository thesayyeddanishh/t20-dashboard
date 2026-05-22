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
            # Fallback handling in case of layout variations between 'Batter' and 'BatsmanName'
            batter_col = "Batter" if "Batter" in df_filtered.columns else "BatsmanName"
            
            leaderboard = df_filtered.groupby(batter_col).agg(
                Runs=("Runs", "sum"),
                Balls_Faced=("Wicket", "count"),
                Dismissals=("Wicket", lambda x: sorted(x).count(True))
            ).reset_index()

            leaderboard = leaderboard[leaderboard["Balls_Faced"] >= min_balls]

            if not leaderboard.empty:
                leaderboard["Strike Rate"] = (leaderboard["Runs"] / leaderboard["Balls_Faced"]) * 100
                leaderboard = leaderboard.sort_values(by="Strike Rate", ascending=False).head(10)
                
                leaderboard["Strike Rate"] = leaderboard["Strike Rate"].round(1)
                leaderboard["Runs"] = leaderboard["Runs"].astype(int)
                
                leaderboard.columns = ["Batter", "Runs", "Balls faced", "Dismissals", "Strike Rate"]
                
                st.subheader(f"📊 Top 10 Batters by Strike Rate vs {filter_label} (Min {min_balls} Balls)")
                
                column_configuration = {
                    "Batter": st.column_config.TextColumn(width=200),
                    "Runs": st.column_config.NumberColumn(alignment="center", width=75),
                    "Balls faced": st.column_config.NumberColumn(alignment="center", width=75),
                    "Dismissals": st.column_config.NumberColumn(alignment="center", width=75),
                    "Strike Rate": st.column_config.NumberColumn(alignment="center", width=100),
                }
                
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
    # BRANCH 2: PACERS SELECTION
    # ==================================================================
    elif f1 == "PACERS":
        
        with col2:
            f2 = st.selectbox(
                "View Type", 
                ["Economy By Length", "% by Lengths", "% Economy by Pace"]
            )
        
        with col3:
            if f2 in ["Economy By Length", "% by Lengths"]:
                f3 = st.selectbox(
                    "Select Length", 
                    ["FULL TOSS", "YORKER", "THE SLOT", "LENGTH", "SHORT", "BOUNCER"]
                )
                filter_label = f3
                
                # Filter the subset based on pitch lengths using your exact bins
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
                    
            elif f2 == "% Economy by Pace":
                f3 = st.selectbox("Select Pace Range", ["Above 140", "Below 125"])
                filter_label = f"Pace ({f3} kph)"
                
                if f3 == "Above 140":
                    df_filtered = df_raw[df_raw["ReleaseSpeed"] > 140]
                elif f3 == "Below 125":
                    df_filtered = df_raw[df_raw["ReleaseSpeed"] < 125]

        with col4:
            min_balls = st.number_input("Minimum balls bowled", min_value=1, value=10, step=1)

        # --- PACERS COMPUTATION ENGINE ---
        if "Bowler Name" in df_raw.columns:
            # Calculate overall total balls per bowler first (crucial for % by lengths scaling metric)
            df_bowler_totals = df_raw.groupby("Bowler Name").agg(
                Total_Balls=("Runs", "count")
            ).reset_index()

            if not df_filtered.empty:
                # Group data within our active context filter subset slice
                leaderboard = df_filtered.groupby("Bowler Name").agg(
                    Runs_Conceded=("Runs", "sum"),
                    Balls_Bowled=("Runs", "count"),
                    Wickets=("Wicket", lambda x: sorted(x).count(True))
                ).reset_index()

                # Safely blend the totals back together 
                leaderboard = leaderboard.merge(df_bowler_totals, on="Bowler Name", how="left")

                # Enforce user threshold filtering boundary rules
                leaderboard = leaderboard[leaderboard["Balls_Bowled"] >= min_balls]

                if not leaderboard.empty:
                    # Calculate true Economy Rate metric formula
                    leaderboard["Economy"] = (leaderboard["Runs_Conceded"] / leaderboard["Balls_Bowled"]) * 6
                    leaderboard["Economy"] = leaderboard["Economy"].round(2)

                    # Branch sorting logic order pathways based on notebook map rules
                    if f2 == "% by Lengths":
                        leaderboard["% of Length"] = (leaderboard["Balls_Bowled"] / leaderboard["Total_Balls"]) * 100
                        leaderboard["% of Length"] = leaderboard["% of Length"].round(1)
                        
                        # High percentage mapping takes precedence
                        leaderboard = leaderboard.sort_values(by="% of Length", ascending=False).head(10)
                        
                        final_cols = ["Bowler Name", "Balls_Bowled", "Wickets", "Economy", "% of Length"]
                        col_titles = ["Bowler", "Balls", "Wickets", "Economy", "% of Length"]
                        pct_col_name = "% of Length"
                    else:
                        # Standard economy display ranks lower runs conceded values to the top
                        leaderboard = leaderboard.sort_values(by="Economy", ascending=True).head(10)
                        
                        final_cols = ["Bowler Name", "Balls_Bowled", "Wickets", "Economy"]
                        col_titles = ["Bowler", "Balls", "Wickets", "Economy"]
                        pct_col_name = None

                    # Format visual components safely
                    leaderboard = leaderboard[final_cols]
                    leaderboard.columns = col_titles

                    st.subheader(f"📊 Top 10 Pacers Performance vs {filter_label} ({f2})")

                    column_configuration = {
                        "Bowler": st.column_config.TextColumn(width=200),
                        "Balls": st.column_config.NumberColumn(alignment="center", width=75),
                        "Wickets": st.column_config.NumberColumn(alignment="center", width=75),
                        "Economy": st.column_config.NumberColumn(alignment="center", width=85),
                    }
                    if pct_col_name:
                        column_configuration[pct_col_name] = st.column_config.NumberColumn(alignment="center", width=100, format="%.1f%%")

                    st.dataframe(
                        leaderboard.set_index("Bowler"), 
                        use_container_width=False, 
                        column_config=column_configuration
                    )
                else:
                    st.info(f"No pacers met the threshold rules of bowling at least {min_balls} balls in this scenario.")
            else:
                st.info("No delivery records found matching this filter combo in your data.")
        else:
            st.error("⚠️ Column tracking identifier 'Bowler Name' missing in uploaded sheet format structure.")

    # ==================================================================
    # BRANCH 3: SPINNERS PLACEHOLDER
    # ==================================================================
    elif f1 == "SPINNERS":
        st.subheader(f"🛠️ {f1} Performance Comparison Rules")
        st.info(f"This section is ready. Next, we will drop the exact filter combinations and grouping paths for your spinners here.")
