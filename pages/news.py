import streamlit as st
from services.news_service import NewsService

def render():
    st.write("Latest news articles:")
    
    news_df = NewsService.get_news_data(['AAPL', 'MSFT'])
    
    if news_df.empty:
        st.info("No news articles available.")
        return
    
    # show each news artical
    for idx, row in news_df.iterrows():
        with st.expander(f"[{row['ticker']}] {row['title']}"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**Publisher:** {row['publisher']}")
                st.write(f"**Published:** {row['published'].strftime('%Y-%m-%d')}")
            
            with col2:
                sentiment_label = "Positive" if row['sentiment'] > 0.6 else "Negative" if row['sentiment'] < 0.4 else "Neutral"
                st.write(f"**Sentiment:** {sentiment_label}")
            
            st.write(row['summary'])