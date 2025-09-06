# enhansed news crawlr

import requests
import time
from datetime import datetime, timedelta
import pandas as pd
from typing import List, Dict, Set
import csv
import re
import threading
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse, parse_qs
from bs4 import BeautifulSoup
import os

class EnhancedNewsCrawler:
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.total_urls_found = 0
        self.sites_completed = 0
        self.start_time = time.time()
        self.lock = threading.Lock()
        self.current_site = ""
        self.last_progress_time = 0
        
        self.site_results = {}
        
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        self.news_sites = [
            # hi yield sites
            {
                'name': 'New York Times',
                'base_url': 'https://www.nytimes.com',
                'strategy': 'deep',
                'patterns': ['/20\\d\\d/', '/section/', '/interactive/20\\d\\d/'],
                'avoid': ['video', 'games', 'cooking', 'real-estate'],
                'deep_paths': ['/section/world', '/section/us', '/section/politics', '/section/business', '/section/technology'],
                'archive_patterns': ['/20{year}/{month:02d}/', '/20{year}/'],
                'max_urls': 25000
            },
            {
                'name': 'New Zealand Herald', 
                'base_url': 'https://www.nzherald.co.nz',
                'strategy': 'deep',
                'patterns': ['/20\\d\\d/', '/nz/', '/world/', '/business/', '/politics/'],
                'avoid': ['video', 'premium', 'interactive'],
                'deep_paths': ['/nz', '/world', '/business', '/politics', '/sport'],
                'archive_patterns': ['/20{year}/', '/{year}/'],
                'max_urls': 20000
            },
            {
                'name': 'RNZ',
                'base_url': 'https://www.rnz.co.nz', 
                'strategy': 'deep',
                'patterns': ['/news/', '/national/', '/world/', '/political/', '/business/'],
                'avoid': ['audio', 'podcast', 'programmes'],
                'deep_paths': ['/news', '/national', '/world', '/political', '/business'],
                'archive_patterns': ['/news/20{year}', '/20{year}'],
                'max_urls': 15000
            },
            {
                'name': 'Fox News',
                'base_url': 'https://www.foxnews.com',
                'strategy': 'deep',
                'patterns': ['/20\\d\\d/', '/politics/', '/us/', '/world/', '/business/'],
                'avoid': ['video', 'media', 'gallery'],
                'deep_paths': ['/politics', '/us', '/world', '/business', '/tech'],
                'archive_patterns': ['/category/politics/20{year}', '/20{year}/'],
                'max_urls': 20000
            },
            {
                'name': 'CNN',
                'base_url': 'https://www.cnn.com',
                'strategy': 'deep',
                'patterns': ['/20\\d\\d/', '/news/', '/politics/', '/business/', '/world/'],
                'avoid': ['video', 'gallery', 'interactive', 'live-news'],
                'deep_paths': ['/politics', '/business', '/world', '/us', '/health'],
                'archive_patterns': ['/20{year}/', '/20{year}/{month:02d}/'],
                'max_urls': 20000
            },
            
            # blockd sites
            {
                'name': 'Washington Post',
                'base_url': 'https://www.washingtonpost.com', 
                'strategy': 'enhanced',
                'patterns': ['/20\\d\\d/', '/news/', '/politics/', '/business/', '/world/'],
                'avoid': ['video', 'graphics', 'interactive'],
                'deep_paths': ['/politics', '/business', '/world', '/national', '/local'],
                'use_archive': True,
                'max_urls': 15000
            },
            {
                'name': 'BBC News',
                'base_url': 'https://www.bbc.com/news',
                'strategy': 'enhanced', 
                'patterns': ['/news/world-', '/news/uk-', '/news/business-', '/news/technology-'],
                'avoid': ['live', 'video', 'programmes'],
                'deep_paths': ['/news/world', '/news/business', '/news/technology', '/news/politics'],
                'use_archive': True,
                'max_urls': 15000
            },
            {
                'name': 'The Telegraph',
                'base_url': 'https://www.telegraph.co.uk',
                'strategy': 'enhanced',
                'patterns': ['/20\\d\\d/', '/news/', '/world-news/', '/business/', '/politics/'],
                'avoid': ['video', 'gallery', 'premium'],
                'deep_paths': ['/news', '/world-news', '/business', '/politics'],
                'use_archive': True, 
                'max_urls': 12000
            },
            
            # med yield
            {
                'name': 'The Guardian',
                'base_url': 'https://www.theguardian.com',
                'strategy': 'standard',
                'patterns': ['/20\\d\\d/', '/world/', '/uk-news/', '/business/', '/politics/'],
                'avoid': ['live', 'video', 'gallery', 'interactive'],
                'deep_paths': ['/world', '/uk-news', '/business', '/politics', '/technology'],
                'max_urls': 15000
            },
            {
                'name': 'CBC News',
                'base_url': 'https://www.cbc.ca/news',
                'strategy': 'standard',
                'patterns': ['/20\\d\\d/', '/canada/', '/world/', '/business/', '/politics/'],
                'avoid': ['video', 'radio', 'player'],
                'deep_paths': ['/canada', '/world', '/business', '/politics'],
                'max_urls': 12000
            },
            {
                'name': 'Globe and Mail',
                'base_url': 'https://www.theglobeandmail.com',
                'strategy': 'standard', 
                'patterns': ['/20\\d\\d/', '/canada/', '/world/', '/business/', '/politics/'],
                'avoid': ['video', 'interactive', 'opinion'],
                'deep_paths': ['/canada', '/world', '/business', '/politics'],
                'max_urls': 10000
            },
            {
                'name': 'ABC News Australia',
                'base_url': 'https://www.abc.net.au/news',
                'strategy': 'standard',
                'patterns': ['/20\\d\\d-', '/australia/', '/world/', '/business/', '/politics/'],
                'avoid': ['video', 'radio', 'listen'],
                'deep_paths': ['/australia', '/world', '/business', '/politics'],
                'max_urls': 10000
            },
            {
                'name': 'Sydney Morning Herald',
                'base_url': 'https://www.smh.com.au',
                'strategy': 'standard',
                'patterns': ['/20\\d\\d/', '/australia/', '/world/', '/business/', '/politics/'],
                'avoid': ['video', 'interactive', 'live'],
                'deep_paths': ['/australia', '/world', '/business', '/politics'],
                'max_urls': 8000
            }
        ]
        
    def get_session(self, enhanced: bool = False):
        session = requests.Session()
        
        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        if enhanced:
            headers.update({
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate', 
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0',
                'Referer': 'https://www.google.com/'
            })
            
        session.headers.update(headers)
        return session
        
    def print_progress(self, force=False):
        import sys
        
        elapsed = time.time() - self.start_time
        rate = self.total_urls_found / elapsed if elapsed > 0 else 0
        
        # eta calc
        remaining_sites = len(self.news_sites) - self.sites_completed
        if rate > 0 and remaining_sites > 0:
            estimated_remaining = remaining_sites * 5000  # Faster estimate
            eta_seconds = estimated_remaining / rate if rate > 0 else 0
            eta_minutes = eta_seconds / 60
            eta_str = f"{eta_minutes:.1f}m"
        else:
            eta_str = "calculating..."
            
        progress_line = (
            f"Site {self.sites_completed + 1}/{len(self.news_sites)}: {self.current_site} | "
            f"URLs: {self.total_urls_found:,} | "
            f"Rate: {rate:.1f}/s | "
            f"ETA: {eta_str} | "
            f"Time: {elapsed/60:.1f}m"
        )
        
        # clear line
        sys.stdout.write('\\r' + ' ' * 100 + '\\r')
        sys.stdout.write(progress_line)
        sys.stdout.flush()
        
    def is_news_article_url(self, url: str, site: Dict) -> bool:
        # must match patern
        pattern_match = any(re.search(pattern, url) for pattern in site['patterns'])
        
        if not pattern_match:
            if site.get('strategy') == 'deep':
                current_year = datetime.now().year
                if str(current_year) in url or str(current_year-1) in url:
                    pattern_match = True
        
        if not pattern_match:
            return False
            
        avoid_match = any(avoid_term in url.lower() for avoid_term in site['avoid'])
        
        parsed = urlparse(url)
        if len(parsed.path.split('/')) < 3:
            return False
            
        return not avoid_match
        
    def get_archive_urls(self, site: Dict) -> Set[str]:
        urls = set()
        
        if not site.get('use_archive'):
            return urls
            
        # archiv dot org
        
        try:
            base_domain = urlparse(site['base_url']).netloc
            api_url = f"http://web.archive.org/cdx/search/cdx"
            
            params = {
                'url': f"{base_domain}/*",
                'from': '20230101', 
                'to': '20241231',
                'matchType': 'prefix',
                'limit': '5000',
                'fl': 'original',
                'filter': 'statuscode:200',
                'collapse': 'urlkey'
            }
            
            session = self.get_session()
            response = session.get(api_url, params=params, timeout=30)
            
            if response.status_code == 200:
                lines = response.text.strip().split('\\n')
                for line in lines[:2000]:  # Limit processing
                    if line.strip():
                        url = line.strip()
                        if self.is_news_article_url(url, site):
                            urls.add(url)
                            with self.lock:
                                self.total_urls_found += 1
                                
        except Exception as e:
            pass
            
        return urls
        
    def extract_urls_from_page(self, url: str, site: Dict, session: requests.Session) -> Set[str]:
        """Extract URLs from a single page with enhanced techniques"""
        found_urls = set()
        
        try:
            # Random delay for rate limiting
            time.sleep(random.uniform(0.5, 2.0))
            
            response = session.get(url, timeout=15)
            if response.status_code != 200:
                return found_urls
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all links
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # Convert relative URLs to absolute
                if href.startswith('/'):
                    full_url = urljoin(site['base_url'], href)
                elif href.startswith('http'):
                    # Only include URLs from same domain
                    if urlparse(href).netloc == urlparse(site['base_url']).netloc:
                        full_url = href
                    else:
                        continue
                else:
                    continue
                    
                # Check if it's a news article URL
                if self.is_news_article_url(full_url, site):
                    found_urls.add(full_url)
                    
        except Exception:
            pass
            
        return found_urls
        
    def deep_crawl_archive_patterns(self, site: Dict, session: requests.Session) -> Set[str]:
        """Deep crawl using archive patterns"""
        urls = set()
        
        if 'archive_patterns' not in site:
            return urls
            
        # Deep crawling archives - silent
        
        # Generate URLs for last 3 years
        current_year = datetime.now().year
        for year in range(current_year - 2, current_year + 1):
            for pattern in site['archive_patterns']:
                if '{year}' in pattern:
                    if '{month' in pattern:
                        # Monthly patterns
                        for month in range(1, 13):
                            try:
                                archive_url = site['base_url'] + pattern.format(year=year, month=month)
                                page_urls = self.extract_urls_from_page(archive_url, site, session)
                                urls.update(page_urls)
                                
                                if len(page_urls) > 0:
                                    # Found URLs - continue silently
                                    pass
                                    
                                with self.lock:
                                    self.total_urls_found += len(page_urls)
                                    
                                if self.total_urls_found % 1000 == 0:
                                    pass  # Silent progress
                                
                                if len(urls) >= site.get('max_urls', 10000) * 0.8:
                                    break
                                    
                            except Exception:
                                continue
                    else:
                        # Yearly patterns
                        try:
                            archive_url = site['base_url'] + pattern.format(year=year)
                            page_urls = self.extract_urls_from_page(archive_url, site, session)
                            urls.update(page_urls)
                            
                            with self.lock:
                                self.total_urls_found += len(page_urls)
                                
                            pass  # Silent progress
                            
                        except Exception:
                            continue
                            
                if len(urls) >= site.get('max_urls', 10000) * 0.8:
                    break
                    
        return urls
        
    def crawl_site_enhanced(self, site: Dict) -> List[str]:
        """Enhanced site crawling based on strategy"""
        all_urls = set()
        self.current_site = site['name']
        
        # Choose session type based on strategy
        enhanced = site['strategy'] in ['enhanced', 'deep']
        session = self.get_session(enhanced=enhanced)
        
        # Silent start - no print
        
        # Method 1: Try archive.org for blocked sites
        if site.get('use_archive'):
            archive_urls = self.get_archive_urls(site)
            all_urls.update(archive_urls)
            # Archive.org completed silently
        
        # Method 2: Standard sitemap crawling
        sitemap_urls = [
            f"{site['base_url']}/sitemap.xml",
            f"{site['base_url']}/sitemap_index.xml",
            f"{site['base_url']}/news-sitemap.xml"
        ]
        
        for sitemap_url in sitemap_urls:
            try:
                response = session.get(sitemap_url, timeout=15)
                if response.status_code == 200:
                    if 'xml' in sitemap_url:
                        soup = BeautifulSoup(response.content, 'xml')
                        for loc in soup.find_all('loc'):
                            url = loc.text.strip()
                            if self.is_news_article_url(url, site):
                                all_urls.add(url)
                                with self.lock:
                                    self.total_urls_found += 1
                                if len(all_urls) % 500 == 0:
                                    pass  # Silent progress
            except Exception:
                pass
        
        # Sitemap completed silently
        
        # Method 3: Deep crawling for high-yield sites
        if site['strategy'] == 'deep':
            # Crawl deep paths
            for deep_path in site.get('deep_paths', []):
                try:
                    deep_url = site['base_url'] + deep_path
                    page_urls = self.extract_urls_from_page(deep_url, site, session)
                    all_urls.update(page_urls)
                    
                    # Crawl sub-pages from deep paths
                    for sub_url in list(page_urls)[:50]:  # Limit sub-crawling
                        if len(all_urls) < site.get('max_urls', 15000):
                            sub_page_urls = self.extract_urls_from_page(sub_url, site, session)
                            all_urls.update(sub_page_urls)
                            
                            with self.lock:
                                self.total_urls_found += len(sub_page_urls)
                            pass  # Silent progress
                            
                except Exception:
                    continue
            
            # Deep paths completed silently
            
            # Archive pattern crawling
            archive_urls = self.deep_crawl_archive_patterns(site, session)
            all_urls.update(archive_urls)
            
        # Method 4: General page crawling
        pages_to_crawl = [site['base_url']] + [site['base_url'] + path for path in site.get('deep_paths', [])]
        crawled_pages = set()
        
        for page_url in pages_to_crawl[:20]:  # Limit initial pages
            if page_url not in crawled_pages and len(all_urls) < site.get('max_urls', 10000):
                crawled_pages.add(page_url)
                page_urls = self.extract_urls_from_page(page_url, site, session)
                all_urls.update(page_urls)
                
                with self.lock:
                    self.total_urls_found += len(page_urls)
                pass  # Silent progress
        
        return list(all_urls)
        
    def save_urls_to_csv(self, site_name: str, urls: List[str]):
        """Save URLs to CSV file"""
        filename = f"enhanced_urls_{site_name.replace(' ', '_').lower()}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['url', 'discovered_date', 'site', 'strategy'])
            
            # Find site info for strategy
            site_strategy = 'standard'
            for site in self.news_sites:
                if site['name'] == site_name:
                    site_strategy = site['strategy']
                    break
            
            for url in urls:
                writer.writerow([url, datetime.now().isoformat(), site_name, site_strategy])
                
        # CSV saved silently
        
    def crawl_all_sites(self):
        """Crawl all news sites with enhanced strategies"""
        print(f">> Enhanced crawler: {len(self.news_sites)} sites | Workers: {self.max_workers}")
        print("=" * 60)
        
        self.start_time = time.time()
        
        # Sort sites by strategy - deep first for maximum results
        sorted_sites = sorted(self.news_sites, key=lambda x: {'deep': 0, 'enhanced': 1, 'standard': 2}[x['strategy']])
        
        # Simple progress updates
        
        for site in sorted_sites:
            try:
                # Crawl site
                urls = self.crawl_site_enhanced(site)
                
                # Save results
                self.site_results[site['name']] = urls
                self.save_urls_to_csv(site['name'], urls)
                
                with self.lock:
                    self.sites_completed += 1
                
                # Update progress after each site
                self.print_progress(force=True)
                pass  # Silent progress
                
            except Exception as e:
                # Site failed silently
                with self.lock:
                    self.sites_completed += 1
        
        # Final summary
        total_time = time.time() - self.start_time
        print(f"\\n\\n")
        print("=" * 80)
        print("ENHANCED CRAWLING COMPLETE!")
        print("=" * 80)
        print(f"Total time: {total_time/60:.1f} minutes")
        print(f"Total URLs found: {self.total_urls_found:,}")
        print(f"Sites completed: {self.sites_completed}/{len(self.news_sites)}")
        print()
        
        # Per-site summary with strategy
        print("URLs collected per site:")
        print("-" * 50)
        for site_name, urls in self.site_results.items():
            strategy = next((s['strategy'] for s in self.news_sites if s['name'] == site_name), 'unknown')
            print(f"{site_name:<25}: {len(urls):>6,} URLs ({strategy})")
        
        print(f"\\nCSV files created: enhanced_urls_[site_name].csv")
        
def main():
    """Main function"""
    print("Starting enhanced news URL crawler...")
    print("Enhanced anti-bot techniques + deep crawling on high-yield sites")
    print()
    
    crawler = EnhancedNewsCrawler(max_workers=4)
    crawler.crawl_all_sites()

if __name__ == '__main__':
    main()