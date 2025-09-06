"""duckdb database initialization and utilities"""

import duckdb
import pandas as pd
from pathlib import Path
import os
from typing import Optional, Dict, Any, List
import json
from datetime import datetime

# database configuration
BASE_DIR = Path(__file__).parent.parent.parent
DATABASE_PATH = BASE_DIR / "data" / "stock_port.db"
PARQUET_DIR = BASE_DIR / "data" / "parquet"

# ensure data directories exist
DATABASE_PATH.parent.mkdir(exist_ok=True)
PARQUET_DIR.mkdir(parents=True, exist_ok=True)

class DuckDBManager:
    """duckdb connection and operations manager"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(DATABASE_PATH)
        self.parquet_dir = PARQUET_DIR
    
    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """get duckdb connection"""
        return duckdb.connect(self.db_path)
    
    def execute_query(self, query: str, params: Optional[Dict] = None) -> pd.DataFrame:
        """execute query and return results as dataframe"""
        with self.get_connection() as conn:
            if params:
                # convert dict params to list for duckdb
                if isinstance(params, dict):
                    # for simple named parameters, extract values in order
                    param_values = list(params.values())
                    return conn.execute(query, param_values).df()
                return conn.execute(query, params).df()
            return conn.execute(query).df()
    
    def insert_dataframe(self, df: pd.DataFrame, table_name: str, mode: str = 'append'):
        """insert dataframe to table"""
        with self.get_connection() as conn:
            if mode == 'replace':
                conn.execute(f"DELETE FROM {table_name}")
            
            # insert data directly into duckdb table
            conn.register('temp_df', df)
            conn.execute(f"INSERT INTO {table_name} SELECT * FROM temp_df")
            conn.unregister('temp_df')

# global database manager instance
db_manager = DuckDBManager()

def create_tables():
    """create all database tables and schemas"""
    with db_manager.get_connection() as conn:
        # news articles table
        conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS news_articles_id_seq;
            CREATE TABLE IF NOT EXISTS news_articles (
                id INTEGER PRIMARY KEY DEFAULT nextval('news_articles_id_seq'),
                url TEXT UNIQUE NOT NULL,
                url_hash TEXT,
                source TEXT,
                domain TEXT,
                ts_published TIMESTAMP,
                ts_crawled TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ts_processed TIMESTAMP,
                title TEXT,
                text TEXT,
                language TEXT,
                extraction_method TEXT,
                is_processed BOOLEAN DEFAULT FALSE,
                has_embeddings BOOLEAN DEFAULT FALSE,
                has_sentiment BOOLEAN DEFAULT FALSE,
                text_quality_score FLOAT,
                relevance_score FLOAT,
                metadata TEXT
            )
        """)
        
        # ticker symbols table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ticker_symbols (
                id INTEGER PRIMARY KEY,
                symbol TEXT UNIQUE NOT NULL,
                company_name TEXT,
                aliases TEXT,
                sector TEXT,
                market_cap TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # article-ticker associations
        conn.execute("""
            CREATE TABLE IF NOT EXISTS article_ticker_associations (
                id INTEGER PRIMARY KEY,
                article_id INTEGER,
                ticker_id INTEGER,
                confidence FLOAT,
                match_method TEXT,
                context_snippet TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # news embeddings
        conn.execute("""
            CREATE TABLE IF NOT EXISTS news_embeddings (
                id INTEGER PRIMARY KEY,
                article_id INTEGER,
                model_name TEXT,
                embedding_type TEXT,
                vector TEXT,
                dimension INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # article sentiments
        conn.execute("""
            CREATE TABLE IF NOT EXISTS article_sentiments (
                id INTEGER PRIMARY KEY,
                article_id INTEGER,
                ticker_id INTEGER,
                sentiment_type TEXT,
                positive FLOAT,
                negative FLOAT,
                neutral FLOAT,
                compound FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # crawl jobs tracking
        conn.execute("""
            CREATE TABLE IF NOT EXISTS crawl_jobs (
                id INTEGER PRIMARY KEY,
                job_type TEXT,
                status TEXT,
                ts_started TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ts_completed TIMESTAMP,
                articles_crawled INTEGER DEFAULT 0,
                articles_processed INTEGER DEFAULT 0,
                errors TEXT,
                metadata TEXT
            )
        """)
        
        # daily ticker sentiment aggregates
        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_ticker_sentiment (
                id INTEGER PRIMARY KEY,
                ticker_id INTEGER,
                date DATE,
                article_count INTEGER,
                avg_sentiment FLOAT,
                sentiment_std FLOAT,
                positive_articles INTEGER,
                negative_articles INTEGER,
                neutral_articles INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

def get_db():
    """get database connection context manager"""
    return db_manager.get_connection()