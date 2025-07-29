import os
import re
import pandas as pd

def robust_read_csv(filepath):
    try:
        return pd.read_csv(filepath, sep=',', encoding='utf-8-sig')
    except Exception as e1:
        try:
            return pd.read_csv(filepath, sep=',', encoding='utf-16')
        except Exception as e2:
            print(f"Failed to read {filepath}: {e1} / {e2}")
            return None

def filter_vol_data(input_folder, output_folder, year, basis_filter, type_filter=None, callput_filter=None, suffix="", month=None, start_date=None, end_date=None):
    os.makedirs(output_folder, exist_ok=True)
    file_dict = {}
    
    for root, _, files in os.walk(input_folder):
        for file in files:
            if not file.endswith('.csv'):
                continue
            full_path = os.path.join(root, file)
            df = robust_read_csv(full_path)
            if df is None:
                print(f"[WARN] Skipping file due to read error: {full_path}")
                continue
            df.columns = df.columns.str.strip().str.replace('\u200b', '')
            df['Basis'] = df['Basis'].astype(str).str.strip()
            df['Type'] = df['Type'].astype(str).str.strip().str.upper()
            df['Call/Put'] = df.get('Call/Put', '').astype(str).str.strip().str.upper()
            if 'Curve_Date' not in df.columns:
                continue
            df['Curve_Date'] = pd.to_datetime(df['Curve_Date'], errors='coerce')
            df = df[df['Curve_Date'].notnull()]
            df['year'] = df['Curve_Date'].dt.year.astype(str)
            df['month'] = df['Curve_Date'].dt.month.apply(lambda x: f"{x:02d}")
            df['date'] = df['Curve_Date']
            # Filter for basis, year/date range, and (if specified) month
            mask = (
                df['Basis'].str.upper().isin([c.upper() for c in basis_filter])
            )
            if type_filter:
                mask &= df['Type'] == type_filter.upper()
            if callput_filter:
                mask &= df['Call/Put'] == callput_filter.upper()
            if start_date and end_date:
                mask &= (df['Curve_Date'] >= pd.to_datetime(start_date)) & (df['Curve_Date'] <= pd.to_datetime(end_date))
            else:
                mask &= (df['year'] == year)
            if month:
                mask &= df['month'] == month
            filtered = df[mask]
            
            # Group by year-month
            for ym, group in filtered.groupby(['year', 'month']):
                month_key = f"{ym[0]}-{ym[1]}"
                if month and ym[1] != month:
                    continue
                if month_key not in file_dict:
                    file_dict[month_key] = []
                file_dict[month_key].append(group)

    for month_key, groups in file_dict.items():
        print(f"[INFO] Processing {month_key} for EWMA/HIST...")
        out_df = pd.concat(groups, ignore_index=True)
        # Create files with the pattern: {curve}_{month}_ewma_hist.csv
        curve_name = basis_filter[0] if basis_filter else "UNKNOWN"
        month_num = month_key.split('-')[1]  # Extract month number (e.g., "02" from "2024-02")
        out_path = os.path.join(output_folder, f"{curve_name}_{month_num}_ewma_hist.csv")
        out_df.to_csv(out_path, index=False)

    # Combine yearly
    all_months = [
        robust_read_csv(os.path.join(output_folder, f))
        for f in sorted(os.listdir(output_folder))
        if f.endswith("_ewma_hist.csv")
    ]
    all_months = [df for df in all_months if df is not None]
    if all_months:
        combined_df = pd.concat(all_months, ignore_index=True)
        curve_name = basis_filter[0] if basis_filter else "UNKNOWN"
        combined_path = os.path.join(output_folder, f"{curve_name}_{year}_ewma_hist_combined.csv")
        combined_df.to_csv(combined_path, index=False)
        print(f"[✅] {curve_name}_{year}_ewma_hist_combined.csv has been created")

