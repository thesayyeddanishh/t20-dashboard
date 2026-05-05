import streamlit as st
import pandas as pd
from io import StringIO

# Required columns check
REQUIRED_COLS = [
    "BatsmanName", "DeliveryType", "Wicket", "StumpsY", "StumpsZ", 
    "BattingTeam", "CreaseY", "CreaseZ", "Runs", "IsBatsmanRightHanded", 
    "LandingX", "LandingY", "BounceX", "BounceY", "InterceptionX", 
    "InterceptionZ", "InterceptionY", "Over"]

# --- Page Configuration ---
st.set_page_config(
    page_title="VR Story Finder",
    layout="wide"
)

# --- Custom CSS for Sidebar Width (200px) ---
# --- Custom CSS for Sidebar Width and Padding Reduction ---
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
with st.sidebar:
    st.write("For Men's T20s only")

# --- Helper Function for Upload Logic ---
def process_upload(uploaded_file):
    if uploaded_file is not None:
        try:
            # Read and decode the uploaded file data
            data = uploaded_file.getvalue().decode("utf-8")
            df_raw = pd.read_csv(StringIO(data))
            
            # Validation: Check if all required columns are present
            if not all(col in df_raw.columns for col in REQUIRED_COLS):
                missing_cols = [col for col in REQUIRED_COLS if col not in df_raw.columns]
                st.error(f"The CSV file is missing required columns: {', '.join(missing_cols)}")
                # Clear state if validation fails
                st.session_state.pop('data_df', None)
                st.session_state.pop('file_name', None)
                return False
            else:
                # Store the valid DataFrame and filename in session state
                st.session_state['data_df'] = df_raw
                st.session_state['file_name'] = uploaded_file.name
                
                # Check if this was a replacement
                if 'initial_load_complete' in st.session_state:
                    st.success(f"Data successfully replaced!\n Total deliveries loaded: {len(df_raw):,}.")
                else:
                    st.session_state['initial_load_complete'] = True
                    st.success(f"Data uploaded successfully! File: {uploaded_file.name}. Please navigate to a dashboard page.")
                return True
        
        except Exception as e:
            st.error(f"Error reading file: {e}")
            st.session_state.pop('data_df', None)
            st.session_state.pop('file_name', None)
            return False
    return False

# =========================================================
# --- Main App Logic (Single Uploader for Load and Replace) ---
# =========================================================

st.title("VR Story Finder")

# Use a single file uploader component
uploaded_file = st.file_uploader(
    "Upload your CSV file here", 
    type=["csv"],
    # The default text is "Browse files" or "Drop file here". Streamlit handles this text.
    key="main_uploader" 
)

# Run the upload process whenever a file is present/changed in the uploader
if uploaded_file is not None:
    # If a file is selected (or replaced), process it immediately
    if 'data_df' not in st.session_state or uploaded_file.name != st.session_state.get('file_name'):
        process_upload(uploaded_file)
        # Note: Streamlit automatically reruns the script when the uploader state changes, 
        # making a manual st.rerun() unnecessary here unless required for external state management.


# --- Display Status and Data Preview ---
if 'data_df' in st.session_state:
    df_loaded = st.session_state['data_df']
    file_name = st.session_state.get('file_name', 'N/A')
    
    st.info("Data is loaded. Use the navigation on the left to switch between pages.")
    
    st.write(f"Total Deliveries Loaded: {len(df_loaded):,}")

    # Display selected file name as requested
    if st.checkbox("Show first 5 rows of current data"):
        st.write(f"**Selected File Name:** `{file_name}`")
        st.dataframe(df_loaded.head())
