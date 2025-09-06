from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, Index, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
import hashlib
from datetime import datetime

Base = declarative_base()

class NewsArticle(Base):
    __tablename__ = 'news_articles'
    
    # primary identifir and dedup
    id = Column(Integer, primary_key=True, autoincrement=True)
    raw_id = Column(String(64), unique=True, nullable=False, index=True)  # url hash for dedup
    url = Column(Text, nullable=False, index=True)
    url_hash = Column(String(64), nullable=False, index=True)
    
    # source metadata
    source = Column(String(255), nullable=False, index=True)
    domain = Column(String(255), nullable=False, index=True)
    
    # temporal data
    ts_published = Column(DateTime, nullable=True, index=True)
    ts_crawled = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    ts_processed = Column(DateTime, nullable=True, index=True)
    
    # article content
    title = Column(Text, nullable=True)
    authors = Column(JSONB, nullable=True)  # array of author names
    text = Column(Text, nullable=True)
    language = Column(String(10), nullable=True, index=True)
    
    # extraction metadata
    extraction_method = Column(String(50), nullable=True)  # news-please, newspaper3k, etc
    raw_html_path = Column(Text, nullable=True)  # path to stored raw html
    
    # processing flags
    is_processed = Column(Boolean, default=False, nullable=False, index=True)
    has_embeddings = Column(Boolean, default=False, nullable=False, index=True)
    has_sentiment = Column(Boolean, default=False, nullable=False, index=True)
    
    # quality scores
    text_quality_score = Column(Float, nullable=True)  # 0-1 score for text quality
    relevance_score = Column(Float, nullable=True)  # 0-1 relevance to finance
    
    # relationships
    embeddings = relationship("NewsEmbedding", back_populates="article", cascade="all, delete-orphan")
    ticker_associations = relationship("ArticleTickerAssociation", back_populates="article", cascade="all, delete-orphan")
    sentiments = relationship("ArticleSentiment", back_populates="article", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_news_source_published', 'source', 'ts_published'),
        Index('idx_news_domain_crawled', 'domain', 'ts_crawled'),
        Index('idx_news_processed_flags', 'is_processed', 'has_embeddings', 'has_sentiment'),
    )
    
    def __init__(self, url, **kwargs):
        self.url = url
        self.url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        self.raw_id = f"{self.url_hash}_{int(datetime.utcnow().timestamp())}"
        super().__init__(**kwargs)

class NewsEmbedding(Base):
    __tablename__ = 'news_embeddings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(Integer, ForeignKey('news_articles.id'), nullable=False, index=True)
    
    # embedding metadata
    model_name = Column(String(100), nullable=False, index=True)
    embedding_type = Column(String(50), nullable=False, index=True)  # title, text, combined
    
    # vector data (stored as json array for compatibility)
    embedding_vector = Column(JSONB, nullable=False)
    vector_dim = Column(Integer, nullable=False)
    
    # processing metadata
    ts_created = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # relationships
    article = relationship("NewsArticle", back_populates="embeddings")
    
    __table_args__ = (
        UniqueConstraint('article_id', 'model_name', 'embedding_type', name='uq_article_model_type'),
        Index('idx_embedding_model_type', 'model_name', 'embedding_type'),
    )

class TickerSymbol(Base):
    __tablename__ = 'ticker_symbols'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True)
    company_name = Column(String(255), nullable=True)
    sector = Column(String(100), nullable=True, index=True)
    market_cap_tier = Column(String(20), nullable=True, index=True)  # large, mid, small, micro
    
    # metadata for tagging
    alternative_symbols = Column(JSONB, nullable=True)  # array of alternative tickers
    company_aliases = Column(JSONB, nullable=True)  # array of company name variations
    
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    ts_created = Column(DateTime, nullable=False, default=datetime.utcnow)
    ts_updated = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # relationships
    article_associations = relationship("ArticleTickerAssociation", back_populates="ticker")

class ArticleTickerAssociation(Base):
    __tablename__ = 'article_ticker_associations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(Integer, ForeignKey('news_articles.id'), nullable=False, index=True)
    ticker_id = Column(Integer, ForeignKey('ticker_symbols.id'), nullable=False, index=True)
    
    # tagging metadata
    confidence_score = Column(Float, nullable=False, default=1.0)  # 0-1 confidence in association
    mention_count = Column(Integer, nullable=False, default=1)  # number of times ticker mentioned
    mention_context = Column(JSONB, nullable=True)  # array of context snippets
    tagging_method = Column(String(50), nullable=False)  # regex, nlp, manual
    
    # temporal
    ts_created = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # relationships
    article = relationship("NewsArticle", back_populates="ticker_associations")
    ticker = relationship("TickerSymbol", back_populates="article_associations")
    
    __table_args__ = (
        UniqueConstraint('article_id', 'ticker_id', name='uq_article_ticker'),
        Index('idx_ticker_confidence', 'ticker_id', 'confidence_score'),
        Index('idx_article_mentions', 'article_id', 'mention_count'),
    )

class ArticleSentiment(Base):
    __tablename__ = 'article_sentiments'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(Integer, ForeignKey('news_articles.id'), nullable=False, index=True)
    
    # sentiment scores
    model_name = Column(String(100), nullable=False, index=True)
    sentiment_type = Column(String(50), nullable=False, index=True)  # overall, ticker-specific
    
    # vader scores
    vader_compound = Column(Float, nullable=True)
    vader_positive = Column(Float, nullable=True) 
    vader_neutral = Column(Float, nullable=True)
    vader_negative = Column(Float, nullable=True)
    
    # finbert scores (if available)
    finbert_positive = Column(Float, nullable=True)
    finbert_negative = Column(Float, nullable=True)
    finbert_neutral = Column(Float, nullable=True)
    finbert_label = Column(String(20), nullable=True)  # positive, negative, neutral
    
    # aggregated sentiment
    final_sentiment_score = Column(Float, nullable=True)  # -1 to 1 normalized score
    final_sentiment_label = Column(String(20), nullable=True, index=True)  # positive, negative, neutral
    
    # optional ticker-specific sentiment
    associated_ticker_id = Column(Integer, ForeignKey('ticker_symbols.id'), nullable=True, index=True)
    
    # metadata
    ts_created = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # relationships
    article = relationship("NewsArticle", back_populates="sentiments")
    ticker = relationship("TickerSymbol")
    
    __table_args__ = (
        Index('idx_sentiment_model_type', 'model_name', 'sentiment_type'),
        Index('idx_sentiment_score_label', 'final_sentiment_score', 'final_sentiment_label'),
        Index('idx_ticker_sentiment', 'associated_ticker_id', 'final_sentiment_score'),
    )

# materialized aggregation tables for performance
class DailyTickerSentiment(Base):
    __tablename__ = 'daily_ticker_sentiment'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker_id = Column(Integer, ForeignKey('ticker_symbols.id'), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    
    # aggregated metrics
    article_count = Column(Integer, nullable=False, default=0)
    avg_sentiment_score = Column(Float, nullable=True)
    weighted_sentiment_score = Column(Float, nullable=True)  # weighted by mention count
    
    # sentiment distribution
    positive_count = Column(Integer, nullable=False, default=0)
    negative_count = Column(Integer, nullable=False, default=0)
    neutral_count = Column(Integer, nullable=False, default=0)
    
    # volume metrics
    total_mentions = Column(Integer, nullable=False, default=0)
    unique_sources = Column(Integer, nullable=False, default=0)
    
    # metadata
    ts_created = Column(DateTime, nullable=False, default=datetime.utcnow)
    ts_updated = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # relationships
    ticker = relationship("TickerSymbol")
    
    __table_args__ = (
        UniqueConstraint('ticker_id', 'date', name='uq_ticker_date'),
        Index('idx_daily_sentiment_score', 'avg_sentiment_score'),
        Index('idx_daily_article_count', 'article_count'),
    )

class CrawlJob(Base):
    __tablename__ = 'crawl_jobs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_type = Column(String(50), nullable=False, index=True)  # pull, backfill
    
    # job parameters
    source_domains = Column(JSONB, nullable=True)  # array of domains
    date_start = Column(DateTime, nullable=True, index=True)
    date_end = Column(DateTime, nullable=True, index=True)
    max_articles = Column(Integer, nullable=True)
    
    # job status
    status = Column(String(20), nullable=False, default='pending', index=True)  # pending, running, completed, failed
    
    # results
    articles_found = Column(Integer, nullable=False, default=0)
    articles_processed = Column(Integer, nullable=False, default=0)
    articles_with_text = Column(Integer, nullable=False, default=0)
    articles_with_publish_date = Column(Integer, nullable=False, default=0)
    
    # timing
    ts_started = Column(DateTime, nullable=True, index=True)
    ts_completed = Column(DateTime, nullable=True, index=True)
    ts_created = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # error tracking
    error_message = Column(Text, nullable=True)
    error_count = Column(Integer, nullable=False, default=0)
    
    __table_args__ = (
        Index('idx_crawl_status_created', 'status', 'ts_created'),
    )