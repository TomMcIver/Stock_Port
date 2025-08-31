import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

class DataService:
    @staticmethod
    def get_stock_data(tickers, start_date, end_date, interval='1d'):
        data = {}
        
        # hardcoded data for aple
        aapl_data = {
            'Close': [180.0, 182.5, 179.8, 185.2, 183.7],
            'Volume': [50000000, 45000000, 52000000, 48000000, 51000000]
        }
        
        msft_data = {
            'Close': [350.0, 355.3, 348.9, 360.1, 358.4],
            'Volume': [30000000, 28000000, 32000000, 29000000, 31000000]
        }
        
        dates = pd.date_range(end=datetime.now(), periods=5, freq='D')
        
        if 'AAPL' in tickers:
            data['AAPL'] = pd.DataFrame(aapl_data, index=dates)
        
        if 'MSFT' in tickers:
            data['MSFT'] = pd.DataFrame(msft_data, index=dates)
        
        return data
    
    @staticmethod
    def get_stock_info(ticker):
        if ticker == 'AAPL':
            return {'longName': 'Apple Inc.', 'sector': 'Technology'}
        elif ticker == 'MSFT':
            return {'longName': 'Microsoft Corporation', 'sector': 'Technology'}
        else:
            return {'longName': f'{ticker} Corp.', 'sector': 'Unknown'}
    
    @staticmethod
    def calculate_returns(price_data):
        if isinstance(price_data, dict):
            returns = {}
            for ticker, df in price_data.items():
                if 'Close' in df.columns:
                    returns[ticker] = df['Close'].pct_change().dropna()
            return returns
        else:
            if 'Close' in price_data.columns:
                return price_data['Close'].pct_change().dropna()
            return pd.Series()
    
    @staticmethod
    def calculate_portfolio_metrics(returns, weights=None):
        if isinstance(returns, dict):
            returns_df = pd.DataFrame(returns)
        else:
            returns_df = returns
        
        if returns_df.empty:
            return {}
        
        if weights is None:
            weights = np.ones(len(returns_df.columns)) / len(returns_df.columns)
        
        portfolio_returns = (returns_df * weights).sum(axis=1)
        
        cumulative_returns = (1 + portfolio_returns).cumprod()
        total_return = cumulative_returns.iloc[-1] - 1
        
        annualized_return = (1 + total_return) ** (252 / len(portfolio_returns)) - 1
        volatility = portfolio_returns.std() * np.sqrt(252)
        sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
        
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = drawdown.min()
        
        downside_returns = portfolio_returns[portfolio_returns < 0]
        downside_std = downside_returns.std() * np.sqrt(252)
        sortino_ratio = annualized_return / downside_std if downside_std > 0 else 0
        
        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'max_drawdown': max_drawdown,
            'portfolio_returns': portfolio_returns,
            'cumulative_returns': cumulative_returns,
            'drawdown': drawdown
        }