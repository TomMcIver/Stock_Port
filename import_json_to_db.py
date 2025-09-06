# import json to db

import sqlite3
import json
from datetime import datetime

def import_json_articles():
    
    print(">> IMPORTING SCRAPED ARTICLES FROM JSON")
    print("=" * 50)
    
    try:
        print("Loading scraped_articles.json...")
        with open('scraped_articles.json', 'r', encoding='utf-8') as f:
            articles = json.load(f)
        
        print(f"Found {len(articles):,} articles in JSON file")
        
        conn = sqlite3.connect('news_articles.db')
        cursor = conn.cursor()
        
        imported_count = 0
        updated_count = 0
        skipped_count = 0
        
        print("\\nImporting articles...")
        
        for i, article in enumerate(articles):
            try:
                    cursor.execute('SELECT id FROM articles WHERE url = ?', (article['url'],))
                existing = cursor.fetchone()
                
                if existing:
                        cursor.execute('''
                        UPDATE articles 
                        SET title = ?, content = ?, author = ?, published_date = ?, scraped_date = ?
                        WHERE url = ?
                    ''', (
                        article.get('title', ''),
                        article.get('content', ''),
                        article.get('author', ''),
                        article.get('published_date', ''),
                        article.get('scraped_date', ''),
                        article['url']
                    ))
                    updated_count += 1
                else:
                        cursor.execute('''
                        INSERT INTO articles 
                        (url, source, domain, title, content, author, published_date, scraped_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        article['url'],
                        article.get('source', ''),
                        article.get('domain', ''),
                        article.get('title', ''),
                        article.get('content', ''),
                        article.get('author', ''),
                        article.get('published_date', ''),
                        article.get('scraped_date', '')
                    ))
                    imported_count += 1
                
                if (i + 1) % 500 == 0:
                    print(f"  Processed {i + 1:,}/{len(articles):,} articles...")
                    
            except Exception as e:
                skipped_count += 1
                continue
        
        conn.commit()
        
        cursor.execute('SELECT COUNT(*) FROM articles')
        total_articles = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM articles WHERE content != ""')
        content_articles = cursor.fetchone()[0]
        
        conn.close()
        
        print("\\n" + "=" * 50)
        print("IMPORT COMPLETE!")
        print("=" * 50)
        print(f"New articles imported: {imported_count:,}")
        print(f"Existing articles updated: {updated_count:,}")
        print(f"Skipped/failed: {skipped_count:,}")
        print()
        print("DATABASE STATS:")
        print(f"  Total articles: {total_articles:,}")
        print(f"  With content: {content_articles:,}")
        print(f"  URL-only: {total_articles - content_articles:,}")
        
    except FileNotFoundError:
        print("Error: scraped_articles.json not found!")
    except Exception as e:
        print(f"Error: {e}")

def main():
    import_json_articles()

if __name__ == '__main__':
    main()