# adaptiv articl scrappr

import requests
import time
from datetime import datetime, timezone
import pandas as pd
from typing import List, Dict, Optional, Tuple
import csv
import re
import threading
import json
import os
import glob
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import pytz
from dateutil.parser import parse as date_parse
from dateutil import tz
import sys

# JavaScript rendering support
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    print("Installing selenium for JavaScript support...")
    os.system("pip install selenium webdriver-manager dateutil pytz")
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        SELENIUM_AVAILABLE = True
    except ImportError:
        SELENIUM_AVAILABLE = False

class AdaptiveArticleScraper:
    """Highly adaptive article scraper with JavaScript support"""
    
    def __init__(self, max_workers: int = 8, use_javascript: bool = True):
        self.max_workers = max_workers
        self.use_javascript = use_javascript and SELENIUM_AVAILABLE
        
        # Progress tracking
        self.urls_processed = 0
        self.articles_scraped = 0
        self.articles_failed = 0
        self.start_time = time.time()
        self.lock = threading.Lock()
        
        # Results storage
        self.scraped_articles = []
        self.failed_urls = []
        
        # Setup HTTP session
        self.session = self.setup_session()
        
        # Setup Selenium for JavaScript sites
        self.drivers = []
        if self.use_javascript:
            self.setup_selenium_drivers()
        
        # Common date patterns for extraction
        self.date_patterns = [
            # ISO formats
            r'(\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}[+-]\\d{2}:\\d{2})',
            r'(\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z?)',
            r'(\\d{4}-\\d{2}-\\d{2})',
            
            # Common formats
            r'(\\w+\\s+\\d{1,2},\\s+\\d{4})',  # January 15, 2024
            r'(\\d{1,2}\\s+\\w+\\s+\\d{4})',   # 15 January 2024
            r'(\\d{1,2}/\\d{1,2}/\\d{4})',     # 01/15/2024
            r'(\\d{1,2}-\\d{1,2}-\\d{4})',     # 01-15-2024
        ]
        
        # Content selectors by site (adaptive patterns)
        self.site_selectors = {
            'cnn.com': {
                'title': ['h1.headline', 'h1', '.headline', 'title'],
                'content': ['.article-content', '.zn-body', '.l-container', 'article'],
                'author': ['.byline', '.author', '.metadata__byline'],
                'date': ['time', '.timestamp', '.article-timestamp', '[datetime]'],
                'js_required': False
            },
            'nytimes.com': {
                'title': ['h1[data-testid="headline"]', 'h1', '.headline'],
                'content': ['section[data-testid="articleBody"]', '.story-content', 'article'],
                'author': ['.byline', '[data-testid="byline"]', '.author'],
                'date': ['time', '[data-testid="timestamp"]', '.timestamp'],
                'js_required': True
            },
            'bbc.com': {
                'title': ['h1[data-testid="headline"]', 'h1', '.story-headline'],
                'content': ['[data-testid="text-block"]', '.story-body', 'article'],
                'author': ['.byline', '.author', '.attribution'],
                'date': ['time', '.date', '.timestamp'],
                'js_required': False
            },
            'foxnews.com': {
                'title': ['h1.headline', 'h1', '.headline'],
                'content': ['.article-content', '.content', 'article'],
                'author': ['.author', '.byline'],
                'date': ['time', '.article-date', '.timestamp'],
                'js_required': False
            },
            'theguardian.com': {
                'title': ['h1[data-gu-name="headline"]', 'h1'],
                'content': ['[data-gu-name="body"]', '.content__article-body', 'article'],
                'author': ['.contributor-byline', '.byline', '.author'],
                'date': ['time', '.content__dateline-time', '.timestamp'],
                'js_required': False
            }
        }
        
    def setup_session(self):
        """Setup HTTP session with realistic headers"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        return session
        
    def setup_selenium_drivers(self):
        """Setup Selenium WebDriver pool for JavaScript sites"""
        if not SELENIUM_AVAILABLE:
            return
            
        try:
            for _ in range(min(3, self.max_workers)):  # Max 3 browser instances
                chrome_options = Options()
                chrome_options.add_argument('--headless')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--disable-gpu')
                chrome_options.add_argument('--window-size=1920x1080')
                chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
                
                driver = webdriver.Chrome(options=chrome_options)
                driver.set_page_load_timeout(30)
                self.drivers.append(driver)
                
        except Exception as e:
            print(f"Warning: Could not setup Selenium drivers: {e}")
            self.use_javascript = False
            
    def get_available_driver(self):
        """Get an available Selenium driver"""
        if self.drivers:
            return self.drivers.pop()
        return None
        
    def return_driver(self, driver):
        """Return Selenium driver to pool"""
        if driver:
            self.drivers.append(driver)
            
    def print_progress(self):
        """Print live progress updates"""
        elapsed = time.time() - self.start_time
        rate = self.urls_processed / elapsed if elapsed > 0 else 0
        
        progress_line = (
            f"URLs: {self.urls_processed:,} | "
            f"Scraped: {self.articles_scraped:,} | "
            f"Failed: {self.articles_failed:,} | "
            f"Rate: {rate:.1f}/s | "
            f"Success: {(self.articles_scraped/(max(self.urls_processed,1)))*100:.1f}% | "
            f"Time: {elapsed/60:.1f}m"
        )
        
        # Clear line and print
        sys.stdout.write('\\r' + ' ' * 120 + '\\r')
        sys.stdout.write(progress_line)
        sys.stdout.flush()
        
    def extract_date_adaptive(self, soup, url: str) -> Optional[datetime]:
        """Adaptive date extraction with timezone handling"""
        date_candidates = []
        
        # Method 1: Look for structured data (JSON-LD, meta tags)
        structured_dates = soup.find_all('script', type='application/ld+json')
        for script in structured_dates:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    for key in ['datePublished', 'dateModified', 'publishDate']:
                        if key in data:
                            date_candidates.append(data[key])
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            for key in ['datePublished', 'dateModified']:
                                if key in item:
                                    date_candidates.append(item[key])
            except:
                continue
                
        # Method 2: Meta tags
        meta_dates = soup.find_all('meta', attrs={'name': re.compile(r'date|time', re.I)})
        for meta in meta_dates:
            if meta.get('content'):
                date_candidates.append(meta['content'])
                
        # Method 3: Time elements
        time_elements = soup.find_all('time')
        for time_elem in time_elements:
            if time_elem.get('datetime'):
                date_candidates.append(time_elem['datetime'])
            if time_elem.get_text().strip():
                date_candidates.append(time_elem.get_text().strip())
                
        # Method 4: Site-specific selectors
        domain = urlparse(url).netloc.lower()
        for site_domain, selectors in self.site_selectors.items():
            if site_domain in domain:
                for selector in selectors.get('date', []):
                    elements = soup.select(selector)
                    for elem in elements:
                        if elem.get('datetime'):
                            date_candidates.append(elem['datetime'])
                        text = elem.get_text().strip()
                        if text:
                            date_candidates.append(text)
                            
        # Method 5: Pattern matching in text
        page_text = soup.get_text()
        for pattern in self.date_patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            date_candidates.extend(matches)
            
        # Parse candidates and return best match
        for candidate in date_candidates:
            try:
                parsed_date = date_parse(candidate, fuzzy=True)
                
                # If no timezone info, assume UTC
                if parsed_date.tzinfo is None:
                    parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                    
                # Sanity check - must be reasonable date
                if datetime(2000, 1, 1, tzinfo=timezone.utc) <= parsed_date <= datetime.now(timezone.utc):
                    return parsed_date
                    
            except:
                continue
                
        return None
        
    def extract_content_adaptive(self, soup, url: str, use_js: bool = False) -> Dict[str, str]:
        """Adaptive content extraction based on site patterns"""
        result = {
            'title': '',
            'content': '',
            'author': ''
        }
        
        domain = urlparse(url).netloc.lower()
        
        # Get site-specific selectors
        selectors = None
        for site_domain, site_selectors in self.site_selectors.items():
            if site_domain in domain:
                selectors = site_selectors
                break
        
        # Fallback to generic selectors
        if not selectors:
            selectors = {
                'title': ['h1', '.title', '.headline', 'title'],
                'content': ['article', '.article-content', '.content', '.story', '.post-content', 'main'],
                'author': ['.author', '.byline', '.writer', '.journalist'],
                'date': ['time', '.date', '.timestamp', '.published']
            }
        
        # Extract title
        for selector in selectors['title']:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = title_elem.get_text().strip()
                if len(title) > 10:  # Reasonable title length
                    result['title'] = title
                    break
                    
        # Extract content
        for selector in selectors['content']:
            content_elem = soup.select_one(selector)
            if content_elem:
                # Remove unwanted elements
                for unwanted in content_elem(['script', 'style', 'nav', 'footer', 'header', '.ad', '.advertisement']):
                    unwanted.decompose()
                    
                content = content_elem.get_text(separator=' ').strip()
                content = re.sub(r'\\s+', ' ', content)  # Normalize whitespace
                
                if len(content) > 200:  # Reasonable content length
                    result['content'] = content
                    break
                    
        # Fallback content extraction from paragraphs
        if not result['content']:
            paragraphs = soup.find_all('p')
            content_parts = []
            for p in paragraphs:
                text = p.get_text().strip()
                if len(text) > 50:  # Skip short paragraphs
                    content_parts.append(text)
            if content_parts:
                result['content'] = ' '.join(content_parts)
        
        # Extract author (optional)
        for selector in selectors['author']:
            author_elem = soup.select_one(selector)
            if author_elem:
                author = author_elem.get_text().strip()
                # Clean author text
                author = re.sub(r'^(By|Author:|Writer:)\\s*', '', author, flags=re.IGNORECASE)
                if len(author) > 2 and len(author) < 100:  # Reasonable author length
                    result['author'] = author
                    break
        
        return result
        
    def scrape_article(self, url: str, source: str) -> Optional[Dict]:
        """Scrape a single article with adaptive methods"""
        try:
            domain = urlparse(url).netloc.lower()
            needs_js = False
            
            # Check if site needs JavaScript
            for site_domain, selectors in self.site_selectors.items():
                if site_domain in domain:
                    needs_js = selectors.get('js_required', False)
                    break
            
            soup = None
            
            # Method 1: Try JavaScript rendering if needed
            if needs_js and self.use_javascript:
                driver = self.get_available_driver()
                if driver:
                    try:
                        driver.get(url)
                        # Wait for content to load
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.TAG_NAME, "article"))
                        )
                        soup = BeautifulSoup(driver.page_source, 'html.parser')
                    except:
                        pass  # Fall back to regular HTTP
                    finally:
                        self.return_driver(driver)
            
            # Method 2: Regular HTTP request
            if not soup:
                response = self.session.get(url, timeout=15)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                else:
                    return None
            
            if not soup:
                return None
            
            # Extract content adaptively
            content_data = self.extract_content_adaptive(soup, url)
            
            # Extract date
            published_date = self.extract_date_adaptive(soup, url)
            
            # Validate minimum requirements
            if not content_data['title'] or len(content_data['content']) < 100:
                return None
            
            # Build article data
            article = {
                'url': url,
                'source': source,
                'domain': domain,
                'title': content_data['title'][:500],  # Limit title length
                'content': content_data['content'][:10000],  # Limit content length
                'author': content_data['author'][:200] if content_data['author'] else '',
                'published_date': published_date.isoformat() if published_date else '',
                'scraped_date': datetime.now(timezone.utc).isoformat(),
                'success': True
            }
            
            return article
            
        except Exception as e:
            # Log failed URL for investigation
            with self.lock:
                self.failed_urls.append({
                    'url': url,
                    'source': source,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
            return None
            
    def load_urls_from_csv_files(self) -> List[Tuple[str, str]]:
        """Load URLs from all enhanced CSV files"""
        urls = []
        
        # Find all CSV files
        csv_files = glob.glob('enhanced_urls_*.csv')
        
        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file)
                for _, row in df.iterrows():
                    url = row['url']
                    source = row['site']
                    urls.append((url, source))
            except Exception as e:
                print(f"Error loading {csv_file}: {e}")
                
        return urls
        
    def save_results(self):
        """Save scraped articles and failed URLs"""
        # Save scraped articles
        if self.scraped_articles:
            articles_df = pd.DataFrame(self.scraped_articles)
            articles_df.to_csv('scraped_articles.csv', index=False)
            
            # Also save as JSON for better structure
            with open('scraped_articles.json', 'w', encoding='utf-8') as f:
                json.dump(self.scraped_articles, f, indent=2, ensure_ascii=False)
        
        # Save failed URLs for investigation
        if self.failed_urls:
            failed_df = pd.DataFrame(self.failed_urls)
            failed_df.to_csv('failed_urls.csv', index=False)
            
    def scrape_all_articles(self):
        """Scrape all articles from CSV files"""
        print(">> ADAPTIVE ARTICLE SCRAPER")
        print("=" * 60)
        
        # Load URLs
        print("Loading URLs from CSV files...")
        url_list = self.load_urls_from_csv_files()
        total_urls = len(url_list)
        
        print(f"Found {total_urls:,} URLs to scrape")
        print(f"JavaScript support: {'Enabled' if self.use_javascript else 'Disabled'}")
        print(f"Workers: {self.max_workers}")
        print("=" * 60)
        
        if total_urls == 0:
            print("No URLs found in CSV files!")
            return
        
        self.start_time = time.time()
        
        # Process URLs with thread pool
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {}
            
            for url, source in url_list:
                future = executor.submit(self.scrape_article, url, source)
                future_to_url[future] = (url, source)
            
            # Process results
            for future in as_completed(future_to_url):
                url, source = future_to_url[future]
                
                with self.lock:
                    self.urls_processed += 1
                
                try:
                    article = future.result()
                    if article:
                        with self.lock:
                            self.articles_scraped += 1
                            self.scraped_articles.append(article)
                    else:
                        with self.lock:
                            self.articles_failed += 1
                            
                except Exception as e:
                    with self.lock:
                        self.articles_failed += 1
                        self.failed_urls.append({
                            'url': url,
                            'source': source,
                            'error': str(e),
                            'timestamp': datetime.now().isoformat()
                        })
                
                # Update progress every 50 URLs
                if self.urls_processed % 50 == 0:
                    self.print_progress()
        
        # Final results
        total_time = time.time() - self.start_time
        self.print_progress()
        print(f"\\n\\n")
        print("=" * 60)
        print("SCRAPING COMPLETE!")
        print("=" * 60)
        print(f"Total time: {total_time/60:.1f} minutes")
        print(f"URLs processed: {self.urls_processed:,}")
        print(f"Articles scraped: {self.articles_scraped:,}")
        print(f"Articles failed: {self.articles_failed:,}")
        print(f"Success rate: {(self.articles_scraped/max(self.urls_processed,1))*100:.1f}%")
        
        # Save results
        self.save_results()
        print(f"\\nResults saved:")
        print(f"- scraped_articles.csv ({self.articles_scraped:,} articles)")
        print(f"- scraped_articles.json ({self.articles_scraped:,} articles)")
        print(f"- failed_urls.csv ({self.articles_failed:,} failed URLs)")
        
        # Cleanup Selenium drivers
        for driver in self.drivers:
            try:
                driver.quit()
            except:
                pass

def main():
    """Main function"""
    print("Starting adaptive article scraper...")
    print("This will scrape articles from all enhanced_urls_*.csv files")
    print()
    
    scraper = AdaptiveArticleScraper(max_workers=6, use_javascript=True)
    scraper.scrape_all_articles()

if __name__ == '__main__':
    main()