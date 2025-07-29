import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

def robust_read_csv(filepath):
    """Robust CSV reading with error handling."""
    try:
        if os.path.getsize(filepath) < 10:  # Skip very small files
            print(f"[WARN] File too small, skipping: {filepath}")
            return None
        df = pd.read_csv(filepath, encoding='utf-8', on_bad_lines='skip')
        if df.empty:
            print(f"[WARN] Empty DataFrame from: {filepath}")
            return None
        return df
    except Exception as e:
        print(f"[ERROR] Failed to read {filepath}: {str(e)}")
        return None

def generate_vol_surfaces(data_folder, output_folder, target_curve, target_month=None, date_range=None, start_date=None, end_date=None):
    os.makedirs(output_folder, exist_ok=True)

    type_to_moneyness = {
        'ATM - $1.00': -1.00, 'ATM - $0.75': -0.75, 'ATM - $0.50': -0.50,
        'ATM - $0.25': -0.25, 'ATM': 0.00,
        'ATM + $0.25': 0.25, 'ATM + $0.50': 0.50, 'ATM + $0.75': 0.75,
        'ATM + $1.00': 1.00, 'ATM + $1.25': 1.25, 'ATM + $1.50': 1.50,
        'ATM + $1.75': 1.75, 'ATM + $2.00': 2.00
    }

    # === Load Data ===
    all_data = []
    for file in os.listdir(data_folder):
        if file.endswith('.csv') and (not target_month or target_month in file):
            df = robust_read_csv(os.path.join(data_folder, file))
            if df is None:
                print(f"[WARN] Skipping file due to read error: {file}")
                continue
                
            df.columns = df.columns.str.strip().str.replace('\u200b', '')
            df['Moneyness'] = df['Type'].map(type_to_moneyness)
            df['Mid'] = pd.to_numeric(df['Mid'], errors='coerce')
            
            # Handle date column - check if 'date' exists, otherwise use 'Curve_Date'
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
            elif 'Curve_Date' in df.columns:
                df['date'] = pd.to_datetime(df['Curve_Date'], errors='coerce')
            else:
                print(f"[WARN] No date column found in {file}. Available columns: {list(df.columns)}")
                continue
                
            df['month'] = df['date'].dt.to_period('M').astype(str)
            all_data.append(df)

    if not all_data:
        print("[WARN] No data loaded for surface generation.")
        return

    df_all = pd.concat(all_data, ignore_index=True)
    df_all['year'] = df_all['date'].dt.year.astype(str)

    # === Filter by date_range or start_date/end_date if provided ===
    if date_range is not None and len(date_range) == 2:
        start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
        df_all = df_all[(df_all['date'] >= start_date) & (df_all['date'] <= end_date)]
    elif start_date and end_date:
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        df_all = df_all[(df_all['date'] >= start_date) & (df_all['date'] <= end_date)]

    # === Monthly Surfaces ===
    for month in df_all['month'].unique():
        df_m = df_all[(df_all['Basis'] == target_curve) & (df_all['month'] == month)]
        if df_m.empty:
            continue

        pivot = df_m.pivot_table(index='date', columns='Moneyness', values='Mid', aggfunc='mean').dropna(axis=1, how='all')
        if pivot.empty:
            continue

        pivot_reset = pivot.reset_index()
        pivot_reset['date_ordinal'] = pivot_reset['date'].map(pd.Timestamp.toordinal)

        X, Y = np.meshgrid(pivot.columns.values, pivot_reset['date_ordinal'].values)
        Z = np.array(pivot.values, dtype=np.float64)

        fig = plt.figure(figsize=(10, 7))
        ax = fig.add_subplot(111, projection='3d')
        ax.plot_surface(X, Y, Z, cmap='viridis', edgecolor='k')

        ax.set_title(f'Volatility Surface - {target_curve} - {month}')
        ax.set_xlabel('Moneyness')
        ax.set_ylabel('Date (ordinal)')
        ax.set_zlabel('Implied Volatility')

        safe_curve = target_curve.replace(' ', '_')
        fname = f"{safe_curve}_{month}_surface"
        plt.savefig(os.path.join(output_folder, f'{fname}.png'))
        plt.close()
        pivot.to_csv(os.path.join(output_folder, f'{fname}_data.csv'))

    # === Yearly Surfaces ===
    for year in df_all['year'].unique():
        df_y = df_all[(df_all['Basis'] == target_curve) & (df_all['year'] == year)]
        if df_y.empty:
            continue

        pivot = df_y.pivot_table(index='date', columns='Moneyness', values='Mid', aggfunc='mean').dropna(axis=1, how='all')
        if pivot.empty:
            continue

        pivot_reset = pivot.reset_index()
        pivot_reset['date_ordinal'] = pivot_reset['date'].map(pd.Timestamp.toordinal)

        X, Y = np.meshgrid(pivot.columns.values, pivot_reset['date_ordinal'].values)
        Z = np.array(pivot.values, dtype=np.float64)

        fig = plt.figure(figsize=(10, 7))
        ax = fig.add_subplot(111, projection='3d')
        ax.plot_surface(X, Y, Z, cmap='viridis', edgecolor='k')

        ax.set_title(f'Yearly Volatility Surface - {target_curve} - {year}')
        ax.set_xlabel('Moneyness')
        ax.set_ylabel('Date (ordinal)')
        ax.set_zlabel('Implied Volatility')

        fname = f"{target_curve.replace(' ', '_')}_{year}_YEARLY_surface"
        plt.savefig(os.path.join(output_folder, f'{fname}.png'))
        plt.close()
        pivot.to_csv(os.path.join(output_folder, f'{fname}_data.csv'))

    print("[✅] Volatility surface plots saved.")
