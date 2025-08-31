import streamlit as st
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(
    page_title="Stock Portfolio Manager",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

def initialize_session_state():
    if 'selected_tickers' not in st.session_state:
        st.session_state.selected_tickers = ['AAPL', 'MSFT']

def create_sidebar():
    with st.sidebar:
        st.title("📊 Stocks")
        
        st.write("**Available Stocks:**")
        st.write("• AAPL - Apple Inc.")
        st.write("• MSFT - Microsoft Corp.")
        
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

def main():
    initialize_session_state()
    create_sidebar()
    
    st.markdown("""
    <style>
        .stDeployButton {display:none;}
        footer {visibility: hidden;}
        .stDecoration {display:none;}
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)
    
    st.title("📈 Stock Portfolio Manager")
    st.markdown("---")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Dashboard", 
        "Data", 
        "News",
        "Model",
        "Trading"
    ])
    
    with tab1:
        st.header("📊 Dashboard")
        from pages import dashboard
        dashboard.render()
    
    with tab2:
        st.header("📂 Data")
        from pages import data
        data.render()
    
    with tab3:
        st.header("📰 News")
        from pages import news
        news.render()
    
    with tab4:
        st.header("🤖 Model")
        from pages import model
        model.render()
    
    with tab5:
        st.header("💹 Trading")
        from pages import trading
        trading.render()

if __name__ == "__main__":
    main()