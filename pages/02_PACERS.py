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


# --- CHART 3: PITCHMAP (BOUNCE LOCATION) ---
def create_pacer_pitch_map(df_in): 
    PITCH_BINS = {
           "Full Toss": [-5, 0.5],
            "Yorker": [0.5,2.5],
            "Slot": [2.5, 5.8],
            "Length": [5.8, 8],
            "Short": [8, 10],
            "Bouncer": [10, 18]
    }

    if df_in.empty:
        # Create an empty figure with a text note if data is missing
        fig, ax = plt.subplots(figsize=(4,6))
        ax.text(0.5, 0.5, f"No data for Pacer Pitch Map", ha='center', va='center', fontsize=12)
        ax.axis('off')
        return fig
        
    # --- Data Filtering ---
    pitch_wickets = df_in[df_in["Wicket"] == True]
    pitch_non_wickets = df_in[df_in["Wicket"] == False]
    
    # --- Chart Setup ---
    fig, ax = plt.subplots(figsize=(4,6)) # Maintained figsize=(4,6)
    ax.set_facecolor('white')
    fig.patch.set_facecolor('white')

    # --- 1. Add Zone Lines & Labels (Horizontal Lines) ---
    
    # Determine boundary Y values to draw lines (excluding the start of the lowest bin)
    boundary_y_values = sorted([v[0] for v in PITCH_BINS.values() if v[0] > -4.0], reverse=True)

    for y_val in boundary_y_values:
        ax.axhline(y=y_val, color="lightgrey", linewidth=1.0, linestyle="--")

    # Add zone labels (Annotation)
    for length, bounds in PITCH_BINS.items():
        mid_y = (bounds[0] + bounds[1]) / 2
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
        s=60, 
        c='#D3D3D3', 
        edgecolor='white', 
        linewidths=1.0, 
        alpha=0.9,
        label="No Wicket"
    )

    # Wickets (red)
    ax.scatter(
        pitch_wickets["BounceY"], pitch_wickets["BounceX"], 
        s=90, 
        c='red', 
        edgecolor='white', 
        linewidths=1.0, 
        alpha=0.95,
        label="Wicket"
    )
    
    # --- 2. Add Stump lines (Vertical Lines) ---
    ax.axvline(x=-0.18, color="#777777", linestyle="--", linewidth=1)
    ax.axvline(x=0.18, color="#777777", linestyle="--", linewidth=1)
    ax.axvline(x=0, color="#777777", linestyle="--", linewidth=0.8)
    
    # --- 4. Layout (Axis and Spines) ---
    
    # Set axis limits
    ax.set_xlim([-1.5, 1.5])
    # Reverse the axis to match the cricket visual (batter at bottom)
    ax.set_ylim([16.0, -4.0]) 

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

# --- CHART 3b: PITCH LENGTH METRICS (BOWLER FOCUS) ---
# --- Helper function for Pitch Bins (Hardcoded for Seam) ---
def get_pacer_pitch_bins():
    return {
           "Full Toss": [-5, 0.5],
            "Yorker": [0.5,2.5],
            "Slot": [2.5, 5.8],
            "Length": [5.8, 8],
            "Short": [8, 10],
            "Bouncer": [10, 18]
    }
def create_pacer_pitch_length_bars(df_in):
    # Fixed size to accommodate three stacked charts comfortably
    FIG_SIZE = (3, 4.5) 
    
    if df_in.empty:
        fig, ax = plt.subplots(figsize=FIG_SIZE)
        ax.text(0.5, 0.5, "No Data for Pacer Pitch Length Comparison", ha='center', va='center', fontsize=12)
        ax.axis('off')
        return fig

    # Get the pitch bins and define order (Fixed for Pacer)
    PITCH_BINS_DICT = get_pacer_pitch_bins()
    ordered_keys = ["Full Toss", "Yorker","Slot", "Length", "Short"]
    
    # 1. Data Preparation
    def assign_pitch_length(x):
        for length, bounds in PITCH_BINS_DICT.items():
            if bounds[0] <= x < bounds[1]: return length
        return None

    df_pitch = df_in.copy()
    df_pitch["PitchLength"] = df_pitch["BounceX"].apply(assign_pitch_length)
    
    # Aggregate data for White Ball metrics
    df_summary = df_pitch.groupby("PitchLength").agg(
        Runs=("Runs", "sum"), 
        Wickets=("Wicket", lambda x: (x == True).sum()), 
        Balls=("Wicket", "count"),
        Dots=("Runs", lambda x: (x == 0).sum())
    ).reset_index().set_index("PitchLength").reindex(ordered_keys).fillna(0)
    
    # White Ball Calculations
    df_summary["Economy"] = df_summary.apply(lambda row: (row["Runs"] / row["Balls"] * 6) if row["Balls"] > 0 else 0.0, axis=1)
    df_summary["Dismissals"] = df_summary["Wickets"]
    df_summary["Dot%"] = df_summary.apply(lambda row: (row["Dots"] / row["Balls"] * 100) if row["Balls"] > 0 else 0.0, axis=1)
    
    # Categories for plotting (reversed for barh)
    categories = df_summary.index.tolist()[::-1]
    
    # 2. Chart Setup (3 Rows, 1 Column)
    fig, axes = plt.subplots(3, 1, figsize=FIG_SIZE, sharey=True) 
    plt.subplots_adjust(hspace=10) 

    # --- Metrics and Titles (Order: Economy, Dismissals, Dot%) ---
    metrics = ["Economy", "Dismissals", "Dot%"]
    titles = ["Economy", "Dismissals", "Dot %"]

    # Dynamic limits for scaling
    max_eco = df_summary["Economy"].max() * 1.2 if df_summary["Economy"].max() > 0 else 12
    max_wkts = df_summary["Dismissals"].max() * 1.5 if df_summary["Dismissals"].max() > 0 else 5
    
    xlim_limits = {
        "Economy": (0, max_eco),
        "Dismissals": (0, max_wkts),
        "Dot%": (0, 100)
    }

    # --- Plotting Loop ---
    for i, ax in enumerate(axes):
        metric = metrics[i]
        title = titles[i]
        
        values = df_summary[metric].values[::-1] 
        ax.set_xlim(xlim_limits[metric])
        
        # Horizontal Bar Chart
        ax.barh(categories, values, height=0.49, color='#ff5000', zorder=3, alpha=0.9)
        
        # --- Annotations ---
        for j, (cat, val) in enumerate(zip(categories, values)):
            if metric == "Dismissals":
                label = f"{int(val)}"
            elif metric == "Dot%":
                label = f"{val:.0f}%"
            else: # Economy
                label = f"{val:.1f}"
            
            ax.text(val, j, label, 
                    ha='left', va='center', 
                    fontsize=10, fontweight='bold', color='black',
                    bbox=dict(facecolor='White', alpha=0.8, edgecolor='none', pad=2),
                    zorder=4)

        # --- Formatting ---
        ax.set_title(title, fontsize=10, fontweight='bold', pad=0, loc='left')
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
def create_pacer_crease_beehive(df_in, handedness_label): # Renamed function and parameter
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
    
    # BOWLING AVERAGE CALCULATION (Same formula as before, just interpreted differently)
    # summary["Avg Runs/Wicket"] = summary.apply(lambda row: row["Runs"] / row["Wickets"] if row["Wickets"] > 0 else np.nan, axis=1)
    # Economy Calculation
    summary["Economy"] = summary.apply(lambda row: (row["Runs"] / row["Balls"]) * 6 if row["Balls"] > 0 else np.nan, axis=1)

    # -----------------------------------------------------------
    # --- 1. SETUP SUBPLOTS ---
    fig = plt.figure(figsize=(7, 5)) 
    gs = fig.add_gridspec(2, 1, height_ratios=[4, 1], hspace=0.005) 
    ax_bh = fig.add_subplot(gs[0, 0])      
    ax_boxes = fig.add_subplot(gs[1, 0])   
    fig.patch.set_facecolor('white')
    

    # -----------------------------------------------------------
    ## --- 2. CHART 2a: CREASE BEEHIVE (ax_bh) ---
    
    # --- Traces ---
    ax_bh.scatter(regular_balls["CreaseY"], regular_balls["CreaseZ"], s=40, c='lightgrey', edgecolor='white', linewidths=1.0, alpha=0.95, label="Regular Ball")
    ax_bh.scatter(boundaries["CreaseY"], boundaries["CreaseZ"], s=80, c='royalblue', edgecolor='white', linewidths=1.0, alpha=0.95, label="Boundary")
    ax_bh.scatter(wickets["CreaseY"], wickets["CreaseZ"], s=80, c='red', edgecolor='white', linewidths=1.0, alpha=0.95, label="Wicket")

    # --- Reference Lines ---
    ax_bh.axvline(x=-0.18, color="grey", linestyle="--", linewidth=0.5) 
    ax_bh.axvline(x=0.18, color="grey", linestyle="--", linewidth=0.5)
    ax_bh.axvline(x=0, color="grey", linestyle="--", linewidth=0.5) 
    ax_bh.axvline(x=-0.92, color="grey", linestyle="-", linewidth=0.5) 
    ax_bh.axvline(x=0.92, color="grey", linestyle="-", linewidth=0.5)
    ax_bh.axhline(y=0.78, color="grey", linestyle="-", linewidth=0.5)

    # --- Annotation ---
    ax_bh.text(-1.5, 0.78, "Stump line", ha='left', va='bottom', fontsize=8, color="grey", transform=ax_bh.transData)
    
    # --- Formatting ---
    ax_bh.set_xlim([-2, 2])
    ax_bh.set_ylim([0, 2])
    ax_bh.set_aspect('equal', adjustable='box')
    ax_bh.set_xticks([]); ax_bh.set_yticks([]); ax_bh.grid(False)
    for spine in ax_bh.spines.values():
        spine.set_visible(False)
    ax_bh.set_facecolor('white')
    
    # -----------------------------------------------------------
    ## --- 3. CHART 2b: LATERAL PERFORMANCE BOXES (ax_boxes) --
    num_regions = len(ordered_zones)
    box_width = 1 / num_regions
    box_height = 0.4 
    left = 0
    
    # Color Normalization
    eco_values = summary["Economy"].dropna()
    norm = mcolors.Normalize(vmin=3, vmax=9) 
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
                              edgecolor="black", facecolor=color, linewidth=0.4)
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

# --- CHART 4: RELEASE SPEED DISTRIBUTION ---
def create_pacer_release_speed_distribution(df_in, handedness_label):
    FIG_SIZE = (4, 4.4)

    if df_in.empty or "ReleaseSpeed" not in df_in.columns or df_in["ReleaseSpeed"].empty:
        fig, ax = plt.subplots(figsize=FIG_SIZE)
        ax.text(0.5, 0.5, f"No Data or Missing 'ReleaseSpeed' for {handedness_label}", ha='center', va='center', fontsize=12)
        ax.axis('off')
        return fig

    # 1. Prepare Data and Determine Histogram Parameters
    speeds = df_in["ReleaseSpeed"].dropna().values
    speeds = speeds[(speeds >= 50) & (speeds <= 155)]

    total_balls = len(speeds)
    
    if total_balls == 0:
        fig, ax = plt.subplots(figsize=FIG_SIZE)
        ax.text(0.5, 0.5, "No Deliveries Found", ha='center', va='center', fontsize=12)
        ax.axis('off')
        return fig

    # Calculate the range to ensure fixed bin width of 5 km/h
    min_speed = np.floor(speeds.min() / 5) * 5
    max_speed = np.ceil(speeds.max() / 5) * 5
    
    # Generate bins with a fixed width of 5 km/h
    bin_width = 5
    bins = np.arange(min_speed, max_speed + bin_width, bin_width)
    
    # Calculate histogram counts and edges
    counts, bin_edges = np.histogram(speeds, bins=bins)
    
    # 2. Process Data for Plotting & Filtering
    raw_percentages = (counts / total_balls) * 100
    # Filter out bins with less than 5 balls
    MIN_BALLS = 5
    valid_counts = []
    valid_bin_labels = []
    
    for i in range(len(counts)):
        if raw_percentages[i] >= 1.0:
            lower = int(bin_edges[i])
            upper = int(bin_edges[i+1])
            label = f"{lower}-{upper}"
            
            valid_counts.append(counts[i])
            valid_bin_labels.append(label)

    if not valid_counts:
        fig, ax = plt.subplots(figsize=FIG_SIZE)
        ax.text(0.5, 0.5, f"No Bins Meet the {MIN_BALLS}-Ball Minimum Filter", ha='center', va='center', fontsize=10)
        ax.axis('off')
        return fig
        
    # Calculate percentages for valid bins only
    valid_percentages = (np.array(valid_counts) / total_balls) * 100
    
    # Reverse order for horizontal bar chart (fastest speeds typically at the top)
    plot_percentages = valid_percentages[::-1]
    plot_labels = valid_bin_labels[::-1]
    plot_counts = valid_counts[::-1]
    
    # 3. Chart Generation (Horizontal Bar / Histogram)
    
    fig, ax = plt.subplots(figsize=FIG_SIZE)
    
    
    y_pos = np.arange(len(plot_labels))
    
    ax.barh(
        y_pos,
        plot_percentages,
        color='#ff5000', # Single, uniform color
        height=0.6
    )

    
            # Add percentage labels
    for i, pct in enumerate(plot_percentages):
        count = plot_counts[i]
        # Display percentage (e.g., 25%)
        label_text = f'{pct:.0f}%'
    
        # Placement logic: Always outside the bar
        # 1. x_pos: Start the text slightly after the end of the bar (pct)
        x_pos = pct + 0.5 
        # 2. ha: Align the start of the text to x_pos
        ha = 'left' 
        text_color = 'black'
    
        ax.text(
        x_pos, 
        i, 
        label_text, 
        ha=ha, va='center', fontsize=12, color=text_color, fontweight='bold'
    )
        


    # 4. Formatting
    
    # Set Y-axis labels
    ax.set_yticks(y_pos, labels=plot_labels, fontsize=10)
    
    # Set X-axis limit slightly higher than the max percentage for clean labels
    max_pct = np.max(plot_percentages) if len(plot_percentages) > 0 else 0
    ax.set_xlim(0, max(max_pct * 1.1, 10)) 
    
    # Hide axis ticks/labels
    ax.set_xticklabels([])
    ax.set_xticks([])
    
    # Remove all spines 
    ax.spines['top'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['right'].set_visible(False)
    # --- ADDING SHARP BORDER ---
    # We create a custom Rectangle patch with 'miter' joinstyle and add it to the figure.
    # Get the bounding box of the axes in figure coordinates
    ax_bbox = ax.get_position()
    
    # Calculate padding based on figure dimensions to ensure a consistent border
    # Use 0.01 for x and y to give a small padding
    padding_x = 0.2* FIG_SIZE[0] / fig.get_size_inches()[0] # Scale padding based on total figure width
    padding_y = 0.01 * FIG_SIZE[1] / fig.get_size_inches()[1] # Scale padding based on total figure height

    border_rect = patches.Rectangle(
        (ax_bbox.x0 - padding_x, ax_bbox.y0 - padding_y), # Start (x,y)
        ax_bbox.width + 2 * padding_x,                    # Width
        ax_bbox.height + 2 * padding_y,                   # Height
        facecolor='none',
        edgecolor='black',
        linewidth=0.5,
        transform=fig.transFigure, # Use figure coordinates
        clip_on=False,             # Ensure it's not clipped
        joinstyle='miter'          # THIS ENSURES SHARP CORNERS
    )
    fig.add_artist(border_rect) # Add the custom rectangle to the figure

    return fig

# Chart 5 Bowler Release Map
def create_pacer_release_analysis(df_in, handedness_label): 
    FIG_SIZE = (4, 3.4) # Increased height for both charts

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
    gs = GridSpec(2, 1, figure=fig, height_ratios=[4, 1.2], hspace=0.1)
    
    ax_map = fig.add_subplot(gs[0, 0])
    ax_metrics = fig.add_subplot(gs[1, 0])

    # --- 3. Plot Release Zone Map (ax_map) ---
    
    release_wickets = df_in[df_in["Wicket"] == True]
    release_non_wickets = df_in[df_in["Wicket"] == False]
    
    # Non-Wickets (light grey)
    ax_map.scatter(
        release_non_wickets["ReleaseY"], release_non_wickets["ReleaseZ"], 
        s=40, color='#D3D3D3', alpha=0.8, edgecolors='white', linewidths=0.5, label="No Wicket"
    )

    # Wickets (red)
    ax_map.scatter(
        release_wickets["ReleaseY"], release_wickets["ReleaseZ"], 
        s=80, color='red', alpha=1.0, edgecolors='white', linewidths=1.0, label="Wicket", zorder=5
    )
    
    # Add Stump Lines
    stump_lines = [-0.18, 0, 0.18]
    for y_val in stump_lines:
        ax_map.axvline(x=y_val, color="#777777", linestyle="--", linewidth=1.0)
    
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
    ax_metrics.text(0.05, 1, "W:", ha='right', va='center', fontsize=10, fontweight='bold')
    ax_metrics.text(0.05, 0.5, "Avg:", ha='right', va='center', fontsize=10, fontweight='bold')
    ax_metrics.text(0.05, 0, "SR:", ha='right', va='center', fontsize=10, fontweight='bold')

    # LEFT Values
    ax_metrics.text(0.2, 1, format_metric(left["Wickets"], is_wickets=True), ha='center', va='center', fontsize=12, color='black', fontweight='bold')
    ax_metrics.text(0.2, 0.5, format_metric(left["BA"]), ha='center', va='center', fontsize=12, color='black', fontweight='bold')
    ax_metrics.text(0.2, 0, format_metric(left["SR"]), ha='center', va='center', fontsize=12, color='black', fontweight='bold')

    # RIGHT Values
    ax_metrics.text(0.9, 1, format_metric(right["Wickets"], is_wickets=True), ha='center', va='center', fontsize=12, color='black', fontweight='bold')
    ax_metrics.text(0.9, 0.5, format_metric(right["BA"]), ha='center', va='center', fontsize=12, color='black', fontweight='bold')
    ax_metrics.text(0.9, 0, format_metric(right["SR"]), ha='center', va='center', fontsize=12, color='black', fontweight='bold')
    
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

# Chart 11: Speed Effectiveness - Death Overs
def create_pacer_speed_effectiveness_3col(df_in):
    if df_in.empty:
        fig, ax = plt.subplots(figsize=(6, 1))
        ax.text(0.5, 0.5, "No Data", ha='center', va='center')
        ax.axis('off')
        return fig

    # 1. Define Speed Groups
    def assign_speed_group(speed):
        if speed < 125:
            return "Slower (<125)"
        else:
            return "Pace On (>125)"

    df_temp = df_in.copy()
    df_temp["ReleaseSpeed"] = pd.to_numeric(df_temp["ReleaseSpeed"], errors='coerce')
    df_temp = df_temp.dropna(subset=["ReleaseSpeed"])
    df_temp["SpeedGroup"] = df_temp["ReleaseSpeed"].apply(assign_speed_group)
    
    # 2. Aggregate Data
    ordered_groups = ["Slower (<125)", "Pace On (>125)"]
    summary = df_temp.groupby("SpeedGroup").agg(
        Runs=("Runs", "sum"), 
        Balls=("Runs", "count"),
        Dots=("Runs", lambda x: (x == 0).sum()),
        Boundaries=("Runs", lambda x: ((x == 4) | (x == 6)).sum())
    ).reindex(ordered_groups).fillna(0)
    
    # White Ball Metrics
    summary["Eco"] = (summary["Runs"] / summary["Balls"] * 6).fillna(0)
    summary["Bd%"] = (summary["Boundaries"] / summary["Balls"] * 100).fillna(0)
    summary["Dot%"] = (summary["Dots"] / summary["Balls"] * 100).fillna(0)

    # 3. Plotting (1 row, 3 columns)
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(9, 2.89), sharey=True)
    plt.subplots_adjust(wspace=0.3) 
    
    y = np.arange(len(ordered_groups))
    height = 0.2
    color_pacer = '#ff5000'

    # --- Column 1: Boundary % ---
    ax1.barh(y, summary["Bd%"], color=color_pacer, edgecolor='white', height=height)
    ax1.set_title("Bd %", fontsize=12, fontweight='bold')
    ax1.set_yticks(y)
    ax1.set_yticklabels(ordered_groups, fontsize=11, fontweight='bold')
    for i, v in enumerate(summary["Bd%"]):
        ax1.text(v + 1, i, f'{v:.0f}%', va='center', fontweight='bold', fontsize=10)

    # --- Column 2: Economy ---
    ax2.barh(y, summary["Eco"], color=color_pacer, edgecolor='white', height=height)
    ax2.set_title("Economy", fontsize=12, fontweight='bold')
    for i, v in enumerate(summary["Eco"]):
        ax2.text(v + 0.2, i, f'{v:.1f}', va='center', fontweight='bold', fontsize=10)

    # --- Column 3: Dot % ---
    ax3.barh(y, summary["Dot%"], color=color_pacer, edgecolor='white', height=height)
    ax3.set_title("Dot %", fontsize=12, fontweight='bold')
    for i, v in enumerate(summary["Dot%"]):
        ax3.text(v + 1, i, f'{v:.0f}%', va='center', fontweight='bold', fontsize=10)

    # Formatting
    for ax in [ax1, ax2, ax3]:
        ax.spines[['top', 'right', 'bottom']].set_visible(False)
        ax.xaxis.set_visible(False)
        ax.invert_yaxis() 

    return fig

# Chart 12: Wagon Wheel : Strike Rate
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

def create_pacer_death_wagon_wheel(df_in):
    # Standard size for single wagon wheel
    FIG_SIZE = (5, 3)

    # Filter for Death Overs (16-20)
    df_death = df_in[df_in["Over"] >= 16].copy()

    if df_death.empty:
        fig, ax = plt.subplots(figsize=FIG_SIZE)
        ax.text(0.5, 0.5, "No Data for Death Overs (16-20)", ha='center', va='center', fontsize=12)
        ax.axis('off')
        return fig

    # 1. Calculate Scoring Areas
    df_death["ScoringWagon"] = df_death.apply(calculate_scoring_wagon, axis=1)
    df_death["FixedAngle"] = df_death["ScoringWagon"].apply(calculate_scoring_angle)
    
    # 2. Aggregate Data (Runs and Balls for SR)
    summary = df_death.groupby("ScoringWagon").agg(
        TotalRuns=("Runs", "sum"), 
        TotalBalls=("Runs", "count"),
        FixedAngle=("FixedAngle", 'first')
    ).reset_index().dropna(subset=["ScoringWagon"])

    # Handedness Check
    is_rhb = df_death["IsBatsmanRightHanded"].mode().iloc[0] if not df_death["IsBatsmanRightHanded"].empty else True
    all_areas = ["FINE LEG", "SQUARE LEG", "LONG ON", "LONG OFF", "COVER", "THIRD MAN"] if is_rhb else \
                ["THIRD MAN", "COVER", "LONG OFF", "LONG ON", "SQUARE LEG", "FINE LEG"]
    
    template = pd.DataFrame({"ScoringWagon": all_areas, "FixedAngle": [calculate_scoring_angle(a) for a in all_areas]})
    summary = template.merge(summary.drop(columns=["FixedAngle"]), on="ScoringWagon", how="left").fillna(0)
    summary["SR"] = summary.apply(lambda row: (row["TotalRuns"] / row["TotalBalls"] * 100) if row["TotalBalls"] > 0 else 0, axis=1)
    summary['RankSR'] = summary['SR'].rank(method='dense', ascending=False)

    # 3. Plotting
    fig, ax = plt.subplots(figsize=FIG_SIZE)
    fig.patch.set_facecolor('white')
    
    angles = summary["FixedAngle"].tolist()
    sr_values = summary["SR"].tolist()
    colors = ['#ff5000' if r == 1 and v > 0 else 'white' for r, v in zip(summary['RankSR'], sr_values)]

    # Pie Chart
    wedges, _ = ax.pie(angles, colors=colors, wedgeprops={"width": 1, "edgecolor": "black", "linewidth": 0.8}, 
                       startangle=90, counterclock=False)

    # Labels
    for i, wedge in enumerate(wedges):
        sr_val = sr_values[i]
        if sr_val > 0:
            angle = (wedge.theta2 + wedge.theta1) / 2.
            x = 0.65 * np.cos(np.deg2rad(angle))
            y = 0.65 * np.sin(np.deg2rad(angle))
            
            # Contrast for #1 Rank
            t_color = 'white' if colors[i] == '#ff5000' else 'black'
            ax.text(x, y, f"{sr_val:.0f}", ha='center', va='center', fontsize=12,fontweight = 'bold', color=t_color)
    ax.axis('equal')
    return fig



# PAGE SETUP LAYOUT

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
col_title_space, col_legend, col_dataname = st.columns([1, 2.5, 1.5]) 

with col_title_space:
    st.title("PACERS")

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
# 2. BASE FILTER: ONLY SEAM DELIVERIES
df_seam_base = df_raw[df_raw["DeliveryType"] == "Seam"]


# --- Prepare Initial Filter Options ---
if "BowlingTeam" in df_seam_base.columns:
    team_column = "BowlingTeam"
else:
    team_column = "BattingTeam" 
    st.warning("The 'BowlingTeam' column was not found. Displaying all Batting Teams as a fallback.")

# 3. FILTERS (Bowling Team, Bowler, and Innings)
filter_col1, filter_col2, filter_col3 = st.columns(3) 

# --- Render Bowling Team Filter (Col 1) ---
all_teams = ["All"] + sorted(df_seam_base[team_column].dropna().unique().tolist())
with filter_col1:
    bowl_team = st.selectbox("Bowling Team", all_teams, index=0)

# --- Determine Bowlers based on selected Team ---
df_for_bowlers = df_seam_base.copy()

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
if "Innings" in df_seam_base.columns:
    valid_Inningss = df_seam_base["Innings"].dropna().astype(int).unique()
    Innings_options.extend(sorted([str(i) for i in valid_Inningss]))
with filter_col3:
    selected_Innings = st.selectbox("Innings", Innings_options, index=0)

st.header(f"{bowler}")

# 4. Apply Filters to the Base Seam Data
df_filtered = df_seam_base.copy()

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

    # Chart 3: PITCHMAP
    pitch_map_col, run_pct_col = st.columns([1, 1]) 
    with pitch_map_col:
        st.markdown("###### PITCHMAP v RHB")
        st.pyplot(create_pacer_pitch_map(df_rhb), use_container_width=True)    
    with run_pct_col:
        st.markdown("##### ")
        st.pyplot(create_pacer_pitch_length_bars(df_rhb), use_container_width=True)
        
    # Chart 1a: Crease Beehive (using the new local function)
    st.markdown("###### CREASE BEEHIVE v RHB")
    st.pyplot(create_pacer_crease_beehive(df_rhb, "RHB"), use_container_width=True)

    # Chart 1b: Lateral Performance Boxes (Bowling Avg)
    # st.pyplot(create_pacer_lateral_performance_boxes(df_rhb, "RHB"), use_container_width=True)
    

     # Chart 4/5: RELEASE
    pace_col, release_col = st.columns([2, 2])
    with pace_col:
        st.markdown("###### RELEASE SPEED v RHB")
        st.pyplot(create_pacer_release_speed_distribution(df_rhb, "RHB"), use_container_width=True)
    with release_col:
        st.markdown("###### RELEASE v RHB")
        st.pyplot(create_pacer_release_analysis(df_rhb, "RHB"), use_container_width=True)
    

    # Chart 16: Speed Distribution - Death Overs
    st.markdown("###### SPEED DISTRIBUTION IN DEATH OVERS - OVERALL")
    st.pyplot(create_pacer_speed_effectiveness_3col(df_do), use_container_width=True)


# === RIGHT COLUMN: AGAINST LEFT-HANDED BATSMEN (LHB) ===
with col_lhb:
    st.markdown("###  v LEFT-HAND BAT")

    # Chart 3: PITCHMAP
    pitch_map_col, run_pct_col = st.columns([1, 1]) 
    with pitch_map_col:
        st.markdown("###### PITCHMAP v LHB")
        st.pyplot(create_pacer_pitch_map(df_lhb), use_container_width=True)    
    with run_pct_col:
        st.markdown("##### ")
        st.pyplot(create_pacer_pitch_length_bars(df_lhb), use_container_width=True)
        
    # Chart 1a: Crease Beehive (using the new local function)
    st.markdown("###### CREASE BEEHIVE v LHB")
    st.pyplot(create_pacer_crease_beehive(df_lhb, "LHB"), use_container_width=True)

    # Chart 1b: Lateral Performance Boxes (Bowling Avg)
    # st.pyplot(create_pacer_lateral_performance_boxes(df_lhb, "LHB"), use_container_width=True)

    # Chart 4/5: RELEASE
    pace_col, release_col = st.columns([2, 2]) 
    with pace_col:
        st.markdown("###### RELEASE SPEED v LHB")
        st.pyplot(create_pacer_release_speed_distribution(df_lhb, "LHB"), use_container_width=True)
    with release_col:
        st.markdown("###### RELEASE v LHB")
        st.pyplot(create_pacer_release_analysis(df_lhb, "LHB"), use_container_width=True)
        
    
    # Chart 16: Wagon wheel sr - Death Overs
    wagon_rhb,wagon_lhb = st.columns([1,1])
    with wagon_rhb:
        st.markdown("###### STRIKE RATE IN DEATH  OVERS v RHB ")
        st.pyplot(create_pacer_death_wagon_wheel(df_rhb), use_container_width=True)
    with wagon_lhb:
        st.markdown("###### STRIKE RATE UIN DEATH OVERS v LHB")
        st.pyplot(create_pacer_death_wagon_wheel(df_rhb), use_container_width=True)   
