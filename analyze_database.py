"""Database analysis tools - explore your news database"""

import logging
import pandas as pd
from datetime import datetime
from src.db import db_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def show_database_schema():
    """Show the complete database structure and columns"""
    
    logger.info("📊 DATABASE SCHEMA ANALYSIS")
    logger.info("=" * 50)
    
    try:
        # Get table info
        schema_df = db_manager.execute_query("""
            SELECT table_name, column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_schema = 'main' 
            ORDER BY table_name, ordinal_position
        """)
        
        logger.info("🗄️  DATABASE TABLES AND COLUMNS:")
        
        current_table = None
        for _, row in schema_df.iterrows():
            if current_table != row['table_name']:
                current_table = row['table_name']
                logger.info(f"\n📋 TABLE: {current_table}")
                logger.info("-" * 30)
            
            nullable = "NULL" if row['is_nullable'] == 'YES' else "NOT NULL"
            logger.info(f"  {row['column_name']:<20} {row['data_type']:<15} {nullable}")
        
    except Exception as e:
        logger.error(f"Schema analysis failed: {e}")

def analyze_articles_by_year():
    """Analyze articles by year with detailed breakdown"""
    
    logger.info("\n📅 ARTICLES BY YEAR ANALYSIS")
    logger.info("=" * 40)
    
    try:
        # Articles by year
        yearly_df = db_manager.execute_query("""
            SELECT 
                EXTRACT(YEAR FROM ts_published) as year,
                COUNT(*) as article_count,
                COUNT(DISTINCT source) as unique_sources,
                MIN(ts_published) as earliest_date,
                MAX(ts_published) as latest_date
            FROM news_articles 
            WHERE ts_published IS NOT NULL
            GROUP BY EXTRACT(YEAR FROM ts_published)
            ORDER BY year DESC
        """)
        
        logger.info("📊 YEARLY BREAKDOWN:")
        logger.info(f"{'Year':<6} {'Articles':<10} {'Sources':<8} {'Date Range'}")
        logger.info("-" * 60)
        
        total_articles = 0
        for _, row in yearly_df.iterrows():
            year = int(row['year']) if pd.notna(row['year']) else 'Unknown'
            count = int(row['article_count'])
            sources = int(row['unique_sources'])
            earliest = row['earliest_date']
            latest = row['latest_date']
            
            total_articles += count
            
            # Format date range
            if pd.notna(earliest) and pd.notna(latest):
                if earliest.date() == latest.date():
                    date_range = earliest.strftime('%b %d')
                else:
                    date_range = f"{earliest.strftime('%b %d')} - {latest.strftime('%b %d')}"
            else:
                date_range = "N/A"
                
            logger.info(f"{year:<6} {count:<10} {sources:<8} {date_range}")
        
        logger.info("-" * 60)
        logger.info(f"TOTAL: {total_articles} articles across {len(yearly_df)} years")
        
    except Exception as e:
        logger.error(f"Yearly analysis failed: {e}")

def analyze_sources_and_content():
    """Analyze sources and content structure"""
    
    logger.info("\n📰 SOURCE AND CONTENT ANALYSIS")
    logger.info("=" * 40)
    
    try:
        # Top sources
        sources_df = db_manager.execute_query("""
            SELECT 
                source,
                COUNT(*) as article_count,
                AVG(LENGTH(title)) as avg_title_length,
                AVG(LENGTH(text)) as avg_text_length,
                MIN(ts_published) as earliest,
                MAX(ts_published) as latest
            FROM news_articles 
            GROUP BY source 
            ORDER BY article_count DESC 
            LIMIT 15
        """)
        
        logger.info("📊 TOP SOURCES:")
        logger.info(f"{'Source':<35} {'Count':<8} {'Avg Title':<10} {'Avg Text':<10}")
        logger.info("-" * 75)
        
        for _, row in sources_df.iterrows():
            source = row['source'][:34] if len(row['source']) > 34 else row['source']
            count = int(row['article_count'])
            title_len = int(row['avg_title_length']) if pd.notna(row['avg_title_length']) else 0
            text_len = int(row['avg_text_length']) if pd.notna(row['avg_text_length']) else 0
            
            logger.info(f"{source:<35} {count:<8} {title_len:<10} {text_len:<10}")
            
    except Exception as e:
        logger.error(f"Source analysis failed: {e}")

def show_sample_articles():
    """Show sample article data to understand format"""
    
    logger.info("\n📖 SAMPLE ARTICLE DATA FORMAT")
    logger.info("=" * 40)
    
    try:
        # Get sample articles
        sample_df = db_manager.execute_query("""
            SELECT 
                id,
                url,
                source,
                ts_published,
                ts_crawled,
                title,
                LEFT(text, 200) as text_sample,
                language,
                extraction_method,
                metadata
            FROM news_articles 
            ORDER BY ts_published DESC 
            LIMIT 3
        """)
        
        logger.info("🔍 RECENT ARTICLE SAMPLES:")
        
        for i, (_, row) in enumerate(sample_df.iterrows(), 1):
            logger.info(f"\n📄 ARTICLE {i}:")
            logger.info(f"  ID: {row['id']}")
            logger.info(f"  URL: {row['url']}")
            logger.info(f"  Source: {row['source']}")
            logger.info(f"  Published: {row['ts_published']}")
            logger.info(f"  Crawled: {row['ts_crawled']}")
            logger.info(f"  Title: {row['title']}")
            logger.info(f"  Text Sample: {row['text_sample']}...")
            logger.info(f"  Language: {row['language']}")
            logger.info(f"  Method: {row['extraction_method']}")
            logger.info(f"  Metadata: {row['metadata']}")
            
    except Exception as e:
        logger.error(f"Sample articles failed: {e}")

def analyze_date_coverage():
    """Analyze date coverage and timezone info"""
    
    logger.info("\n🕐 DATE AND TIMEZONE ANALYSIS")
    logger.info("=" * 40)
    
    try:
        # Date range analysis
        date_analysis_df = db_manager.execute_query("""
            SELECT 
                COUNT(*) as total_articles,
                COUNT(ts_published) as articles_with_dates,
                MIN(ts_published) as earliest_date,
                MAX(ts_published) as latest_date,
                COUNT(DISTINCT DATE(ts_published)) as unique_days,
                COUNT(DISTINCT EXTRACT(YEAR FROM ts_published)) as years_covered
            FROM news_articles
        """)
        
        row = date_analysis_df.iloc[0]
        total = int(row['total_articles'])
        with_dates = int(row['articles_with_dates'])
        earliest = row['earliest_date']
        latest = row['latest_date']
        unique_days = int(row['unique_days']) if pd.notna(row['unique_days']) else 0
        years = int(row['years_covered']) if pd.notna(row['years_covered']) else 0
        
        logger.info(f"📊 DATE COVERAGE SUMMARY:")
        logger.info(f"  Total articles: {total:,}")
        logger.info(f"  Articles with dates: {with_dates:,} ({with_dates/total*100:.1f}%)")
        logger.info(f"  Date range: {earliest} to {latest}")
        logger.info(f"  Unique days: {unique_days:,}")
        logger.info(f"  Years covered: {years}")
        
        if earliest and latest:
            days_span = (latest - earliest).days
            logger.info(f"  Total span: {days_span:,} days ({days_span/365.25:.1f} years)")
            
    except Exception as e:
        logger.error(f"Date analysis failed: {e}")

def main():
    """Run all database analysis functions"""
    
    logger.info("🔍 COMPREHENSIVE DATABASE ANALYSIS")
    logger.info("=" * 60)
    
    show_database_schema()
    analyze_articles_by_year()
    analyze_sources_and_content()
    analyze_date_coverage()
    show_sample_articles()
    
    logger.info("\n✅ DATABASE ANALYSIS COMPLETE!")

if __name__ == '__main__':
    main()