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
    
    # Ensure Over column is parsed cleanly as numbers for matching boundary rules
    if "Over" in df_raw.columns:
        df_raw["Over"] = pd.to_numeric(df_raw["Over"], errors="coerce")

    # ------------------------------------------------------------------
    # --- DYNAMIC HORIZONTAL FILTER LAYOUT ---
    # ------------------------------------------------------------------
    # Row 1: Core category and view parameters
    row1_col1, row1_col2, row1_col3 = st.columns(3)

    with row1_col1:
        f1 = st.selectbox("Select Player Role", ["BATTERS", "PACERS", "SPINNERS"])
    
    # Objects to hold our conditional data slice
    df_filtered = pd.DataFrame()
    filter_label = ""

    # Row 2: Secondary situational constraints and volume limits (Shared visually across roles)
    row2_col1, row2_col2 = st.columns(2)
    
    with row2_col1:
        f_overs = st.selectbox("Match Phase (Overs)", ["All", "Powerplay (1-6)", "Middle (7-16)", "Death (17-20)"])

    # Global/Base phase filtering adjustment rule applied to the primary dataframe copy
    if "Over" in df_raw.columns:
        if f_overs == "Powerplay (1-6)":
            df_raw = df_raw[df_raw["Over"] < 6]
        elif f_overs == "Middle (7-16)":
            df_raw = df_raw[(df_raw["Over"] >= 6) & (df_raw["Over"] < 16)]
        elif f_overs == "Death (17-20)":
            df_raw = df_raw[df_raw["Over"] >= 16]

    # ==================================================================
    # BRANCH 1: BATTERS SELECTION
    # ==================================================================
    if f1 == "BATTERS":
        with row1_col2:
            f2 = st.selectbox("SR by Length / Pace", ["LENGTH", "PACE"])
        
        with row1_col3:
            if f2 == "LENGTH":
                f3 = st.selectbox(
                    "Select Length", 
                    ["FULL TOSS", "YORKER", "THE SLOT", "LENGTH", "SHORT", "BOUNCER"]
                )
                filter_label = f3
                
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

        with row2_col2:
            min_balls = st.number_input("Minimum balls faced", min_value=1, value=10, step=1)

        # --- GENERATE BATTERS DATA TABLE LEADERBOARD ---
        if not df_filtered.empty:
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
                
                st.subheader(f" Top 10 Batters by Strike Rate vs {filter_label} (Min {min_balls} Balls)")
             
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
        # Global filter restriction for Pacers
        df_role_base = df_raw[df_raw["DeliveryType"].str.lower() == "seam"] if "DeliveryType" in df_raw.columns else df_raw.copy()
        
        with row1_col2:
            f2 = st.selectbox(
                "View Type", 
                ["Economy By Length", "% by Lengths", "Economy by Pace", "% Balls by Pace"]
            )
        
        with row1_col3:
            if f2 in ["Economy By Length", "% by Lengths"]:
                f3 = st.selectbox(
                    "Select Length", 
                    ["FULL TOSS", "YORKER", "THE SLOT", "LENGTH", "SHORT", "BOUNCER"]
                )
                filter_label = f3
                
                if f3 == "FULL TOSS":
                    df_filtered = df_role_base[df_role_base["BounceX"] < 2.5]
                elif f3 == "YORKER":
                    df_filtered = df_role_base[df_role_base["BounceX"] < 2.5]
                elif f3 == "THE SLOT":
                    df_filtered = df_role_base[(df_role_base["BounceX"] >= 2.5) & (df_role_base["BounceX"] < 5.8)]
                elif f3 == "LENGTH":
                    df_filtered = df_role_base[(df_role_base["BounceX"] >= 5.8) & (df_role_base["BounceX"] < 8.0)]
                elif f3 == "SHORT":
                    df_filtered = df_role_base[(df_role_base["BounceX"] >= 8.0) & (df_role_base["BounceX"] < 10.0)]
                elif f3 == "BOUNCER":
                    df_filtered = df_role_base[df_role_base["BounceX"] >= 10.0]
                    
            elif f2 in ["Economy by Pace", "% Balls by Pace"]:
                f3 = st.selectbox("Select Pace Range", ["Above 140", "Below 125"])
                filter_label = f"Pace ({f3} kph)"
                
                if f3 == "Above 140":
                    df_filtered = df_role_base[df_role_base["ReleaseSpeed"] > 140]
                elif f3 == "Below 125":
                    df_filtered = df_role_base[df_role_base["ReleaseSpeed"] < 125]

        with row2_col2:
            min_balls = st.number_input("Minimum balls bowled", min_value=1, value=10, step=1)

        # --- PACERS COMPUTATION ENGINE ---
        if "BowlerName" in df_raw.columns:
            # Denominator tracks legal active deliveries for the selected context
            df_bowler_totals = df_role_base.groupby("BowlerName").agg(
                Total_Balls=("Runs", "count")
            ).reset_index()

            if not df_filtered.empty:
                leaderboard = df_filtered.groupby("BowlerName").agg(
                    Runs_Conceded=("Runs", "sum"),
                    Balls_Bowled=("Runs", "count"),
                    Wickets=("Wicket", lambda x: sorted(x).count(True))
                ).reset_index()

                leaderboard = leaderboard.merge(df_bowler_totals, on="BowlerName", how="left")
                leaderboard = leaderboard[leaderboard["Balls_Bowled"] >= min_balls]

                if not leaderboard.empty:
                    leaderboard["Economy"] = (leaderboard["Runs_Conceded"] / leaderboard["Balls_Bowled"]) * 6
                    leaderboard["Economy"] = leaderboard["Economy"].round(2)

                    if f2 == "% by Lengths":
                        leaderboard["% of Length"] = (leaderboard["Balls_Bowled"] / leaderboard["Total_Balls"]) * 100
                        leaderboard["% of Length"] = leaderboard["% of Length"].round(1)
                        leaderboard = leaderboard.sort_values(by="% of Length", ascending=False).head(10)
                        
                        final_cols = ["BowlerName", "Balls_Bowled", "Wickets", "Economy", "% of Length"]
                        col_titles = ["Bowler", "Balls", "Wickets", "Economy", "% of Length"]
                        pct_col_name = "% of Length"
                        
                    elif f2 == "% Balls by Pace":
                        leaderboard["% of Pace Context"] = (leaderboard["Balls_Bowled"] / leaderboard["Total_Balls"]) * 100
                        leaderboard["% of Pace Context"] = leaderboard["% of Pace Context"].round(1)
                        leaderboard = leaderboard.sort_values(by="% of Pace Context", ascending=False).head(10)
                        
                        final_cols = ["BowlerName", "Balls_Bowled", "Wickets", "Economy", "% of Pace Context"]
                        col_titles = ["Bowler", "Balls", "Wickets", "Economy", "% of Pace"]
                        pct_col_name = "% of Pace"
                        
                    else:
                        leaderboard = leaderboard.sort_values(by="Economy", ascending=True).head(10)
                        
                        final_cols = ["BowlerName", "Balls_Bowled", "Wickets", "Economy"]
                        col_titles = ["Bowler", "Balls", "Wickets", "Economy"]
                        pct_col_name = None

                    leaderboard = leaderboard[final_cols]
                    leaderboard.columns = col_titles

                    # Clean descriptive table subheader capturing all filters
                    st.subheader(f"Top 10 Pacers' Performance vs {filter_label}")

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
            st.error("⚠️ Column tracking identifier 'BowlerName' missing in uploaded sheet format structure.")

    # ==================================================================
    # BRANCH 3: SPINNERS SELECTION
    # ==================================================================
    elif f1 == "SPINNERS":
        # Global filter restriction for Spinners
        df_role_base = df_raw[df_raw["DeliveryType"].str.lower() == "spin"] if "DeliveryType" in df_raw.columns else df_raw.copy()
        
        with row1_col2:
            f2 = st.selectbox(
                "View Type", 
                ["Economy By Length", "% by Lengths", "% /Away/No/In (TURN)"]
            )
        
        with row1_col3:
            if f2 in ["Economy By Length", "% by Lengths"]:
                f3 = st.selectbox(
                    "Select Length", 
                    ["FULL TOSS", "YORKER", "THE SLOT", "LENGTH", "SHORT", "BOUNCER"]
                )
                filter_label = f3
                
                if f3 == "FULL TOSS":
                    df_filtered = df_role_base[df_role_base["BounceX"] < 2.5]
                elif f3 == "YORKER":
                    df_filtered = df_role_base[df_role_base["BounceX"] < 2.5]
                elif f3 == "THE SLOT":
                    df_filtered = df_role_base[(df_role_base["BounceX"] >= 2.5) & (df_role_base["BounceX"] < 5.8)]
                elif f3 == "LENGTH":
                    df_filtered = df_role_base[(df_role_base["BounceX"] >= 5.8) & (df_role_base["BounceX"] < 8.0)]
                elif f3 == "SHORT":
                    df_filtered = df_role_base[(df_role_base["BounceX"] >= 8.0) & (df_role_base["BounceX"] < 10.0)]
                elif f3 == "BOUNCER":
                    df_filtered = df_role_base[df_role_base["BounceX"] >= 10.0]
                    
            elif f2 == "% /Away/No/In (TURN)":
                f3 = st.selectbox("Select Ball Break Direction", ["Away from Batter", "Into Batter", "No Turn"])
                filter_label = f3
                df_filtered = df_role_base.copy()

        with row2_col2:
            min_balls = st.number_input("Minimum balls bowled", min_value=1, value=10, step=1)

        # --- SPINNERS COMPUTATION ENGINE ---
        if "BowlerName" in df_raw.columns:
            df_bowler_totals = df_role_base.groupby("BowlerName").agg(
                Total_Balls=("Runs", "count")
            ).reset_index()

            if not df_filtered.empty:
                leaderboard = df_filtered.groupby("BowlerName").agg(
                    Runs_Conceded=("Runs", "sum"),
                    Balls_Bowled=("Runs", "count"),
                    Wickets=("Wicket", lambda x: sorted(x).count(True))
                ).reset_index()

                leaderboard = leaderboard.merge(df_bowler_totals, on="BowlerName", how="left")
                leaderboard = leaderboard[leaderboard["Balls_Bowled"] >= min_balls]

                if not leaderboard.empty:
                    leaderboard["Economy"] = (leaderboard["Runs_Conceded"] / leaderboard["Balls_Bowled"]) * 6
                    leaderboard["Economy"] = leaderboard["Economy"].round(2)

                    if f2 in ["% by Lengths", "% /Away/No/In (TURN)"]:
                        leaderboard["% Metric"] = (leaderboard["Balls_Bowled"] / leaderboard["Total_Balls"]) * 100
                        leaderboard["% Metric"] = leaderboard["% Metric"].round(1)
                        leaderboard = leaderboard.sort_values(by="% Metric", ascending=False).head(10)
                        
                        final_cols = ["BowlerName", "Balls_Bowled", "Wickets", "Economy", "% Metric"]
                        col_titles = ["Bowler", "Balls", "Wickets", "Economy", "% Metric"]
                        pct_col_name = "% Metric"
                    else:
                        leaderboard = leaderboard.sort_values(by="Economy", ascending=True).head(10)
                        
                        final_cols = ["BowlerName", "Balls_Bowled", "Wickets", "Economy"]
                        col_titles = ["Bowler", "Balls", "Wickets", "Economy"]
                        pct_col_name = None

                    leaderboard = leaderboard[final_cols]
                    leaderboard.columns = col_titles

                    st.subheader(f"Top 10 Spinners Performance vs {filter_label}")

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
                    st.info(f"No spinners met the threshold rules of bowling at least {min_balls} balls in this scenario.")
            else:
                st.info("No delivery records found matching this filter combo in your data.")
        else:
            st.error("⚠️ Column tracking identifier 'BowlerName' missing in uploaded sheet format structure.")
