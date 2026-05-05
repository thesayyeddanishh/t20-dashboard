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

## --- CHART 2b: LATERAL PERFORMANCE BOXES (ax_boxes) ---
    
    num_regions = len(ordered_zones)
    box_width = 1 / num_regions
    box_height = 1  # Increased slightly to fit two lines of text
    left = 0
    
    # 4. COLOR NORMALIZATION BY STRIKE RATE
    sr_values = summary["SR"].replace([np.inf, -np.inf], np.nan)
    sr_max = sr_values.max() if sr_values.max() > 0 else 200
    norm = mcolors.Normalize(vmin=0, vmax=sr_max)
    cmap = cm.get_cmap('Wistia')

    # summary["Avg"] = (summary["Runs"] / summary["Wickets"]).replace([np.inf, -np.inf], summary["Runs"]).fillna(0)

    for index, row in summary.iterrows():
        runs = int(row["Runs"])
        outs = int(row["Wickets"])
        avg = row.get("Avg", 0)
        sr = row["SR"]
    
        if np.isnan(sr) or sr == np.inf:
            color = 'white'
            text_color = 'black'
            sr_display = '0'
            avg_display = '0.0'
        else:
            color = cmap(norm(sr))
            sr_display = f"{sr:.0f}"
            avg_display = f"{avg:.0f}"
            
            # Contrast logic for text
            r, g, b, a = color
            luminosity = 0.2126 * r + 0.7152 * g + 0.0722 * b
            text_color = 'white' if luminosity < 0.5 else 'black'
        
        # Draw the box
        ax_boxes.add_patch(patches.Rectangle((left, 0), box_width, box_height, 
                                             edgecolor="black", facecolor=color, linewidth=1))
    
        # Zone Name (e.g., STUMPS)
        ax_boxes.text(left + box_width / 2, box_height + 0.05, index, 
                      ha='center', va='bottom', fontsize=8, fontweight='bold', color='black')
    
        # --- UPDATED TEXT: Multi-line Format ---
        # Line 1: Runs and Outs
        label_top = f"{runs} R, {outs} W"
        # Line 2: Avg and SR
        label_bottom = f"{avg_display} Avg, {sr_display} SR"
        
        # Position Line 1 slightly above center
        ax_boxes.text(left + box_width / 2, box_height * 0.65, label_top, 
                      ha='center', va='center', fontsize=8, fontweight='bold', color=text_color)
        
        # Position Line 2 slightly below center
        ax_boxes.text(left + box_width / 2, box_height * 0.35, label_bottom, 
                      ha='center', va='center', fontsize=8, fontweight='bold', color=text_color)
    
        left += box_width

    # Formatting and Border logic...
    ax_boxes.set_xlim(0, 1)
    ax_boxes.set_ylim(-0.1, box_height + 0.3) # Adjusted limits for better spacing
    ax_boxes.axis('off')
    
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

    # Total Runs
    df_summary["TotalRuns"] = df_summary["Runs"]
    
    # Categories for plotting (reversed for barh)
    categories = df_summary.index.tolist()[::-1]
    
    # 2. Chart Setup (3 Rows, 1 Column)
    # sharex=False is default, sharey=True forces Y-axis to be the same, 
    # which is what we want for aligning the bar labels.
    fig, axes = plt.subplots(3, 1, figsize=FIG_SIZE, sharey=True) 
    # Adjust space between charts to minimize it vertically
    plt.subplots_adjust(hspace=10) 

    metrics = ["StrikeRate", "Average","Runs"]
    titles = ["Batting Strike Rate", "Batting Average", "Runs"]
    colors = ['#ff5000', '#ff5000', '#ff5000']
                                
    # Define limits for each chart to ensure proper scaling
    max_sr = df_summary["StrikeRate"].max() * 1.2 if df_summary["StrikeRate"].max() > 0 else 300
    max_avg = df_summary["Average"].max() * 1.2 if df_summary["Average"].max() > 0 else 100
    max_runs = df_summary["Runs"].max() * 1.2 if df_summary["Runs"].max() > 0 else 100

    xlim_limits = {
        "Average": (0, max_avg),
        "StrikeRate": (0, max_sr),
        "Runs": (0, max_runs)
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
                label = f"{val:.0f}"
            
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
    
    # --- 1. Data Preparation ---
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

# Calculate Strike Rate (SR) and Average (Avg)
    df_summary["SR"] = df_summary.apply(
    lambda row: (row["Runs"] / row["Balls"]) * 100 if row["Balls"] > 0 else 0, axis=1
    )

# Calculate Average (Avg)
    df_summary["Avg"] = df_summary.apply(
    lambda row: row["Runs"] / row["Wickets"] if row["Wickets"] > 0 else row["Runs"], axis=1
    )

# --- 2. Plotting Equal Boxes ---
    num_boxes = len(ordered_keys)
    box_width = 1.0 / num_boxes 
    left = 0.0
    box_height = 0.6 # Original height

    max_sr_val = df_summary["SR"].replace([np.inf, -np.inf], np.nan).max()
    max_sr = max_sr_val if max_sr_val > 0 else 200 

    norm = mcolors.Normalize(vmin=0, vmax=max_sr)
    cmap = cm.get_cmap(COLORMAP)

    for index, row in df_summary.iterrows():
        runs = int(row["Runs"])
        wickets = int(row["Wickets"])
        sr = row["SR"]
        avg = row["Avg"]
    
        if sr == 0 or np.isnan(sr):
            sr_display = '0'
            avg_display = '0.0'
            color = 'white'
            text_color = 'black'
        else:
            sr_display = f"{sr:.0f}"
            avg_display = f"{avg:.1f}" # Use .1f so Avg isn't just a rounded whole number
            color = cmap(norm(sr)) 
        
        # Contrast logic for text
        r, g, b, a = color
        luminosity = 0.2126 * r + 0.7152 * g + 0.0722 * b
        text_color = 'white' if luminosity < 0.5 else 'black'
        
    # Draw the box  
    ax_bar.barh(
        y=0.5,             
        width=box_width,
        height=box_height,          
        left=left,         
        color=color,
        edgecolor='black',
        linewidth=0.4
    )
    
    # --- FIXED VARIABLE NAMES HERE ---
    label_top = f"{runs} Runs, {wickets}W" 
    label_bottom = f"{avg_display} Avg, {sr_display} SR"
    
    center_x = left + box_width / 2
    
    # Position Line 1 (Upper half)
    ax_bar.text(center_x, 0.62, label_top, ha='center', va='center', 
                fontsize=8, fontweight='bold', color=text_color)
    
    # Position Line 2 (Lower half)
    ax_bar.text(center_x, 0.38, label_bottom, ha='center', va='center', 
                fontsize=8, fontweight='bold', color=text_color)
    
    # Crease Width Label (Top of the box)
    ax_bar.text(center_x, 0.82, index, ha='center', va='bottom', fontsize=9, color='black')

    left += box_width
ax_bar.set_xlim(0, 1)
ax_bar.set_ylim(0, 1) 
ax_bar.axis('off')

    

# --- Helper Functions for Chart 6 ---
def calculate_scoring_wagon(row):
    """Calculates the scoring area based on LandingX/Y coordinates and handedness."""
    LX = row.get("LandingX")
    LY = row.get("LandingY")
    RH = row.get("IsBatsmanRightHanded")
    
    if RH is None or LX is None or LY is None or row.get("Runs", 0) == 0: 
        return None
    
    def atan_safe(numerator, denominator): 
        return np.arctan(numerator / denominator) if denominator != 0 else np.nan 
    
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

# --- Main Combined Function (Chart 6) ---
def create_wagon_wheel(df_in, delivery_type):
    FIG_WIDTH = 7
    FIG_HEIGHT = 5
    FIG_SIZE = (FIG_WIDTH, FIG_HEIGHT)

    if df_in.empty:
        fig, ax = plt.subplots(figsize=FIG_SIZE)
        ax.text(0.5, 0.5, f"No Data for {delivery_type} Analysis", ha='center', va='center', fontsize=8)
        ax.axis('off')
        return fig

    # CRITICAL FIX: Initialize the figure and axes to avoid NameError
    fig, (ax_wagon) = plt.subplots(1, 1, figsize=FIG_SIZE)
    plt.subplots_adjust(hspace=0.3)

    try:
        # 1. Data Preparation (Must be indented 8 spaces from the left)
        df_wagon = df_in.copy()
        df_wagon["ScoringWagon"] = df_wagon.apply(calculate_scoring_wagon, axis=1)
        df_wagon["FixedAngle"] = df_wagon["ScoringWagon"].apply(calculate_scoring_angle)
        
        summary_with_shots = df_wagon.groupby("ScoringWagon").agg(
            TotalRuns=("Runs", "sum"), 
            Balls=("Runs", "count"),
            FixedAngle=("FixedAngle", 'first')
        ).reset_index().dropna(subset=["ScoringWagon"])
        
        # 2. Handedness & Area Logic
        handedness_mode = df_in["IsBatsmanRightHanded"].dropna().mode()
        is_right_handed = handedness_mode.iloc[0] if not handedness_mode.empty else True
        
        all_areas = ["FINE LEG", "SQUARE LEG", "LONG ON", "LONG OFF", "COVER", "THIRD MAN"] if is_right_handed else ["THIRD MAN", "COVER", "LONG OFF", "LONG ON", "SQUARE LEG", "FINE LEG"]
            
        template_df = pd.DataFrame({
            "ScoringWagon": all_areas, 
            "FixedAngle": [calculate_scoring_angle(area) for area in all_areas]
        })

        wagon_summary = template_df.merge(summary_with_shots.drop(columns=["FixedAngle"], errors='ignore'), on="ScoringWagon", how="left").fillna(0)
        wagon_summary["RunPercentage"] = (wagon_summary["TotalRuns"] / wagon_summary["TotalRuns"].sum() * 100).fillna(0)
        
        # 3. Plot Part 1: Wagon Wheel (ax_wagon)
        angles = wagon_summary["FixedAngle"].tolist()
        wagon_summary['Rank'] = wagon_summary['RunPercentage'].rank(method='dense', ascending=False)
        colors = ['#ff5000' if (r == 1 and p > 0) else 'white' for r, p in zip(wagon_summary['Rank'], wagon_summary['RunPercentage'])]

        wedges, texts, autotexts = ax_wagon.pie(
            angles, 
            colors=colors, 
            wedgeprops={"width": 1, "edgecolor": "black"}, 
            startangle=90, 
            counterclock=False, 
            autopct='%1.0f%%', # Changed from '' to '%1.0f%%'
            pctdistance=0.6
        )

        # 4. Styling Text with Contrast Logic
        for i, autotext in enumerate(autotexts):
            if wagon_summary["RunPercentage"].iloc[i] > 0:
                autotext.set_text(f'{wagon_summary["RunPercentage"].iloc[i]:.0f}%')
                autotext.set_fontsize(15); autotext.set_fontweight('bold')
                rgb = mcolors.to_rgb(colors[i])
                lum = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
                autotext.set_color('white' if lum < 0.5 else 'black')
            else:
                autotext.set_text('')

        ax_wagon.set_title("RUNS DISTRIBUTION (%)", fontsize=20, fontweight='bold', pad=20)
        ax_wagon.axis('equal')

    except Exception as e:
        # If ax_wagon is already defined, we can use it to show the error
        ax_wagon.text(0.5, 0.5, f"Error: {e}", ha='center', va='center')
        ax_wagon.axis('off')

    return fig        

    # === CRITICAL FIX: CENTERING PERCENTAGE LABELS AND STYLING ===
    # --- Inside the autotext loop ---
    for i, autotext in enumerate(autotexts):
            if i >= len(run_percentages): 
                break
            
            percent = run_percentages[i]
            
            if percent > 0:
                # 1. Set text and alignment
                autotext.set_text(f'{percent:.0f}%')
                autotext.set_horizontalalignment('center')
                autotext.set_verticalalignment('center')
                
                # 2. Set styling (Font size and weight)
                autotext.set_fontsize(15)
                autotext.set_fontweight('bold')
                
                # 3. Dynamic contrast: Determine if text should be white or black
                color_rgb = mcolors.to_rgb(colors[i])
                luminosity = 0.2126 * color_rgb[0] + 0.7152 * color_rgb[1] + 0.0722 * color_rgb[2]
                
                # If background is dark (luminosity < 0.5), use white text
                if luminosity < 0.5:
                    autotext.set_color('white')
                else:
                    autotext.set_color('black')
            else:
                # Hide text for 0% slices
                autotext.set_text('')
    ax_wagon.axis('equal');

#------------ Chart 12: Speed Effectiveness
def create_speed_metrics_bar(df_in, delivery_type):
    if df_in.empty:
        fig, ax = plt.subplots(figsize=(5, 3))
        ax.text(0.5, 0.5, "No Data", ha='center', va='center')
        ax.axis('off')
        return fig

    # 1. Define Dynamic Speed Groups
    def assign_speed_group(speed):
        if delivery_type == "Seam":
            if speed < 125: return "<125"
            elif 125 <= speed <= 140: return "125-140"
            else: return "140+"
        else: # Spin logic
            if speed < 85: return "<85"
            elif 85 <= speed <= 95: return "85-95"
            else: return "95+"

    df_temp = df_in.copy()
    df_temp["ReleaseSpeed"] = pd.to_numeric(df_temp["ReleaseSpeed"], errors='coerce')
    df_temp = df_temp.dropna(subset=["ReleaseSpeed"])
    df_temp["SpeedGroup"] = df_temp["ReleaseSpeed"].apply(assign_speed_group)
    
    # 2. Set Order based on Delivery Type
    if delivery_type == "Seam":
        ordered_groups = ["140+", "125-140", "<125"]
    else:
        ordered_groups = ["95+", "85-95", "<85"]

    # 3. Aggregate Data
    summary = df_temp.groupby("SpeedGroup").agg(
        Runs=("Runs", "sum"), 
        Balls=("Runs", "count"),
        Dismissals=("Wicket", "sum") 
    ).reindex(ordered_groups).fillna(0)
    
    # Calculations
    summary["SR"] = (summary["Runs"] / summary["Balls"] * 100).fillna(0)
    
    # Calculate Average
    # If Dismissals > 0, do the math; otherwise, the average is just the Total Runs
    summary["Avg"] = (summary["Runs"] / summary["Dismissals"])
    
    # This checks for both positive and negative infinity and replaces with Runs
    summary.loc[np.isinf(summary["Avg"]), "Avg"] = summary["Runs"]
    
    # Finally, fill any remaining NaNs (0/0 cases) with 0
    summary["Avg"] = summary["Avg"].fillna(0)

    # 4. Plotting - Wider figure to prevent squashing
    fig, (ax1, ax2, ax3, ax4) = plt.subplots(1, 4, figsize=(16, 4), sharey=True)
    plt.subplots_adjust(wspace=0.3) 
    
    y = np.arange(len(ordered_groups))
    height = 0.7 

    metrics = ["Runs", "Dismissals", "Avg", "SR"]
    titles = ["Runs", "Outs", "Avg", "SR"]
    axes = [ax1, ax2, ax3, ax4]

    for ax, metric, title in zip(axes, metrics, titles):
        vals = summary[metric]
        ax.barh(y, vals, color='#ff5000', edgecolor='black', height=height)
        ax.set_title(title, fontsize=14, fontweight='bold')
        
        # FIX: Place text at a fixed X-position (5% of the max value) 
        # to ensure it's always readable and aligned
        max_val = vals.max() if vals.max() > 0 else 1
        for i, v in enumerate(vals):
            # If the bar is very short, put black text after it. 
            # If bar is long, put white text at the start of the bar.
            label_x = max_val * 0.05 
            
            ax.text(
                label_x, i, 
                f'{v:.0f}' if metric != "Avg" else f'{v:.1f}',
                va='center', 
                ha='left',
                fontweight='bold', 
                fontsize=13,
                color='white' if v > (max_val * 0.2) else 'black'
            )

    # Formatting
    ax1.set_yticks(y)
    ax1.set_yticklabels(ordered_groups, fontsize=12, fontweight='bold')
    
    for ax in axes:
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
    st.markdown("###### INTERCEPTION SIDE-VIEW v SEAM")
    st.pyplot(create_interception_side_on(df_seam, "Seam"), use_container_width=True)

    # Row 7: Interception and Scoring Areas (Side-by-Side)
    st.markdown("###### SCORING AREAS v SEAM ")
    st.pyplot(create_wagon_wheel(df_seam, "Seam"), use_container_width=True)
    
    # --- Row 9 & 10 RELEASE SPEED ANALYSIS---
    st.markdown("###### METRICS BY RELEASE SPEED v SEAM")
    st.pyplot(create_speed_metrics_bar(df_seam, "Seam"), use_container_width=True)
        
# --- RIGHT COLUMN: SPIN ANALYSIS ---
with col2:
    st.markdown("### v SPIN")
    
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

    # Row 7: Scoring Areas (Side-by-Side)
    st.markdown("###### SCORING AREAS v SPIN")
    st.pyplot(create_wagon_wheel(df_spin,'SPIN'), use_container_width=True)
    
    # --- Row 9 & 10 RELEASE SPEED ANALYSIS---
    st.markdown("###### METRICS BY RELEASE SPEED v SEAM")
    st.pyplot(create_speed_metrics_bar(df_spin, "Spin"), use_container_width=True)
    
        # # --- Lower Chart: Release Speed Metrics ---
        #     st.markdown("###### METRICS BY RELEASE SPEED v SPIN")
        # # Reuses the speed logic (Pace On vs Slower) for the spinners
        #     fig_speed_stats_spin = create_speed_metrics_bar(df_death_spin)
        #     st.pyplot(fig_speed_stats_spin, use_container_width=True)
