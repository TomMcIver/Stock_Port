# view articls db

import sqlite3
import pandas as pd
from datetime import datetime

def truncate_text(text, max_length=60):
    if not text or pd.isna(text):
        return ""
    
    text = str(text).strip()
    if len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..."

def view_database():
    
    try:
        conn = sqlite3.connect('news_articles.db')
        
        print(">> NEWS ARTICLES DATABASE")
        print("=" * 80)
        
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM articles')
        total_articles = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM articles WHERE content != ""')
        scraped_articles = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT source) FROM articles')
        total_sources = cursor.fetchone()[0]
        
        print(f"📊 DATABASE OVERVIEW:")
        print(f"   Total records: {total_articles:,}")
        print(f"   Full articles: {scraped_articles:,}")
        print(f"   URL-only: {total_articles - scraped_articles:,}")
        print(f"   Sources: {total_sources}")
        
        print(f"\\n📰 ARTICLES BY SOURCE:")
        source_df = pd.read_sql_query('''
            SELECT source, 
                   COUNT(*) as total,
                   COUNT(CASE WHEN content != "" THEN 1 END) as with_content
            FROM articles 
            GROUP BY source 
            ORDER BY total DESC
        ''', conn)
        
        for _, row in source_df.iterrows():
            source = row['source'][:20].ljust(20)
            total = str(row['total']).rjust(6)
            content = str(row['with_content']).rjust(6)
            print(f"   {source} | Total: {total} | Content: {content}")
        
        print(f"\\n📄 RECENT ARTICLES (Sample):")
        print("-" * 80)
        
        recent_df = pd.read_sql_query('''
            SELECT source, title, content, author, published_date, created_at
            FROM articles 
            WHERE content != ""
            ORDER BY created_at DESC 
            LIMIT 10
        ''', conn)
        
        if recent_df.empty:
            print("No articles with content found.")
        else:
            for i, row in recent_df.iterrows():
                source = row['source'][:15].ljust(15)
                title = truncate_text(row['title'], 45)
                content = truncate_text(row['content'], 80)
                author = truncate_text(row['author'], 20) if row['author'] else ""
                
                print(f"{i+1:2}. [{source}] {title}")
                if author:
                    print(f"    By: {author}")
                print(f"    {content}")
                print()
        
        # url only sampls
        cursor.execute('SELECT COUNT(*) FROM articles WHERE content = ""')
        url_only_count = cursor.fetchone()[0]
        
        if url_only_count > 0:
            print(f"\\n🔗 URL-ONLY RECORDS (Sample of {url_only_count:,}):")
            print("-" * 80)
            
            url_df = pd.read_sql_query('''
                SELECT source, url
                FROM articles 
                WHERE content = ""
                ORDER BY created_at DESC 
                LIMIT 5
            ''', conn)
            
            for i, row in url_df.iterrows():
                source = row['source'][:15].ljust(15)
                url = truncate_text(row['url'], 60)
                print(f"{i+1}. [{source}] {url}")
        
        import os
        if os.path.exists('news_articles.db'):
            file_size = os.path.getsize('news_articles.db') / (1024 * 1024)
            print(f"\\n💾 DATABASE FILE:")
            print(f"   File: news_articles.db")
            print(f"   Size: {file_size:.1f} MB")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except FileNotFoundError:
        print("Database file 'news_articles.db' not found!")
        print("Run 'python import_articles_to_db.py' first to create the database.")
    except Exception as e:
        print(f"Error: {e}")

def search_articles(search_term=None, source=None, limit=5):
    
    try:
        conn = sqlite3.connect('news_articles.db')
        
        query = "SELECT source, title, content, author FROM articles WHERE content != ''"
        params = []
        
        if search_term:
            query += " AND (title LIKE ? OR content LIKE ?)"
            params.extend([f'%{search_term}%', f'%{search_term}%'])
        
        if source:
            query += " AND source LIKE ?"
            params.append(f'%{source}%')
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        df = pd.read_sql_query(query, conn, params=params)
        
        if df.empty:
            print("No matching articles found.")
        else:
            print(f"\\n🔍 SEARCH RESULTS ({len(df)} articles):")
            print("-" * 80)
            
            for i, row in df.iterrows():
                source = row['source'][:15].ljust(15)
                title = truncate_text(row['title'], 50)
                content = truncate_text(row['content'], 80)
                author = truncate_text(row['author'], 20) if row['author'] else ""
                
                print(f"{i+1}. [{source}] {title}")
                if author:
                    print(f"    By: {author}")
                print(f"    {content}")
                print()
        
        conn.close()
        
    except Exception as e:
        print(f"Search error: {e}")

def main():
    
    while True:
        print("\\n" + "=" * 50)
        print("NEWS ARTICLES DATABASE VIEWER")
        print("=" * 50)
        print("1. View database overview")
        print("2. Search articles by keyword")
        print("3. Search by news source")
        print("4. Exit")
        
        choice = input("\\nEnter choice (1-4): ").strip()
        
        if choice == '1':
            view_database()
        elif choice == '2':
            term = input("Enter search term: ").strip()
            if term:
                search_articles(search_term=term)
        elif choice == '3':
            source = input("Enter news source (e.g., CNN, BBC): ").strip()
            if source:
                search_articles(source=source)
        elif choice == '4':
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == '__main__':
    main()