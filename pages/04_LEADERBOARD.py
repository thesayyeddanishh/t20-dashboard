import streamlit as st
import pandas as pd
import numpy as np

# --- ADVANCED DASHBOARD THEME CSS ---
st.markdown(
    """
    <style>
        /* Global Header Typography - Safe Layout to prevent clipping */
        h1 {
            font-weight: 800 !important;
            color: #1E293B !important;
            letter-spacing: -0.5px;
            margin-top: 0px !important;
            padding-top: 0px !important;
            margin-bottom: 5px !important;
        }
        h2, h3 {
            font-weight: 700 !important;
            color: #334155 !important;
            margin-top: 0px !important;
            padding-top: 0px !important;
        }
        
        /* Table Styling Overrides */
        th[data-testid="stTableHeadCell"] {
            text-align: center !important;
            background-color: #F8FAFC !important;
            color: #475569 !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            font-size: 0.85rem !important;
            border-bottom: 2px solid #E2E8F0 !important;
        }
        th {
            text-align: center !important;
        }
        div[data-testid="stTableHeadCellContent"] {
            justify-content: center !important;
            text-align: center !important;
        }

        /* Compact Layout Overrides for the Control Panel Column */
        div[data-testid="column"]:nth-of-type(2) label p {
            font-size: 0.825rem !important;
            font-weight: 600 !important;
            margin-bottom: -2px !important; /* Pulls widgets closer to labels */
        }
        
        div[data-testid="column"]:nth-of-type(2) div[data-baseweb="select"] > div {
            min-height: 32px !important; /* Keeps dropdown inputs compact */
            height: 32px !important;
            padding-top: 0px !important;
            padding-bottom: 0px !important;
        }

        div[data-testid="column"]:nth-of-type(2) div[data-testid="stNumberInput"] div[data-baseweb="input"] {
            min-height: 32px !important;
            height: 32px !important;
        }

        /* Tighten default vertical element spacing gaps in the controls layout */
        div[data-testid="column"]:nth-of-type(2) div[data-testid="stVerticalBlock"] > div {
            gap: 0.4rem !important; 
        }
        
        /* Subtitle formatting for active filters */
        .filter-caption {
            color: #64748B;
            font-size: 0.9rem;
            margin-top: -10px !important;
            margin-bottom: 20px !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# Header Section
st.title("LEADERBOARD")
st.write("---")

# --- 1. SESSION STATE DATA CHECK ---
if 'data_df' not in st.session_state or st.session_state['data_df'] is None:
    st.error("No Data Found! Please navigate back to the HOME page and upload your CSV tracking asset first.")
else:
    # Safely extract and copy the dataframe
    df_raw = st.session_state['data_df'].copy()
    
    # Clean and explicitly prepare data types for accurate filtering
    df_raw["ReleaseSpeed"] = pd.to_numeric(df_raw["ReleaseSpeed"], errors="coerce")
    df_raw["BounceX"] = pd.to_numeric(df_raw["BounceX"], errors="coerce")
    df_raw["Deviation"] = pd.to_numeric(df_raw["Deviation"], errors="coerce")
    df_raw["Wicket"] = df_raw["Wicket"].astype(bool)
    df_raw["Runs"] = pd.to_numeric(df_raw["Runs"], errors="coerce").fillna(0)
    
    # Ensure Over column is parsed cleanly as numbers for matching boundary rules
    if "Over" in df_raw.columns:
        df_raw["Over"] = pd.to_numeric(df_raw["Over"], errors="coerce")

    # ------------------------------------------------------------------
    # --- SPLIT SCREEN LAYOUT DESIGN ---
    # ------------------------------------------------------------------
    main_display_col, filter_panel_col = st.columns([3.1, 1], gap="large")

    # Objects to hold our conditional data slice
    df_filtered = pd.DataFrame()
    filter_label = ""

    # ==================================================================
    # STEP 2: RENDER CONTROLS IN THE RIGHT FILTER PANEL (SIDEBAR LOOK)
    # ==================================================================
    with filter_panel_col:
        st.subheader("⚙️ Control Panel")
        
        # Filter 1: Player Role Selection
        f1 = st.selectbox("Select Player Role", ["BATTERS", "PACERS", "SPINNERS"])
        
        # Shared Filter 2: Match Phase Filter (Overs) - Defaults to "All"
        f_overs = st.selectbox("Match Phase (Overs)", ["All", "Powerplay (1-6)", "Middle (7-16)", "Death (17-20)"])

        # Apply global Match Phase Filtering to df_raw
        if "Over" in df_raw.columns:
            if f_overs == "Powerplay (1-6)":
                df_raw = df_raw[df_raw["Over"] < 6]
            elif f_overs == "Middle (7-16)":
                df_raw = df_raw[(df_raw["Over"] >= 6) & (df_raw["Over"] < 16)]
            elif f_overs == "Death (17-20)":
                df_raw = df_raw[df_raw["Over"] >= 16]

        # Conditional Filters based on Selected Role
        if f1 == "BATTERS":
            f2 = st.selectbox("SR by Length / Pace", ["LENGTH", "PACE"])
            
            if f2 == "LENGTH":
                # "All" added as the default option
                f3 = st.selectbox(
                    "Select Length", 
                    ["All", "FULL TOSS", "YORKER", "THE SLOT", "LENGTH", "SHORT", "BOUNCER"]
                )
                filter_label = f3
                
                if f3 == "All":
                    df_filtered = df_raw.copy()
                elif f3 == "FULL TOSS":
                    df_filtered = df_raw[df_raw["BounceX"] < 0.5]
                elif f3 == "YORKER":
                    df_filtered = df_raw[(df_raw["BounceX"] >= 0.5) & (df_raw["BounceX"] < 2.5)]
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

            min_balls = st.number_input("Minimum balls faced", min_value=1, value=10, step=1)

        elif f1 == "PACERS":
            df_role_base = df_raw[df_raw["DeliveryType"].str.lower() == "seam"] if "DeliveryType" in df_raw.columns else df_raw.copy()
            
            # "All" added as the top default option
            f2 = st.selectbox(
                "View Type", 
                ["All", "Economy By Length", "% by Lengths", "Economy by Pace", "% Balls by Pace"]
            )
            
            if f2 == "All":
                df_filtered = df_role_base.copy()
                filter_label = "All Lengths"
            elif f2 in ["Economy By Length", "% by Lengths"]:
                f3 = st.selectbox(
                    "Select Length", 
                    ["FULL TOSS", "YORKER", "THE SLOT", "LENGTH", "SHORT", "BOUNCER"]
                )
                filter_label = f3
                
                if f3 == "FULL TOSS":
                    df_filtered = df_role_base[df_role_base["BounceX"] < 0.5]
                elif f3 == "YORKER":
                    df_filtered = df_role_base[(df_role_base["BounceX"] >= 0.5) & (df_role_base["BounceX"] < 2.5)]
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

            min_balls = st.number_input("Minimum balls bowled", min_value=1, value=10, step=1)

        elif f1 == "SPINNERS":
            df_role_base = df_raw[df_raw["DeliveryType"].str.lower() == "spin"] if "DeliveryType" in df_raw.columns else df_raw.copy()
            
            # "All" added as the top default option
            f2 = st.selectbox(
                "View Type", 
                ["All", "Economy By Length", "% by Lengths", "% /Turn (TURN)"]
            )
            
            if f2 == "All":
                df_filtered = df_role_base.copy()
                filter_label = "All Lengths"
            elif f2 in ["Economy By Length", "% by Lengths"]:
                f3 = st.selectbox(
                    "Select Length", 
                    ["OVERPITCHED", "FULL", "GOOD", "SHORT"]
                )
                filter_label = f3
                
                if f3 == "OVERPITCHED":
                    df_filtered = df_role_base[df_role_base["BounceX"] <= 2.8]
                elif f3 == "FULL":
                    df_filtered = df_role_base[(df_role_base["BounceX"] > 2.8) & (df_role_base["BounceX"] <= 4.4)]
                elif f3 == "GOOD":
                    df_filtered = df_role_base[(df_role_base["BounceX"] > 4.4) & (df_role_base["BounceX"] <= 6.2)]
                elif f3 == "SHORT":
                    df_filtered = df_role_base[df_role_base["BounceX"] > 6.2]
                    
            elif f2 == "% /Turn (TURN)":
                f3 = st.selectbox("Select Ball Turn Direction", ["Turn Left", "No Turn", "Turn Right"])
                filter_label = f3
                
                if f3 == "Turn Left":
                    df_filtered = df_role_base[df_role_base["Deviation"] < -0.1]
                elif f3 == "No Turn":
                    df_filtered = df_role_base[(df_role_base["Deviation"] >= -0.1) & (df_role_base["Deviation"] <= 0.1)]
                elif f3 == "Turn Right":
                    df_filtered = df_role_base[df_role_base["Deviation"] > 0.1]

            min_balls = st.number_input("Minimum balls bowled", min_value=1, value=10, step=1)

    # ==================================================================
    # STEP 3: EXECUTE CALCULATIONS & RENDER LEADERBOARDS ON LEFT SIDE
    # ==================================================================
    with main_display_col:
        
        # --- RENDER ENGINE: BATTERS ---
        if f1 == "BATTERS":
            if not df_filtered.empty:
                batter_col = "Batter" if "Batter" in df_filtered.columns else "BatsmanName"
                
                leaderboard = df_filtered.groupby(batter_col).agg(
                    Runs=("Runs", "sum"),
                    Balls_Faced=("Runs", "count"),
                    Dismissals=("Wicket", lambda x: sorted(x).count(True))
                ).reset_index()
                
                leaderboard[leaderboard["Balls_Faced"] >= min_balls]

                if not leaderboard.empty:
                    leaderboard["Strike Rate"] = (leaderboard["Runs"] / leaderboard["Balls_Faced"]) * 100
                    leaderboard = leaderboard.sort_values(by="Strike Rate", ascending=False).head(10)
                    
                    leaderboard["Strike Rate"] = leaderboard["Strike Rate"].round(1)
                    leaderboard["Runs"] = leaderboard["Runs"].astype(int)
                    
                    leaderboard.columns = ["Batter", "Runs", "Balls faced", "Dismissals", "Strike Rate"]
                    
                    st.subheader(f"Top 10 Batters by Strike Rate vs {filter_label}")
                    st.markdown(f'<div class="filter-caption">Applied Filters: Phase: <b>{f_overs}</b> | Minimum Requirement: <b>{min_balls} Balls Faced</b></div>', unsafe_allow_html=True)
                    
                    column_configuration = {
                        "Batter": st.column_config.TextColumn(width=200),
                        "Runs": st.column_config.NumberColumn(alignment="center", width=75),
                        "Balls faced": st.column_config.NumberColumn(alignment="center", width=75),
                        "Dismissals": st.column_config.NumberColumn(alignment="center", width=75),
                        "Strike Rate": st.column_config.NumberColumn(alignment="center", width=100),
                    }
                    
                    st.dataframe(
                        leaderboard.set_index("Batter"), 
                        use_container_width=True, 
                        column_config=column_configuration
                    )
                else:
                    st.info(f"No batters found matching the minimum requirement threshold of {min_balls} balls faced.")
            else:
                st.info("No delivery metrics recorded in the raw data matching this custom query scenario.")

        # --- RENDER ENGINE: PACERS ---
        elif f1 == "PACERS":
            if "BowlerName" in df_raw.columns:
                df_bowler_totals = df_role_base.groupby("BowlerName").agg(Total_Balls=("Runs", "count")).reset_index()

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

                        # Sorting Logic: Default View "All" sorts by Wickets descending
                        if f2 == "All":
                            leaderboard = leaderboard.sort_values(by="Wickets", ascending=False).head(10)
                            final_cols = ["BowlerName", "Balls_Bowled", "Wickets", "Economy"]
                            col_titles = ["Bowler", "Balls", "Wickets", "Economy"]
                            pct_col_name = None
                        elif f2 == "% by Lengths":
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

                        title_suffix = "by Wickets" if f2 == "All" else f"vs {filter_label} ({f2})"
                        st.subheader(f"Top 10 Pacers' Performance {title_suffix}")
                        st.markdown(f'<div class="filter-caption">Applied Filters: Phase: <b>{f_overs}</b> | Minimum Requirement: <b>{min_balls} Balls Bowled</b></div>', unsafe_allow_html=True)

                        column_configuration = {
                            "Bowler": st.column_config.TextColumn(width=200),
                            "Balls": st.column_config.NumberColumn(alignment="center", width=75),
                            "Wickets": st.column_config.NumberColumn(alignment="center", width=75),
                            "Economy": st.column_config.NumberColumn(alignment="center", width=85),
                        }
                        if pct_col_name:
                            column_configuration[pct_col_name] = st.column_config.NumberColumn(alignment="center", width=100, format="%.1f%%")

                        st.dataframe(leaderboard.set_index("Bowler"), use_container_width=True, column_config=column_configuration)
                    else:
                        st.info(f"No pacers found matching the minimum requirement threshold of {min_balls} balls bowled.")
                else:
                    st.info("No delivery metrics recorded in the raw data matching this custom query scenario.")
            else:
                st.error("Column tracking identifier 'BowlerName' missing in uploaded sheet format structure.")

        # --- RENDER ENGINE: SPINNERS ---
        elif f1 == "SPINNERS":
            if "BowlerName" in df_raw.columns:
                df_bowler_totals = df_role_base.groupby("BowlerName").agg(Total_Balls=("Runs", "count")).reset_index()

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

                        # Sorting Logic: Default View "All" sorts by Wickets descending
                        if f2 == "All":
                            leaderboard = leaderboard.sort_values(by="Wickets", ascending=False).head(10)
                            final_cols = ["BowlerName", "Balls_Bowled", "Wickets", "Economy"]
                            col_titles = ["Bowler", "Balls", "Wickets", "Economy"]
                            pct_col_name = None
                        elif f2 in ["% by Lengths", "% /Turn (TURN)"]:
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

                        title_suffix = "by Wickets" if f2 == "All" else f"vs {filter_label} ({f2})"
                        st.subheader(f"Top 10 Spinners Performance {title_suffix}")
                        st.markdown(f'<div class="filter-caption">Applied Filters: Phase: <b>{f_overs}</b> | Minimum Requirement: <b>{min_balls} Balls Bowled</b></div>', unsafe_allow_html=True)

                        column_configuration = {
                            "Bowler": st.column_config.TextColumn(width=200),
                            "Balls": st.column_config.NumberColumn(alignment="center", width=75),
                            "Wickets": st.column_config.NumberColumn(alignment="center", width=75),
                            "Economy": st.column_config.NumberColumn(alignment="center", width=85),
                        }
                        if pct_col_name:
                            column_configuration[pct_col_name] = st.column_config.NumberColumn(alignment="center", width=100, format="%.1f%%")

                        st.dataframe(leaderboard.set_index("Bowler"), use_container_width=True, column_config=column_configuration)
                    else:
                        st.info(f"No spinners found matching the minimum requirement threshold of {min_balls} balls bowled.")
                else:
                    st.info("No delivery metrics recorded in the raw data matching this custom query scenario.")
            else:
                st.error("Column tracking identifier 'BowlerName' missing in uploaded sheet format structure.")
