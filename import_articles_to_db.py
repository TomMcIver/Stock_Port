# import articls to db

import sqlite3
import pandas as pd
import os
import glob
from datetime import datetime

def create_database():
    """Create SQLite database and articles table"""
    conn = sqlite3.connect('news_articles.db')
    cursor = conn.cursor()
    
    # Create articles table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            source TEXT,
            domain TEXT,
            title TEXT,
            content TEXT,
            author TEXT,
            published_date TEXT,
            scraped_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create index for faster queries
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_source ON articles(source)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_published_date ON articles(published_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_domain ON articles(domain)')
    
    conn.commit()
    return conn

def import_csv_files():
    """Import all CSV files and delete them after successful import"""
    
    print(">> IMPORTING ARTICLES TO DATABASE")
    print("=" * 50)
    
    # Find all relevant CSV files
    csv_files = []
    csv_files.extend(glob.glob('scraped_articles.csv'))
    csv_files.extend(glob.glob('enhanced_urls_*.csv'))
    csv_files.extend(glob.glob('urls_*.csv'))
    
    # Remove duplicates
    csv_files = list(set(csv_files))
    
    if not csv_files:
        print("No CSV files found to import!")
        return
    
    print(f"Found {len(csv_files)} CSV files to import:")
    for file in csv_files:
        print(f"  - {file}")
    
    # Create database
    conn = create_database()
    cursor = conn.cursor()
    
    total_imported = 0
    total_skipped = 0
    files_deleted = []
    
    # Import each CSV file
    for csv_file in csv_files:
        try:
            print(f"\\nImporting {csv_file}...")
            df = pd.read_csv(csv_file)
            
            imported_count = 0
            skipped_count = 0
            
            # Handle different CSV file types
            if 'content' in df.columns:
                # This is scraped articles CSV
                for _, row in df.iterrows():
                    try:
                        cursor.execute('''
                            INSERT OR IGNORE INTO articles 
                            (url, source, domain, title, content, author, published_date, scraped_date)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            row.get('url', ''),
                            row.get('source', ''),
                            row.get('domain', ''),
                            row.get('title', ''),
                            row.get('content', ''),
                            row.get('author', ''),
                            row.get('published_date', ''),
                            row.get('scraped_date', datetime.now().isoformat())
                        ))
                        
                        if cursor.rowcount > 0:
                            imported_count += 1
                        else:
                            skipped_count += 1
                            
                    except Exception as e:
                        skipped_count += 1
                        continue
            
            else:
                # This is URL-only CSV (from crawlers)
                for _, row in df.iterrows():
                    try:
                        # Insert as placeholder with just URL and source
                        cursor.execute('''
                            INSERT OR IGNORE INTO articles 
                            (url, source, domain, title, content, author, published_date, scraped_date)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            row.get('url', ''),
                            row.get('site', row.get('source', 'Unknown')),
                            '',  # domain will be extracted later if needed
                            'URL Only - Not Scraped',
                            '',  # empty content
                            '',  # empty author
                            '',  # empty published_date
                            row.get('discovered_date', datetime.now().isoformat())
                        ))
                        
                        if cursor.rowcount > 0:
                            imported_count += 1
                        else:
                            skipped_count += 1
                            
                    except Exception as e:
                        skipped_count += 1
                        continue
            
            conn.commit()
            
            print(f"  Imported: {imported_count:,} records")
            print(f"  Skipped (duplicates): {skipped_count:,} records")
            
            total_imported += imported_count
            total_skipped += skipped_count
            
            # Delete CSV file after successful import
            try:
                os.remove(csv_file)
                files_deleted.append(csv_file)
                print(f"  Deleted: {csv_file}")
            except Exception as e:
                print(f"  Warning: Could not delete {csv_file}: {e}")
                
        except Exception as e:
            print(f"  Error importing {csv_file}: {e}")
            continue
    
    # Get final database stats
    cursor.execute('SELECT COUNT(*) FROM articles')
    total_articles = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(DISTINCT source) FROM articles')
    total_sources = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM articles WHERE content != ""')
    scraped_articles = cursor.fetchone()[0]
    
    conn.close()
    
    # Final summary
    print(f"\\n")
    print("=" * 50)
    print("IMPORT COMPLETE!")
    print("=" * 50)
    print(f"Total records imported: {total_imported:,}")
    print(f"Total duplicates skipped: {total_skipped:,}")
    print(f"CSV files deleted: {len(files_deleted)}")
    print()
    print("DATABASE STATISTICS:")
    print(f"  Total articles: {total_articles:,}")
    print(f"  Full articles (with content): {scraped_articles:,}")
    print(f"  URL-only records: {total_articles - scraped_articles:,}")
    print(f"  News sources: {total_sources}")
    print()
    print(f"Database saved as: news_articles.db")
    
    if files_deleted:
        print(f"\\nDeleted CSV files:")
        for file in files_deleted:
            print(f"  - {file}")

def main():
    """Main function"""
    import_csv_files()

if __name__ == '__main__':
    main()