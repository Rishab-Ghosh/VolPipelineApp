# VolPipelineStreamlit

A comprehensive financial volatility analysis pipeline built with Streamlit for processing, visualizing, and analyzing implied volatility surfaces, time series data, and daily volatility shocks.

## 🌟 Features

### **Data Processing**
- **Multi-format input**: Support for ZIP uploads and local folder paths
- **Flexible data filtering**: Filter by curve, year, month, and date ranges
- **Separate pipelines**: Surface data and EWMA/historical data processing
- **Automatic data validation**: Robust CSV reading with error handling

### **Volatility Analysis**
- **Implied Volatility Surfaces**: 3D surface plots with interactive visualization
- **Time Series Analysis**: Rolling window smoothing with customizable periods
- **Daily Volatility Shocks**: Daily change analysis and visualization
- **EWMA Processing**: Exponential weighted moving average calculations

### **Interactive Visualizations**
- **Plotly Charts**: Interactive 3D surfaces and time series plots
- **Dropdown Selection**: Choose specific months/periods for analysis
- **Real-time Updates**: Dynamic chart generation based on user selections

### **Export Capabilities**
- **Excel Export**: Structured data in multiple sheets
- **PNG Images**: High-quality static plots
- **ZIP Downloads**: Organized package downloads
- **Combined Exports**: Multiple formats in single download


### **Prerequisites**
```bash
Python 3.8+
pip install -r requirements.txt
```

### **Installation**
1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/VolPipelineStreamlit.git
   cd VolPipelineStreamlit
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   streamlit run app.py
   ```

## Project Structure

```
VolPipelineStreamlit/
├── app.py                          # Main Streamlit application
├── modules/
│   ├── curve_filter.py             # Data filtering and processing
│   ├── volatility_surface.py       # Implied volatility surface generation
│   ├── time_series_plotter.py      # Time series and daily shock analysis
│   └── vol_extractor.py            # Data extraction utilities
├── .streamlit/
│   └── config.toml                 # Streamlit configuration
├── requirements.txt                # Python dependencies
├── README.md                       # Project documentation
└── .gitignore                      # Git ignore rules
```

## 🔧 Usage

### **Step 1: Filter & Download Data**
- Select curve name (NYMEX, HSC, etc.)
- Choose year and optional month
- Upload ZIP file or provide local folder path
- Filter surface data and EWMA data separately
- Download filtered data as ZIP files

### **Step 2: Upload Filtered Data**
- Upload surface data ZIP for implied volatility analysis
- Upload EWMA data ZIP for time series analysis
- Data is automatically extracted and prepared

### **Step 3: Visualize & Download**
- Select outputs to generate (Surface, Time Series, Daily Shock)
- Configure rolling window parameters
- Run pipeline with progress tracking
- View results and download exports

### **Step 4: Interactive Charts**
- Explore implied volatility surfaces with 3D visualization
- Analyze time series with rolling averages
- Examine daily volatility shocks
- Use dropdowns to select specific periods

### **Step 5: Download Results**
- Choose outputs to download
- Select format (Excel, PNG, or Both)
- Download organized ZIP packages

## Supported Curves

- NYMEX
- HSC
- TGP - 500
- TRANSCO 65
- FGT - Z3
- CG MAINLINE
- NGPL - TxOk
- NGPL - MIDCON
- PEPL
- VENTURA
- DEMARC
- CHICAGO
- MICHCON
- DOMINION
- TCO
- TETCO - M3
- TRANSCO Z6
- ALGONQUIN
- EP PERMIAN
- EP SAN JUAN
- WAHA
- ROCKIES
- CIG
- PG&E CITYGATE
- SOCAL
- AECO

## Config

### **Streamlit Configuration**
The app is configured for large file uploads (up to 1GB) in `.streamlit/config.toml`:

```toml
[server]
maxUploadSize = 1024

[theme]
primaryColor = "#F63366"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
```

### **Data Requirements**
- **CSV files** with columns: Basis, Type, Call/Put, Mid, date/Curve_Date
- **File naming**: YYYYMMDD format for date extraction
- **Data structure**: Compatible with implied volatility surface calculations

### **Implied Volatility Surface**
- 3D surface visualization using Plotly
- Moneyness conversion for Call/Put options
- Monthly and yearly surface generation
- Interactive camera controls and zoom

### **Time Series Analysis**
- Rolling window smoothing (5-60 days)
- Original vs smoothed data comparison
- Daily change calculations
- Consolidated data processing

### **Daily Volatility Shocks**
- Daily volatility change analysis
- Rolling average-based calculations
- Shock visualization and identification
- Trend analysis capabilities

## Stack

- Built with [Streamlit](https://streamlit.io/) for web application framework
- Data visualization powered by [Plotly](https://plotly.com/)
- Financial data processing with [Pandas](https://pandas.pydata.org/)
- Mathematical computations with [NumPy](https://numpy.org/)

---

**Note**: This application is designed for financial data analysis and should be used in accordance with your organization's data handling policies and regulatory requirements. 
