import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from services.data_service import DataService

def render():
    tickers = ['AAPL', 'MSFT']
    
    price_data = DataService.get_stock_data(tickers, None, None)
    
    if not price_data:
        st.error("No data available.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        if 'AAPL' in price_data:
            current_price = price_data['AAPL']['Close'].iloc[-1]
            st.metric("AAPL Price", f"${current_price:.2f}")
    
    with col2:
        if 'MSFT' in price_data:
            current_price = price_data['MSFT']['Close'].iloc[-1]
            st.metric("MSFT Price", f"${current_price:.2f}")
    
    st.subheader("Stock Prices")
    
    fig = go.Figure()
    
    # add both stocks to chart
    for ticker in tickers:
        if ticker in price_data:
            df = price_data[ticker]
            fig.add_trace(go.Scatter(
                x=df.index,
                y=df['Close'],
                mode='lines',
                name=ticker,
                line=dict(width=2)
            ))
    
    fig.update_layout(
        title="Stock Price Chart",
        xaxis_title="Date",
        yaxis_title="Price ($)",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("Stock Data")
    
    # show data tables for each stok
    for ticker in tickers:
        if ticker in price_data:
            st.write(f"**{ticker}**")
            st.dataframe(price_data[ticker], use_container_width=True)