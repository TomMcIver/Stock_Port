"""ticker symbol tagging system with comprehensive symbol dictionary"""

import re
import json
import logging
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict, Counter
from dataclasses import dataclass

import pandas as pd
from ...db import db_manager
# Ticker patterns and blacklist moved inline
TICKER_PATTERNS = [
    r'\b([A-Z]{1,5})\b',  # Basic ticker pattern
    r'\$([A-Z]{1,5})\b',  # $ prefixed tickers
]

TICKER_BLACKLIST = {
    'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 'HER', 
    'WAS', 'ONE', 'OUR', 'HAD', 'DAY', 'GET', 'USE', 'MAN', 'NEW', 'NOW',
    'OLD', 'SEE', 'HIM', 'TWO', 'HOW', 'ITS', 'WHO', 'OIL', 'SIT', 'SET',
    'USA', 'CEO', 'CFO', 'CTO', 'IPO', 'SEC', 'FDA', 'FBI', 'CIA', 'NSA'
}

def extract_tickers_from_text(text: str) -> List[str]:
    """Extract ticker symbols from text"""
    tickers = []
    for pattern in TICKER_PATTERNS:
        matches = re.findall(pattern, text.upper())
        tickers.extend([t for t in matches if t not in TICKER_BLACKLIST])
    return list(set(tickers))

logger = logging.getLogger(__name__)

@dataclass
class TickerMatch:
    """represents a ticker match in text"""
    symbol: str
    company_name: str
    positions: List[Tuple[int, int]]  # (start, end) positions in text
    context_snippets: List[str]  # surrounding text context
    confidence: float  # 0-1 confidence score
    match_method: str  # how it was matched

class TickerTagger:
    """comprehensive ticker symbol tagger with symbol dictionary"""
    
    def __init__(self):
        self.symbol_dict = {}  # symbol -> TickerSymbol object
        self.company_name_dict = {}  # company name -> TickerSymbol object  
        self.alias_dict = {}  # alias -> TickerSymbol object
        
        # load ticker data from database
        self._load_ticker_data()
        
        # compile regex patterns for efficient matching
        self._compile_patterns()
        
        logger.info(f"initialized ticker tagger with {len(self.symbol_dict)} symbols")
    
    def _load_ticker_data(self):
        """load ticker symbols from database"""
        try:
            symbols_df = db_manager.execute_query(
                "SELECT * FROM ticker_symbols WHERE is_active = true"
            )
            
            for _, row in symbols_df.iterrows():
                # create simple symbol object
                symbol_obj = {
                    'id': int(row['id']) if 'id' in row else None,
                    'symbol': row['symbol'], 
                    'company_name': row.get('company_name'),
                    'aliases': json.loads(row.get('aliases', '[]')) if pd.notna(row.get('aliases')) and row.get('aliases') else [],
                    'sector': row.get('sector')
                }
                
                # main symbol
                self.symbol_dict[symbol_obj['symbol']] = symbol_obj
                
                # company name
                if symbol_obj['company_name']:
                    self.company_name_dict[symbol_obj['company_name'].lower()] = symbol_obj
                
                # company aliases
                if symbol_obj['aliases']:
                    for alias in symbol_obj['aliases']:
                        self.alias_dict[alias.lower()] = symbol_obj
            
            logger.info(f"loaded {len(self.symbol_dict)} symbols, {len(self.company_name_dict)} company names")
        except Exception as e:
            logger.warning(f"failed to load ticker data: {e}")
            # continue with empty dicts
    
    def _compile_patterns(self):
        """compile regex patterns for ticker matching"""
        
        # create pattern for all known symbols
        symbols = list(self.symbol_dict.keys())
        if symbols:
            # escape special regex characters and sort by length (longest first)
            escaped_symbols = [re.escape(s) for s in symbols]
            escaped_symbols.sort(key=len, reverse=True)
            
            self.known_symbols_pattern = re.compile(
                r'\b(' + '|'.join(escaped_symbols) + r')\b',
                re.IGNORECASE
            )
        else:
            self.known_symbols_pattern = None
        
        # pattern for company names (more complex)
        company_names = list(self.company_name_dict.keys())
        if company_names:
            # sort by length, escape, and create pattern
            escaped_names = [re.escape(name) for name in company_names if len(name) > 3]
            escaped_names.sort(key=len, reverse=True)
            
            self.company_names_pattern = re.compile(
                r'\b(' + '|'.join(escaped_names) + r')\b',
                re.IGNORECASE
            ) if escaped_names else None
        else:
            self.company_names_pattern = None
    
    def tag_article_text(self, title: str, text: str, article_id: Optional[int] = None) -> List[TickerMatch]:
        """tag ticker symbols in article title and text"""
        
        full_text = f"{title} {text}" if title else text
        if not full_text.strip():
            return []
        
        matches = []
        
        # method 1: match known symbols from database
        known_matches = self._match_known_symbols(full_text)
        matches.extend(known_matches)
        
        # method 2: match company names
        company_matches = self._match_company_names(full_text)
        matches.extend(company_matches)
        
        # method 3: pattern-based matching for unknown symbols
        pattern_matches = self._match_ticker_patterns(full_text)
        matches.extend(pattern_matches)
        
        # method 4: contextual matching (ticker mentioned near company name)
        contextual_matches = self._match_contextual_tickers(full_text)
        matches.extend(contextual_matches)
        
        # deduplicate and score matches
        final_matches = self._deduplicate_and_score(matches, full_text)
        
        logger.debug(f"found {len(final_matches)} ticker matches in article")
        
        return final_matches
    
    def _match_known_symbols(self, text: str) -> List[TickerMatch]:
        """match against known symbols from database"""
        matches = []
        
        if not self.known_symbols_pattern:
            return matches
        
        for match in self.known_symbols_pattern.finditer(text):
            symbol = match.group(1).upper()
            start, end = match.span()
            
            # skip if in blacklist
            if symbol in TICKER_BLACKLIST:
                continue
            
            # get ticker object
            ticker_obj = self.symbol_dict.get(symbol)
            if not ticker_obj:
                continue
            
            # extract context
            context = self._extract_context(text, start, end)
            
            matches.append(TickerMatch(
                symbol=symbol,
                company_name=ticker_obj.get('company_name', '') or "",
                positions=[(start, end)],
                context_snippets=[context],
                confidence=0.9,  # high confidence for known symbols
                match_method="known_symbol"
            ))
        
        return matches
    
    def _match_company_names(self, text: str) -> List[TickerMatch]:
        """match company names and map to symbols"""
        matches = []
        
        if not self.company_names_pattern:
            return matches
        
        for match in self.company_names_pattern.finditer(text):
            company_name = match.group(1).lower()
            start, end = match.span()
            
            ticker_obj = self.company_name_dict.get(company_name)
            if not ticker_obj:
                # try aliases
                ticker_obj = self.alias_dict.get(company_name)
            
            if not ticker_obj:
                continue
            
            context = self._extract_context(text, start, end)
            
            matches.append(TickerMatch(
                symbol=ticker_obj['symbol'],
                company_name=ticker_obj.get('company_name', '') or "",
                positions=[(start, end)],
                context_snippets=[context],
                confidence=0.8,  # slightly lower confidence for company names
                match_method="company_name"
            ))
        
        return matches
    
    def _match_ticker_patterns(self, text: str) -> List[TickerMatch]:
        """match ticker-like patterns not in our database"""
        matches = []
        
        # use patterns from sources.py
        potential_tickers = extract_tickers_from_text(text, use_whitelist=False)
        
        for ticker in potential_tickers:
            # skip if we already know this symbol
            if ticker in self.symbol_dict:
                continue
            
            # find all occurrences in text
            pattern = re.compile(r'\b' + re.escape(ticker) + r'\b')
            for match in pattern.finditer(text):
                start, end = match.span()
                context = self._extract_context(text, start, end)
                
                # calculate confidence based on context
                confidence = self._calculate_pattern_confidence(ticker, context, text)
                
                if confidence > 0.3:  # minimum threshold
                    matches.append(TickerMatch(
                        symbol=ticker,
                        company_name="",  # unknown
                        positions=[(start, end)],
                        context_snippets=[context],
                        confidence=confidence,
                        match_method="pattern_match"
                    ))
        
        return matches
    
    def _match_contextual_tickers(self, text: str) -> List[TickerMatch]:
        """match tickers mentioned near company names or financial context"""
        matches = []
        
        # look for patterns like "Apple (AAPL)" or "AAPL shares" or "trades as MSFT"
        contextual_patterns = [
            re.compile(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*\(\s*([A-Z]{1,5})\s*\)'),  # Company (TICKER)
            re.compile(r'\b([A-Z]{1,5})\s+(?:stock|shares|equity)', re.IGNORECASE),  # TICKER stock
            re.compile(r'(?:trades|trading|listed)\s+as\s+([A-Z]{1,5})', re.IGNORECASE),  # trades as TICKER
            re.compile(r'ticker\s+(?:symbol\s+)?([A-Z]{1,5})', re.IGNORECASE),  # ticker TICKER
            re.compile(r'\$([A-Z]{1,5})\b'),  # $TICKER
        ]
        
        for pattern in contextual_patterns:
            for match in pattern.finditer(text):
                groups = match.groups()
                ticker = groups[-1].upper()  # last group is usually the ticker
                start, end = match.span()
                
                # skip blacklisted terms
                if ticker in TICKER_BLACKLIST:
                    continue
                
                context = self._extract_context(text, start, end, window=100)
                confidence = self._calculate_contextual_confidence(ticker, context, match.group(0))
                
                company_name = groups[0] if len(groups) > 1 and groups[0] else ""
                
                if confidence > 0.5:
                    matches.append(TickerMatch(
                        symbol=ticker,
                        company_name=company_name,
                        positions=[(start, end)],
                        context_snippets=[context],
                        confidence=confidence,
                        match_method="contextual_match"
                    ))
        
        return matches
    
    def _extract_context(self, text: str, start: int, end: int, window: int = 50) -> str:
        """extract context around a match"""
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        
        context = text[context_start:context_end].strip()
        
        # clean up context
        context = ' '.join(context.split())  # normalize whitespace
        
        return context
    
    def _calculate_pattern_confidence(self, ticker: str, context: str, full_text: str) -> float:
        """calculate confidence for pattern-matched tickers"""
        confidence = 0.5  # base confidence
        
        context_lower = context.lower()
        
        # positive indicators
        financial_indicators = ['stock', 'shares', 'trading', 'market', 'price', 'earnings', 
                               'revenue', 'investor', 'analyst', 'upgrade', 'downgrade']
        
        for indicator in financial_indicators:
            if indicator in context_lower:
                confidence += 0.1
        
        # bonus for dollar sign prefix
        if f'${ticker}' in full_text:
            confidence += 0.2
        
        # bonus for multiple mentions
        mention_count = full_text.count(ticker)
        confidence += min(mention_count * 0.05, 0.2)
        
        # penalty for very common letter combinations
        if ticker in ['THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 'HER', 'WAS', 'ONE', 'OUR', 'HAD', 'BUT', 'SAID']:
            confidence *= 0.1
        
        return min(confidence, 1.0)
    
    def _calculate_contextual_confidence(self, ticker: str, context: str, matched_text: str) -> float:
        """calculate confidence for contextually matched tickers"""
        confidence = 0.7  # higher base for contextual matches
        
        # bonus for parenthetical format "Company (TICKER)"
        if '(' in matched_text and ')' in matched_text:
            confidence += 0.2
        
        # bonus for explicit financial language
        financial_terms = ['stock', 'shares', 'ticker', 'symbol', 'trades', 'listed', 'nasdaq', 'nyse']
        for term in financial_terms:
            if term in matched_text.lower():
                confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _deduplicate_and_score(self, matches: List[TickerMatch], text: str) -> List[TickerMatch]:
        """deduplicate matches and calculate final scores"""
        
        # group matches by symbol
        symbol_matches = defaultdict(list)
        for match in matches:
            symbol_matches[match.symbol].append(match)
        
        final_matches = []
        
        for symbol, match_list in symbol_matches.items():
            if not match_list:
                continue
            
            # merge matches for the same symbol
            all_positions = []
            all_contexts = []
            confidences = []
            methods = []
            
            for match in match_list:
                all_positions.extend(match.positions)
                all_contexts.extend(match.context_snippets)
                confidences.append(match.confidence)
                methods.append(match.match_method)
            
            # calculate final confidence (weighted average, favoring higher confidences)
            final_confidence = max(confidences) * 0.7 + (sum(confidences) / len(confidences)) * 0.3
            
            # get best company name
            company_names = [m.company_name for m in match_list if m.company_name]
            best_company_name = max(company_names, key=len) if company_names else ""
            
            # count mentions
            mention_count = len(all_positions)
            
            # boost confidence for multiple mentions
            if mention_count > 1:
                final_confidence = min(final_confidence * (1 + mention_count * 0.05), 1.0)
            
            final_matches.append(TickerMatch(
                symbol=symbol,
                company_name=best_company_name,
                positions=all_positions,
                context_snippets=all_contexts[:5],  # keep top 5 contexts
                confidence=final_confidence,
                match_method=max(methods, key=lambda m: {'known_symbol': 4, 'company_name': 3, 'contextual_match': 2, 'pattern_match': 1}.get(m, 0))
            ))
        
        # sort by confidence
        final_matches.sort(key=lambda m: m.confidence, reverse=True)
        
        return final_matches
    
    def persist_ticker_associations(self, article_id: int, ticker_matches: List[TickerMatch]):
        """save ticker associations to database"""
        
        if not ticker_matches:
            return
        
        associations_data = []
        
        for match in ticker_matches:
            # get or create ticker symbol
            existing_ticker = db_manager.execute_query(
                "SELECT id FROM ticker_symbols WHERE symbol = ?",
                [match.symbol]
            )
            
            if existing_ticker.empty:
                # create new ticker
                next_id = db_manager.execute_query("SELECT COALESCE(MAX(id), 0) + 1 as next_id FROM ticker_symbols").iloc[0]['next_id']
                ticker_data = pd.DataFrame([{
                    'id': int(next_id),
                    'symbol': match.symbol,
                    'company_name': match.company_name if match.company_name else None,
                    'aliases': '[]',
                    'sector': None,
                    'market_cap': None,
                    'is_active': True,
                    'created_at': pd.Timestamp.now()
                }])
                
                db_manager.insert_dataframe(ticker_data, 'ticker_symbols', mode='append')
                
                # get the new ID
                ticker_result = db_manager.execute_query(
                    "SELECT id FROM ticker_symbols WHERE symbol = ?",
                    [match.symbol]
                )
                ticker_id = ticker_result.iloc[0]['id']
            else:
                ticker_id = existing_ticker.iloc[0]['id']
            
            # create association data
            associations_data.append({
                'id': len(associations_data) + 1,  # manual ID
                'article_id': article_id,
                'ticker_id': ticker_id,
                'confidence': match.confidence,
                'match_method': match.match_method,
                'context_snippet': match.context_snippets[0] if match.context_snippets else '',
                'created_at': pd.Timestamp.now()
            })
        
        if associations_data:
            associations_df = pd.DataFrame(associations_data)
            db_manager.insert_dataframe(associations_df, 'article_ticker_associations', mode='append')
            logger.debug(f"saved {len(ticker_matches)} ticker associations for article {article_id}")

# utility functions for populating ticker database
def populate_ticker_database_from_csv(csv_path: str):
    """populate ticker database from csv file with symbol,company_name,sector columns"""
    import pandas as pd
    
    df = pd.read_csv(csv_path)
    
    # prepare data
    ticker_data = []
    for _, row in df.iterrows():
        symbol = row['symbol'].strip().upper()
        company_name = row.get('company_name', '').strip()
        sector = row.get('sector', '').strip()
        
        # check if already exists
        existing = db_manager.execute_query(
            "SELECT id FROM ticker_symbols WHERE symbol = ?",
            [symbol]
        )
        if not existing.empty:
            continue
        
        ticker_data.append({
            'symbol': symbol,
            'company_name': company_name if company_name else None,
            'sector': sector if sector else None,
            'aliases': '[]',
            'is_active': True,
            'created_at': pd.Timestamp.now()
        })
    
    if ticker_data:
        ticker_df = pd.DataFrame(ticker_data)
        db_manager.insert_dataframe(ticker_df, 'ticker_symbols', mode='append')
        logger.info(f"populated ticker database with {len(ticker_data)} symbols")

def populate_sp500_tickers():
    """populate database with S&P 500 tickers (example)"""
    
    # this would normally fetch from a reliable source
    sp500_tickers = [
        ('AAPL', 'Apple Inc.', 'Technology'),
        ('MSFT', 'Microsoft Corporation', 'Technology'), 
        ('GOOGL', 'Alphabet Inc.', 'Technology'),
        ('AMZN', 'Amazon.com Inc.', 'Consumer Discretionary'),
        ('TSLA', 'Tesla Inc.', 'Consumer Discretionary'),
        ('META', 'Meta Platforms Inc.', 'Communication Services'),
        ('NVDA', 'NVIDIA Corporation', 'Technology'),
        ('JPM', 'JPMorgan Chase & Co.', 'Financials'),
        ('V', 'Visa Inc.', 'Information Technology'),
        ('JNJ', 'Johnson & Johnson', 'Health Care'),
        # add more as needed...
    ]
    
    ticker_data = []
    for symbol, name, sector in sp500_tickers:
        # check if already exists
        existing = db_manager.execute_query(
            "SELECT id FROM ticker_symbols WHERE symbol = ?",
            [symbol]
        )
        if not existing.empty:
            continue
        
        ticker_data.append({
            'id': len(ticker_data) + 1,  # manual ID
            'symbol': symbol,
            'company_name': name,
            'sector': sector,
            'market_cap': 'large',
            'aliases': '[]',
            'is_active': True,
            'created_at': pd.Timestamp.now()
        })
    
    if ticker_data:
        ticker_df = pd.DataFrame(ticker_data)
        db_manager.insert_dataframe(ticker_df, 'ticker_symbols', mode='append')
        logger.info(f"populated database with {len(ticker_data)} S&P 500 tickers")