import streamlit as st
import os
from modules.curve_filter import extract_curve_data
from modules.vol_extractor import filter_vol_data
from modules.volatility_surface import generate_vol_surfaces
from modules.time_series_plotter import build_vol_time_series
import tempfile
import shutil
from datetime import datetime
from PIL import Image
import plotly.graph_objs as go
import pandas as pd
from fpdf import FPDF
import io
import zipfile
import uuid

def combine_images(image_paths, output_path):
    images = [Image.open(p) for p in image_paths]
    n = len(images)
    if n == 2:
        # Side by side
        widths, heights = zip(*(i.size for i in images))
        total_width = sum(widths)
        max_height = max(heights)
        combined = Image.new('RGB', (total_width, max_height), (255, 255, 255))
        x_offset = 0
        for im in images:
            combined.paste(im, (x_offset, 0))
            x_offset += im.size[0]
    elif n == 3:
        # 2x2 grid, last cell blank
        widths, heights = zip(*(i.size for i in images))
        max_width = max(widths)
        max_height = max(heights)
        combined = Image.new('RGB', (2*max_width, 2*max_height), (255, 255, 255))
        positions = [(0,0), (max_width,0), (0,max_height)]
        for im, pos in zip(images, positions):
            combined.paste(im, pos)
    else:
        # Just return the first image if only one
        images[0].save(output_path)
        return output_path
    combined.save(output_path)
    return output_path

def find_all_csvs(folder):
    csv_files = []
    for root, _, files in os.walk(folder):
        for file in files:
            if file.lower().endswith('.csv') and not file.startswith('.'):
                csv_files.append(os.path.join(root, file))
    return csv_files

st.set_page_config(page_title="Volatility Pipeline", layout="wide")

st.title("📊 Volatility Pipeline App")

CURVE_LIST = [
    "NYMEX", "HSC", "TGP - 500", "TRANSCO 65", "FGT - Z3", "CG MAINLINE", "NGPL - TxOk", "NGPL - MIDCON", "PEPL", "VENTURA", "DEMARC", "CHICAGO", "MICHCON", "DOMINION", "TCO", "TETCO - M3", "TRANSCO Z6", "ALGONQUIN", "EP PERMIAN", "EP SAN JUAN", "WAHA", "ROCKIES", "CIG", "PG&E CITYGATE", "SOCAL", "AECO"
]

YEARS = [str(y) for y in range(2014, 2026)]

# === Tabs ===
tabs = st.tabs(["Filter & Download Data", "Upload Filtered Data", "Visualize & Download", "Interactive Charts", "Download Results"])

# --- Tab 1: Filter & Download Data ---
with tabs[0]:
    st.header("Step 1: Filter Data and Download Zip")
    curve = st.selectbox("Curve Name", CURVE_LIST, index=CURVE_LIST.index("NYMEX") if "NYMEX" in CURVE_LIST else 0)
    year = st.selectbox("Year (full year)", YEARS, index=YEARS.index("2024"))
    use_full_year = st.checkbox("Use full year?", value=True)
    if use_full_year:
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        custom_date_disabled = True
    else:
        start_date, end_date = st.date_input("Select date range", [datetime(int(year), 1, 1), datetime(int(year), 12, 31)])
        start_date = str(start_date)
        end_date = str(end_date)
        custom_date_disabled = False
    month = st.text_input("Month (MM, optional)", value="")
    # Input method selection
    input_method = st.radio("Choose input method:", ["Upload ZIP file", "Local folder path"])
    
    if input_method == "Upload ZIP file":
        uploaded_folder = st.file_uploader("Upload a zipped folder containing all CSV files", type="zip", key="filter_upload")
        st.info("""
        **Instructions:**
        1. Place all your CSV files in a single folder.
        2. Zip the folder (right-click → 'Send to compressed (zipped) folder' on Windows, or 'Compress' on Mac).
        3. Upload the resulting `.zip` file below.
        
        **Note:** If your zip file is larger than 200MB, try these solutions:
        - **Option A:** Split your data into smaller chunks (e.g., by year or month)
        - **Option B:** Use the command: `streamlit run app.py --server.maxUploadSize 1024`
        - **Option C:** Compress your zip file more aggressively
        """)
    else:
        uploaded_folder = None
        col1, col2 = st.columns([3, 1])
        with col1:
            local_folder_path = st.text_input("Enter the full path to your CSV folder:", 
                                             placeholder="C:\\Users\\YourName\\Documents\\CSV_Files or /home/username/data/csv_files")
        with col2:
            if st.button("📁 Browse", help="Click to open file browser"):
                st.info("Please enter the path manually or use the text input above")
        
        # Show folder info if path is provided
        if local_folder_path and os.path.exists(local_folder_path):
            # Count CSV files in all subdirectories
            csv_count = 0
            for root, dirs, files in os.walk(local_folder_path):
                csv_count += len([f for f in files if f.endswith('.csv')])
            st.success(f"✅ Folder found! Contains {csv_count} CSV files in all subdirectories")
        elif local_folder_path:
            st.error("❌ Folder not found. Please check the path.")
        st.info("""
        **Instructions for local folder:**
        1. Enter the full path to the folder containing your CSV files
        2. Make sure the path is correct and the folder exists
        3. The app will process all CSV files in that folder and subfolders
        
        **Example paths:**
        - Windows: `C:\\Users\\YourName\\Documents\\CSV_Files`
        - Mac/Linux: `/home/username/data/csv_files`
        """)
    if st.button("Filter & Download Data") and (uploaded_folder or (input_method == "Local folder path" and local_folder_path)):
        with tempfile.TemporaryDirectory() as temp_dir:
            if input_method == "Upload ZIP file" and uploaded_folder:
                zip_path = os.path.join(temp_dir, uploaded_folder.name)
                with open(zip_path, "wb") as f:
                    f.write(uploaded_folder.getvalue())
                shutil.unpack_archive(zip_path, temp_dir)
                extracted_folder = temp_dir
            else:
                # Use local folder path
                if not os.path.exists(local_folder_path):
                    st.error(f"❌ Folder not found: {local_folder_path}")
                    st.stop()
                extracted_folder = local_folder_path
            filtered_output = os.path.join(temp_dir, "filtered")
            os.makedirs(filtered_output, exist_ok=True)
            extract_curve_data(
                input_folder=extracted_folder,
                output_folder=filtered_output,
                year=year,
                target_curves=[curve],
                target_strikes=[
                    'ATM - $1.00', 'ATM - $0.75', 'ATM - $0.50', 'ATM - $0.25', 'ATM',
                    'ATM + $0.25', 'ATM + $0.50', 'ATM + $0.75'
                ],
                month=month if month else None
            )
            # Zip the filtered output
            zip_output = os.path.join(temp_dir, "filtered_data.zip")
            with zipfile.ZipFile(zip_output, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(filtered_output):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, filtered_output)
                        zipf.write(file_path, arcname)
            with open(zip_output, "rb") as f:
                st.download_button("Download Filtered Data Zip", f, file_name="filtered_data.zip")
    
    # --- Separate EWMA Data Filtering Section ---
    st.markdown("---")
    st.subheader("Filter EWMA Data (for Time Series & Daily Shock)")
    st.write("This section filters the original data for EWMA values to use in time series analysis.")
    
    # Store the extracted folder path in session state for EWMA filtering
    if 'extracted_folder_path' not in st.session_state:
        st.session_state['extracted_folder_path'] = None
    
    if st.button("Filter EWMA Data", type="secondary"):
        # Check if we have data to work with
        if (input_method == "Local folder path" and local_folder_path and os.path.exists(local_folder_path)) or (input_method == "Upload ZIP file" and uploaded_folder is not None):
            with st.spinner("Filtering EWMA data..."):
                # Create temporary folder for EWMA data
                ewma_folder = os.path.join(tempfile.gettempdir(), f"ewma_data_{uuid.uuid4().hex}")
                os.makedirs(ewma_folder, exist_ok=True)
                
                csv_files_found = 0
                csv_files_processed = 0
                
                # Determine the source folder based on input method
                if input_method == "Local folder path":
                    source_folder = local_folder_path
                else:  # Upload ZIP file
                    # Extract the ZIP file for EWMA processing
                    with tempfile.TemporaryDirectory() as temp_dir:
                        zip_path = os.path.join(temp_dir, uploaded_folder.name)
                        with open(zip_path, "wb") as f:
                            f.write(uploaded_folder.getvalue())
                        shutil.unpack_archive(zip_path, temp_dir)
                        source_folder = temp_dir
                
                # === STEP 1: Build file dictionary by month ===
                file_dict = {}
                for root, _, files in os.walk(source_folder):
                    for file in files:
                        if file.endswith('.csv') and year in file:
                            # Extract month from filename (assuming format like 20240101.csv)
                            import re
                            match = re.search(rf'{year}(\d{{2}})\d{{2}}', file)
                            if match:
                                month = f"{year}-{match.group(1)}"
                                file_dict.setdefault(month, []).append((file, os.path.join(root, file)))
                
                csv_files_found = sum(len(files) for files in file_dict.values())
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # === STEP 2: Process files month by month ===
                for month, files in file_dict.items():
                    status_text.text(f"Processing {month}...")
                    compiled_data = []
                    
                    for filename, full_path in sorted(files):
                        try:
                            df = pd.read_csv(full_path, encoding='utf-8', on_bad_lines='skip')
                            if df.empty:
                                continue
                                
                            df.columns = df.columns.str.strip().str.replace('\u200b', '')
                            
                            # Check if required columns exist
                            required_cols = ['Basis', 'Call/Put', 'Type']
                            if not all(col in df.columns for col in required_cols):
                                continue
                            
                            # Sanitize filtering columns (like your old version)
                            df['Basis'] = df['Basis'].astype(str).str.strip()
                            df['Type'] = df['Type'].astype(str).str.strip().str.upper()
                            df['Call/Put'] = df['Call/Put'].astype(str).str.strip().str.upper()
                            
                            # Extract date from filename (like your old version)
                            import re
                            match = re.search(rf'{year}\d{{4}}', filename)
                            if match:
                                date_str = match.group(0)
                                df['date'] = pd.to_datetime(date_str, format='%Y%m%d')
                            else:
                                continue
                            
                            # ✅ Apply ALL filters: Basis, Type, Call/Put (like your old version)
                            df_filtered = df[
                                (df['Basis'].str.upper() == curve.upper()) &
                                (df['Type'] == 'HIST') &
                                (df['Call/Put'] == 'EWMA')
                            ]
                            
                            if not df_filtered.empty:
                                compiled_data.append(df_filtered)
                                
                        except Exception as e:
                            continue
                    
                    # Save monthly file if we have data
                    if compiled_data:
                        final_df = pd.concat(compiled_data, ignore_index=True)
                        monthly_file = os.path.join(ewma_folder, f"{month}.csv")
                        final_df.to_csv(monthly_file, index=False)
                        csv_files_processed += 1
                    
                    progress_bar.progress(len([m for m in file_dict.keys() if m <= month]) / len(file_dict))
                
                # === STEP 3: Combine all monthly files ===
                all_months_data = []
                for file in sorted(os.listdir(ewma_folder)):
                    if file.endswith('.csv') and re.match(r'\d{4}-\d{2}', file):
                        df = pd.read_csv(os.path.join(ewma_folder, file))
                        all_months_data.append(df)
                
                if all_months_data:
                    combined_df = pd.concat(all_months_data, ignore_index=True)
                    combined_file = os.path.join(ewma_folder, f"{year}_combined.csv")
                    combined_df.to_csv(combined_file, index=False)
                    csv_files_processed += 1
                
                # Clear progress indicators
                progress_bar.empty()
                status_text.empty()
                
                if csv_files_processed > 0:
                    # Create ZIP file for EWMA data
                    ewma_zip_path = os.path.join(tempfile.gettempdir(), f"ewma_data_{uuid.uuid4().hex}.zip")
                    with zipfile.ZipFile(ewma_zip_path, 'w') as zipf:
                        for root, _, files in os.walk(ewma_folder):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, ewma_folder)
                                zipf.write(file_path, arcname)
                    
                    # Download button for EWMA data
                    with open(ewma_zip_path, 'rb') as f:
                        st.download_button(
                            label="📥 Download EWMA Data ZIP",
                            data=f.read(),
                            file_name=f"ewma_data_{curve}_{year}.zip",
                            mime="application/zip"
                        )
                    
                    st.success(f"✅ EWMA data filtering complete! Found {csv_files_found} files, processed {csv_files_processed} files with EWMA data.")
                else:
                    st.error("No EWMA data found in the original files. Please check your data.")
                    st.write("💡 Make sure your data contains:")
                    st.write("- Basis column with your selected curve name")
                    st.write("- Call/Put column with 'EWMA' values")
                    st.write("- Type column with 'HIST' values")
                    st.write("- Curve_Date column for date processing")
        else:
            st.error("Please provide a valid local folder path or upload a ZIP file first.")
 

 
# --- Tab 2: Upload Filtered Data ---
with tabs[1]:
    st.header("Step 2: Upload Filtered Data Zips for Processing")
    st.info("""
    **Instructions:**
    1. Upload the filtered_data.zip (surface data) from Step 1.
    2. Upload the ewma_data.zip (EWMA data) from Step 1.
    3. Each dataset will be processed separately for its respective analysis.
    """)
    
    # Surface data upload
    st.subheader("Surface Data (for Implied Volatility Surface)")
    filtered_zip = st.file_uploader("Upload the filtered_data.zip from Step 1", type="zip", key="filtered_zip_upload")
    
    # EWMA data upload
    st.subheader("EWMA Data (for Time Series & Daily Shock)")
    ewma_zip = st.file_uploader("Upload the ewma_data.zip from Step 1", type="zip", key="ewma_zip_upload")
    
    # Process uploads
    if filtered_zip or ewma_zip:
        temp_dir = os.path.join(tempfile.gettempdir(), f"filtered_data_{uuid.uuid4().hex}")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Process surface data
        if filtered_zip:
            surface_temp_dir = os.path.join(tempfile.gettempdir(), f"surface_data_{uuid.uuid4().hex}")
            os.makedirs(surface_temp_dir, exist_ok=True)
            
            zip_path = os.path.join(surface_temp_dir, filtered_zip.name)
            with open(zip_path, "wb") as f:
                f.write(filtered_zip.getvalue())
            shutil.unpack_archive(zip_path, surface_temp_dir)
            st.session_state["filtered_data_folder"] = surface_temp_dir
            st.success("✅ Surface data extracted and ready for processing.")
        
        # Process EWMA data
        if ewma_zip:
            ewma_temp_dir = os.path.join(tempfile.gettempdir(), f"ewma_data_{uuid.uuid4().hex}")
            os.makedirs(ewma_temp_dir, exist_ok=True)
            
            ewma_zip_path = os.path.join(ewma_temp_dir, ewma_zip.name)
            with open(ewma_zip_path, "wb") as f:
                f.write(ewma_zip.getvalue())
            shutil.unpack_archive(ewma_zip_path, ewma_temp_dir)
            st.session_state["ewma_data_folder"] = ewma_temp_dir
            st.success("✅ EWMA data extracted and ready for processing.")
        
        # Debug info
        if filtered_zip:
            for root, dirs, files in os.walk(surface_temp_dir):
                print(f"[DEBUG] Surface Root: {root}, Files: {files}")
        if ewma_zip:
            for root, dirs, files in os.walk(ewma_temp_dir):
                print(f"[DEBUG] EWMA Root: {root}, Files: {files}")

# --- Tab 3: Visualize & Download ---
with tabs[2]:
    st.header("Step 3: Select Outputs & Visualize")
    st.info("""
    **Instructions:**
    1. Make sure you have uploaded your filtered_data.zip in Step 2.
    2. Select the outputs you want to generate and visualize.
    3. Use the export options to download Excel or PDF reports.
    """)
    if "filtered_data_folder" not in st.session_state:
        st.warning("Please complete Steps 1 and 2 before proceeding.")
    else:
        filtered_data_folder = st.session_state["filtered_data_folder"]
        print("[DEBUG] Searching for CSVs in folder:", filtered_data_folder)
        filtered_csvs = find_all_csvs(filtered_data_folder)
        print("[DEBUG] Filtered CSVs found:", filtered_csvs)
        if not filtered_csvs:
            st.error("No CSV files found in the uploaded filtered data. Please check your zip and try again.")
        else:
            st.success(f"Found {len(filtered_csvs)} CSV files. Proceeding to visualization and export.")
            # Surface data processing options
            st.subheader("Surface Data Processing")
            surface_output_options = st.multiselect(
                "Select surface outputs to generate:",
                ["Implied Volatility Surface"],
                default=["Implied Volatility Surface"]
            )
            
            # EWMA data processing options
            st.subheader("EWMA Data Processing")
            ewma_output_options = st.multiselect(
                "Select EWMA outputs to generate:",
                ["Time Series + Rolling", "Daily Shock"],
                default=["Time Series + Rolling"]
            )
            
            rolling_window = st.slider("Rolling Window (days)", min_value=5, max_value=60, value=21, step=1)

            show_interactive = st.checkbox("Show Interactive Plot (Plotly)", value=True)

            run_button = st.button("🚀 Run Pipeline")

            # Initialize image lists
            surf_imgs = []
            
            if run_button:
                if not (curve and year and "filtered_data_folder" in st.session_state):
                    st.error("Curve, year, and filtered data are required.")
                else:
                    month_val = month if month else None
                    # Use a persistent directory instead of temporary
                    session_dir = os.path.join(tempfile.gettempdir(), f"vol_pipeline_{uuid.uuid4().hex}")
                    surface_output = os.path.join(session_dir, "surfaces")
                    time_series_output = os.path.join(session_dir, "time_series")
                    os.makedirs(surface_output, exist_ok=True)
                    os.makedirs(time_series_output, exist_ok=True)
                    
                    if run_button:
                        # Create progress tracking
                        progress_container = st.container()
                        status_container = st.container()
                        
                        with progress_container:
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                        
                        with status_container:
                            with st.spinner("Running pipelines..."):
                                total_steps = len(surface_output_options) + len(ewma_output_options)
                                current_step = 0
                                
                                                                # Process surface data for implied volatility surface
                                if "Implied Volatility Surface" in surface_output_options:
                                    current_step += 1
                                    status_text.text(f"Step {current_step}/{total_steps}: Generating Implied Volatility Surface...")
                                    progress_bar.progress(current_step / total_steps)
                                    
                                    # Use the surface data folder from session state
                                    surface_data_folder = st.session_state.get("filtered_data_folder", filtered_data_folder)
                                    
                                    generate_vol_surfaces(
                                        data_folder=surface_data_folder,
                                        output_folder=surface_output,
                                        target_curve=curve,
                                        target_month=month_val,
                                        start_date=start_date,
                                        end_date=end_date
                                    )
                                    
                                    surf_imgs = [os.path.join(surface_output, f) for f in os.listdir(surface_output) if f.endswith('.png')]
                            
                            # Process EWMA data for time series and daily shock
                            if ewma_output_options and "ewma_data_folder" in st.session_state:
                                current_step += 1
                                status_text.text(f"Step {current_step}/{total_steps}: Processing Time Series & Daily Shock...")
                                progress_bar.progress(current_step / total_steps)
                                
                                ewma_data_folder = st.session_state.get("ewma_data_folder")
                                if ewma_data_folder and os.path.exists(ewma_data_folder):
                                    # Import the time series module
                                    from modules.time_series_plotter import build_vol_time_series
                                    
                                    build_vol_time_series(
                                        input_folder=ewma_data_folder,
                                        iv_surface_folder=surface_output,
                                        output_folder=time_series_output,
                                        curve_name=curve,
                                        month=month_val,
                                        rolling_window=rolling_window,
                                        start_date=start_date,
                                        end_date=end_date
                                    )
                                    
                                    # Get the generated images
                                    ts_imgs = [os.path.join(time_series_output, f) for f in os.listdir(time_series_output) if 'timeseries_rolling' in f and f.endswith('.png')]
                                    dc_imgs = [os.path.join(time_series_output, f) for f in os.listdir(time_series_output) if 'dailychange' in f and f.endswith('.png')]
                                else:
                                    st.warning("EWMA data not found. Please upload the ewma_data.zip in Step 2.")
                                    ts_imgs, dc_imgs = [], []
                            else:
                                ts_imgs, dc_imgs = [], []
                            
                            # Clear progress indicators
                            progress_bar.empty()
                            status_text.empty()
                                
                        st.success("✅ Pipeline execution complete.")
                        
                    # Store the output directories in session state for display
                    st.session_state["surface_output"] = surface_output
                    st.session_state["time_series_output"] = time_series_output
                    st.session_state["surf_imgs"] = surf_imgs
                    st.session_state["ts_imgs"] = ts_imgs
                    st.session_state["dc_imgs"] = dc_imgs
                    st.session_state["pipeline_completed"] = True








# --- Tab 4: Interactive Charts ---
with tabs[3]:
    st.header("📈 Interactive Charts")
    st.info("""
    **Interactive Charts:**
    This tab shows interactive Plotly charts for all available data types.
    Charts will appear here after you run the pipeline in Step 3.
    """)
    
    if "pipeline_completed" in st.session_state and st.session_state["pipeline_completed"]:
        surface_output = st.session_state["surface_output"]
        
        # Create sub-tabs for different chart types
        chart_tabs = st.tabs(["Implied Volatility Surface", "Time Series & Rolling", "Daily Shock"])
        
        # Implied Volatility Surface Tab
        with chart_tabs[0]:
            st.subheader("🌊 Implied Volatility Surface")
            if os.path.exists(surface_output):
                # Debug: Show all files in surface output
                all_files = os.listdir(surface_output)
                st.write(f"Debug: All files in surface output: {all_files}")
                
                surf_csvs = [f for f in os.listdir(surface_output) if f.endswith('_data.csv')]
                st.write(f"Debug: Surface CSV files found: {surf_csvs}")
                
                if surf_csvs:
                    # Create dropdown for surface files
                    surface_file_options = [f.replace('_data.csv', '') for f in surf_csvs]
                    selected_surface = st.selectbox("Select Month/Period:", surface_file_options, index=0, key="surface_select")
                    
                    try:
                        selected_file = f"{selected_surface}_data.csv"
                        df = pd.read_csv(os.path.join(surface_output, selected_file))
                        moneyness = [c for c in df.columns if c not in ['date', 'date_ordinal']]
                        if moneyness:
                            z = df[moneyness].values
                            x = [float(m.replace('ATM + $', '').replace('ATM - $', '-').replace('ATM', '0')) if 'ATM' in m else float(m) for m in moneyness]
                            y = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d').tolist()
                            
                            fig = go.Figure(data=[go.Surface(z=z, x=x, y=y, colorscale='Viridis')])
                            fig.update_layout(
                                title=f'Implied Volatility Surface - {selected_surface}',
                                scene={
                                    'xaxis_title': 'Moneyness',
                                    'yaxis_title': 'Date',
                                    'zaxis_title': 'Implied Volatility',
                                    'camera': {
                                        'eye': {'x': 1.5, 'y': 1.5, 'z': 1.5}
                                    }
                                },
                                width=800,
                                height=600
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.warning("No moneyness data found in the surface file.")
                    except Exception as e:
                        st.error(f"Error reading volatility surface data: {str(e)}")
                else:
                    st.warning("No surface data files found. Please run the pipeline with 'Implied Volatility Surface' selected.")
            else:
                st.warning("Surface output directory not found. Please run the pipeline first.")
        
        # Time Series & Rolling Tab
        with chart_tabs[1]:
            st.subheader("📈 Time Series & Rolling Average")
            time_series_output = st.session_state.get("time_series_output")
            if time_series_output and os.path.exists(time_series_output):
                excel_files = [f for f in os.listdir(time_series_output) if f.endswith('.xlsx')]
                if excel_files:
                    # Create dropdown for Excel files
                    excel_file_options = [f.replace('.xlsx', '') for f in excel_files]
                    selected_excel = st.selectbox("Select Month/Period:", excel_file_options, index=0, key="ts_excel_select")
                    
                    try:
                        selected_file = f"{selected_excel}.xlsx"
                        df = pd.read_excel(os.path.join(time_series_output, selected_file), sheet_name=None)
                        
                        orig = df.get("Original_TS")
                        roll = None
                        for k in df.keys():
                            if k.startswith("Rolling"):
                                roll = df[k]
                                break
                        
                        if orig is not None and roll is not None:
                            # For EWMA data, there's usually only one column (EWMA_Volatility)
                            # For surface data, limit to first 3 columns to avoid too many graphs
                            columns_to_plot = [col for col in orig.columns if col != 'date'][:3]
                            
                            for col in columns_to_plot:
                                fig = go.Figure()
                                fig.add_trace(go.Scatter(x=orig['date'], y=orig[col], mode='lines', name='Original', line=dict(color='blue')))
                                fig.add_trace(go.Scatter(x=roll['date'], y=roll[col], mode='lines', name='Rolling Average', line=dict(color='red', dash='dash')))
                                fig.update_layout(
                                    title=f"Time Series & Rolling Average: {col} - {selected_excel}",
                                    xaxis_title="Date",
                                    yaxis_title="Volatility",
                                    hovermode='x unified'
                                )
                                st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.warning("Time series data not found in the Excel file.")
                    except Exception as e:
                        st.error(f"Error reading time series data: {str(e)}")
                else:
                    st.warning("No Excel files found. Please run the pipeline with 'Time Series + Rolling' selected.")
            else:
                st.warning("Time series output directory not found. Please run the pipeline first.")
        
        # Daily Shock Tab
        with chart_tabs[2]:
            st.subheader("⚡ Daily Volatility Shocks")
            time_series_output = st.session_state.get("time_series_output")
            if time_series_output and os.path.exists(time_series_output):
                excel_files = [f for f in os.listdir(time_series_output) if f.endswith('.xlsx')]
                if excel_files:
                    # Create dropdown for Excel files (same as time series since they're in the same files)
                    excel_file_options = [f.replace('.xlsx', '') for f in excel_files]
                    selected_excel = st.selectbox("Select Month/Period:", excel_file_options, index=0, key="ds_excel_select")
                    
                    try:
                        selected_file = f"{selected_excel}.xlsx"
                        df = pd.read_excel(os.path.join(time_series_output, selected_file), sheet_name=None)
                        daily_change = df.get("Daily_Change")
                        
                        if daily_change is not None:
                            # For EWMA data, there's usually only one column (EWMA_Volatility)
                            # For surface data, limit to first 3 columns to avoid too many graphs
                            columns_to_plot = [col for col in daily_change.columns if col != 'date'][:3]
                            
                            for col in columns_to_plot:
                                fig = go.Figure()
                                fig.add_trace(go.Scatter(
                                    x=daily_change['date'], 
                                    y=daily_change[col], 
                                    mode='lines', 
                                    name='Daily ΔVol', 
                                    line=dict(color='red', width=2)
                                ))
                                fig.update_layout(
                                    title=f"Daily Volatility Shocks: {col} - {selected_excel}",
                                    xaxis_title="Date",
                                    yaxis_title="Δ Volatility",
                                    hovermode='x unified'
                                )
                                st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.warning("Daily change data not found in the Excel file.")
                    except Exception as e:
                        st.error(f"Error reading daily shock data: {str(e)}")
                else:
                    st.warning("No Excel files found. Please run the pipeline with 'Daily Shock' selected.")
            else:
                st.warning("Time series output directory not found. Please run the pipeline first.")
        

    else:
        st.info("👆 Please run the pipeline in Step 3 to see interactive charts here.")


# --- Tab 5: Download Results ---
with tabs[4]:
    st.header("📥 Download Results")
    st.info("""
    **Download your processed results as Excel files or PNG images.**
    Select the outputs you want to download and choose your preferred format.
    """)
    
    # Check if pipeline has been run
    if "pipeline_completed" not in st.session_state or not st.session_state["pipeline_completed"]:
        st.warning("👆 Please run the pipeline in Step 3 first to generate results for download.")
    else:
        surface_output = st.session_state.get("surface_output")
        time_series_output = st.session_state.get("time_series_output")
        
        # Download options
        st.subheader("Select Outputs to Download")
        
        download_options = []
        if surface_output and os.path.exists(surface_output):
            download_options.append("Implied Volatility Surface")
        if time_series_output and os.path.exists(time_series_output):
            download_options.append("Time Series & Rolling")
            download_options.append("Daily Shock")
        
        if not download_options:
            st.warning("No results found. Please run the pipeline first.")
        else:
            selected_downloads = st.multiselect(
                "Choose outputs to download:",
                download_options,
                default=download_options
            )
            
            # File format selection
            file_format = st.radio("Download format:", ["Excel Files", "PNG Images", "Both"])
            
            if selected_downloads and st.button("📦 Create Download Package"):
                with st.spinner("Creating download package..."):
                    # Create temporary directory for the download package
                    temp_download_dir = os.path.join(tempfile.gettempdir(), f"download_package_{uuid.uuid4().hex}")
                    os.makedirs(temp_download_dir, exist_ok=True)
                    
                    files_to_zip = []
                    
                    # Process each selected output
                    for output_type in selected_downloads:
                        if output_type == "Implied Volatility Surface" and surface_output:
                            # Surface data - Excel files
                            if file_format in ["Excel Files", "Both"]:
                                surface_csvs = [f for f in os.listdir(surface_output) if f.endswith('_data.csv')]
                                for csv_file in surface_csvs:
                                    csv_path = os.path.join(surface_output, csv_file)
                                    excel_path = os.path.join(temp_download_dir, f"Surface_{csv_file.replace('.csv', '.xlsx')}")
                                    # Convert CSV to Excel
                                    df = pd.read_csv(csv_path)
                                    df.to_excel(excel_path, index=False)
                                    files_to_zip.append(excel_path)
                            
                            # Surface data - PNG images
                            if file_format in ["PNG Images", "Both"]:
                                surface_pngs = [f for f in os.listdir(surface_output) if f.endswith('.png')]
                                for png_file in surface_pngs:
                                    png_path = os.path.join(surface_output, png_file)
                                    dest_path = os.path.join(temp_download_dir, f"Surface_{png_file}")
                                    shutil.copy2(png_path, dest_path)
                                    files_to_zip.append(dest_path)
                        
                        elif output_type in ["Time Series & Rolling", "Daily Shock"] and time_series_output:
                            # Time series data - Excel files
                            if file_format in ["Excel Files", "Both"]:
                                time_series_excels = [f for f in os.listdir(time_series_output) if f.endswith('.xlsx')]
                                for excel_file in time_series_excels:
                                    excel_path = os.path.join(time_series_output, excel_file)
                                    dest_path = os.path.join(temp_download_dir, f"TimeSeries_{excel_file}")
                                    shutil.copy2(excel_path, dest_path)
                                    files_to_zip.append(dest_path)
                            
                            # Time series data - PNG images
                            if file_format in ["PNG Images", "Both"]:
                                time_series_pngs = [f for f in os.listdir(time_series_output) if f.endswith('.png')]
                                for png_file in time_series_pngs:
                                    png_path = os.path.join(time_series_output, png_file)
                                    dest_path = os.path.join(temp_download_dir, f"TimeSeries_{png_file}")
                                    shutil.copy2(png_path, dest_path)
                                    files_to_zip.append(dest_path)
                    
                    # Create ZIP file
                    if files_to_zip:
                        zip_filename = f"volatility_results_{curve}_{year}_{file_format.lower().replace(' ', '_')}.zip"
                        zip_path = os.path.join(tempfile.gettempdir(), zip_filename)
                        
                        with zipfile.ZipFile(zip_path, 'w') as zipf:
                            for file_path in files_to_zip:
                                if os.path.exists(file_path):
                                    arcname = os.path.basename(file_path)
                                    zipf.write(file_path, arcname)
                        
                        # Provide download button
                        with open(zip_path, 'rb') as f:
                            st.download_button(
                                label=f"📥 Download {zip_filename}",
                                data=f.read(),
                                file_name=zip_filename,
                                mime="application/zip"
                            )
                        
                        st.success(f"✅ Download package created with {len(files_to_zip)} files!")
                        
                        # Show file list
                        st.subheader("📋 Files in package:")
                        for file_path in files_to_zip:
                            if os.path.exists(file_path):
                                st.write(f"• {os.path.basename(file_path)}")
                    else:
                        st.error("No files found to include in the download package.")

