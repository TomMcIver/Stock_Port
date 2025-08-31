import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

class NewsService:
    @staticmethod
    def get_news_data(tickers, days_back=7):
        # just two news articals hardcoded
        all_news = [
            {
                'ticker': 'AAPL',
                'title': 'Apple Reports Strong Q3 Earnings',
                'publisher': 'MarketWatch',
                'published': datetime.now() - timedelta(days=1),
                'url': 'https://example.com/apple-earnings',
                'sentiment': 0.7,
                'summary': 'Apple exceeded expectations with strong iPhone sales and services growth.'
            },
            {
                'ticker': 'MSFT',
                'title': 'Microsoft Cloud Revenue Grows 25%',
                'publisher': 'Bloomberg',
                'published': datetime.now() - timedelta(days=2),
                'url': 'https://example.com/microsoft-cloud',
                'sentiment': 0.8,
                'summary': 'Microsoft Azure and cloud services continue showing strong growth momentum.'
            }
        ]
        
        return pd.DataFrame(all_news)
    
    @staticmethod
    def _analyze_sentiment_simple(text):
        positive_words = ['gain', 'up', 'rise', 'bull', 'positive', 'growth', 'profit', 'strong', 'beat', 'outperform']
        negative_words = ['loss', 'down', 'fall', 'bear', 'negative', 'decline', 'drop', 'weak', 'miss', 'underperform']
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return 0.7
        elif negative_count > positive_count:
            return 0.3
        else:
            return 0.5
    
    @staticmethod
    def get_sentiment_trend(news_df, ticker=None):
        if news_df.empty:
            return pd.DataFrame()
        
        df = news_df.copy()
        if ticker:
            df = df[df['ticker'] == ticker]
        
        df['date'] = pd.to_datetime(df['published']).dt.date
        sentiment_trend = df.groupby(['ticker', 'date'])['sentiment'].mean().reset_index()
        
        return sentiment_trend
    
    @staticmethod
    def extract_topics(news_df, n_topics=5):
        if news_df.empty:
            return []
        
        all_titles = ' '.join(news_df['title'].astype(str))
        
        common_topics = ['earnings', 'acquisition', 'partnership', 'regulation', 'product', 'market', 'revenue', 'growth']
        
        topics = []
        for topic in common_topics:
            if topic in all_titles.lower():
                count = all_titles.lower().count(topic)
                topics.append({'topic': topic, 'frequency': count})
        
        return sorted(topics, key=lambda x: x['frequency'], reverse=True)[:n_topics]