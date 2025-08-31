# Stock Portfolio Manager 📈

A comprehensive Streamlit-based desktop application for stock portfolio management, analysis, and backtesting.

## Features

### 📊 Dashboard
- Real-time portfolio equity curve and drawdown analysis
- Key performance metrics (Sharpe Ratio, Sortino Ratio, Max Drawdown, CAGR)
- Current holdings overview with portfolio allocation
- Top/bottom contributors analysis

### 📂 Data Management
- Ticker list CRUD operations with validation
- Automated data backfilling from Yahoo Finance
- Data quality monitoring and status logs
- Coverage and health metrics

### 📰 News & Sentiment
- Latest financial news aggregation per ticker
- Sentiment analysis and trending
- News volume analytics by ticker and time
- Topic extraction and tagging

### 🤖 ML Model
- Feature engineering for technical indicators
- Random Forest and Logistic Regression models
- Cross-validation and performance metrics
- Feature importance analysis and confusion matrices

### 💹 Backtest/Trade
- Strategy backtesting with transaction costs
- Paper trading simulation mode
- Performance comparison vs buy-and-hold
- Detailed trade analysis and export capabilities

## Quick Start

### Option 1: Using the run script
```bash
python run.py
```

### Option 2: Manual installation
```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run app.py
```

The application will be available at http://localhost:8501

## Architecture

```
Stock_Port/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── run.py                # Startup script
├── pages/                # Individual page modules
│   ├── dashboard.py      # Portfolio dashboard
│   ├── data.py          # Data management
│   ├── news.py          # News and sentiment
│   ├── model.py         # ML model training
│   └── backtest.py      # Backtesting and trading
├── services/            # Business logic services
│   ├── data_service.py  # Data fetching and processing
│   ├── news_service.py  # News aggregation and sentiment
│   ├── ml_service.py    # Machine learning pipeline
│   └── backtest_service.py # Strategy backtesting
└── utils/               # Utility modules
    └── state.py         # Session state management
```

## Global Controls

The application features a persistent sidebar with:
- **Portfolio Selector**: Switch between different portfolio configurations
- **Date Range**: Adjust analysis timeframe
- **Ticker Selection**: Multi-select dropdown for stocks
- **Data Interval**: Choose between daily, weekly, monthly data
- **Refresh Button**: Clear cache and reload data

## Usage Workflow

1. **Data Setup**: Start by adding tickers in the Data tab and backfilling historical data
2. **Portfolio Analysis**: View performance metrics and charts in the Dashboard
3. **News Monitoring**: Track sentiment and news flow in the News tab
4. **Model Training**: Create ML models for prediction in the Model tab
5. **Strategy Testing**: Backtest strategies and analyze performance in Backtest/Trade

## Technical Details

- **Frontend**: Streamlit with Plotly/Altair for interactive charts
- **Data Source**: Mock data generation (ready for API integration)
- **ML Framework**: scikit-learn for model training and evaluation
- **State Management**: Streamlit session state for shared data
- **Caching**: Built-in Streamlit caching for performance optimization

## Future Enhancements

- **Data Integration**: Add Yahoo Finance, Alpha Vantage, or other market data APIs
- Electron/Tauri wrapper for native desktop experience
- Real-time data streaming
- Additional ML models (XGBoost, Neural Networks)
- Portfolio optimization algorithms
- Risk management tools
- Export to Excel/PDF reports

## Requirements

- Python 3.8+
- Modern web browser

## Development

The application is designed with modularity in mind:
- Each page is self-contained in the `pages/` directory
- Business logic is separated into `services/` modules
- Shared utilities are in `utils/`
- Easy to extend with new features and pages

For development, run the app with:
```bash
streamlit run app.py --logger.level=debug
```