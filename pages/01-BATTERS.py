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
from matplotlib.backends.backend_pdf import PdfPages
import io, zipfile

# --- 1. GLOBAL UTILITY FUNCTIONS ---

# Required columns check
REQUIRED_COLS = [
    "BatsmanName", "DeliveryType", "Wicket", "StumpsY", "StumpsZ", 
    "BattingTeam", "CreaseY", "CreaseZ", "Runs", "IsBatsmanRightHanded", 
    "LandingX", "LandingY", "BounceX", "BounceY", "InterceptionX", 
    "InterceptionZ", "InterceptionY", "Over"
]

# Function to encode Matplotlib figure to image for Streamlit
def fig_to_image(fig):
    return fig

# --- CHART 1: ZONAL ANALYSIS (CBH Boxes) ---
def create_zonal_analysis(df_in, batsman_name, delivery_type):
    if df_in.empty:
        fig, ax = plt.subplots(figsize=(4, 4)); ax.text(0.5, 0.5, "No Data", ha='center', va='center'); return fig

    is_right_handed = True
    handed_data = df_in["IsBatsmanRightHanded"].dropna().unique()
    if len(handed_data) > 0 and batsman_name != "All": is_right_handed = handed_data[0]
        
    right_hand_zones = { "Z1": (-0.72, 0, -0.45, 1.91), "Z2": (-0.45, 0, -0.18, 0.71), "Z3": (-0.18, 0, 0.18, 0.71), "Z4": (-0.45, 0.71, -0.18, 1.31), "Z5": (-0.18, 0.71, 0.18, 1.31), "Z6": (-0.45, 1.31, 0.18, 1.91)}
    left_hand_zones = { "Z1": (0.45, 0, 0.72, 1.91), "Z2": (0.18, 0, 0.45, 0.71), "Z3": (-0.18, 0, 0.18, 0.71), "Z4": (0.18, 0.71, 0.45, 1.31), "Z5": (-0.18, 0.71, 0.18, 1.31), "Z6": (-0.18, 1.31, 0.45, 1.91)}
    zones_layout = right_hand_zones if is_right_handed else left_hand_zones
    
    def assign_zone(row):
        x, y = row["CreaseY"], row["CreaseZ"]
        for zone, (x1, y1, x2, y2) in zones_layout.items():
            if x1 <= x <= x2 and y1 <= y <= y2: return zone
        return "Other"

    df_chart2 = df_in.copy(); df_chart2["Zone"] = df_chart2.apply(assign_zone, axis=1)
    df_chart2 = df_chart2[df_chart2["Zone"] != "Other"]
    
    # 1. UPDATED AGGREGATION: Added Boundaries for B%
    summary = (
        df_chart2.groupby("Zone").agg(
            Runs=("Runs", "sum"), 
            Wickets=("Wicket", lambda x: (x == True).sum()), 
            Balls=("Wicket", "count"),
            Boundaries=("Runs", lambda x: ((x == 4) | (x == 6)).sum())
        )
        .reindex([f"Z{i}" for i in range(1, 7)]).fillna(0)
    )
    
    # 2. UPDATED METRICS
    summary["Avg"] = summary.apply(lambda row: row["Runs"] / row["Wickets"] if row["Wickets"] > 0 else 0, axis=1)
    summary["SR"] = summary.apply(lambda row: (row["Runs"] / row["Balls"]) * 100 if row["Balls"] > 0 else 0, axis=1)
    summary["BPct"] = summary.apply(lambda row: (row["Boundaries"] / row["Balls"]) * 100 if row["Balls"] > 0 else 0, axis=1)

    # 3. CHANGE COLORING TO STRIKE RATE
    sr_values = summary["SR"]
    sr_max = sr_values.max() if sr_values.max() > 0 else 200 # Default max for scaling
    sr_min = 0
    norm = mcolors.Normalize(vmin=sr_min, vmax=sr_max)
    cmap = cm.get_cmap('Wistia')

    fig_boxes, ax = plt.subplots(figsize=(3,2), subplot_kw={'xticks': [], 'yticks': []}) 
    
    for zone, (x1, y1, x2, y2) in zones_layout.items():
        w, h = x2 - x1, y2 - y1
        z_key = zone.replace("Zone ", "Z")
        
        runs, wkts, avg, sr, bpct = (0, 0, 0, 0, 0)
        if z_key in summary.index:
            wkts = int(summary.loc[z_key, "Wickets"])
            avg = summary.loc[z_key, "Avg"]
            sr = summary.loc[z_key, "SR"]
            bpct = summary.loc[z_key, "BPct"]
        
        # Color mapped to SR instead of Avg
        color = cmap(norm(sr)) if sr > 0 else 'white'

        ax.add_patch(patches.Rectangle((x1, y1), w, h, edgecolor="black", facecolor=color, linewidth=0.8))

        # 4. UPDATED TEXT: SR, Boundry%, Wicket, Avg
        ax.text(x1 + w / 2, y1 + h / 2, 
        f"SR: {sr:.0f}\nBND%: {bpct:.0f}%\nW: {wkts}\nA: {avg:.1f}", 
        ha="center", 
        va="center", 
        fontsize=4.5, # Slightly smaller to fit new text
        fontweight = 'bold',
        color="black" if norm(sr) < 0.6 else "white", # Adaptive text color
        linespacing=1.2)

        # Spines and styling logic...
        spine_color = 'black'
        spine_width = 0.5
        for spine_name in ['left', 'top', 'bottom','right']:  
            ax.spines[spine_name].set_visible(True)
            ax.spines[spine_name].set_color(spine_color)
            ax.spines[spine_name].set_linewidth(spine_width)

    ax.set_xlim(-0.75, 0.75); ax.set_ylim(0, 2); ax.axis('off'); 
    plt.tight_layout(pad=0.1) 
    return fig_boxes    
    bbox = ax.get_position()
    LINE_THICKNESS = 0.3
    
    # 2. DEFINE CUSTOM PADDING FOR EACH SIDE (in figure coordinates, e.g., 0.01 = 1% of figure dimension)
    # Adjust these values to shift the border relative to the plot content:
    custom_padding = {
        'left': 0.0002,   # Increase for wider gap on the left
        'bottom': 0.03, # Decrease for tighter gap on the bottom
        'right': 0.0002,  # Increase for wider gap on the right
        'top': 0.00001     # Decrease for tighter gap on the top
    }
    
    # 3. CALCULATE NEW RECTANGLE POSITION AND SIZE
    
    # New X start position (original X start minus left padding)
    x_start = bbox.x0 - custom_padding['left']
    
    # New Y start position (original Y start minus bottom padding)
    y_start = bbox.y0 - custom_padding['bottom']
    
    # New Width (original width + left padding + right padding)
    new_width = (bbox.x1 - bbox.x0) + custom_padding['left'] + custom_padding['right']
    
    # New Height (original height + bottom padding + top padding)
    new_height = (bbox.y1 - bbox.y0) + custom_padding['bottom'] + custom_padding['top']
    
    # Create the border rectangle
    border_rect = patches.Rectangle(
        (x_start, y_start), 
        new_width, 
        new_height, 
        facecolor='none', 
        edgecolor='black', 
        linewidth=LINE_THICKNESS, 
        transform=fig_boxes.transFigure, 
        clip_on=False
    )
    
    # Add the border to the figure
    fig_boxes.patches.append(border_rect)
    
    return fig_boxes

# Chart 2: CREASE BEEHIVE
def create_crease_beehive(df_in, delivery_type):
    if df_in.empty:
        fig, ax = plt.subplots(figsize=(7, 5)); 
        ax.text(0.5, 0.5, "No data for Analysis", ha='center', va='center', fontsize=12); 
        ax.axis('off'); 
        return fig

    # --- Data Filtering ---
    wickets = df_in[df_in["Wicket"] == True]
    non_wickets_all = df_in[df_in["Wicket"] == False]
    boundaries = non_wickets_all[(non_wickets_all["Runs"] == 4) | (non_wickets_all["Runs"] == 6)]
    regular_balls = non_wickets_all[(non_wickets_all["Runs"] != 4) & (non_wickets_all["Runs"] != 6)]
    
    # --- Lateral Zone Data Prep (Chart 2b) ---
    df_lateral = df_in.copy()
    is_rhb = df_in["IsBatsmanRightHanded"].iloc[0] if not df_in.empty and "IsBatsmanRightHanded" in df_in.columns else True

    def assign_lateral_zone(row):
        y = row["CreaseY"]
        if row["IsBatsmanRightHanded"] == True:
            if y > 0.18: return "LEG"
            elif y >= -0.18: return "STUMPS"
            elif y > -0.65: return "OUTSIDE OFF"
            else: return "WAY OUTSIDE OFF"
        else: # Left-Handed
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
    
    # 2. Define standard zone order (RHB: Left to Right == WOO to LEG)
    ordered_zones = ["WAY OUTSIDE OFF", "OUTSIDE OFF", "STUMPS", "LEG"]
    summary = summary.reindex(ordered_zones).fillna(0)
    summary["Avg Runs/Wicket"] = summary.apply(lambda row: row["Runs"] / row["Wickets"] if row["Wickets"] > 0 else np.nan, axis=1)
    summary["SR"] = summary.apply(lambda row: (row["Runs"] / row["Balls"]) * 100 if row["Balls"] > 0 else np.nan, axis=1)

    # 3. HANDEDNESS AWARE REVERSAL: Reverse order for LHB
    if not is_rhb:
        # Reverses the DataFrame for LHB (LEG, STUMPS, OUTSIDE OFF, WAY OUTSIDE OFF)
        summary = summary.iloc[::-1]

    # -----------------------------------------------------------
    # --- 1. SETUP SUBPLOTS (Increased Figure Width) ---
    # Increased width from 7 to 8 for a wider Beehive chart relative to height
    fig = plt.figure(figsize=(7, 5)) 
    gs = fig.add_gridspec(2, 1, height_ratios=[4, 1], hspace=0.005) 
    ax_bh = fig.add_subplot(gs[0, 0])      # Top subplot (Beehive)
    ax_boxes = fig.add_subplot(gs[1, 0])   # Bottom subplot (Lateral Boxes)
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
    ## --- 3. CHART 2b: LATERAL PERFORMANCE BOXES (ax_boxes) ---
    ## --- CHART 2b: LATERAL PERFORMANCE BOXES (ax_boxes) ---
    num_regions = len(ordered_zones)
    box_width = 1 / num_regions
    box_height = 0.4 
    left = 0
    
    # 4. COLOR NORMALIZATION BY STRIKE RATE
    sr_values = summary["SR"].replace([np.inf, -np.inf], np.nan)
    sr_max = sr_values.max() if sr_values.max() > 0 else 200
    norm = mcolors.Normalize(vmin=0, vmax=sr_max)
    cmap = cm.get_cmap('Wistia')

    for index, row in summary.iterrows():
        sr = row["SR"]
        wkts = int(row["Wickets"])
    
        if np.isnan(sr) or sr == np.inf:
            color = 'white'
            text_color = 'black'
            sr_display = '0'
        else:
            color = cmap(norm(sr))
            sr_display = f"{sr:.0f}"
            
            # Contrast logic for text
            r, g, b, a = color
            luminosity = 0.2126 * r + 0.7152 * g + 0.0722 * b
            text_color = 'white' if luminosity < 0.5 else 'black'
        
        ax_boxes.add_patch(patches.Rectangle((left, 0), box_width, box_height, edgecolor="black", facecolor=color, linewidth=1))
    
        # Zone Name
        ax_boxes.text(left + box_width / 2, box_height + 0.1, index, ha='center', va='bottom', fontsize=7, color='black')
    
        # 5. UPDATED TEXT: Wickets and Strike Rate
        label_wkts_sr = f"{wkts}W - SR {sr_display}"
        ax_boxes.text(left + box_width / 2, box_height * 0.5, label_wkts_sr, ha='center', va='center', fontsize=9, fontweight='bold', color=text_color)
    
        left += box_width

    # Formatting and Border logic...
    ax_boxes.set_xlim(0, 1); ax_boxes.set_ylim(0, box_height + 0.3); ax_boxes.axis('off')
    plt.tight_layout(pad=0.2)
    
    # Define Padding Value (in figure coordinates)
    PADDING = 0.008

    # 2. Get the bounding box of the two subplots in Figure coordinates
    bh_bbox = ax_bh.get_position()
    box_bbox = ax_boxes.get_position()
    
    # Determine the total bounds (original compact bounds)
    x0_orig = min(bh_bbox.x0, box_bbox.x0)
    y0_orig = box_bbox.y0
    x1_orig = max(bh_bbox.x1, box_bbox.x1)
    y1_orig = bh_bbox.y1
    
    # 3. Apply Padding
    x0_pad = x0_orig - PADDING
    y0_pad = y0_orig - PADDING
    
    # Width and Height must be increased by 2*PADDING (one for each side)
    width_pad = (x1_orig - x0_orig) + (2 * PADDING)
    height_pad = (y1_orig - y0_orig) + (2 * PADDING)

    # 4. Draw the custom Rectangle using the padded bounds
    border_rect = patches.Rectangle(
        (x0_pad, y0_pad), 
        width_pad, 
        height_pad,  
        facecolor='none', 
        edgecolor='black', 
        linewidth=0.5, 
        transform=fig.transFigure, # Use the figure's coordinate system
        clip_on=False
    )

    fig.patches.append(border_rect)

    return fig


# --- CHART 3: PITCHMAP ---
# --- Helper function for Pitch Bins (Centralized) ---
def get_pitch_bins(delivery_type):
    if delivery_type == "Seam":
        # Seam Bins: 1.2-6: Full, 6-8 Length, 8-10 Short, 10-15 Bouncer
        return {
            "Full Toss": [-2, 0.9],
            "Yorker": [0.9,2.8],
            "Slot": [2.8, 5.9],
            "Length": [5.9, 8.6],
            "Short": [8.6, 15]
        }
    elif delivery_type == "Spin":
        # Spin Bins: 1.22-2.22: OP, 2.22-4: full, 4-6: Good, 6-15: short
        return  {
         "OP": [-2, 2.8],
        "Full": [2.8, 4.4],
        "Good": [4.4, 6.2],
        "Short": [6.2, 15.0]
    }
    return {} # Default

# --- CHART 3: PITCH MAP (BOUNCE LOCATION) ---
def create_pitch_map(df_in, delivery_type):
    if df_in.empty:
        # Create an empty figure with a text note if data is missing
        fig, ax = plt.subplots(figsize=(4,6))
        ax.text(0.5, 0.5, f"No data for Pitch Map ({delivery_type})", ha='center', va='center', fontsize=12)
        ax.axis('off')
        return fig

    # --- Data Filtering ---
    pitch_wickets = df_in[df_in["Wicket"] == True]
    pitch_non_wickets = df_in[df_in["Wicket"] == False]
    
    # --- Chart Setup ---
    fig, ax = plt.subplots(figsize=(4,6))
    ax.set_facecolor('white')
    fig.patch.set_facecolor('white')

    # --- Pitch Bins & Full Toss Adjustment ---
    PITCH_BINS = get_pitch_bins(delivery_type)
    
    # --- 1. Add Zone Lines & Labels (Horizontal Lines) ---
    
    # Determine boundary Y values to draw lines (excluding the start of the lowest bin)
    # The 'Full Toss' bin is assumed to start at -4.0, which is the bottom plot limit.
    boundary_y_values = sorted([v[0] for v in PITCH_BINS.values() if v[0] > -4.0], reverse=True)

    for y_val in boundary_y_values:
        # ax.axhline is the Matplotlib equivalent of fig_pitch.add_hline
        ax.axhline(y=y_val, color="lightgrey", linewidth=1.0, linestyle="--")

    # Add zone labels (equivalent to fig_pitch.add_annotation)
    for Length, bounds in PITCH_BINS.items():
        mid_y = (bounds[0] + bounds[1]) / 2
        # Use ax.text for annotation, positioned on the far left (x=-1.45)
        ax.text(
            x=-1.45, 
            y=mid_y, 
            s=Length.upper(), 
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
        s=60, # Matplotlib size equivalent to Plotly size=10
        c='#D3D3D3', 
        edgecolor='white', 
        linewidths=1.0, 
        alpha=0.9,
        label="No Wicket"
    )

    # Wickets (red)
    ax.scatter(
        pitch_wickets["BounceY"], pitch_wickets["BounceX"], 
        s=90, # Matplotlib size equivalent to Plotly size=12
        c='red', 
        edgecolor='white', 
        linewidths=1.0, 
        alpha=0.95,
        label="Wicket"
    )
    # --- 2. Add Stump lines (Vertical Lines) ---
    # ax.axvline is the Matplotlib equivalent of fig_pitch.add_vline
    ax.axvline(x=-0.18, color="#777777", linestyle="--", linewidth=1)
    ax.axvline(x=0.18, color="#777777", linestyle="--", linewidth=1)
    ax.axvline(x=0, color="#777777", linestyle="--", linewidth=0.8)
    # --- 4. Layout (Axis and Spines) ---
    
    # Set axis limits
    ax.set_xlim([-1.5, 1.5])
    # Note: Matplotlib typically plots y-axis increasing upwards, but here we set 
    # the range from [16.0, -4.0] to reverse the axis and match the Plotly visual 
    # where lower values (closer to batter) are at the bottom.
    ax.set_ylim([16.0, -4.0])

    # Hide all axis elements (equivalent to visible=False)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.grid(False)
    
    # Hide axis spines (plot border)
    # 1. Set line style for all spines you want visible
    spine_color = 'black'
    spine_width = 0.5
    for spine_name in ['left', 'top', 'bottom','right']:
        ax.spines[spine_name].set_visible(True)
        ax.spines[spine_name].set_color(spine_color)
        ax.spines[spine_name].set_linewidth(spine_width)
        
    plt.tight_layout()
    
    return fig

# --- CHART 3b: PITCH Length RUN % (EQUAL SIZED BOXES) ---
def create_pitch_Length_bars(df_in, delivery_type):
    """
    Generates a figure with three vertically stacked horizontal bar charts 
    for Batting Average, Strike Rate, and Dismissals by Pitch Length.
    """
    # Increased height to accommodate three stacked charts comfortably
    FIG_SIZE = (3, 4.7) 
    
    if df_in.empty:
        fig, ax = plt.subplots(figsize=FIG_SIZE)
        ax.text(0.5, 0.5, "No Data for Pitch Length Comparison", ha='center', va='center', fontsize=12)
        ax.axis('off')
        return fig

    # Get the pitch bins and define order
    def get_pitch_bins(delivery_type):
        if delivery_type == "Seam":
            # Seam Bins: 1.2-6: Full, 6-8 Length, 8-10 Short, 10-15 Bouncer
            return {
                "Full Toss": [-2, 0.9],
                "Yorker": [0.9,2.8],
                 "Slot": [2.8, 5.9],
                "Length": [5.9, 8.6],
                "Short": [8.6, 15]
            }
        elif delivery_type == "Spin":
            # Spin Bins: 1.22-2.22: OP, 2.22-4: full, 4-6: Good, 6-15: short
            return  {
             "OP": [-2, 2.8],
            "Full": [2.8, 4.4],
            "Good": [4.4, 6.2],
            "Short": [6.2, 15.0]
        }
        return {}
    PITCH_BINS_DICT = get_pitch_bins(delivery_type)
    
    if delivery_type == "Seam":
        ordered_keys = ["Full Toss","Yorker", "Slot", "Length", "Short" ]
    elif delivery_type == "Spin":
        ordered_keys = ["OP", "Full" , "Good", "Short"]
    else:
        fig, ax = plt.subplots(figsize=FIG_SIZE)
        ax.text(0.5, 0.5, "Invalid Delivery Type", ha='center', va='center', fontsize=12)
        ax.axis('off')
        return fig

    # 1. Data Preparation
    def assign_pitch_Length(x):
        for Length, bounds in PITCH_BINS_DICT.items():
            if bounds[0] <= x < bounds[1]: return Length
        return None

    df_pitch = df_in.copy()
    df_pitch["PitchLength"] = df_pitch["BounceX"].apply(assign_pitch_Length)
    
    # Aggregate data
    df_summary = df_pitch.groupby("PitchLength").agg(
    Runs=("Runs", "sum"),  
    Wickets=("Wicket", lambda x: (x == True).sum()), 
    Balls=("Wicket", "count"),
    Boundaries=("Runs", lambda x: ((x == 4) | (x == 6)).sum())
    ).reset_index().set_index("PitchLength").reindex(ordered_keys).fillna(0)

    # Calculate Metrics
    # Strike Rate
    df_summary["StrikeRate"] = df_summary.apply(
    lambda row: (row["Runs"] / row["Balls"]) * 100 if row["Balls"] > 0 else 0, axis=1
    ) 

    # Average (Using np.nan for 0 wickets is often better for color mapping)
    df_summary["Average"] = df_summary.apply(
    lambda row: row["Runs"] / row["Wickets"] if row["Wickets"] > 0 else 0, axis=1
    )

    # Boundary Percentage
    df_summary["Bpct"] = df_summary.apply(
    lambda row: (row["Boundaries"] / row["Balls"]) * 100 if row["Balls"] > 0 else 0, axis=1
    )
    # Categories for plotting (reversed for barh)
    categories = df_summary.index.tolist()[::-1]
    
    # 2. Chart Setup (3 Rows, 1 Column)
    # sharex=False is default, sharey=True forces Y-axis to be the same, 
    # which is what we want for aligning the bar labels.
    fig, axes = plt.subplots(3, 1, figsize=FIG_SIZE, sharey=True) 
    # Adjust space between charts to minimize it vertically
    plt.subplots_adjust(hspace=10) 

    metrics = ["StrikeRate", "Average","Bpct"]
    titles = ["Batting Strike Rate", "Batting Average", "Boundry %"]
    colors = ['#ff5000', '#ff5000', '#ff5000']
                                
    # Define limits for each chart to ensure proper scaling
    max_sr = df_summary["StrikeRate"].max() * 1.1 if df_summary["StrikeRate"].max() > 0 else 300
    max_avg = df_summary["Average"].max() * 1.1 if df_summary["Average"].max() > 0 else 100
    max_Bpct = df_summary["Bpct"].max() * 1.1 if df_summary["Bpct"].max() > 0 else 100

    xlim_limits = {
        "Average": (0, max_avg),
        "StrikeRate": (0, max_sr),
        "Bpct": (0, max_Bpct)
    }

    # --- Plotting Loop ---
    for i, ax in enumerate(axes):
        metric = metrics[i]
        title = titles[i]
        
        # Data values (reversed to align with category order)
        values = df_summary[metric].values[::-1] 
        
        # Define x limits
        ax.set_xlim(xlim_limits[metric])
        
        # Horizontal Bar Chart
        ax.barh(categories, values, height=0.49, color='#ff5000', zorder=3, alpha=0.9)
        
        # --- Annotations ---
        for j, (cat, val) in enumerate(zip(categories, values)):
            # Format value
            if metric == "Wickets":
                label = f"{int(val)}"
            else:
                label = f"{val:.2f}"
            
            # Place label slightly to the right of the bar tip
            ax.text(val, j, label, 
                    ha='left', va='center', 
                    fontsize=9,fontweight = 'bold', color='black',
                    bbox=dict(facecolor='White', alpha=0.8, edgecolor='none', pad=2),
                    zorder=4)

        # --- Formatting ---
        ax.set_title(title, fontsize=10,fontweight = 'bold', pad=0, loc='left')
        ax.set_facecolor('white')

        # Set Ticks and Spines
        ax.tick_params(axis='x', labelsize=8)
        ax.tick_params(axis='y', length=0) # Hide y ticks

        # Set Y-axis labels only on the bottom-most chart (ax[2])
        # This keeps the labels at the bottom, mimicking the style in your image
        if i == 2:
            ax.set_yticks(np.arange(len(categories)), labels=[c.upper() for c in categories], fontsize=8)
        else:
             # Remove y-tick labels for the top two charts
            ax.set_yticks(np.arange(len(categories)), labels=[''] * len(categories))
            
        ax.xaxis.grid(False) 
        ax.yaxis.grid(False)

        # Hide x labels/ticks
        ax.set_xticks([]) 
        ax.set_xlim(0, xlim_limits[metric][1]) 
        
        # --- Custom Spines: Right, Top, Bottom ---
        spine_color = 'lightgray'
        spine_width = 1.0 
        for spine_name in ['left', 'right', 'top', 'bottom']:
            ax.spines[spine_name].set_visible(True)
            ax.spines[spine_name].set_color(spine_color)
            ax.spines[spine_name].set_linewidth(spine_width)
    plt.tight_layout(pad=0.5)
    return fig
    
  
# --- CHART 4a: INTERCEPTION SIDE-ON --- (Wide View)
# --- Helper function for Interception Bins ---

def get_interception_bins():
    """Defines the bins for the Crease Width Split chart."""
    return {
        "0m-1m": [0, 1],
        "1m-2m": [1, 2],
        "2m-3m": [2, 3],
        "3m+": [3, 100]  # Assuming max possible value is < 100
    }

def create_interception_side_on(df_in, delivery_type):
    # Define Figure Size (slightly narrower and taller for the vertical stack)
    FIG_WIDTH = 7
    FIG_HEIGHT = 5
    FIG_SIZE = (FIG_WIDTH, FIG_HEIGHT)

    if df_in.empty or df_in["InterceptionX"].isnull().all():
        fig, ax = plt.subplots(figsize=FIG_SIZE)
        ax.text(0.5, 0.5, "No Data for Combined Interception Analysis", ha='center', va='center', fontsize=12)
        ax.axis('off')
        return fig

    # --- SETUP GRID FOR TWO ROWS ---
    # Top: Scatter Plot (Larger) | Bottom: Bar Chart (Smaller)
    fig = plt.figure(figsize=FIG_SIZE)
    # Ratio: 80% for scatter plot, 20% for bar chart
    gs = fig.add_gridspec(2, 1, height_ratios=[4, 1], hspace=0.1) 
    
    ax_scatter = fig.add_subplot(gs[0, 0])
    ax_bar = fig.add_subplot(gs[1, 0])
    
    fig.patch.set_facecolor('white')

    # ----------------------------------------------------------------------
    ## --- PART 1: CHART 4a - INTERCEPTION SIDE-ON SCATTER (ax_scatter) ---
    # ----------------------------------------------------------------------
    df_interception = df_in[df_in["InterceptionX"] > -999].copy()    
    df_interception["ColorType"] = "Other"
    df_interception.loc[df_interception["Wicket"] == True, "ColorType"] = "Wicket"
    df_interception.loc[df_interception["Runs"].isin([4, 6]), "ColorType"] = "Boundary"
    # Define color_map inline as it's needed for the loop
    color_map = {"Wicket": "red", "Boundary": "royalblue", "Other": "white"}
    
    # 1. Plot Data (Layered for correct border visibility)
    
    # Plot "Other" (White with Grey Border)
    df_other = df_interception[df_interception["ColorType"] == "Other"]
    # === USING PROVIDED LOGIC: PLOT (InterceptionX + 10) on X-axis ===
    ax_scatter.scatter(
        df_other["InterceptionX"] + 10, df_other["InterceptionZ"], 
        color='#D3D3D3', edgecolors='white', linewidths=0.3, s=40, label="Other"
    )
    
    # Plot "Wicket" and "Boundary" (Solid colors)
    for ctype in ["Boundary", "Wicket"]:
        df_slice = df_interception[df_interception["ColorType"] == ctype]
        # === USING PROVIDED LOGIC: PLOT (InterceptionX + 10) on X-axis ===
        ax_scatter.scatter(
            df_slice["InterceptionX"] + 10, df_slice["InterceptionZ"], 
            color=color_map[ctype],edgecolors='white', linewidths=0.3, s=60, label=ctype
        )

    # 2. Draw Vertical Dashed Lines with Labels (FIXED LINES: 0.0, 1.25, 2.0, 3.0)
    line_specs = {
        0.0: "Stumps",
        1.250: "Crease",
        2.000: "2m",     
        3.000: "3m" 
    }
    
    for x_val, label in line_specs.items():
        ax_scatter.axvline(x=x_val, color='lightgrey', linestyle='--', linewidth=0.8, alpha=0.7)     
        ax_scatter.text(x_val, 1.45, label.split(':')[-1].strip(), ha='center', va='center', fontsize=8, color='grey', bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1))
        
    ax_scatter.axhline(y=0.78, color="grey", linestyle="-", linewidth=0.5)
    # --- Annotation ---
    ax_scatter.text(0.1, 0.78, "Stumps Height", ha='left', va='bottom', fontsize=7, color="grey", transform=ax_scatter.transData)
    
    # Set Y limit as fixed
    y_limit = 1.5
    
    # Set X limit based on delivery type
    if delivery_type == "Seam":
        x_limit_max = 3.4
    elif delivery_type == "Spin":
        x_limit_max = 4.4
    else:
        # Fallback to the original seam limit if type is unknown
        x_limit_max = 3.4 
        
    x_limit_min = -0.2
    
    ax_scatter.set_xlim(x_limit_min, x_limit_max) 
    ax_scatter.set_ylim(0, y_limit) 
    # ... (Rest of the styling remains the same)
    ax_scatter.tick_params(axis='y', which='both', labelleft=False, left=False); ax_scatter.tick_params(axis='x', which='both', labelbottom=False, bottom=False)
    ax_scatter.spines['right'].set_visible(False)
    ax_scatter.spines['top'].set_visible(False)
    ax_scatter.spines['left'].set_visible(False)
    ax_scatter.spines['bottom'].set_visible(False)

    # ----------------------------------------------------------------------
    ## --- PART 2: CHART 4b - CREASE WIDTH SPLIT BARS (ax_bar) ---
    # ----------------------------------------------------------------------
    
    # 1. Data Preparation
    INTERCEPTION_BINS = get_interception_bins()
    ordered_keys = ["0m-1m", "1m-2m", "2m-3m", "3m+"]  # Order: Close to Wide
    COLORMAP = 'Wistia'
    
    def assign_crease_width(x):
        for width, bounds in INTERCEPTION_BINS.items():
            if bounds[0] <= x < bounds[1]: return width
        return None

    df_crease = df_in.copy()
    df_crease["CreaseWidth"] = (df_crease["InterceptionX"] + 10).apply(assign_crease_width)
    
    df_summary = df_crease.groupby("CreaseWidth").agg(
        Runs=("Runs", "sum"), 
        Wickets=("Wicket", lambda x: (x == True).sum()), 
        Balls=("Wicket", "count")
    ).reset_index().set_index("CreaseWidth").reindex(ordered_keys).fillna(0)
    
    # NEW: Calculate Strike Rate (SR) instead of Average
    df_summary["SR"] = df_summary.apply(
        lambda row: (row["Runs"] / row["Balls"]) * 100 if row["Balls"] > 0 else np.nan, axis=1
    )
    
    # 2. Plotting Equal Boxes
    num_boxes = len(ordered_keys)
    box_width = 1.0 / num_boxes 
    left = 0.0

    # Normalization changed to Strike Rate
    max_sr_val = df_summary["SR"].replace([np.inf, -np.inf], np.nan).max()
    max_sr = max_sr_val if max_sr_val > 0 else 200 # Default max for scaling
    
    norm = mcolors.Normalize(vmin=0, vmax=max_sr)
    cmap = cm.get_cmap(COLORMAP)
    
    for index, row in df_summary.iterrows():
        wickets = row["Wickets"]
        sr = row["SR"] 
        
        # --- CONDITIONAL STYLING LOGIC ---
        if np.isnan(sr) or sr == np.inf:
            sr_display = '0'
            color = 'white'
            text_color = 'black'
        else:
            sr_display = f"{sr:.0f}"
            color = cmap(norm(sr)) 
            
            # Contrast logic for text
            r, g, b, a = color
            luminosity = 0.2126 * r + 0.7152 * g + 0.0722 * b
            text_color = 'white' if luminosity < 0.5 else 'black'
            
        # Draw the box  
        ax_bar.barh(
            y=0.5,             
            width=box_width,
            height=0.6,          
            left=left,         
            color=color,
            edgecolor='black',
            linewidth=0.4
        )
        
        # --- UPDATED TEXT: Wickets and Strike Rate ---
        label_text = f"{int(wickets)}W - SR {sr_display}"
        
        center_x = left + box_width / 2
        center_y = 0.5
        
        ax_bar.text(
            center_x, center_y, 
            label_text,
            ha='center', va='center', 
            fontsize=9, 
            fontweight = 'bold',
            color=text_color
        )
        
        # Crease Width Label (Top of the box)
        ax_bar.text(center_x, 0.8, index, ha='center', va='bottom', fontsize=9, color='black')

        left += box_width

    # 3. Styling for Bar Chart
    ax_bar.set_xlim(0, 1)
    ax_bar.set_ylim(0, 1) 
    ax_bar.axis('off')


    # ----------------------------------------------------------------------
    ## --- PART 3: DRAW SINGLE COMPACT BORDER ---
    # ----------------------------------------------------------------------
    
    plt.tight_layout(pad=0.2) 
    
    PADDING = 0.005 

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


    
# --- CHART 5: INTERCEPTION FRONT-ON --- (Distance vs Width)
def create_interception_front_on(df_in, delivery_type):
    df_interception = df_in[df_in["InterceptionX"] > -999].copy()
    if df_interception.empty:
        fig, ax = plt.subplots(figsize=(4, 6)); ax.text(0.5, 0.5, "No Data", ha='center', va='center'); ax.axis('off'); return fig
        
    df_interception["ColorType"] = "Other"
    df_interception.loc[df_interception["Wicket"] == True, "ColorType"] = "Wicket"
    df_interception.loc[df_interception["Runs"].isin([4, 6]), "ColorType"] = "Boundary"
    # Define color_map inline as it's needed for the loop
    color_map = {"Wicket": "red", "Boundary": "royalblue", "Other": "white"}
    
    fig_8, ax_8 = plt.subplots(figsize=(4, 6), subplot_kw={'xticks': [], 'yticks': []}) 

    # 1. Plot Data
    # Plot "Other" (White with Grey Border)
    df_other = df_interception[df_interception["ColorType"] == "Other"]
    # === USING PROVIDED LOGIC: PLOT (InterceptionX + 10) on Y-axis (Distance) ===
    ax_8.scatter(
        df_other["InterceptionY"], df_other["InterceptionX"] + 10, 
        color='#D3D3D3', edgecolors='white', linewidths=0.5, s=70, label="Other"
    ) 
    
    # Plot "Wicket" and "Boundary" (Solid colors)
    for ctype in ["Boundary", "Wicket"]:
        df_slice = df_interception[df_interception["ColorType"] == ctype]
        # === USING PROVIDED LOGIC: PLOT (InterceptionX + 10) on Y-axis (Distance) ===
        ax_8.scatter(
            df_slice["InterceptionY"], df_slice["InterceptionX"] + 10, 
            color=color_map[ctype],edgecolors='white', s=90, label=ctype
        ) 

    # 2. Draw Horizontal Dashed Lines with Labels (FIXED LINES: 0.0, 1.25)
    line_specs = {
        0.00: "Stumps",
        1.25: "Crease"        
    }
    for y_val, label in line_specs.items():
        ax_8.axhline(y=y_val, color='lightgrey', linestyle='--', linewidth=0.8, alpha=0.7)
        ax_8.text(-0.95, y_val, label.split(':')[-1].strip(), ha='left', va='center', fontsize=12, color='grey', bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1))

    # Boundary lines (FIXED LINES: -0.18, 0.18)
    ax_8.axvline(x=-0.18, color='grey', linestyle='--', linewidth=1, alpha=0.7)
    ax_8.axvline(x= 0.18, color='grey', linestyle='--', linewidth=1, alpha=0.7)
    ax_8.axvline(x= 0, color='grey', linestyle='--', linewidth=1, alpha=0.7)
    
    # 3. Set Axes Limits and Labels (FIXED LIMITS: Y-axis -0.2 to 3.5)
    ax_8.set_xlim(-1, 1); ax_8.set_ylim(-0.2, 3.5); ax_8.invert_yaxis()      
    ax_8.tick_params(axis='y', which='both', labelleft=False, left=False); ax_8.tick_params(axis='x', which='both', labelbottom=False, bottom=False)
     # Hide axis spines (plot border)
    # 1. Set line style for all spines you want visible
    spine_color = 'black'
    spine_width = 0.5
    
    for spine_name in ['left', 'top', 'bottom','right']:
        ax_8.spines[spine_name].set_visible(True)
        ax_8.spines[spine_name].set_color(spine_color)
        ax_8.spines[spine_name].set_linewidth(spine_width)
    plt.tight_layout(pad=0.5)
    return fig_8
    

# Chart 6 Scoring wagon wheel
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

# --- Main Combined Function ---
def create_wagon_wheel(df_in, delivery_type):
    FIG_WIDTH = 11.0
    FIG_HEIGHT = 16 # Adjusted height for the vertical stack
    FIG_SIZE = (FIG_WIDTH, FIG_HEIGHT)

    if df_in.empty:
        fig, ax = plt.subplots(figsize=FIG_SIZE)
        ax.text(0.5, 0.5, "No Data for Combined Scoring Analysis", ha='center', va='center', fontsize=12)
        ax.axis('off')
        return fig

    # --- SETUP GRID FOR TWO ROWS ---
    # Top: Wagon Wheel (Larger) | Bottom: Left/Right Split (Smaller)
    fig = plt.figure(figsize=FIG_SIZE)
    # Ratio: 75% for Wagon Wheel, 25% for Left/Right Split
    gs = fig.add_gridspec(2, 1, height_ratios=[1, 1], hspace=0.1) 
    
    ax_wagon = fig.add_subplot(gs[0, 0])
    ax_split = fig.add_subplot(gs[1, 0])
    
    fig.patch.set_facecolor('white')

    # ----------------------------------------------------------------------
    ## --- PART 1: CHART 6 - SCORING WAGON WHEEL (ax_wagon) ---
    # ----------------------------------------------------------------------
    wagon_summary = pd.DataFrame() 
    try:
        df_wagon = df_in.copy()
        df_wagon["ScoringWagon"] = df_wagon.apply(calculate_scoring_wagon, axis=1)
        df_wagon["FixedAngle"] = df_wagon["ScoringWagon"].apply(calculate_scoring_angle)
        
        summary_with_shots = df_wagon.groupby("ScoringWagon").agg(TotalRuns=("Runs", "sum"), FixedAngle=("FixedAngle", 'first')).reset_index().dropna(subset=["ScoringWagon"])
        
        handedness_mode = df_in["IsBatsmanRightHanded"].dropna().mode()
        is_right_handed = handedness_mode.iloc[0] if not handedness_mode.empty else True
        
        if is_right_handed:
            # RHB areas start from Fine Leg (top left) and go clockwise
            all_areas = ["FINE LEG", "SQUARE LEG", "LONG ON", "LONG OFF", "COVER", "THIRD MAN"] 
        else:
            # LHB areas start from Third Man (top left) and go clockwise
            all_areas = ["THIRD MAN", "COVER", "LONG OFF", "LONG ON", "SQUARE LEG", "FINE LEG"]
            
        template_df = pd.DataFrame({"ScoringWagon": all_areas, "FixedAngle": [calculate_scoring_angle(area) for area in all_areas]})

        wagon_summary = template_df.merge(summary_with_shots.drop(columns=["FixedAngle"], errors='ignore'), on="ScoringWagon", how="left").fillna(0) 
        wagon_summary["ScoringWagon"] = pd.Categorical(wagon_summary["ScoringWagon"], categories=all_areas, ordered=True)
        wagon_summary = wagon_summary.sort_values("ScoringWagon")
        
        total_runs = wagon_summary["TotalRuns"].sum()
        wagon_summary["RunPercentage"] = (wagon_summary["TotalRuns"] / total_runs) * 100 if total_runs > 0 else 0 
        
        wagon_summary["FixedAngle"] = pd.to_numeric(wagon_summary["FixedAngle"], errors='coerce').fillna(0).astype(int)
    
    except Exception as e:
        ax_wagon.text(0.5, 0.5, f"Wagon Wheel Calculation Error: {e}", ha='center', va='center', fontsize=8)
        ax_wagon.axis('off')
        return fig # Return early if data processing fails

    
    # --- Data Extraction and CRITICAL Validation ---
    angles = wagon_summary["FixedAngle"].tolist()
    run_percentages = wagon_summary["RunPercentage"].tolist() 
    labels = wagon_summary["ScoringWagon"].tolist()
    
    if not angles or all(a == 0 for a in angles):
        ax_wagon.text(0.5, 0.5, "Insufficient Wagon Wheel Data", ha='center', va='center', fontsize=8) 
        ax_wagon.axis('off')
        # Skip plotting the pie chart, but allow the rest of the combined chart to proceed
    else:
        # --- Color Logic (Top 1 Rank Only) ---
        wagon_summary['Rank'] = wagon_summary['RunPercentage'].rank(method='dense', ascending=False)
        COLOR_HIGH = '#ff5000'
        COLOR_DEFAULT = 'white'

        colors = []
        for index, row in wagon_summary.iterrows():
            current_rank = row['Rank']
            if row['RunPercentage'] == 0:
                colors.append(COLOR_DEFAULT)
                continue
            if current_rank == 1:
                colors.append(COLOR_HIGH)
            else:
                colors.append(COLOR_DEFAULT)

        # --- Plotting Call ---
        pie_output = ax_wagon.pie(
            angles, 
            colors=colors, 
            wedgeprops={"width": 1, "edgecolor": "black"}, 
            startangle=90, 
            counterclock=False, 
            autopct='%.0f', 
            pctdistance=0.6 # Keeps percentage label centered in radius
        )
        ax_wagon.set_title("RUNS DISTRIBUTION (%)", fontsize=20, fontweight='bold', pad=20)
        
        if len(pie_output) == 3:
            wedges, texts, autotexts = pie_output
        elif len(pie_output) == 2:
            wedges, texts = pie_output
            autotexts = [] # Assign an empty list if autotexts are missing
        else:
            # Handle unexpected plot output
            ax_wagon.text(0.5, 0.5, "Wagon Wheel Plotting Error", ha='center', va='center', fontsize=8)
            ax_wagon.axis('off')
            return fig
        
        # === CRITICAL FIX: CENTERING PERCENTAGE LABELS AND STYLING ===
        for i, autotext in enumerate(autotexts):
            if i >= len(run_percentages): break
                
            percent = run_percentages[i]
            
            # 1. Set the actual percentage text
            if percent > 0:
                autotext.set_text(f'{percent:.0f}%')
                
                # 💥 FIX: Ensure percentage text is centered in the slice (horizontally and vertically)
                autotext.set_horizontalalignment('center')
                autotext.set_verticalalignment('center')
                
                # Add a white stroke (outline) for text visibility
            else:
                autotext.set_text('')
                
            # 2. Set text color based on background color for contrast
            color_rgb = mcolors.to_rgb(colors[i])
            luminosity = 0.2126 * color_rgb[0] + 0.7152 * color_rgb[1] + 0.0722 * color_rgb[2]
            
            autotext.set_color('white' if luminosity < 0.5 and colors[i] == COLOR_HIGH else 'black') 
            autotext.set_fontsize(26)
            autotext.set_fontweight('bold')
        
        ax_wagon.axis('equal'); 

# ----------------------------------------------------------------------
    ## --- PART 2: CHART 7 - STRIKE RATE WAGON WHEEL (ax_split) ---
    # ----------------------------------------------------------------------
    sr_wagon_summary = pd.DataFrame()
    try:
        # Use the same data prepared for the previous wagon wheel
        # Calculate Runs AND Balls (count of deliveries) per area
        summary_sr = df_wagon.groupby("ScoringWagon").agg(
            TotalRuns=("Runs", "sum"), 
            TotalBalls=("Runs", "count"),
            FixedAngle=("FixedAngle", 'first')
        ).reset_index().dropna(subset=["ScoringWagon"])
        
        # Merge with template to ensure all areas are present
        sr_wagon_summary = template_df.merge(summary_sr.drop(columns=["FixedAngle"], errors='ignore'), on="ScoringWagon", how="left").fillna(0)
        sr_wagon_summary["ScoringWagon"] = pd.Categorical(sr_wagon_summary["ScoringWagon"], categories=all_areas, ordered=True)
        sr_wagon_summary = sr_wagon_summary.sort_values("ScoringWagon")
        
        # Calculate Strike Rate (Text format, not %)
        sr_wagon_summary["SR"] = sr_wagon_summary.apply(
            lambda row: (row["TotalRuns"] / row["TotalBalls"]) * 100 if row["TotalBalls"] > 0 else 0, axis=1
        )
        
        # Identify Rank for Coloring (Highest SR gets the color)
        sr_wagon_summary['RankSR'] = sr_wagon_summary['SR'].rank(method='dense', ascending=False)
        
    except Exception as e:
        ax_split.text(0.5, 0.5, f"SR Wagon Error: {e}", ha='center', va='center', fontsize=8)
        ax_split.axis('off')

    # --- Plotting the SR Wagon Wheel ---
    sr_angles = sr_wagon_summary["FixedAngle"].tolist()
    sr_values = sr_wagon_summary["SR"].tolist()
    
    if not sr_angles or all(a == 0 for a in sr_angles):
        ax_split.text(0.5, 0.5, "No SR Data", ha='center', va='center', fontsize=14)
        ax_split.axis('off')
    else:
        # Define Colors (Highlight only the #1 Highest SR)
        sr_colors = [COLOR_HIGH if r == 1 and val > 0 else COLOR_DEFAULT for r, val in zip(sr_wagon_summary['RankSR'], sr_values)]

        # Plot Pie
        sr_pie = ax_split.pie(
            sr_angles, 
            colors=sr_colors, 
            wedgeprops={"width": 1, "edgecolor": "black", "linewidth": 0.5}, 
            startangle=90, 
            counterclock=False
        )
        
        # Add Strike Rate Text Labels
        # Pie returns (wedges, texts) or (wedges, texts, autotexts)
        # Since we aren't using autopct, we calculate label positions manually
        for i, wedge in enumerate(sr_pie[0]):
            sr_val = sr_values[i]
            if sr_val > 0:
                # Calculate mid-angle for text placement
                angle = (wedge.theta2 + wedge.theta1) / 2.
                x = 0.6 * np.cos(np.deg2rad(angle))
                y = 0.6 * np.sin(np.deg2rad(angle))
                
                # Contrast check
                color_rgb = mcolors.to_rgb(sr_colors[i])
                lum = 0.2126 * color_rgb[0] + 0.7152 * color_rgb[1] + 0.0722 * color_rgb[2]
                t_color = 'white' if lum < 0.5 and sr_colors[i] == COLOR_HIGH else 'black'
                
                ax_split.text(x, y, f"{sr_val:.0f}", ha='center', va='center', 
                             fontsize=26, fontweight='bold', color=t_color)
        ax_split.set_title("STRIKE RATE", fontsize=20, fontweight='bold', pad=0)
        ax_split.axis('equal')
    
  

# # --- CHART 9/10: DIRECTIONAL SPLIT (Side-by-Side Bars) ---
def create_directional_split(df_in, direction_col, chart_title, delivery_type):
    if df_in.empty:
        fig, ax = plt.subplots(figsize=(7, 12))
        ax.text(0.5, 0.5, "No Data for Directional Analysis", ha='center', va='center')
        ax.axis('off')
        return fig

    segments = [
        ("OVERALL", (0, 20)),
        ("POWERPLAY", (1, 6)),
        ("DEATH OVERS", (16, 20))
    ]
    
    fig, axes = plt.subplots(3, 1, figsize=(7, 12))
    fig.patch.set_facecolor('white')
    plt.subplots_adjust(hspace=0.6) 

    for i, (seg_title, (o_start, o_end)) in enumerate(segments):
        ax = axes[i]
        df_seg = df_in[(df_in['Over'] >= o_start) & (df_in['Over'] <= o_end)].copy()
        
        if df_seg.empty:
            ax.text(0.5, 0.5, f"No Data for {seg_title}", ha='center', va='center', fontsize=10)
            ax.axis('off')
            continue

        df_seg["Direction"] = np.where(df_seg[direction_col] < 0, "LEFT", "RIGHT")
        
        summary = df_seg.groupby("Direction").agg(
            Runs=("Runs", "sum"), 
            Balls=("Wicket", "count"),
            Boundaries=("Runs", lambda x: ((x == 4) | (x == 6)).sum()),
            Dots=("Runs", lambda x: (x == 0).sum())
        ).reset_index().set_index("Direction").reindex(["RIGHT", "LEFT"]).fillna(0)
        
        summary["SR"] = summary.apply(lambda r: (r["Runs"]/r["Balls"])*100 if r["Balls"] > 0 else 0, axis=1)
        summary["BPct"] = summary.apply(lambda r: (r["Boundaries"]/r["Balls"])*100 if r["Balls"] > 0 else 0, axis=1)
        summary["DotPct"] = summary.apply(lambda r: (r["Dots"]/r["Balls"])*100 if r["Balls"] > 0 else 0, axis=1)
        
        y_positions = [0, 1] 
        sr_values = [summary.loc["RIGHT", "SR"], -summary.loc["LEFT", "SR"]] 
        
        ax.barh(y_positions, sr_values, color='#ff5000', edgecolor='black', linewidth=0.5, height=0.5)
        
        # 3. Add Labels (Modified Layout)
        for idx, direction in enumerate(["RIGHT", "LEFT"]):
            row = summary.loc[direction]
            x_val = sr_values[idx]
            ha = 'left' if x_val >= 0 else 'right'
            offset = 10 if x_val >= 0 else -10
            
            # SR (Large)
            ax.text(x_val + offset, idx + 0.12, f"{row['SR']:.0f}", 
                    va='center', ha=ha, fontsize=18, fontweight='bold', color='#ff5000')
            
            # B% | Dot% (Small)
            sub_stats = f"{row['BPct']:.0f}% | {row['DotPct']:.0f}%"
            ax.text(x_val + offset, idx - 0.18, sub_stats, 
                    va='center', ha=ha, fontsize=14, fontweight='bold', color='#000000')

        # 4. Styling
        ax.set_title(seg_title, fontsize=14, fontweight='bold', pad=15)
        ax.axvline(0, color='black', linewidth=1)
        ax.set_yticks([]) 
        ax.set_yticklabels([])
        ax.set_xlim(-320, 320) # Increased limit to accommodate larger font
        
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.tick_params(axis='both', which='both', bottom=False, labelbottom=False, left=False)

    return fig


# Chart : Pitchmap - death overs
import matplotlib.pyplot as plt

def create_pitch_map_death(df_in, delivery_type):
    if df_in.empty:
        # Create an empty figure with a text note if data is missing
        fig, ax = plt.subplots(figsize=(4, 6))
        ax.text(0.5, 0.5, f"No data for Pitch Map ({delivery_type})", ha='center', va='center', fontsize=12)
        ax.axis('off')
        return fig

    # --- Data Filtering ---
    # 1. Separate Wickets
    pitch_wickets = df_in[df_in["Wicket"] == True]
    
    # 2. Separate Non-Wicket Boundaries (4s and 6s)
    pitch_boundaries = df_in[(df_in["Wicket"] == False) & (df_in["Runs"].isin([4, 6]))]
    
    # 3. Separate Non-Wicket Others (0, 1, 2, 3 runs)
    pitch_others = df_in[(df_in["Wicket"] == False) & (~df_in["Runs"].isin([4, 6]))]
    
    # --- Chart Setup ---
    fig, ax = plt.subplots(figsize=(4, 6))
    ax.set_facecolor('white')
    fig.patch.set_facecolor('white')

    # --- Pitch Bins & Zone Lines ---
    PITCH_BINS = get_pitch_bins(delivery_type)
    
    # Draw horizontal zone lines
    boundary_y_values = sorted([v[0] for v in PITCH_BINS.values() if v[0] > -4.0], reverse=True)
    for y_val in boundary_y_values:
        ax.axhline(y=y_val, color="lightgrey", linewidth=1.0, linestyle="--")

    # Add zone labels on the far left
    for length_label, bounds in PITCH_BINS.items():
        mid_y = (bounds[0] + bounds[1]) / 2
        ax.text(
            x=-1.45, 
            y=mid_y, 
            s=length_label.upper(), 
            ha='left', 
            va='center', 
            fontsize=8, 
            color="grey", 
            fontweight='bold'
        )

    # --- Plot Data (Scatter Traces) ---
    
    # 1. Others (Light Grey) - Plotted first to stay in background
    ax.scatter(
        pitch_others["BounceY"], pitch_others["BounceX"], 
        s=60, 
        c='#D3D3D3', 
        edgecolor='white', 
        linewidths=1.0, 
        alpha=0.9,
        label="Others"
    )

    # 2. Boundaries (Royal Blue) - New Category
    ax.scatter(
        pitch_boundaries["BounceY"], pitch_boundaries["BounceX"], 
        s=70, 
        c='#4169E1', # Royal Blue
        edgecolor='white', 
        linewidths=1.0, 
        alpha=0.95,
        label="Boundary"
    )

    # 3. Wickets (Red) - Plotted last to stay on top
    ax.scatter(
        pitch_wickets["BounceY"], pitch_wickets["BounceX"], 
        s=90, 
        c='red', 
        edgecolor='white', 
        linewidths=1.0, 
        alpha=0.95,
        label="Wicket"
    )

    # --- Stump lines (Vertical Lines) ---
    ax.axvline(x=-0.18, color="#777777", linestyle="--", linewidth=1)
    ax.axvline(x=0.18, color="#777777", linestyle="--", linewidth=1)
    ax.axvline(x=0, color="#777777", linestyle="--", linewidth=0.8)

    # --- Layout (Axis and Spines) ---
    ax.set_xlim([-1.5, 1.5])
    # Reversed axis: lower values at bottom
    ax.set_ylim([16.0, -4.0])

    # Hide ticks and labels
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.grid(False)
    
    # Set spines/borders
    spine_color = 'black'
    spine_width = 0.5
    for spine_name in ['left', 'top', 'bottom', 'right']:
        ax.spines[spine_name].set_visible(True)
        ax.spines[spine_name].set_color(spine_color)
        ax.spines[spine_name].set_linewidth(spine_width)
        
    plt.tight_layout()
    
    return fig
    
## ----------------------------------------------------------
## CHart 11: Death Overs PitchLength Performance
## ----------------------------------------------------------
def create_pitch_metrics_bar(df_in, delivery_type):
    if df_in.empty:
        fig, ax = plt.subplots(figsize=(10, 9))
        ax.text(0.5, 0.5, "No Data", ha='center', va='center')
        ax.axis('off')
        return fig

    # Data Processing
    bins_dict = get_pitch_bins(delivery_type)
    ordered_keys = list(bins_dict.keys())[::-1]
    
    def assign_label(x):
        for label, bounds in bins_dict.items():
            if bounds[0] <= x < bounds[1]: return label
        return "Other"

    df_temp = df_in.copy()
    df_temp["PitchLengthLabel"] = df_temp["BounceX"].apply(assign_label)
    
    summary = df_temp.groupby("PitchLengthLabel").agg(
        Runs=("Runs", "sum"), Balls=("Runs", "count"),
        Boundaries=("Runs", lambda x: ((x == 4) | (x == 6)).sum())
    ).reindex(ordered_keys).fillna(0)
    
    summary["SR"] = (summary["Runs"] / summary["Balls"] * 100).fillna(0)
    summary["BPct"] = (summary["Boundaries"] / summary["Balls"] * 100).fillna(0)

    # Plotting: 1 row, 2 columns
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 9), sharey=True)
    plt.subplots_adjust(wspace=0.3) # Space between the two bar columns
    
    y = np.arange(len(ordered_keys))

    # --- Column 1: Strike Rate ---
    ax1.barh(y, summary["SR"], color='#ff5000', edgecolor='black', height=0.6)
    ax1.set_title("Strike Rate", fontsize=20, fontweight='bold', color='#000000')
    ax1.set_yticks(y)
    ax1.set_yticklabels(ordered_keys, fontsize=16, fontweight='bold')
    # ax1.set_xlim(0, 250)
    
    # Add SR labels at end of bars
    for i, v in enumerate(summary["SR"]):
        ax1.text(v + 5, i, f'{v:.0f}', va='center', fontsize=18, fontweight='bold')

    # --- Column 2: Boundary % ---
    ax2.barh(y, summary["BPct"], color='#ff5000', edgecolor='black', height=0.6)
    ax2.set_title("Boundary %", fontsize=20, fontweight='bold', color='#000000')
    ax2.set_xlim(0, 100)
    
    # Add B% labels at end of bars
    for i, v in enumerate(summary["BPct"]):
        ax2.text(v + 2, i, f'{v:.1f}%', va='center',fontsize=18, fontweight='bold')

    # Clean up both axes
    for ax in [ax1, ax2]:
        ax.spines[['top', 'right', 'bottom']].set_visible(False)
        ax.xaxis.set_visible(False)
        ax.invert_yaxis() # Top-down order (Full Toss at top)

    return fig


# Chart 12 Slower ball Effectiveness
def create_speed_metrics_bar(df_in):
    if df_in.empty:
        fig, ax = plt.subplots(figsize=(5, 2))
        ax.text(0.5, 0.5, "No Data", ha='center', va='center')
        ax.axis('off')
        return fig

    # 1. Define Speed Groups
    def assign_speed_group(speed):
        if speed < 125:
            return "Slower (<125)"
        return "Pace On (>125)"

    df_temp = df_in.copy()
    # Ensure ReleaseSpeed is numeric
    df_temp["ReleaseSpeed"] = pd.to_numeric(df_temp["ReleaseSpeed"], errors='coerce')
    df_temp = df_temp.dropna(subset=["ReleaseSpeed"])
    
    df_temp["SpeedGroup"] = df_temp["ReleaseSpeed"].apply(assign_speed_group)
    
    # 2. Aggregate Data
    ordered_groups = ["Pace On (>125)", "Slower (<125)"]
    summary = df_temp.groupby("SpeedGroup").agg(
        Runs=("Runs", "sum"), 
        Balls=("Runs", "count"),
        Boundaries=("Runs", lambda x: ((x == 4) | (x == 6)).sum())
    ).reindex(ordered_groups).fillna(0)
    
    summary["SR"] = (summary["Runs"] / summary["Balls"] * 100).fillna(0)
    summary["BPct"] = (summary["Boundaries"] / summary["Balls"] * 100).fillna(0)

    # 3. Plotting (1 row, 2 columns)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(5, 3), sharey=True)
    plt.subplots_adjust(wspace=0.4) 
    
    y = np.arange(len(ordered_groups))
    height = 0.5

    # --- Column 1: Strike Rate ---
    ax1.barh(y, summary["SR"], color='#ff5000', edgecolor='black', height=height)
    ax1.set_title("Strike Rate", fontsize=14, fontweight='bold', color='#000000')
    ax1.set_yticks(y)
    ax1.set_yticklabels(ordered_groups, fontsize=14, fontweight='bold')
    #ax1.set_xlim(0, 250)
    
    for i, v in enumerate(summary["SR"]):
        ax1.text(v + 5, i, f'{v:.0f}', va='center', fontweight='bold', fontsize = 14)

    # --- Column 2: Boundary % ---
    ax2.barh(y, summary["BPct"], color='#ff5000', edgecolor='black', height=height)
    ax2.set_title("Boundary %", fontsize=14, fontweight='bold', color='#000000')
    ax2.set_xlim(0, 100)
    
    for i, v in enumerate(summary["BPct"]):
        ax2.text(v + 2, i, f'{v:.1f}%', va='center', fontweight='bold',fontsize = 14)

    # Formatting
    for ax in [ax1, ax2]:
        ax.spines[['top', 'right', 'bottom']].set_visible(False)
        ax.xaxis.set_visible(False)
        ax.invert_yaxis() 

    return fig

# PAG LAYOUT SETUP

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
# --- Sidebar Content ---



# =========================================================
# 💥 1. CRITICAL: GET DATA FROM SESSION STATE
# This check ensures the page cannot run without data uploaded via Home.py
# =========================================================
if 'data_df' not in st.session_state:
    st.error("Please go back to the **Home** page and upload the data first to begin the analysis.")
    # Stop execution of the rest of the script if data is missing
    st.stop()


# Retrieve the full raw DataFrame
df_raw = st.session_state['data_df']
with st.sidebar:
    st.title("MEN'S")
    st.write("Red Ball")
# 1. Define columns with appropriate widths
col_title_space, col_legend, col_dataname = st.columns([1, 2.5, 1.5]) 

with col_title_space:
    st.title("BATTERS")

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
# NOTE: BattingTeam is often case-sensitive, but converting Batsman/Bowler is key here.
# =========================================================
# 🌟 FILTERS 🌟
# =========================================================
# Use columns to align the four filters horizontally
filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4) 

# --- Filter Logic ---
all_teams = ["All"] + sorted(df_raw["BattingTeam"].dropna().unique().tolist())

# 1. Batting Team Filter (in column 1)
with filter_col1:
    bat_team = st.selectbox("Batting Team", all_teams, index=0)

# 2. Batsman Name Filter (Logic depends on Batting Team - in column 2)
if bat_team != "All":
    # Filter batsmen based on selected team
    batsmen_options = ["All"] + sorted(df_raw[df_raw["BattingTeam"] == bat_team]["BatsmanName"].dropna().unique().tolist())
else:
    # Show all batsmen if 'All' teams is selected
    batsmen_options = ["All"] + sorted(df_raw["BatsmanName"].dropna().unique().tolist())
    
with filter_col2:
    batsman = st.selectbox("Batsman Name", batsmen_options, index=0)

# 3. Innings Filter (in column 3)
# Check if 'Innings' column exists before creating options (Robustness)
if "Innings" in df_raw.columns:
    innings_options = ["All"] + sorted(df_raw["Innings"].dropna().unique().tolist())
    with filter_col3:
        selected_innings = st.selectbox("Innings", innings_options, index=0)
else:
    selected_innings = "All" # Default if column is missing
    with filter_col3:
        st.info("Innings filter unavailable.")

# 4. Bowler Hand Filter (in column 4)
# Check if 'IsBowlerRightHanded' column exists (CRITICAL FIX)
if "IsBowlerRightHanded" in df_raw.columns:
    bowler_hand_options = ["All", "Right Hand", "Left Hand"]
    with filter_col4:
        selected_bowler_hand = st.selectbox("Bowler Hand", bowler_hand_options, index=0)
else:
    selected_bowler_hand = "All" # Default if column is missing
    with filter_col4:
        st.info("Bowler Hand filter unavailable.")
    
# =========================================================

# --- Apply Filters to the Raw dataframes ---

def apply_filters(df):
    df_filtered = df.copy() # Work on a copy of the sub-dataframes

    if bat_team != "All":
        df_filtered = df_filtered[df_filtered["BattingTeam"] == bat_team]
        
    if batsman != "All":
        df_filtered = df_filtered[df_filtered["BatsmanName"] == batsman]
        
    # Apply Innings Filter (Only if column exists)
    if selected_innings != "All" and "Innings" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["Innings"] == selected_innings]
        
    # Apply Bowler Hand Filter (Only if column exists)
    if selected_bowler_hand != "All" and "IsBowlerRightHanded" in df_filtered.columns:
        # True for Right Hand, False for Left Hand
        is_right = (selected_bowler_hand == "Right Hand") 
        df_filtered = df_filtered[df_filtered["IsBowlerRightHanded"] == is_right]
        
    return df_filtered

# Separate by delivery type BEFORE filtering to save a little processing, then apply filters
df_seam_base = df_raw[df_raw["DeliveryType"] == "Seam"]
df_spin_base = df_raw[df_raw["DeliveryType"] == "Spin"]

# Apply filters
df_seam = apply_filters(df_seam_base)
df_spin = apply_filters(df_spin_base)
    
heading_text = batsman.upper() if batsman != "All" else "ALL"
# Use st.markdown to inject HTML, setting the text color directly
st.markdown(
    f"<h3 style='color: #ff5000;'><b>{heading_text}</b></h3>",
    unsafe_allow_html=True
)

# --- 4. DISPLAY CHARTS IN TWO COLUMNS (SEAM vs. SPIN) ---
col1, col2 = st.columns(2)
    
# --- LEFT COLUMN: SEAM ANALYSIS ---
with col1:
    st.markdown("### v SEAM")

    # Row 1: Zonal Analysis (Beehive Zones)
    st.markdown("###### CREASE BEEHIVE ZONES v SEAM")
    st.pyplot(create_zonal_analysis(df_seam, batsman, "Seam"), use_container_width=True)
    
    # Row 2: Crease Beehive Scatter
    st.markdown("###### CREASE BEEHIVE v SEAM")
    st.pyplot(create_crease_beehive(df_seam, "Seam"), use_container_width=True)
    
    # Row 4: Pitch Map and Vertical Run % Bar (Side-by-Side)
    pitch_col, pitch_bars = st.columns(2)
    with pitch_col:
        st.markdown("###### PITCHMAP v SEAM")
        st.pyplot(create_pitch_map(df_seam, "Seam"), use_container_width=True)  
    with pitch_bars:
        st.markdown("###### ")
        st.pyplot(create_pitch_Length_bars(df_seam, "Seam"), use_container_width=True)   

    # Row 5: Interception Side-On (Wide View)
    # Row 5: Interception Side-On (Wide View)
    st.markdown("###### INTERCEPTION SIDE-VIEW v SEAM")
    st.pyplot(create_interception_side_on(df_seam, "Seam"), use_container_width=True)

    # Row 7: Interception and Scoring Areas (Side-by-Side)
    bottom_col_left, bottom_col_right = st.columns(2)
    with bottom_col_left:
        st.markdown("###### INTERCEPTION TOP-VIEW v SEAM")
        st.pyplot(create_interception_front_on(df_seam, "Seam"), use_container_width=True)
        
    with bottom_col_right:
        st.markdown("###### SCORING AREAS v SEAM ")    
        # Two charts stacked vertically in the right column
        st.pyplot(create_wagon_wheel(df_seam, "Seam"), use_container_width=True)
        
    
    # Row 8: Swing/Deviation Direction Analysis (Side-by-Side)
    final_col_swing, final_col_deviation = st.columns(2)

    with final_col_swing:
        st.markdown("###### SWING v SEAM")
        st.pyplot(create_directional_split(df_seam, "Swing", "Swing", "Seam"), use_container_width=True)

    with final_col_deviation:
        st.markdown("###### DEVIATION v SEAM")
        st.pyplot(create_directional_split(df_seam, "Deviation", "Deviation", "Seam"), use_container_width=True) 

    st.markdown("""<hr style="height:5px;border:none;color:#333;background-color:#333;margin-bottom:8px;margin-top:5px;" /> """, unsafe_allow_html=True)
    st.markdown("### DEATH OVERS")
   
    # --- Row 9 & 10 DEATH OVERS ANALYSIS (Overs 16-20) ---
    df_death_seam = df_seam[(df_seam['Over'] >= 16) & (df_seam['Over'] <= 20)].copy()

    if df_death_seam.empty:
        st.warning("No data available for Death Overs (16-20).")
    else:
    # 1. Create the two main columns
        death_map_col, death_bars_col = st.columns([1, 1]) 
    
        with death_map_col:
            st.markdown("###### PITCHMAP IN DEATH OVERS v SEAM ")
            fig_death_map = create_pitch_map_death(df_death_seam, "Seam")
            st.pyplot(fig_death_map, use_container_width=True)    
        
        # 2. This column will now hold BOTH the Length and Speed charts
        with death_bars_col:
            # --- Upper Chart: Pitch Length Metrics ---
            st.markdown("###### PITCH METRICS IN DEATH OVERS v SEAM")
            fig_death_metrics = create_pitch_metrics_bar(df_death_seam, "Seam")
            st.pyplot(fig_death_metrics, use_container_width=True)
        
        # --- Lower Chart: Release Speed Metrics ---
            st.markdown("###### METRICS BY RELEASE SPEED v SEAM")
            fig_speed_stats = create_speed_metrics_bar(df_death_seam)
            st.pyplot(fig_speed_stats, use_container_width=True)
        
# --- RIGHT COLUMN: SPIN ANALYSIS ---
with col2:
    st.markdown("### v SPIN")
    
    # Row 1: Zonal Analysis (Beehive Zones)
    st.markdown("###### CREASE BEEHIVE ZONES v SPIN")
    st.pyplot(create_zonal_analysis(df_spin, batsman, "Spin"), use_container_width=True)
    
    # Row 2: Crease Beehive Scatter
    st.markdown("###### CREASE BEEHIVE v SPIN")
    st.pyplot(create_crease_beehive(df_spin, "Spin"), use_container_width=True)
 

    # Row 4: Pitch Map and Vertical Run % Bar (Side-by-Side)
    pitch_col, pitch_bars = st.columns(2)
    with pitch_col:
        st.markdown("###### PITCHMAP v SPIN")
        st.pyplot(create_pitch_map(df_spin, "Spin"), use_container_width=True)  
    with pitch_bars:
        st.markdown("###### ")
        st.pyplot(create_pitch_Length_bars(df_spin, "Spin"), use_container_width=True)    
    
    # Row 5: Interception Side-On (Wide View)
    st.markdown("###### INTERCEPTION SIDE-VIEW v SPIN")
    st.pyplot(create_interception_side_on(df_spin, "Spin"), use_container_width=True)

    # Row 7: Interception Front-On and Scoring Areas (Side-by-Side)
    bottom_col_left, bottom_col_right = st.columns(2)

    with bottom_col_left:
        st.markdown("###### INTERCEPTION TOP-VIEW v SPIN")
        st.pyplot(create_interception_front_on(df_spin, "Spin"), use_container_width=True)
        
    with bottom_col_right:
        st.markdown("###### SCORING AREAS v SPIN")
        st.pyplot(create_wagon_wheel(df_spin,'SPIN'), use_container_width=True)
            

    # Row 8: Swing/Deviation Direction Analysis (Side-by-Side)
    final_col_swing, final_col_deviation = st.columns(2)

    with final_col_swing:
        st.markdown("###### DRIFT v SPIN")
        # For spin, we often look at 'Drift' instead of 'Swing'
        st.pyplot(create_directional_split(df_spin, "Swing", "Drift", "Spin"), use_container_width=True)

    with final_col_deviation:
        st.markdown("###### TURN v SPIN")
        # For spin, we often look at 'Turn' instead of 'Deviation'
        st.pyplot(create_directional_split(df_spin, "Deviation", "Turn", "Spin"), use_container_width=True)

    # --- Row 11 & 12 DEATH OVERS ANALYSIS (SPIN) ---
    st.markdown("""<hr style="height:5px;border:none;color:#333;background-color:#333;margin-bottom:8px;margin-top:5px;" /> """, unsafe_allow_html=True)
    st.markdown("### ")
    # Filter specifically for Spin data during Death Overs
    df_death_spin = df_spin[(df_spin['Over'] >= 16) & (df_spin['Over'] <= 20)].copy()

    if df_death_spin.empty:
        st.warning("No spin data available for Death Overs (16-20).")
    else:
        # 1. Create the two main columns
        death_spin_map_col, death_spin_bars_col = st.columns([1, 1]) 
    
        with death_spin_map_col:
            st.markdown("###### PITCHMAP IN DEATH OVERS v SPIN")
            # Pass "Spin" to ensure the correct pitch visual and bins are used
            fig_death_map_spin = create_pitch_map_death(df_death_spin, "Spin")
            st.pyplot(fig_death_map_spin, use_container_width=False)    
        
        # 2. Stack the Length and Speed charts in the right column
        with death_spin_bars_col:
            # --- Upper Chart: Pitch Length Metrics ---
            st.markdown("###### PITCH METRICS IN DEATH OVERS v SPIN")
            fig_death_metrics = create_pitch_metrics_bar(df_death_spin, "Spin")
            st.pyplot(fig_death_metrics, use_container_width=True)
        
        # # --- Lower Chart: Release Speed Metrics ---
        #     st.markdown("###### METRICS BY RELEASE SPEED v SPIN")
        # # Reuses the speed logic (Pace On vs Slower) for the spinners
        #     fig_speed_stats_spin = create_speed_metrics_bar(df_death_spin)
        #     st.pyplot(fig_speed_stats_spin, use_container_width=True)
