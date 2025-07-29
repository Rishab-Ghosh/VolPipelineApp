import os
import re
import pandas as pd

def extract_curve_data(input_folder, output_folder, year, target_curves, target_strikes, month=None):
    print(f"[INFO] Starting curve data extraction...")
    print(f"[INFO] Input folder: {input_folder}")
    print(f"[INFO] Output folder: {output_folder}")
    print(f"[INFO] Target curves: {target_curves}")
    print(f"[INFO] Target strikes: {target_strikes}")
    print(f"[INFO] Year: {year}")
    print(f"[INFO] Month: {month}")
    
    os.makedirs(output_folder, exist_ok=True)
    file_dict = {}

    csv_files_found = 0
    csv_files_processed = 0
    
    for root, _, files in os.walk(input_folder):
        for file in files:
            if not file.endswith('.csv'):
                continue
            csv_files_found += 1
            full_path = os.path.join(root, file)
            try:
                # Check if file is empty or too small
                if os.path.getsize(full_path) < 10:  # Less than 10 bytes
                    print(f"[WARNING] Skipping empty file: {full_path}")
                    continue
                
                df = pd.read_csv(full_path, encoding='utf-8', on_bad_lines='skip')
                if df.empty:
                    print(f"[WARNING] Skipping empty dataframe from: {full_path}")
                    continue
            except Exception as e:
                print(f"[ERROR] Failed to read {full_path}: {str(e)}")
                continue
                
            df.columns = df.columns.str.strip()
            
            # Check if required columns exist
            required_columns = ['Basis', 'Type', 'Curve_Date']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                print(f"[WARNING] Missing required columns {missing_columns} in {full_path}")
                continue
                
            df['Basis'] = df['Basis'].astype(str).str.strip()
            df['Type'] = df['Type'].astype(str).str.strip().str.upper()
            df['Curve_Date'] = pd.to_datetime(df['Curve_Date'], errors='coerce')
            df = df[df['Curve_Date'].notnull()]
            if not isinstance(df['Curve_Date'], pd.Series):
                df['Curve_Date'] = pd.Series(df['Curve_Date'])
            df['year'] = df['Curve_Date'].dt.year.astype(str)
            df['month'] = df['Curve_Date'].dt.month.astype(int).apply(lambda x: f"{x:02d}")
            df['date'] = df['Curve_Date']
            
            # Filter for target curves, year, and (if specified) month
            df_filtered = df[
                (df['Basis'].str.upper().isin([c.upper() for c in target_curves])) &
                (df['Type'].isin([t.upper() for t in target_strikes])) &
                (df['year'] == year)
            ]
            if month:
                df_filtered = df_filtered[df_filtered['month'] == month]
                
            # Group by year-month
            for ym, group in df_filtered.groupby(['year', 'month']):
                month_key = f"{ym[0]}-{ym[1]}"
                if month and ym[1] != month:
                    continue
                if month_key not in file_dict:
                    file_dict[month_key] = []
                file_dict[month_key].append(group)
            csv_files_processed += 1

    print(f"[INFO] Found {csv_files_found} CSV files, processed {csv_files_processed} files")

    for month_key, groups in file_dict.items():
        print(f"[INFO] Processing {month_key}...")
        out_df = pd.concat(groups, ignore_index=True)
        out_path = os.path.join(output_folder, f"{month_key}.csv")
        out_df.to_csv(out_path, index=False)

    # Combine yearly
    all_months = [
        pd.read_csv(os.path.join(output_folder, f))
        for f in sorted(os.listdir(output_folder))
        if f.endswith('.csv') and re.match(r'\d{4}-\d{2}\.csv', f)
    ]
    if all_months:
        combined_df = pd.concat(all_months, ignore_index=True)
        combined_path = os.path.join(output_folder, f"{year}_combined.csv")
        combined_df.to_csv(combined_path, index=False)
        print(f"[✅] {year}_combined.csv has been created")
