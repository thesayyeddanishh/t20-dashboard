import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go 
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.cm as cm
import matplotlib.colors as mcolors
from io import StringIO
import base64
import matplotlib.patheffects as pe
from matplotlib import cm, colors, patches
import matplotlib.colors as mcolors
from matplotlib.gridspec import GridSpec
from math import floor, ceil

# =========================================================
# --- CHART 2: PITCH MAP (BOUNCE LOCATION) ---
# =========================================================
# --- HELPERS ---
def get_spinner_pitch_bins():
    """Defines the length categories for spin bowling."""
    return {
         "OP": [-2, 2.8],
        "Full": [2.8, 4.4],
        "Good": [4.4, 6.2],
        "Short": [6.2, 15.0]
    }


def create_Spinner_pitch_map(df_in): 
    PITCH_BINS = {
         "OP": [-2, 2.8],
        "Full": [2.8, 4.4],
        "Good": [4.4, 6.2],
        "Short": [6.2, 15.0]
    }

    if df_in.empty:
        # Create an empty figure with a text note if data is missing
        fig, ax = plt.subplots(figsize=(4,6))
        ax.text(0.5, 0.5, f"No data for Spinner Pitch Map", ha='center', va='center', fontsize=12)
        ax.axis('off')
        return fig

    # --- Data Filtering ---
    pitch_wickets = df_in[df_in["Wicket"] == True]
    pitch_non_wickets = df_in[df_in["Wicket"] == False]
    
    # --- Chart Setup ---
    fig, ax = plt.subplots(figsize=(4.5,9))
    ax.set_facecolor('white')
    fig.patch.set_facecolor('white')

    # --- 1. Add Zone Lines & Labels (Horizontal Lines) ---
    
    # Determine boundary Y values to draw lines (excluding the start of the lowest bin)
    boundary_y_values = sorted([v[0] for v in PITCH_BINS.values() if v[0] > -4.0], reverse=True)

    for y_val in boundary_y_values:
        ax.axhline(y=y_val, color="lightgrey", linewidth=1.0, linestyle="--")

    # Add zone labels (Annotation)
    for length, bounds in PITCH_BINS.items():
        if length != "Full Toss": 
            mid_y = (bounds[0] + bounds[1]) / 2.2
            # Use ax.text for annotation, positioned on the far left (x=-1.45)
            ax.text(
                x=-1.45, 
                y=mid_y, 
                s=length.upper(), 
                ha='left', 
                va='center', 
                fontsize=8, 
                color="grey", 
                fontweight='bold'
            )

    
    # --- 3. Plot Data (Scatter Traces) ---
    
    # Non-Wickets (light grey)
    ax.scatter(
        pitch_non_wickets["BounceY"], pitch_non_wickets["BounceX"], 
        s=100, 
        c='#D3D3D3', 
        edgecolor='white', 
        linewidths=1.0, 
        alpha=0.9,
        label="No Wicket"
    )

    # Wickets (red)
    ax.scatter(
        pitch_wickets["BounceY"], pitch_wickets["BounceX"], 
        s=150, 
        c='red', 
        edgecolor='white', 
        linewidths=1.0, 
        alpha=0.95,
        label="Wicket"
    )
    
    # --- 2. Add Stump lines (Vertical Lines) ---
    ax.axvline(x=-0.18, color="#777777", linestyle="-", linewidth=0.5)
    ax.axvline(x=0.18, color="#777777", linestyle="-", linewidth=0.5)
    ax.axvline(x=0, color="#777777", linestyle="-", linewidth=0.5)
    
    # --- 4. Layout (Axis and Spines) ---
    
    # Set axis limits
    ax.set_xlim([-1.5, 1.5])
    # Reverse the axis to match the cricket visual (batter at bottom)
    ax.set_ylim([10.0, 0]) 

    # Hide all axis elements
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.grid(False)
    
    # Hide axis spines (plot border)
    spine_color = 'black'
    spine_width = 0.5
    for spine_name in ['left', 'top', 'bottom','right']:
        ax.spines[spine_name].set_visible(True)
        ax.spines[spine_name].set_color(spine_color)
        ax.spines[spine_name].set_linewidth(spine_width)
        
    plt.tight_layout()
    
    return fig

def create_Spinner_pitch_length_bars(df_in):
    # Fixed size to accommodate three stacked charts comfortably
    FIG_SIZE = (6, 12) 
    
    if df_in.empty:
        fig, ax = plt.subplots(figsize=FIG_SIZE)
        ax.text(0.5, 0.5, "No Data for Spinner Pitch Length Comparison", ha='center', va='center', fontsize=12)
        ax.axis('off')
        return fig

    PITCH_BINS_DICT = get_spinner_pitch_bins()
    ordered_keys = ["OP", "Full", "Good" , "Short"]
    
    # 1. Data Preparation
    def assign_pitch_length(x):
        for length, bounds in PITCH_BINS_DICT.items():
            if bounds[0] <= x < bounds[1]: return length
        return None

    df_pitch = df_in.copy()
    df_pitch["PitchLength"] = df_pitch["BounceX"].apply(assign_pitch_length)
    
    # Aggregate data (Includes Wickets, Runs, and Balls for new metrics)
    df_summary = df_pitch.groupby("PitchLength").agg(
        Runs=("Runs", "sum"), 
        Wickets=("Wicket", lambda x: (x == True).sum()), 
        Balls=("Wicket", "count")
    ).reset_index().set_index("PitchLength").reindex(ordered_keys).fillna(0)
    
    # --- UPDATED CALCULATIONS ---
    df_summary["Economy"] = df_summary.apply(lambda row: (row["Runs"] / row["Balls"] * 6) if row["Balls"] > 0 else 0.0, axis=1)
    
    # Bowling Strike Rate (Balls per Wicket)
    df_summary["SR"] = df_summary.apply(
        lambda row: row["Balls"] / row["Wickets"] if row["Wickets"] > 0 else row["Balls"], axis=1
    )
    
    # Bowling Average (Runs per Wicket)
    df_summary["Avg"] = df_summary.apply(
        lambda row: row["Runs"] / row["Wickets"] if row["Wickets"] > 0 else row["Runs"], axis=1
    )
    
    # Categories for plotting (reversed for barh)
    categories = df_summary.index.tolist()[::-1]
    
    # 2. Chart Setup (3 Rows, 1 Column)
    fig, axes = plt.subplots(3, 1, figsize=FIG_SIZE, sharey=True) 
    plt.subplots_adjust(hspace=0.5) # Adjusted to 0.5 for reasonable spacing

    # --- UPDATED ORDER: Economy, SR, Avg ---
    metrics = ["Economy", "SR", "Avg"]
    
    # Dynamic limits for scaling
    max_eco = df_summary["Economy"].max() * 1.2 if df_summary["Economy"].max() > 0 else 12
    max_sr = df_summary["SR"].max() * 1.2 if df_summary["SR"].max() > 0 else 40
    max_avg = df_summary["Avg"].max() * 1.2 if df_summary["Avg"].max() > 0 else 50
    
    xlim_limits = {
        "Economy": (0, max_eco),
        "SR": (0, max_sr),
        "Avg": (0, max_avg)
    }

    # --- Plotting Loop ---
    for i, ax in enumerate(axes):
        metric = metrics[i]
        
        # Reverse the summary to match reversed categories
        df_rev = df_summary.iloc[::-1]
        values = df_rev[metric].values 
        ax.set_xlim(xlim_limits[metric])
        
        # Horizontal Bar Chart
        ax.barh(categories, values, height=0.49, color='#ff5000', zorder=3, alpha=0.9)
        
        # --- DYNAMIC TITLES ---
        if metric == "SR":
            title = "Balls" if df_summary["Wickets"].sum() == 0 else "Bowling Strike Rate (SR)"
        elif metric == "Avg":
            title = "Runs" if df_summary["Wickets"].sum() == 0 else "Bowling Average (Avg)"
        else:
            title = "Economy"
            
        ax.set_title(title, fontsize=12, fontweight='bold', pad=0, loc='left')
        
        # --- DYNAMIC ANNOTATIONS (The R and B Trick) ---
        for j, (idx, row) in enumerate(df_rev.iterrows()):
            val = row[metric]
            wickets = row["Wickets"]
            
            if metric == "Economy":
                label = f"{val:.1f}"
            elif metric == "SR":
                # If no wickets, show total Balls + B
                label = f"{int(row['Balls'])} B" if wickets == 0 else f"{val:.1f}"
            elif metric == "Avg":
                # If no wickets, show total Runs + R
                label = f"{int(row['Runs'])} R" if wickets == 0 else f"{val:.1f}"
            
            ax.text(val, j, label, 
                    ha='left', va='center', 
                    fontsize=15, fontweight='bold', color='black',
                    bbox=dict(facecolor='White', alpha=0.8, edgecolor='none', pad=2),
                    zorder=4)

        # --- Formatting ---
        ax.set_facecolor('white')
        ax.tick_params(axis='x', labelsize=8)
        ax.tick_params(axis='y', length=0) 

        if i == 2:
            ax.set_yticks(np.arange(len(categories)), labels=[c.upper() for c in categories], fontsize=9)
        else:
            ax.set_yticks(np.arange(len(categories)), labels=[''] * len(categories))
            
        ax.xaxis.grid(False) 
        ax.yaxis.grid(False)
        ax.set_xticks([]) 
        
        spine_color = 'lightgray'
        for spine_name in ['left', 'right', 'top', 'bottom']:
            ax.spines[spine_name].set_visible(True)
            ax.spines[spine_name].set_color(spine_color)
            ax.spines[spine_name].set_linewidth(1.0)
            
    plt.tight_layout(pad=0.5)
    return fig
# =========================================================
# Chart 1: CREASE BEEHIVE 
# ========================================================
def create_Spinner_crease_beehive(df_in, handedness_label): # Renamed function and parameter
    if df_in.empty:
        fig, ax = plt.subplots(figsize=(7, 5)); 
        ax.text(0.5, 0.5, f"No data for Analysis ({handedness_label})", ha='center', va='center', fontsize=12); 
        ax.axis('off'); 
        return fig

    # --- Data Filtering ---
    wickets = df_in[df_in["Wicket"] == True]
    non_wickets_all = df_in[df_in["Wicket"] == False]
    boundaries = non_wickets_all[(non_wickets_all["Runs"] == 4) | (non_wickets_all["Runs"] == 6)]
    regular_balls = non_wickets_all[(non_wickets_all["Runs"] != 4) & (non_wickets_all["Runs"] != 6)]
    
    # --- Lateral Zone Data Prep (Chart 2b) ---
    df_lateral = df_in.copy()
    
    # DETERMINE HANDEDNESS FOR ZONE REVERSAL
    # If the function is called with a single handedness filter (RHB or LHB), this will be consistent.
    is_rhb = handedness_label == "RHB" 

    def assign_lateral_zone(row):
        y = row["CreaseY"]
        if row["IsBatsmanRightHanded"] == True:
            # RHB: Off side is negative Y, Leg side is positive Y
            if y > 0.18: return "LEG"
            elif y >= -0.18: return "STUMPS"
            elif y > -0.65: return "OUTSIDE OFF"
            else: return "WAY OUTSIDE OFF"
        else: # Left-Handed
            # LHB: Leg side is negative Y, Off side is positive Y
            if y > 0.65: return "WAY OUTSIDE OFF"
            elif y > 0.18: return "OUTSIDE OFF"
            elif y >= -0.18: return "STUMPS"
            else: return "LEG"
            
    df_lateral["LateralZone"] = df_lateral.apply(assign_lateral_zone, axis=1)
    
    summary = (
        df_lateral.groupby("LateralZone").agg(
            Runs=("Runs", "sum"), Wickets=("Wicket", lambda x: (x == True).sum()), Balls=("Wicket", "count")
        )
    )
    
    # 1. Define standard zone order (WOO to LEG)
    ordered_zones_base = ["WAY OUTSIDE OFF", "OUTSIDE OFF", "STUMPS", "LEG"]
    
    # 2. HANDEDNESS AWARE REVERSAL: Reverse order for LHB for visual consistency
    ordered_zones = ordered_zones_base if is_rhb else ordered_zones_base[::-1]
    
    summary = summary.reindex(ordered_zones).fillna(0)
    
    # BOWLING Metrics
    # summary["Avg Runs/Wicket"] = summary.apply(lambda row: row["Runs"] / row["Wickets"] if row["Wickets"] > 0 else np.nan, axis=1)
    summary["Economy"] = summary.apply(lambda row: (row["Runs"] / row["Balls"]) * 6 if row["Balls"] > 0 else np.nan, axis=1)

    # -----------------------------------------------------------
    # --- 1. SETUP SUBPLOTS ---
    fig = plt.figure(figsize=(7, 5)) 
    gs = fig.add_gridspec(2, 1, height_ratios=[4, 1], hspace=0.005) 
    ax_bh = fig.add_subplot(gs[0, 0])      
    ax_boxes = fig.add_subplot(gs[1, 0])   
    fig.patch.set_facecolor('white')

    
    # --- Traces ---
    ax_bh.scatter(regular_balls["CreaseY"], regular_balls["CreaseZ"], s=40, c='lightgrey', edgecolor='white', linewidths=1.0, alpha=0.95, label="Regular Ball")
    ax_bh.scatter(boundaries["CreaseY"], boundaries["CreaseZ"], s=80, c='royalblue', edgecolor='white', linewidths=1.0, alpha=0.95, label="Boundary")
    ax_bh.scatter(wickets["CreaseY"], wickets["CreaseZ"], s=80, c='red', edgecolor='white', linewidths=1.0, alpha=0.95, label="Wicket")

    # --- Reference Lines ---
    ax_bh.axvline(x=-0.18, color="grey", linestyle="--", linewidth=0.5) 
    ax_bh.axvline(x=0.18, color="grey", linestyle="--", linewidth=0.5)
    ax_bh.axvline(x=0, color="grey", linestyle="--", linewidth=0.5) 
    ax_bh.axvline(x=-0.92, color="red", linestyle="-", linewidth=0.25) 
    ax_bh.axvline(x=0.92, color="red", linestyle="-", linewidth=0.25)
    ax_bh.axhline(y=0.78, color="grey", linestyle="-", linewidth=0.5)

    # --- Annotation ---
    ax_bh.text(-1.5, 0.78, "Stump line", ha='left', va='bottom', fontsize=8, color="grey", transform=ax_bh.transData)
    
    # --- Formatting ---
    ax_bh.set_xlim([-1.8, 1.8])
    ax_bh.set_ylim([0, 1.5])
    ax_bh.set_aspect('equal', adjustable='box')
    ax_bh.set_xticks([]); ax_bh.set_yticks([]); ax_bh.grid(False)
    for spine in ax_bh.spines.values():
        spine.set_visible(False)
    ax_bh.set_facecolor('white')
    
    # -----------------------------------------------------------
    ## --- 3. CHART 1b: LATERAL PERFORMANCE BOXES (ax_boxes) ----
    num_regions = len(ordered_zones)
    box_width = 1 / num_regions
    box_height = 0.4 
    left = 0
    
    # Color Normalization
    eco_values = summary["Economy"].dropna()
    eco_max = eco_values.max() if eco_values.max() > 0 else 18 # Use a suitable default max
    norm = mcolors.Normalize(vmin=0, vmax=eco_max) 
    cmap = cm.get_cmap('Wistia')

    for index, row in summary.iterrows():
        eco = row["Economy"]
        wkts = int(row["Wickets"]) # Ensure wkts is defined here from the row
        balls = int(row["Balls"])
        
        # Color based on Economy (handling NaN)
        color = cmap(norm(eco)) if not np.isnan(eco) else (1, 1, 1, 1) # White if no balls bowled
        
        # Draw the Rectangle
        ax_boxes.add_patch(
            patches.Rectangle((left, 0), box_width, box_height, 
                              edgecolor="white", facecolor=color, linewidth=0.5)
        )
        
        # Label 1: Zone Name
        ax_boxes.text(left + box_width / 2, box_height + 0.1, 
                      index, ha='center', va='bottom', fontsize=7, color='black')
        
        # Contrast logic for text
        text_color = 'black'
        if balls > 0:
            r, g, b, a = color
            luminosity = 0.2126 * r + 0.7152 * g + 0.0722 * b
            text_color = 'white' if luminosity < 0.5 else 'black'
        
        # Label 2: Wickets and Economy (Replaces Average)
        label_wkts_eco = f"{wkts}W - Eco {eco:.1f}" if not np.isnan(eco) else "No Data"
        ax_boxes.text(left + box_width / 2, box_height * 0.5, 
                      label_wkts_eco,
                      ha='center', va='center', fontsize=9, fontweight='bold', color=text_color)
        
        left += box_width

    # Formatting
    ax_boxes.set_xlim(0, 1)
    ax_boxes.set_ylim(0, box_height + 0.3) 
    ax_boxes.axis('off')
    for spine in ax_boxes.spines.values():
        spine.set_visible(False)
    ax_boxes.set_facecolor('white')

    # -----------------------------------------------------------
    ## --- 4. DRAW SINGLE COMPACT BORDER AROUND THE ENTIRE FIGURE ---
    
    plt.tight_layout(pad=0.2)
    
    PADDING = 0.008

    bh_bbox = ax_bh.get_position()
    box_bbox = ax_boxes.get_position()
    
    x0_orig = min(bh_bbox.x0, box_bbox.x0)
    y0_orig = box_bbox.y0
    x1_orig = max(bh_bbox.x1, box_bbox.x1)
    y1_orig = bh_bbox.y1
    
    x0_pad = x0_orig - PADDING
    y0_pad = y0_orig - PADDING
    
    width_pad = (x1_orig - x0_orig) + (2 * PADDING)
    height_pad = (y1_orig - y0_orig) + (2 * PADDING)

    border_rect = patches.Rectangle(
        (x0_pad, y0_pad), 
        width_pad, 
        height_pad, 
        facecolor='none', 
        edgecolor='black', 
        linewidth=0.5, 
        transform=fig.transFigure, 
        clip_on=False
    )

    fig.patches.append(border_rect)

    return fig

# =========================================================
# Chart 4 Bowler Release Map
# =========================================================

def create_Spinner_release_analysis(df_in, handedness_label): 
    FIG_SIZE = (3, 3) # Increased height for both charts

    if df_in.empty or "ReleaseY" not in df_in.columns or "ReleaseZ" not in df_in.columns:
        fig, ax = plt.subplots(figsize=FIG_SIZE)
        ax.text(0.5, 0.5, f"No data for Release Analysis vs. {handedness_label}", ha='center', va='center', fontsize=12)
        ax.axis('off')
        return fig

    # --- 1. Calculate Lateral Release Performance (LEFT vs RIGHT) ---
    df_temp = df_in.copy()
    
    # Categorize based on ReleaseY sign
    df_temp["ReleaseCategory"] = np.where(
        df_temp["ReleaseY"] < 0, "LEFT (<0)", 
        np.where(df_temp["ReleaseY"] > 0, "RIGHT (>0)", "CENTER (=0)")
    )
    
    df_temp = df_temp[df_temp["ReleaseCategory"] != "CENTER (=0)"]
    
    # Calculation functions
    def calculate_ba(row):
        # Use np.nan as a flag for "N/A"
        return row["Runs"] / row["Wickets"] if row["Wickets"] > 0 else np.nan

    def calculate_sr(row):
        # Strike Rate = Balls per Wicket (normalized by 6 for Cricket SR)
        return (row["Balls"] / row["Wickets"]) if row["Wickets"] > 0 else np.nan
        
    summary = df_temp.groupby("ReleaseCategory").agg(
        Wickets=("Wicket", lambda x: (x == True).sum()),
        Runs=("Runs", "sum"),
        Balls=("Wicket", "count")
    )

    # Ensure both categories are present for consistent plotting
    summary = summary.reindex(["LEFT (<0)", "RIGHT (>0)"]).fillna(0)
    
    summary["BA"] = summary.apply(calculate_ba, axis=1)
    summary["SR"] = summary.apply(calculate_sr, axis=1)

    # Formatting helper
    def format_metric(value, is_wickets=False):
        if is_wickets:
            return f"{int(value)}"
        if np.isnan(value) or value == np.inf:
            return "N/A"
        return f"{value:.1f}"

    left = summary.loc["LEFT (<0)"]
    right = summary.loc["RIGHT (>0)"]

    # --- 2. Setup Figure and GridSpec ---
    fig = plt.figure(figsize=FIG_SIZE, facecolor='white')
    gs = GridSpec(2, 1, figure=fig, height_ratios=[4, 1], hspace=0.1)
    
    ax_map = fig.add_subplot(gs[0, 0])
    ax_metrics = fig.add_subplot(gs[1, 0])

    # --- 3. Plot Release Zone Map (ax_map) ---
    
    release_wickets = df_in[df_in["Wicket"] == True]
    release_non_wickets = df_in[df_in["Wicket"] == False]
    
    # Non-Wickets (light grey)
    ax_map.scatter(
        release_non_wickets["ReleaseY"], release_non_wickets["ReleaseZ"], 
        s=15, color='#D3D3D3', alpha=1.0, linewidths=0, label="No Wicket"
    )

    # Wickets (red)
    ax_map.scatter(
        release_wickets["ReleaseY"], release_wickets["ReleaseZ"], 
        s=15, color='red', alpha=1.0, linewidths=0, label="Wicket", zorder=5
    )
    
    # Add Stump Lines
    stump_lines = [-0.18, 0, 0.18]
    for y_val in stump_lines:
        ax_map.axvline(x=y_val, color="#777777", linestyle="-", linewidth=0.5)
    
    # Formatting Map
    ax_map.set_xlim(-1.5, 1.5)
    ax_map.set_ylim(0.5, 2.5)
    ax_map.set_xticks([])
    ax_map.set_yticks([])
    ax_map.set_facecolor('white')
    ax_map.grid(True)

    
    # Hide all map spines
    for spine in ax_map.spines.values():
        spine.set_visible(False)
        
    # --- 4. Draw Lateral Metrics Table (ax_metrics) ---
    
    # Hide all metrics spines/ticks/labels
    ax_metrics.axis('off')
    ax_metrics.set_xlim(0, 1)
    ax_metrics.set_ylim(-0.5, 1)

    # Titles
    # Metric Labels (Left Alignment for labels)
    ax_metrics.text(0.05, 1, "W:", ha='right', va='center', fontsize=5, fontweight='bold')
    ax_metrics.text(0.05, 0.5, "Avg:", ha='right', va='center', fontsize=5, fontweight='bold')
    ax_metrics.text(0.05, 0, "SR:", ha='right', va='center', fontsize=5, fontweight='bold')

    # LEFT Values
    ax_metrics.text(0.2, 1, format_metric(left["Wickets"], is_wickets=True), ha='center', va='center', fontsize=8, color='red', fontweight='bold')
    ax_metrics.text(0.2, 0.5, format_metric(left["BA"]), ha='center', va='center', fontsize=8, color='black', fontweight='bold')
    ax_metrics.text(0.2, 0, format_metric(left["SR"]), ha='center', va='center', fontsize=8, color='black', fontweight='bold')

    # RIGHT Values
    ax_metrics.text(0.9, 1, format_metric(right["Wickets"], is_wickets=True), ha='center', va='center', fontsize=8, color='red', fontweight='bold')
    ax_metrics.text(0.9, 0.5, format_metric(right["BA"]), ha='center', va='center', fontsize=8, color='black', fontweight='bold')
    ax_metrics.text(0.9, 0, format_metric(right["SR"]), ha='center', va='center', fontsize=8, color='black', fontweight='bold')
    
    # --- 5. Add Sharp Border to Figure ---
    plt.tight_layout(pad=0.1)
    
    # Create and add a custom Rectangle patch for sharp border
    ax_bbox = ax_map.get_position()
    # Calculate padding relative to figure size
    padding_x = 0.001 * FIG_SIZE[0] / fig.get_size_inches()[0] 
    padding_y = 0.001 * FIG_SIZE[1] / fig.get_size_inches()[1] 
    
    border_rect = patches.Rectangle(
        (0.05, 0.13), 
        0.9, 
        0.8, 
        facecolor='none',
        edgecolor='black',
        linewidth=0.5,
        transform=fig.transFigure,
        clip_on=False,
        joinstyle='miter' # Ensures sharp corners
    )
    fig.add_artist(border_rect)

    return fig

# =========================================================
# Chart 7 Spinners Hitting Missing
# =========================================================

def create_spinner_hitting_missing(df_in, handedness_label):

    FIG_SIZE = (10, 10)

    # Early exit if empty
    if df_in.empty:
        fig, ax = plt.subplots(figsize=FIG_SIZE)
        ax.text(0.5, 0.5, f"No data for Hitting/Missing Analysis ({handedness_label})",
                ha='center', va='center', fontsize=12)
        ax.axis('off')
        return fig

    df_map = df_in.copy()

    # 1. Define HITTING / MISSING
    is_hitting_target = (
        (df_map["StumpsY"] >= -0.18) &
        (df_map["StumpsY"] <= 0.18) &
        (df_map["StumpsZ"] >= 0) &
        (df_map["StumpsZ"] <= 0.72)
    )
    df_map["HittingCategory"] = np.where(is_hitting_target, "HITTING", "MISSING")

    # 2. Percentages
    counts = df_map["HittingCategory"].value_counts(normalize=True).mul(100).round(1)
    hitting_pct = counts.get("HITTING", 0.0)
    missing_pct = counts.get("MISSING", 0.0)

    # 3. Figure + Grid
    fig = plt.figure(figsize=FIG_SIZE, facecolor='white')
    gs = GridSpec(2, 3, figure=fig, height_ratios=[4, 1], wspace=0.3, hspace=0.25)

    ax_map = fig.add_subplot(gs[0, :])
    ax_wickets = fig.add_subplot(gs[1, 0])
    ax_ba = fig.add_subplot(gs[1, 1])
    ax_sr = fig.add_subplot(gs[1, 2])

    # 4. MAP
    df_missing_no_wicket = df_map[(df_map["HittingCategory"] == "MISSING") & (df_map["Wicket"] == False)]
    df_hitting_no_wicket = df_map[(df_map["HittingCategory"] == "HITTING") & (df_map["Wicket"] == False)]
    df_wicket = df_map[df_map["Wicket"] == True]

    # Box lines
    ax_map.axvline(x=-0.18, color='grey', linestyle='--', linewidth=1)
    ax_map.axvline(x=0, color='grey', linestyle=':', linewidth=1)
    ax_map.axvline(x=0.18, color='grey', linestyle='--', linewidth=1)
    ax_map.axhline(y=0.78, color='grey', linestyle='--', linewidth=1)
    ax_map.axhline(y=0, color='grey', linestyle='-', linewidth=1)

    # Points
    ax_map.scatter(df_missing_no_wicket["StumpsY"], df_missing_no_wicket["StumpsZ"],
                   color='#D3D3D3', s=75, edgecolor='white', linewidth=0.4, alpha=0.8)
    ax_map.scatter(df_hitting_no_wicket["StumpsY"], df_hitting_no_wicket["StumpsZ"],
                   color='#3b3b3b', s=85, edgecolor='white', linewidth=0.4, alpha=0.9)
    ax_map.scatter(df_wicket["StumpsY"], df_wicket["StumpsZ"],
                   color='red', s=100, edgecolor='white', linewidth=0.6, zorder=25)

    ax_map.set_xlim(-1.1, 1.1)
    ax_map.set_ylim(0, 1.4)
    ax_map.axis('off')

    # Labels
    ax_map.text(0.74, 1.4, f"Hitting: {hitting_pct:.0f}%",
                transform=ax_map.transData, ha='right', va='top',
                fontsize=15, color='#3b3b3b', weight='bold')
    ax_map.text(1.2, 1.4, f"Missing: {missing_pct:.0f}%",
                transform=ax_map.transData, ha='right', va='top',
                fontsize=15, color='#D3D3D3', weight='bold')

    # 5. SUMMARY TABLE
    summary = df_map.groupby("HittingCategory").agg(
        Wickets=("Wicket", lambda x: (x == True).sum()),
        Runs=("Runs", "sum"),
        Balls=("Wicket", "count")
    )

    # Ensure both, correct order
    for cat in ["HITTING", "MISSING"]:
        if cat not in summary.index:
            summary.loc[cat] = [0, 0, 0]

    summary = summary.reindex(["HITTING", "MISSING"])

    summary["BA"] = summary.apply(lambda r: r["Runs"] / r["Wickets"] if r["Wickets"] > 0 else 0, axis=1)
    summary["SR"] = summary.apply(lambda r: r["Balls"] / r["Wickets"] if r["Wickets"] > 0 else 0, axis=1)

    metrics_data = {
        "Wickets": {"data": summary["Wickets"].tolist(), "title": "Wickets"},
        "BA": {"data": summary["BA"].tolist(), "title": "Average"},
        "SR": {"data": summary["SR"].tolist(), "title": "Strike Rate"},
    }

    max_values = {
        "Wickets": summary["Wickets"].max() * 1.2 if summary["Wickets"].max() > 0 else 5,
        "BA": summary["BA"].replace([np.inf], np.nan).max() * 1.2 if summary["BA"].max() > 0 else 100,
        "SR": summary["SR"].replace([np.inf], np.nan).max() * 1.2 if summary["SR"].max() > 0 else 100,
    }

    bar_colors = ["#3b3b3b", "#D3D3D3"]
    y_labels = ["HITTING", "MISSING"]
    axes = [ax_wickets, ax_ba, ax_sr]

    # 6. PLOTTING METRICS
    for i, (metric, meta) in enumerate(metrics_data.items()):
        ax = axes[i]
        bars = ax.barh(y_labels, meta["data"], color=bar_colors, height=0.5)
        ax.invert_yaxis()
        ax.set_title(meta["title"], fontsize=10, pad=5)
        ax.set_xlim(0, max_values[metric])
        ax.xaxis.set_visible(False)

        if i == 0:
            ax.tick_params(axis='y', length=0)
            ax.set_yticks([0, 1])
            ax.set_yticklabels(y_labels, fontsize=10, weight='bold')
        else:
            ax.yaxis.set_visible(False)

        for bar, value in zip(bars, meta["data"]):
            text = "N/A" if np.isnan(value) else f"{value:.1f}" if metric != "Wickets" else f"{int(value)}"
            ax.text(bar.get_width() + 0.5,
                    bar.get_y() + bar.get_height() / 2,
                    text, ha='left', va='center', fontsize=9, weight='bold')

        for spine in ["right", "top", "bottom", "left"]:
            ax.spines[spine].set_visible(False)

        ax.grid(False)

    # 7. BORDER (outside loop)
    plt.tight_layout(pad=0.01)
    border_rect = patches.Rectangle(
        (0.005, 0.09),
        0.99,
        0.85,
        facecolor='none',
        edgecolor='black',
        linewidth=0.5,
        transform=fig.transFigure
    )
    fig.add_artist(border_rect)

    return fig
    
    # ----------------------------------------------------------------------
    ## --- PART 3: DRAW SINGLE COMPACT BORDER ---
    # ----------------------------------------------------------------------
    
    plt.tight_layout(pad=0.1) 
    
    PADDING = 0.004

    # Get the bounding box of the top (scatter) and bottom (bar) charts
    scatter_bbox = ax_scatter.get_position()
    bar_bbox = ax_bar.get_position() 
    # Determine the total bounds (figure coordinates)
    x0_orig = scatter_bbox.x0         
    y0_orig = bar_bbox.y0  
    x1_orig = scatter_bbox.x1     
    y1_orig = scatter_bbox.y1         
    
    # Apply Padding
    x0_pad = x0_orig - PADDING
    y0_pad = y0_orig - PADDING
    
    width_pad = (x1_orig - x0_orig) + (2 * PADDING)
    height_pad = (y1_orig - y0_orig) + (2 * PADDING)

    # Draw the custom Rectangle 
    border_rect = patches.Rectangle(
        (x0_pad-0.008, y0_pad+0.02), 
        width_pad+0.017, 
        height_pad,  
        facecolor='none', 
        edgecolor='black', 
        linewidth=0.5, 
        transform=fig.transFigure, 
        clip_on=False
    )

    fig.patches.append(border_rect)

    return fig


# Chart 10 : Scoring Areas
def calculate_scoring_wagon(row):
    """Calculates the scoring area based on LandingX/Y coordinates and handedness."""
    LX = row.get("LandingX"); LY = row.get("LandingY"); RH = row.get("IsBatsmanRightHanded")
    if RH is None or LX is None or LY is None or row.get("Runs", 0) == 0: return None
    
    def atan_safe(numerator, denominator): return np.arctan(numerator / denominator) if denominator != 0 else np.nan 
    
    # Right Handed Batsman Logic
    if RH == True: 
        if LX <= 0 and LY > 0: return "FINE LEG"
        elif LX <= 0 and LY <= 0: return "THIRD MAN"
        elif LX > 0 and LY < 0:
            if atan_safe(LY, LX) < np.pi / -4: return "COVER"
            elif atan_safe(LX, LY) <= np.pi / -4: return "LONG OFF" 
        elif LX > 0 and LY >= 0:
            if atan_safe(LY, LX) >= np.pi / 4: return "SQUARE LEG"
            elif atan_safe(LY, LX) <= np.pi / 4: return "LONG ON"
    # Left Handed Batsman Logic
    elif RH == False: 
        if LX <= 0 and LY > 0: return "THIRD MAN"
        elif LX <= 0 and LY <= 0: return "FINE LEG"
        elif LX > 0 and LY < 0:
            if atan_safe(LY, LX) < np.pi / -4: return "SQUARE LEG"
            elif atan_safe(LX, LY) <= np.pi / -4: return "LONG ON"
        elif LX > 0 and LY >= 0:
            if atan_safe(LY, LX) >= np.pi / 4: return "COVER"
            elif atan_safe(LY, LX) <= np.pi / 4: return "LONG OFF"
    return None

def calculate_scoring_angle(area):
    """Defines the fixed angle size for each wedge."""
    if area in ["FINE LEG", "THIRD MAN"]: return 90
    elif area in ["COVER", "SQUARE LEG", "LONG OFF", "LONG ON"]: return 45
    return 0

def create_spinner_wagon_wheel(df_in):
    # Standard size for single wagon wheel
    FIG_SIZE = (5, 3)

    if df_in.empty:
        fig, ax = plt.subplots(figsize=FIG_SIZE)
        ax.text(0.5, 0.5, "No Data", ha='center', va='center', fontsize=12)
        ax.axis('off')
        return fig

    # 1. Calculate Scoring Areas
    df_in["ScoringWagon"] = df_in.apply(calculate_scoring_wagon, axis=1)
    df_in["FixedAngle"] = df_in["ScoringWagon"].apply(calculate_scoring_angle)
    
    # 2. Aggregate Data (Runs and Balls for SR)
    summary = df_in.groupby("ScoringWagon").agg(
        TotalRuns=("Runs", "sum"), 
        FixedAngle=("FixedAngle", 'first')
    ).reset_index().dropna(subset=["ScoringWagon"])

    # Handedness Check
    is_rhb = df_in["IsBatsmanRightHanded"].mode().iloc[0] if not df_in["IsBatsmanRightHanded"].empty else True
    all_areas = ["FINE LEG", "SQUARE LEG", "LONG ON", "LONG OFF", "COVER", "THIRD MAN"] if is_rhb else \
                ["THIRD MAN", "COVER", "LONG OFF", "LONG ON", "SQUARE LEG", "FINE LEG"]
    
    template = pd.DataFrame({"ScoringWagon": all_areas, "FixedAngle": [calculate_scoring_angle(a) for a in all_areas]})
    summary = template.merge(summary.drop(columns=["FixedAngle"]), on="ScoringWagon", how="left").fillna(0)
    total_runs_overall = summary["TotalRuns"].sum()
    if total_runs_overall > 0:
        summary["RunPct"] = (summary["TotalRuns"] / total_runs_overall * 100)
    else:
        summary["RunPct"] = 0
        
    summary['Rank'] = summary['RunPct'].rank(method='dense', ascending=False)

    # 3. Plotting
    fig, ax = plt.subplots(figsize=FIG_SIZE)
    fig.patch.set_facecolor('white')
    
    angles = summary["FixedAngle"].tolist()
    pct_values = summary["RunPct"].tolist()
    # Highlight the area with the highest percentage of runs
    colors = ['#ff5000' if r == 1 and v > 0 else 'white' for r, v in zip(summary['Rank'], pct_values)]

    # Pie Chart
    wedges, _ = ax.pie(angles, colors=colors, wedgeprops={"width": 1, "edgecolor": "black", "linewidth": 0.8}, 
                       startangle=90, counterclock=False)

    # Labels
    for i, wedge in enumerate(wedges):
        val = pct_values[i]
        if val > 0:
            angle = (wedge.theta2 + wedge.theta1) / 2.
            x = 0.65 * np.cos(np.deg2rad(angle))
            y = 0.65 * np.sin(np.deg2rad(angle))
            
            # Contrast for #1 Rank
            t_color = 'white' if colors[i] == '#ff5000' else 'black'
            # Display as percentage (e.g., 25%)
            ax.text(x, y, f"{val:.0f}%", ha='center', va='center', fontsize=12, fontweight='bold', color=t_color)
            
    ax.axis('equal')
    return fig

# =========================================================
# _________________________________________________________________________________________________________________________________________________________________________________________
# PAGE SETUP LAYOUT
# =========================================================

st.set_page_config(
    layout="wide"
)
st.markdown(
    """
    <style>
    section[data-testid="stSidebar"] {
        width: 200px !important; 
    }
    <style>
    """,
    unsafe_allow_html=True,
)

    
# 1. CRITICAL: GET DATA AND CHECK FOR AVAILABILITY
if 'data_df' not in st.session_state:
    st.error("Please go back to the **Home** page and upload the data first to begin the analysis.")
    st.stop()
    
df_raw = st.session_state['data_df']
with st.sidebar:
    st.title("MEN'S")
    st.write("Red Ball")
# 1. Define columns with appropriate widths
col_title_space, col_legend, col_dataname = st.columns([1.5, 2.5, 1.5]) 

with col_title_space:
    st.title("SPINNERS")

with col_legend:
    legend_markdown = """
    <p style='font-size: 16px; margin-top: 30px;'>
        <span style='color: red; font-size: 20px;'>&#9679;</span> Wickets &nbsp;&nbsp;&nbsp; 
        <span style='color: royalblue; font-size: 20px;'>&#9679;</span> Boundaries &nbsp;&nbsp;&nbsp; 
        <span style='color: lightgrey; font-size: 20px;'>&#9679;</span> Others
    </p>
    """
    st.markdown(legend_markdown, unsafe_allow_html=True)

with col_dataname:
    # Use the variable defined in columns: col_dataname
    file_name = st.session_state.get('file_name', 'N/A')
    # Added a div with margin-top to align vertically with the legend
    st.markdown(f"""
        <div style='margin-top: 35px; text-align: right;'>
            <span style='color: grey; font-size: 14px;'>File: </span>
            <code style='font-size: 14px;'>{file_name}</code>
        </div>
    """, unsafe_allow_html=True)

# Ensure columns exist before attempting to convert them
if "BatsmanName" in df_raw.columns:
    df_raw["BatsmanName"] = df_raw["BatsmanName"].astype(str).str.upper()
if "BowlerName" in df_raw.columns:
    # Assuming 'BowlerName' is used elsewhere, convert it here too for consistency
    df_raw["BowlerName"] = df_raw["BowlerName"].astype(str).str.upper()
    
# 2. BASE FILTER: ONLY spin DELIVERIES
df_spin_base = df_raw[df_raw["DeliveryType"] == "Spin"]

# --- Prepare Initial Filter Options ---
if "BowlingTeam" in df_spin_base.columns:
    team_column = "BowlingTeam"
else:
    team_column = "BattingTeam" 
    st.warning("The 'BowlingTeam' column was not found. Displaying all Batting Teams as a fallback.")

# 3. FILTERS (Bowling Team, Bowler, and Innings)
filter_col1, filter_col2, filter_col3 = st.columns(3) 

# --- Render Bowling Team Filter (Col 1) ---
all_teams = ["All"] + sorted(df_spin_base[team_column].dropna().unique().tolist())
with filter_col1:
    bowl_team = st.selectbox("Bowling Team", all_teams, index=0)

# --- Determine Bowlers based on selected Team ---
df_for_bowlers = df_spin_base.copy()

if bowl_team != "All":
    # Filter the DataFrame used for populating the bowler list
    df_for_bowlers = df_for_bowlers[df_for_bowlers[team_column] == bowl_team]

if "BowlerName" in df_for_bowlers.columns:
    # Generate the list of bowlers from the team-filtered DataFrame
    relative_bowlers = ["All"] + sorted(df_for_bowlers["BowlerName"].dropna().unique().tolist())
else:
    relative_bowlers = ["All"]
    
# --- Render Bowler Name Filter (Col 2) ---
with filter_col2:
    bowler = st.selectbox("Bowler Name", relative_bowlers, index=0)

# --- Render Inningss Filter (Col 3) ---
Innings_options = ["All"]
if "Innings" in df_spin_base.columns:
    valid_Inningss = df_spin_base["Innings"].dropna().astype(int).unique()
    Innings_options.extend(sorted([str(i) for i in valid_Inningss]))
with filter_col3:
    selected_Innings = st.selectbox("Innings", Innings_options, index=0)

st.header(f"{bowler}")

# 4. Apply Filters to the Base spin Data
df_filtered = df_spin_base.copy()

# Apply Team Filter
if bowl_team != "All":
    df_filtered = df_filtered[df_filtered[team_column] == bowl_team]
    
# Apply Bowler Filter (This uses the value selected in the relative dropdown)
if bowler != "All":
    if "BowlerName" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["BowlerName"] == bowler]
    else:
        st.warning("BowlerName column not found for filtering.")

# Apply Innings Filter
if selected_Innings != "All" and "Innings" in df_filtered.columns:
    Innings_int = int(selected_Innings)
    df_filtered = df_filtered[df_filtered["Innings"] == Innings_int]

# =========================================================
# 5. SPLIT AND DISPLAY CHARTS (RHB vs LHB) 🏏
# =========================================================

# Check for the required column to split the data
if "IsBatsmanRightHanded" not in df_filtered.columns:
    st.error("Cannot split data by handedness: 'IsBatsmanRightHanded' column is missing.")
    st.stop()

# --- Data Split ---
# True is Right-Handed (RHB), False is Left-Handed (LHB)
df_rhb = df_filtered[df_filtered["IsBatsmanRightHanded"] == True]
df_lhb = df_filtered[df_filtered["IsBatsmanRightHanded"] == False]

# --- Display Layout ---
col_rhb, col_lhb = st.columns(2)

# === LEFT COLUMN: AGAINST RIGHT-HANDED BATSMEN (RHB) ===
with col_rhb:
    st.markdown("###  v RIGHT-HAND BAT")  

    # Chart 2: PITCHMAP
    pitch_map_col, run_pct_col = st.columns([1, 1]) 
    with pitch_map_col:
        st.markdown("###### PITCHMAP v RHB")
        st.pyplot(create_Spinner_pitch_map(df_rhb), use_container_width=True)    
    with run_pct_col:
        st.markdown("##### ")
        st.pyplot(create_Spinner_pitch_length_bars(df_rhb), use_container_width=True)
        
    # Chart 1: Crease Beehive
    st.markdown("###### CREASE BEEHIVE v RHB")
    st.pyplot(create_Spinner_crease_beehive(df_rhb, "RHB"), use_container_width=True)

     # Chart 3/4: RELEASE
    st.markdown("###### RELEASE v RHB")
    st.pyplot(create_Spinner_release_analysis(df_rhb, "RHB"), use_container_width=True)

    # Chart 7 Spinner Hitting Missing
    st.markdown("###### STUMP BEEHIVE v RHB")
    st.pyplot(create_spinner_hitting_missing(df_rhb,"RHB"),use_container_width = True)
   
    # Chart 8: SCORING AREAS
    st.markdown("###### SCORING AREAS by RHB")
    st.pyplot(create_spinner_wagon_wheel(df_rhb),use_container_width = True)


# === RIGHT COLUMN: AGAINST LEFT-HANDED BATSMEN (LHB) ===

with col_lhb:
    st.markdown("###  v LEFT-HAND BAT")

    # Chart 2: PITCHMAP
    pitch_map_col, run_pct_col = st.columns([1, 1]) 
    with pitch_map_col:
        st.markdown("###### PITCHMAP v LHB")
        st.pyplot(create_Spinner_pitch_map(df_lhb), use_container_width=True)    
    with run_pct_col:
        st.markdown("##### ")
        st.pyplot(create_Spinner_pitch_length_bars(df_lhb), use_container_width=True)
    
    # Chart 1: Crease Beehive (using the new local function)
    st.markdown("###### CREASE BEEHIVE v LHB")
    st.pyplot(create_Spinner_crease_beehive(df_lhb, "LHB"), use_container_width=True)

    # Chart 3/4: RELEASE
    st.markdown("###### RELEASE v LHB")
    st.pyplot(create_Spinner_release_analysis(df_lhb, "LHB"), use_container_width=True)

    # Chart 7 Spinner Hitting Missing
    st.markdown("###### STUMP BEEHIVE v LHB")
    st.pyplot(create_spinner_hitting_missing(df_lhb,"LHB"),use_container_width = True)

    # Chart 9: Wagon Wheel SR
    st.markdown("###### SCORING AREAS by LHB")
    st.pyplot(create_spinner_wagon_wheel(df_lhb),use_container_width = True)
