import streamlit as st
import pandas as pd
from services.data_service import DataService

def render():
    st.write("Available stocks: AAPL and MSFT")
    
    tickers = ['AAPL', 'MSFT']
    data = DataService.get_stock_data(tickers, None, None)
    
    if data:
        st.write("### Stock Information")
        
        # show info for each stok
        for ticker in tickers:
            info = DataService.get_stock_info(ticker)
            st.write(f"**{ticker}** - {info['longName']} ({info['sector']})")
        
        st.write("### Current Data Status")
        status_data = []
        
        for ticker in tickers:
            if ticker in data:
                df = data[ticker]
                latest_price = df['Close'].iloc[-1]
                data_points = len(df)
                
                status_data.append({
                    'Ticker': ticker,
                    'Latest Price': f"${latest_price:.2f}",
                    'Data Points': data_points,
                    'Status': '✅ OK'
                })
        
        if status_data:
            status_df = pd.DataFrame(status_data)
            st.dataframe(status_df, use_container_width=True)
    else:
        st.error("No data available")