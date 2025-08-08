import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def build_vol_time_series(input_folder, iv_surface_folder, output_folder, curve_name, month=None, rolling_window=21, start_date=None, end_date=None):
    """
    Build volatility time series using the simple and elegant approach from the working code.
    """
    os.makedirs(output_folder, exist_ok=True)
    
    # === STEP 1: Collect and combine all data ===
    all_data = []

    for root, _, files in os.walk(input_folder):
        for file in files:
            if not file.endswith(".csv"):
                continue
            
            # Skip if month filter is specified and file doesn't match
            if month and month not in file:
                continue

            file_path = os.path.join(root, file)
            
            try:
                # Read CSV file
                df = pd.read_csv(file_path, encoding='utf-8', on_bad_lines='skip')
                if df.empty:
                    continue
                
                # Clean column names
                df.columns = df.columns.str.strip().str.replace('\u200b', '')
                
                # Parse and clean dates
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'], errors='coerce')
                elif 'Curve_Date' in df.columns:
                    df['date'] = pd.to_datetime(df['Curve_Date'], errors='coerce')
                else:
                    continue

                # Apply date filtering if specified
                if start_date and end_date:
                    start = pd.to_datetime(start_date)
                    end = pd.to_datetime(end_date)
                    df = df[(df['date'] >= start) & (df['date'] <= end)]
                
                # Convert Mid to numeric
                df['Mid'] = pd.to_numeric(df['Mid'], errors='coerce')
                df = df.dropna(subset=['Mid'])
                
                if not df.empty:
                    all_data.append(df)
                    
            except Exception as e:
                print(f"Error processing {file}: {str(e)}")
                continue
    
    if not all_data:
        print("No valid data found to process")
        return True
    
    # === STEP 2: Combine all data ===
    combined_df = pd.concat(all_data, ignore_index=True)
    combined_df = combined_df.sort_values('date')
    
    # Get curve name
    curve = combined_df['Basis'].iloc[0] if 'Basis' in combined_df.columns else curve_name
    
    # === STEP 3: Create consolidated pivot table ===
    if 'Contract_Month' in combined_df.columns:
        # Surface data structure
        pivot = combined_df.pivot_table(
            index='date',
            columns='Contract_Month',
            values='Mid',
            aggfunc='mean'
        ).sort_index()
    else:
        # EWMA data structure - just group by date
        pivot = combined_df.groupby('date')['Mid'].mean().to_frame().sort_index()
        pivot.columns = ['EWMA_Volatility']
    
    # === STEP 4: Compute rolling average and daily change ===
    # Adjust min_periods based on data size and rolling window
    min_periods = min(rolling_window, len(pivot), 10)
    rolling = pivot.rolling(window=rolling_window, min_periods=min_periods).mean()
    daily_change = rolling.diff()

    # Debug: Print rolling window info
    print(f"Applied {rolling_window}-day rolling window to {len(pivot)} data points")
    print(f"Rolling average range: {rolling.min().iloc[0]:.4f} to {rolling.max().iloc[0]:.4f}")
    print(f"Original data range: {pivot.min().iloc[0]:.4f} to {pivot.max().iloc[0]:.4f}")
    
    # === STEP 5: Save consolidated Excel file ===
    period_label = month if month else f"{curve_name}_combined"
    output_file = os.path.join(output_folder, f"{curve}_{period_label}_time_series.xlsx")

    with pd.ExcelWriter(output_file) as writer:
        pivot.to_excel(writer, sheet_name="Original_TS")
        rolling.to_excel(writer, sheet_name=f"Rolling_{rolling_window}D")
        daily_change.to_excel(writer, sheet_name="Daily_Change")

    # === STEP 6: Create consolidated plots ===
    if 'Contract_Month' not in combined_df.columns:
        # EWMA data - create one consolidated plot
        fig, axs = plt.subplots(2, 1, figsize=(15, 10), sharex=True)
        
        # Plot 1: Original + Rolling (smoothed)
        axs[0].plot(pivot.index, pivot['EWMA_Volatility'], label='Original EWMA', alpha=0.7, linewidth=1, color='gray')
        axs[0].plot(rolling.index, rolling['EWMA_Volatility'], label=f'{rolling_window}D Rolling Avg', color='blue', linewidth=3)
        axs[0].set_ylabel("Volatility")
        axs[0].set_title(f"EWMA Volatility - {period_label} ({rolling_window}-day smoothing)")
        axs[0].legend()
        axs[0].grid(True, alpha=0.3)
        
        # Plot 2: Daily Change (from rolling average)
        axs[1].plot(daily_change.index, daily_change['EWMA_Volatility'], label='Daily ΔVol', color='red', linewidth=1)
        axs[1].set_ylabel("Δ Volatility")
        axs[1].legend()
        axs[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plot_path = os.path.join(output_folder, f"{curve}_{period_label}_timeseries_rolling.png")
        plt.savefig(plot_path, dpi=150, bbox_inches='tight')
        plt.close()

        # Create consolidated daily change plot
        fig, ax = plt.subplots(figsize=(15, 6))
        ax.plot(daily_change.index, daily_change['EWMA_Volatility'], label='Daily ΔVol', color='red', linewidth=1)
        ax.set_ylabel("Δ Volatility")
        ax.set_title(f"Daily Volatility Shocks - {period_label}")
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        daily_plot_path = os.path.join(output_folder, f"{curve}_{period_label}_dailychange.png")
        plt.savefig(daily_plot_path, dpi=150, bbox_inches='tight')
        plt.close()
        
    else:
        # Surface data - process all contract months
        contract_months = pivot.columns  # Process all months, not just first 3
        
        for contract_month in contract_months:
            # Create matplotlib plots
            fig, axs = plt.subplots(3, 1, figsize=(12, 12), sharex=True)
            
            # Plot 1: Original + Rolling
            axs[0].plot(pivot.index, pivot[contract_month], label='Original', alpha=0.5, linewidth=1)
            axs[0].plot(rolling.index, rolling[contract_month], label=f'{rolling_window}D Rolling Avg', color='blue', linewidth=2)
            axs[0].set_ylabel("Volatility")
            axs[0].legend()
            axs[0].grid(True, alpha=0.3)
            
            # Plot 2: Daily Change
            axs[1].plot(daily_change.index, daily_change[contract_month], label='Daily ΔVol', color='red', linewidth=1)
            axs[1].set_ylabel("Δ Volatility")
            axs[1].legend()
            axs[1].grid(True, alpha=0.3)
            
            # Plot 3: Title / IV Image Placeholder
            if pd.notnull(contract_month):
                try:
                    # Handle both datetime and string contract_month
                    if hasattr(contract_month, 'strftime'):
                        month_str = contract_month.strftime('%Y-%m')
                    else:
                        month_str = str(contract_month)
                    iv_img_path = os.path.join(iv_surface_folder, f"{month_str}.png")
                    title = f"Vol Comparison for {month_str}"
                    if os.path.exists(iv_img_path):
                        title += " (IV image found)"
                except Exception as e:
                    month_str = str(contract_month)
                    title = f"Vol Comparison for {month_str}"
            else:
                month_str = "Unknown"
                title = "Vol Comparison (No contract month)"
            
            axs[2].set_title(title)
            axs[2].axis('off')  # Placeholder for IV image space
            
            plt.tight_layout()
            plot_path = os.path.join(output_folder, f"{curve}_{period_label}_{month_str}_timeseries_rolling.png")
            plt.savefig(plot_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            # Create daily change plot
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.plot(daily_change.index, daily_change[contract_month], label='Daily ΔVol', color='red', linewidth=1)
            ax.set_ylabel("Δ Volatility")
            ax.set_title(f"Daily Volatility Shocks - {month_str}")
            ax.legend()
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            daily_plot_path = os.path.join(output_folder, f"{curve}_{period_label}_{month_str}_dailychange.png")
            plt.savefig(daily_plot_path, dpi=150, bbox_inches='tight')
            plt.close()
    
    print(f"Time series processing complete for {curve_name} - Created consolidated plots for {period_label}")
    return True
